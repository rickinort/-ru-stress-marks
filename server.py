import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.responses import FileResponse
from processor import StressProcessor
import config

app = FastAPI(title="Russian Stress Marks Service")
processor = StressProcessor()

class TextRequest(BaseModel):
    text: str

class TextResponse(BaseModel):
    original: str
    processed: str

@app.post("/api/stress", response_model=TextResponse)
async def add_stress(request: TextRequest):
    if not request.text.strip():
        return TextResponse(original="", processed="")

    if not processor.wait_until_ready():
        raise HTTPException(status_code=503, detail="Model is still loading...")

    if not processor.is_ready:
        raise HTTPException(status_code=503, detail=f"Model error: {processor._error}")

    try:
        processed = processor.process(request.text)
        return TextResponse(original=request.text, processed=processed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    return {
        "status": "ready" if processor.is_ready else "loading",
        "model": "turbo"
    }

# Раздача статики
if getattr(sys, 'frozen', False):
    static_dir = os.path.join(sys._MEIPASS, "static")
else:
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
