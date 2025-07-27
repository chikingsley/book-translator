"""Format text content using proper TOC structure with Gemini 2.5 Flash."""

import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai

# ============== CONFIGURATION ==============
TOC_FILE = "test-book-pdfs/toc.json"
CONSENSUS_FILE = "test-book-pdfs/pages_4-26_consensus.md"
OUTPUT_FILE = "test-book-pdfs/pages_4-26_toc_formatted.md"
# ==========================================


def create_toc_structure_prompt(toc_data: list[dict[str, Any]]) -> str:
    """Create the target heading structure from TOC data."""
    toc_template: list[str] = []
    for item in toc_data:
        level_marker = "#" * (int(item["level"]) + 1)  # Add 1 to shift down
        toc_template.append(f'{level_marker} {item["title"]!s}')
    
    return "\n".join(toc_template)


def format_text(client: genai.Client, content: str, toc_data: list[dict[str, Any]]) -> str:
    """Use Flash to fix heading structure according to TOC."""
    target_structure = create_toc_structure_prompt(toc_data)
    
    format_prompt = f"""
Reformat this text to match the EXACT heading structure below.

TARGET HEADING STRUCTURE:
{target_structure}

INSTRUCTIONS:
1. Replace all existing headings with the exact titles and levels shown above
2. Combine split headings (e.g., "ERSTER TEIL" + "DIE BOTSCHAFT" → "## Erster Teil: DIE BOTSCHAFT")
3. Keep ALL content text unchanged and in the EXACT SAME ORDER
4. Do NOT rearrange, move, or reorganize any content sections
5. Remove any auto-generated table of contents sections
6. Preserve all paragraph breaks and formatting within content
7. Only change heading levels and titles - nothing else
8. Do not add any introduction - just provide the reformatted text

Text to format:
"""
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[format_prompt, content]
        )
        if response.text:
            return response.text
        return content
    except Exception as e:
        print(f"Error in TOC formatting: {e}")
        return content


def main() -> None:
    """Format text with proper TOC structure."""
    load_dotenv()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found")
        return
    
    # Setup client
    google_api_key = os.environ.pop("GOOGLE_API_KEY", None)
    client = genai.Client(api_key=api_key)
    if google_api_key:
        os.environ["GOOGLE_API_KEY"] = google_api_key
    
    print("Loading TOC structure...")
    try:
        with open(TOC_FILE, encoding='utf-8') as f:
            toc_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: TOC file not found: {TOC_FILE}")
        return
    
    print("Loading consensus text...")
    try:
        with open(CONSENSUS_FILE, encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: Consensus file not found: {CONSENSUS_FILE}")
        return
    
    print(f"Read {len(content)} characters")
    print(f"TOC has {len(toc_data)} entries")
    
    print("\nFormatting text with proper TOC structure using Gemini 2.5 Flash...")
    formatted_text = format_text(client, content, toc_data)
    
    # Save result
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# {os.path.basename(OUTPUT_FILE)}\n\n")  # Single top heading
        f.write(formatted_text)
    
    print(f"TOC-formatted content saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()