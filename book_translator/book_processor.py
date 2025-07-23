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
        
        # Find next available output version
        self.output_dir = self._get_next_output_dir()
    
    def _get_next_output_dir(self) -> Path:
        """Find the next available output_vX directory."""
        base_dir = self.project_dir
        version = 1
        
        # Find all existing output_vX directories
        while (base_dir / f"output_v{version}").exists():
            version += 1
        
        output_dir = base_dir / f"output_v{version}"
        print(f"📁 Using output directory: {output_dir}")
        return output_dir

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
        self.output_dir.mkdir(parents=True, exist_ok=True)

        with open(self.output_dir / "table_of_contents.json", "w", encoding="utf-8") as f:
            json.dump(self.toc_entries, f, indent=2, ensure_ascii=False)

        with open(self.output_dir / "table_of_contents.md", "w", encoding="utf-8") as f:
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
        chapter_dir = self.output_dir / folder_name
        chapter_dir.mkdir(parents=True, exist_ok=True)

        # Fix escaped newlines in extracted text
        extracted_text = chapter_data.get("extracted_text", "")
        extracted_text = extracted_text.replace("\\n", "\n")
        
        files = {
            "content.md": extracted_text,
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
        progress_file = self.output_dir / "progress.json"

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
        combined_file = self.output_dir / "full_content.md"

        if not combined_file.exists():
            header = "# Full Book Content\n\n"
            header += "---\n\n"
            combined_file.write_text(header, encoding="utf-8")

        # Fix escaped newlines in extracted text
        extracted_text = chapter_data.get("extracted_text", "")
        extracted_text = extracted_text.replace("\\n", "\n")
        
        chapter_content = "\n"
        chapter_content += extracted_text
        chapter_content += "\n\n"


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

        for i, entry in enumerate(self.toc_entries):
            # Get the next entry to use as boundary
            next_entry = self.toc_entries[i + 1] if i + 1 < len(self.toc_entries) else None
            
            if next_entry:
                print(f"\n📖 Processing: {entry['title']} (Page {entry['page']} → stops before '{next_entry['title']}' on page {next_entry['page']})")
            else:
                print(f"\n📖 Processing: {entry['title']} (Page {entry['page']} → end of document)")

            # Check if this is likely a front matter page without visible title
            is_front_matter = any(keyword in entry['title'].lower() for keyword in [
                'titelblatt', 'title page', 'cover',
                'urheberrecht', 'copyright', 'publishing',
                'inhalt', 'contents', 'toc'
            ])
            
            if is_front_matter:
                # Special handling for pages without visible titles
                entry_prompt = f"""
                For page {entry['page']}, create a markdown document that preserves the visual layout.
                
                First line should be: # {entry['title']}
                
                Then reproduce the page content with proper line breaks between each line of text.
                If the original has text on separate lines, put them on separate lines in markdown.
                Do not combine lines into a single paragraph.
                """
            else:
                # Regular handling for chapters/sections with visible titles
                entry_prompt = f"""
                Extract content starting from '{entry['title']}' on page {entry['page']}."""
                
                if next_entry:
                    entry_prompt += f"""
                Stop extraction when you encounter '{next_entry['title']}' on page {next_entry['page']}.
                Do not include the next section's title or content."""
                else:
                    entry_prompt += """
                This is the last section - extract until the end of the document."""
                    
                entry_prompt += f"""

                Instructions:
                1. Start extracting from where '{entry['title']}' appears on page {entry['page']}
                2. Include the section title with proper markdown heading
                3. Extract all content that belongs to this section
                4. Stop before the next section begins (do not include it)
                5. Preserve formatting and structure
                6. Format as clean Markdown
                """
            result: dict[str, Any] | None = None
            retry_count = 0
            
            while True:
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
                    break  # Success - exit the retry loop

                except Exception as e:
                    retry_count += 1
                    print(f"❌ Chapter processing error (attempt {retry_count}): {e}")
                    print("🔄 Retrying...")
                    
                    # Wait a bit before retrying
                    time.sleep(2)
                    continue  # Try again

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
