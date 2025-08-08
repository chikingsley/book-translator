#!/usr/bin/env python3
"""Citation Replacement Script.

Replace citations in humancheck file with modernized versions (excluding citation 16).
"""

import re
from pathlib import Path


def load_modernized_citations(modernized_file):
    """Load modernized citations from the citations file."""
    citations = {}

    with open(modernized_file, encoding='utf-8') as f:
        content = f.read()

    # Find all citation blocks
    citation_pattern = r'## \[(\^?\d+)\]\s*\n\n\*\*Original:\*\* (.*?)\n\n\*\*Modernized:\*\* (.*?)(?=\n\n---|$)'
    matches = re.findall(citation_pattern, content, re.DOTALL)

    for citation_id, original, modernized in matches:
        # Clean up citation ID (remove ^ if present)
        clean_id = citation_id.lstrip('^')
        citations[clean_id] = {
            'original': original.strip(),
            'modernized': modernized.strip()
        }

    return citations


def replace_citations_in_text(text, citations, exclude_citation=None):
    """Replace citation footnotes in text with modernized versions."""

    def replace_citation(match):
        citation_num = match.group(1)

        # Skip citation 16 if excluded
        if exclude_citation and citation_num == str(exclude_citation):
            return match.group(0)  # Return unchanged

        if citation_num in citations:
            modernized = citations[citation_num]['modernized']
            return f'[^{citation_num}]({modernized})'
        else:
            # Return unchanged if no modernized version found
            return match.group(0)

    # Pattern to match footnote citations: [^N](text)
    citation_pattern = r'\[\^(\d+)\]\(([^)]+)\)'

    result = re.sub(citation_pattern, replace_citation, text)
    return result


def main():
    """Replace citations with modernized versions."""
    # File paths
    base_dir = Path(__file__).parent.parent
    modernized_file = base_dir / "test-book-pdfs" / "archive" / "Das Reich ohne Raum -- Bruno Goetz-modernized_citations.md"
    humancheck_file = base_dir / "test-book-pdfs" / "archive" / "Das Reich ohne Raum -- Bruno Goetz-humancheck-1.md"

    print("Loading modernized citations...")
    citations = load_modernized_citations(modernized_file)
    print(f"Loaded {len(citations)} modernized citations")

    print("Reading humancheck file...")
    with open(humancheck_file, encoding='utf-8') as f:
        content = f.read()

    print("Replacing citations (excluding citation 16)...")
    updated_content = replace_citations_in_text(content, citations, exclude_citation=16)

    # Count replacements made
    original_citations = len(re.findall(r'\[\^(\d+)\]\([^)]+\)', content))

    print(f"Found {original_citations} citations in original text")

    # Write updated content
    with open(humancheck_file, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    print(f"Successfully updated {humancheck_file}")
    print("Citation 16 was excluded from replacement as requested")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
