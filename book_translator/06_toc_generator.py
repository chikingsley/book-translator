"""Generate TOC and add proper spacing around headings."""

import os
import re
from pathlib import Path


def add_heading_spacing(text: str) -> str:
    """Add proper spacing around headings."""
    lines = text.split('\n')
    result = []
    
    for i, line in enumerate(lines):
        # Check if current line is a heading
        if line.strip().startswith('#'):
            # Add blank line before heading (if not already there and not first line)
            if i > 0 and lines[i-1].strip() != '' and result and result[-1] != '':
                result.append('')
            
            result.append(line)
            
            # Add blank line after heading (if not already there and not last line)
            if i < len(lines) - 1 and lines[i+1].strip() != '':
                result.append('')
        else:
            result.append(line)
    
    return '\n'.join(result)


def convert_h1_to_h2(text: str) -> str:
    """Convert all H1 headings to H2 headings."""
    lines = text.split('\n')
    result = []
    
    for line in lines:
        if line.strip().startswith('#') and not line.strip().startswith('##'):
            # Convert H1 to H2
            result.append('#' + line)
        else:
            result.append(line)
    
    return '\n'.join(result)


def generate_toc(text: str, filename: str) -> str:
    """Generate table of contents from headings."""
    lines = text.split('\n')
    toc_lines = []
    
    # Add filename as top-level TOC entry  
    filename_anchor = filename.lower().replace(' ', '-').replace('.', '')
    toc_lines.append(f"- [{filename}](#{filename_anchor})")
    
    for line in lines:
        if line.strip().startswith('#'):
            # Count heading level
            level = len(line) - len(line.lstrip('#'))
            title = line.lstrip('#').strip()
            
            # Include all headings (don't skip any)
            # Create anchor link - preserve German characters
            anchor = title.lower().replace(' ', '-').replace(':', '').replace('«', '').replace('»', '')
            anchor = re.sub(r'[^a-z0-9\-äöüß]', '', anchor)
            
            # Create TOC entry with proper indentation (everything nested under filename)
            # Level 1 and 2 get 2 spaces, level 3+ get 4 spaces
            if level <= 2:
                indent = '  '  # 2 spaces for level 1 and 2
            else:
                indent = '    '  # 4 spaces for level 3+
            toc_lines.append(f"{indent}- [{title}](#{anchor})")
    
    return '\n'.join(toc_lines)


def process_file(input_file: str, output_file: str) -> None:
    """Process a single file to add TOC and spacing."""
    print(f"Processing {input_file}...")
    
    # Read input file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Convert all H1s to H2s
    content = convert_h1_to_h2(content)
    
    # Add proper spacing around headings
    formatted_content = add_heading_spacing(content)
    
    # Get filename for title
    filename = os.path.basename(output_file)
    
    # Generate TOC
    toc_content = generate_toc(formatted_content, filename)
    
    # Write output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# {filename}\n\n")
        f.write("## Table of Contents\n\n")
        f.write(toc_content)
        f.write("\n\n")
        f.write(formatted_content)
        f.write("\n")  # Add trailing newline
    
    print(f"Saved to {output_file}")


def main() -> None:
    """Process all test files."""
    test_files = [
        ("test-toc/test1.md", "test-toc/test1_formatted.md"),
        ("test-toc/test2.md", "test-toc/test2_formatted.md"),
        ("test-toc/test3.md", "test-toc/test3_formatted.md"),
        ("test-toc/test4.md", "test-toc/test4_formatted.md"),
    ]
    
    for input_file, output_file in test_files:
        try:
            process_file(input_file, output_file)
        except FileNotFoundError:
            print(f"Error: File not found: {input_file}")
        except Exception as e:
            print(f"Error processing {input_file}: {e}")
    
    print("\nAll files processed!")
    print("Check the *_formatted.md files in test-toc/ directory")


if __name__ == "__main__":
    main()