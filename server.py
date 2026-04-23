import os
import re
import sys
import threading
import webbrowser
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
        # Справочник ручных исправлений
        custom_dict = {
            "узнаете": "узн+аете",
            "узнаёте": "узн+аете",
            "лет": "лет",            
            "после": "после",
            "это": "это",           # Убираем ударение
            "изо": "изо",           # Убираем ударение
        }
        
        # Справочник для слов с двойным смыслом (омографов)
        custom_homographs = {
            "боли": ["б+оли"], # По умолчанию ставим на первый слог, если контекст подвел
            "узнаете": ["узн+аете"]
        }

        print("Loading RUAccent models...")
        # Указываем turbo, так как tiny2.1 глючит на входах ONNX
        a = RUAccent()
        a.load(
            omograph_model_size="turbo", 
            use_dictionary=False, 
            custom_dict=custom_dict,
            custom_homographs=custom_homographs
        )
        # Гарантируем, что "лет" не станет "лёт"
        if hasattr(a, 'yo_words'):
            a.yo_words.pop("лет", None)
            a.yo_words["лет"] = "лет"
            
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
        
        # Раз и навсегда: бронебойный метод через регулярку, которая видит ударения
        def final_clean(text):
            to_remove = ["после", "это", "изо", "лет"]
            
            # Функция для обработки найденного слова
            def word_fix(match):
                word = match.group(0)
                # Чистая версия для проверки (без ударения и к 'е')
                test = word.replace(ACUTE_ACCENT, "").replace("ё", "е").lower()
                
                # 1. Если это исключение на удаление ударений
                if test in to_remove:
                    res = word.replace(ACUTE_ACCENT, "")
                    if test == "лет": res = res.replace("ё", "е")
                    return res
                
                # 2. Если это "узнаете"
                if test == "узнаете":
                    res = "узна" + ACUTE_ACCENT + "ете"
                    if word[0].isupper(): res = res.capitalize()
                    return res
                
                return word

            # Ищем последовательности русских букв ВКЛЮЧАЯ буквы со значком ударения
            # [а-яА-ЯёЁ\u0301]+ -- это обеспечит, что слово не развалится
            pattern = re.compile(r'[а-яА-ЯёЁ' + ACUTE_ACCENT + r']+')
            return re.sub(pattern, word_fix, text)

        visual_text = final_clean(visual_text)
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
    import threading
    import time

    def open_browser():
        time.sleep(3)  # Увеличим до 3 секунд для надежности
        webbrowser.open("http://127.0.0.1:8000")

    threading.Thread(target=open_browser, daemon=True).start()

    # Полностью отключаем логи, чтобы не было ошибки isatty
    config = uvicorn.Config(
        app, 
        host="127.0.0.1", 
        port=8000, 
        log_config=None  # Глушим логирование на корню
    )
    server = uvicorn.Server(config)
    server.run()
