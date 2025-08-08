#!/usr/bin/env python3
"""Extract citation references from markdown files and create a clean list."""

import re
import sys
from pathlib import Path


def extract_citations(file_path):
    """Extract all [^#](#TODO ...) citations from a markdown file."""
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    # Pattern to match [^#](#TODO ...) where # is a number
    # This captures the number and the content inside the parentheses
    pattern = r'\[\^(\d+)\]\(#TODO\s+([^)]+)\)'

    citations = []
    for match in re.finditer(pattern, content):
        ref_num = match.group(1)
        citation_text = match.group(2).strip()
        citations.append((int(ref_num), citation_text))

    # Sort by reference number
    citations.sort(key=lambda x: x[0])

    return citations


def remove_citations(file_path, output_path=None):
    """Remove all [^#](#TODO ...) citations from the markdown file."""
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    # Pattern to match [^#](#TODO ...) where # is a number
    pattern = r'\[\^\d+\]\(#TODO\s+[^)]+\)'

    # Remove all matches
    cleaned_content = re.sub(pattern, '', content)

    # Clean up any double spaces left behind
    cleaned_content = re.sub(r'  +', ' ', cleaned_content)

    # Clean up any spaces before punctuation
    cleaned_content = re.sub(r' +([.,;:!?])', r'\1', cleaned_content)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)

    return cleaned_content


def main():
    """Extract citations from markdown files."""
    if len(sys.argv) < 2:
        print("Usage: python extract_citations.py <markdown_file> [--remove] [--output <output_file>]")
        print("\nOptions:")
        print("  --remove    Remove citations from the text (default: just list them)")
        print("  --output    Specify output file for cleaned text (default: print to stdout)")
        sys.exit(1)

    file_path = sys.argv[1]
    remove_mode = '--remove' in sys.argv

    output_file = None
    if '--output' in sys.argv:
        output_idx = sys.argv.index('--output')
        if output_idx + 1 < len(sys.argv):
            output_file = sys.argv[output_idx + 1]

    if not Path(file_path).exists():
        print(f"Error: File '{file_path}' not found")
        sys.exit(1)

    # Extract citations
    citations = extract_citations(file_path)

    if not remove_mode:
        # Just list the citations
        print(f"Found {len(citations)} citations in {file_path}:\n")
        print("# Citations List\n")

        for ref_num, citation_text in citations:
            print(f"[^{ref_num}]: {citation_text}")

        # Also create a simple numbered list
        print("\n## Simple numbered list:\n")
        for i, (_ref_num, citation_text) in enumerate(citations, 1):
            print(f"{i}. {citation_text}")

    else:
        # Remove citations and save/print cleaned text
        cleaned_content = remove_citations(file_path, output_file)

        if output_file:
            print(f"Cleaned text saved to: {output_file}")
            print(f"Removed {len(citations)} citations")
        else:
            print(cleaned_content)

        # Also save the citations list
        citations_file = Path(file_path).stem + "_citations.md"
        with open(citations_file, 'w', encoding='utf-8') as f:
            f.write(f"# Citations from {Path(file_path).name}\n\n")
            f.write(f"Total citations: {len(citations)}\n\n")

            for ref_num, citation_text in citations:
                f.write(f"[^{ref_num}]: {citation_text}\n")

        print(f"\nCitations list saved to: {citations_file}")


if __name__ == "__main__":
    main()
