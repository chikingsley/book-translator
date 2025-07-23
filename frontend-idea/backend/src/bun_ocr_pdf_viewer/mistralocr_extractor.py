
"""Mistral OCR extractor for images."""

import base64
import os
from typing import Any

from dotenv import load_dotenv
from mistralai import Mistral

# Load environment variables from .env file
load_dotenv()

async def run_ocr(image_path: str) -> dict[str, list[dict[str, Any]]]:
    """Run Mistral OCR on an image and return structured data."""
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY not found in environment variables")

    client = Mistral(api_key=api_key)

    # Encode the image to base64
    try:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError as e:
        raise ValueError(f"Image file not found at {image_path}") from e

    # Determine image type from file extension
    image_ext = image_path.lower().split('.')[-1]
    image_type = "jpeg" if image_ext in ["jpg", "jpeg"] else image_ext

    # Call Mistral OCR API
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "image_url",
            "image_url": f"data:image/{image_type};base64,{base64_image}" 
        },
        include_image_base64=True
    )

    
    # Structure the response based on actual Mistral OCR response
    pages_data: list[dict[str, Any]] = []
    
    # Try to access the pages - the structure might be different
    if hasattr(ocr_response, 'pages'):
        for i, page in enumerate(ocr_response.pages):
            page_data: dict[str, Any] = {
                "page_number": i + 1,
                "words": []
            }
            
            # Check what attributes the page actually has
            # Use getattr with default to avoid attribute errors
            words = getattr(page, 'words', [])
            
            # If no words, check if there's markdown content
            if not words and hasattr(page, 'markdown'):
                page_data['markdown'] = page.markdown
            
            for word in words:
                word_data: dict[str, Any] = {}
                word_data['text'] = getattr(word, 'text', '')
                # Try both bbox and bounding_box attributes
                bbox = getattr(word, 'bbox', None) or getattr(word, 'bounding_box', None)
                if bbox:
                    word_data['bbox'] = bbox
                page_data['words'].append(word_data)
            
            # Try to get dimensions if available
            width = getattr(page, 'width', None)
            if width is not None:
                page_data['width'] = width
            height = getattr(page, 'height', None)
            if height is not None:
                page_data['height'] = height
            
            pages_data.append(page_data)
    
    return {"pages": pages_data}
