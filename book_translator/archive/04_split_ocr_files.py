"""Split Gemini and Mistral OCR files to match human-checked chapter structure."""

import re
from pathlib import Path

# ============== CONFIGURATION ==============
MISTRAL_FILE = Path("test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-mistral.md")
GEMINI_FILE = Path("test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-gemini.md")
HUMAN_CHAPTERS_DIR = Path("test-book-pdfs/chapters_literal_human")
OVERWRITE_EXISTING = True  # Set to False to skip existing files
# ==========================================


def get_human_chapter_files():
    """Get list of human chapter files in order (excluding already split files)."""
    files = sorted(HUMAN_CHAPTERS_DIR.glob("*.md"))
    # Filter out files that already have -mistral or -gemini suffix
    files = [f for f in files if not f.stem.endswith(("-mistral", "-gemini"))]
    return [(f.stem, f.name) for f in files]


def extract_chapter_title(filename):
    """Extract the chapter title from filename (after the number)."""
    # Remove the number prefix (e.g., "009_")
    parts = filename.split("_", 1)
    if len(parts) > 1:
        # Remove .md extension and return the title part
        return parts[1].replace(".md", "")
    return filename.replace(".md", "")


def create_chapter_patterns(chapter_title):
    """Create search patterns for a chapter title."""
    patterns = []
    clean_title = chapter_title.replace("- ", ": ")

    # Handle special cases
    if "KOMMENTAR" in clean_title:
        # Commentary sections - match the specific commentary pattern
        if "Einführung" in clean_title:
            patterns.append(r"#{1,2}\s*KOMMENTAR\s*[:\-\s]*Einführung")
            patterns.append(r"KOMMENTAR\s*[:\-\s]*Einführung")
            # Mistral format: # KOMMENTAR then ## Einführung (with typo Einfübrung)
            patterns.append(r"#\s*KOMMENTAR\s*\n+\s*#{1,2}\s*Einf[üu]h?rung")
            patterns.append(r"#\s*KOMMENTAR\s*\n+\s*#{1,2}\s*Einfübrung")
        elif "Das erste Kapitel" in clean_title:
            patterns.append(r"#{1,2}\s*KOMMENTAR\s*[:\-\s]*Das erste Kapitel")
            patterns.append(r"KOMMENTAR\s*[:\-\s]*Das erste Kapitel")
        elif "Das zweite Kapitel" in clean_title:
            patterns.append(r"#{1,2}\s*KOMMENTAR\s*[:\-\s]*Das zweite Kapitel")
            patterns.append(r"KOMMENTAR\s*[:\-\s]*Das zweite Kapitel")
            # Mistral format: # KOMMENTAR then ## Das zweite Kapitel
            patterns.append(r"#\s*KOMMENTAR\s*\n+\s*#{1,2}\s*Das zweite Kapitel")
        elif "Das vierte Kapitel" in clean_title:
            patterns.append(r"#{1,2}\s*KOMMENTAR\s*[:\-\s]*Das vierte Kapitel")
            patterns.append(r"KOMMENTAR\s*[:\-\s]*Das vierte Kapitel")
            # Mistral format
            patterns.append(r"#\s*KOMMENTAR\s*\n+\s*#{1,2}\s*Das vierte Kapitel")
        elif "Das fünfte Kapitel" in clean_title:
            patterns.append(r"#{1,2}\s*KOMMENTAR\s*[:\-\s]*Das fünfte Kapitel")
            patterns.append(r"KOMMENTAR\s*[:\-\s]*Das fünfte Kapitel")
            # Mistral format
            patterns.append(r"#\s*KOMMENTAR\s*\n+\s*#{1,2}\s*Das fünfte Kapitel")
        elif "Das siebte und achte Kapitel" in clean_title:
            patterns.append(r"#{1,2}\s*KOMMENTAR\s*[:\-\s]*Das siebte und achte Kapitel")
            patterns.append(r"KOMMENTAR\s*[:\-\s]*Das siebte und achte Kapitel")
            # Mistral format
            patterns.append(r"#\s*KOMMENTAR\s*\n+\s*#{1,2}\s*Das siebte und achte Kapitel")
        elif "Das neunte Kapitel" in clean_title:
            patterns.append(r"#{1,2}\s*KOMMENTAR\s*[:\-\s]*Das neunte Kapitel")
            patterns.append(r"KOMMENTAR\s*[:\-\s]*Das neunte Kapitel")
            # Mistral format
            patterns.append(r"#\s*KOMMENTAR\s*\n+\s*#{1,2}\s*Das neunte Kapitel")
        elif "Das zebnte Kapitel" in clean_title or "Das zehnte Kapitel" in clean_title:
            patterns.append(r"#{1,2}\s*KOMMENTAR\s*[:\-\s]*Das ze[bh]nte Kapitel")
            patterns.append(r"KOMMENTAR\s*[:\-\s]*Das ze[bh]nte Kapitel")
            # Mistral format
            patterns.append(r"#\s*KOMMENTAR\s*\n+\s*#{1,2}\s*Das ze[bh]nte Kapitel")
        elif "Der Dritte Teil" in clean_title:
            patterns.append(r"#{1,2}\s*KOMMENTAR\s*[:\-\s]*Der Dritte Teil")
            patterns.append(r"KOMMENTAR\s*[:\-\s]*Der Dritte Teil")
            # Mistral format
            patterns.append(r"#\s*KOMMENTAR\s*\n+\s*#{1,2}\s*Der Dritte Teil")
        elif "Der Vierte Teil" in clean_title:
            patterns.append(r"#{1,2}\s*KOMMENTAR\s*[:\-\s]*Der Vierte Teil")
            patterns.append(r"KOMMENTAR\s*[:\-\s]*Der Vierte Teil")
            # Mistral format
            patterns.append(r"#\s*KOMMENTAR\s*\n+\s*#{1,2}\s*Der Vierte Teil")
        elif "Das letzte Kapitel" in clean_title:
            patterns.append(r"#{1,2}\s*KOMMENTAR\s*[:\-\s]*Das letzte Kapitel")
            patterns.append(r"KOMMENTAR\s*[:\-\s]*Das letzte Kapitel")
            # Mistral format
            patterns.append(r"#\s*KOMMENTAR\s*\n+\s*#{1,2}\s*Das letzte Kapitel")
    elif "Das erste Kapitel" in clean_title and "«Schimmelberg»" in clean_title:
        patterns.append(r"#{1,2}\s*Das erste Kapitel\s*[:\-\s]*[«»„" "]Schimmelberg")
        patterns.append(r"Das erste Kapitel\s*[:\-\s]*[«»„" "]Schimmelberg")
    elif "Das siebzebnte Kapitel" in clean_title or "Das siebzehnte Kapitel" in clean_title:
        # Handle typo in original: "siebzebnte" vs "siebzehnte" and "Wiederkebr" vs "Wiederkehr"
        patterns.append(r"#{1,2}\s*Das siebze[bh]nte Kapitel\s*[:\-\s]*[«»„""]Die Wiederkeh?r")
        patterns.append(r"Das siebze[bh]nte Kapitel\s*[:\-\s]*[«»„""]Die Wiederkeh?r")
        # Also match with typo "Wiederkebr"
        patterns.append(r"#{1,2}\s*Das siebze[bh]nte Kapitel\s*[:\-\s]*[«»„""]Die Wiederkebr")
    elif "«Weltbühne Radium»" in clean_title:
        # Match both correct spelling "Weltbühne" and typo "Weltbübne"
        patterns.append(r"#{1,2}\s*[«»„""]Weltb[üu](?:hne|bne) Radium[«»„""]?")
        patterns.append(r"[«»„""]Weltb[üu](?:hne|bne) Radium[«»„""]?")
    elif "FRITTES KAPITEL" in clean_title:
        # Handle typo: FRITTES vs DRITTES
        patterns.append(r"#{1,2}\s*(FRITTES|DRITTES)\s+KAPITEL\s*\n+\s*#{1,2}\s*FO")
        patterns.append(r"#\s*(FRITTES|DRITTES)\s+KAPITEL\s*\n+\s*##\s*FO")
        patterns.append(r"#{1,2}\s*(FRITTES|DRITTES)\s+KAPITEL\s*[:\-\s]*FO")
        patterns.append(r"(FRITTES|DRITTES)\s+KAPITEL\s*[:\-\s]*FO")
    elif "ERSTES KAPITEL" in clean_title and "SCHIMMELBERG" in clean_title:
        # Handle the special case where chapter title is on separate lines
        patterns.append(r"#{1,2}\s*ERSTES\s+KAPITEL\s*\n+\s*#{1,2}\s*SCHIMMELBERG")
        patterns.append(r"#\s*ERSTES\s+KAPITEL\s*\n+\s*##\s*SCHIMMELBERG")
        patterns.append(r"#{1,2}\s*ERSTES\s+KAPITEL\s*[:\-\s]*SCHIMMELBERG")
        patterns.append(r"ERSTES\s+KAPITEL\s*[:\-\s]*SCHIMMELBERG")
    elif "KAPITEL" in clean_title:
        # Regular chapter patterns
        parts = clean_title.split(":")
        if len(parts) >= 2:
            chapter_num = parts[0].strip()
            chapter_name = parts[1].strip() if len(parts) > 1 else ""

            # Handle chapters that might be on separate lines (with # or ##)
            patterns.append(
                f"#{{1,2}}\\s*{re.escape(chapter_num)}\\s*\\n+\\s*#{{1,2}}\\s*{re.escape(chapter_name)}"
            )
            patterns.append(
                f"#\\s*{re.escape(chapter_num)}\\s*\\n+\\s*##\\s*{re.escape(chapter_name)}"
            )
            patterns.append(
                f"#{{1,2}}\\s*{re.escape(chapter_num)}\\s*[:\\-\\s]*{re.escape(chapter_name)}"
            )
            patterns.append(f"{re.escape(chapter_num)}\\s*[:\\-\\s]*{re.escape(chapter_name)}")

            # IMPORTANT: Also look for just the chapter name alone (Mistral format)
            # This handles cases where Mistral has just "# DIE ENTFESSELTEN" without "VIERTES KAPITEL"
            patterns.append(f"#{{1,2}}\\s+{re.escape(chapter_name)}(?:\\s|$)")
            patterns.append(f"^#{{1,2}}\\s+{re.escape(chapter_name)}")
            patterns.append(f"\\n#{{1,2}}\\s+{re.escape(chapter_name)}")
            
            # Special case for VIERZEHNTES with Greek letters (ΚΑΡITEL instead of KAPITEL)
            if "VIERZEHNTES KAPITEL" in chapter_num:
                patterns.append(f"VIERZEHNTES\\s+ΚΑΡITEL\\s*\\n+\\s*{re.escape(chapter_name)}")
                patterns.append(f"VIERZEHNTES\\s+ΚΑΡITEL\\s*[:\\-\\s]*{re.escape(chapter_name)}")
                patterns.append(f"VIERZEHNTES\\s+KAPITEL\\s*\\n+\\s*{re.escape(chapter_name)}")
                patterns.append(f"VIERZEHNTES\\s+KAPITEL\\s*[:\\-\\s]*{re.escape(chapter_name)}")
    else:
        # Generic pattern
        patterns.append(f"#{{1,2}}\\s*{re.escape(clean_title)}")
        patterns.append(re.escape(clean_title))

    return patterns


def find_all_chapter_positions(content, human_chapters):
    """Find all chapter positions in the content."""
    chapter_positions = []

    for i, (_stem, filename) in enumerate(human_chapters):
        chapter_title = extract_chapter_title(filename)
        patterns = create_chapter_patterns(chapter_title)

        # Try each pattern
        best_match = None
        for pattern in patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
            if matches:
                # Take the first match
                best_match = matches[0]
                break

        if best_match:
            chapter_positions.append((i, chapter_title, best_match.start(), best_match.end()))
        else:
            chapter_positions.append((i, chapter_title, None, None))

    return chapter_positions


def extract_chapter_content(content, start_pos, end_match_start):
    """Extract chapter content between positions."""
    if start_pos is None:
        return None

    # Find the actual end position
    if end_match_start is not None:
        chapter_content = content[start_pos:end_match_start]
    else:
        chapter_content = content[start_pos:]

    # Clean up page markers if present
    chapter_content = re.sub(r"^# Page \d+\n+", "", chapter_content, flags=re.MULTILINE)
    chapter_content = re.sub(r"\n+# Page \d+\n+", "\n\n", chapter_content)

    return chapter_content.strip()


def split_ocr_file(ocr_file, source_name):
    """Split an OCR file based on human chapter structure."""
    print(f"\nProcessing {source_name} file: {ocr_file}")

    # Read the OCR content
    with open(ocr_file, encoding="utf-8") as f:
        content = f.read()

    # Get human chapter files
    human_chapters = get_human_chapter_files()

    # Find all chapter positions first
    chapter_positions = find_all_chapter_positions(content, human_chapters)

    # Process each chapter
    found_chapters = []
    not_found_chapters = []
    skipped_chapters = []

    for i, (idx, chapter_title, start_pos, _match_end) in enumerate(chapter_positions):
        _stem, filename = human_chapters[idx]

        # Check if file already exists and skip if configured
        output_filename = filename.replace(".md", f"-{source_name.lower()}.md")
        output_path = HUMAN_CHAPTERS_DIR / output_filename

        if not OVERWRITE_EXISTING and output_path.exists():
            # Check if it has real content (not just placeholder)
            with open(output_path, encoding="utf-8") as f:
                existing_content = f.read()
                if "[Chapter content not found in OCR]" not in existing_content:
                    skipped_chapters.append(chapter_title)
                    print(f"  ⏭️  Skipped (exists): {chapter_title}")
                    continue

        # Find the next chapter's start position
        next_start = None
        for j in range(i + 1, len(chapter_positions)):
            if chapter_positions[j][2] is not None:
                next_start = chapter_positions[j][2]
                break

        # Extract chapter content
        if start_pos is not None:
            chapter_content = extract_chapter_content(content, start_pos, next_start)
        else:
            chapter_content = None

        if chapter_content:
            # Save the chapter with source suffix
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"# {chapter_title}\n\n")
                f.write(f"<!-- Source: {source_name} OCR -->\n\n")
                f.write(chapter_content)

            found_chapters.append(chapter_title)
            print(f"  ✓ Found and saved: {chapter_title}")
        else:
            not_found_chapters.append(chapter_title)
            print(f"  ✗ Not found: {chapter_title}")

            # Create empty placeholder file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(f"# {chapter_title}\n\n")
                f.write(f"<!-- Source: {source_name} OCR -->\n")
                f.write(f"<!-- WARNING: Chapter not found in {source_name} OCR -->\n\n")
                f.write("[Chapter content not found in OCR]\n")

    print(f"\n{source_name} Summary:")
    print(f"  Found: {len(found_chapters)}/{len(human_chapters)} chapters")
    if skipped_chapters:
        print(f"  Skipped (existing): {len(skipped_chapters)} chapters")
    if not_found_chapters:
        print("  Missing chapters:")
        for chapter in not_found_chapters:
            print(f"    - {chapter}")

    return found_chapters, not_found_chapters


def main():
    """Split OCR files based on human chapter structure."""
    print("Splitting Gemini and Mistral OCR files to match human chapter structure")
    print(f"Output directory: {HUMAN_CHAPTERS_DIR}")
    print(f"Overwrite existing: {OVERWRITE_EXISTING}")

    # Check if files exist
    if not MISTRAL_FILE.exists():
        print(f"Error: Mistral file not found: {MISTRAL_FILE}")
        return

    if not GEMINI_FILE.exists():
        print(f"Error: Gemini file not found: {GEMINI_FILE}")
        return

    if not HUMAN_CHAPTERS_DIR.exists():
        print(f"Error: Human chapters directory not found: {HUMAN_CHAPTERS_DIR}")
        return

    # Process Mistral file
    mistral_found, mistral_missing = split_ocr_file(MISTRAL_FILE, "mistral")

    # Process Gemini file
    gemini_found, gemini_missing = split_ocr_file(GEMINI_FILE, "gemini")

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    human_chapters = get_human_chapter_files()
    print(f"Total chapters in human reference: {len(human_chapters)}")
    print(f"Mistral chapters found: {len(mistral_found)}/{len(human_chapters)}")
    print(f"Gemini chapters found: {len(gemini_found)}/{len(human_chapters)}")

    # Check which chapters are missing in both
    both_missing = set(mistral_missing) & set(gemini_missing)
    if both_missing:
        print(f"\nChapters missing in BOTH OCR files ({len(both_missing)}):")
        for chapter in sorted(both_missing):
            print(f"  - {chapter}")

    print("\n✅ Splitting complete!")
    print(f"Files saved to: {HUMAN_CHAPTERS_DIR}")
    print("  - Human files: original names")
    print("  - Mistral files: *-mistral.md")
    print("  - Gemini files: *-gemini.md")

    if not OVERWRITE_EXISTING:
        print("\nNote: Set OVERWRITE_EXISTING = True to overwrite existing files")


if __name__ == "__main__":
    main()
