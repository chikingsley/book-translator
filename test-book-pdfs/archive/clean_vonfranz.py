"""Clean up von Franz text - remove page numbers, headers, fix formatting."""

import re

def clean_text(input_path: str, output_path: str) -> None:
    """Clean up the von Franz extracted text."""
    with open(input_path, encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    prev_was_empty = False

    for line in lines:
        stripped = line.strip()

        # Skip page numbers (2-3 digit numbers alone on a line)
        if re.match(r'^\d{2,3}$', stripped):
            continue

        # Skip repeated headers
        if stripped in ['Marie-Louise von Franz', 'Problem of the Puer Aeternus']:
            continue

        # Handle empty lines - preserve paragraph breaks but not excessive gaps
        if not stripped:
            if not prev_was_empty:
                cleaned_lines.append('\n')
                prev_was_empty = True
            continue

        prev_was_empty = False

        # Mark lecture headers
        if re.match(r'^Lecture \d+$', stripped):
            cleaned_lines.append(f'\n---\n\n# {stripped}\n\n')
            continue

        cleaned_lines.append(stripped + '\n')

    # Join lines and fix paragraph formatting
    text = ''.join(cleaned_lines)

    # Fix broken sentences (line ending without period followed by lowercase)
    # This joins lines that were broken by page formatting
    text = re.sub(r'(\w)\n([a-z])', r'\1 \2', text)

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# The Problem of the Puer Aeternus\n')
        f.write('## Marie-Louise von Franz\n')
        f.write('### Lectures 9-12: Das Reich ohne Raum (The Kingdom Without Space)\n\n')
        f.write('---\n\n')
        f.write(text)

    print(f"Cleaned text saved to {output_path}")

    # Stats
    with open(output_path, encoding='utf-8') as f:
        content = f.read()
    line_count = content.count('\n')
    char_count = len(content)
    print(f"Lines: {line_count:,}")
    print(f"Characters: {char_count:,}")


if __name__ == '__main__':
    input_file = '/Users/chiejimofor/Documents/Github/book-translator/test-book-pdfs/von-franz-das-reich-analysis.txt'
    output_file = '/Users/chiejimofor/Documents/Github/book-translator/test-book-pdfs/von-franz-das-reich-clean.md'
    clean_text(input_file, output_file)
