import sys
import os
import logging

if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)
    log_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'PSV Sizing Suite', 'logs')
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.dirname(os.path.abspath(__file__))

os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "psv_sizing_suite.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)

from PyQt5.QtWidgets import QApplication, QDialog
from desktop.app import PSVSizingApp, LoginDialog

if __name__ == "__main__":
    logging.info("PSV Sizing Suite starting up")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    login = LoginDialog()
    if login.exec_() == QDialog.Accepted:
        logging.info("User logged in as: %s", login.role)
        window = PSVSizingApp(role=login.role)
        window.show()
        sys.exit(app.exec_())
