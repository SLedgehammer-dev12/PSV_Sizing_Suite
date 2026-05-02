import streamlit.web.cli as stcli
import os
import sys
import threading
import time
import webbrowser

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

def open_browser():
    time.sleep(3) # Wait for server to start
    webbrowser.open("http://localhost:8501")

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    sys.argv = ["streamlit", "run", os.path.join(base_path, "web_app.py"), "--server.headless=true", "--global.developmentMode=false"]
    sys.exit(stcli.main())
