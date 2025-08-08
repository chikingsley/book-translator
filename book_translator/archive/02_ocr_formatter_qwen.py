"""Format OCR output using Qwen 3 from Cerebras."""

import os
import re

from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv


def extract_pages_content(content: str, start_page: int = 4, end_page: int = 13) -> str:
    """Extract content from specified pages, removing page markers and separators."""
    lines = content.split('\n')
    result_lines: list[str] = []
    current_page = 0
    include_content = False

    for line in lines:
        # Check for page markers
        if line.startswith('# Page '):
            try:
                page_num = int(line.split('# Page ')[1].strip())
                current_page = page_num
                include_content = start_page <= current_page <= end_page
                continue  # Skip the page marker line
            except (IndexError, ValueError):
                continue

        # Skip separator lines
        if line.strip() == '---':
            continue

        # Include content if we're in the right page range
        if include_content:
            result_lines.append(line)

    return '\n'.join(result_lines)


def remove_think_tags(text: str) -> str:
    """Remove <think> </think> tags and their content from the text."""
    # Remove <think>...</think> blocks (case insensitive, multiline)
    pattern = r'<think>.*?</think>'
    cleaned_text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)

    # Clean up any extra whitespace left behind
    cleaned_text = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_text)
    cleaned_text = cleaned_text.strip()

    return cleaned_text


def post_process_markdown(text: str) -> str:
    """Apply final markdown formatting fixes."""
    # Convert various forms of *** to --- (horizontal rules)
    text = re.sub(r'^\s*\*\s*\*\s*\*\s*$', '---', text, flags=re.MULTILINE)

    # Ensure file ends with newline (MD047)
    if text and not text.endswith('\n'):
        text += '\n'

    return text


def format_text(client: Cerebras, text: str) -> str:
    """Use Qwen 3 to fix formatting and remove page numbers."""
    format_prompt = """You are formatting German text from OCR. Please reformat this text with proper paragraph structure and remove OCR artifacts.

Instructions:
1. Remove standalone page numbers (like "7" or "24" on their own lines)
2. Join lines that are part of the same paragraph - OCR often breaks paragraphs incorrectly
3. Keep proper paragraph breaks (single blank line between paragraphs)
4. Preserve section headers and special formatting like poem structure
5. Fix obvious line break issues from OCR
6. Remove hyphens that split words across lines (e.g., "nie-mand" should become "niemand")
7. Keep the content exactly the same, just fix formatting
8. Do not add any introduction or explanation - just provide the reformatted text
9. Preserve the original German text exactly, only fix formatting issues

Text to format:"""

    try:
        stream = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": format_prompt
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            model="qwen-3-235b-a22b",
            stream=True,
            max_completion_tokens=40000,
            temperature=0.1,  # Lower temperature for more consistent formatting
            top_p=0.95
        )

        result = ""
        for chunk in stream:
            # Type-safe access to streaming response
            try:
                choices = getattr(chunk, 'choices', None)
                if choices and len(choices) > 0:
                    delta = getattr(choices[0], 'delta', None)
                    if delta:
                        content = getattr(delta, 'content', None)
                        if content:
                            result += content
            except (AttributeError, IndexError, TypeError):
                # Skip malformed chunks
                continue

        # Post-process the result
        if result:
            result = remove_think_tags(result)
            result = post_process_markdown(result)

        return result if result else text

    except Exception as e:
        print(f"Error in formatting: {e}")
        return text


def main():
    """Format OCR text using Qwen 3."""
    load_dotenv()

    api_key = os.environ.get("CEREBRAS_API_KEY")
    if not api_key:
        print("Error: CEREBRAS_API_KEY not found")
        return

    client = Cerebras(api_key=api_key)

    gemini_file = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz_pages_4_13_gemini_pro_adaptive.md"

    print("Processing pages 4-13 with Qwen 3")
    print('=' * 50)

    print(f"Reading {gemini_file}...")

    try:
        with open(gemini_file, encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {gemini_file}")
        return

    print("Extracting pages 4-13 content (removing page markers)...")
    pages_content = extract_pages_content(content, 4, 13)

    print(f"Extracted content length: {len(pages_content)} characters")
    print("Formatting with Qwen 3...")
    formatted_text = format_text(client, pages_content)

    # Save formatted output
    output_file = "test-book-pdfs/pages_4_13_gemini_pro_adaptive_qwen_formatted.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Pages 4-13 - Gemini Pro Adaptive - Qwen 3 Formatted\n\n")
        f.write(formatted_text)

    print(f"\nFormatted text saved to: {output_file}")
    print("Processing complete!")


if __name__ == "__main__":
    main()
