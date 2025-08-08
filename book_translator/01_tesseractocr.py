#!/usr/bin/env python3
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false
"""Modern PyMuPDF + Tesseract OCR Script.

Creates searchable PDFs with invisible text layers mapped to original coordinates.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

import pymupdf

# ============== CONFIGURATION ==============
PDF_PATH = "../test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz.pdf"
TESSERACT_LANGUAGE = "deu"
# ==========================================


class TesseractOCR:
    """Modern PyMuPDF OCR with coordinate mapping and invisible text layers."""

    def __init__(self, tessdata_prefix: str | None = None):
        """Initialize OCR with optional Tesseract data path."""
        if tessdata_prefix:
            os.environ['TESSDATA_PREFIX'] = tessdata_prefix
        elif 'TESSDATA_PREFIX' not in os.environ:
            # Set default tessdata path for Homebrew installation
            os.environ['TESSDATA_PREFIX'] = '/opt/homebrew/share/tessdata'

        # Check if Tesseract is available
        try:
            # Test OCR capability
            test_doc = pymupdf.open()
            test_page = test_doc.new_page()
            test_page.get_textpage_ocr()  # type: ignore
            test_doc.close()
        except Exception as e:
            print(f"Tesseract OCR not available: {e}")
            sys.exit(1)

    def analyze_pdf(self, pdf_path: str) -> dict[str, Any]:
        """Analyze PDF to determine which pages need OCR."""
        doc = pymupdf.open(pdf_path)
        analysis: dict[str, Any] = {
            'total_pages': len(doc),
            'text_pages': [],
            'image_pages': [],
            'mixed_pages': [],
            'needs_ocr': []
        }

        for page_num in range(len(doc)):
            page = doc[page_num]
            text_dict = page.get_text("dict")  # type: ignore
            text_blocks: list[Any] = []
            if isinstance(text_dict, dict) and "blocks" in text_dict:
                text_blocks = cast(list[Any], text_dict["blocks"])
            image_blocks = page.get_images()

            has_text = any(
                isinstance(block, dict) and block.get("type") == 0 and bool(block.get("lines"))
                for block in text_blocks
            )
            has_images = len(image_blocks) > 0

            # Calculate text density
            page_text = page.get_text()  # type: ignore
            text_chars = len(page_text.strip())

            if has_text and text_chars > 50:
                if has_images:
                    analysis['mixed_pages'].append(page_num)
                else:
                    analysis['text_pages'].append(page_num)
            elif has_images or text_chars < 10:
                analysis['image_pages'].append(page_num)
                analysis['needs_ocr'].append(page_num)
            else:
                analysis['mixed_pages'].append(page_num)

        doc.close()
        return analysis

    def extract_with_ocr(self, pdf_path: str, language: str = "eng") -> dict[str, Any]:
        """Extract text using OCR with coordinate mapping."""
        doc = pymupdf.open(pdf_path)
        results: dict[str, Any] = {
            'pages': [],
            'full_text': '',
            'metadata': {
                'source': pdf_path,
                'language': language,
                'total_pages': len(doc)
            }
        }

        print(f"Processing {len(doc)} pages with OCR...")

        for page_num in range(len(doc)):
            page = doc[page_num]
            print(f"OCR processing page {page_num + 1}/{len(doc)}")

            # Get OCR text with coordinates
            textpage_ocr = page.get_textpage_ocr(language=language, dpi=300)  # type: ignore

            # Extract text blocks with coordinates
            blocks: list[dict[str, Any]] = []
            text_dict = textpage_ocr.extractDICT()  # type: ignore

            if isinstance(text_dict, dict) and "blocks" in text_dict:
                text_blocks_list = cast(list[Any], text_dict["blocks"])
                for block in text_blocks_list:
                    if isinstance(block, dict) and block.get("type") == 0:  # Text block
                        lines = cast(list[Any], block.get("lines", []))
                        for line in lines:
                            if isinstance(line, dict):
                                spans = cast(list[Any], line.get("spans", []))
                                for span in spans:
                                    if isinstance(span, dict):
                                        blocks.append({
                                            'text': str(span.get("text", "")),
                                            'bbox': list(span.get("bbox", [0, 0, 0, 0])),
                                            'font': str(span.get("font", "")),
                                            'size': float(span.get("size", 0)),
                                            'confidence': 1.0  # PyMuPDF doesn't provide confidence
                                        })

            page_text = textpage_ocr.extractText()  # type: ignore

            results['pages'].append({
                'page_num': page_num,
                'text': page_text,
                'blocks': blocks,
                'bbox_count': len(blocks)
            })

            results['full_text'] += f"\n--- Page {page_num + 1} ---\n{page_text}\n"

        doc.close()
        return results

    def create_searchable_pdf(self, pdf_path: str, output_path: str, language: str = "eng") -> str:
        """Create searchable PDF with invisible text layer using modern PyMuPDF methods."""
        doc = pymupdf.open(pdf_path)
        new_doc = pymupdf.open()  # Create new document

        print(f"Creating searchable PDF: {output_path}")

        for page_num in range(len(doc)):
            page = doc[page_num]
            print(f"Adding OCR text layer to page {page_num + 1}/{len(doc)}")

            # Get page as high-resolution pixmap
            mat = pymupdf.Matrix(2.0, 2.0)  # 2x zoom for better OCR
            pix = page.get_pixmap(matrix=mat)  # type: ignore

            # Use modern pdfocr_tobytes method to create PDF with invisible text layer
            pdf_bytes = pix.pdfocr_tobytes(language=language, tessdata=None)  # type: ignore

            # Open the OCR result and add to new document
            ocr_doc = pymupdf.open("pdf", pdf_bytes)  # type: ignore
            new_doc.insert_pdf(ocr_doc)
            ocr_doc.close()

            pix = None  # Free pixmap memory

        # Save the searchable PDF
        new_doc.save(output_path, garbage=4, deflate=True, clean=True)
        new_doc.close()
        doc.close()

        return output_path

    def create_comparison_pdf(self, pdf_path: str, output_path: str, language: str = "eng") -> str:
        """Create PDF showing OCR differences with visible overlays."""
        doc = pymupdf.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Get OCR text with coordinates
            textpage_ocr = page.get_textpage_ocr(language=language, dpi=300)  # type: ignore
            text_dict = textpage_ocr.extractDICT()  # type: ignore

            # Draw colored rectangles around OCR text blocks
            if isinstance(text_dict, dict) and "blocks" in text_dict:
                text_blocks_list = cast(list[Any], text_dict["blocks"])
                for block in text_blocks_list:
                    if isinstance(block, dict) and block.get("type") == 0:  # Text block
                        lines = cast(list[Any], block.get("lines", []))
                        for line in lines:
                            if isinstance(line, dict):
                                spans = cast(list[Any], line.get("spans", []))
                                for span in spans:
                                    if isinstance(span, dict) and "bbox" in span:
                                        bbox_data = span["bbox"]
                                        if isinstance(bbox_data, list | tuple) and len(bbox_data) >= 4:
                                            bbox = pymupdf.Rect(bbox_data)  # type: ignore
                                            # Draw semi-transparent overlay
                                            page.draw_rect(bbox, color=(0, 1, 0), width=1, fill=(0, 1, 0, 0.2))

                                            # Add small text annotation
                                            text_point = pymupdf.Point(bbox.x0, bbox.y0 - 2)
                                            span_text = str(span.get("text", ""))
                                            page.insert_text(text_point, f"OCR: {len(span_text)} chars",
                                                           fontsize=6, color=(0, 0.5, 0))

        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()

        return output_path

    def save_ocr_data(self, ocr_results: dict[str, Any], output_path: str) -> str:
        """Save OCR results as JSON for analysis."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ocr_results, f, indent=2, ensure_ascii=False)
        return output_path


def main() -> None:
    """Run the OCR processing based on command line arguments."""
    parser = argparse.ArgumentParser(description="Modern PyMuPDF Tesseract OCR")
    parser.add_argument("--create-searchable", action="store_true", help="Create searchable PDF")
    parser.add_argument("--create-comparison", action="store_true", help="Create comparison PDF with visible OCR")

    args = parser.parse_args()

    # Validate input
    input_path = Path(PDF_PATH)
    if not input_path.exists():
        print(f"Error: Input file {input_path} not found")
        sys.exit(1)

    # Setup output directory (same as input)
    output_dir = input_path.parent
    output_dir.mkdir(exist_ok=True)

    # Initialize OCR
    ocr = TesseractOCR()

    base_name = input_path.stem

    print(f"Processing PDF: {input_path}")
    print(f"Using Tesseract language: {TESSERACT_LANGUAGE}")

    # Default behavior: Extract text as markdown
    if not (args.create_searchable or args.create_comparison):
        print("📝 Extracting text to Markdown...")
        ocr_results = ocr.extract_with_ocr(str(input_path), TESSERACT_LANGUAGE)

        # Save as markdown with -tesseract suffix
        markdown_path = output_dir / f"{base_name}-tesseract.md"
        with open(markdown_path, 'w', encoding='utf-8') as f:
            full_text = ocr_results.get('full_text', '')
            if isinstance(full_text, str):
                f.write(full_text)
        print(f"Markdown saved: {markdown_path}")
        print(f"OCR extraction complete! Total pages processed: {ocr_results.get('metadata', {}).get('total_pages', 0)}")
        return

    # Create searchable PDF
    if args.create_searchable:
        print("\n📄 Creating searchable PDF...")
        searchable_path = output_dir / f"{base_name}_searchable.pdf"
        ocr.create_searchable_pdf(str(input_path), str(searchable_path), TESSERACT_LANGUAGE)
        print(f"Searchable PDF created: {searchable_path}")

    # Create comparison PDF
    if args.create_comparison:
        print("\n🔍 Creating comparison PDF...")
        comparison_path = output_dir / f"{base_name}_ocr_comparison.pdf"
        ocr.create_comparison_pdf(str(input_path), str(comparison_path), TESSERACT_LANGUAGE)
        print(f"Comparison PDF created: {comparison_path}")

    print("\n✅ OCR processing complete!")


if __name__ == "__main__":
    main()
