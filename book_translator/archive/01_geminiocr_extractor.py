"""Gemini OCR extractor for PDF documents."""

import os
import sys
import time
from pathlib import Path

import pymupdf
from dotenv import load_dotenv
from google import genai


def save_markdown(content: str, output_path: str) -> None:
    """Save markdown content to a file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Markdown saved to: {output_path}")
    except Exception as e:
        print(f"Error saving file: {e}")

def main() -> None:
    """Process PDF with Gemini OCR."""
    pdf_path = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz.pdf"
    load_dotenv()
    
    if not os.path.exists(pdf_path):
        print(f"Error: The file {pdf_path} was not found.")
        sys.exit(1)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables or .env file")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    print(f"Processing PDF: {pdf_path}")
    print("Uploading PDF to Gemini...")
    
    try:
        pdf_file = client.files.upload(file=pdf_path)
        print("PDF uploaded successfully")
    except Exception as e:
        print(f"Error uploading PDF: {e}")
        sys.exit(1)
    
    print("Getting page count...")
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    doc.close()
    print(f"Total pages in PDF: {total_pages}")
    
    input_path = Path(pdf_path)
    output_path = input_path.with_stem(input_path.stem + '-gemini').with_suffix('.md')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("") 
    
    print(f"Output will be written to: {output_path}")
    
    failed_pages = 0
    first_page = True
    
    for page_num in range(1, total_pages + 1):
        retry_count = 0
        page_extracted = False
        
        while not page_extracted:
            retry_count += 1
            status = f"Page {page_num}/{total_pages} ({page_num/total_pages*100:.1f}%)"
            if retry_count > 1:
                status += f" - Retry {retry_count}"
            print(f"\r{status}...", end='', flush=True)
            
            page_prompt = f"""
            Extract all text from page {page_num} of this PDF exactly as it appears.
            Start with "# Page {page_num}"
            Then provide the raw text without any modifications.
            """
            
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-pro",
                    contents=[page_prompt, pdf_file]
                )
                
                if response.text and len(response.text.strip()) > 20:
                    with open(output_path, 'a', encoding='utf-8') as f:
                        if not first_page:
                            f.write("\n\n---\n\n")
                        f.write(response.text)
                    
                    first_page = False
                    page_extracted = True
                elif retry_count < 5:
                    time.sleep(2)  
                    continue
                else:
                    print(f"\n  Waiting 10s before retry (attempt {retry_count})...")
                    time.sleep(10)
                    
            except Exception as e:
                error_msg = str(e)
                if "500" in error_msg or "rate" in error_msg.lower():
                    wait_time = min(30, 5 * retry_count)
                    print(f"\n  Error: {error_msg[:50]}... Waiting {wait_time}s before retry")
                    time.sleep(wait_time)
                else:
                    print(f"\n  Error on page {page_num}: {error_msg[:50]}...")
                    time.sleep(2)
        
        if not page_extracted:
            failed_pages += 1
    
    print("\n\nAll pages processed!")
    print(f"OCR extraction complete! Total pages: {total_pages}, Successfully extracted: {total_pages - failed_pages}")
    print(f"Output saved to: {output_path}")

if __name__ == "__main__":
    main()