#!/usr/bin/env -S uv run python
"""Evaluate OCR formatting quality against reference using OpenRouter LLM analysis."""

import glob
import os

from dotenv import load_dotenv
from openai import OpenAI

# Import FORMAT_PROMPT from 02_ocr_formatter.py
try:
    import importlib.util
    
    current_dir = os.path.dirname(__file__)
    formatter_path = os.path.join(current_dir, "02_ocr_formatter.py")
    spec = importlib.util.spec_from_file_location("ocr_formatter", formatter_path)
    if spec and spec.loader:
        ocr_formatter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ocr_formatter)
        _format_prompt: str = ocr_formatter.FORMAT_PROMPT
    else:
        raise ImportError("Could not load ocr_formatter module")
except ImportError:
    # Fallback - define inline if import fails
    _format_prompt = "FORMAT_PROMPT import failed - using fallback"

FORMAT_PROMPT = _format_prompt

# ============== CONFIGURATION ==============
REFERENCE_FILE = "test-book-pdfs/citations/pages_1-13_final.md"
OUTPUT_FILE = "test-book-pdfs/quality_evaluation_results.md"
GEMINI_FILES = [
    "test-book-pdfs/gemini_formatted.md",
    "test-book-pdfs/gemini_formatted_1.md",
]
# ==========================================


def get_llm_evaluation(formatted_content: str, reference_content: str, filename: str) -> str:
    """Get LLM analysis of formatting quality against reference."""
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "Error: OPENROUTER_API_KEY environment variable not set"
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    

    prompt = f"""Evaluate this OCR formatting attempt against the reference version:

FORMATTED VERSION ({filename}):
{formatted_content}

REFERENCE VERSION (gold standard):
{reference_content}

Analyze and rate 1-10:
1. **Content Accuracy** - Are all words/text preserved correctly?
2. **Formatting Quality** - Page breaks, headers, structure, markdown formatting
3. **German Text Handling** - Umlauts, compound words, quotation marks (»« vs \"\")
4. **Layout Preservation** - Paragraphs, spacing, indentation
5. **Citation/Reference Format** - Footnotes, page numbers, special formatting

For each category, provide:
- Score (1-10)
- Specific issues found
- Formatting mistakes to fix

**CURRENT FORMATTING PROMPT:**
{FORMAT_PROMPT}

End with:
- Overall Score: X/10
- Key improvements needed
- **PROMPT RECOMMENDATIONS:** Based on the issues found, suggest 2-3 specific improvements to the formatting prompt above. Focus on practical changes that would fix the problems you identified, not perfection."""

    try:
        completion = client.chat.completions.create(
            model="openrouter/horizon-alpha",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content or "No content returned"
    except Exception as e:
        return f"Error calling OpenRouter API: {e!s}"



def check_already_evaluated(output_file: str, filename: str) -> bool:
    """Check if a file has already been evaluated in the output file."""
    if not os.path.exists(output_file):
        return False
    
    try:
        with open(output_file, encoding='utf-8') as f:
            content = f.read()
        
        # Look for the filename as a header in the results
        return f". {filename}" in content
    except Exception:
        return False


def main() -> None:
    """Evaluate all Gemini formatted files against reference."""
    # Handle path resolution for different execution contexts
    import os
    if not os.path.exists("test-book-pdfs"):
        # We're probably running from book_translator subdirectory
        base_path = ".."
    else:
        # We're running from project root
        base_path = "."
    
    reference_file = os.path.join(base_path, REFERENCE_FILE)
    output_file = os.path.join(base_path, OUTPUT_FILE)
    
    print("OCR Formatting Quality Evaluator")
    print("="*80)
    print(f"Reference file: {reference_file}")
    print(f"Output file: {output_file}")
    
    # Check if reference exists
    if not os.path.exists(reference_file):
        print(f"Error: Reference file {reference_file} not found")
        return
    
    # Find all gemini formatted files (including numbered ones)
    all_gemini_files: list[str] = []
    patterns = [
        os.path.join(base_path, "test-book-pdfs/gemini_formatted.md"), 
        os.path.join(base_path, "test-book-pdfs/gemini_formatted_*.md")
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        all_gemini_files.extend(matches)
    
    # Sort to ensure consistent order
    all_gemini_files.sort()
    
    if not all_gemini_files:
        print("No gemini_formatted*.md files found")
        return
    
    print(f"Found {len(all_gemini_files)} files to evaluate:")
    
    # Filter out already evaluated files
    files_to_evaluate: list[str] = []
    for f in all_gemini_files:
        filename = os.path.basename(f)
        if check_already_evaluated(output_file, filename):
            print(f"  - {filename} (ALREADY EVALUATED - SKIPPING)")
        else:
            print(f"  - {filename} (NEW)")
            files_to_evaluate.append(f)
    
    if not files_to_evaluate:
        print("\nAll files have already been evaluated!")
        print(f"Check existing results in: {output_file}")
        return
    
    print(f"\nEvaluating {len(files_to_evaluate)} new files...")
    
    # Append to existing output file or create new one
    mode = 'a' if os.path.exists(output_file) else 'w'
    with open(output_file, mode, encoding='utf-8') as out:
        if mode == 'w':
            # Write header for new file
            out.write("# OCR Formatting Quality Evaluation Results\n\n")
            out.write(f"**Reference file:** {reference_file}\n")
            out.write(f"**Evaluation date:** {os.popen('date').read().strip()}\n")
            out.write(f"**Files evaluated:** {len(all_gemini_files)}\n\n")
        else:
            # Add timestamp for new evaluations
            out.write(f"\n\n---\n\n**New evaluations added:** {os.popen('date').read().strip()}\n\n")
        
        # Get starting number for new evaluations
        if mode == 'a':
            start_num = len(all_gemini_files) - len(files_to_evaluate) + 1
        else:
            start_num = 1
        
        # Evaluate each new file and write to output
        for i, formatted_file in enumerate(files_to_evaluate, start_num):
            print(f"\nEvaluating {i-start_num+1}/{len(files_to_evaluate)}: {os.path.basename(formatted_file)}")
            
            try:
                with open(formatted_file, encoding='utf-8') as f:
                    formatted = f.read()
            except FileNotFoundError:
                print(f"Error: {formatted_file} not found")
                continue
            
            try:
                with open(reference_file, encoding='utf-8') as f:
                    reference = f.read()
            except FileNotFoundError:
                print(f"Error: {reference_file} not found")
                return
            
            # Write file section to output
            out.write(f"## {i}. {os.path.basename(formatted_file)}\n\n")
            
            # Basic statistics
            out.write("**Statistics:**\n")
            out.write(f"- Formatted length: {len(formatted)} chars\n")
            out.write(f"- Reference length: {len(reference)} chars\n")
            out.write(f"- Length difference: {len(formatted) - len(reference):+d} chars\n")
            
            form_lines = formatted.split('\n')
            ref_lines = reference.split('\n')
            out.write(f"- Formatted lines: {len(form_lines)}\n")
            out.write(f"- Reference lines: {len(ref_lines)}\n")
            out.write(f"- Line difference: {len(form_lines) - len(ref_lines):+d} lines\n\n")
            
            # Get LLM evaluation
            print("  Getting LLM evaluation...")
            evaluation = get_llm_evaluation(formatted, reference, os.path.basename(formatted_file))
            out.write(f"**LLM Quality Evaluation:**\n\n{evaluation}\n\n")
            out.write("---\n\n")
    
    print(f"\n{'='*80}")
    print("EVALUATION COMPLETE")
    print(f"{'='*80}")
    print(f"Results saved to: {output_file}")
    if len(files_to_evaluate) < len(all_gemini_files):
        print(f"Evaluated {len(files_to_evaluate)} new files (skipped {len(all_gemini_files) - len(files_to_evaluate)} already done)")
    print("Compare the scores to see if prompt improvements are working!")


if __name__ == "__main__":
    main()