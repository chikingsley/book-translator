#!/usr/bin/env python3
"""Quotation Mark Formatter using Gemini Flash.

This script fixes quotation marks in text files by using Gemini Flash to analyze
a source-of-truth file and correct quotation marks in target files to match
the proper German guillemets « » format.

Usage:
    python fix_quotes_with_gemini.py <source_file> <target_file> [--dry-run]

Example:
    python fix_quotes_with_gemini.py ../test-book-pdfs/citations/pages_1-13_final.md ../test-book-pdfs/gemini_formatted.md

Requirements:
    - GEMINI_API_KEY environment variable set (or in .env file)
    - google package installed

"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai


def setup_gemini() -> genai.Client:
    """Set up Gemini API with API key from environment."""
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables or .env file", file=sys.stderr)
        sys.exit(1)

    return genai.Client(api_key=api_key)


def create_correction_prompt(source_text: str, target_text: str) -> str:
    """Create a prompt for Gemini to fix quotation marks."""
    return f"""You are a text formatting expert specializing in German quotation marks.

TASK: Fix quotation marks in the TARGET TEXT to match the formatting style of the SOURCE TEXT.

RULES:
1. The SOURCE TEXT uses correct German quotation marks (guillemets): « »
2. Replace any incorrect quotation marks in TARGET TEXT with proper German guillemets « »
3. Only change quotation marks - do NOT modify any other text content
4. Preserve all formatting, spacing, line breaks, and structure exactly
5. Return ONLY the corrected TARGET TEXT with no additional commentary

SOURCE TEXT (showing correct quotation mark style):
{source_text[:2000]}...

TARGET TEXT (to be corrected):
{target_text}

CORRECTED TARGET TEXT:"""


def fix_quotes_with_gemini(client: genai.Client, source_text: str, target_text: str) -> str:
    """Use Gemini to fix quotation marks in target text."""
    prompt = create_correction_prompt(source_text, target_text)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=[prompt]
        )
        return response.text.strip() if hasattr(response, 'text') and response.text else ""
    except Exception as e:
        print(f"Error calling Gemini API: {e}", file=sys.stderr)
        sys.exit(1)


def show_differences(original: str, corrected: str) -> None:
    """Show a summary of changes made."""
    original_lines = original.split('\n')
    corrected_lines = corrected.split('\n')

    changes = 0
    for i, (orig_line, corr_line) in enumerate(zip(original_lines, corrected_lines, strict=False)):
        if orig_line != corr_line:
            changes += 1
            if changes <= 5:  # Show first 5 changes
                print(f"Line {i + 1}:")
                print(f"  Before: {orig_line[:100]}...")
                print(f"  After:  {corr_line[:100]}...")

    if changes > 5:
        print(f"... and {changes - 5} more changes")

    print(f"\nTotal lines changed: {changes}")


def main() -> None:
    """Process quotation mark corrections."""
    parser = argparse.ArgumentParser(description='Fix quotation marks using Gemini Flash')
    parser.add_argument('source_file', help='Source file with correct quotation marks')
    parser.add_argument('target_file', help='Target file to correct')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying them')
    parser.add_argument('--output', '-o', help='Output file (default: overwrite target)')

    args = parser.parse_args()

    source_path = Path(args.source_file)
    target_path = Path(args.target_file)

    if not source_path.exists():
        print(f"Error: Source file '{source_path}' not found", file=sys.stderr)
        sys.exit(1)

    if not target_path.exists():
        print(f"Error: Target file '{target_path}' not found", file=sys.stderr)
        sys.exit(1)

    # Read files
    try:
        with open(source_path, encoding='utf-8') as f:
            source_text = f.read()

        with open(target_path, encoding='utf-8') as f:
            target_text = f.read()
    except Exception as e:
        print(f"Error reading files: {e}", file=sys.stderr)
        sys.exit(1)

    print("Setting up Gemini Flash...")
    client = setup_gemini()

    print("Analyzing quotation marks with Gemini...")
    corrected_text = fix_quotes_with_gemini(client, source_text, target_text)

    # Check if any changes were made
    if corrected_text == target_text:
        print("No corrections needed!")
        return

    print("Changes found:")
    show_differences(target_text, corrected_text)

    if args.dry_run:
        print("\nDry run - no changes applied")
        print("\nFirst 500 characters of corrected text:")
        print(corrected_text[:500] + "...")
        return

    # Write output
    output_path = Path(args.output) if args.output else target_path

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(corrected_text)
        print(f"\nCorrected quotation marks written to: {output_path}")
    except Exception as e:
        print(f"Error writing file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
