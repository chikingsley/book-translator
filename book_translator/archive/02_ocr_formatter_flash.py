"""Format OCR output using Gemini 2.5 Flash."""

import os
import re

from dotenv import load_dotenv
from google import genai


def extract_page_range(content: str, start_page: int, end_page: int) -> str:
    """Extract specific page range from markdown content."""
    pages: list[str] = []
    current_page: int | None = None
    current_content: list[str] = []

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
    """Use Gemini Flash to fix formatting and remove page numbers."""
    format_prompt = """You are formatting German text from OCR. Please reformat this text with proper paragraph structure and remove OCR artifacts.

Instructions:
1. Remove standalone page numbers (like "7", "8", "9", "10", "11", "12", "13", "14", "15", "17" on their own lines)
2. Join lines that are part of the same paragraph - OCR often breaks paragraphs incorrectly
3. Keep proper paragraph breaks (single blank line between paragraphs)
4. Add proper markdown headers: ## VORWORT and ## IN MEMORIAM FERRUCCIO BUSONI
5. Fix obvious line break issues from OCR
6. Remove hyphens that split words across lines (e.g., "mechanistischen Na-" should connect to "turwissenschaften")
7. Standardize German quotation marks to »« style consistently
8. Fix broken quotation marks like <<<Göttern>>> or «Götter>>> to proper «Götter»
9. Keep the content exactly the same, just fix formatting
10. Do not add any introduction or explanation - just provide the reformatted text
11. Preserve poem structure and indentation
12. Remove duplicate content that appears multiple times
13. Ensure no sentences are cut off or truncated - complete all thoughts
14. If text seems to end abruptly, indicate with [...] rather than cutting off mid-sentence

Text to format:"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[format_prompt, text]
        )
        if response.text:
            return response.text
        return text
    except Exception as e:
        print(f"Error in formatting: {e}")
        return text


def main() -> None:
    """Format OCR text using Gemini Flash."""
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

    # Hardcoded file path for Gemini Pro Adaptive
    gemini_file = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz_pages_4_26_gemini_pro_single.md"

    print("Processing Gemini Pro Adaptive OCR output with Flash (Pages 4-26)")
    print('=' * 70)

    print(f"Reading {gemini_file}...")

    try:
        with open(gemini_file, encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {gemini_file}")
        return

    # Extract pages 4-26
    print("Extracting pages 4-26...")
    extracted_text = extract_page_range(content, 4, 26)

    if not extracted_text:
        print("Error: No content found in page range 4-26")
        return

    print(f"Extracted {len(extracted_text)} characters")

    # Format with Gemini Flash
    print("\nFormatting text with Gemini 2.5 Flash...")
    formatted_text = format_text(client, extracted_text)

    # Save result
    output_file = "test-book-pdfs/pages_4_26_gemini_pro_adaptive_flash_formatted.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Pages 4-26 - Gemini Pro Adaptive - Flash Formatted\n\n")
        f.write(formatted_text)

    print(f"Formatted text saved to: {output_file}")
    print("Formatting complete!")


if __name__ == "__main__":
    main()
