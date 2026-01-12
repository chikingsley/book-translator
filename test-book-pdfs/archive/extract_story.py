"""Extract story content from von Franz's Puer Aeternus analysis - v2."""

import re

# More aggressive analysis markers
ANALYSIS_PATTERNS = [
    # Jungian/psychological terminology
    r'\bSelf\b', r'\bshadow\b', r'\banima\b', r'\banimus\b',
    r'\barchetype\b', r'\bunconscious\b', r'\bego complex\b',
    r'\bpuer aeternus\b', r'\bpsycholog', r'\bneurosis\b',
    r'\bsymbol\b', r'\bprojection\b', r'\bdissociation\b',

    # Commentary/lecture markers
    r'\bYou see\b', r'\bYou can see\b', r'\bYou could say\b',
    r'\bYou will find\b', r'\bYou remember\b', r'\bYou would\b',
    r'\bI think\b', r'\bI would\b', r'\bI have\b', r'\bI once\b',
    r'\bI know\b', r'\bI am\b', r'\bI cannot\b',
    r'\bWe can\b', r'\bWe could\b', r'\bWe see\b', r'\bWe are\b',
    r'\bWe cannot\b', r'\bWe should\b', r'\bWe have\b',
    r'\bThis means\b', r'\bThis is a\b', r'\bThis shows\b',
    r'\bThis symboliz', r'\bThis illustrat', r'\bThis mirrors\b',
    r'\bThat is\b', r'\bThat was\b', r'\bThat would\b',
    r'\bIn other words\b', r'\bIn Jungian\b', r'\bIn analysis\b',
    r'\bIn psycholog', r'\bIn anticipation\b',
    r'\bAs you see\b', r'\bAs I said\b', r'\bAs we\b',
    r'\bNaturally\b', r'\bObviously\b', r'\bClearly\b',
    r'\bAmplif', r'\bpersonif', r'\binterpret\b',

    # References to the author/book as object
    r'\bThe author\b', r'\bGoetz\b', r'\bBruno Goetz\b',
    r'\bthe book\b', r'\bthis novel\b', r'\bthe story\b',
    r'\bthe hero\b', r'\bour story\b',

    # References to other works/concepts
    r'\bKubin\b', r'\bMeyrinck\b', r'\bHoffman\b', r'\bPoe\b',
    r'\bPersian\b', r'\bGnostic\b', r'\bManichaen\b',
    r'\bWotan\b', r'\bViking\b', r'\bLittle Prince\b',
    r'\bJung\b', r'\bFreud\b',

    # Meta-discussion
    r'\bAnswer:\b', r'\bQuestion:\b', r'\bMrs\. \w+\b',
    r'\blecture\b', r'\btold you\b', r'\bmentioned\b',
    r'\bas I told\b', r'\bas mentioned\b',
    r'\balchemical process\b', r'\bfascinosum\b',

    # Comparing/explaining
    r'\bcompare\b', r'\bsimilar to\b', r'\blike the\b',
    r'\bis typical\b', r'\bis well known\b', r'\bis also\b',
    r'\bwould predict\b', r'\bwould you\b',
]


def is_analysis_paragraph(para: str) -> bool:
    """Check if paragraph is analysis rather than story."""
    for pattern in ANALYSIS_PATTERNS:
        if re.search(pattern, para, re.IGNORECASE):
            return True
    return False


def is_page_number(line: str) -> bool:
    """Check if line is just a page number."""
    return bool(re.match(r'^\s*\d{2,3}\s*$', line))


def is_header(line: str) -> bool:
    """Check if line is a header."""
    return line.strip() in ['Marie-Louise von Franz', 'Problem of the Puer Aeternus']


def get_chapter_title(line: str) -> str | None:
    """Extract chapter title if this is a chapter marker."""
    # "The first chapter, entitled "Schimmelberg"..."
    match = re.search(r'The (\w+) chapter[^"]*"([^"]+)"', line, re.IGNORECASE)
    if match:
        return f"Chapter: {match.group(2)}"

    # "Lecture 9" etc
    match = re.match(r'^Lecture (\d+)', line)
    if match:
        return f"Lecture {match.group(1)}"

    return None


def extract_story(input_path: str, output_path: str) -> None:
    """Extract story portions from von Franz text."""
    with open(input_path, encoding='utf-8') as f:
        text = f.read()

    # Split into paragraphs
    paragraphs = text.split('\n\n')

    story_parts = []
    current_chapter = None

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Clean up page numbers and headers within paragraph
        lines = para.split('\n')
        clean_lines = []
        for line in lines:
            if is_page_number(line) or is_header(line):
                continue
            clean_lines.append(line)
        para = ' '.join(clean_lines).strip()

        if not para:
            continue

        # Check for chapter markers
        chapter = get_chapter_title(para)
        if chapter:
            current_chapter = chapter
            story_parts.append(f'\n\n## {chapter}\n\n')
            continue

        # Skip analysis paragraphs
        if is_analysis_paragraph(para):
            continue

        # This looks like story content
        story_parts.append(para + '\n\n')

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('# Das Reich ohne Raum - English Story\n\n')
        f.write('*Extracted from Marie-Louise von Franz\'s retelling*\n\n')
        f.write('---\n\n')
        f.writelines(story_parts)

    # Count stats
    with open(output_path, encoding='utf-8') as f:
        content = f.read()

    print(f"Extracted story to {output_path}")
    print(f"Output size: {len(content):,} characters")
    print(f"Paragraphs: {len(story_parts)}")


if __name__ == '__main__':
    input_file = '/Users/chiejimofor/Documents/Github/book-translator/test-book-pdfs/von-franz-das-reich-analysis.txt'
    output_file = '/Users/chiejimofor/Documents/Github/book-translator/test-book-pdfs/das-reich-english-story-v2.md'
    extract_story(input_file, output_file)
