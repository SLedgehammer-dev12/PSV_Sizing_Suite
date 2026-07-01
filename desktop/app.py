import sys
import os
import json
import re
import platform
import subprocess
import shutil
import time
import webbrowser

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QAction,
                             QFileDialog, QMessageBox, QLineEdit, QComboBox, QLabel,
                             QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QDialogButtonBox, QInputDialog, QProgressBar, QPushButton)
from PyQt5.QtCore import Qt

from desktop.tabs import LiquidReliefTab, GasReliefTab, TwoPhaseReliefTab
from desktop.tabs_extra import FireWettedTab, FireUnwettedTab, ThermalExpansionTab
from desktop.report_generator import generate_and_open_report
from desktop.graph_window import PlotWindow
from desktop.auth import check_login, change_password, must_change_password, set_password_changed, get_lockout_remaining
from desktop.workers import UpdateCheckWorker, UpdateDownloadWorker
from core import __version_tag__

APP_VERSION = __version_tag__
SCHEMA_VERSION = '2.3'
GITHUB_RELEASES_URL = "https://api.github.com/repos/SLedgehammer-dev12/PSV_Sizing_Suite/releases/latest"
GITHUB_RELEASES_PAGE = "https://github.com/SLedgehammer-dev12/PSV_Sizing_Suite/releases/latest"


def parse_version(version_str):
    match = re.search(r"v?(\d+)\.(\d+)(?:\.(\d+))?", version_str)
    if not match:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3) or 0))


def get_platform_info():
    system = platform.system()
    frozen = getattr(sys, 'frozen', False)
    is_managed = False
    if frozen:
        exe_dir = os.path.dirname(sys.executable)
        if "Program Files" in exe_dir:
            is_managed = True
    return {"os": system, "frozen": frozen, "is_managed": is_managed}


def select_asset(assets, platform_info):
    if not assets:
        return None
    os_name = platform_info["os"]
    is_managed = platform_info["is_managed"]
    for asset in assets:
        name = asset.get("name", "")
        if os_name == "Windows":
            if is_managed and "Setup_" in name and name.endswith(".exe"):
                return asset
            if not is_managed and "Desktop_" in name and name.endswith(".zip"):
                return asset
        elif os_name == "Darwin" and name.endswith(".dmg"):
            return asset
    return None


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
        update_menu = menubar.addMenu("Guncelleme (Update)")
        
        check_update_action = QAction("Guncellemeleri Kontrol Et (Check for Updates)", self)
        check_update_action.triggered.connect(self.check_update)
        update_menu.addAction(check_update_action)

        # YARDIM (HELP) MENU
        help_menu = menubar.addMenu("Yardim (Help)")
        
        about_action = QAction("Hakkinda (About)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        if self.role == "admin":
            admin_menu = menubar.addMenu("Yönetici (Admin)")
            change_pw_action = QAction("Kullanıcı Şifresini Değiştir", self)
            change_pw_action.triggered.connect(self.change_user_pw)
            admin_menu.addAction(change_pw_action)

    # --- MENU ACTION METHODS ---

    def extract_tab_data(self, tab_widget):
        """Extract user inputs and computed results from a tab widget."""
        inputs = {}
        results = {}

        SKIP_ATTRS = {
            'calc_btn', 'pdf_btn', 'graph_btn', 'progress', 'btn_layout',
            'main_layout', 'vendor_table_widget', 'tab_name',
            'calc_button_text', 'calc_button_color', 'last_inputs',
            'last_res', 'worker', 'plot_win', 'coolprop_fluids',
            'comp_table', 'frac_type_combo', 'btn_add_fluid', 'btn_remove_fluid',
            'res_area_unit',
        }

        for attr_name, obj in tab_widget.__dict__.items():
            if attr_name in SKIP_ATTRS:
                continue
            if isinstance(obj, QLineEdit):
                inputs[attr_name] = obj.text()
            elif isinstance(obj, QComboBox):
                inputs[attr_name] = obj.currentText()
            elif isinstance(obj, QLabel) and attr_name.startswith("res_"):
                results[attr_name] = obj.text()

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
        assets = data.get("assets", [])

        if not latest_tag:
            self._show_update_error("Sürüm bilgisi alınamadı.")
            return

        current = parse_version(APP_VERSION)
        latest = parse_version(latest_tag)

        if latest > current:
            self._show_update_available(latest_tag, release_notes, html_url, assets)
        else:
            QMessageBox.information(self, "Güncelleme", f"PSV Sizing Suite ({APP_VERSION})\n\nProgramınız güncel.")

    def _on_update_check_error(self, err_msg):
        if hasattr(self, '_update_status'):
            self.statusBar().removeWidget(self._update_status)
            del self._update_status
        if self.calc_btn_update:
            self.calc_btn_update.setEnabled(True)
        self._show_update_error(err_msg)

    def _show_update_available(self, tag, notes, url, assets):
        notes_preview = (notes[:300] + "...") if len(notes) > 300 else notes
        asset = select_asset(assets, get_platform_info())
        download_text = ""
        if asset:
            size_mb = asset.get("size", 0) // 1048576
            download_text = f"\nDosya: {asset.get('name', '')} ({size_mb} MB)"
        msg = (
            f"Yeni surum mevcut: {tag}\n"
            f"Mevcut surum: {APP_VERSION}\n\n"
            f"Degisiklikler:\n{notes_preview}\n\n"
            f"Indirilip kurulsun mu?{download_text}"
        )
        reply = QMessageBox.question(self, "Guncelleme Mevcut", msg, QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if not asset:
                webbrowser.open(url)
                return
            dialog = DownloadDialog(tag, asset, self)
            dialog.start_download()
            if dialog.exec_() == QDialog.Accepted and dialog.downloaded_path:
                self._install_downloaded_update(dialog.downloaded_path, asset.get("name", ""))

    def _install_downloaded_update(self, file_path, asset_name):
        system = platform.system()
        info = get_platform_info()
        reply = QMessageBox.question(
            self, "Kurulum",
            "Kurulum baslatilacak. Program kapatilacak.\nDevam etmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        backup_dir = None
        if info["frozen"]:
            backup_dir = self._backup_current_version()

        if system == "Windows":
            if info["is_managed"] and asset_name.endswith(".exe"):
                self._install_windows_managed(file_path)
            else:
                self._install_windows_portable(file_path)
        elif system == "Darwin":
            self._install_macos(file_path)
        else:
            QMessageBox.warning(self, "Hata", f"Bu isletim sistemi icin otomatik kurulum desteklenmiyor: {system}")
            if backup_dir:
                self._show_rollback_option(backup_dir)

    def _backup_current_version(self):
        exe_path = sys.executable
        exe_dir = os.path.dirname(exe_path)
        backup_root = os.path.join(
            os.environ.get('APPDATA', os.path.expanduser('~')),
            'PSV Sizing Suite', 'backups'
        )
        os.makedirs(backup_root, exist_ok=True)
        ts = int(time.time())
        backup_dir = os.path.join(backup_root, f'{APP_VERSION}_{ts}')
        try:
            shutil.copytree(exe_dir, backup_dir,
                            ignore=shutil.ignore_patterns('backups', '__pycache__'))
            return backup_dir
        except Exception:
            return None

    def _install_windows_managed(self, setup_path):
        try:
            subprocess.Popen([setup_path, "/S"], shell=True)
            QApplication.quit()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kurulum baslatilamadi: {e}")

    def _install_windows_portable(self, zip_path):
        exe_dir = os.path.dirname(sys.executable)
        batch_path = os.path.join(exe_dir, "update_psv.bat")
        batch_content = f"""@echo off
title PSV Sizing Suite - Guncelleme
echo Guncelleme uygulaniyor, lutfen bekleyin...
timeout /t 3 /nobreak >nul
powershell -Command "Expand-Archive -Path '{zip_path}' -DestinationPath '%~dp0' -Force"
start "" "%~dp0PSV_Sizing_Suite_v2.3.0.exe"
del "%~f0"
"""
        try:
            with open(batch_path, "w") as f:
                f.write(batch_content)
            subprocess.Popen(["cmd", "/c", "start", "", batch_path],
                             shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            QApplication.quit()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Guncelleme baslatilamadi: {e}")

    def _install_macos(self, dmg_path):
        app_name = "PSV_Sizing_Suite_v2.3.0"
        script = f"""#!/bin/bash
sleep 3
hdiutil attach "{dmg_path}" -nobrowse -quiet
cp -R "/Volumes/{app_name}/{app_name}.app" /Applications/ 2>/dev/null
if [ $? -ne 0 ]; then
    osascript -e 'do shell script "cp -R \\"/Volumes/{app_name}/{app_name}.app\\" /Applications/" with administrator privileges'
fi
hdiutil detach "/Volumes/{app_name}" -quiet
open /Applications/{app_name}.app
rm -rf "{dmg_path}" "$(dirname "{dmg_path}")"
"""
        script_path = "/tmp/update_psv.sh"
        try:
            with open(script_path, "w") as f:
                f.write(script)
            os.chmod(script_path, 0o755)
            subprocess.Popen(["bash", script_path],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            QApplication.quit()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Guncelleme baslatilamadi: {e}")

    def _show_rollback_option(self, backup_dir):
        reply = QMessageBox.question(
            self, "Geri Yukleme",
            "Kurulum basarisiz. Eski surume donulsun mu?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes and backup_dir and os.path.exists(backup_dir):
            try:
                exe_dir = os.path.dirname(sys.executable)
                for item in os.listdir(backup_dir):
                    src = os.path.join(backup_dir, item)
                    dst = os.path.join(exe_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                QMessageBox.information(self, "Basarili", "Eski surume geri donuldu.")
            except Exception:
                QMessageBox.warning(self, "Hata", "Geri yukleme basarisiz. Manuel olarak tekrar kurun.")

    def _show_update_error(self, reason):
        QMessageBox.warning(
            self, "Guncelleme Hatasi",
            f"{reason}\n\nLutfen internet baglantinizi kontrol edin veya "
            f"{GITHUB_RELEASES_PAGE} adresini ziyaret edin."
        )

    def show_about(self):
        from PyQt5.QtCore import QSize
        about_text = (
            f"<h2>PSV Sizing Suite {APP_VERSION}</h2>"
            f"<p><b>Advanced Engineering Calculation Platform</b><br>"
            f"Pressure Safety Valve (PSV) sizing based on API 520 Part I and API 521.</p>"
            f"<hr>"
            f"<h3>Standards Compliance — API 2020 Edition</h3>"
            f"<table>"
            f"<tr><td><b>API 520 Part I</b></td><td>10th Ed. (October 2020)</td></tr>"
            f"<tr><td>§5.6</td><td>Gas/Vapor Sizing (C=520, F2=735, Eq.12-16)</td></tr>"
            f"<tr><td>§5.7</td><td>Steam Sizing — Napier (51.5, Kn, Ksh, Tables 12-13)</td></tr>"
            f"<tr><td>§5.8</td><td>Liquid Sizing (38, Re=2800, Eq.32-35)</td></tr>"
            f"<tr><td>§5.8.1.3</td><td>Viscosity Correction Kv = (1+170/Re)^(-0.5), Eq.34</td></tr>"
            f"<tr><td>§5.3</td><td>Backpressure Kb — Fig.31/32/37, Fig.C.3</td></tr>"
            f"<tr><td>§4.2 / §5.2</td><td>Pilot Kd: Gas=0.99, Liquid=0.80, 2-Phase=0.85</td></tr>"
            f"<tr><td>Annex C</td><td>Two-Phase Omega Method (ηc Eq.C.15, G=68.09, A=W/(25·G·Kd))</td></tr>"
            f"<tr><td>Annex C §C.2.3</td><td>Subcooled Flashing Two-Phase</td></tr>"
            f"<tr><td><b>API 520 Part II</b></td><td>7th Ed. (October 2020)</td></tr>"
            f"<tr><td>§4.2.1</td><td>Inlet ΔP ≤ 3% Set (Darcy-Weisbach + Colebrook-White)</td></tr>"
            f"<tr><td>§5.3</td><td>Outlet Built-up BP ≤ 10% Set</td></tr>"
            f"<tr><td><b>API 521</b></td><td>7th Ed. (June 2020)</td></tr>"
            f"<tr><td>§4.4.13 Eq.7-8</td><td>Fire Wetted: Q = 21000·F·A^0.82, W = Q/hfg</td></tr>"
            f"<tr><td>§4.4.13.2.4.3 Eq.10</td><td>Fire Unwetted: F' = 0.1406...(Tw-Tg)^1.25/Tg^0.6506</td></tr>"
            f"<tr><td>§4.4.12 Eq.3</td><td>Thermal Expansion: Q = β·H/(500·G·Cp)</td></tr>"
            f"<tr><td><b>API 526</b></td><td>2023 Ed. — Orifices D(0.110) through T(26.0) sq.in</td></tr>"
            f"</table>"
            f"<hr>"
            f"<p><b>Test Suite:</b> 143 tests passed<br>"
            f"<b>Version:</b> {APP_VERSION}<br>"
            f"<b>GitHub:</b> github.com/SLedgehammer-dev12/PSV_Sizing_Suite</p>"
        )
        msg = QMessageBox(self)
        msg.setWindowTitle("Hakkinda — PSV Sizing Suite")
        msg.setTextFormat(1)  # RichText
        msg.setText(about_text)
        msg.setIcon(QMessageBox.Information)
        msg.setStyleSheet("QLabel{min-width: 600px;}")
        msg.exec_()

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


class DownloadDialog(QDialog):
    def __init__(self, tag, asset, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guncelleme Indiriliyor")
        self.setMinimumWidth(450)
        self.asset = asset
        self.downloaded_path = None
        self.worker = None

        layout = QVBoxLayout(self)

        info = QLabel(f"Yeni surum: {tag}\nDosya: {asset.get('name', '')}\nBoyut: {asset.get('size', 0) // 1048576} MB")
        layout.addWidget(info)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        self.status_label = QLabel("Hazir")
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Iptal")
        self.cancel_btn.clicked.connect(self._cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def start_download(self):
        self.status_label.setText("Indiriliyor...")
        self.cancel_btn.setEnabled(True)
        self.worker = UpdateDownloadWorker(
            self.asset["browser_download_url"],
            self.asset.get("digest")
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, current, total, filename):
        if total > 0:
            pct = int(current * 100 / total)
            self.progress.setValue(pct)
            self.status_label.setText(f"Indiriliyor... {current // 1048576}.{current % 1048576 * 10 // 1048576}/{total // 1048576} MB")
        else:
            self.status_label.setText(f"Indiriliyor... {current // 1024} KB")

    def _on_finished(self, path):
        self.status_label.setText("SHA256 dogrulandi. Kurulum hazir.")
        self.downloaded_path = path
        self.accept()

    def _on_error(self, msg):
        self.status_label.setText(f"Hata: {msg}")
        self.cancel_btn.setText("Kapat")

    def _cancel(self):
        if self.worker:
            self.worker.cancel()
        self.reject()
