"""Tests for chapter splitting behavior."""

from book_translator.chaptering import split_markdown_into_chapters
from book_translator.models import ChapteringConfig


def test_chapter_titles_strip_markdown_hashes() -> None:
    """Normalize heading titles regardless of heading depth."""
    content = "# One\nBody\n\n## Two\nBody\n\n### Three\nBody"
    chapters = split_markdown_into_chapters(content, ChapteringConfig())

    assert [chapter.title for chapter in chapters] == ["One", "Two", "Three"]


def test_chaptering_returns_single_document_without_headings() -> None:
    """Fallback to a single synthetic chapter when no headings exist."""
    content = "No heading text"
    chapters = split_markdown_into_chapters(content, ChapteringConfig())

    assert len(chapters) == 1
    assert chapters[0].chapter_id == "001"
