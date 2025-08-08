"""Evaluate OCR text for semantic sense using Gemini 2.5 Pro."""

import os

from dotenv import load_dotenv
from google import genai

# ============== CONFIGURATION ==============
INPUT_FILE = "test-book-pdfs/pages_4-26_consensus.md"
OUTPUT_FILE = "test-book-pdfs/pages_4-26_evaluated.md"
# ==========================================


def evaluate_text(client: genai.Client, text: str) -> str:
    """Use Pro to evaluate semantic sense and flag issues."""
    eval_prompt = """
    Evaluate this German text (consensus from two OCR outputs) for semantic sense and quality.

    Instructions:
    1. Read through the text carefully

    2. For text already marked with **disputed (...)**:
       - Add your recommendation in square brackets after the dispute
       - Example: **disputed (Mistral: Riesenbogen / Gemini: Regenbogen)** [Gemini likely correct - rainbow makes more sense]
       - Keep the ** ** marking unchanged

    3. For sentences with semantic/grammar issues NOT already marked as disputed:
       - Put single asterisks *like this* around problematic sentences
       - Add explanation in square brackets
       - Example: *Der Mann ging auf dem Tisch.* [Semantic error: should be "an den Tisch"]

    4. At the end of each major section (like after VORWORT ends, or after a poem), add:

       --- EVALUATION REPORT ---
       Confidence: HIGH/MEDIUM/LOW
       Disputed words resolved: [number and which ones seem correct]
       Semantic issues found: [number]
       Types of issues: [brief description]
       Overall assessment: [1-2 sentences]
       -------------------------

    5. Keep all original text and markings, just add evaluations

    Text to evaluate:
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[eval_prompt, text]
        )
        if response.text:
            return response.text
        return text
    except Exception as e:
        print(f"Error in evaluation: {e}")
        return text


def main():
    """Run semantic evaluation on OCR text."""
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

    # Read consensus text
    input_file = INPUT_FILE
    print(f"Reading {input_file}...")

    try:
        with open(input_file, encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {input_file}")
        print("Please run ocr_consensus_builder.py first to create the consensus file.")
        return

    # Skip the header lines
    lines = content.split('\n')
    # Find where actual content starts (after "## Disputes marked...")
    start_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("## Disputes marked"):
            start_idx = i + 2  # Skip this line and the empty line after
            break

    text_to_evaluate = '\n'.join(lines[start_idx:])

    print(f"Evaluating {len(text_to_evaluate)} characters with Gemini 2.5 Pro...")

    # Evaluate with Pro
    evaluated_text = evaluate_text(client, text_to_evaluate)

    # Save result
    output_file = OUTPUT_FILE
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# {os.path.basename(output_file)}\n\n")
        f.write("## Semantic Evaluation by Gemini 2.5 Pro\n\n")
        f.write("### Marking system:\n")
        f.write("- **disputed (...)** = OCR engine disagreements (unchanged from consensus)\n")
        f.write("- *text* = Semantic/grammar issues found by evaluator\n")
        f.write("- [text in brackets] = Evaluator's comments and recommendations\n")
        f.write("- Evaluation reports appear after each major section\n\n")
        f.write("---\n\n")
        f.write(evaluated_text)

    print(f"\nEvaluation saved to: {output_file}")
    print("\nCheck the output for:")
    print("- [Bracketed] suspicious sentences")
    print("- Confidence scores and evaluation reports after sections")


if __name__ == "__main__":
    main()
