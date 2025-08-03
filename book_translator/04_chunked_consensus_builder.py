"""Build consensus from multiple OCR outputs using chunked processing with Gemini 2.5 Flash."""

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from alive_progress import alive_bar
from dotenv import load_dotenv
from google import genai

MISTRAL_FILE = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-mistral.md"
GEMINI_FILE = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-gemini.md"
HUMANCHECK_FILE = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-humancheck-1.md"
OUTPUT_FILE = "test-book-pdfs/consensus_final.md"
DISPUTES_FILE = "test-book-pdfs/disputes_review.md"
PROGRESS_FILE = "consensus_progress.json"
CHUNK_SIZE = 25


def count_tokens(client: genai.Client, *texts: str) -> int:
    """Count tokens for all input texts combined."""
    combined_text = "\n\n".join(texts)
    try:
        token_count = client.models.count_tokens(
            model="gemini-2.5-flash", contents=[combined_text]
        )
        return token_count.total_tokens or 0
    except Exception:
        return int(len(combined_text.split()) * 1.3)


def extract_page_chunks(content: str, chunk_size: int = CHUNK_SIZE) -> list[tuple[str, str, int, int]]:
    """Extract content in page-based chunks."""
    page_pattern = r'^# Page (\d+)$'
    pages: list[tuple[int, str]] = []
    
    lines = content.split('\n')
    current_page = 1
    current_content: list[str] = []
    
    for line in lines:
        page_match = re.match(page_pattern, line)
        if page_match:
            if current_content:
                pages.append((current_page, '\n'.join(current_content)))
            current_page = int(page_match.group(1))
            current_content = [line]
        else:
            current_content.append(line)
    
    if current_content:
        pages.append((current_page, '\n'.join(current_content)))
    
    chunks: list[tuple[str, str, int, int]] = []
    for i in range(0, len(pages), chunk_size):
        chunk_pages = pages[i:i+chunk_size]
        chunk_content = '\n\n'.join([content for _, content in chunk_pages])
        start_page = chunk_pages[0][0]
        end_page = chunk_pages[-1][0]
        chunk_id = f"pages_{start_page:03d}_{end_page:03d}"
        chunks.append((chunk_id, chunk_content, start_page, end_page))
    
    return chunks


def extract_human_chunks(content: str, target_chunks: list[tuple[str, str, int, int]]) -> list[tuple[str, str]]:
    """Extract human content aligned with page-based chunks."""
    sections = re.split(r'\n## ', content)
    if not sections[0].startswith('##'):
        sections[0] = '## ' + sections[0] if sections else content
    
    total_human_chars = len(content)
    total_target_pages = sum(end - start + 1 for _, _, start, end in target_chunks)
    
    chunks: list[tuple[str, str]] = []
    section_idx = 0
    current_chars = 0
    
    for chunk_id, _, start_page, end_page in target_chunks:
        target_chars = int((end_page - start_page + 1) / total_target_pages * total_human_chars)
        
        chunk_content = ""
        while section_idx < len(sections) and current_chars < target_chars:
            if chunk_content:
                chunk_content += "\n## "
            chunk_content += sections[section_idx]
            current_chars += len(sections[section_idx])
            section_idx += 1
        
        current_chars = 0
        chunks.append((chunk_id, chunk_content))
    
    return chunks


def build_consensus(client: genai.Client, mistral_text: str, gemini_text: str, humancheck_text: str, chunk_id: str) -> str:
    """Build consensus from three versions using Gemini Flash."""
    consensus_prompt = f"""
    Compare these three versions of the same German text (Chunk: {chunk_id}) and create a consensus version.
    
    Instructions:
    1. When all three versions agree exactly → use that text
    2. When two versions agree and one differs → use the majority version
    3. When all three have different versions → mark as: **[DISPUTE-CRITICAL: Mistral="X" | Gemini="Y" | Human="Z"]**
    4. When they have minor differences (punctuation, capitalization) → choose the most likely correct version and mark as: **[DISPUTE-MINOR: using X version]**
    5. If one version has text that's missing in others → mark as: **[MISSING-IN-VERSION: text]**
    6. Pay special attention to:
       - German quotation marks (»« vs «» vs "")
       - Umlauts (ä, ö, ü)
       - Compound words (should they be joined or separated?)
       - Proper names and capitalization
       - Italics formatting (*text* vs _text_)
    
    Priority order for conflicts:
    1. Human-checked version (highest quality)
    2. Majority consensus of any two versions
    3. Best German grammar/spelling when all differ
    
    Output only the consensus text, with disputes clearly marked.
    Do not add any introduction or explanation.
    
    Mistral version:
    ---
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                consensus_prompt,
                mistral_text,
                "\n\nGemini version:\n---\n",
                gemini_text,
                "\n\nHuman-checked version:\n---\n",
                humancheck_text,
                "\n\nConsensus version:"
            ]
        )
        if response.text:
            return response.text.strip()
        return f"Error: No consensus generated for {chunk_id}"
    except Exception as e:
        print(f"Error building consensus for {chunk_id}: {e}")
        return f"Error processing {chunk_id}: {e!s}"


def extract_disputes(consensus_text: str) -> list[str]:
    """Extract all dispute markings from consensus text."""
    dispute_patterns = [
        r'\*\*\[DISPUTE-CRITICAL:.*?\]\*\*',
        r'\*\*\[DISPUTE-MINOR:.*?\]\*\*',
        r'\*\*\[MISSING-IN-.*?\]\*\*'
    ]
    
    disputes: list[str] = []
    for pattern in dispute_patterns:
        matches = re.findall(pattern, consensus_text, re.DOTALL)
        disputes.extend(matches)
    
    return disputes


def load_progress() -> dict[str, Any]:
    """Load progress from previous session."""
    if Path(PROGRESS_FILE).exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"completed_chunks": [], "current_chunk": 0, "total_chunks": 0}


def save_progress(progress: dict[str, Any]) -> None:
    """Save current progress."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def process_all_chunks(client: genai.Client, mistral_chunks: list[Any], gemini_chunks: list[Any], human_chunks: list[Any]) -> tuple[list[str], list[str], dict[str, Any]]:
    """Process all chunks and return consensus results, disputes, and timing stats."""
    progress = load_progress()
    total_chunks = len(mistral_chunks)
    progress["total_chunks"] = total_chunks
    
    consensus_results: list[str] = []
    all_disputes: list[str] = []
    
    # Time tracking for progress estimation
    chunk_times: list[float] = []
    chunks_completed = len(progress["completed_chunks"])
    overall_start_time = time.time()
    
    print(f"Processing {total_chunks} chunks...")
    
    # Write headers if this is the first run
    if not progress["completed_chunks"]:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(f"# {Path(OUTPUT_FILE).stem}\n\n")
            f.write("## Consensus built from Mistral, Gemini, and human-checked versions\n")
            f.write("## Disputes marked for review - see disputes_review.md\n\n")
            f.write("---\n\n")
        
        with open(DISPUTES_FILE, 'w', encoding='utf-8') as f:
            f.write("# Disputes Review\n\n")
            f.write(f"Processing {total_chunks} chunks...\n\n")
            f.write("## Dispute Types:\n")
            f.write("- **[DISPUTE-CRITICAL]**: All three versions differ - manual decision needed\n")
            f.write("- **[DISPUTE-MINOR]**: Minor differences resolved automatically\n") 
            f.write("- **[MISSING-IN-X]**: Content missing in one version\n\n")
            f.write("---\n\n")
    
    with alive_bar(
        manual=True,
        title="Building Consensus",
        dual_line=True,
        refresh_secs=0.05,
        calibrate=1,
        length=50,
        stats=False
    ) as bar:  # type: ignore[misc]
        for i, ((chunk_id, mistral_text, start_page, end_page), (_, gemini_text, _, _), (_, human_text)) in enumerate(zip(mistral_chunks, gemini_chunks, human_chunks, strict=False)):
            
            if chunk_id in progress["completed_chunks"]:
                continue
            
            chunk_start_time = time.time()
            
            # Update progress
            actual_progress = (chunks_completed + 0.5) / total_chunks
            bar(actual_progress)
            
            # Calculate current rate and ETA
            if chunks_completed > 0:
                overall_elapsed = time.time() - overall_start_time
                current_rate = chunks_completed / overall_elapsed
                remaining_chunks = total_chunks - chunks_completed
                
                if current_rate > 0:
                    eta_seconds = remaining_chunks / current_rate
                    if eta_seconds < 60:
                        eta_text = f"ETA: {eta_seconds:.0f}s"
                    else:
                        minutes = int(eta_seconds // 60)
                        seconds = int(eta_seconds % 60)
                        eta_text = f"ETA: {minutes}m {seconds}s"
                else:
                    eta_text = "ETA: calculating..."
            else:
                current_rate = 0
                eta_text = "ETA: calculating..."
            
            # Update bar text
            bar.text = f"Chunk {i+1}/{total_chunks} ({chunk_id}): Pages {start_page}-{end_page} | {current_rate:.2f} chunks/s | {eta_text}"
            
            tokens = count_tokens(client, mistral_text, gemini_text, human_text)
            if tokens > 50000:
                bar.text = f"⚠️  {chunk_id}: {tokens:,} tokens - may hit limits | Processing..."
            
            consensus_text = build_consensus(client, mistral_text, gemini_text, human_text, chunk_id)
            
            chunk_disputes = extract_disputes(consensus_text)
            if chunk_disputes:
                dispute_summary = f"\n## Chunk {chunk_id} (Pages {start_page}-{end_page})\n"
                dispute_summary += f"Found {len(chunk_disputes)} disputes:\n\n"
                for dispute in chunk_disputes:
                    dispute_summary += f"- {dispute}\n"
                all_disputes.append(dispute_summary)
                
                # Write disputes incrementally
                with open(DISPUTES_FILE, 'a', encoding='utf-8') as f:
                    f.write(dispute_summary)
            
            chunk_header = f"\n<!-- CHUNK: {chunk_id} (Pages {start_page}-{end_page}) -->\n"
            consensus_results.append(chunk_header + consensus_text)
            
            # Write consensus incrementally
            with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                f.write(chunk_header + consensus_text + "\n")
            
            # Update progress tracking
            chunk_time = time.time() - chunk_start_time
            chunk_times.append(chunk_time)
            chunks_completed += 1
            
            progress["completed_chunks"].append(chunk_id)
            progress["current_chunk"] = i + 1
            save_progress(progress)
            
            # Update final progress
            actual_progress = chunks_completed / total_chunks
            bar(actual_progress)
            
            # Update bar with completion info
            dispute_text = f"{len(chunk_disputes)} disputes" if chunk_disputes else "no disputes"
            bar.text = f"✓ {chunk_id}: {chunk_time:.1f}s | {dispute_text} | {current_rate:.2f} chunks/s | {eta_text}"
            
            # Brief pause to show completion status
            time.sleep(0.2)
    
    # Return results with timing stats
    timing_stats = {
        "chunk_times": chunk_times,
        "overall_start_time": overall_start_time,
        "total_elapsed": time.time() - overall_start_time
    }
    
    return consensus_results, all_disputes, timing_stats


def main() -> None:
    """Build consensus from OCR outputs using chunked processing."""
    load_dotenv()
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found")
        return
    
    google_api_key = os.environ.pop("GOOGLE_API_KEY", None)
    client = genai.Client(api_key=api_key)
    if google_api_key:
        os.environ["GOOGLE_API_KEY"] = google_api_key
    
    print("Building chunked consensus from three book versions...")
    print(f"Chunk size: {CHUNK_SIZE} pages")
    
    files_to_load = [
        (MISTRAL_FILE, "Mistral"),
        (GEMINI_FILE, "Gemini"), 
        (HUMANCHECK_FILE, "Human-checked")
    ]
    
    file_contents: dict[str, str] = {}
    for filepath, name in files_to_load:
        print(f"Reading {name} version: {filepath}")
        try:
            with open(filepath, encoding='utf-8') as f:
                file_contents[name.lower().replace('-', '')] = f.read()
        except FileNotFoundError:
            print(f"Error: {filepath} not found")
            return
    
    print(f"\nExtracting chunks ({CHUNK_SIZE} pages each)...")
    
    mistral_chunks = extract_page_chunks(file_contents["mistral"], CHUNK_SIZE)
    gemini_chunks = extract_page_chunks(file_contents["gemini"], CHUNK_SIZE)
    human_chunks = extract_human_chunks(file_contents["humanchecked"], mistral_chunks)
    
    print(f"Found {len(mistral_chunks)} chunks in Mistral version")
    print(f"Found {len(gemini_chunks)} chunks in Gemini version")
    print(f"Aligned {len(human_chunks)} chunks in Human version")
    
    min_chunks = min(len(mistral_chunks), len(gemini_chunks), len(human_chunks))
    mistral_chunks = mistral_chunks[:min_chunks]
    gemini_chunks = gemini_chunks[:min_chunks]
    human_chunks = human_chunks[:min_chunks]
    
    print(f"Processing {min_chunks} aligned chunks...")
    
    consensus_results, all_disputes, timing_stats = process_all_chunks(client, mistral_chunks, gemini_chunks, human_chunks)
    
    # Update disputes file with final count
    if Path(DISPUTES_FILE).exists():
        with open(DISPUTES_FILE, encoding='utf-8') as f:
            disputes_content = f.read()
        
        # Replace the processing line with final count
        disputes_content = disputes_content.replace(
            f"Processing {len(mistral_chunks)} chunks...",
            f"Found {len(all_disputes)} chunks with disputes requiring review."
        )
        
        with open(DISPUTES_FILE, 'w', encoding='utf-8') as f:
            f.write(disputes_content)
    
    if Path(PROGRESS_FILE).exists():
        Path(PROGRESS_FILE).unlink()
    
    # Calculate final statistics
    total_elapsed = timing_stats["total_elapsed"]
    chunk_times = timing_stats["chunk_times"]
    
    if total_elapsed > 0:
        final_rate = min_chunks / total_elapsed
    else:
        final_rate = 0
    
    print("\n✅ Consensus building complete!")
    print(f"📖 Final book: {OUTPUT_FILE}")
    print(f"⚠️  Disputes: {DISPUTES_FILE}")
    print(f"📊 Total chunks processed: {len(consensus_results)}")
    print(f"🔍 Chunks with disputes: {len(all_disputes)}")
    
    # Print timing statistics
    if chunk_times:
        avg_time = sum(chunk_times) / len(chunk_times)
        print("\n⏱  Performance Statistics:")
        print(f"   - Total time: {total_elapsed/60:.1f} minutes")
        print(f"   - Average time per chunk: {avg_time:.1f}s")
        print(f"   - Overall processing rate: {final_rate:.2f} chunks/s")
    
    if all_disputes:
        print(f"\n👀 Review {DISPUTES_FILE} to resolve remaining conflicts")
    else:
        print("\n🎉 No disputes found - consensus is clean!")


if __name__ == "__main__":
    main()