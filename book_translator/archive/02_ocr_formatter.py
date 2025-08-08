"""Format OCR output using Gemini 2.5 Flash."""

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai

# ============== CONFIGURATION ==============
GEMINI_FILE = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-gemini.md"
TESSERACT_FILE = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-tesseract.md"
MISTRAL_FILE = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-mistral.md"
GEMINI_OUTPUT = "test-book-pdfs/gemini_formatted.md"
TESSERACT_OUTPUT = "test-book-pdfs/tesseract_formatted.md"
MISTRAL_OUTPUT = "test-book-pdfs/mistral_formatted.md"

PROCESS_LINE_RANGE: tuple[int, int] | None = None
PROCESS_PAGE_NUMBERS: list[int] | None = list(range(4, 51))
# ==========================================


def extract_pages(content: str, page_numbers: list[int]) -> str:
    """Extract specific pages from the content."""
    page_pattern = r"^# Page (\d+)$"
    page_matches = list(re.finditer(page_pattern, content, re.MULTILINE))

    if not page_matches:
        page_pattern = r"^--- Page (\d+) ---$"
        page_matches = list(re.finditer(page_pattern, content, re.MULTILINE))

    if not page_matches:
        print("Warning: No page markers found in content (tried both '# Page X' and '--- Page X ---' formats)")
        return content

    pages: list[tuple[int, int, int]] = []
    for i, match in enumerate(page_matches):
        page_num = int(match.group(1))
        start_pos = match.start()

        if i < len(page_matches) - 1:
            end_pos = page_matches[i + 1].start()
        else:
            end_pos = len(content)

        pages.append((page_num, start_pos, end_pos))

    selected_content: list[str] = []
    for page_num, start, end in pages:
        if page_num in page_numbers:
            selected_content.append(content[start:end])

    return "".join(selected_content).strip()


def apply_line_range(content: str, start_line: int, end_line: int) -> str:
    """Extract specific line range from content."""
    lines = content.split("\n")
    start_idx = max(0, start_line - 1)
    end_idx = min(len(lines), end_line)
    return "\n".join(lines[start_idx:end_idx])


def get_next_available_filename(base_path: str) -> str:
    """Get the next available filename with auto-incrementing number."""
    path = Path(base_path)

    if not path.exists():
        return base_path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    counter = 2
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return str(new_path)
        counter += 1


def count_tokens(client: genai.Client, text: str, format_prompt: str) -> int:
    """Count tokens for Gemini model input."""
    token_count = client.models.count_tokens(
        model="gemini-2.5-flash", contents=[format_prompt, text]
    )
    return token_count.total_tokens or 0


GEMINI_FORMAT_PROMPT = """
Please reformat this OCR-extracted German text by removing OCR artifacts and fixing line breaks.

1. REMOVE page headers like "# Page 1", "# Page 2", etc. - these are OCR metadata, not content
2. REMOVE horizontal rule separators "---" between pages - these are OCR page breaks, not content
3. REMOVE standalone page numbers on their own lines (like "2", "5", "24")
4. JOIN lines that were artificially broken mid-sentence (line ends without punctuation . ! ? : ; and next line continues with lowercase)
5. PRESERVE actual paragraph breaks (blank lines)
6. PRESERVE poetry formatting and quotation marks « » exactly as they appear
7. PRESERVE actual content formatting like table of contents alignment
8. OUTPUT ONLY the cleaned text - no commentary, no "Here is...", no code fences, no metadata

The goal: Remove OCR scaffolding but preserve the actual document content and structure.

Text to format:
"""

TESSERACT_FORMAT_PROMPT = """
Please reformat this Tesseract OCR-extracted German text by removing OCR formatting artifacts only.

1. REMOVE page headers like "--- Page 1 ---", "--- Page 2 ---", etc. - these are OCR metadata, not content
2. REMOVE garbled/corrupted text lines with special characters like "����������", "������", etc.
3. REMOVE nonsense single characters on their own lines (like ":", "|", "oo", ",", ".")
4. REMOVE standalone page numbers on their own lines (like "2", "5", "24")
5. JOIN lines that were artificially broken mid-sentence (line ends without punctuation . ! ? : ; and next line continues with lowercase)
6. PRESERVE actual paragraph breaks (blank lines)
7. PRESERVE poetry formatting and quotation marks exactly as they appear
8. PRESERVE actual content formatting like table of contents alignment
9. OUTPUT ONLY the cleaned text - no commentary, no "Here is...", no code fences, no metadata

IMPORTANT: Do not fix OCR recognition errors or change any words - only remove formatting artifacts and join broken lines.

The goal: Remove OCR formatting scaffolding but preserve the actual document content exactly as recognized.

Text to format:
"""


def format_text(client: genai.Client, text: str, prompt: str) -> str:
    """Use Flash to fix formatting and remove page numbers."""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=[prompt, text]
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

    google_api_key = os.environ.pop("GOOGLE_API_KEY", None)
    client = genai.Client(api_key=api_key)
    if google_api_key:
        os.environ["GOOGLE_API_KEY"] = google_api_key

    files_to_process = [
        ("Gemini", GEMINI_FILE, GEMINI_OUTPUT),
        ("Tesseract", TESSERACT_FILE, TESSERACT_OUTPUT),
        ("Mistral", MISTRAL_FILE, MISTRAL_OUTPUT),
    ]

    for source, input_file, output_file in files_to_process:
        if not input_file or not output_file:
            continue

        print(f"\n{'=' * 50}")
        print(f"Processing {source} output")
        print("=" * 50)

        print(f"Reading {input_file}...")

        try:
            with open(input_file, encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {input_file}")
            continue

        print(f"Read {len(content):,} characters")

        if PROCESS_PAGE_NUMBERS:
            print(f"Extracting pages: {PROCESS_PAGE_NUMBERS}")
            content = extract_pages(content, PROCESS_PAGE_NUMBERS)
            print(f"After page extraction: {len(content):,} characters")

        if PROCESS_LINE_RANGE:
            start_line, end_line = PROCESS_LINE_RANGE
            print(f"Extracting lines {start_line} to {end_line}")
            content = apply_line_range(content, start_line, end_line)
            print(f"After line range: {len(content):,} characters")
        if source == "Tesseract":
            format_prompt = TESSERACT_FORMAT_PROMPT
        else:
            format_prompt = GEMINI_FORMAT_PROMPT

        tokens = count_tokens(client, content, format_prompt)
        print(f"Input size: {tokens:,} tokens")

        print(f"\nFormatting {source} text with Gemini 2.5 Flash...")
        formatted_text = format_text(client, content, format_prompt)

        final_output_file = get_next_available_filename(output_file)
        if final_output_file != output_file:
            print(f"File exists, using: {final_output_file}")

        with open(final_output_file, "w", encoding="utf-8") as f:
            f.write(f"# {os.path.basename(final_output_file)}\n\n")
            f.write(formatted_text)

        print(f"Formatted text saved to: {final_output_file}")

    print("\n\nFormatting complete!")
    print("Output files:")
    print(f"- {GEMINI_OUTPUT}")
    print(f"- {TESSERACT_OUTPUT}")
    print(f"- {MISTRAL_OUTPUT}")


if __name__ == "__main__":
    main()
