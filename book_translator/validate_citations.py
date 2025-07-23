import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
import os
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

class CitationValidator:
    """Validate and enrich citations using various APIs."""
    
    def __init__(self):
        self.session = None
        self.google_books_key = os.getenv("GOOGLE_BOOKS_API_KEY")
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
    
    async def search_google_books(self, citation: Dict) -> Optional[Dict]:
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
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('totalItems', 0) > 0:
                        # Return the first match
                        return data['items'][0]['volumeInfo']
        except Exception as e:
            print(f"Google Books error for {citation.get('footnote_num')}: {e}")
            
        return None
    
    async def search_crossref(self, citation: Dict) -> Optional[Dict]:
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
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    items = data.get('message', {}).get('items', [])
                    if items:
                        return items[0]
        except Exception as e:
            print(f"CrossRef error for {citation.get('footnote_num')}: {e}")
            
        return None
    
    async def search_openlibrary(self, citation: Dict) -> Optional[Dict]:
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
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('docs'):
                        return data['docs'][0]
        except Exception as e:
            print(f"OpenLibrary error for {citation.get('footnote_num')}: {e}")
            
        return None
    
    def enrich_citation(self, citation: Dict, google_data: Optional[Dict], 
                       crossref_data: Optional[Dict], openlibrary_data: Optional[Dict]) -> Dict:
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
        
        return enriched
    
    async def validate_citation(self, citation: Dict) -> Dict:
        """Validate and enrich a single citation."""
        # Skip certain types
        if citation.get('citation_type') in ['explanatory_note', 'reference', 'poem']:
            return citation
        
        # Skip if no title or already validated
        if not citation.get('title') or citation.get('validated'):
            return citation
        
        # Search APIs in parallel
        tasks = [
            self.search_google_books(citation),
            self.search_crossref(citation),
            self.search_openlibrary(citation)
        ]
        
        google_data, crossref_data, openlibrary_data = await asyncio.gather(*tasks)
        
        # Enrich citation
        enriched = self.enrich_citation(citation, google_data, crossref_data, openlibrary_data)
        
        return enriched


async def main():
    """Validate all citations in the parsed citations file."""
    input_file = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz.parsed_citations.json"
    output_file = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz.validated_citations.json"
    
    # Check if validated file exists and use it as input to preserve manual fixes
    if os.path.exists(output_file):
        print(f"Using existing validated file to preserve manual fixes...")
        input_file = output_file
    
    # Load citations
    with open(input_file, 'r', encoding='utf-8') as f:
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
            if validated.get('validation_sources'):
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
    
    # Summary statistics
    validated_count = sum(1 for c in validated_citations if c.get('validated'))
    enriched_count = sum(1 for c in validated_citations if c.get('validation_sources'))
    
    print(f"\nSummary:")
    print(f"- Total citations: {len(citations)}")
    print(f"- Validated: {validated_count}")
    print(f"- Enriched with API data: {enriched_count}")
    
    # Show citations that need manual review
    needs_review = [c for c in validated_citations 
                    if c.get('citation_type') not in ['explanatory_note', 'reference', 'poem'] 
                    and not c.get('validation_sources')]
    
    if needs_review:
        print(f"\n{len(needs_review)} citations need manual review:")
        for c in needs_review:
            title = c.get('title', 'No title')
            if isinstance(title, list):
                title = title[0] if title else 'No title'
            print(f"  - {c['footnote_num']}: {title[:60]}...")


if __name__ == "__main__":
    asyncio.run(main())