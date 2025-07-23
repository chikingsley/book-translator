"""Basic OCR evaluation script to compare Mistral and Gemini outputs."""

import re
from difflib import SequenceMatcher
from typing import Any


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    # Remove multiple spaces and normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace from lines
    lines = [line.strip() for line in text.split('\n')]
    # Remove empty lines
    lines = [line for line in lines if line]
    return '\n'.join(lines)


def extract_pages(content: str) -> dict[int, str]:
    """Extract individual pages from markdown content."""
    pages = {}
    
    # Split by page markers
    page_splits = re.split(r'\n---\n|^---\n', content)
    
    for section in page_splits:
        if not section.strip():
            continue
            
        # Look for page number
        page_match = re.search(r'#\s*Page\s*(\d+)', section)
        if page_match:
            page_num = int(page_match.group(1))
            # Remove the page header for comparison
            page_content = re.sub(r'#\s*Page\s*\d+\s*\n', '', section).strip()
            pages[page_num] = page_content
    
    return pages


def compare_texts(text1: str, text2: str) -> float:
    """Compare two texts and return similarity ratio (0-1)."""
    matcher = SequenceMatcher(None, text1, text2)
    return matcher.ratio()


def find_differences(text1: str, text2: str, context: int = 20) -> list[tuple[str, str]]:
    """Find specific differences between texts with context."""
    differences = []
    matcher = SequenceMatcher(None, text1, text2)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != 'equal':
            # Get context around the difference
            context_start1 = max(0, i1 - context)
            context_end1 = min(len(text1), i2 + context)
            context_start2 = max(0, j1 - context)
            context_end2 = min(len(text2), j2 + context)
            
            diff1 = text1[context_start1:context_end1]
            diff2 = text2[context_start2:context_end2]
            
            differences.append((diff1, diff2))
    
    return differences


def evaluate_page(mistral_text: str, gemini_text: str, page_num: int) -> dict[str, Any]:
    """Evaluate a single page comparison."""
    # Normalize for comparison
    mistral_norm = normalize_text(mistral_text)
    gemini_norm = normalize_text(gemini_text)
    
    # Calculate similarity
    similarity = compare_texts(mistral_norm, gemini_norm)
    
    # Find differences
    differences = find_differences(mistral_norm, gemini_norm)
    
    # Count words
    mistral_words = len(mistral_norm.split())
    gemini_words = len(gemini_norm.split())
    
    return {
        'page': page_num,
        'similarity': similarity,
        'mistral_words': mistral_words,
        'gemini_words': gemini_words,
        'word_diff': abs(mistral_words - gemini_words),
        'differences': differences[:5]  # First 5 differences
    }


def main():
    """Run OCR evaluation comparison."""
    # File paths
    mistral_file = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz.md"
    gemini_file = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-gemini.md"
    
    print("OCR Evaluation: Mistral vs Gemini")
    print("=" * 50)
    
    # Read files
    try:
        with open(mistral_file, encoding='utf-8') as f:
            mistral_content = f.read()
        with open(gemini_file, encoding='utf-8') as f:
            gemini_content = f.read()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    
    # Extract pages
    print("\nExtracting pages...")
    mistral_pages = extract_pages(mistral_content)
    gemini_pages = extract_pages(gemini_content)
    
    print(f"Mistral pages found: {len(mistral_pages)}")
    print(f"Gemini pages found: {len(gemini_pages)}")
    
    # Find common pages
    common_pages = set(mistral_pages.keys()) & set(gemini_pages.keys())
    print(f"Common pages: {len(common_pages)}")
    
    # Evaluate each page
    results = []
    low_similarity_pages = []
    
    print("\nEvaluating pages...")
    for page_num in sorted(common_pages):
        result = evaluate_page(
            mistral_pages[page_num], 
            gemini_pages[page_num], 
            page_num
        )
        results.append(result)
        
        if result['similarity'] < 0.9:
            low_similarity_pages.append(result)
    
    # Summary statistics
    print("\n" + "=" * 50)
    print("SUMMARY STATISTICS")
    print("=" * 50)
    
    avg_similarity = 0.0
    if results:
        avg_similarity = sum(r['similarity'] for r in results) / len(results)
        print(f"Average similarity: {avg_similarity:.2%}")
        
        total_word_diff = sum(r['word_diff'] for r in results)
        print(f"Total word count difference: {total_word_diff}")
        
        print(f"\nPages with low similarity (<90%): {len(low_similarity_pages)}")
        
        if low_similarity_pages:
            print("\nProblematic pages:")
            for page in sorted(low_similarity_pages, key=lambda x: x['similarity'])[:10]:
                print(f"  Page {page['page']}: {page['similarity']:.2%} similarity, "
                      f"{page['word_diff']} word difference")
    
    # Save detailed report
    report_path = "test-book-pdfs/ocr_evaluation_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("OCR Evaluation Report: Mistral vs Gemini\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"Total pages compared: {len(results)}\n")
        f.write(f"Average similarity: {avg_similarity:.2%}\n")
        f.write(f"Pages with <90% similarity: {len(low_similarity_pages)}\n\n")
        
        f.write("Detailed Results by Page:\n")
        f.write("-" * 70 + "\n")
        
        for result in sorted(results, key=lambda x: x['page']):
            f.write(f"\nPage {result['page']}:\n")
            f.write(f"  Similarity: {result['similarity']:.2%}\n")
            f.write(f"  Word count - Mistral: {result['mistral_words']}, "
                   f"Gemini: {result['gemini_words']}\n")
            
            if result['differences'] and result['similarity'] < 0.95:
                f.write("  Sample differences:\n")
                for i, (diff1, diff2) in enumerate(result['differences'][:3]):
                    f.write(f"    Mistral: ...{diff1}...\n")
                    f.write(f"    Gemini:  ...{diff2}...\n")
                    if i < len(result['differences']) - 1:
                        f.write("    ---\n")
    
    print(f"\nDetailed report saved to: {report_path}")


if __name__ == "__main__":
    main()