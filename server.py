import os
import re
import sys
import threading
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.responses import FileResponse

app = FastAPI(title="Russian Stress Marks Service")

ACUTE_ACCENT = "\u0301"

accentizer = None
_model_loading = False
_model_ready = threading.Event()

def load_model():
    global accentizer, _model_loading
    _model_loading = True
    try:
        from ruaccent import RUAccent
        print("Loading RUAccent models...")
        a = RUAccent()
        a.load(omograph_model_size='turbo', use_dictionary=False)
        accentizer = a
        print("Models loaded successfully.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR loading models: {e}")
    finally:
        _model_loading = False
        _model_ready.set()

# Load models in a background thread so the server starts immediately
threading.Thread(target=load_model, daemon=True).start()


class TextRequest(BaseModel):
    text: str

class TextResponse(BaseModel):
    original: str
    processed: str

def convert_plus_to_unicode(text: str) -> str:
    return re.sub(r'\+([\u0430\u0435\u0451\u0438\u043e\u0443\u044b\u044d\u044e\u044f\u0410\u0415\u0401\u0418\u041e\u0423\u042b\u042d\u042e\u042f])', r'\1' + ACUTE_ACCENT, text)

@app.post("/api/stress", response_model=TextResponse)
async def add_stress(request: TextRequest):
    if not request.text.strip():
        return TextResponse(original="", processed="")

    # Wait up to 300 seconds for model to be ready
    if not _model_ready.wait(timeout=300):
        raise HTTPException(status_code=503, detail="Model is still loading, try again in a moment.")

    if accentizer is None:
        raise HTTPException(status_code=503, detail="Model failed to load. Check server logs.")

    try:
        processed = accentizer.process_all(request.text)
        visual_text = convert_plus_to_unicode(processed)
        return TextResponse(original=request.text, processed=visual_text)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    ready = _model_ready.is_set() and accentizer is not None
    return {"status": "ready" if ready else "loading", "model": "turbo"}

# Serve static files
if getattr(sys, 'frozen', False):
    # If running as EXE
    bundle_dir = sys._MEIPASS
    static_dir = os.path.join(bundle_dir, "static")
else:
    # If running as script
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
