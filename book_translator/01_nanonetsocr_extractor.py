"""Nanonets OCR extractor for document text extraction."""

from typing import Any

from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor, AutoTokenizer

model_path = "nanonets/Nanonets-OCR-s"

# Type annotations suppressed due to transformers library dynamic typing
model: Any = AutoModelForImageTextToText.from_pretrained(  # type: ignore[misc]
    model_path, 
    torch_dtype="auto", 
    device_map="auto", 
    attn_implementation="flash_attention_2"
)
model.eval()  # type: ignore[misc]

tokenizer: Any = AutoTokenizer.from_pretrained(model_path)  # type: ignore[misc]
processor: Any = AutoProcessor.from_pretrained(model_path)  # type: ignore[misc]


def ocr_page_with_nanonets_s(
    image_path: str, 
    model: Any, 
    processor: Any, 
    max_new_tokens: int = 4096
) -> str:
    """Extract text from document image using Nanonets OCR model.
    
    Args:
        image_path: Path to the image file
        model: The Nanonets OCR model
        processor: The model processor
        max_new_tokens: Maximum number of tokens to generate
        
    Returns:
        Extracted text from the document
        
    """
    prompt = """Extract the text from the above document as if you were reading it naturally. Return the tables in html format. Return the equations in LaTeX representation. If there is an image in the document and image caption is not present, add a small description of the image inside the <img></img> tag; otherwise, add the image caption inside <img></img>. Watermarks should be wrapped in brackets. Ex: <watermark>OFFICIAL COPY</watermark>. Page numbers should be wrapped in brackets. Ex: <page_number>14</page_number> or <page_number>9/22</page_number>. Prefer using ☐ and ☑ for check boxes."""
    image = Image.open(image_path)
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": [
            {"type": "image", "image": f"file://{image_path}"},
            {"type": "text", "text": prompt},
        ]},
    ]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)  # type: ignore[misc]
    inputs = processor(text=[text], images=[image], padding=True, return_tensors="pt")  # type: ignore[misc]
    inputs = inputs.to(model.device)  # type: ignore[misc]
    
    output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)  # type: ignore[misc]
    generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, output_ids, strict=True)]  # type: ignore[misc]
    
    output_text = processor.batch_decode(generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)  # type: ignore[misc]
    return output_text[0]  # type: ignore[misc]

image_path = "/path/to/your/document.jpg"
result = ocr_page_with_nanonets_s(image_path, model, processor, max_new_tokens=15000)
print(result)
