#!/usr/bin/env python3
"""Check and fix missing chapter titles in markdown files."""

from pathlib import Path


def fix_chapter_titles():
    """Check first line of each chapter and add # if missing."""
    chapters_dir = Path("test-book-pdfs/chapters_literal")

    if not chapters_dir.exists():
        print(f"Error: Directory {chapters_dir} not found")
        return

    fixed_count = 0

    for filepath in sorted(chapters_dir.glob("*.md")):
        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            print(f"Empty file: {filepath.name}")
            continue

        first_line = lines[0].strip()

        # Check if first line is short and missing #
        if len(first_line) < 20 and "#" not in first_line:
            print(f"Fixing {filepath.name}: '{first_line}' -> '# {first_line}'")

            # Add # to the beginning
            lines[0] = f"# {first_line}\n"

            # Write back
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(lines)

            fixed_count += 1
        elif "#" in first_line and first_line.count("#") > 1:
            # Multiple # symbols - reduce to just one
            # Remove all # and add just one at the beginning
            clean_title = first_line.replace("#", "").strip()
            print(f"Fixing {filepath.name}: Multiple # -> '# {clean_title}'")

            lines[0] = f"# {clean_title}\n"

            # Write back
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(lines)

            fixed_count += 1
        elif "#" not in first_line:
            # First line too long - create title from filename
            # Remove number prefix and .md extension
            filename = filepath.stem  # Gets filename without .md

            # Remove the number prefix (e.g., "017_")
            if "_" in filename:
                title = filename.split("_", 1)[1]
            else:
                title = filename

            # Replace - with :
            title = title.replace("-", ":")

            print(f"Adding title to {filepath.name}: '# {title}'")

            # Create new content with title
            new_content = [f"# {title}\n", "\n"] + lines

            # Write back
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(new_content)

            fixed_count += 1
        else:
            print(f"OK: {filepath.name}")

        # Check if file ends properly with exactly ONE newline
        needs_fix = False
        if lines:
            # Remove all trailing empty lines
            while len(lines) > 0 and lines[-1].strip() == "":
                lines.pop()
                needs_fix = True

            # Now ensure last line has exactly one newline character
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
                needs_fix = True

            # Don't add any extra empty lines - just the one newline at end of content

            if needs_fix:
                print(f"  Fixed ending of {filepath.name}")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                fixed_count += 1

    print(f"\nFixed {fixed_count} files")


if __name__ == "__main__":
    fix_chapter_titles()
