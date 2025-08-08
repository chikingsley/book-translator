#!/usr/bin/env python3
"""Move chapter files smaller than 200 bytes to a 'small' subfolder.
This helps identify chapters that are just section dividers or minimal content.
"""

import os
import shutil
from pathlib import Path


def get_file_size(file_path):
    """Get the size of a file in bytes."""
    return os.path.getsize(file_path)


def move_small_files(input_dir, size_threshold=200):
    """Move files smaller than threshold to a 'small' subfolder.

    Args:
        input_dir: Directory containing the chapter files
        size_threshold: Files smaller than this (in bytes) will be moved

    """
    input_path = Path(input_dir)
    small_dir = input_path / "small"

    # Create the small directory if it doesn't exist
    small_dir.mkdir(exist_ok=True)

    moved_files = []
    kept_files = []

    # Process all .md files in the input directory
    for file_path in sorted(input_path.glob("*.md")):
        file_size = get_file_size(file_path)

        if file_size < size_threshold:
            # Move to small folder
            dest_path = small_dir / file_path.name
            shutil.move(str(file_path), str(dest_path))
            moved_files.append((file_path.name, file_size))
            print(f"Moved: {file_path.name} ({file_size} bytes)")
        else:
            kept_files.append((file_path.name, file_size))
            print(f"Kept:  {file_path.name} ({file_size:,} bytes)")

    # Print summary
    print(f"\n{'=' * 60}")
    print("Summary:")
    print(f"  Files moved to 'small' folder: {len(moved_files)}")
    print(f"  Files kept in main folder: {len(kept_files)}")

    if moved_files:
        print(f"\nMoved files (< {size_threshold} bytes):")
        for filename, size in moved_files:
            print(f"  - {filename}: {size} bytes")

    print("\nAll files processed successfully!")
    print(f"Small files are now in: {small_dir}")


def main():
    # Directory containing the chapter files
    chapters_dir = "test-book-pdfs/chapters_literal"

    # Check if directory exists
    if not os.path.exists(chapters_dir):
        print(f"Error: Directory '{chapters_dir}' not found!")
        return

    print(f"Processing files in: {chapters_dir}")
    print("Moving files smaller than 200 bytes to 'small' subfolder...")
    print(f"{'=' * 60}\n")

    move_small_files(chapters_dir)


if __name__ == "__main__":
    main()
