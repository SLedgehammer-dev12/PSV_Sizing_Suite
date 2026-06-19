import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl
from core.report import generate_report


def generate_and_open_report(tab_name: str, inputs_dict: dict, results_dict: dict):
    path = generate_report(tab_name, inputs_dict, results_dict)
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))
