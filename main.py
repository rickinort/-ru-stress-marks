import threading
import time
import webbrowser
import uvicorn
from server import app, processor
import config

def open_browser():
    """Открывает браузер через паузу после старта сервера."""
    time.sleep(2)
    url = f"http://{config.HOST}:{config.PORT}"
    print(f"Opening browser at {url}...")
    webbrowser.open(url)

if __name__ == "__main__":
    print("Starting Russian Stress Marks Service (Portable)...")
    
    # Запускаем загрузку моделей в фоне
    processor.start_loading()
    
    # Запускаем браузер
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Конфиг сервера
    uvicorn_config = uvicorn.Config(
        app, 
        host=config.HOST, 
        port=config.PORT, 
        log_level="info"
    )
    server = uvicorn.Server(uvicorn_config)
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nService stopped by user.")
