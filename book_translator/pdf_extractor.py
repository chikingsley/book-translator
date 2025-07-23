#!/usr/bin/env python3
"""PDF content extraction using PyMuPDF4LLM.

Extracts text in markdown format and metadata from PDF files.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pymupdf
import pymupdf4llm


class PDFExtractor:
    """Extract content from PDF files using PyMuPDF4LLM."""

    def __init__(self, pdf_path: str):
        """Initialize the PDF extractor with a PDF file path."""
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.doc = pymupdf.open(str(self.pdf_path))
        self.output_dir = self.pdf_path.parent / f"{self.pdf_path.stem}_extracted"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_text(self) -> str:
        """Extract text from all pages of the PDF in markdown format.
        
        Returns:
            Extracted text as markdown string

        """
        # Use pymupdf4llm to extract markdown
        markdown_text = pymupdf4llm.to_markdown(str(self.pdf_path))
        return markdown_text
    
    def extract_text_by_page(self) -> list[str]:
        """Extract text page by page in markdown format, returning a list of page texts."""
        page_texts = []
        
        # Extract each page separately
        for page_num in range(self.doc.page_count):
            # Extract just this page
            page_markdown = pymupdf4llm.to_markdown(
                str(self.pdf_path),
                pages=[page_num]
            )
            page_texts.append(page_markdown)
        
        return page_texts
    
    def extract_metadata(self) -> dict[str, Any]:
        """Extract document metadata."""
        metadata = dict(self.doc.metadata)
        
        # Add custom metadata
        metadata['page_count'] = self.doc.page_count
        metadata['is_encrypted'] = self.doc.is_encrypted
        metadata['is_form_pdf'] = getattr(self.doc, 'is_form_pdf', False)
        
        # Convert datetime objects to strings for JSON serialization
        for key, value in metadata.items():
            if hasattr(value, 'isoformat'):
                metadata[key] = value.isoformat()
        
        return metadata
    
    def extract_all(self) -> dict[str, Any]:
        """Extract all content from the PDF."""
        # Extract text in markdown format
        markdown_content = self.extract_text()
        with open(self.output_dir / "content.md", "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        # Extract metadata
        metadata = self.extract_metadata()
        with open(self.output_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        # Summary
        summary = {
            'pdf_file': str(self.pdf_path),
            'output_directory': str(self.output_dir),
            'page_count': self.doc.page_count,
            'markdown_file': str(self.output_dir / "content.md"),
            'metadata_file': str(self.output_dir / "metadata.json")
        }
        
        return summary
    
    def close(self):
        """Close the PDF document."""
        self.doc.close()
    
    def __enter__(self):
        """Enter the context manager."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context manager and close the PDF document."""
        self.close()


def main():
    """Run the PDF extractor from command line."""
    parser = argparse.ArgumentParser(description="Extract content from PDF files using PyMuPDF4LLM")
    parser.add_argument("pdf_file", help="Path to the PDF file")
    parser.add_argument("--page-by-page", action="store_true", 
                       help="Save text page by page in separate markdown files")
    
    args = parser.parse_args()
    
    try:
        with PDFExtractor(args.pdf_file) as extractor:
            if args.page_by_page:
                # Extract page by page
                page_texts = extractor.extract_text_by_page()
                for i, text in enumerate(page_texts, 1):
                    page_file = extractor.output_dir / f"page_{i:04d}.md"
                    with open(page_file, "w", encoding="utf-8") as f:
                        f.write(text)
                print(f"Extracted {len(page_texts)} pages to {extractor.output_dir}")
            else:
                # Full extraction
                summary = extractor.extract_all()
                print("\nExtraction completed successfully!")
                print(f"Output directory: {summary['output_directory']}")
                print(f"Pages extracted: {summary['page_count']}")
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())