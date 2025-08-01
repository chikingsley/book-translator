"""Build consensus from multiple OCR outputs using Gemini 2.5 Pro."""

import os

from dotenv import load_dotenv
from google import genai

# ============== CONFIGURATION ==============
MISTRAL_FILE = "test-book-pdfs/mistral_formatted_4-50.md"
GEMINI_FILE = "test-book-pdfs/gemini_formatted_4-50.md"
HUMANCHECK_FILE = "test-book-pdfs/humancheck_formatted_4-50.md"
OUTPUT_FILE = "test-book-pdfs/three_way_consensus_4-50.md"
# ==========================================


def count_tokens(client: genai.Client, *texts: str) -> int:
    """Count tokens for all input texts combined."""
    combined_text = "\n\n".join(texts)
    token_count = client.models.count_tokens(
        model="gemini-2.5-pro", contents=[combined_text]
    )
    return token_count.total_tokens or 0


def build_consensus(client: genai.Client, mistral_text: str, gemini_text: str, humancheck_text: str) -> str:
    """Use Pro to build consensus from three versions: Mistral, Gemini, and human-checked."""
    consensus_prompt = """
    Compare these three versions of the same German text and create a consensus version.
    
    Instructions:
    1. When all three versions agree exactly → use that text
    2. When two versions agree and one differs → use the majority version
    3. When all three have different versions → mark as: **disputed (Mistral: X / Gemini: Y / Human: Z)**
    4. When they have minor differences (punctuation, capitalization) → choose the most likely correct version
    5. If one version has text that's missing in others → mark as: **missing in [Mistral/Gemini/Human]: [text]**
    6. Pay special attention to:
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
                "\n\nHuman-checked version:\n---\n",
                humancheck_text,
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
    
    google_api_key = os.environ.pop("GOOGLE_API_KEY", None)
    client = genai.Client(api_key=api_key)
    if google_api_key:
        os.environ["GOOGLE_API_KEY"] = google_api_key
    
    mistral_file = MISTRAL_FILE
    gemini_file = GEMINI_FILE
    humancheck_file = HUMANCHECK_FILE
    
    print("Building consensus from three versions: Mistral, Gemini, and human-checked...")
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
    
    print(f"Reading human-checked version {humancheck_file}...")
    
    try:
        with open(humancheck_file, encoding='utf-8') as f:
            humancheck_content = f.read()
    except FileNotFoundError:
        print(f"Error: {humancheck_file} not found.")
        return
    
    mistral_lines = mistral_content.split('\n')
    gemini_lines = gemini_content.split('\n')
    
    mistral_start = 0
    for i, line in enumerate(mistral_lines):
        if line.startswith(f'# {os.path.basename(mistral_file)}'):
            mistral_start = i + 2  
            break
    
    gemini_start = 0
    for i, line in enumerate(gemini_lines):
        if line.startswith(f'# {os.path.basename(gemini_file)}'):
            gemini_start = i + 2 
            break
    
    mistral_text = '\n'.join(mistral_lines[mistral_start:])
    gemini_text = '\n'.join(gemini_lines[gemini_start:])
    humancheck_text = humancheck_content  
    
    tokens = count_tokens(client, mistral_text, gemini_text, humancheck_text)
    print(f"\nTotal input size: {tokens:,} tokens")
    
    print("\nBuilding consensus with Gemini 2.5 Pro...")
    print("This compares all three versions and marks disputes...")
    
    consensus_text = build_consensus(client, mistral_text, gemini_text, humancheck_text)
    
    output_file = OUTPUT_FILE
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# {os.path.basename(output_file)}\n\n")
        f.write("## Consensus built from Mistral, Gemini, and human-checked versions\n")
        f.write("## Disputes marked as: **disputed (Mistral: X / Gemini: Y / Human: Z)**\n")
        f.write("## Missing text marked as: **missing in [Mistral/Gemini/Human]: [text]**\n\n")
        f.write(consensus_text)
    
    print(f"\nConsensus saved to: {output_file}")
    print("\nCheck the output for:")
    print("- **disputed (...)** markings where versions disagree")
    print("- **missing in [...]** markings where content appears in only some versions")
    print("- Majority consensus where two versions agree")
    print(f"\nThis consensus compares all three versions for user review (Total tokens: {tokens:,}).")


if __name__ == "__main__":
    main()