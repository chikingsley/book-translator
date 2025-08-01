#!/usr/bin/env -S uv run python
"""Compare OCR quality across three versions: unformatted, formatted, and reference."""

import os

from dotenv import load_dotenv
from openai import OpenAI

# ============== CONFIGURATION ==============
UNFORMATTED_FILE = "test-book-pdfs/gemini_notformatted.md"
FORMATTED_FILE = "test-book-pdfs/gemini_formatted_3.md"
REFERENCE_FILE = "test-book-pdfs/citations/pages_1-13_final.md"
OUTPUT_FILE = "test-book-pdfs/three_way_quality_comparison.md"
# ==========================================


def get_three_way_evaluation(unformatted: str, formatted: str, reference: str) -> str:
    """Get LLM analysis comparing unformatted OCR, formatted version, and reference."""
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "Error: OPENROUTER_API_KEY environment variable not set"
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    prompt = f"""You are evaluating how well formatting prepares OCR text for consensus building. The goal is to make different OCR outputs structurally similar enough to compare side-by-side for building consensus.

**RAW OCR INPUT:**
{unformatted}

**FORMATTED VERSION:**
{formatted}

**TARGET REFERENCE:**
{reference}

Analyze how well the formatting supports consensus building:

## Consensus Readiness Assessment
**Structural normalization achieved:**
- Section boundaries and headings standardized
- Paragraph breaks and content flow normalized  
- Typography artifacts (page numbers, headers) removed
- Content blocks clearly separated and identifiable

**Consensus preparation score:** Rate 1-10 how ready this is for side-by-side comparison with other OCR outputs.

## Alignment Analysis
**How well does the formatted version match the target structure:**
- **Section organization**: Are major content blocks (TOC, chapters, poems) clearly delineated like the target?
- **Paragraph structure**: Does paragraph flow match the target for easy comparison?
- **Typography normalization**: Are quotation marks, spacing, special characters consistent with target style?
- **Content preservation**: Is all original content preserved without word-level changes?

## Consensus Building Optimization
**Priority improvements for better consensus preparation:**
- Structural alignment fixes needed to match target organization
- Typography standardization required for consistent comparison
- Content block separation improvements
- Format the recommendations as specific directives for the formatting process

**Focus on changes that would make this version more comparable to other formatted OCR outputs of the same text.**

## Consensus Building Assessment  
- **Structural alignment with target:** X/10
- **Readiness for consensus building:** X/10
- **Top 3 improvements for better consensus preparation:** List specific changes needed
- **Consensus building potential:** How well would this formatted version work in side-by-side comparison with other OCR engines?"""

    try:
        completion = client.chat.completions.create(
            model="openrouter/horizon-alpha",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content or "No content returned"
    except Exception as e:
        return f"Error calling OpenRouter API: {e!s}"


def main() -> None:
    """Run three-way quality comparison analysis."""
    # Handle path resolution for different execution contexts
    if not os.path.exists("test-book-pdfs"):
        # We're probably running from book_translator subdirectory
        base_path = ".."
    else:
        # We're running from project root
        base_path = "."
    
    unformatted_file = os.path.join(base_path, UNFORMATTED_FILE)
    formatted_file = os.path.join(base_path, FORMATTED_FILE)
    reference_file = os.path.join(base_path, REFERENCE_FILE)
    output_file = os.path.join(base_path, OUTPUT_FILE)
    
    print("Three-Way OCR Quality Comparison")
    print("=" * 80)
    print(f"Unformatted OCR: {unformatted_file}")
    print(f"Formatted version: {formatted_file}")
    print(f"Reference file: {reference_file}")
    print(f"Output file: {output_file}")
    
    # Check all files exist
    files_to_check = [
        (unformatted_file, "Unformatted OCR"),
        (formatted_file, "Formatted version"),
        (reference_file, "Reference file")
    ]
    
    for file_path, description in files_to_check:
        if not os.path.exists(file_path):
            print(f"Error: {description} not found at {file_path}")
            return
    
    print("\nReading files...")
    
    # Read all files
    try:
        with open(unformatted_file, encoding='utf-8') as f:
            unformatted = f.read()
        with open(formatted_file, encoding='utf-8') as f:
            formatted = f.read()
        with open(reference_file, encoding='utf-8') as f:
            reference = f.read()
    except Exception as e:
        print(f"Error reading files: {e}")
        return
    
    # Basic statistics
    print("\nFile Statistics:")
    print(f"  Unformatted: {len(unformatted)} chars, {len(unformatted.splitlines())} lines")
    print(f"  Formatted:   {len(formatted)} chars, {len(formatted.splitlines())} lines")
    print(f"  Reference:   {len(reference)} chars, {len(reference.splitlines())} lines")
    
    # Get LLM evaluation
    print("\nGetting three-way comparison analysis...")
    evaluation = get_three_way_evaluation(unformatted, formatted, reference)
    
    # Write results
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("# Three-Way OCR Quality Comparison\n\n")
        out.write(f"**Generated:** {os.popen('date').read().strip()}\n\n")
        out.write("**Files analyzed:**\n")
        out.write(f"- Unformatted OCR: `{UNFORMATTED_FILE}`\n")
        out.write(f"- Formatted version: `{FORMATTED_FILE}`\n")
        out.write(f"- Reference (gold standard): `{REFERENCE_FILE}`\n\n")
        
        out.write("## File Statistics\n\n")
        out.write("| Version | Characters | Lines | vs Reference |\n")
        out.write("|---------|------------|-------|--------------|\n")
        out.write(f"| Unformatted | {len(unformatted):,} | {len(unformatted.splitlines()):,} | {len(unformatted) - len(reference):+,} chars |\n")
        out.write(f"| Formatted | {len(formatted):,} | {len(formatted.splitlines()):,} | {len(formatted) - len(reference):+,} chars |\n")
        out.write(f"| Reference | {len(reference):,} | {len(reference.splitlines()):,} | baseline |\n\n")
        
        out.write("## Detailed Analysis\n\n")
        out.write(evaluation)
        out.write("\n\n---\n\n")
        out.write("*Analysis generated using OpenRouter Horizon Alpha model*\n")
    
    print(f"\n{'=' * 80}")
    print("THREE-WAY COMPARISON COMPLETE")
    print(f"{'=' * 80}")
    print(f"Results saved to: {output_file}")
    print("This analysis shows what OCR captured, what formatting improved, and what still needs work!")


if __name__ == "__main__":
    main()