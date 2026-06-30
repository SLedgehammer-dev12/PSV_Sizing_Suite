import streamlit.web.cli as stcli
import os
import sys
import threading
import time
import webbrowser
import socket

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

def open_browser():
    for _ in range(20):
        try:
            with socket.create_connection(("localhost", 8501), timeout=0.5):
                break
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(0.5)
    webbrowser.open("http://localhost:8501")

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    web_app_path = os.path.join(base_path, "web_app.py")
    sys.argv = [
        "streamlit", "run", web_app_path,
        "--server.headless=true",
        "--server.port=8501",
        "--browser.gatherUsageStats=false",
        "--client.toolbarMode=minimal",
    ]
    os.environ["STREAMLIT_DEVELOPMENT_MODE"] = "false"
    sys.exit(stcli.main())
