import sys
import os
import json

# Add parent directory to path so 'core' and 'desktop' can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QAction, 
                             QFileDialog, QMessageBox, QLineEdit, QComboBox, QLabel)

from desktop.tabs import LiquidReliefTab, GasReliefTab, TwoPhaseReliefTab
from desktop.tabs_extra import FireWettedTab, FireUnwettedTab, ThermalExpansionTab
from desktop.report_generator import generate_and_open_report
from desktop.graph_window import PlotWindow
from desktop.auth import check_login, change_password
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox, QInputDialog

class PSVSizingApp(QMainWindow):
    def __init__(self, role="user"):
        super().__init__()
        self.role = role
        self.setWindowTitle(f"PSV Sizing Suite - Advanced Engineering v2.1 ({self.role.upper()})")
        self.setMinimumSize(950, 700)
        self.init_ui()
        self.create_menus()

    def init_ui(self):
        self.tabs = QTabWidget()
        
        self.tab_liquid = LiquidReliefTab()
        self.tab_gas = GasReliefTab()
        self.tab_twophase = TwoPhaseReliefTab()
        self.tab_fire_wetted = FireWettedTab()
        self.tab_fire_unwetted = FireUnwettedTab()
        self.tab_thermal = ThermalExpansionTab()
        
        self.tabs.addTab(self.tab_liquid, "1. Liquid Relief")
        self.tabs.addTab(self.tab_gas, "2. Gas/Vapor Relief")
        self.tabs.addTab(self.tab_twophase, "3. Two-Phase (Flashing)")
        self.tabs.addTab(self.tab_fire_wetted, "4. Fire (Wetted)")
        self.tabs.addTab(self.tab_fire_unwetted, "5. Fire (Unwetted)")
        self.tabs.addTab(self.tab_thermal, "6. Thermal Expansion")
        
        self.tabs.setStyleSheet("""
            QTabBar::tab { height: 35px; width: 150px; font-weight: bold; }
        """)

        self.setCentralWidget(self.tabs)

    def create_menus(self):
        menubar = self.menuBar()

        # DOSYA (FILE) MENU
        file_menu = menubar.addMenu("Dosya (File)")
        
        save_action = QAction("Kaydet (Save Inputs)", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_state)
        file_menu.addAction(save_action)

        load_action = QAction("Yükle (Load Inputs)", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load_state)
        file_menu.addAction(load_action)

        # RAPOR (REPORT) MENU
        report_menu = menubar.addMenu("Rapor (Report)")
        
        gen_report_action = QAction("HTML Raporu Oluştur (Generate Report)", self)
        gen_report_action.setShortcut("Ctrl+R")
        gen_report_action.triggered.connect(self.generate_report)
        report_menu.addAction(gen_report_action)

        # GRAFİK (GRAPHS) MENU
        graph_menu = menubar.addMenu("Grafik (Graphs)")
        
        plot_action = QAction("Eğri ve Performans Grafiği (Show Graph)", self)
        plot_action.triggered.connect(self.show_graph)
        graph_menu.addAction(plot_action)

        # GÜNCELLEME (UPDATE) MENU
        update_menu = menubar.addMenu("Güncelleme (Update)")
        
        check_update_action = QAction("Güncellemeleri Kontrol Et (Check for Updates)", self)
        check_update_action.triggered.connect(self.check_update)
        update_menu.addAction(check_update_action)

        if self.role == "admin":
            admin_menu = menubar.addMenu("Yönetici (Admin)")
            change_pw_action = QAction("Kullanıcı Şifresini Değiştir", self)
            change_pw_action.triggered.connect(self.change_user_pw)
            admin_menu.addAction(change_pw_action)

    # --- MENU ACTION METHODS ---

    def extract_tab_data(self, tab_widget):
        """Helper to extract data from a tab's line edits and combo boxes."""
        inputs = {}
        results = {}
        
        # Iterate over all attributes of the tab
        for attr_name, obj in tab_widget.__dict__.items():
            if isinstance(obj, QLineEdit):
                inputs[attr_name] = obj.text()
            elif isinstance(obj, QComboBox):
                inputs[attr_name] = obj.currentText()
            elif isinstance(obj, QLabel) and attr_name.startswith("res_"):
                # Result labels
                results[attr_name] = obj.text()
                
        # Special handling for tables
        if hasattr(tab_widget, 'comp_table'):
            table_data = []
            for row in range(tab_widget.comp_table.rowCount()):
                combo = tab_widget.comp_table.cellWidget(row, 0)
                edit = tab_widget.comp_table.cellWidget(row, 1)
                if combo and edit:
                    table_data.append({
                        "fluid": combo.currentText(),
                        "fraction": edit.text()
                    })
            inputs['__comp_table__'] = table_data
                
        return inputs, results

    def restore_tab_data(self, tab_widget, data):
        """Helper to restore data to a tab's widgets."""
        for attr_name, val in data.items():
            if attr_name == '__comp_table__' and hasattr(tab_widget, 'comp_table'):
                # Clear existing
                tab_widget.comp_table.setRowCount(0)
                # Repopulate
                for row_data in val:
                    tab_widget.add_fluid_row()
                    row = tab_widget.comp_table.rowCount() - 1
                    tab_widget.comp_table.cellWidget(row, 0).setCurrentText(row_data['fluid'])
                    tab_widget.comp_table.cellWidget(row, 1).setText(row_data['fraction'])
                if hasattr(tab_widget, 'update_property_inputs_state'):
                    tab_widget.update_property_inputs_state()
            elif hasattr(tab_widget, attr_name):
                obj = getattr(tab_widget, attr_name)
                if isinstance(obj, QLineEdit):
                    obj.setText(str(val))
                elif isinstance(obj, QComboBox):
                    obj.setCurrentText(str(val))

    def save_state(self):
        current_tab = self.tabs.currentWidget()
        inputs, _ = self.extract_tab_data(current_tab)
        
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Verileri Kaydet", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(inputs, f, indent=4)
            QMessageBox.information(self, "Başarılı", "Girdi değerleri başarıyla kaydedildi!")

    def load_state(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Verileri Yükle", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    inputs = json.load(f)
                current_tab = self.tabs.currentWidget()
                self.restore_tab_data(current_tab, inputs)
                QMessageBox.information(self, "Başarılı", "Girdi değerleri yüklendi!")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya okunamadı: {e}")

    def generate_report(self):
        current_tab_name = self.tabs.tabText(self.tabs.currentIndex())
        current_tab = self.tabs.currentWidget()
        inputs, results = self.extract_tab_data(current_tab)
        
        # Check if calculated
        has_results = any(v != "-" and v != "Error" and v != "Calculating..." for v in results.values())
        if not has_results:
            QMessageBox.warning(self, "Uyarı", "Lütfen rapor oluşturmadan önce HESAPLA butonuna basarak sonuçları elde edin.")
            return
            
        try:
            generate_and_open_report(current_tab_name, inputs, results)
        except Exception as e:
            QMessageBox.critical(self, "Rapor Hatası", f"Rapor oluşturulurken hata oluştu: {e}")

    def show_graph(self):
        current_tab_name = self.tabs.tabText(self.tabs.currentIndex())
        current_tab = self.tabs.currentWidget()
        
        if not hasattr(current_tab, 'last_inputs'):
            QMessageBox.warning(self, "Uyarı", "Lütfen grafik oluşturmadan önce HESAPLA butonuna basarak sonuçları elde edin.")
            return
            
        _, results = self.extract_tab_data(current_tab)
        
        has_results = any(v != "-" and v != "Error" and v != "Calculating..." for v in results.values())
        if not has_results:
            QMessageBox.warning(self, "Uyarı", "Lütfen grafik oluşturmadan önce HESAPLA butonuna basarak sonuçları elde edin.")
            return

        self.plot_win = PlotWindow(self, current_tab_name, current_tab.last_inputs, results)
        self.plot_win.exec_()

    def check_update(self):
        QMessageBox.information(self, "Güncelleme", "PSV Sizing Suite (v2.1)\n\nProgramınız güncel.")

    def change_user_pw(self):
        new_pw, ok = QInputDialog.getText(self, "Şifre Değiştir", "Yeni Kullanıcı Şifresini Girin:", QLineEdit.Password)
        if ok and new_pw:
            change_password("user", new_pw)
            QMessageBox.information(self, "Başarılı", "Kullanıcı şifresi başarıyla değiştirildi!")

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sisteme Giriş")
        self.setFixedSize(300, 150)
        self.role = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.user_input = QComboBox()
        self.user_input.addItems(["user", "admin"])
        
        self.pw_input = QLineEdit()
        self.pw_input.setEchoMode(QLineEdit.Password)
        
        form.addRow("Kullanıcı:", self.user_input)
        form.addRow("Şifre:", self.pw_input)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.attempt_login)
        self.buttons.rejected.connect(self.reject)
        
        layout.addLayout(form)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

    def attempt_login(self):
        username = self.user_input.currentText()
        password = self.pw_input.text()
        
        if check_login(username, password):
            self.role = username
            self.accept()
        else:
            QMessageBox.warning(self, "Hata", "Hatalı şifre! Lütfen tekrar deneyin.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    login = LoginDialog()
    if login.exec_() == QDialog.Accepted:
        window = PSVSizingApp(role=login.role)
        window.show()
        sys.exit(app.exec_())
