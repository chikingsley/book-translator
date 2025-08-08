#!/usr/bin/env python3
"""Split markdown document into chapters using exact titles from TOC JSON."""

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

from alive_progress import alive_bar
from cerebras.cloud.sdk import Cerebras
from dotenv import load_dotenv
from google import genai

TOC_FILE = "test-book-pdfs/toc-list.json"
INPUT_FILE = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-humancheck-1.md"
OUTPUT_DIR = "test-book-pdfs/chapters_literal"


def load_toc(toc_path: Path) -> list[str]:
    """Load table of contents from JSON file."""
    with open(toc_path, encoding="utf-8") as f:
        return json.load(f)


def find_chapter_positions(content: str, toc_titles: list[str]) -> list[tuple[str, int]]:
    """Find exact positions of chapter titles in content.

    Returns list of (title, position) tuples sorted by position.
    """
    positions: list[tuple[str, int]] = []

    for title in toc_titles:
        found = False

        patterns_to_try = [
            f"# {title}",
            f"#### KOMMENTAR: *{title[11:]}*" if title.startswith("KOMMENTAR:") else None,
            f"### *{title}*",
            f"#### *{title}*",
            f"#### {title}",
            f"### {title}",
            f"## {title}",
        ]

        if title == "Das siebzebnte Kapitel: «Die Wiederkebr»":
            patterns_to_try.insert(1, "### *Das siebzebnte Kapitel: «Die Wiederkebr»*")

        if title == "Das erste Kapitel: «Schimmelberg»":
            patterns_to_try.insert(1, "#### *Das erste Kapitel: «Schimmelberg»*")

        if title == "«Weltbühne Radium»":
            patterns_to_try.insert(0, "#### *«Weltbühne Radium»*")

        for pattern in patterns_to_try:
            if pattern and pattern in content:
                pos = content.find(pattern)
                positions.append((title, pos))
                print(f"Found: {title} at position {pos}")
                found = True
                break

        if not found:
            pos = content.find(title)
            if pos != -1 and (pos == 0 or content[pos - 1] == '\n'):
                positions.append((title, pos))
                print(f"Found (no #): {title} at position {pos}")
            else:
                print(f"Not found: {title}")

    positions.sort(key=lambda x: x[1])
    return positions


def clean_chapter_with_cerebras(content: str, client: Any, model: str = "gpt-oss-120b") -> str | None:
    """Clean chapter ending using Cerebras models."""
    prompt = """Clean up the ending of this text:
    - Remove any stray '#' characters at the end
    - Remove excessive blank lines (keep max 1 blank line at end)
    - Fix any formatting issues at the end
    - Ensure proper ending with single newline

    Return ONLY the cleaned text, nothing else."""

    try:
        params = {
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": content}
            ],
            "model": model,
            "stream": False,
            "temperature": 0.1,
            "top_p": 0.95
        }

        if model == "gpt-oss-120b":
            params["max_completion_tokens"] = 65536
            params["reasoning_effort"] = "low"
        else:  # qwen model
            params["max_completion_tokens"] = 20000
            params["temperature"] = 0.7
            params["top_p"] = 0.8

        response = client.chat.completions.create(**params)

        if response and response.choices and len(response.choices) > 0:
            result = response.choices[0].message.content
            return result.rstrip() + '\n' if result else None
        return None
    except Exception:
        return None


def clean_chapter_with_api(
    content: str,
    title: str,
    gemini_client: Any,
    cerebras_client: Any,
    bar: Any,
    chapter_index: int,
    total_chapters: int,
    estimated_time: float,
    time_estimates: list[float],
) -> str:
    """Clean chapter ending, alternating between APIs on errors."""
    prompt_gemini = """Clean up the ending of this text:
    - Remove any stray '#' characters at the end
    - Remove excessive blank lines (keep max 1 blank line at end)
    - Fix any formatting issues at the end
    - Ensure proper ending with single newline

    Return ONLY the cleaned text, nothing else.

    Text to clean:
    """

    attempt = 0
    while True:
        attempt += 1
        api_choice = attempt % 4

        if api_choice == 1 and gemini_client:
            bar.text = f"Chapter {chapter_index + 1}/{total_chapters}: Gemini Flash-Lite (attempt {attempt})..."

            result: dict[str, Any] = {"text": None, "error": None, "completed": False}

            def api_call(result_dict: dict[str, Any] = result):
                """Run the API call in a separate thread."""
                try:
                    response = gemini_client.models.generate_content(
                        model="gemini-2.5-flash-lite",
                        contents=[prompt_gemini + content]
                    )
                    result_dict["text"] = response.text if response.text else None
                except Exception as e:
                    result_dict["error"] = e
                finally:
                    result_dict["completed"] = True

            api_thread = threading.Thread(target=api_call)
            api_thread.daemon = True
            api_thread.start()

            start_time = time.time()

            while not result["completed"]:
                elapsed = time.time() - start_time

                if time_estimates:
                    estimated_progress = min(elapsed / estimated_time, 1.0)
                    total_progress = (chapter_index + estimated_progress) / total_chapters
                    bar(total_progress)
                    bar.text = f"Chapter {chapter_index + 1}/{total_chapters}: {title[:30]}... {elapsed:.1f}s"
                else:
                    estimated_progress = min(elapsed / estimated_time, 1.0)
                    total_progress = estimated_progress / total_chapters
                    bar(total_progress)
                    bar.text = f"Chapter {chapter_index + 1}/{total_chapters}: Learning timing... {elapsed:.1f}s"

                time.sleep(0.1)
                if elapsed > (estimated_time * 3):
                    bar.text = f"Chapter {chapter_index + 1}: Timeout, switching API..."
                    break

            api_thread.join(timeout=5)

            if not result["error"] and result["text"]:
                return result["text"]

        elif api_choice == 2 and cerebras_client:
            bar.text = f"Chapter {chapter_index + 1}/{total_chapters}: Cerebras GPT (attempt {attempt})..."
            try:
                cerebras_result = clean_chapter_with_cerebras(content, cerebras_client, "gpt-oss-120b")
                if cerebras_result:
                    return cerebras_result
            except Exception:
                pass

        elif api_choice == 3 and cerebras_client:
            bar.text = f"Chapter {chapter_index + 1}/{total_chapters}: Qwen-3 (attempt {attempt})..."
            try:
                qwen_result = clean_chapter_with_cerebras(content, cerebras_client, "qwen-3-235b-a22b-instruct-2507")
                if qwen_result:
                    return qwen_result
            except Exception:
                pass

        elif api_choice == 0 and gemini_client:
            bar.text = f"Chapter {chapter_index + 1}/{total_chapters}: Gemini Flash (attempt {attempt})..."

            result: dict[str, Any] = {"text": None, "error": None, "completed": False}

            def api_call(result_dict: dict[str, Any] = result):
                """Run the API call in a separate thread."""
                try:
                    response = gemini_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[prompt_gemini + content]
                    )
                    result_dict["text"] = response.text if response.text else None
                except Exception as e:
                    result_dict["error"] = e
                finally:
                    result_dict["completed"] = True

            api_thread = threading.Thread(target=api_call)
            api_thread.daemon = True
            api_thread.start()

            start_time = time.time()

            while not result["completed"]:
                elapsed = time.time() - start_time

                if time_estimates:
                    estimated_progress = min(elapsed / estimated_time, 1.0)
                    total_progress = (chapter_index + estimated_progress) / total_chapters
                    bar(total_progress)
                    bar.text = f"Chapter {chapter_index + 1}/{total_chapters}: Gemini Flash... {elapsed:.1f}s"
                else:
                    estimated_progress = min(elapsed / estimated_time, 1.0)
                    total_progress = estimated_progress / total_chapters
                    bar(total_progress)
                    bar.text = f"Chapter {chapter_index + 1}/{total_chapters}: Learning timing... {elapsed:.1f}s"

                time.sleep(0.1)
                if elapsed > (estimated_time * 3):
                    bar.text = f"Chapter {chapter_index + 1}: Timeout, switching API..."
                    break

            api_thread.join(timeout=5)

            if not result["error"] and result["text"]:
                return result["text"]

        if not gemini_client and not cerebras_client:
            return content


def save_chapter(title: str, content: str, index: int, output_dir: Path):
    """Save a single chapter to file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_title = title.replace("/", "-").replace(":", "-").replace("?", "").replace("*", "")
    safe_title = safe_title.replace("<", "").replace(">", "").replace("|", "").replace('"', "")

    filename = f"{index + 1:03d}_{safe_title}.md"
    filepath = output_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath.name


def validate_output(output_dir: Path, toc_titles: list[str]):
    """Validate that output files match TOC entries."""
    print("\n=== Validation ===")

    output_files = sorted(output_dir.glob("*.md"))
    found_count = 0
    total_count = len(output_files)

    for filepath in output_files:
        with open(filepath, encoding="utf-8") as f:
            first_line = f.readline().strip()

        if first_line.startswith("# "):
            first_line = first_line[2:]

        if first_line in toc_titles:
            found_count += 1
        else:
            print(f"✗ {filepath.name}: '{first_line}' NOT in TOC")

    print(f"Validation: {found_count}/{total_count} chapters found in TOC")


def main():
    """Split document into chapters with progress tracking."""
    toc_path = TOC_FILE
    input_path = INPUT_FILE
    output_dir = OUTPUT_DIR

    load_dotenv()
    gemini_key = os.environ.get("GEMINI_API_KEY")
    gemini_client = None
    if gemini_key:
        gemini_client = genai.Client(api_key=gemini_key)
        print("Gemini API initialized for chapter cleanup")
    else:
        print("Warning: GEMINI_API_KEY not found")
    cerebras_key = os.environ.get("CEREBRAS_API_KEY")
    cerebras_client = None
    if cerebras_key:
        cerebras_client = Cerebras(api_key=cerebras_key)
        print("Cerebras API initialized as fallback")
    else:
        print("Warning: CEREBRAS_API_KEY not found")

    if not gemini_client and not cerebras_client:
        print("No API keys found - using simple cleanup")

    print("Loading TOC...")
    toc_titles = load_toc(Path(toc_path))
    print(f"Loaded {len(toc_titles)} titles from TOC")

    print("\nLoading document...")
    with open(input_path, encoding="utf-8") as f:
        content = f.read()
    print(f"Document loaded: {len(content)} characters")

    print("\nFinding chapter positions...")
    positions = find_chapter_positions(content, toc_titles)
    print(f"Found {len(positions)} chapters in document")

    if not positions:
        print("Error: No chapters found!")
        sys.exit(1)

    print("\nExtracting chapters...")
    chapters: list[tuple[str, str]] = []
    for i, (title, start_pos) in enumerate(positions):
        if i + 1 < len(positions):
            end_pos = positions[i + 1][1]
            chapter_content = content[start_pos:end_pos].rstrip()
        else:
            chapter_content = content[start_pos:].strip()

        if not gemini_client and not cerebras_client:
            if chapter_content.endswith('\n#'):
                chapter_content = chapter_content[:-2].rstrip() + '\n'
            elif chapter_content.endswith('#'):
                chapter_content = chapter_content[:-1].rstrip() + '\n'

        chapters.append((title, chapter_content))

    total_chapters = len(chapters)
    print(f"\nProcessing and saving {total_chapters} chapters...")

    time_estimates: list[float] = []
    overall_start_time = time.time()
    chapters_processed = 0

    with alive_bar(
        manual=True,
        title="Chapter Processing",
        dual_line=True,
        refresh_secs=0.05,
        calibrate=1,
        length=50,
        stats=False
    ) as bar:  # type: ignore[misc]
        for chapter_index, (title, chapter_content) in enumerate(chapters):
            chapter_start_time = time.time()

            if time_estimates:
                recent_estimates = time_estimates[-5:] if len(time_estimates) > 5 else time_estimates
                estimated_time = sum(recent_estimates) / len(recent_estimates)
            else:
                estimated_time = 2.0

            if gemini_client or cerebras_client:
                cleaned_content = clean_chapter_with_api(
                    chapter_content,
                    title,
                    gemini_client,
                    cerebras_client,
                    bar,
                    chapter_index,
                    total_chapters,
                    estimated_time,
                    time_estimates,
                )
            else:
                cleaned_content = chapter_content

            filename = save_chapter(title, cleaned_content, chapter_index, Path(output_dir))

            actual_time = time.time() - chapter_start_time
            time_estimates.append(actual_time)
            chapters_processed += 1

            actual_progress = (chapter_index + 1) / total_chapters
            bar(actual_progress)
            overall_elapsed = time.time() - overall_start_time
            current_rate = chapters_processed / overall_elapsed if overall_elapsed > 0 else 0
            remaining_chapters = total_chapters - chapters_processed

            if remaining_chapters > 0 and current_rate > 0:
                eta_seconds = remaining_chapters / current_rate
                if eta_seconds < 60:
                    eta_text = f"ETA: {eta_seconds:.0f}s"
                else:
                    minutes = int(eta_seconds // 60)
                    seconds = int(eta_seconds % 60)
                    eta_text = f"ETA: {minutes}m {seconds}s"
            else:
                eta_text = "Complete!"

            bar.text = f"Saved: {filename} ({actual_time:.1f}s) | {current_rate:.2f} ch/s | {eta_text}"
            time.sleep(0.1)

    validate_output(Path(output_dir), toc_titles)
    print("\n=== Summary ===")
    print(f"Chapters processed: {chapters_processed}")
    print(f"Output directory: {output_dir}")

    if time_estimates:
        avg_time = sum(time_estimates) / len(time_estimates)
        print(f"Average time per chapter: {avg_time:.1f}s")

    total_elapsed = time.time() - overall_start_time
    final_rate = chapters_processed / total_elapsed if total_elapsed > 0 else 0
    print(f"Overall processing rate: {final_rate:.1f} chapters/s")
    print(f"Total time: {total_elapsed:.1f}s")


if __name__ == "__main__":
    main()
