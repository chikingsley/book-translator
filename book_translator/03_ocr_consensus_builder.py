"""Build consensus from multiple OCR outputs using Gemini 2.5 Pro."""

import os

from dotenv import load_dotenv
from google import genai


def build_consensus(client: genai.Client, mistral_text: str, gemini_text: str) -> str:
    """Use Pro to build consensus from two OCR outputs."""
    consensus_prompt = """
    Compare these two OCR outputs of the same German text and create a consensus version.
    
    Instructions:
    1. When both versions agree exactly → use that text
    2. When they have minor differences (punctuation, capitalization) → choose the most likely correct version
    3. When they have significant differences → mark as: **disputed (Mistral: X / Gemini: Y)**
    4. If one version has text that's missing in the other → mark as: **missing in [Mistral/Gemini]: [text]**
    5. Pay special attention to:
       - German quotation marks (»« vs «» vs "")
       - Umlauts (ä, ö, ü)
       - Compound words (should they be joined or separated?)
       - Proper names and capitalization
    
    Output only the consensus text, with disputes clearly marked.
    Do not add any introduction or explanation.
    
    Mistral version:
    ---
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[
                consensus_prompt,
                mistral_text,
                "\n\nGemini version:\n---\n",
                gemini_text,
                "\n\nConsensus version:"
            ]
        )
        if response.text:
            return response.text
        return "Error: No consensus generated"
    except Exception as e:
        print(f"Error building consensus: {e}")
        return f"Error: {e!s}"


def main() -> None:
    """Build consensus from OCR outputs."""
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
    
    # Hardcoded input files
    mistral_file = "test-book-pdfs/pages_4-13_mistral_formatted.md"
    gemini_file = "test-book-pdfs/pages_4-13_gemini_formatted.md"
    
    print("Building consensus from OCR outputs...")
    print(f"Reading {mistral_file}...")
    
    try:
        with open(mistral_file, encoding='utf-8') as f:
            mistral_content = f.read()
    except FileNotFoundError:
        print(f"Error: {mistral_file} not found. Run ocr_formatter.py first.")
        return
    
    print(f"Reading {gemini_file}...")
    
    try:
        with open(gemini_file, encoding='utf-8') as f:
            gemini_content = f.read()
    except FileNotFoundError:
        print(f"Error: {gemini_file} not found. Run ocr_formatter.py first.")
        return
    
    # Extract just the content (skip the header line)
    mistral_lines = mistral_content.split('\n')
    gemini_lines = gemini_content.split('\n')
    
    # Find where content starts (after the # filename line and empty line)
    mistral_start = 0
    for i, line in enumerate(mistral_lines):
        if line.startswith('# pages_4-13_mistral_formatted.md'):
            mistral_start = i + 2  # Skip header and empty line
            break
    
    gemini_start = 0
    for i, line in enumerate(gemini_lines):
        if line.startswith('# pages_4-13_gemini_formatted.md'):
            gemini_start = i + 2  # Skip header and empty line
            break
    
    mistral_text = '\n'.join(mistral_lines[mistral_start:])
    gemini_text = '\n'.join(gemini_lines[gemini_start:])
    
    print("\nBuilding consensus with Gemini 2.5 Pro...")
    print("This compares both versions and marks disputes...")
    
    # Build consensus
    consensus_text = build_consensus(client, mistral_text, gemini_text)
    
    # Save result
    output_file = "test-book-pdfs/pages_4-13_consensus.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# pages_4-13_consensus.md\n\n")
        f.write("## Consensus built from Mistral and Gemini OCR outputs\n")
        f.write("## Disputes marked as: **disputed (Mistral: X / Gemini: Y)**\n\n")
        f.write(consensus_text)
    
    print(f"\nConsensus saved to: {output_file}")
    print("\nCheck the output for:")
    print("- **disputed (...)** markings where OCR engines disagree")
    print("- **missing in [...]** markings where content appears in only one version")
    print("\nThis consensus version is ready for semantic evaluation.")


if __name__ == "__main__":
    main()