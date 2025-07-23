"""Citation validation module for enriching bibliographic data using multiple APIs."""

import asyncio
import json
import os
from typing import Any, cast
from urllib.parse import quote

import aiohttp
from dotenv import load_dotenv

load_dotenv()

class CitationValidator:
    """Validate and enrich citations using various APIs."""
    
    def __init__(self):
        self.session: aiohttp.ClientSession | None = None
        self.google_books_key = os.getenv("GOOGLE_API_KEY")
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        if self.session:
            await self.session.close()
    
    async def search_google_books(self, citation: dict[str, Any]) -> dict[str, Any] | None:
        """Search Google Books API for citation details."""
        if not self.google_books_key:
            return None
            
        # Build search query
        query_parts = []
        
        # Add title
        if citation.get('title'):
            if isinstance(citation['title'], list):
                # Handle split citations like 2a/2b
                title = citation['title'][0] if citation['title'] else None
            else:
                title = citation['title']
            if title:
                query_parts.append(f'intitle:"{title}"')
        
        # Add authors
        if citation.get('authors'):
            for author in citation['authors']:
                if author.get('surname'):
                    name = author['surname']
                    if author.get('firstname'):
                        name = f"{author['firstname']} {name}"
                    query_parts.append(f'inauthor:"{name}"')
        
        if not query_parts:
            return None
            
        query = ' '.join(query_parts)
        url = f"https://www.googleapis.com/books/v1/volumes?q={quote(query)}&key={self.google_books_key}"
        
        try:
            if not self.session:
                return None
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('totalItems', 0) > 0:
                        # Return the first match
                        return data['items'][0]['volumeInfo']
        except Exception as e:
            print(f"Google Books error for {citation.get('footnote_num')}: {e}")
            
        return None
    
    async def search_crossref(self, citation: dict[str, Any]) -> dict[str, Any] | None:
        """Search CrossRef API for journal articles."""
        if citation.get('citation_type') != 'journal' or not citation.get('title'):
            return None
            
        title = citation['title'][0] if isinstance(citation['title'], list) else citation['title']
        
        # Build query
        query_parts = [title]
        if citation.get('authors'):
            for author in citation['authors']:
                if author.get('surname'):
                    query_parts.append(author['surname'])
        
        query = ' '.join(query_parts)
        url = f"https://api.crossref.org/works?query={quote(query)}&rows=1"
        
        try:
            if not self.session:
                return None
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('message', {}).get('items', [])
                    if items:
                        return items[0]
        except Exception as e:
            print(f"CrossRef error for {citation.get('footnote_num')}: {e}")
            
        return None
    
    async def search_openlibrary(self, citation: dict[str, Any]) -> dict[str, Any] | None:
        """Search OpenLibrary API for book details."""
        if not citation.get('title'):
            return None
            
        title = citation['title'][0] if isinstance(citation['title'], list) else citation['title']
        
        # Build search query
        params = {'title': title, 'limit': 1}
        
        # Add author if available
        if citation.get('authors') and citation['authors'][0].get('surname'):
            params['author'] = citation['authors'][0]['surname']
        
        url = "https://openlibrary.org/search.json"
        
        try:
            if not self.session:
                return None
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('docs'):
                        return data['docs'][0]
        except Exception as e:
            print(f"OpenLibrary error for {citation.get('footnote_num')}: {e}")
            
        return None
    
    
    def generate_modern_citation(self, citation: dict[str, Any]) -> str:
        """Generate modern German citation format."""
        cite_type = citation.get('citation_type', '')
        
        # Handle special types
        if cite_type == 'explanatory_note':
            return f"Anmerkung: {citation.get('raw_text', '').replace('${ }^{' + str(citation.get('footnote_num')) + '}$ ', '').strip()}"
        elif cite_type == 'reference':
            # For references like "ebenda" or "l.c.", we should have already expanded them
            # But if not, keep the reference note
            notes = citation.get('notes', '')
            if 'Reference to footnote' in notes:
                ref_num = notes.split('Reference to footnote ')[-1]
                return f"Siehe Anm. {ref_num}"
            elif 'ebenda' in notes.lower():
                return "Ebd."
            elif 'l.c.' in notes:
                return "A.a.O."  # am angegebenen Ort (modern German for l.c.)
        elif cite_type == 'poem':
            authors = citation.get('authors', [])
            if authors and authors[0].get('surname'):
                author = f"{authors[0].get('surname')}, {authors[0].get('firstname', '')}"
                title = citation.get('title', '')
                journal = citation.get('journal', '')
                year = citation.get('year', '')
                location = citation.get('location', '')
                publisher = citation.get('publisher', '')
                
                if journal:
                    return f'{author}: „{title}". In: {journal}. {location}: {publisher}, {year}.'
                else:
                    return f'{author}: „{title}". {location}: {publisher}, {year}.'
            return citation.get('raw_text', '')
            
        # Build modern citation for books/journals
        parts = []
        
        # Authors
        authors = citation.get('authors', [])
        if authors:
            author_parts = []
            for i, author in enumerate(authors):
                surname = author.get('surname', '')
                firstname = author.get('firstname', '')
                if surname:
                    if i == 0:  # First author: Surname, Firstname
                        author_parts.append(f"{surname}, {firstname}".strip())
                    else:  # Other authors: Firstname Surname
                        author_parts.append(f"{firstname} {surname}".strip())
            
            if author_parts:  # Only add if we have authors
                if len(author_parts) > 1:
                    parts.append(' und '.join(author_parts))
                else:
                    parts.append(author_parts[0])
        
        # Year
        year = citation.get('year')
        if year:
            parts.append(f"({year})")
        
        # Title
        title = citation.get('title', '')
        if cite_type == 'journal':
            parts.append(f'„{title}"')
        else:
            parts.append(f'{title}')
        
        # Journal details
        if cite_type == 'journal':
            journal = citation.get('journal', '')
            if journal:
                parts.append(f"In: {journal}")
            
            volume = citation.get('volume')
            issue = citation.get('issue')
            if volume:
                vol_str = f"Bd. {volume}"
                if issue:
                    vol_str += f", Nr. {issue}"
                parts.append(vol_str)
        
        # Edition
        edition = citation.get('edition')
        if edition:
            parts.append(edition)
        
        # Location and Publisher
        location = citation.get('location')
        publisher = citation.get('publisher')
        if location and publisher:
            parts.append(f"{location}: {publisher}")
        elif location:
            parts.append(location)
        elif publisher:
            parts.append(publisher)
        
        # Pages
        pages = citation.get('pages', '')
        if pages:
            # Convert old style to new
            pages = pages.replace('p. ', 'S. ').replace('pp. ', 'S. ')
            if not pages.startswith('S.'):
                pages = f"S. {pages}"
            parts.append(pages)
        
        # DOI
        doi = citation.get('doi')
        if doi:
            parts.append(f"DOI: {doi}")
        
        return '. '.join(filter(None, parts)) + '.'
    
    def enrich_citation(self, citation: dict[str, Any], google_data: dict[str, Any] | None, 
                       crossref_data: dict[str, Any] | None, openlibrary_data: dict[str, Any] | None) -> dict[str, Any]:
        """Enrich citation with data from APIs."""
        enriched = citation.copy()
        
        # Skip explanatory notes and references
        if citation.get('citation_type') in ['explanatory_note', 'reference']:
            return enriched
        
        # Google Books enrichment
        if google_data:
            if not enriched.get('year') and google_data.get('publishedDate'):
                year_str = google_data['publishedDate'][:4]
                if year_str.isdigit():
                    enriched['year'] = int(year_str)
            
            if not enriched.get('publisher') and google_data.get('publisher'):
                enriched['publisher'] = google_data['publisher']
            
            if google_data.get('industryIdentifiers'):
                enriched['isbn'] = google_data['industryIdentifiers'][0]['identifier']
            
            if google_data.get('pageCount'):
                enriched['total_pages'] = google_data['pageCount']
        
        # CrossRef enrichment for journal articles
        if crossref_data and citation.get('citation_type') == 'journal':
            if not enriched.get('year') and crossref_data.get('published-print'):
                year_parts = crossref_data['published-print'].get('date-parts', [[]])
                if year_parts and year_parts[0]:
                    enriched['year'] = year_parts[0][0]
            
            if crossref_data.get('DOI'):
                enriched['doi'] = crossref_data['DOI']
            
            if not enriched.get('journal') and crossref_data.get('container-title'):
                enriched['journal'] = crossref_data['container-title'][0]
            
            if not enriched.get('volume') and crossref_data.get('volume'):
                enriched['volume'] = crossref_data['volume']
            
            if not enriched.get('issue') and crossref_data.get('issue'):
                enriched['issue'] = crossref_data['issue']
        
        # OpenLibrary enrichment
        if openlibrary_data:
            if not enriched.get('year') and openlibrary_data.get('first_publish_year'):
                enriched['year'] = openlibrary_data['first_publish_year']
            
            if openlibrary_data.get('isbn'):
                enriched['isbn'] = openlibrary_data['isbn'][0]
            
            if not enriched.get('publisher') and openlibrary_data.get('publisher'):
                enriched['publisher'] = openlibrary_data['publisher'][0]
        
        # Mark as validated
        enriched['validated'] = True
        enriched['validation_sources'] = []
        if google_data:
            enriched['validation_sources'].append('google_books')
        if crossref_data:
            enriched['validation_sources'].append('crossref')
        if openlibrary_data:
            enriched['validation_sources'].append('openlibrary')
        
        # Generate modern citation
        enriched['modern_citation'] = self.generate_modern_citation(enriched)
        
        return enriched
    
    async def validate_citation(self, citation: dict[str, Any]) -> dict[str, Any]:
        """Validate and enrich a single citation."""
        # Skip certain types but still generate modern citation
        if citation.get('citation_type') in ['explanatory_note', 'reference', 'poem']:
            citation['modern_citation'] = self.generate_modern_citation(citation)
            return citation
        
        # Skip if no title or already validated
        if not citation.get('title') or citation.get('validated'):
            return citation
        
        # Search multiple sources in parallel
        openlibrary_task = self.search_openlibrary(citation)
        google_task = self.search_google_books(citation)
        
        # Run OpenLibrary and Google Books in parallel
        openlibrary_data, google_data = await asyncio.gather(
            openlibrary_task,
            google_task,
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(openlibrary_data, Exception):
            openlibrary_data = None
        if isinstance(google_data, Exception):
            google_data = None
        
        crossref_data: dict[str, Any] | None = None
        
        # For journal articles, also try CrossRef
        if citation.get('citation_type') == 'journal':
            crossref_data = await self.search_crossref(citation)
        
        # Enrich citation - cast to correct types for type checker
        google_final = cast(dict[str, Any] | None, None if isinstance(google_data, Exception) else google_data)
        openlibrary_final = cast(dict[str, Any] | None, None if isinstance(openlibrary_data, Exception) else openlibrary_data)
        enriched = self.enrich_citation(citation, google_final, crossref_data, openlibrary_final)
        
        return enriched


async def main():
    """Validate all citations in the parsed citations file."""
    input_file = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz.citations.json"
    output_file = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz.validated_citations.json"
    
    # Check if validated file exists and use it as input to preserve manual fixes
    if os.path.exists(output_file):
        print("Using existing validated file to preserve manual fixes...")
        input_file = output_file
    
    # Load citations
    with open(input_file, encoding='utf-8') as f:
        citations = json.load(f)
    
    print(f"Loaded {len(citations)} citations")
    
    # Validate citations
    async with CitationValidator() as validator:
        validated_citations = []
        
        for i, citation in enumerate(citations):
            print(f"\nValidating citation {citation['footnote_num']} ({i+1}/{len(citations)})...", end='', flush=True)
            
            validated = await validator.validate_citation(citation)
            validated_citations.append(validated)
            
            # Show what was found
            if citation.get('citation_type') in ['explanatory_note', 'reference', 'poem']:
                print(f" - Skipped ({citation.get('citation_type')})")
            elif validated.get('validation_sources'):
                print(f" ✓ Found in: {', '.join(validated['validation_sources'])}")
                if validated.get('isbn'):
                    print(f"  - ISBN: {validated['isbn']}")
                if validated.get('doi'):
                    print(f"  - DOI: {validated['doi']}")
                if validated.get('year') and not citation.get('year'):
                    print(f"  - Year: {validated['year']}")
                if validated.get('publisher') and not citation.get('publisher'):
                    print(f"  - Publisher: {validated['publisher']}")
            else:
                print(" - No matches found")
    
    # Save validated citations
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(validated_citations, f, indent=2, ensure_ascii=False)
    
    print(f"\n\nValidation complete! Results saved to: {output_file}")
    
    # Summary statistics - separate bibliographic from non-bibliographic
    bibliographic = [c for c in validated_citations 
                     if c.get('citation_type') not in ['explanatory_note', 'reference', 'poem']]
    non_bibliographic = [c for c in validated_citations 
                         if c.get('citation_type') in ['explanatory_note', 'reference', 'poem']]
    
    validated_biblio = sum(1 for c in bibliographic if c.get('validation_sources'))
    
    print("\nSummary:")
    print(f"- Total entries: {len(citations)}")
    print(f"  - Bibliographic citations: {len(bibliographic)}")
    print(f"  - Non-bibliographic (notes/references/poems): {len(non_bibliographic)}")
    print("\nValidation Results (bibliographic only):")
    print(f"- Validated: {validated_biblio}/{len(bibliographic)} ({validated_biblio/len(bibliographic)*100:.1f}%)")
    
    # Show breakdown by source
    source_counts = {}
    for c in bibliographic:
        if c.get('validation_sources'):
            for source in c['validation_sources']:
                source_counts[source] = source_counts.get(source, 0) + 1
    
    if source_counts:
        print("\nFound by source:")
        for source, count in sorted(source_counts.items()):
            print(f"  - {source}: {count}")
    
    # Show citations that need manual review
    needs_review = [c for c in bibliographic if not c.get('validation_sources')]
    
    if needs_review:
        print(f"\n{len(needs_review)} bibliographic citations NOT FOUND by any API:")
        for c in needs_review:
            title = c.get('title', 'No title')
            if isinstance(title, list):
                title = title[0] if title else 'No title'
            print(f"  - {c['footnote_num']}: {title[:60]}...")


if __name__ == "__main__":
    asyncio.run(main())