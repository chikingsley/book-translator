import re
import sys
from typing import Dict, List, Tuple

def extract_all_footnotes(markdown_file: str) -> Tuple[Dict[int, str], List[int], List[int]]:
    """Extract all footnotes from a markdown file."""
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all footnotes with pattern ${ }^{n}$
    pattern = r'\$\{\s*\}\s*\^\{(\d+)\}'
    matches = re.findall(pattern, content)

    # Get unique footnote numbers
    unique_nums = sorted(set(int(n) for n in matches))
    print(f"Total footnote references found: {len(matches)}")
    print(f"Unique footnote numbers: {len(unique_nums)}")
    print(f"Numbers: {unique_nums}")

    # Now extract the actual footnote text
    # They can appear in two formats:
    # 1. [^0]: ${ }^{n}$ text...
    # 2. Just ${ }^{n}$ text... on its own line

    footnotes: Dict[int, str] = {}
    lines = content.split('\n')

    for i, line in enumerate(lines):
        # Check if line contains a footnote reference with LaTeX format
        match = re.match(r'^\[\^0\]:\s*\$\{\s*\}\s*\^\{(\d+)\}\s*(.+)$', line)
        if match:
            num = int(match.group(1))
            text = f"${{ }}^{{{num}}} {match.group(2)}"
            footnotes[num] = text
            
            # Check for multiple footnotes on the same line
            remaining_text = match.group(2)
            while True:
                multi_match = re.search(r'\$\{\s*\}\s*\^\{(\d+)\}\s*(.*)$', remaining_text)
                if multi_match:
                    extra_num = int(multi_match.group(1))
                    extra_text = f"${{ }}^{{{extra_num}}} {multi_match.group(2)}"
                    footnotes[extra_num] = extra_text
                    remaining_text = multi_match.group(2)
                else:
                    break
            continue
        
        # Check for standalone footnote (not [^0] format)
        match = re.match(r'^\$\{\s*\}\s*\^\{(\d+)\}\s*(.+)$', line)
        if match:
            num = int(match.group(1))
            text = line.strip()
            footnotes[num] = text
            continue
            
        # Check for simple indented format like "    ${ }^{5}$ text..."
        match = re.match(r'^\s+\$\{\s*\}\s*\^\{(\d+)\}\s*(.+)$', line)
        if match:
            num = int(match.group(1))
            text = line.strip()
            footnotes[num] = text

    print(f"\nExtracted footnotes: {len(footnotes)}")
    print("\nFootnotes found:")
    for num in sorted(footnotes.keys()):
        print(f"{num}: {footnotes[num][:80]}...")

    # Find missing footnotes
    missing: List[int] = []
    for i in range(1, max(unique_nums) + 1):
        if i not in footnotes:
            missing.append(i)

    if missing:
        print(f"\nMissing footnotes: {missing}")
        print(f"Total missing: {len(missing)}")
    
    # Final summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY:")
    print(f"{'='*60}")
    print(f"Total unique footnote numbers referenced in text: {len(unique_nums)}")
    print(f"Total footnote definitions found: {len(footnotes)}")
    print(f"Success rate: {len(footnotes)/len(unique_nums)*100:.1f}%")
    
    if len(missing) <= 10:
        print(f"\nFootnotes referenced but not defined: {missing}")
    else:
        print(f"\nFootnotes referenced but not defined: {missing[:10]}... and {len(missing)-10} more")
    
    return footnotes, unique_nums, missing


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_footnotes.py <markdown_file>")
        sys.exit(1)
    
    extract_all_footnotes(sys.argv[1])