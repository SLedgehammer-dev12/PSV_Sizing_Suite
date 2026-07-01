from PyQt5.QtWidgets import (QHBoxLayout, QFormLayout,
                              QLineEdit, QComboBox, QPushButton, QLabel,
                              QMessageBox, QGroupBox, QGridLayout)

from core.unit_converter import (barg_to_psia, m2_to_sqft,
                                 c_to_rankine, kcal_kg_to_btu_lb, kw_to_btu_h, kcal_h_to_btu_h)
from desktop.workers import FireWettedWorker, FireUnwettedWorker, ThermalWorker
from desktop.base_tab import BaseCalcTab

class FireWettedTab(BaseCalcTab):
    def __init__(self):
        super().__init__("Fire (Wetted)", calc_button_color="#e74c3c")

    def init_inputs(self):
        input_group = QGroupBox("Inputs (Fire Wetted)")
        form_layout = QFormLayout()

        area_layout = QHBoxLayout()
        self.area_input = QLineEdit("12.836")
        self.area_unit = QComboBox()
        self.area_unit.addItems(["sq.ft", "m2"])
        area_layout.addWidget(self.area_input)
        area_layout.addWidget(self.area_unit)
        form_layout.addRow("Wetted Area:", area_layout)

        hvap_layout = QHBoxLayout()
        self.hvap_input = QLineEdit("50")
        self.hvap_unit = QComboBox()
        self.hvap_unit.addItems(["kcal/kg", "Btu/lb"])
        hvap_layout.addWidget(self.hvap_input)
        hvap_layout.addWidget(self.hvap_unit)
        form_layout.addRow("Latent Heat of Vap.:", hvap_layout)

        p1_layout = QHBoxLayout()
        self.p1_input = QLineEdit("16.94")
        self.p1_unit = QComboBox()
        self.p1_unit.addItems(["barg", "psia"])
        p1_layout.addWidget(self.p1_input)
        p1_layout.addWidget(self.p1_unit)
        form_layout.addRow("Relieving Pressure (P1):", p1_layout)

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

        p2_layout = QHBoxLayout()
        self.p2_input = QLineEdit("14.7")
        self.p2_unit = QComboBox()
        self.p2_unit.addItems(["barg", "psia"])
        p2_layout.addWidget(self.p2_input)
        p2_layout.addWidget(self.p2_unit)
        form_layout.addRow("Back Pressure (P2):", p2_layout)

        self.valve_type_combo = QComboBox()
        self.valve_type_combo.addItems(["conventional", "balanced_bellows", "pilot"])
        form_layout.addRow("Valve Type:", self.valve_type_combo)

        input_group.setLayout(form_layout)
        self.main_layout.insertWidget(0, input_group)

    def _area_row(self):
        return 1

    def _add_result_widgets(self, layout):
        self.res_q = QLabel("-")
        self.res_w = QLabel("-")
        layout.addWidget(QLabel("Heat Absorption (Btu/h):"), 0, 0)
        layout.addWidget(self.res_q, 0, 1)
        layout.addWidget(QLabel("Relief Load (lb/h):"), 0, 2)
        layout.addWidget(self.res_w, 0, 3)

    def _update_extra_results(self, res):
        self.res_q.setText(f"{res['Heat_Absorption_Btu_h']:.2f}")
        self.res_w.setText(f"{res['Relief_Load_lb_h']:.2f}")

    def _get_export_results(self):
        base = super()._get_export_results()
        base.update({"Heat Absorption (Btu/h)": self.res_q.text(), "Relief Load (lb/h)": self.res_w.text()})
        return base

    def _get_graph_results(self):
        return {"res_area": self.res_area.text(), "res_orifice": self.res_orifice.text(), "req_area_sqin": self.last_res.get('Required_Area_sqin', 0), "sel_area_sqin": self.last_res.get('Selected_Orifice_Area_sqin', 0)}

    def run_calculation(self):
        try:
            area = float(self.area_input.text())
            hvap = float(self.hvap_input.text())
            p1 = float(self.p1_input.text())
            t = float(self.t_input.text())
            z = float(self.z_input.text())
            mw = float(self.mw_input.text())
            k = float(self.k_input.text())
            f = float(self.f_input.text())
            p2 = float(self.p2_input.text())

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
                't_rankine': t, 'z': z, 'mw': mw, 'k': k, 'f_factor': f,
                'valve_type': self.valve_type_combo.currentText()
            }
            self.last_inputs = inputs

            self.calc_btn.setEnabled(False)
            self.progress.setVisible(True)
            self.res_area.setText("Calculating...")

            self.worker = FireWettedWorker(inputs)
            self.worker.finished.connect(self.on_calc_success)
            self.worker.error.connect(self.on_calc_error)
            self.worker.start()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numerical values.")
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Unexpected error: {str(e)}")



class FireUnwettedTab(BaseCalcTab):
    def __init__(self):
        super().__init__("Fire (Unwetted)", calc_button_color="#d35400")

    def init_inputs(self):
        input_group = QGroupBox("Inputs (Fire Unwetted)")
        form_layout = QFormLayout()

        area_layout = QHBoxLayout()
        self.area_input = QLineEdit("44.177")
        self.area_unit = QComboBox()
        self.area_unit.addItems(["sq.ft", "m2"])
        area_layout.addWidget(self.area_input)
        area_layout.addWidget(self.area_unit)
        form_layout.addRow("Exposed Area:", area_layout)

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
        self.main_layout.insertWidget(0, input_group)

    def _add_result_widgets(self, layout):
        self.res_fprime = QLabel("-")
        layout.addWidget(QLabel("F' Factor:"), 0, 0)
        layout.addWidget(self.res_fprime, 0, 1)

    def _update_extra_results(self, res):
        self.res_fprime.setText(f"{res['F_Prime']:.5f}")

    def _get_export_results(self):
        base = super()._get_export_results()
        base["F' Factor"] = self.res_fprime.text()
        return base

    def _get_graph_results(self):
        return {"res_area": self.res_area.text(), "res_orifice": self.res_orifice.text(), "req_area_sqin": self.last_res.get('Required_Area_sqin', 0), "sel_area_sqin": self.last_res.get('Selected_Orifice_Area_sqin', 0)}

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
            self.last_inputs = inputs

            self.calc_btn.setEnabled(False)
            self.progress.setVisible(True)
            self.res_area.setText("Calculating...")

            self.worker = FireUnwettedWorker(inputs)
            self.worker.finished.connect(self.on_calc_success)
            self.worker.error.connect(self.on_calc_error)
            self.worker.start()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numerical values.")
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Unexpected error: {str(e)}")



class ThermalExpansionTab(BaseCalcTab):
    def __init__(self):
        super().__init__("Thermal Expansion")

    def init_inputs(self):
        input_group = QGroupBox("Inputs (Hydraulic Expansion)")
        form_layout = QFormLayout()

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

        self.valve_type_combo = QComboBox()
        self.valve_type_combo.addItems(["conventional", "balanced_bellows", "pilot"])
        form_layout.addRow("Valve Type:", self.valve_type_combo)

        input_group.setLayout(form_layout)
        self.main_layout.insertWidget(0, input_group)

    def _area_row(self):
        return 1

    def _add_result_widgets(self, layout):
        self.res_q = QLabel("-")
        layout.addWidget(QLabel("Relief Load (US GPM):"), 0, 0)
        layout.addWidget(self.res_q, 0, 1)

    def _update_extra_results(self, res):
        self.res_q.setText(f"{res['Relief_Load_gpm']:.3f}")

    def _get_export_results(self):
        base = super()._get_export_results()
        base["Relief Load (US GPM)"] = self.res_q.text()
        return base

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
                'p1_psia': p1, 'p2_psia': p2,
                'valve_type': self.valve_type_combo.currentText()
            }
            self.last_inputs = inputs

            self.calc_btn.setEnabled(False)
            self.progress.setVisible(True)
            self.res_area.setText("Calculating...")

            self.worker = ThermalWorker(inputs)
            self.worker.finished.connect(self.on_calc_success)
            self.worker.error.connect(self.on_calc_error)
            self.worker.start()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numerical values.")
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Unexpected error: {str(e)}")

