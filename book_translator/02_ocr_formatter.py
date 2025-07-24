"""Format OCR output using Gemini 2.5 Flash Lite."""

import os
import re
from pathlib import Path
from google import genai
from dotenv import load_dotenv


def extract_page_range(content: str, start_page: int, end_page: int) -> str:
    """Extract specific page range from markdown content."""
    pages = []
    current_page = None
    current_content = []
    
    for line in content.split('\n'):
        # Check for page marker
        page_match = re.match(r'^#\s*Page\s*(\d+)', line)
        if page_match:
            # Save previous page if in range
            if current_page and start_page <= current_page <= end_page:
                pages.append('\n'.join(current_content))
            
            current_page = int(page_match.group(1))
            current_content = []
            
            # Skip the page header line - don't add it
        elif line.strip() == '---':
            # Skip separators
            continue
        # Add content if we're in a page
        elif current_page and start_page <= current_page <= end_page:
            current_content.append(line)
    
    # Don't forget the last page
    if current_page and start_page <= current_page <= end_page:
        pages.append('\n'.join(current_content))
    
    return '\n\n'.join(pages)


def format_text(client: genai.Client, text: str) -> str:
    """Use Flash Lite to fix formatting and remove page numbers."""
    
    format_prompt = """
    Reformat this German text with proper line lengths and paragraph structure.
    
    Instructions:
    1. Remove standalone page numbers (like "7" or "24" on their own lines)
    2. Join lines that are part of the same paragraph
    3. Keep proper paragraph breaks (single blank line between paragraphs)
    4. Preserve section headers and special formatting
    5. Fix obvious line break issues from OCR
    6. Keep the content exactly the same, just fix formatting
    7. Do not add any introduction like "Here is..." - just provide the reformatted text
    
    Text to format:
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[format_prompt, text]
        )
        if response.text:
            return response.text
        return text
    except Exception as e:
        print(f"Error in formatting: {e}")
        return text


def main():
    """Main formatting function."""
    load_dotenv()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found")
        return
    
    # Temporarily unset GOOGLE_API_KEY to avoid warning
    google_api_key = os.environ.pop("GOOGLE_API_KEY", None)
    client = genai.Client(api_key=api_key)
    if google_api_key:
        os.environ["GOOGLE_API_KEY"] = google_api_key
    
    # Hardcoded file paths
    gemini_file = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-gemini.md"
    mistral_file = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-mistral.md"
    
    # Process both files
    for source, filepath in [("Gemini", gemini_file), ("Mistral", mistral_file)]:
        print(f"\n{'='*50}")
        print(f"Processing {source} output")
        print('='*50)
        
        print(f"Reading {filepath}...")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {filepath}")
            continue
        
        # Extract pages 4-13
        print("Extracting pages 4-13...")
        extracted_text = extract_page_range(content, 4, 13)
        
        if not extracted_text:
            print(f"Error: No content found in page range 4-13 for {source}")
            continue
        
        print(f"Extracted {len(extracted_text)} characters")
        
        # Format with Flash Lite
        print(f"\nFormatting {source} text with Gemini 2.5 Flash Lite...")
        formatted_text = format_text(client, extracted_text)
        
        # Save result with source name
        output_file = f"test-book-pdfs/pages_4-13_{source.lower()}_formatted.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# pages_4-13_{source.lower()}_formatted.md\n\n")
            f.write(formatted_text)
        
        print(f"Formatted text saved to: {output_file}")
    
    print("\n\nFormatting complete!")
    print("Output files:")
    print("- test-book-pdfs/pages_4-13_gemini_formatted.md")
    print("- test-book-pdfs/pages_4-13_mistral_formatted.md")


if __name__ == "__main__":
    main()