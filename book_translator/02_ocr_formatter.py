"""Format OCR output using Gemini 2.5 Flash."""

import os

from dotenv import load_dotenv
from google import genai

# ============== CONFIGURATION ==============
GEMINI_FILE = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-gemini-4-26.md"
MISTRAL_FILE = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-mistral-4-26.md"
GEMINI_OUTPUT = "test-book-pdfs/pages_4-26_gemini_formatted.md"
MISTRAL_OUTPUT = "test-book-pdfs/pages_4-26_mistral_formatted.md"
# ==========================================


def format_text(client: genai.Client, text: str) -> str:
    """Use Flash to fix formatting and remove page numbers."""
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
    """Format OCR output files."""
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
    
    files_to_process = [
        ("Gemini", GEMINI_FILE, GEMINI_OUTPUT),
        ("Mistral", MISTRAL_FILE, MISTRAL_OUTPUT)
    ]
    
    for source, input_file, output_file in files_to_process:
        print(f"\n{'='*50}")
        print(f"Processing {source} output")
        print('='*50)
        
        print(f"Reading {input_file}...")
        
        try:
            with open(input_file, encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {input_file}")
            continue
        
        print(f"Read {len(content)} characters")
        
        print(f"\nFormatting {source} text with Gemini 2.5 Flash...")
        formatted_text = format_text(client, content)
        
        # Save result
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {os.path.basename(output_file)}\n\n")
            f.write(formatted_text)
        
        print(f"Formatted text saved to: {output_file}")
    
    print("\n\nFormatting complete!")
    print("Output files:")
    print(f"- {GEMINI_OUTPUT}")
    print(f"- {MISTRAL_OUTPUT}")


if __name__ == "__main__":
    main()