"""Module for parsing citations from footnotes using Mistral AI."""

import asyncio
import json
import os
import sys
from dataclasses import asdict, dataclass, field

from dotenv import load_dotenv
from mistralai import Mistral
from mistralai.models import UserMessage

try:
    from .extract_footnotes import extract_all_footnotes
except ImportError:
    # Running as script
    from extract_footnotes import extract_all_footnotes

load_dotenv()

@dataclass
class ParsedCitation:
    """Structured citation data."""

    footnote_num: int
    raw_text: str
    authors: list[dict[str, str]] = field(default_factory=list)
    title: str | None = None
    journal: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    year: str | None = None
    publisher: str | None = None
    location: str | None = None
    edition: str | None = None
    citation_type: str | None = None  # book, journal, etc.
    notes: str | None = None  # for things like "ebenda", "l.c."


class CitationParser:
    """Parse citations from footnotes."""
    
    def __init__(self):
        """Initialize the citation parser with Mistral API."""
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable not set")
        
        self.client = Mistral(api_key=api_key)
        self.model = "mistral-large-latest"
        self.fallback_model = "mistral-medium-latest"
        self.current_model = self.model
        
    
    async def parse_citation(self, footnote_num: int, text: str) -> ParsedCitation:
        """Parse a single citation using Mistral."""
        prompt = """Parse this academic citation and extract structured information. Return JSON only.

Citation: """ + text + """

Extract:
- authors: array of objects with firstname and surname (e.g., [{"firstname": "C. G.", "surname": "Jung"}])
- title: the work's title (without location, year, or page numbers)
- journal: journal name if it's a journal article (null if not)
- volume: volume number (null if not present)
- issue: issue number (null if not present)  
- pages: page numbers (e.g., "p. 123" or "pp. 123-145") (null if not present)
- year: publication year as integer (null if not present)
- publisher: publisher name (null if not present)
- location: city of publication (null if not present)
- edition: edition info if present (null if not present)
- citation_type: "book", "journal", "book_series", "reference", or "unknown"
- notes: special notes like "ebenda" (ibid), "l.c." (loco citato), or if it's a poem/quote (null if none)

For "ebenda" or "ibid", set citation_type to "reference" and add appropriate note.
For German citations, "Vgl." means "compare/see" and should be ignored.
"l.c." means "loco citato" (in the place cited).

Use null for missing values, not empty strings."""

        # Keep trying with alternating models until success
        attempt = 0
        while True:
            try:
                response = await self.client.chat.complete_async(
                    model=self.current_model,
                    messages=[UserMessage(content=prompt)],
                    response_format={
                        "type": "json_object"
                    }
                )
                
                # Get content from response - with json_object mode it's always valid JSON
                content = response.choices[0].message.content
                if not isinstance(content, str):
                    raise ValueError(f"Unexpected content type: {type(content)}")
                parsed_data = json.loads(content)
                break  # Success!
                
            except Exception as e:
                if "429" in str(e) or "capacity" in str(e).lower():
                    # Switch models
                    self.current_model = self.fallback_model if self.current_model == self.model else self.model
                    attempt += 1
                    print(f" (retry {attempt} with {self.current_model})", end='', flush=True)
                    await asyncio.sleep(0.5)  # Small delay between retries
                    continue
                else:
                    # Other error - re-raise
                    raise
        
        try:
            # Create ParsedCitation object
            citation = ParsedCitation(
                footnote_num=footnote_num,
                raw_text=text,
                authors=parsed_data.get('authors', []),
                title=parsed_data.get('title'),
                journal=parsed_data.get('journal'),
                volume=parsed_data.get('volume'),
                issue=parsed_data.get('issue'),
                pages=parsed_data.get('pages'),
                year=parsed_data.get('year'),
                publisher=parsed_data.get('publisher'),
                location=parsed_data.get('location'),
                edition=parsed_data.get('edition'),
                citation_type=parsed_data.get('citation_type'),
                notes=parsed_data.get('notes')
            )
            
            return citation
            
        except Exception as e:
            print(f"Error parsing citation {footnote_num}: {e}")
            # Return minimal citation on error
            return ParsedCitation(footnote_num=footnote_num, raw_text=text)


async def main(markdown_file: str):
    """Parse all citations from a markdown file."""
    # First extract footnotes
    footnotes, _, _ = extract_all_footnotes(markdown_file)
    
    print(f"\n{'='*60}")
    print("PARSING CITATIONS")
    print(f"{'='*60}\n")
    
    parser = CitationParser()
    parsed_citations = []
    
    # Process citations with async
    total = len(footnotes)
    for i, num in enumerate(sorted(footnotes.keys())):
        print(f"Parsing citation {num} ({i+1}/{total})...", end='', flush=True)
        citation = await parser.parse_citation(num, footnotes[num])
        parsed_citations.append(citation)
        print(" done")
        
        # Show sample of what was extracted
        if citation.authors:
            authors_str = ', '.join([f"{a.get('firstname', '')} {a.get('surname', '')}".strip() for a in citation.authors])
            print(f"  Authors: {authors_str}")
        if citation.title:
            print(f"  Title: {citation.title[:60]}...")
        if citation.year:
            print(f"  Year: {citation.year}")
    
    # Save parsed citations
    output_file = markdown_file.replace('.md', '.parsed_citations.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([asdict(c) for c in parsed_citations], f, indent=2, ensure_ascii=False)
    
    print(f"\nParsed citations saved to: {output_file}")
    
    # Summary statistics
    print(f"\n{'='*60}")
    print("PARSING SUMMARY")
    print(f"{'='*60}")
    print(f"Total citations parsed: {len(parsed_citations)}")
    
    # Count by type
    type_counts = {}
    for c in parsed_citations:
        ctype = c.citation_type or 'unknown'
        type_counts[ctype] = type_counts.get(ctype, 0) + 1
    
    print("\nBy type:")
    for ctype, count in sorted(type_counts.items()):
        print(f"  {ctype}: {count}")
    
    # Count successful extractions
    with_authors = sum(1 for c in parsed_citations if c.authors)
    with_title = sum(1 for c in parsed_citations if c.title)
    with_year = sum(1 for c in parsed_citations if c.year)
    
    print("\nExtraction success:")
    print(f"  With authors: {with_authors}/{len(parsed_citations)} ({with_authors/len(parsed_citations)*100:.1f}%)")
    print(f"  With title: {with_title}/{len(parsed_citations)} ({with_title/len(parsed_citations)*100:.1f}%)")
    print(f"  With year: {with_year}/{len(parsed_citations)} ({with_year/len(parsed_citations)*100:.1f}%)")
    
    # Show failed citations
    failed_citations = []
    for c in parsed_citations:
        if not c.authors and not c.title and c.citation_type != 'reference':
            failed_citations.append(c)
    
    if failed_citations:
        print(f"\n## FAILED TO PARSE ({len(failed_citations)} citations)\n")
        for c in failed_citations:
            print(f"### Footnote {c.footnote_num}")
            print(f"**Raw text:** {c.raw_text}")
            print(f"**Type:** {c.citation_type or 'unknown'}\n")
    
    # Save failed citations only
    failed_file = markdown_file.replace('.md', '.failed_citations.md')
    with open(failed_file, 'w', encoding='utf-8') as f:
        if failed_citations:
            for c in failed_citations:
                f.write(f"{c.raw_text}\n\n")
    
    print(f"\n📄 Failed citations saved to: {failed_file}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parse_citations.py <markdown_file>")
        sys.exit(1)
    
    asyncio.run(main(sys.argv[1]))