"""Mistral OCR extractor for PDF documents."""

import base64
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from mistralai import Mistral


def encode_pdf(pdf_path: str) -> str | None:
    """Encode the pdf to base64."""
    try:
        with open(pdf_path, "rb") as pdf_file:
            return base64.b64encode(pdf_file.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"Error: The file {pdf_path} was not found.")
        return None
    except Exception as e:  # Added general exception handling
        print(f"Error: {e}")
        return None

def save_markdown(content: str, output_path: str) -> None:
    """Save markdown content to a file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Markdown saved to: {output_path}")
    except Exception as e:
        print(f"Error saving file: {e}")

def process_footnotes(text: str) -> str:
    """Convert LaTeX-style footnote references to Markdown footnote syntax.
    
    Converts:
    - ${ }^{n}$ or ${^{n}}$ in text to [^n]
    - Lines starting with ${ }^{n}$ to [^n]: format
    """
    # First pass: Convert inline footnote references
    # Match patterns like ${ }^{2}$ or ${^{2}}$
    text = re.sub(r'\$\{\s*\^\{(\d+)\}\s*\}', r'[^\1]', text)
    
    # Second pass: Convert footnote definitions at start of lines
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        # Check if line starts with footnote pattern
        footnote_match = re.match(r'^\$\{\s*\^\{(\d+)\}\s*\}\s*(.*)', line)
        if footnote_match:
            footnote_num = footnote_match.group(1)
            footnote_text = footnote_match.group(2)
            processed_lines.append(f'[^{footnote_num}]: {footnote_text}')
        else:
            processed_lines.append(line)
    
    return '\n'.join(processed_lines)

def main() -> None:
    """Run Mistral OCR extraction on PDF."""
    # Hardcoded PDF path
    pdf_path = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz.pdf"
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Getting the base64 string
    print(f"Processing PDF: {pdf_path}")
    base64_pdf = encode_pdf(pdf_path)
    if not base64_pdf:
        sys.exit(1)
    
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("Error: MISTRAL_API_KEY not found in environment variables or .env file")
        sys.exit(1)
    
    client = Mistral(api_key=api_key)
    
    print("Calling Mistral OCR API...")
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{base64_pdf}" 
        },
        include_image_base64=False  # We don't need images
    )
    
    # Extract markdown from all pages
    print("Extracting markdown content...")
    markdown_pages = []
    for i, page in enumerate(ocr_response.pages):
        if page.markdown:
            markdown_pages.append(f"# Page {i + 1}\n\n{page.markdown}")
    
    # Combine all pages
    full_markdown = "\n\n---\n\n".join(markdown_pages)
    
    # Process footnotes
    print("Processing footnote references...")
    full_markdown = process_footnotes(full_markdown)
    
    # Generate output filename with -mistral suffix
    input_path = Path(pdf_path)
    output_path = input_path.with_stem(input_path.stem + '-mistral').with_suffix('.md')
    
    # Save to file
    save_markdown(full_markdown, str(output_path))
    
    print(f"OCR extraction complete! Total pages processed: {len(ocr_response.pages)}")

if __name__ == "__main__":
    main()