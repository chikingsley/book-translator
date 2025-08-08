"""Build consensus from split chapter files using Gemini 2.0 Flash."""

import os
import re
import time
from pathlib import Path
from typing import Any

from alive_progress import alive_bar
from dotenv import load_dotenv
from google import genai

# ============== CONFIGURATION ==============
CHAPTERS_DIR = Path("test-book-pdfs/chapters_literal_human")
DISPUTES_FILE = Path("test-book-pdfs/consensus_disputes.md")
# ==========================================


def get_chapter_files() -> list[tuple[str, str]]:
    """Get list of unique chapters (without suffixes)."""
    all_files = sorted(CHAPTERS_DIR.glob("*.md"))

    chapters: dict[str, str] = {}
    for f in all_files:
        if f.stem.endswith(("-mistral", "-gemini")):
            continue
        chapters[f.stem] = f.name

    return sorted(chapters.items())


def read_chapter_versions(chapter_stem: str, chapter_name: str) -> dict[str, str]:
    """Read all three versions of a chapter."""
    versions: dict[str, str] = {}

    human_path = CHAPTERS_DIR / chapter_name
    if human_path.exists():
        with open(human_path, encoding="utf-8") as f:
            versions["human"] = f.read()

    mistral_name = chapter_name.replace(".md", "-mistral.md")
    mistral_path = CHAPTERS_DIR / mistral_name
    if mistral_path.exists():
        with open(mistral_path, encoding="utf-8") as f:
            content = f.read()
            if "[Chapter content not found in OCR]" not in content:
                versions["mistral"] = content

    gemini_name = chapter_name.replace(".md", "-gemini.md")
    gemini_path = CHAPTERS_DIR / gemini_name
    if gemini_path.exists():
        with open(gemini_path, encoding="utf-8") as f:
            content = f.read()
            if "[Chapter content not found in OCR]" not in content:
                versions["gemini"] = content

    return versions


def build_consensus(
    client: Any, versions: dict[str, str], chapter_title: str
) -> tuple[str | None, str | None]:
    """Mark all differences between versions using Gemini Flash."""
    if len(versions) == 1:
        source = next(iter(versions.keys()))
        return versions[source], f"Only {source} version available"

    # Always feed all three versions, even if some are missing
    prompt = f"""
Compare these three versions of the same German text chapter "{chapter_title}" and mark ALL differences.

Instructions:
1. When all three versions agree exactly → use that text
2. When two versions agree and one differs → mark as: **[DIFF-2v1: Majority="X" | Other(source)="Y"]**
3. When all three differ → mark as: **[DIFF-ALL: M="X" | G="Y" | H="Z"]**
4. Mark ALL differences, DO NOT CHOOSE.

IMPORTANT: DO NOT MAKE DECISIONS. Mark every single difference for human review.
Output the text with ALL differences marked inline.

MISTRAL version:
---
{versions.get("mistral", "[Not available]")}

GEMINI version:
---
{versions.get("gemini", "[Not available]")}

HUMAN version:
---
{versions.get("human", "[Not available]")}

Output with differences marked:"""

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt])
        if response.text:
            return response.text.strip(), None
        return None, "No response from Gemini"
    except Exception as e:
        return None, f"Error: {e!s}"


def extract_disputes(consensus_text: str) -> list[tuple[str, str, int]]:
    """Extract dispute/difference markers with context from consensus text.

    Returns list of tuples: (dispute_marker, context, line_number)
    """
    disputes: list[tuple[str, str, int]] = []
    patterns = [
        r"\*\*\[DIFF[^]]*\]\*\*",
        r"\[DIFF[^]]*\]",
    ]

    # Split text into lines for line number tracking
    lines = consensus_text.split("\n")

    # Combine all patterns into one regex
    combined_pattern = "|".join(f"({p})" for p in patterns)

    for line_num, line in enumerate(lines, 1):
        for match in re.finditer(combined_pattern, line):
            dispute_marker = match.group()

            # Get context: the current line plus surrounding text
            start_pos = max(0, match.start() - 100)
            end_pos = min(len(line), match.end() + 100)

            # If we're at line boundaries, include previous/next lines for context
            context_parts: list[str] = []

            # Add previous line context if at beginning of current line
            if match.start() < 50 and line_num > 1:
                prev_line = lines[line_num - 2]
                context_parts.append("..." + prev_line[-50:] if len(prev_line) > 50 else prev_line)

            # Add current line context
            if start_pos > 0:
                context_parts.append("..." + line[start_pos : match.start()])
            else:
                context_parts.append(line[start_pos : match.start()])

            context_parts.append(f"**{dispute_marker}**")

            if end_pos < len(line):
                context_parts.append(line[match.end() : end_pos] + "...")
            else:
                context_parts.append(line[match.end() : end_pos])

            # Add next line context if at end of current line
            if match.end() > len(line) - 50 and line_num < len(lines):
                next_line = lines[line_num]
                context_parts.append(next_line[:50] + "..." if len(next_line) > 50 else next_line)

            context = " ".join(context_parts).replace("  ", " ").strip()
            disputes.append((dispute_marker, context, line_num))

    return disputes


def main() -> None:
    """Build consensus for all chapters."""
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment")
        return

    google_api_key = os.environ.pop("GOOGLE_API_KEY", None)
    client = genai.Client(api_key=api_key)
    if google_api_key:
        os.environ["GOOGLE_API_KEY"] = google_api_key

    print("Building consensus from chapter files...")
    print(f"Input directory: {CHAPTERS_DIR}")

    chapters = get_chapter_files()
    print(f"Found {len(chapters)} chapters to process")

    all_disputes: list[tuple[str, list[tuple[str, str, int]]]] = []
    successful = 0
    failed = 0
    start_time = time.time()
    with open(DISPUTES_FILE, "w", encoding="utf-8") as f:
        f.write("# Consensus Building Disputes\n\n")
        f.write(f"Processing {len(chapters)} chapters\n\n")

    with alive_bar(len(chapters), title="Building Consensus") as bar:  # type: ignore[reportUnknownVariableType]
        for _i, (chapter_stem, chapter_name) in enumerate(chapters):
            chapter_title = chapter_stem.split("_", 1)[1] if "_" in chapter_stem else chapter_stem
            bar.text = f"Processing: {chapter_title}"

            versions = read_chapter_versions(chapter_stem, chapter_name)

            if not versions:
                print(f"\n⚠️  No versions found for {chapter_title}")
                failed += 1
                bar()
                continue

            consensus_text, error = build_consensus(client, versions, chapter_title)

            if error:
                print(f"\n❌ Failed {chapter_title}: {error}")
                failed += 1
                bar()
                continue

            chapter_disputes = extract_disputes(consensus_text) if consensus_text else []
            if chapter_disputes:
                all_disputes.append((chapter_title, chapter_disputes))
                with open(DISPUTES_FILE, "a", encoding="utf-8") as f:
                    f.write(f"\n## {chapter_title}\n")
                    f.write(f"Found {len(chapter_disputes)} disputes:\n\n")
                    for i, (dispute_marker, context, line_num) in enumerate(chapter_disputes, 1):
                        f.write(f"### Dispute {i} (Line ~{line_num})\n")
                        f.write(f"**Marker:** `{dispute_marker}`\n")
                        f.write(f"**Context:** {context}\n\n")

            successful += 1
            bar()

            time.sleep(0.5)

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("CONSENSUS BUILDING COMPLETE")
    print("=" * 60)
    print(f"✅ Successful: {successful}/{len(chapters)} chapters")
    if failed > 0:
        print(f"❌ Failed: {failed} chapters")
    print(f"⚠️  Disputes found: {sum(len(d) for _, d in all_disputes)} total")
    print(f"⏱️  Time elapsed: {elapsed:.1f} seconds")
    print(f"\n📁 Disputes log: {DISPUTES_FILE}")

    with open(DISPUTES_FILE, encoding="utf-8") as f:
        disputes_content = f.read()

    total_disputes = sum(len(d) for _, d in all_disputes)
    disputes_content = disputes_content.replace(
        f"Processing {len(chapters)} chapters",
        f"Processed {successful} chapters successfully, found {total_disputes} disputes",
    )

    with open(DISPUTES_FILE, "w", encoding="utf-8") as f:
        f.write(disputes_content)


if __name__ == "__main__":
    main()
