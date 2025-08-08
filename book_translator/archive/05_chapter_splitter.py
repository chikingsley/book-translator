"""Split markdown document into individual chapter files."""

import re
from pathlib import Path

# ============== CONFIGURATION ==============
INPUT_FILE = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-humancheck-1.md"
OUTPUT_DIR = "test-book-pdfs/test-chapters"
# ==========================================


def detect_chapters(content: str) -> list[tuple[int, str, str]]:
    """Detect chapter boundaries in the markdown content.

    Returns:
        List of tuples: (line_number, chapter_title, chapter_level)

    """
    chapters: list[tuple[int, str, str]] = []
    lines = content.split('\n')

    chapter_patterns = [
        (r'^#{2,3}\s+(.*(KAPITEL|TEIL).*)', 'chapter'),
        (r'^#{2}\s+(VORWORT|IN MEMORIAM|AN FO)', 'frontmatter'),
    ]

    for i, line in enumerate(lines):
        for pattern, chapter_type in chapter_patterns:
            match = re.match(pattern, line)
            if match:
                title = re.sub(r'^#{2,3}\s+', '', line).strip()
                chapters.append((i, title, chapter_type))
                break

    return chapters


def extract_chapter_content(content: str, chapters: list[tuple[int, str, str]],
                           chapter_index: int) -> str:
    """Extract content for a specific chapter.

    Args:
        content: Full document content
        chapters: List of detected chapters
        chapter_index: Index of chapter to extract

    Returns:
        Chapter content as string

    """
    lines = content.split('\n')
    start_line = chapters[chapter_index][0]

    if chapter_index < len(chapters) - 1:
        end_line = chapters[chapter_index + 1][0]
    else:
        end_line = len(lines)

    chapter_lines = lines[start_line:end_line]

    while chapter_lines and not chapter_lines[-1].strip():
        chapter_lines.pop()

    return '\n'.join(chapter_lines)


def split_chapters(input_file: str, output_dir: str):
    """Split a markdown document into individual chapter files.

    Args:
        input_file: Path to input markdown file
        output_dir: Directory to save chapter files

    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with open(input_file, encoding='utf-8') as f:
        content = f.read()

    chapters = detect_chapters(content)

    if not chapters:
        print("No chapters detected in the document!")
        return

    print(f"Detected {len(chapters)} chapters/sections:")
    for i, (line_num, title, chapter_type) in enumerate(chapters):
        print(f"  {i + 1}. Line {line_num}: {title} ({chapter_type})")

    for i, (_line_num, title, _chapter_type) in enumerate(chapters):
        print(f"\nProcessing chapter {i + 1}/{len(chapters)}: {title}")

        chapter_content = extract_chapter_content(content, chapters, i)

        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title).lower()[:100]
        filename = f"{i + 1:02d}_{safe_title}.md"
        filepath = output_path / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(chapter_content)

        print(f"  Saved to: {filepath}")

    index_content = "# Das Reich ohne Raum - Chapter Index\n\n"
    index_content += "## Chapters\n\n"

    for i, (_, title, _chapter_type) in enumerate(chapters):
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title).lower()[:100]
        filename = f"{i + 1:02d}_{safe_title}.md"
        index_content += f"- [{title}]({filename})\n"

    index_path = output_path / "00_index.md"
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(index_content)

    print(f"\nIndex saved to: {index_path}")
    print(f"\nSuccessfully split {len(chapters)} chapters into {output_dir}")


def main():
    """Run the chapter splitter."""
    split_chapters(INPUT_FILE, OUTPUT_DIR)


if __name__ == "__main__":
    main()
