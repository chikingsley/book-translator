"""EPUB creation utility from markdown output."""

from __future__ import annotations

import argparse
from pathlib import Path

import pypandoc


def create_ebook(markdown_path: Path, output_path: Path) -> None:
    """Convert markdown into EPUB using pypandoc if available."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pypandoc.convert_file(
        str(markdown_path),
        to="epub",
        outputfile=str(output_path),
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for EPUB export."""
    parser = argparse.ArgumentParser(description="Create EPUB from markdown")
    parser.add_argument("input_markdown", type=Path, help="Path to markdown source")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output EPUB path (defaults to input filename with .epub)",
    )
    args = parser.parse_args(argv)

    output_path = args.output or args.input_markdown.with_suffix(".epub")
    create_ebook(args.input_markdown, output_path)
    print(f"EPUB created: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
