"""Search for citations using the raw text after the colon."""

import asyncio
import json
import os
import re
from typing import Any
from urllib.parse import quote

import aiohttp
from dotenv import load_dotenv
from google import genai

load_dotenv()


class CitationSearcher:
    """Search for citations using raw text."""

    def __init__(self):
        """Initialize the citation searcher."""
        self.session: aiohttp.ClientSession | None = None
        self.google_books_key = os.getenv("GOOGLE_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.gemini_client: genai.Client | None = None
        if self.gemini_key:
            google_api_key = os.environ.pop("GOOGLE_API_KEY", None)
            self.gemini_client = genai.Client(api_key=self.gemini_key)
            if google_api_key:
                os.environ["GOOGLE_API_KEY"] = google_api_key

    async def __aenter__(self):
        """Enter async context manager."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        """Exit async context manager."""
        if self.session:
            await self.session.close()

    def extract_search_text(self, raw_text: str) -> str:
        """Extract searchable text from citation."""
        text = ' '.join(raw_text.split())
        return text.strip()

    async def search_google_books(self, text: str) -> list[dict[str, Any]]:
        """Search Google Books with API key."""
        if not self.google_books_key:
            return []

        url = f"https://www.googleapis.com/books/v1/volumes?q={quote(text)}&key={self.google_books_key}"

        try:
            if not self.session:
                return []
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    results: list[dict[str, Any]] = []
                    for item in data.get('items', [])[:3]:
                        info = item.get('volumeInfo', {})
                        result: dict[str, Any] = {
                            'title': info.get('title'),
                            'authors': info.get('authors', []),
                            'publisher': info.get('publisher'),
                            'publishedDate': info.get('publishedDate'),
                            'description': info.get('description'),
                            'pageCount': info.get('pageCount'),
                            'categories': info.get('categories', []),
                            'language': info.get('language'),
                            'previewLink': info.get('previewLink'),
                            'infoLink': info.get('infoLink')
                        }
                        results.append(result)
                    return results
        except Exception as e:
            print(f"Google Books error: {e}")

        return []

    async def search_openlibrary(self, text: str) -> list[dict[str, Any]]:
        """Search OpenLibrary."""
        url = f"https://openlibrary.org/search.json?q={quote(text)}&limit=3"

        try:
            if not self.session:
                return []
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    results: list[dict[str, Any]] = []
                    for doc in data.get('docs', []):
                        result: dict[str, Any] = {
                            'title': doc.get('title'),
                            'authors': list(doc.get('author_name', [])),
                            'publisher': doc.get('publisher', [None])[0] if doc.get('publisher') else None,
                            'publish_year': doc.get('first_publish_year'),
                            'isbn': doc.get('isbn', [None])[0] if doc.get('isbn') else None,
                            'language': doc.get('language', []),
                            'subject': doc.get('subject', []),
                            'openlibrary_key': doc.get('key')
                        }
                        results.append(result)
                    return results
        except Exception as e:
            print(f"OpenLibrary error: {e}")

        return []

    def evaluate_results_with_gemini(self, citation_text: str, search_results: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        """Use Gemini to evaluate which search results match the citation."""
        if not self.gemini_client or not any(search_results.values()):
            return {}

        prompt = f"""Given this German academic citation:
"{citation_text}"

Evaluate which of these search results (if any) is the book/article being cited. Consider:
- Author names (including variations/abbreviations)
- Title matches (partial or full)
- Publication year
- Publisher/location
- Page numbers

For each result, respond with ONLY a JSON object like:
{{
  "google_books_0": {{"match": true/false, "confidence": 0-100, "reason": "brief reason"}},
  "openlibrary_1": {{"match": true/false, "confidence": 0-100, "reason": "brief reason"}}
}}

Search results:
"""

        for source, results in search_results.items():
            for i, result in enumerate(results):
                prompt += f"\n{source}_{i}:\n"
                if source == "google_books":
                    prompt += f"Title: {result.get('title', 'N/A')}\n"
                    prompt += f"Authors: {', '.join(result.get('authors', []))}\n"
                    prompt += f"Publisher: {result.get('publisher', 'N/A')}\n"
                    prompt += f"Date: {result.get('publishedDate', 'N/A')}\n"
                else:  # openlibrary
                    prompt += f"Title: {result.get('title', 'N/A')}\n"
                    prompt += f"Authors: {', '.join(result.get('authors', []))}\n"
                    prompt += f"Publisher: {result.get('publisher', 'N/A')}\n"
                    prompt += f"Year: {result.get('publish_year', 'N/A')}\n"

        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[prompt]
            )
            if response.text:
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.endswith("```"):
                    text = text[:-3]
                return json.loads(text)
        except Exception as e:
            print(f"Gemini evaluation error: {e}")

        return {}

    async def search_citation(self, footnote_num: int, raw_text: str) -> dict[str, Any]:
        """Search for a single citation across multiple sources."""
        search_text = self.extract_search_text(raw_text)

        if not search_text or len(search_text) < 10:
            return {
                'footnote_num': footnote_num,
                'raw_text': raw_text,
                'search_text': search_text,
                'status': 'too_short',
                'results': {}
            }

        google_books_task = self.search_google_books(search_text)
        openlibrary_task = self.search_openlibrary(search_text)

        google_books_results, openlibrary_results = await asyncio.gather(
            google_books_task,
            openlibrary_task,
            return_exceptions=True
        )

        if isinstance(google_books_results, Exception):
            google_books_results = []
        if isinstance(openlibrary_results, Exception):
            openlibrary_results = []

        results = {
            'footnote_num': footnote_num,
            'raw_text': raw_text,
            'search_text': search_text,
            'status': 'searched',
            'results': {
                'google_books': google_books_results,
                'openlibrary': openlibrary_results
            }
        }

        found_any = bool(google_books_results or openlibrary_results)
        results['found'] = found_any

        if found_any and isinstance(google_books_results, list) and isinstance(openlibrary_results, list):
            gemini_evaluation = self.evaluate_results_with_gemini(
                raw_text,
                {'google_books': google_books_results, 'openlibrary': openlibrary_results}
            )
            results['gemini_evaluation'] = gemini_evaluation

        return results


async def main():
    """Search for all citations in the markdown file."""
    with open('test-book-pdfs/archive/Das Reich ohne Raum -- Bruno Goetz-citations.md', encoding='utf-8') as f:
        content = f.read()

    citation_pattern = r'\[\^(\d+)\]:\s*(.+?)(?=\[\^\d+\]:|$)'
    citations = re.findall(citation_pattern, content, re.DOTALL | re.MULTILINE)

    print(f"Found {len(citations)} citations to search")

    async with CitationSearcher() as searcher:
        results: list[dict[str, Any]] = []

        for i, (num, raw_text) in enumerate(citations):
            text = ' '.join(line.strip() for line in raw_text.strip().split('\n') if line.strip())

            print(f"\nSearching citation {num} ({i + 1}/{len(citations)})...")
            print(f"Text: {text[:100]}...")

            result = await searcher.search_citation(int(num), text)
            results.append(result)

            if result['status'] == 'too_short':
                print("  - Skipped (too short)")
            elif result['found']:
                print("  ✓ Found results:")
                if result['results']['google_books']:
                    print(f"    - Google Books: {len(result['results']['google_books'])} results")
                if result['results']['openlibrary']:
                    print(f"    - OpenLibrary: {len(result['results']['openlibrary'])} results")

                if result.get('gemini_evaluation'):
                    matches = [k for k, v in result['gemini_evaluation'].items() if v.get('match')]
                    if matches:
                        print(f"    - Gemini identified {len(matches)} likely match(es)")
            else:
                print("  - No results found")

            await asyncio.sleep(0.5)

    with open('test-book-pdfs/archive/Das Reich ohne Raum -- Bruno Goetz-search_results.md', 'w', encoding='utf-8') as f:
        f.write("# Citation Search Results\n\n")

        for result in results:
            f.write(f"## [^{result['footnote_num']}]\n\n")
            f.write(f"**Original text:** {result['raw_text']}\n\n")
            f.write(f"**Search text:** {result['search_text']}\n\n")

            if result['status'] == 'too_short':
                f.write("**Status:** ❌ Too short to search\n\n")
            elif result['found']:
                f.write("**Status:** ✅ Found results\n\n")

                gemini_eval = result.get('gemini_evaluation', {})

                if result['results']['google_books']:
                    f.write("### Google Books Results\n\n")
                    for i, book in enumerate(result['results']['google_books']):
                        eval_key = f"google_books_{i}"
                        eval_data = gemini_eval.get(eval_key, {})

                        if eval_data.get('match'):
                            f.write(f"{i + 1}. ✅ **{book.get('title', 'No title')}** (Confidence: {eval_data.get('confidence', 0)}%)\n")
                            f.write(f"   - **Match reason:** {eval_data.get('reason', 'N/A')}\n")
                        else:
                            f.write(f"{i + 1}. ❌ **{book.get('title', 'No title')}**\n")
                            if eval_data.get('reason'):
                                f.write(f"   - **No match:** {eval_data['reason']}\n")

                        if book.get('authors'):
                            f.write(f"   - Authors: {', '.join(book['authors'])}\n")
                        if book.get('publisher'):
                            f.write(f"   - Publisher: {book['publisher']}\n")
                        if book.get('publishedDate'):
                            f.write(f"   - Published: {book['publishedDate']}\n")
                        if book.get('infoLink'):
                            f.write(f"   - [View on Google Books]({book['infoLink']})\n")
                        f.write("\n")

                if result['results']['openlibrary']:
                    f.write("### OpenLibrary Results\n\n")
                    for i, book in enumerate(result['results']['openlibrary']):
                        eval_key = f"openlibrary_{i}"
                        eval_data = gemini_eval.get(eval_key, {})

                        if eval_data.get('match'):
                            f.write(f"{i + 1}. ✅ **{book.get('title', 'No title')}** (Confidence: {eval_data.get('confidence', 0)}%)\n")
                            f.write(f"   - **Match reason:** {eval_data.get('reason', 'N/A')}\n")
                        else:
                            f.write(f"{i + 1}. ❌ **{book.get('title', 'No title')}**\n")
                            if eval_data.get('reason'):
                                f.write(f"   - **No match:** {eval_data['reason']}\n")

                        if book.get('authors'):
                            f.write(f"   - Authors: {', '.join(book['authors'])}\n")
                        if book.get('publisher'):
                            f.write(f"   - Publisher: {book['publisher']}\n")
                        if book.get('publish_year'):
                            f.write(f"   - Year: {book['publish_year']}\n")
                        if book.get('isbn'):
                            f.write(f"   - ISBN: {book['isbn']}\n")
                        f.write("\n")
            else:
                f.write("**Status:** ❌ No results found\n\n")

            f.write("---\n\n")

    print("\n\nSearch complete! Results saved to search_results.md")

    found_count = sum(1 for r in results if r.get('found'))
    searched_count = sum(1 for r in results if r['status'] == 'searched')

    print("\nSummary:")
    print(f"- Total citations: {len(results)}")
    print(f"- Searched: {searched_count}")
    print(f"- Found results: {found_count} ({found_count / searched_count * 100:.1f}% of searched)")


if __name__ == "__main__":
    asyncio.run(main())
