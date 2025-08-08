#!/usr/bin/env python3
"""E-book generator for translated books.

Creates EPUB/MOBI files from translated markdown.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pypandoc


class EbookGenerator:
    """Generator for creating e-books from translated content."""

    def __init__(self, output_dir: str = "output"):
        """Initialize the e-book generator with output directory."""
        self.output_dir = Path(output_dir)
        self.toc_file = self.output_dir / "table_of_contents.json"
        self.metadata: dict[str, Any] = {}

    def load_metadata(self) -> bool:
        """Load book metadata from TOC file."""
        if not self.toc_file.exists():
            print("❌ No table_of_contents.json found. Run translation first.")
            return False

        with open(self.toc_file, encoding="utf-8") as f:
            self.metadata = json.load(f)
        return True

    def create_metadata_yaml(self) -> Path:
        """Create pandoc metadata file with proper formatting."""
        metadata_file = self.output_dir / "ebook_metadata.yaml"

        # Escape special characters in YAML
        def escape_yaml(text: str) -> str:
            if not text:
                return ""
            # Escape quotes and special chars
            text = text.replace('"', '\\"').replace("'", "''")
            # Wrap in quotes if contains special chars
            if any(c in text for c in ":#@|>-"):
                text = f'"{text}"'
            return text

        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"title: {escape_yaml(self.metadata.get('book_title', 'Untitled'))}\n")
            f.write(f"author: {escape_yaml(self.metadata.get('author', 'Unknown'))}\n")

            # Add optional metadata if available
            if self.metadata.get('publisher'):
                f.write(f"publisher: {escape_yaml(self.metadata['publisher'])}\n")
            if self.metadata.get('publication_year'):
                f.write(f"date: {self.metadata['publication_year']}\n")
            if self.metadata.get('isbn'):
                f.write("identifier:\n")
                f.write("- scheme: ISBN\n")
                f.write(f"  text: {self.metadata['isbn']}\n")

            # E-book specific metadata
            f.write("lang: en\n")  # Target language
            f.write("cover-image: cover.png\n")  # If you have a cover
            f.write("---\n")

        return metadata_file

    def prepare_content(self) -> Path:
        """Prepare combined markdown with proper structure."""
        print("📝 Preparing content...")

        # Check if we have the combined file
        combined_file = self.output_dir / "full_translation.md"
        if combined_file.exists():
            return combined_file

        # Otherwise, combine chapter files
        print("🔨 Building combined markdown from chapters...")
        combined_content: list[str] = []

        # Add title and front matter
        combined_content.append(f"# {self.metadata.get('book_title', 'Book')}\n")
        combined_content.append(f"*By {self.metadata.get('author', 'Unknown')}*\n\n")
        combined_content.append("---\n\n")

        # Add chapters in order
        chapters = sorted(self.metadata.get('chapters', []), key=lambda x: x['number'])
        for chapter in chapters:
            chapter_dir = self.output_dir / f"chapter_{chapter['number']:02d}"
            translation_file = chapter_dir / "translation.md"

            if translation_file.exists():
                with open(translation_file, encoding="utf-8") as f:
                    content = f.read()

                # Ensure chapter has proper heading
                if not content.startswith("#"):
                    content = f"## Chapter {chapter['number']}: {chapter['title']}\n\n{content}"

                combined_content.append(content)
                combined_content.append("\n\n---\n\n")
            else:
                print(f"⚠️  Missing translation for chapter {chapter['number']}")

        # Write combined file
        with open(combined_file, "w", encoding="utf-8") as f:
            f.write("\n".join(combined_content))

        return combined_file

    def generate_epub(self, custom_css: str | None = None) -> Path | None:
        """Generate EPUB with pandoc."""
        print("📚 Generating EPUB...")

        # Prepare files
        metadata_file = self.create_metadata_yaml()
        content_file = self.prepare_content()

        # Output filename
        safe_title = "".join(c for c in self.metadata.get('book_title', 'book')
                             if c.isalnum() or c in ' -_').strip()
        epub_file = self.output_dir / f"{safe_title}.epub"

        # Build extra args for pandoc
        extra_args = [
            f"--metadata-file={metadata_file}",
            "--toc",
            "--toc-depth=2",
            "--epub-chapter-level=2"
        ]

        # Add custom CSS if provided
        if custom_css and Path(custom_css).exists():
            extra_args.extend(["--css", str(custom_css)])

        try:
            # Convert markdown to EPUB using pypandoc
            pypandoc.convert_file(  # type: ignore[reportUnknownMemberType]
                str(content_file),
                'epub',
                outputfile=str(epub_file),
                extra_args=extra_args
            )
            print(f"✅ EPUB created: {epub_file}")
            return epub_file
        except Exception as e:
            print(f"❌ EPUB generation failed: {e}")
            return None

    def generate_kindle(self, epub_path: Path | None = None) -> Path | None:
        """Convert EPUB to Kindle format (AZW3/MOBI)."""
        print("📖 Generating Kindle format...")

        if not epub_path:
            epub_path = self.generate_epub()
            if not epub_path:
                return None

        # Output file
        kindle_file = epub_path.with_suffix('.azw3')

        # Use calibre's ebook-convert
        cmd = [
            "ebook-convert",
            str(epub_path),
            str(kindle_file),
            "--enable-heuristics"
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            print(f"✅ Kindle file created: {kindle_file}")
            return kindle_file
        except subprocess.CalledProcessError as e:
            print(f"❌ Kindle conversion failed: {e}")
            return None
        except FileNotFoundError:
            print("❌ ebook-convert not found.")
            return None

    def generate_all_formats(self) -> dict[str, Path]:
        """Generate all supported e-book formats."""
        results: dict[str, Path] = {}

        # Generate EPUB first (base format)
        epub_path = self.generate_epub()
        if epub_path:
            results['epub'] = epub_path

            # Generate Kindle from EPUB
            kindle_path = self.generate_kindle(epub_path)
            if kindle_path:
                results['kindle'] = kindle_path

        return results

    def create_custom_css(self) -> Path:
        """Create a custom CSS file for better e-book styling."""
        css_file = self.output_dir / "ebook_style.css"

        css_content = """
/* Custom e-book styling */
body {
    font-family: Georgia, serif;
    line-height: 1.6;
    text-align: justify;
}

h1, h2, h3 {
    font-family: Helvetica, Arial, sans-serif;
    text-align: left;
}

h1 {
    font-size: 2em;
    margin-top: 2em;
    margin-bottom: 1em;
}

h2 {
    font-size: 1.5em;
    margin-top: 1.5em;
    margin-bottom: 0.8em;
}

p {
    text-indent: 1.5em;
    margin-top: 0;
    margin-bottom: 0.5em;
}

/* First paragraph of chapter - no indent */
h1 + p, h2 + p, hr + p {
    text-indent: 0;
}

/* Page breaks */
h1, h2 {
    page-break-before: always;
}

/* Horizontal rules */
hr {
    margin: 2em 0;
    border: none;
    text-align: center;
}

hr:after {
    content: "* * *";
    font-size: 1.2em;
}
"""

        with open(css_file, "w", encoding="utf-8") as f:
            f.write(css_content)

        return css_file


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(description="Generate e-books from translated content")
    parser.add_argument("--output-dir", default="output", help="Output directory (default: output)")
    parser.add_argument("--format", choices=["epub", "kindle", "all"], default="epub",
                        help="Output format (default: epub)")
    parser.add_argument("--custom-css", help="Path to custom CSS file")

    args = parser.parse_args()

    # Initialize generator
    generator = EbookGenerator(args.output_dir)

    # Load metadata
    if not generator.load_metadata():
        return 1

    print(f"📖 Generating e-book for: {generator.metadata.get('book_title', 'Unknown')}")

    # Create custom CSS if not provided
    if not args.custom_css:
        args.custom_css = str(generator.create_custom_css())

    # Generate requested format
    if args.format == "epub":
        generator.generate_epub(args.custom_css)
    elif args.format == "kindle":
        generator.generate_kindle()
    elif args.format == "all":
        results = generator.generate_all_formats()
        print(f"\n✅ Generated {len(results)} formats:")
        for fmt, path in results.items():
            print(f"  - {fmt}: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
