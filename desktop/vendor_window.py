from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel
from PyQt5.QtCore import Qt
from core.vendor_catalog import get_vendor_valves

class VendorTableWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Üretici (Manufacturer)", 
            "Seri (Series)", 
            "Model Kodu", 
            "Dizayn (Design)", 
            "Giriş/Çıkış Çapı", 
            "Gerçek Alan (mm2)"
        ])
        
        header = self.table.horizontalHeader()
        for i in range(6):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setMinimumHeight(150)
        
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)

    def update_valves(self, api_letter):
        api_letter = api_letter.split('(')[0].strip() if api_letter else "-"
        valves = get_vendor_valves(api_letter)
        self.table.setRowCount(len(valves))
        for row, v in enumerate(valves):
            self.table.setItem(row, 0, QTableWidgetItem(str(v.get("manufacturer", ""))))
            self.table.setItem(row, 1, QTableWidgetItem(str(v.get("series", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(v.get("model_code", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(str(v.get("design_type", ""))))
            self.table.setItem(row, 4, QTableWidgetItem(str(v.get("inlet_outlet_size_in", ""))))
            
            area_item = QTableWidgetItem(str(v.get("actual_area_mm2", "")))
            area_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, area_item)
