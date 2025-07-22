import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pymupdf
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel


class ChapterSection(BaseModel):
    """Represents a section within a chapter."""

    title: str
    page: int | None = None


class ChapterMetadata(BaseModel):
    """Metadata for a single chapter."""

    number: int
    title: str
    page: int | None = None
    sections: list[ChapterSection] = []


class TableOfContents(BaseModel):
    """Structured representation of a book's table of contents."""

    book_title: str = "Untitled Book"
    author: str = "Unknown Author"
    chapters: list[ChapterMetadata] = []
    total_pages: int | None = None


class ChapterContent(BaseModel):
    """Structured output for chapter content extraction."""

    extracted_text: str
    summary: str
    key_terms: list[str] = []
    notes: str = ""


class BookProcessor:
    def __init__(self, api_key: str):
        """Initialize with Gemini 2.5 Flash for text extraction."""
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash"
        self.toc: TableOfContents = TableOfContents()
        self.toc_entries: list[dict[str, Any]] = [] 
        self.project_dir = Path(".")
        self._uploaded_files: dict[str, Any] = {}
        self.continuous_mode = False

    def _generate_with_retry(self, prompt: str | list[Any], schema: type[BaseModel]):
        """Generate content with retry logic and structured output."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": schema,
                    }
                )
                if response.text:
                    return json.loads(response.text)
                else:
                    raise ValueError("Empty response from API")
            except Exception as e:
                if "rate limit" in str(e).lower() or "429" in str(e):
                    wait_time = (2**attempt) * 5  
                    print(f"⏳ Rate limit hit. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    if attempt == max_retries - 1:
                        raise
                else:
                    raise
        raise Exception("Failed to generate content after multiple retries.")

    def extract_toc_from_pdf(self, pdf_path: str) -> bool:
        """Extract TOC using PyMuPDF. Returns True if successful."""
        print("📚 Extracting Table of Contents from PDF...")
        
        try:
            document = pymupdf.open(pdf_path)
            toc = document.get_toc()  # type: ignore[attr-defined]
            document.close()
            
            if not toc:
                print("❌ No table of contents found in PDF!")
                print("Please add bookmarks manually using PDFgear or similar tool.")
                print("Then run the book extractor again.")
                return False
                
            self.toc_entries = []
            for i, (level, title, page) in enumerate(toc):
                self.toc_entries.append({
                    'sequence': i + 1,
                    'level': level,
                    'title': title,
                    'page': page
                })
                
            print(f"✅ Found {len(self.toc_entries)} entries in table of contents")
            self._save_toc()
            return True
            
        except Exception as e:
            print(f"❌ Error reading PDF: {e}")
            return False

    def _save_toc(self) -> None:
        """Auto-save TOC when updated."""
        output_dir = self.project_dir / "output"
        output_dir.mkdir(exist_ok=True)

        with open(output_dir / "table_of_contents.json", "w", encoding="utf-8") as f:
            json.dump(self.toc_entries, f, indent=2, ensure_ascii=False)

        with open(output_dir / "table_of_contents.md", "w", encoding="utf-8") as f:
            f.write("# Table of Contents\n\n")
            
            for entry in self.toc_entries:
                level = entry['level']
                indent = "  " * (level - 1)
                f.write(f"{indent}- {entry['title']} (Page {entry['page']})\n")

        print("✅ TOC saved automatically!")


    def save_chapter(self, chapter_data: dict[str, Any]) -> None:
        """Save chapter with auto-updating project structure."""
        sequence = chapter_data.get('sequence', chapter_data.get('chapter_num', 1))
        title = chapter_data.get('title', chapter_data.get('chapter_title', 'untitled'))
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:50]  
        
        folder_name = f"{sequence:03d}_{safe_title}"
        chapter_dir = self.project_dir / "output" / folder_name
        chapter_dir.mkdir(parents=True, exist_ok=True)

        files = {
            "content.md": chapter_data.get("extracted_text", ""),
            "metadata.json": json.dumps(
                {
                    "sequence": chapter_data.get("sequence", chapter_data.get("chapter_num", 0)),
                    "title": chapter_data.get("title", chapter_data.get("chapter_title", "")),
                    "page": chapter_data.get("page", 0),
                    "summary": chapter_data.get("summary", ""),
                    "key_terms": chapter_data.get("key_terms", []),
                    "notes": chapter_data.get("notes", ""),
                    "processed_at": chapter_data["processed_at"],
                },
                indent=2,
            ),
        }

        for filename, content in files.items():
            with open(chapter_dir / filename, "w", encoding="utf-8") as f:
                f.write(content)

        sequence = chapter_data.get("sequence", chapter_data.get("chapter_num", 0))
        self._update_progress(sequence)

        self._update_combined_extraction(chapter_data)

    def _update_progress(self, chapter_num: int) -> None:
        """Track progress and generate overview."""
        progress_file = self.project_dir / "output" / "progress.json"

        if progress_file.exists():
            with open(progress_file) as f:
                progress = json.load(f)
        else:
            progress = {"completed_chapters": [], "last_updated": ""}

        completed_chapters = progress.get("completed_chapters", [])
        if isinstance(completed_chapters, list) and chapter_num not in completed_chapters:
            completed_chapters.append(chapter_num)
            completed_chapters.sort()
            progress["completed_chapters"] = completed_chapters

        progress["last_updated"] = datetime.now().isoformat()

        with open(progress_file, "w") as f:
            json.dump(progress, f, indent=2)

        total_entries = len(self.toc_entries) if self.toc_entries else len(self.toc.chapters)
        print(
            f"📊 Progress: {len(progress['completed_chapters'])}/{total_entries} entries"
        )

    def _update_combined_extraction(self, chapter_data: dict[str, Any]) -> None:
        """Append chapter to combined extracted file."""
        combined_file = self.project_dir / "output" / "full_content.md"

        if not combined_file.exists():
            header = "# Full Book Content\n\n"
            header += "---\n\n"
            combined_file.write_text(header, encoding="utf-8")

        title = chapter_data.get('title', chapter_data.get('chapter_title', 'Untitled'))
        chapter_content = f"\n## {title}\n\n"
        chapter_content += chapter_data.get("extracted_text", "")
        chapter_content += "\n\n---\n"


        with open(combined_file, "a", encoding="utf-8") as f:
            f.write(chapter_content)


    def process_pdf_direct(self, pdf_path: str) -> None:
        """Process PDF directly with Gemini."""
        if not self.extract_toc_from_pdf(pdf_path):
            sys.exit(1)  
            
        print("📄 Uploading PDF to Gemini...")
        if pdf_path not in self._uploaded_files:
            self._uploaded_files[pdf_path] = self.client.files.upload(file=pdf_path)
        pdf_file = self._uploaded_files[pdf_path]

        for entry in self.toc_entries:
            print(f"\n📖 Processing: {entry['title']} (Page {entry['page']})")

            entry_prompt = f"""
            Extract the content for: '{entry['title']}'
            This content starts on page {entry['page']}.

            Instructions:
            1. Find where this section starts (page {entry['page']})
            2. Extract ALL text until the next major section begins
            3. Preserve formatting and structure
            4. Format as clean Markdown with proper headings
            """
            result: dict[str, Any] | None = None
            try:
                result_data = self._generate_with_retry(
                    [entry_prompt, pdf_file], schema=ChapterContent
                )
                result = ChapterContent.model_validate(result_data).model_dump()

                result["sequence"] = entry['sequence']
                result["title"] = entry['title']
                result["page"] = entry['page']
                result["processed_at"] = datetime.now().isoformat()
                self.save_chapter(result)

            except Exception as e:
                print(f"❌ Chapter processing error: {e}")
                result = {
                    "extracted_text": f"Extraction failed. Error: {e}",
                    "summary": "Could not parse response",
                    "notes": str(e),
                    "sequence": entry['sequence'],
                    "title": entry['title'],
                    "page": entry['page'],
                    "processed_at": datetime.now().isoformat(),
                }
                self.save_chapter(result)

            if not self.continuous_mode:
                action = input(
                    "\n[Enter] Continue | [r] Review | [c] Continuous mode | [q] Quit: "
                ).lower()
                if action == "r" and result:
                    print(
                        f"\n--- Extracted content preview ---\n{result.get('extracted_text', '')[:500]}..."
                    )
                    input("\nPress Enter to continue...")
                elif action == "c":
                    self.continuous_mode = True
                    print(
                        "🚀 Continuous mode activated! Press Ctrl+C to pause at next chapter."
                    )
                elif action == "q":
                    break
            else:
                print("✅ Chapter saved. Continuing...")
                try:
                    time.sleep(2)
                except KeyboardInterrupt:
                    print("\n⏸️ Paused. Switching back to interactive mode.")
                    self.continuous_mode = False


def main() -> None:
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: book-extractor <pdf_file>")
        print("Example: book-extractor book.pdf")
        sys.exit(1)

    pdf_file = sys.argv[1]

    if not os.path.exists(pdf_file):
        print(f"❌ File not found: {pdf_file}")
        sys.exit(1)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env file")
        sys.exit(1)

    processor = BookProcessor(api_key=api_key)

    print(f"📚 Processing: {pdf_file}")

    processor.process_pdf_direct(pdf_file)


if __name__ == "__main__":
    main()
