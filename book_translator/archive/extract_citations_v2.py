#!/usr/bin/env python3
"""Extract citation references from markdown files and create a clean list."""

import re
import sys
from pathlib import Path


def extract_citations(file_path):
    """Extract all citation patterns from a markdown file."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    citations = []
    
    # Pattern 1: [^#](#TODO ...) where # is a number
    pattern1 = r'\[\^(\d+)\]\(#TODO\s+([^)]+)\)'
    for match in re.finditer(pattern1, content):
        ref_num = match.group(1)
        citation_text = match.group(2).strip()
        citations.append((int(ref_num), citation_text, 'TODO'))
    
    # Pattern 2: [^#](text...) where # is a number (without #TODO)
    pattern2 = r'\[\^(\d+)\]\((?!#TODO)([^)]+)\)'
    for match in re.finditer(pattern2, content):
        ref_num = match.group(1)
        citation_text = match.group(2).strip()
        citations.append((int(ref_num), citation_text, 'inline'))
    
    # Sort by reference number
    citations.sort(key=lambda x: x[0])
    
    return citations


def remove_citations(file_path, output_path=None):
    """Remove all citation patterns from the markdown file."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to match both [^#](#TODO ...) and [^#](text...)
    pattern = r'\[\^\d+\]\([^)]+\)'
    
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
    if len(sys.argv) < 2:
        print("Usage: python extract_citations_v2.py <markdown_file> [--remove] [--output <output_file>]")
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
        
        # Group by type
        todo_citations = [(num, text) for num, text, ctype in citations if ctype == 'TODO']
        inline_citations = [(num, text) for num, text, ctype in citations if ctype == 'inline']
        
        if todo_citations:
            print("# TODO Citations\n")
            for ref_num, citation_text in todo_citations:
                print(f"[^{ref_num}]: {citation_text}")
        
        if inline_citations:
            print("\n# Inline Citations\n")
            for ref_num, citation_text in inline_citations:
                # Truncate long inline citations
                if len(citation_text) > 100:
                    citation_text = citation_text[:97] + "..."
                print(f"[^{ref_num}]: {citation_text}")
        
        # Also create a simple numbered list
        print("\n## All citations (numbered list):\n")
        for i, (ref_num, citation_text, ctype) in enumerate(citations, 1):
            type_label = f" [{ctype}]" if ctype == 'inline' else ""
            if len(citation_text) > 100:
                citation_text = citation_text[:97] + "..."
            print(f"{i}. [^{ref_num}]{type_label}: {citation_text}")
    
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
            
            # Group by type
            todo_citations = [(num, text) for num, text, ctype in citations if ctype == 'TODO']
            inline_citations = [(num, text) for num, text, ctype in citations if ctype == 'inline']
            
            if todo_citations:
                f.write("## TODO Citations\n\n")
                for ref_num, citation_text in todo_citations:
                    f.write(f"[^{ref_num}]: {citation_text}\n")
            
            if inline_citations:
                f.write("\n## Inline Citations\n\n")
                for ref_num, citation_text in inline_citations:
                    f.write(f"[^{ref_num}]: {citation_text}\n")
        
        print(f"\nCitations list saved to: {citations_file}")


if __name__ == "__main__":
    main()
