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

import traceback

from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from desktop.app import PSVSizingApp, LoginDialog


def global_excepthook(exc_type, exc_value, exc_tb):
    """Handle unhandled exceptions without letting PyQt5 call qFatal/abort.

    PyQt5 aborts the process (SIGABRT) when an unhandled Python exception
    escapes a slot and sys.excepthook is left at its default. Installing a
    custom hook makes PyQt5 route the error here instead, so we can log the
    full traceback and inform the user without crashing.
    """
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.critical("Unhandled exception:\n%s", tb_text)
    try:
        QMessageBox.critical(
            None,
            "Beklenmeyen Hata",
            f"Beklenmeyen bir hata oluştu:\n\n{tb_text}\n\n"
            f"Detaylar log dosyasına yazıldı.",
        )
    except Exception:
        pass


sys.excepthook = global_excepthook

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
