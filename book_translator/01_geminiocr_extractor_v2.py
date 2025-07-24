"""Gemini OCR extractor for PDF documents - Enhanced version with adaptive progress estimation."""

import os
import sys
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Any

import pymupdf
from alive_progress import alive_bar
from dotenv import load_dotenv
from google import genai


def extract_pages_to_pdf(
    input_pdf_path: str, start_page: int, end_page: int
) -> BytesIO:
    """Extract specific pages from PDF and return as BytesIO object."""
    doc = pymupdf.open(input_pdf_path)
    new_doc = pymupdf.open()

    for page_num in range(start_page - 1, end_page):
        if page_num < len(doc):
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

    pdf_bytes = BytesIO()
    pdf_bytes.write(new_doc.write())  # type: ignore[misc]
    pdf_bytes.seek(0)

    doc.close()
    new_doc.close()

    return pdf_bytes


def save_markdown(content: str, output_path: str) -> None:
    """Save markdown content to a file."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Markdown saved to: {output_path}")
    except Exception as e:
        print(f"Error saving file: {e}")


def process_page_with_progress(
    client: Any,
    page_prompt: str,
    pdf_file: Any,
    bar: Any,
    page_index: int,
    total_pages: int,
    actual_page_num: int,
    estimated_time: float,
    time_estimates: list[float],
    prediction_errors: list[float],
    pages_completed: int,
    overall_start_time: float,
    recent_page_times: list[tuple[float, float]],
    retry_count: int = 1,
) -> str | None:
    """Process a single page with real-time progress updates."""
    result: dict[str, str | Exception | bool | None] = {"text": None, "error": None, "completed": False}

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

            # Calculate confidence based on prediction accuracy
            if len(prediction_errors) >= 3:
                recent_errors = prediction_errors[-5:]
                # Use median instead of mean to reduce outlier impact
                sorted_errors = sorted(recent_errors)
                median_error = sorted_errors[len(sorted_errors) // 2]
                # Scale confidence more gradually
                confidence = max(20, min(95, (1 - median_error) * 80 + 20))
            else:
                confidence = 50  # Neutral until we have enough data

            # Calculate current processing rate using recent pages
            if len(recent_page_times) >= 2:
                time_span = recent_page_times[-1][0] - recent_page_times[0][0]
                pages_span = recent_page_times[-1][1] - recent_page_times[0][1]
                current_rate = pages_span / time_span if time_span > 0 else 0
            else:
                # Fallback to overall rate if not enough recent data
                overall_elapsed = time.time() - overall_start_time
                current_rate = pages_completed / overall_elapsed if overall_elapsed > 0 else 0

            # Calculate ETA with better logic
            remaining_pages = total_pages - pages_completed
            if current_rate > 0 and remaining_pages > 0:
                raw_eta = remaining_pages / current_rate
                
                # If we have enough history, blend with per-page estimate
                if time_estimates:
                    avg_page_time = sum(time_estimates[-5:]) / min(5, len(time_estimates))
                    estimate_based_eta = remaining_pages * avg_page_time
                    # Blend the two approaches
                    eta_seconds = raw_eta * 0.6 + estimate_based_eta * 0.4
                else:
                    eta_seconds = raw_eta
                
                # Format as countdown
                if eta_seconds < 60:
                    eta_text = f"ETA: {eta_seconds:.0f}s"
                else:
                    minutes = int(eta_seconds // 60)
                    seconds = int(eta_seconds % 60)
                    eta_text = f"ETA: {minutes}m {seconds}s"
            else:
                eta_text = "ETA: calculating..."

            retry_text = f" (retry {retry_count})" if retry_count > 1 else ""
            bar.text = (f"Page {actual_page_num}{retry_text}: "
                       f"{elapsed:.1f}s / ~{estimated_time:.1f}s | "
                       f"{current_rate:.2f} p/s | "
                       f"{confidence:.0f}% conf | "
                       f"{eta_text}")
        else:
            # First page - show gradual progress
            estimated_page_progress = min(elapsed / estimated_time, 1.0)
            total_progress = estimated_page_progress / total_pages
            bar(total_progress)
            retry_text = f" (retry {retry_count})" if retry_count > 1 else ""
            bar.text = f"Page 1{retry_text}: Learning timing... {elapsed:.1f}s elapsed"

        # Sleep briefly before next update
        time.sleep(0.1)  # Update every 100ms for smooth progress

        # Timeout check
        if elapsed > (estimated_time * 3):  # Timeout after 3x estimated time
            bar.text = f"Page {actual_page_num}: API timeout after {elapsed:.1f}s"
            break

    # Wait for thread to complete (with timeout)
    api_thread.join(timeout=5)

    # Handle results
    if result["error"]:
        error = result["error"]
        if isinstance(error, Exception):
            raise error

    text_result = result["text"]
    return text_result if isinstance(text_result, str) else None


def main() -> None:
    """Process PDF pages 4-26 with adaptive progress estimation."""
    pdf_path = "test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz.pdf"
    start_page = 4
    end_page = 26

    load_dotenv()

    if not os.path.exists(pdf_path):
        print(f"Error: The file {pdf_path} was not found.")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables or .env file")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    print(f"Processing PDF: {pdf_path}")
    print(f"Extracting pages {start_page}-{end_page}...")

    try:
        pdf_bytes = extract_pages_to_pdf(pdf_path, start_page, end_page)
        print(f"Successfully extracted pages {start_page}-{end_page}")
    except Exception as e:
        print(f"Error extracting pages: {e}")
        sys.exit(1)

    print("Uploading extracted pages to Gemini...")

    try:
        temp_path = f"temp_pages_{start_page}_{end_page}.pdf"
        with open(temp_path, "wb") as f:
            f.write(pdf_bytes.getvalue())

        pdf_file = client.files.upload(file=temp_path)
        print("PDF uploaded successfully")

        os.remove(temp_path)

    except Exception as e:
        print(f"Error uploading PDF: {e}")
        sys.exit(1)

    total_pages = end_page - start_page + 1
    print(f"Total pages to process: {total_pages}")

    input_path = Path(pdf_path)
    output_path = input_path.with_stem(
        f"{input_path.stem}_pages_{start_page}_{end_page}_gemini_pro_adaptive"
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
            pdf_page_num = page_index + 1
            page_start_time = time.time()

            # Calculate current best estimate
            if time_estimates:
                # Use only recent estimates (last 5-10 pages)
                recent_estimates = time_estimates[-10:] if len(time_estimates) > 10 else time_estimates
                
                # If the most recent time is significantly different, adapt quickly
                last_time = recent_estimates[-1]
                avg_recent = sum(recent_estimates) / len(recent_estimates)
                
                if last_time > avg_recent * 1.5:  # Last call was 50% slower
                    # Weight the last call heavily when it's an outlier
                    estimated_time = last_time * 0.7 + avg_recent * 0.3
                else:
                    # Normal exponential smoothing (recent pages weighted more)
                    weights = [0.5**(len(recent_estimates)-i-1) for i in range(len(recent_estimates))]
                    estimated_time = sum(t * w for t, w in zip(recent_estimates, weights)) / sum(weights)
                
                # Add conservative buffer early on, reduce as we get more data
                confidence_factor = min(len(time_estimates) / 20, 1.0)  # 0 to 1 as we process pages
                buffer = 1.2 - (0.2 * confidence_factor)  # Start with 20% buffer, reduce to 0%
                estimated_time *= buffer
            else:
                estimated_time = 45  # Conservative first guess

            retry_count = 0
            page_extracted = False

            while not page_extracted and retry_count < 10:
                retry_count += 1

                page_prompt = f"""
                Extract all text from page {pdf_page_num} of this PDF exactly as it appears.
                Start with "# Page {actual_page_num}"
                Then provide the raw text without any modifications.
                """

                try:
                    # Use the new threaded function for smooth progress
                    page_text = process_page_with_progress(
                        client,
                        page_prompt,
                        pdf_file,
                        bar,
                        page_index,
                        total_pages,
                        actual_page_num,
                        estimated_time,
                        time_estimates,
                        prediction_errors,
                        pages_completed,
                        overall_start_time,
                        recent_page_times,
                        retry_count,
                    )

                    if page_text and len(page_text.strip()) > 20:
                        # Page completed successfully!
                        actual_time = time.time() - page_start_time
                        time_estimates.append(actual_time)
                        pages_completed += 1
                        
                        # Track recent page times for rate calculation
                        recent_page_times.append((time.time(), pages_completed))
                        # Keep only last 5 pages or last 5 minutes
                        recent_page_times = [(t, p) for t, p in recent_page_times 
                                             if t > time.time() - 300 and len(recent_page_times) - recent_page_times.index((t, p)) <= 5]

                        # Calculate prediction error for confidence tracking
                        if (
                            len(time_estimates) > 1
                        ):  # Skip first page as it has no prediction
                            prediction_error = (
                                abs(actual_time - estimated_time) / estimated_time
                            )
                            prediction_errors.append(prediction_error)

                        # Jump to actual completion for this page
                        actual_progress = (page_index + 1) / total_pages
                        bar(actual_progress)

                        # Save the extracted text
                        with open(output_path, "a", encoding="utf-8") as f:
                            if not first_page:
                                f.write("\n\n---\n\n")
                            f.write(page_text)

                        first_page = False
                        page_extracted = True

                        # Calculate final stats for this page
                        char_count = len(page_text)
                        
                        # Use recent page times for better rate calculation
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

                        time.sleep(1)  # Brief pause to show completion message

                    elif retry_count < 5:
                        bar.text = f"Page {actual_page_num} - Short response, retrying in 2s..."
                        time.sleep(2)
                        continue
                    else:
                        bar.text = (
                            f"Page {actual_page_num} - Waiting 10s before retry..."
                        )
                        time.sleep(10)

                except Exception as e:
                    error_msg = str(e)
                    if "500" in error_msg or "rate" in error_msg.lower():
                        wait_time = min(30, 5 * retry_count)
                        bar.text = f"Rate limited - waiting {wait_time}s..."
                        time.sleep(wait_time)
                    else:
                        bar.text = (
                            f"Error on page {actual_page_num}: {error_msg[:50]}..."
                        )
                        time.sleep(2)

            if not page_extracted:
                failed_pages += 1
                # Still record a time estimate for failed pages (helps with remaining estimates)
                failed_time = time.time() - page_start_time
                time_estimates.append(failed_time)
                pages_completed += (
                    1  # Count failed pages as "completed" for rate calculation
                )
                
                # Track recent page times even for failed pages
                recent_page_times.append((time.time(), pages_completed))
                recent_page_times = [(t, p) for t, p in recent_page_times 
                                     if t > time.time() - 300 and len(recent_page_times) - recent_page_times.index((t, p)) <= 5]

                # Calculate prediction error even for failed pages
                if len(time_estimates) > 1:
                    prediction_error = (
                        abs(failed_time - estimated_time) / estimated_time
                    )
                    prediction_errors.append(prediction_error)

                # Update progress as if page completed (for progress bar continuity)
                actual_progress = (page_index + 1) / total_pages
                bar(actual_progress)

                # Calculate current rate and ETA
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

    # Final processing rate
    total_elapsed = time.time() - overall_start_time
    final_rate = pages_completed / total_elapsed if total_elapsed > 0 else 0
    print(f"Overall processing rate: {final_rate:.1f} pages/s")

    # Final confidence score
    if len(prediction_errors) >= 3:
        # Use median for final confidence too
        sorted_errors = sorted(prediction_errors)
        median_error = sorted_errors[len(sorted_errors) // 2]
        final_confidence = max(20, min(95, (1 - median_error) * 80 + 20))
        print(f"Final prediction confidence: {final_confidence:.0f}%")

    print(f"Output saved to: {output_path}")


if __name__ == "__main__":
    main()
