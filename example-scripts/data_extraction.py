"""data_extraction.py

## Annotations for Structured Outputs and Data Extraction
In this cookbook, we will explore the basics of Annotations and to achieve structured outputs fueled by our OCR model.

You may want to do this in case current vision models are not powerful enough, hence enhancing their vision OCR capabilities with the OCR model to achieve better structured data extraction.

---

- [OCR without Annotations](#scrollTo=NhwM0aITt7ti)
- [OCR with Annotations](#scrollTo=LNzRYPDcyaLX)
- [Full Document with Annotations](#scrollTo=thKVdfrJ2fvB)
- [Other Examples](#scrollTo=UtCyIWRuimm6)

What are Annotations?

Mistral Document AI API adds two annotation functionalities:
- `document_annotation`: returns the annotation of the entire document based on the input schema.
- `box_annotation`: gives you the annotation of the bboxes extracted by the OCR model (charts/ figures etc) based on user requirement. The user may ask to describe/caption the figure for instance.

Learn more about Annotations [here](https://docs.mistral.ai/capabilities/OCR/annotations/).

## Setup

First, let's install `mistralai` and download the required files.
"""

# Commented out IPython magic to ensure Python compatibility.
# %%capture
# !pip install mistralai

"""### Download PDF"""

# Commented out IPython magic to ensure Python compatibility.
# %%capture
# !wget https://raw.githubusercontent.com/mistralai/cookbook/refs/heads/main/mistral/ocr/mistral7b.pdf

"""### Create Client

We will need to set up our client. You can create an API key on our [Plateforme](https://console.mistral.ai/api-keys/).
"""

# Initialize Mistral client with API key
from mistralai import Mistral

api_key = "API_KEY" # Replace with your API key
client = Mistral(api_key=api_key)

"""## Mistral OCR without Annotations
For our cookbook we will use a pdf file, annotate it and extract data from the document.

First we have to make a function to encode our pdf file in base64, you can also upload the file to our cloud and use a signed url instead.
"""

import base64

def encode_pdf(pdf_path):
    """Encode the pdf to base64."""
    try:
        with open(pdf_path, "rb") as pdf_file:
            return base64.b64encode(pdf_file.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"Error: The file {pdf_path} was not found.")
        return None
    except Exception as e:  # Added general exception handling
        print(f"Error: {e}")
        return None

"""Now with our function ready, we can encode our pdf file and call our OCR model."""

import requests
import os
import json

# Path to your pdf
pdf_path = "mistral7b.pdf"

# Getting the base64 string
base64_pdf = encode_pdf(pdf_path)

# Call the OCR API
pdf_response = client.ocr.process(
    model="mistral-ocr-latest",
    document={
        "type": "document_url",
        "document_url": f"data:application/pdf;base64,{base64_pdf}"
    },
    include_image_base64=True
)

# Convert response to JSON format
response_dict = json.loads(pdf_response.model_dump_json())

print(json.dumps(response_dict, indent=4)[0:1000]) # check the first 1000 characters

"""We can view the result with the following:


"""

from mistralai.models import OCRResponse
from IPython.display import Markdown, display

def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
    """
    Replace image placeholders in markdown with base64-encoded images.

    Args:
        markdown_str: Markdown text containing image placeholders
        images_dict: Dictionary mapping image IDs to base64 strings

    Returns:
        Markdown text with images replaced by base64 data
    """
    for img_name, base64_str in images_dict.items():
        markdown_str = markdown_str.replace(
            f"![{img_name}]({img_name})", f"![{img_name}]({base64_str})"
        )
    return markdown_str

def get_combined_markdown(ocr_response: OCRResponse) -> str:
    """
    Combine OCR text and images into a single markdown document.

    Args:
        ocr_response: Response from OCR processing containing text and images

    Returns:
        Combined markdown string with embedded images
    """
    markdowns: list[str] = []
    # Extract images from page
    for page in ocr_response.pages:
        image_data = {}
        for img in page.images:
            image_data[img.id] = img.image_base64
        # Replace image placeholders with actual images
        markdowns.append(replace_images_in_markdown(page.markdown, image_data))

    return "\n\n".join(markdowns)

# Display combined markdowns and images
display(Markdown(get_combined_markdown(pdf_response)))

"""## Mistral OCR with Annotations
First, we need to create our Annotation Formats, for that we advise make use of `pydantic`.  
For this example, we will extract the image type and a description of each bbox; as well as the language, authors and a summary of the full document.
"""

from pydantic import BaseModel, Field
from enum import Enum

class ImageType(str, Enum):
    GRAPH = "graph"
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"

class Image(BaseModel):
    image_type: ImageType = Field(..., description="The type of the image. Must be one of 'graph', 'text', 'table' or 'image'.")
    description: str = Field(..., description="A description of the image.")

class Document(BaseModel):
    language: str = Field(..., description="The language of the document in ISO 639-1 code format (e.g., 'en', 'fr').")
    summary: str = Field(..., description="A summary of the document.")
    authors: list[str] = Field(..., description="A list of authors who contributed to the document.")

"""Now with our pydantic models created for our Annotations, we can call our OCR endpoint.  
The objective is to Annotate and Extract information from our document and the bbox/images detected.
"""

from mistralai.extra import response_format_from_pydantic_model

# OCR Call with Annotations
annotations_response = client.ocr.process(
    model="mistral-ocr-latest",
    pages=list(range(8)), # Document Annotations has a limit of 8 pages, we recommend spliting your documents when using it; bbox annotations does not have the same limit
    document={
        "type": "document_url",
        "document_url": f"data:application/pdf;base64,{base64_pdf}"
    },
    bbox_annotation_format=response_format_from_pydantic_model(Image),
    document_annotation_format=response_format_from_pydantic_model(Document),
    include_image_base64=False # We are not interested on retrieving the bbox images in this example, only their annotations
  )

# Convert response to JSON format
response_dict = json.loads(annotations_response.model_dump_json())

print(json.dumps(response_dict, indent=4))

"""Let's print the Annotations only!"""

print("Document Annotation:\n", annotations_response.document_annotation)
print("\nBBox/Images:")
for page in annotations_response.pages:
    for image in page.images:
        print("\nImage", image.id)
        print("Location:")
        print(" - top_left_x:", image.top_left_x)
        print(" - top_left_y:", image.top_left_y)
        print(" - bottom_right_x:", image.bottom_right_x)
        print(" - bottom_right_y:", image.bottom_right_y)
        print("BBox/Image Annotation:\n", image.image_annotation)

"""## Full Document with Annotation
For reference, let's do the same but including the bbox images.
"""

# OCR Call with Annotations
annotations_response = client.ocr.process(
    model="mistral-ocr-latest",
    pages=list(range(8)), # Document Annotations has a limit of 8 pages, we recommend spliting your documents when using it; bbox annotations does not have the same limit
    document={
        "type": "document_url",
        "document_url": f"data:application/pdf;base64,{base64_pdf}"
    },
    bbox_annotation_format=response_format_from_pydantic_model(Image),
    document_annotation_format=response_format_from_pydantic_model(Document),
    include_image_base64=True
  )

"""Now, we will display the full document with the OCR content and the annotation in bold:
- Document Annotation at the start of the document.
- BBox Annotation at below each bbox/image extracted.
"""

def replace_images_in_markdown_annotated(markdown_str: str, images_dict: dict) -> str:
    """
    Replace image placeholders in markdown with base64-encoded images and their annotation.

    Args:
        markdown_str: Markdown text containing image placeholders
        images_dict: Dictionary mapping image IDs to base64 strings

    Returns:
        Markdown text with images replaced by base64 data and their annotation
    """
    for img_name, data in images_dict.items():
        markdown_str = markdown_str.replace(
            f"![{img_name}]({img_name})", f"![{img_name}]({data['image']})\n\n**{data['annotation']}**"
        )
    return markdown_str

def get_combined_markdown_annotated(ocr_response: OCRResponse) -> str:
    """
    Combine OCR text, annotation and images into a single markdown document.

    Args:
        ocr_response: Response from OCR processing containing text and images

    Returns:
        Combined markdown string with embedded images and their annotation
    """
    markdowns: list[str] = ["**" + ocr_response.document_annotation + "**"]
    # Extract images from page
    for page in ocr_response.pages:
        image_data = {}
        for img in page.images:
            image_data[img.id] = {"image":img.image_base64, "annotation": img.image_annotation}
        # Replace image placeholders with actual images
        markdowns.append(replace_images_in_markdown_annotated(page.markdown, image_data))

    return "\n\n".join(markdowns)

# Display combined markdowns and images
display(Markdown(get_combined_markdown_annotated(annotations_response)))

"""## Other Examples"""

#@title PDF Financial Document

# Create the annotations formats
class ImageType(str, Enum):
    GRAPH = "graph"
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"

class Image(BaseModel):
    image_type: ImageType = Field(..., description="The type of the image. Must be one of 'graph', 'text', 'table' or 'image'.")
    description: str = Field(..., description="A description of the image.")

class Document(BaseModel):
    languages: list[str] = Field(..., description="The list of languages present in the document in ISO 639-1 code format (e.g., 'en', 'fr').")
    summary: str = Field(..., description="A summary of the document.")

# OCR Call with Annotations
annotations_response = client.ocr.process(
    model="mistral-ocr-latest",
    pages=list(range(8)), # Document Annotations has a limit of 8 pages, we recommend spliting your documents when using it; bbox annotations does not have the same limit
    document={
        "type": "document_url",
        "document_url": "https://upload.wikimedia.org/wikipedia/foundation/f/f6/WMF_Mid-Year-Financials_08-09-FINAL.pdf"
    },
    bbox_annotation_format=response_format_from_pydantic_model(Image),
    document_annotation_format=response_format_from_pydantic_model(Document),
    include_image_base64=True
  )

# Display combined markdowns and images
display(Markdown(get_combined_markdown_annotated(annotations_response)))