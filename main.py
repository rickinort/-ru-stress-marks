import threading
import time
import webbrowser
import uvicorn
from server import app, processor
import config
import logging
import sys
import os

# Настройка логирования в файл для портативной версии
log_path = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else ".", "service_error.log")

# Заглушка для stdout/stderr в режиме без консоли
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def open_browser():
    """Открывает браузер через паузу после старта сервера."""
    time.sleep(2)
    url = f"http://{config.HOST}:{config.PORT}"
    print(f"Opening browser at {url}...")
    webbrowser.open(url)

if __name__ == "__main__":
    logger.info("Starting Russian Stress Marks Service (Portable)...")
    
    # Запускаем загрузку моделей в фоне
    processor.start_loading()
    
    # Запускаем браузер
    threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        uvicorn.run(
            app, 
            host=config.HOST, 
            port=config.PORT, 
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    except KeyboardInterrupt:
        logger.info("Service stopped by user.")
