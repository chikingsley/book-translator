"""Gemini OCR extractor for PDF documents."""

# ============== CONFIGURATION ==============
PROCESS_FULL_PDF = False
START_PAGE = 4
END_PAGE = 5
PDF_PATH = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz.pdf"
# ==========================================

import os
import sys
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import pymupdf
from alive_progress import alive_bar
from dotenv import load_dotenv
from google import genai


def extract_single_page_to_pdf(input_pdf_path: str, page_num: int) -> BytesIO:
    """Extract a single page from PDF and return as BytesIO object."""
    doc = pymupdf.open(input_pdf_path)
    new_doc = pymupdf.open()
    
    if page_num - 1 < len(doc):
        new_doc.insert_pdf(doc, from_page=page_num - 1, to_page=page_num - 1)
    
    pdf_bytes = BytesIO()
    pdf_bytes.write(new_doc.write())  # type: ignore[misc]
    pdf_bytes.seek(0)
    
    doc.close()
    new_doc.close()
    
    return pdf_bytes


def upload_and_process_single_page(
    client: Any,
    pdf_path: str,
    page_num: int,
    bar: Any,
    page_index: int,
    total_pages: int,
    estimated_time: float,
    time_estimates: list[float],
    prediction_errors: list[float],
    pages_completed: int,
    overall_start_time: float,
    recent_page_times: list[tuple[float, float]],
    retry_count: int = 1,
) -> Optional[str]:
    """Upload and process a single page."""
    try:
        pdf_bytes = extract_single_page_to_pdf(pdf_path, page_num)
    except Exception as e:
        print(f"Error extracting page {page_num}: {e}")
        return None
    
    temp_path = f"temp_page_{page_num}.pdf"
    try:
        with open(temp_path, "wb") as f:
            f.write(pdf_bytes.getvalue())
        
        pdf_file = client.files.upload(file=temp_path)
        
        os.remove(temp_path)
        
    except Exception as e:
        print(f"Error uploading page {page_num}: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return None
    page_prompt = f"""
    Extract all text from this PDF exactly as it appears.
    Start with "# Page {page_num}"
    Then provide the raw text without any modifications.
    This PDF contains only one page, so extract all content from it.
    """
    
    result: dict[str, Any] = {"text": None, "error": None, "completed": False}
    
    def api_call():
        """Run the API call in a separate thread."""
        try:
            response = client.models.generate_content(
                model="gemini-2.5-pro", contents=[page_prompt, pdf_file]
            )
            result["text"] = response.text if response.text else None
        except Exception as e:
            result["error"] = e
        finally:
            result["completed"] = True
    
    api_thread = threading.Thread(target=api_call)
    api_thread.daemon = True
    api_thread.start()
    
    start_time = time.time()
    
    while not result["completed"]:
        elapsed = time.time() - start_time
        
        if time_estimates:
            estimated_page_progress = min(elapsed / estimated_time, 1.0)
            total_progress = (page_index + estimated_page_progress) / total_pages
            bar(total_progress)
            if len(prediction_errors) >= 3:
                recent_errors = prediction_errors[-5:]
                sorted_errors = sorted(recent_errors)
                median_error = sorted_errors[len(sorted_errors) // 2]
                confidence = max(20, min(95, (1 - median_error) * 80 + 20))
            else:
                confidence = 50
            if len(recent_page_times) >= 2:
                time_span = recent_page_times[-1][0] - recent_page_times[0][0]
                pages_span = recent_page_times[-1][1] - recent_page_times[0][1]
                current_rate = pages_span / time_span if time_span > 0 else 0
            else:
                overall_elapsed = time.time() - overall_start_time
                current_rate = pages_completed / overall_elapsed if overall_elapsed > 0 else 0
            remaining_pages = total_pages - pages_completed
            if current_rate > 0 and remaining_pages > 0:
                raw_eta = remaining_pages / current_rate
                
                if time_estimates:
                    avg_page_time = sum(time_estimates[-5:]) / min(5, len(time_estimates))
                    estimate_based_eta = remaining_pages * avg_page_time
                    eta_seconds = raw_eta * 0.6 + estimate_based_eta * 0.4
                else:
                    eta_seconds = raw_eta
                
                if eta_seconds < 60:
                    eta_text = f"ETA: {eta_seconds:.0f}s"
                else:
                    minutes = int(eta_seconds // 60)
                    seconds = int(eta_seconds % 60)
                    eta_text = f"ETA: {minutes}m {seconds}s"
            else:
                eta_text = "ETA: calculating..."
            
            retry_text = f" (retry {retry_count})" if retry_count > 1 else ""
            bar.text = (f"Page {page_num}{retry_text}: "
                       f"{elapsed:.1f}s / ~{estimated_time:.1f}s | "
                       f"{current_rate:.2f} p/s | "
                       f"{confidence:.0f}% conf | "
                       f"{eta_text}")
        else:
            estimated_page_progress = min(elapsed / estimated_time, 1.0)
            total_progress = estimated_page_progress / total_pages
            bar(total_progress)
            retry_text = f" (retry {retry_count})" if retry_count > 1 else ""
            bar.text = f"Page {page_num}{retry_text}: Learning timing... {elapsed:.1f}s elapsed"
        
        time.sleep(0.1)
        if elapsed > (estimated_time * 3):
            bar.text = f"Page {page_num}: API timeout after {elapsed:.1f}s"
            break
    
    api_thread.join(timeout=5)
    try:
        client.files.delete(pdf_file.name)
    except:
        pass
    if result["error"]:
        error = result["error"]
        if isinstance(error, Exception):
            raise error
    
    text_result = result["text"]
    return text_result if isinstance(text_result, str) else None


def main() -> None:
    """Process PDF pages with single page extraction and processing."""
    pdf_path = PDF_PATH
    
    load_dotenv()
    
    if not os.path.exists(pdf_path):
        print(f"Error: The file {pdf_path} was not found.")
        sys.exit(1)
    
    if PROCESS_FULL_PDF:
        try:
            doc = pymupdf.open(pdf_path)
            start_page = 1
            end_page = len(doc)
            doc.close()
            print(f"Processing entire PDF: {end_page} pages")
        except Exception as e:
            print(f"Error opening PDF to count pages: {e}")
            sys.exit(1)
    else:
        start_page = START_PAGE
        end_page = END_PAGE
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables or .env file")
        sys.exit(1)
    
    client = genai.Client(api_key=api_key)
    
    print(f"Processing PDF: {pdf_path}")
    print(f"Processing pages {start_page}-{end_page} individually...")
    
    total_pages = end_page - start_page + 1
    print(f"Total pages to process: {total_pages}")
    
    input_path = Path(pdf_path)
    if PROCESS_FULL_PDF:
        output_path = input_path.with_stem(input_path.stem + '-gemini').with_suffix('.md')
    else:
        output_path = input_path.with_stem(
            f"{input_path.stem}-pages-{start_page}-{end_page}-gemini"
        ).with_suffix(".md")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("")
    
    print(f"Output will be written to: {output_path}")
    
    failed_pages = 0
    first_page = True
    time_estimates: list[float] = []
    prediction_errors: list[float] = []
    pages_completed = 0
    overall_start_time = time.time()
    recent_page_times: list[tuple[float, float]] = []
    
    with alive_bar(
        manual=True,
        title="Smart OCR Processing",
        dual_line=True,
        refresh_secs=0.05,
        calibrate=1,
        length=50,
        stats=False
    ) as bar:  # type: ignore[misc]
        for page_index in range(total_pages):
            actual_page_num = start_page + page_index
            page_start_time = time.time()
            if time_estimates:
                recent_estimates = time_estimates[-10:] if len(time_estimates) > 10 else time_estimates
                
                last_time = recent_estimates[-1]
                avg_recent = sum(recent_estimates) / len(recent_estimates)
                
                if last_time > avg_recent * 1.5:
                    estimated_time = last_time * 0.7 + avg_recent * 0.3
                else:
                    weights = [0.5**(len(recent_estimates)-i-1) for i in range(len(recent_estimates))]
                    estimated_time = sum(t * w for t, w in zip(recent_estimates, weights)) / sum(weights)
                
                confidence_factor = min(len(time_estimates) / 20, 1.0)
                buffer = 1.2 - (0.2 * confidence_factor)
                estimated_time *= buffer
            else:
                estimated_time = 45
            
            retry_count = 0
            page_extracted = False
            
            while not page_extracted and retry_count < 10:
                retry_count += 1
                
                try:
                    page_text = upload_and_process_single_page(
                        client,
                        pdf_path,
                        actual_page_num,
                        bar,
                        page_index,
                        total_pages,
                        estimated_time,
                        time_estimates,
                        prediction_errors,
                        pages_completed,
                        overall_start_time,
                        recent_page_times,
                        retry_count,
                    )
                    
                    if page_text and len(page_text.strip()) > 20:
                        actual_time = time.time() - page_start_time
                        time_estimates.append(actual_time)
                        pages_completed += 1
                        recent_page_times.append((time.time(), pages_completed))
                        recent_page_times = [(t, p) for t, p in recent_page_times 
                                             if t > time.time() - 300 and len(recent_page_times) - recent_page_times.index((t, p)) <= 5]
                        if len(time_estimates) > 1:
                            prediction_error = abs(actual_time - estimated_time) / estimated_time
                            prediction_errors.append(prediction_error)
                        actual_progress = (page_index + 1) / total_pages
                        bar(actual_progress)
                        with open(output_path, "a", encoding="utf-8") as f:
                            if not first_page:
                                f.write("\n\n---\n\n")
                            f.write(page_text)
                        
                        first_page = False
                        page_extracted = True
                        char_count = len(page_text)
                        
                        if len(recent_page_times) >= 2:
                            time_span = recent_page_times[-1][0] - recent_page_times[0][0]
                            pages_span = recent_page_times[-1][1] - recent_page_times[0][1]
                            current_rate = pages_span / time_span if time_span > 0 else 0
                        else:
                            overall_elapsed = time.time() - overall_start_time
                            current_rate = pages_completed / overall_elapsed if overall_elapsed > 0 else 0
                        
                        remaining_pages = total_pages - pages_completed
                        
                        if len(time_estimates) == 1:
                            bar.text = f"Page 1: Done! Baseline: {actual_time:.1f}s ({char_count} chars) | {current_rate:.2f} p/s"
                        else:
                            diff = actual_time - estimated_time
                            if remaining_pages > 0 and current_rate > 0:
                                raw_eta = remaining_pages / current_rate
                                avg_page_time = sum(time_estimates[-5:]) / min(5, len(time_estimates))
                                estimate_based_eta = remaining_pages * avg_page_time
                                eta_seconds = raw_eta * 0.6 + estimate_based_eta * 0.4
                                
                                if eta_seconds < 60:
                                    eta_text = f"ETA: {eta_seconds:.0f}s"
                                else:
                                    minutes = int(eta_seconds // 60)
                                    seconds = int(eta_seconds % 60)
                                    eta_text = f"ETA: {minutes}m {seconds}s"
                            else:
                                eta_text = "ETA: complete!"
                            bar.text = f"Page {actual_page_num}: {actual_time:.1f}s ({diff:+.1f}s vs estimate, {char_count} chars) | {current_rate:.2f} p/s | {eta_text}"
                        
                        time.sleep(1)
                    
                    elif retry_count < 5:
                        bar.text = f"Page {actual_page_num} - Short response, retrying in 2s..."
                        time.sleep(2)
                        continue
                    else:
                        bar.text = f"Page {actual_page_num} - Waiting 10s before retry..."
                        time.sleep(10)
                
                except Exception as e:
                    error_msg = str(e)
                    if "500" in error_msg or "rate" in error_msg.lower():
                        wait_time = min(30, 5 * retry_count)
                        bar.text = f"Rate limited - waiting {wait_time}s..."
                        time.sleep(wait_time)
                    else:
                        bar.text = f"Error on page {actual_page_num}: {error_msg[:50]}..."
                        time.sleep(2)
            
            if not page_extracted:
                failed_pages += 1
                failed_time = time.time() - page_start_time
                time_estimates.append(failed_time)
                pages_completed += 1
                
                recent_page_times.append((time.time(), pages_completed))
                recent_page_times = [(t, p) for t, p in recent_page_times 
                                     if t > time.time() - 300 and len(recent_page_times) - recent_page_times.index((t, p)) <= 5]
                
                if len(time_estimates) > 1:
                    prediction_error = abs(failed_time - estimated_time) / estimated_time
                    prediction_errors.append(prediction_error)
                
                actual_progress = (page_index + 1) / total_pages
                bar(actual_progress)
                
                if len(recent_page_times) >= 2:
                    time_span = recent_page_times[-1][0] - recent_page_times[0][0]
                    pages_span = recent_page_times[-1][1] - recent_page_times[0][1]
                    current_rate = pages_span / time_span if time_span > 0 else 0
                else:
                    overall_elapsed = time.time() - overall_start_time
                    current_rate = pages_completed / overall_elapsed if overall_elapsed > 0 else 0
                
                remaining_pages = total_pages - pages_completed
                if remaining_pages > 0 and current_rate > 0:
                    raw_eta = remaining_pages / current_rate
                    if time_estimates:
                        avg_page_time = sum(time_estimates[-5:]) / min(5, len(time_estimates))
                        estimate_based_eta = remaining_pages * avg_page_time
                        eta_seconds = raw_eta * 0.6 + estimate_based_eta * 0.4
                    else:
                        eta_seconds = raw_eta
                    
                    if eta_seconds < 60:
                        eta_text = f"ETA: {eta_seconds:.0f}s"
                    else:
                        minutes = int(eta_seconds // 60)
                        seconds = int(eta_seconds % 60)
                        eta_text = f"ETA: {minutes}m {seconds}s"
                else:
                    eta_text = "ETA: complete!"
                
                bar.text = f"Page {actual_page_num} - Failed after {retry_count} attempts ({failed_time:.1f}s) | {current_rate:.2f} p/s | {eta_text}"
                time.sleep(1)
    
    print("\nOCR extraction complete!")
    print(f"Pages processed: {start_page}-{end_page} ({total_pages} total)")
    print(f"Successfully extracted: {total_pages - failed_pages}")
    print(f"Failed pages: {failed_pages}")
    if time_estimates:
        avg_time = sum(time_estimates) / len(time_estimates)
        print(f"Average time per page: {avg_time:.1f}s")
    
    total_elapsed = time.time() - overall_start_time
    final_rate = pages_completed / total_elapsed if total_elapsed > 0 else 0
    print(f"Overall processing rate: {final_rate:.1f} pages/s")
    
    if len(prediction_errors) >= 3:
        sorted_errors = sorted(prediction_errors)
        median_error = sorted_errors[len(sorted_errors) // 2]
        final_confidence = max(20, min(95, (1 - median_error) * 80 + 20))
        print(f"Final prediction confidence: {final_confidence:.0f}%")
    
    print(f"Output saved to: {output_path}")


if __name__ == "__main__":
    main()