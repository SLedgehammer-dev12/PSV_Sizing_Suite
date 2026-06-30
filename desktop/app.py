import sys
import os
import json
import re

# Add parent directory to path so 'core' and 'desktop' can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QAction, 
                             QFileDialog, QMessageBox, QLineEdit, QComboBox, QLabel)

from desktop.tabs import LiquidReliefTab, GasReliefTab, TwoPhaseReliefTab
from desktop.tabs_extra import FireWettedTab, FireUnwettedTab, ThermalExpansionTab
from desktop.report_generator import generate_and_open_report
from desktop.graph_window import PlotWindow
from desktop.auth import check_login, change_password, must_change_password, set_password_changed, get_lockout_remaining
from desktop.workers import UpdateCheckWorker
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox, QInputDialog

APP_VERSION = "v2.2"
SCHEMA_VERSION = '2.2'
GITHUB_RELEASES_URL = "https://api.github.com/repos/SLedgehammer-dev12/PSV_Sizing_Suite/releases/latest"
GITHUB_RELEASES_PAGE = "https://github.com/SLedgehammer-dev12/PSV_Sizing_Suite/releases/latest"


def parse_version(version_str):
    match = re.search(r"v?(\d+)\.(\d+)(?:\.(\d+))?", version_str)
    if not match:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3) or 0))

class PSVSizingApp(QMainWindow):
    def __init__(self, role="user"):
        super().__init__()
        self.role = role
        self.setWindowTitle(f"PSV Sizing Suite - Advanced Engineering {APP_VERSION} ({self.role.upper()})")
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
        all_tabs_data = {}
        tab_names = ["liquid", "gas", "twophase", "fire_wetted", "fire_unwetted", "thermal"]
        tab_widgets = [self.tab_liquid, self.tab_gas, self.tab_twophase,
                       self.tab_fire_wetted, self.tab_fire_unwetted, self.tab_thermal]

        for name, widget in zip(tab_names, tab_widgets):
            inputs, _ = self.extract_tab_data(widget)
            all_tabs_data[name] = inputs

        all_tabs_data['__schema_version__'] = SCHEMA_VERSION
        all_tabs_data['__current_tab__'] = self.tabs.tabText(self.tabs.currentIndex())

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Projeyi Kaydet", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(all_tabs_data, f, indent=4)
            QMessageBox.information(self, "Başarılı", "Tüm girdi değerleri başarıyla kaydedildi!")

    def load_state(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Projeyi Yükle", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                schema_ver = data.get('__schema_version__', '1.0')
                try:
                    schema_num = float(schema_ver)
                except ValueError:
                    schema_num = 1.0
                if schema_num < 2.0:
                    reply = QMessageBox.question(self, "Uyumluluk",
                        f"Bu dosya v{schema_ver} formatında. Yüklenebilir ancak bazı alanlar eksik olabilir. Devam etmek istiyor musunuz?",
                        QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.No:
                        return

                tab_names = ["liquid", "gas", "twophase", "fire_wetted", "fire_unwetted", "thermal"]
                tab_widgets = [self.tab_liquid, self.tab_gas, self.tab_twophase,
                               self.tab_fire_wetted, self.tab_fire_unwetted, self.tab_thermal]

                if 'tabs' in data:
                    for name, widget in zip(tab_names, tab_widgets):
                        if name in data['tabs']:
                            self.restore_tab_data(widget, data['tabs'][name])
                else:
                    for name, widget in zip(tab_names, tab_widgets):
                        if name in data:
                            self.restore_tab_data(widget, data[name])

                current_tab_name = data.get('__current_tab__', data.get('__tab_name__'))
                if current_tab_name:
                    for i in range(self.tabs.count()):
                        if self.tabs.tabText(i) == current_tab_name:
                            self.tabs.setCurrentIndex(i)
                            break

                QMessageBox.information(self, "Başarılı", "Tüm girdi değerleri yüklendi!")
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
        self.calc_btn_update = self.sender()
        if self.calc_btn_update:
            self.calc_btn_update.setEnabled(False)
        self._update_status = QLabel("Güncelleme kontrol ediliyor...", self)
        self._update_status.setStyleSheet("color: #7f8c8d; font-style: italic;")
        self.statusBar().addWidget(self._update_status)

        self.update_worker = UpdateCheckWorker(GITHUB_RELEASES_URL)
        self.update_worker.finished.connect(self._on_update_check_success)
        self.update_worker.error.connect(self._on_update_check_error)
        self.update_worker.start()

    def _on_update_check_success(self, data):
        if hasattr(self, '_update_status'):
            self.statusBar().removeWidget(self._update_status)
            del self._update_status
        if self.calc_btn_update:
            self.calc_btn_update.setEnabled(True)

        latest_tag = data.get("tag_name", "")
        release_notes = data.get("body", "")
        html_url = data.get("html_url", GITHUB_RELEASES_PAGE)

        if not latest_tag:
            self._show_update_error("Sürüm bilgisi alınamadı.")
            return

        current = parse_version(APP_VERSION)
        latest = parse_version(latest_tag)

        if latest > current:
            self._show_update_available(latest_tag, release_notes, html_url)
        else:
            QMessageBox.information(self, "Güncelleme", f"PSV Sizing Suite ({APP_VERSION})\n\nProgramınız güncel.")

    def _on_update_check_error(self, err_msg):
        if hasattr(self, '_update_status'):
            self.statusBar().removeWidget(self._update_status)
            del self._update_status
        if self.calc_btn_update:
            self.calc_btn_update.setEnabled(True)
        self._show_update_error(err_msg)

    def _show_update_available(self, tag, notes, url):
        notes_preview = (notes[:500] + "...") if len(notes) > 500 else notes
        msg = (
            f"Yeni sürüm mevcut: {tag}\n"
            f"Mevcut sürüm: {APP_VERSION}\n\n"
            f"Değişiklikler:\n{notes_preview}\n\n"
            f"İndirmek için 'Evet' butonuna basın."
        )
        reply = QMessageBox.question(self, "Güncelleme Mevcut", msg, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            import webbrowser
            webbrowser.open(url)

    def _show_update_error(self, reason):
        QMessageBox.warning(
            self, "Güncelleme Hatası",
            f"{reason}\n\nLütfen internet bağlantınızı kontrol edin veya "
            f"{GITHUB_RELEASES_PAGE} adresini ziyaret edin."
        )

    def change_user_pw(self):
        admin_pw, ok = QInputDialog.getText(self, "Admin Dogrulama", "Admin sifrenizi tekrar girin:", QLineEdit.Password)
        if not ok or not check_login("admin", admin_pw):
            QMessageBox.warning(self, "Hata", "Admin sifresi dogrulanamadi!")
            return
        new_pw, ok = QInputDialog.getText(self, "Sifre Degistir", "Yeni Kullanici Sifresini Girin (en az 8 karakter):", QLineEdit.Password)
        if ok and new_pw and len(new_pw) >= 8:
            change_password("user", new_pw)
            QMessageBox.information(self, "Basarili", "Kullanici sifresi basariyla degistirildi!")
        elif ok:
            QMessageBox.warning(self, "Hata", "Sifre en az 8 karakter olmalidir.")

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

        lockout = get_lockout_remaining(username)
        if lockout > 0:
            mins = lockout // 60
            secs = lockout % 60
            QMessageBox.warning(self, "Hesap Kilitlendi",
                f"Cok fazla hatali giris denemesi. Lutfen {mins} dakika {secs} saniye sonra tekrar deneyin.")
            return

        if check_login(username, password):
            self.role = username
            if must_change_password(username):
                self._prompt_password_change(username)
            else:
                self.accept()
        else:
            QMessageBox.warning(self, "Hata", "Hatali sifre! Lutfen tekrar deneyin.")

    def _prompt_password_change(self, username):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Sifre Degisimi Gerekli")
        msg.setText("Guvenlik nedeniyle sifrenizi degistirmeniz gerekmektedir.")
        msg.setInformativeText("Varsayilan sifre ile giris yapilamaz. Lutfen yeni bir sifre belirleyin.")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        if msg.exec_() != QMessageBox.Ok:
            return

        while True:
            new_pw, ok = QInputDialog.getText(self, "Yeni Sifre", "Yeni sifrenizi girin (en az 8 karakter):", QLineEdit.Password)
            if not ok:
                return
            if not new_pw:
                QMessageBox.warning(self, "Hata", "Sifre bos birakilamaz.")
                continue
            if len(new_pw) < 8:
                QMessageBox.warning(self, "Hata", "Sifre en az 8 karakter olmalidir.")
                continue
            change_password(username, new_pw)
            set_password_changed(username)
            QMessageBox.information(self, "Basarili", "Sifreniz basariyla degistirildi!")
            self.accept()
            break
