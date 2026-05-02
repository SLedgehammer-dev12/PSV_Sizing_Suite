import sys
import os

# Add the root directory to sys.path to ensure absolute imports work
if getattr(sys, 'frozen', False):
    sys.path.insert(0, sys._MEIPASS)
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QDialog
from desktop.app import PSVSizingApp, LoginDialog

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    login = LoginDialog()
    if login.exec_() == QDialog.Accepted:
        window = PSVSizingApp(role=login.role)
        window.show()
        sys.exit(app.exec_())
