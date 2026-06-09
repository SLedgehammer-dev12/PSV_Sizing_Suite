from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QComboBox, QPushButton, QLabel, 
                             QMessageBox, QGroupBox, QProgressBar)
from PyQt5.QtGui import QFont

from core.unit_converter import (barg_to_psia, sqft_to_m2, m2_to_sqft, 
                                 c_to_rankine, kcal_kg_to_btu_lb, kw_to_btu_h, kcal_h_to_btu_h)
from desktop.workers import FireWettedWorker, FireUnwettedWorker, ThermalWorker

class FireWettedTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        input_group = QGroupBox("Inputs (Fire Wetted)")
        form_layout = QFormLayout()

        # Wetted Area
        area_layout = QHBoxLayout()
        self.area_input = QLineEdit("12.836")
        self.area_unit = QComboBox()
        self.area_unit.addItems(["sq.ft", "m2"])
        area_layout.addWidget(self.area_input)
        area_layout.addWidget(self.area_unit)
        form_layout.addRow("Wetted Area:", area_layout)

        # Heat of Vaporization
        hvap_layout = QHBoxLayout()
        self.hvap_input = QLineEdit("50")
        self.hvap_unit = QComboBox()
        self.hvap_unit.addItems(["kcal/kg", "Btu/lb"])
        hvap_layout.addWidget(self.hvap_input)
        hvap_layout.addWidget(self.hvap_unit)
        form_layout.addRow("Latent Heat of Vap.:", hvap_layout)

        # Relieving Pressure
        p1_layout = QHBoxLayout()
        self.p1_input = QLineEdit("16.94")
        self.p1_unit = QComboBox()
        self.p1_unit.addItems(["barg", "psia"])
        p1_layout.addWidget(self.p1_input)
        p1_layout.addWidget(self.p1_unit)
        form_layout.addRow("Relieving Pressure (P1):", p1_layout)

        # Back Pressure
        p2_layout = QHBoxLayout()
        self.p2_input = QLineEdit("14.7")
        self.p2_unit = QComboBox()
        self.p2_unit.addItems(["barg", "psia"])
        p2_layout.addWidget(self.p2_input)
        p2_layout.addWidget(self.p2_unit)
        form_layout.addRow("Back Pressure (P2):", p2_layout)

        self.t_input = QLineEdit("564.67")
        form_layout.addRow("Gas Temp (°R):", self.t_input)

        self.z_input = QLineEdit("0.92")
        form_layout.addRow("Compressibility (Z):", self.z_input)

        self.mw_input = QLineEdit("21")
        form_layout.addRow("Molecular Weight (MW):", self.mw_input)

        self.k_input = QLineEdit("1.3")
        form_layout.addRow("Spec. Heat Ratio (k):", self.k_input)

        self.f_input = QLineEdit("1.0")
        form_layout.addRow("Environment Factor (F):", self.f_input)

        input_group.setLayout(form_layout)
        main_layout.addWidget(input_group)

        self.calc_btn = QPushButton("HESAPLA (CALCULATE)")
        self.calc_btn.setMinimumHeight(40)
        self.calc_btn.setStyleSheet("font-weight: bold; background-color: #e74c3c; color: white;")
        self.calc_btn.clicked.connect(self.run_calculation)
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)

        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.calc_btn)

        result_group = QGroupBox("Results")
        res_layout = QFormLayout()
        
        self.res_q = QLabel("-")
        self.res_w = QLabel("-")
        self.res_area = QLabel("-")
        self.res_orifice = QLabel("-")
        
        res_font = QFont("Arial", 11, QFont.Bold)
        self.res_area.setFont(res_font)
        self.res_orifice.setFont(res_font)

        res_layout.addRow("Heat Absorption (Btu/h):", self.res_q)
        res_layout.addRow("Relief Load (lb/h):", self.res_w)
        res_layout.addRow("Required Area:", self.res_area)
        res_layout.addRow("Selected API Orifice:", self.res_orifice)

        result_group.setLayout(res_layout)
        main_layout.addWidget(result_group)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def run_calculation(self):
        try:
            area = float(self.area_input.text())
            hvap = float(self.hvap_input.text())
            p1 = float(self.p1_input.text())
            p2 = float(self.p2_input.text())
            t = float(self.t_input.text())
            z = float(self.z_input.text())
            mw = float(self.mw_input.text())
            k = float(self.k_input.text())
            f = float(self.f_input.text())

            if self.area_unit.currentText() == "m2":
                area = m2_to_sqft(area)
            if self.hvap_unit.currentText() == "kcal/kg":
                hvap = kcal_kg_to_btu_lb(hvap)
            if self.p1_unit.currentText() == "barg":
                p1 = barg_to_psia(p1)
            if self.p2_unit.currentText() == "barg":
                p2 = barg_to_psia(p2)

            inputs = {
                'a_wetted': area, 'h_vap': hvap, 'p1_psia': p1, 'p2_psia': p2,
                't_rankine': t, 'z': z, 'mw': mw, 'k': k, 'f_factor': f
            }

            self.calc_btn.setEnabled(False)
            self.progress.setVisible(True)
            self.res_area.setText("Calculating...")
            
            self.worker = FireWettedWorker(inputs)
            self.worker.finished.connect(self.on_calc_success)
            self.worker.error.connect(self.on_calc_error)
            self.worker.start()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid numbers.")

    def on_calc_success(self, res):
        self.calc_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.res_q.setText(f"{res['Heat_Absorption_Btu_h']:.2f}")
        self.res_w.setText(f"{res['Relief_Load_lb_h']:.2f}")
        self.res_area.setText(f"{res['Required_Area_sqin']:.4f} sq.inch")
        self.res_orifice.setText(f"{res['Selected_Orifice_Letter']} ({res['Selected_Orifice_Area_sqin']} sq.inch)")

    def on_calc_error(self, err_msg):
        self.calc_btn.setEnabled(True)
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Error", err_msg)


class FireUnwettedTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        input_group = QGroupBox("Inputs (Fire Unwetted)")
        form_layout = QFormLayout()

        # Exposed Area
        area_layout = QHBoxLayout()
        self.area_input = QLineEdit("44.177")
        self.area_unit = QComboBox()
        self.area_unit.addItems(["sq.ft", "m2"])
        area_layout.addWidget(self.area_input)
        area_layout.addWidget(self.area_unit)
        form_layout.addRow("Exposed Area:", area_layout)

        # Relieving Pressure
        p1_layout = QHBoxLayout()
        self.p1_input = QLineEdit("16.94")
        self.p1_unit = QComboBox()
        self.p1_unit.addItems(["barg", "psia"])
        p1_layout.addWidget(self.p1_input)
        p1_layout.addWidget(self.p1_unit)
        form_layout.addRow("Relieving Pressure (P1):", p1_layout)

        self.tgas_input = QLineEdit("564.67")
        form_layout.addRow("Gas Temp (°R):", self.tgas_input)

        self.twall_input = QLineEdit("1560")
        form_layout.addRow("Wall Temp (°R):", self.twall_input)

        self.k_input = QLineEdit("1.2")
        form_layout.addRow("Spec. Heat Ratio (k):", self.k_input)

        input_group.setLayout(form_layout)
        main_layout.addWidget(input_group)

        self.calc_btn = QPushButton("HESAPLA (CALCULATE)")
        self.calc_btn.setMinimumHeight(40)
        self.calc_btn.setStyleSheet("font-weight: bold; background-color: #d35400; color: white;")
        self.calc_btn.clicked.connect(self.run_calculation)
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)

        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.calc_btn)

        result_group = QGroupBox("Results")
        res_layout = QFormLayout()
        
        self.res_fprime = QLabel("-")
        self.res_area = QLabel("-")
        self.res_orifice = QLabel("-")
        
        res_font = QFont("Arial", 11, QFont.Bold)
        self.res_area.setFont(res_font)
        self.res_orifice.setFont(res_font)

        res_layout.addRow("F' Factor:", self.res_fprime)
        res_layout.addRow("Required Area:", self.res_area)
        res_layout.addRow("Selected API Orifice:", self.res_orifice)

        result_group.setLayout(res_layout)
        main_layout.addWidget(result_group)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def run_calculation(self):
        try:
            area = float(self.area_input.text())
            p1 = float(self.p1_input.text())
            tgas = float(self.tgas_input.text())
            twall = float(self.twall_input.text())
            k = float(self.k_input.text())

            if self.area_unit.currentText() == "m2":
                area = m2_to_sqft(area)
            if self.p1_unit.currentText() == "barg":
                p1 = barg_to_psia(p1)

            inputs = {
                'a_exposed': area, 'p1_psia': p1, 
                't_gas': tgas, 't_wall': twall, 'k': k
            }

            self.calc_btn.setEnabled(False)
            self.progress.setVisible(True)
            self.res_area.setText("Calculating...")
            
            self.worker = FireUnwettedWorker(inputs)
            self.worker.finished.connect(self.on_calc_success)
            self.worker.error.connect(self.on_calc_error)
            self.worker.start()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid numbers.")

    def on_calc_success(self, res):
        self.calc_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.res_fprime.setText(f"{res['F_Prime']:.5f}")
        self.res_area.setText(f"{res['Required_Area_sqin']:.4f} sq.inch")
        self.res_orifice.setText(f"{res['Selected_Orifice_Letter']} ({res['Selected_Orifice_Area_sqin']} sq.inch)")

    def on_calc_error(self, err_msg):
        self.calc_btn.setEnabled(True)
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Error", err_msg)


class ThermalExpansionTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        input_group = QGroupBox("Inputs (Hydraulic Expansion)")
        form_layout = QFormLayout()

        # Heat Transfer
        h_layout = QHBoxLayout()
        self.h_input = QLineEdit("2100")
        self.h_unit = QComboBox()
        self.h_unit.addItems(["kW", "BTU/h", "kcal/h"])
        h_layout.addWidget(self.h_input)
        h_layout.addWidget(self.h_unit)
        form_layout.addRow("Total Heat Transfer (H):", h_layout)

        self.b_input = QLineEdit("0.0005")
        form_layout.addRow("Expansion Coeff (B) [1/°F]:", self.b_input)

        self.g_input = QLineEdit("0.85")
        form_layout.addRow("Specific Gravity (G):", self.g_input)

        self.c_input = QLineEdit("0.599")
        form_layout.addRow("Specific Heat (C) [Btu/lb°F]:", self.c_input)

        self.mu_input = QLineEdit("51.0")
        form_layout.addRow("Viscosity (cP):", self.mu_input)

        # Relieving Pressure
        p1_layout = QHBoxLayout()
        self.p1_input = QLineEdit("16.94")
        self.p1_unit = QComboBox()
        self.p1_unit.addItems(["barg", "psia"])
        p1_layout.addWidget(self.p1_input)
        p1_layout.addWidget(self.p1_unit)
        form_layout.addRow("Relieving Pressure (P1):", p1_layout)

        p2_layout = QHBoxLayout()
        self.p2_input = QLineEdit("0.5")
        self.p2_unit = QComboBox()
        self.p2_unit.addItems(["barg", "psia"])
        p2_layout.addWidget(self.p2_input)
        p2_layout.addWidget(self.p2_unit)
        form_layout.addRow("Back Pressure (P2):", p2_layout)

        input_group.setLayout(form_layout)
        main_layout.addWidget(input_group)

        self.calc_btn = QPushButton("HESAPLA (CALCULATE)")
        self.calc_btn.setMinimumHeight(40)
        self.calc_btn.setStyleSheet("font-weight: bold; background-color: #2980b9; color: white;")
        self.calc_btn.clicked.connect(self.run_calculation)
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)

        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.calc_btn)

        result_group = QGroupBox("Results")
        res_layout = QFormLayout()
        
        self.res_q = QLabel("-")
        self.res_area = QLabel("-")
        self.res_orifice = QLabel("-")
        
        res_font = QFont("Arial", 11, QFont.Bold)
        self.res_area.setFont(res_font)
        self.res_orifice.setFont(res_font)

        res_layout.addRow("Relief Load (US GPM):", self.res_q)
        res_layout.addRow("Required Area:", self.res_area)
        res_layout.addRow("Selected API Orifice:", self.res_orifice)

        result_group.setLayout(res_layout)
        main_layout.addWidget(result_group)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def run_calculation(self):
        try:
            h = float(self.h_input.text())
            b = float(self.b_input.text())
            g = float(self.g_input.text())
            c = float(self.c_input.text())
            mu = float(self.mu_input.text())
            p1 = float(self.p1_input.text())
            p2 = float(self.p2_input.text())

            if self.h_unit.currentText() == "kW":
                h = kw_to_btu_h(h)
            elif self.h_unit.currentText() == "kcal/h":
                h = kcal_h_to_btu_h(h)

            if self.p1_unit.currentText() == "barg":
                p1 = barg_to_psia(p1)
            if self.p2_unit.currentText() == "barg":
                p2 = barg_to_psia(p2)

            inputs = {
                'h_btu': h, 'b': b, 'g': g, 'c': c, 'mu_cp': mu,
                'p1_psia': p1, 'p2_psia': p2
            }

            self.calc_btn.setEnabled(False)
            self.progress.setVisible(True)
            self.res_area.setText("Calculating...")
            
            self.worker = ThermalWorker(inputs)
            self.worker.finished.connect(self.on_calc_success)
            self.worker.error.connect(self.on_calc_error)
            self.worker.start()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Invalid numbers.")

    def on_calc_success(self, res):
        self.calc_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.res_q.setText(f"{res['Relief_Load_gpm']:.3f} gpm")
        self.res_area.setText(f"{res['Required_Area_Final_sqin']:.4f} sq.inch")
        self.res_orifice.setText(f"{res['Selected_Orifice_Letter']} ({res['Selected_Orifice_Area_sqin']} sq.inch)")

    def on_calc_error(self, err_msg):
        self.calc_btn.setEnabled(True)
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Error", err_msg)
