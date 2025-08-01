"""Split OCR file into different token-sized chunks for testing."""

import os

from dotenv import load_dotenv
from google import genai


def count_tokens(client: genai.Client, text: str) -> int:
    """Count tokens for text using Gemini."""
    try:
        token_count = client.models.count_tokens(
            model="gemini-2.5-flash", contents=[text]
        )
        return token_count.total_tokens or 0
    except Exception as e:
        print(f"Error counting tokens: {e}")
        return 0


def create_chunks(
    client: genai.Client, content: str, target_sizes: list[int]
) -> dict[int, str]:
    """Create chunks of approximately the target token sizes."""
    chunks: dict[int, str] = {}
    lines = content.split("\n")

    for target_size in target_sizes:
        print(f"\nCreating chunk for ~{target_size:,} tokens...")

        current_chunk: list[str] = []

        for i, line in enumerate(lines):
            current_chunk.append(line)

            # Check token count every 50 lines to avoid too many API calls
            if i % 50 == 0 or i == len(lines) - 1:
                test_text = "\n".join(current_chunk)
                tokens = count_tokens(client, test_text)

                if tokens >= target_size:
                    chunks[target_size] = test_text
                    print(
                        f"  Created chunk with {tokens:,} tokens ({len(test_text):,} chars)"
                    )
                    break

        if target_size not in chunks:
            # If we ran out of content, use what we have
            final_text = "\n".join(current_chunk)
            final_tokens = count_tokens(client, final_text)
            chunks[target_size] = final_text
            print(
                f"  Created chunk with {final_tokens:,} tokens ({len(final_text):,} chars) - all available content"
            )

    return chunks


def save_chunks(chunks: dict[int, str], base_path: str):
    """Save chunks to separate files."""
    for size, content in chunks.items():
        filename = f"{base_path}_chunk_{size}_tokens.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Saved: {filename}")


def main() -> None:
    """Create token-sized chunks from the OCR file."""
    load_dotenv()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found")
        return

    # Create client
    google_api_key = os.environ.pop("GOOGLE_API_KEY", None)
    client = genai.Client(api_key=api_key)
    if google_api_key:
        os.environ["GOOGLE_API_KEY"] = google_api_key

    # Read the full file
    input_file = "/Volumes/simons-enjoyment/GitHub/book-translator/test-book-pdfs/Das Reich ohne Raum -- Bruno Goetz-gemini.md"
    print(f"Reading {input_file}...")

    try:
        with open(input_file, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {input_file}")
        return

    print(f"Read {len(content):,} characters")

    # Count total tokens
    print("\nCounting total tokens...")
    total_tokens = count_tokens(client, content)
    print(f"Total tokens in file: {total_tokens:,}")

    # Target sizes - more granular between 15k and 100k
    target_sizes = [1000, 5000, 10000, 15000, 25000, 40000, 60000, 80000, 100000]

    # Create chunks
    chunks = create_chunks(client, content, target_sizes)

    # Save chunks
    print("\nSaving chunks...")
    base_path = (
        "/Volumes/simons-enjoyment/GitHub/book-translator/test-book-pdfs/gemini_ocr"
    )
    save_chunks(chunks, base_path)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for size, chunk in chunks.items():
        actual_tokens = count_tokens(client, chunk)
        lines = len(chunk.split("\n"))
        print(
            f"Target: {size:,} tokens -> Actual: {actual_tokens:,} tokens ({lines:,} lines, {len(chunk):,} chars)"
        )


if __name__ == "__main__":
    main()
