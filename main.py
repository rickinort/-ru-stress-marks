import os
import sys
import webbrowser
import threading
import uvicorn
from server import app

def open_browser():
    # Wait a bit for the server to start
    import time
    time.sleep(2)
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    # Start browser in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start server
    print("Starting Russian Stress Marks Service...")
    print("The interface will open in your browser shortly.")
    print("To stop the service, close this console window.")
    
    # We use 8000 locally as requested
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")
