"""Chapter splitting utilities."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import ChapteringConfig


@dataclass(slots=True)
class Chapter:
    """A chapter unit in source or translated form."""

    chapter_id: str
    title: str
    content: str


def split_markdown_into_chapters(text: str, config: ChapteringConfig) -> list[Chapter]:
    """Split markdown text into chapters by heading pattern."""
    if not config.split_on_heading:
        return [Chapter(chapter_id="001", title="Document", content=text.strip())]

    heading_regex = re.compile(config.heading_pattern)
    matches = list(heading_regex.finditer(text))
    if not matches:
        return [Chapter(chapter_id="001", title="Document", content=text.strip())]

    chapters: list[Chapter] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()
        if not chunk:
            continue

        first_line = chunk.splitlines()[0].strip()
        title = re.sub(r"^#+\s*", "", first_line).strip()
        chapter_id = f"{len(chapters) + 1:03d}"
        chapters.append(Chapter(chapter_id=chapter_id, title=title, content=chunk))

    if chapters:
        return chapters

    return [Chapter(chapter_id="001", title="Document", content=text.strip())]
