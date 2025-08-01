"""Extract Table of Contents from PDF using PyMuPDF."""

import json
import sys
from pathlib import Path
from typing import Any, cast

import pymupdf


def extract_toc(pdf_path: str) -> list[dict[str, Any]]:
    """Extract table of contents from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of TOC entries with level, title, and page number

    """
    try:
        doc = pymupdf.open(pdf_path)
        raw_toc = doc.get_toc()  # type: ignore
        
        if not raw_toc:
            print("No table of contents found in the PDF.")
            return []
        
        toc = cast(list[tuple[int, str, int]], raw_toc)
        formatted_toc: list[dict[str, Any]] = []
        
        for level, title, page in toc:
            formatted_toc.append({
                "level": level,
                "title": title,
                "page": page
            })
        
        doc.close()
        return formatted_toc
        
    except Exception as e:
        print(f"Error extracting TOC: {e}")
        return []


def format_toc_markdown(toc: list[dict[str, Any]]) -> str:
    """Format TOC entries as markdown.
    
    Args:
        toc: List of TOC entries
        
    Returns:
        Markdown formatted string

    """
    if not toc:
        return "# Table of Contents\n\nNo table of contents found."
    
    markdown = "# Table of Contents\n\n"
    
    for entry in toc:
        level = entry["level"]
        title = entry["title"]
        page = entry["page"]
        
        # Create indentation based on level
        indent = "  " * (level - 1)
        markdown += f"{indent}- {title} (page {page})\n"
    
    return markdown


def save_toc(toc: list[dict[str, Any]], output_path: str | None = None, output_format: str = "markdown") -> None:
    """Save TOC to file.
    
    Args:
        toc: List of TOC entries
        output_path: Output file path (if None, prints to stdout)
        output_format: Output format ('markdown' or 'json')

    """
    if output_format == "markdown":
        content = format_toc_markdown(toc)
    elif output_format == "json":
        content = json.dumps(toc, indent=2, ensure_ascii=False)
    else:
        raise ValueError(f"Unsupported format: {output_format}")
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"TOC saved to: {output_path}")
    else:
        print(content)


def main() -> None:
    """Extract TOC from PDF."""
    pdf_path = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz.pdf"
    output_path = "test-book-pdfs/toc.json"
    output_format = "json"
    
    if not Path(pdf_path).exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    print(f"Extracting TOC from: {pdf_path}")
    toc = extract_toc(pdf_path)
    
    if toc:
        print(f"Found {len(toc)} TOC entries")
        save_toc(toc, output_path, output_format)
    else:
        print("No TOC entries found")


if __name__ == "__main__":
    main()