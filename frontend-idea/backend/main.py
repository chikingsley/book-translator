"""FastAPI backend for OCR PDF viewer application."""

import os
import traceback
import uuid
from pathlib import Path

import pymupdf
import uvicorn
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.bun_ocr_pdf_viewer.mistralocr_extractor import run_ocr

# Create directories if they don't exist
UPLOADS_DIR = Path("uploads")
STATIC_DIR = Path("static")
UPLOADS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the static directory to serve images
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.post("/api/ocr")
async def ocr_pdf(file: UploadFile):
    """Process a PDF file through OCR.

    Accept a PDF file, save it, convert its pages to images,
    run OCR on it, and return the structured OCR data.
    """
    try:
        # Save the uploaded PDF
        session_id = str(uuid.uuid4())
        pdf_path = UPLOADS_DIR / f"{session_id}_{file.filename}"
        with open(pdf_path, "wb") as buffer:
            buffer.write(await file.read())

        # 1. Convert PDF pages to images
        doc = pymupdf.open(pdf_path)
        image_paths = []
        image_files = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=300)
            image_path = STATIC_DIR / f"{session_id}_page_{i + 1}.png"
            pix.save(image_path)
            image_paths.append(f"/static/{session_id}_page_{i + 1}.png")
            image_files.append(str(image_path))
        doc.close()

        # 2. Extract text with positions using PyMuPDF
        doc = pymupdf.open(pdf_path)
        ocr_pages = []
        
        for i, (page, image_file) in enumerate(zip(doc, image_files, strict=False)):
            # Get text with positions from PyMuPDF
            words = []
            text_dict = page.get_text("dict")
            
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                bbox = span.get("bbox", [0, 0, 0, 0])
                                words.append({
                                    "text": text,
                                    "bbox": bbox  # [x0, y0, x1, y1]
                                })
            
            # Also run Mistral OCR for markdown
            mistral_result = await run_ocr(image_file)
            markdown = ""
            if mistral_result.get("pages"):
                markdown = mistral_result["pages"][0].get("markdown", "")
            
            ocr_pages.append({
                "page_number": i + 1,
                "words": words,
                "markdown": markdown,
                "width": page.rect.width,
                "height": page.rect.height
            })
        
        doc.close()
        ocr_result = {"pages": ocr_pages}

        # 3. Combine results and return
        response_data = {
            "session_id": session_id,
            "pages": []
        }
        for i, page_data in enumerate(ocr_result.get("pages", [])):
            page_data["image_url"] = image_paths[i]
            response_data["pages"].append(page_data)
            
        # Clean up the uploaded PDF file
        os.remove(pdf_path)

        return JSONResponse(content=response_data)

    except Exception as e:
        print(f"Error processing PDF: {e!s}")
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e), "traceback": traceback.format_exc()})

@app.post("/api/save-markdown")
async def save_markdown(data: dict):
    """Save edited text as markdown file."""
    try:
        session_id = data.get("session_id", "untitled")
        page_number = data.get("page_number", 1)
        text = data.get("text", "")
        
        # Save to markdown file
        markdown_dir = Path("markdown_exports")
        markdown_dir.mkdir(exist_ok=True)
        
        filename = markdown_dir / f"{session_id}_page_{page_number}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)
        
        return JSONResponse(content={"success": True, "filename": str(filename)})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/")
def read_root():
    """Return API status message."""
    return {"message": "OCR PDF Viewer Backend is running."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)