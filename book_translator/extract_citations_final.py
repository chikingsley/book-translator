#!/usr/bin/env python3
"""Extract citation references from markdown files and create a clean list."""

import re
from pathlib import Path


def extract_citations(file_path: Path) -> list[tuple[int, str, str]]:
    """Extract all citation patterns from a markdown file.
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        List of tuples containing (reference_number, citation_text, citation_type)

    """
    with open(file_path, encoding='utf-8') as f:
        content = f.read()
    
    citations = []
    
    # Use a more sophisticated approach to handle nested parentheses
    # Find all [^#]( patterns and then manually balance parentheses
    
    # Find all citation starts
    citation_pattern = r'\[\^(\d+)\]\('
    
    for match in re.finditer(citation_pattern, content):
        ref_num = int(match.group(1))
        start_pos = match.end()
        
        # Find the matching closing parenthesis by counting parentheses
        paren_count = 1
        pos = start_pos
        
        while pos < len(content) and paren_count > 0:
            if content[pos] == '(':
                paren_count += 1
            elif content[pos] == ')':
                paren_count -= 1
            pos += 1
        
        # Extract the citation text
        citation_text = content[start_pos:pos-1].strip()
        
        # Determine type
        if citation_text.startswith('#TODO'):
            citation_text = citation_text[5:].strip()
            citation_type = 'TODO'
        else:
            citation_type = 'inline'
        
        citations.append((ref_num, citation_text, citation_type))
    
    # Sort by reference number
    citations.sort(key=lambda x: x[0])
    
    return citations


def main() -> None:
    """Extract citations from humancheck markdown file."""
    # Hardcoded paths
    input_file = Path("../test-book-pdfs/archive/Das Reich ohne Raum -- Bruno Goetz-humancheck-1.md")
    output_file = Path("../test-book-pdfs/archive/Das Reich ohne Raum -- Bruno Goetz-citations.md")
    
    if not input_file.exists():
        print(f"Error: Input file '{input_file}' not found")
        return
    
    # Extract citations
    citations = extract_citations(input_file)
    
    # Format output - just the citations
    output_lines = []
    for ref_num, citation_text, _ in citations:
        output_lines.append(f"[^{ref_num}]: {citation_text}")
    
    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"Extracted {len(citations)} citations from {input_file.name}")
    print(f"Citations saved to: {output_file}")


if __name__ == "__main__":
    main()
