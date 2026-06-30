from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout, 
                             QLineEdit, QComboBox, QPushButton, QLabel, 
                             QMessageBox, QGroupBox, QProgressBar, QScrollArea,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.unit_converter import (barg_to_psia, bara_to_psia, m3_h_to_gpm, kg_h_to_lb_h, c_to_rankine, m3_kg_to_ft3_lb,
                                 kg_s_to_lb_h, actual_m3_h_to_lb_h, sm3_h_to_lb_h, nm3_h_to_lb_h)
from desktop.workers import LiquidCalcWorker, GasCalcWorker, TwoPhaseCalcWorker
from core.thermo_props import calculate_mixture_properties, get_coolprop_fluids
from desktop.vendor_window import VendorTableWidget
from desktop.report_generator import generate_and_open_report
from desktop.graph_window import PlotWindow
from desktop.base_tab import BaseCalcTab

class LiquidReliefTab(BaseCalcTab):
    def __init__(self):
        super().__init__("Liquid Relief")

    def init_inputs(self):
        input_group = QGroupBox("Operating Conditions & Properties")
        grid = QGridLayout()

        flow_layout = QHBoxLayout()
        self.flow_input = QLineEdit("60")
        self.flow_unit = QComboBox()
        self.flow_unit.addItems(["m3/h", "US gpm"])
        flow_layout.addWidget(self.flow_input)
        flow_layout.addWidget(self.flow_unit)

        p1_layout = QHBoxLayout()
        self.p1_input = QLineEdit("52.8")
        self.p1_unit = QComboBox()
        self.p1_unit.addItems(["barg", "psia"])
        p1_layout.addWidget(self.p1_input)
        p1_layout.addWidget(self.p1_unit)

        p2_layout = QHBoxLayout()
        self.p2_input = QLineEdit("1.0")
        self.p2_unit = QComboBox()
        self.p2_unit.addItems(["barg", "psia"])
        p2_layout.addWidget(self.p2_input)
        p2_layout.addWidget(self.p2_unit)

        self.g_input = QLineEdit("1.1")
        self.mu_input = QLineEdit("1.0")
        self.num_valves_input = QLineEdit("1")

        grid.addWidget(QLabel("Flow Rate:"), 0, 0)
        grid.addLayout(flow_layout, 0, 1)
        grid.addWidget(QLabel("Relieving Pressure (P1):"), 0, 2)
        grid.addLayout(p1_layout, 0, 3)
        grid.addWidget(QLabel("Total Back Pressure (P2):"), 1, 0)
        grid.addLayout(p2_layout, 1, 1)
        grid.addWidget(QLabel("Specific Gravity (G):"), 1, 2)
        grid.addWidget(self.g_input, 1, 3)
        grid.addWidget(QLabel("Viscosity (cP):"), 2, 0)
        grid.addWidget(self.mu_input, 2, 1)
        grid.addWidget(QLabel("Number of Parallel Valves:"), 2, 2)
        grid.addWidget(self.num_valves_input, 2, 3)

        self.valve_type_combo = QComboBox()
        self.valve_type_combo.addItems(["conventional", "balanced_bellows", "pilot"])
        grid.addWidget(QLabel("Valve Type:"), 3, 0)
        grid.addWidget(self.valve_type_combo, 3, 1)

        input_group.setLayout(grid)
        self.main_layout.insertWidget(0, input_group)

    def _area_row(self):
        return 2

    def _add_result_widgets(self, layout):
        self.res_re = QLabel("-")
        self.res_kv = QLabel("-")
        layout.addWidget(QLabel("Reynolds Number (Re):"), 2, 0)
        layout.addWidget(self.res_re, 2, 1)
        layout.addWidget(QLabel("Viscosity Corr. (Kv):"), 2, 2)
        layout.addWidget(self.res_kv, 2, 3)

    def _update_extra_results(self, res):
        self.res_re.setText(f"{res['Reynolds_Number']:.2f}")
        self.res_kv.setText(f"{res['Kv']:.4f}")

    def _get_export_results(self):
        base = super()._get_export_results()
        base.update({
            "Reynolds Number (Re)": self.res_re.text(),
            "Viscosity Corr. (Kv)": self.res_kv.text()
        })
        return base

    def run_calculation(self):
        try:
            flow = float(self.flow_input.text())
            p1 = float(self.p1_input.text())
            p2 = float(self.p2_input.text())
            g = float(self.g_input.text())
            mu = float(self.mu_input.text())

            if self.flow_unit.currentText() == "m3/h":
                flow = m3_h_to_gpm(flow)
            if self.p1_unit.currentText() == "barg":
                p1 = barg_to_psia(p1)
            if self.p2_unit.currentText() == "barg":
                p2 = barg_to_psia(p2)

            num_valves = int(self.num_valves_input.text())
            if num_valves < 1:
                num_valves = 1

            inputs = {'q_gpm': flow, 'p1_psia': p1, 'p2_psia': p2, 'g': g, 'mu_cp': mu, 'num_valves': num_valves, 'valve_type': self.valve_type_combo.currentText(), 'overpressure_pct': 10.0}
            self.last_inputs = inputs

            self.calc_btn.setEnabled(False)
            self.progress.setVisible(True)
            self.res_area.setText("Calculating...")

            self.worker = LiquidCalcWorker(inputs)
            self.worker.finished.connect(self.on_calc_success)
            self.worker.error.connect(self.on_calc_error)
            self.worker.start()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numerical values.")
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Unexpected error: {str(e)}")


class GasReliefTab(BaseCalcTab):
    def __init__(self):
        self.coolprop_fluids = get_coolprop_fluids()
        super().__init__("Gas/Vapor Relief")

    def init_inputs(self):
        comp_group = QGroupBox("Fluid Composition (CoolProp Auto-Calculation)")
        comp_layout = QVBoxLayout()
        
        frac_type_layout = QHBoxLayout()
        frac_type_layout.addWidget(QLabel("Fraction Type:"))
        self.frac_type_combo = QComboBox()
        self.frac_type_combo.addItems(["Mole %", "Mass %"])
        frac_type_layout.addWidget(self.frac_type_combo)
        frac_type_layout.addStretch()
        comp_layout.addLayout(frac_type_layout)

        self.comp_table = QTableWidget(0, 2)
        self.comp_table.setHorizontalHeaderLabels(["Fluid", "Fraction (%)"])
        self.comp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        
        btn_layout = QHBoxLayout()
        self.btn_add_fluid = QPushButton("+ Add Fluid")
        self.btn_add_fluid.clicked.connect(self.add_fluid_row)
        self.btn_remove_fluid = QPushButton("- Remove Selected")
        self.btn_remove_fluid.clicked.connect(self.remove_fluid_row)
        btn_layout.addWidget(self.btn_add_fluid)
        btn_layout.addWidget(self.btn_remove_fluid)
        
        comp_layout.addWidget(self.comp_table)
        comp_layout.addLayout(btn_layout)
        comp_group.setLayout(comp_layout)
        self.main_layout.insertWidget(0, comp_group)

        input_group = QGroupBox("Operating Conditions & Properties")
        grid = QGridLayout()

        flow_layout = QHBoxLayout()
        self.flow_input = QLineEdit("9633")
        self.flow_unit = QComboBox()
        self.flow_unit.addItems(["kg/h", "lb/h", "kg/s", "m3/h", "sm3/h", "Nm3/h"])
        flow_layout.addWidget(self.flow_input)
        flow_layout.addWidget(self.flow_unit)

        p1_layout = QHBoxLayout()
        self.p1_input = QLineEdit("15.4")
        self.p1_unit = QComboBox()
        self.p1_unit.addItems(["barg", "psia"])
        p1_layout.addWidget(self.p1_input)
        p1_layout.addWidget(self.p1_unit)

        p2_layout = QHBoxLayout()
        self.p2_input = QLineEdit("1.2")
        self.p2_unit = QComboBox()
        self.p2_unit.addItems(["barg", "psia"])
        p2_layout.addWidget(self.p2_input)
        p2_layout.addWidget(self.p2_unit)

        t_layout = QHBoxLayout()
        self.t_input = QLineEdit("35")
        self.t_unit = QComboBox()
        self.t_unit.addItems(["°C", "°R"])
        t_layout.addWidget(self.t_input)
        t_layout.addWidget(self.t_unit)

        self.z_input = QLineEdit("0.85")
        self.z_input.setPlaceholderText("Auto or manual")
        self.mw_input = QLineEdit("21")
        
        k_layout = QHBoxLayout()
        self.k_input = QLineEdit("1.3")
        k_layout.addWidget(self.k_input)

        self.num_valves_input = QLineEdit("1")

        grid.addWidget(QLabel("Flow Rate:"), 0, 0)
        grid.addLayout(flow_layout, 0, 1)
        grid.addWidget(QLabel("Relieving Pressure (P1):"), 0, 2)
        grid.addLayout(p1_layout, 0, 3)
        grid.addWidget(QLabel("Total Back Pressure (P2):"), 1, 0)
        grid.addLayout(p2_layout, 1, 1)
        grid.addWidget(QLabel("Relieving Temp (T):"), 1, 2)
        grid.addLayout(t_layout, 1, 3)
        grid.addWidget(QLabel("Compressibility (Z):"), 2, 0)
        grid.addWidget(self.z_input, 2, 1)
        grid.addWidget(QLabel("Molecular Weight (MW):"), 2, 2)
        grid.addWidget(self.mw_input, 2, 3)
        grid.addWidget(QLabel("Specific Heat Ratio (k):"), 3, 0)
        grid.addLayout(k_layout, 3, 1)

        self.valve_type_combo = QComboBox()
        self.valve_type_combo.addItems(["conventional", "balanced_bellows", "pilot"])
        grid.addWidget(QLabel("Valve Type:"), 4, 0)
        grid.addWidget(self.valve_type_combo, 4, 1)
        grid.addWidget(QLabel("Number of Parallel Valves:"), 4, 2)
        grid.addWidget(self.num_valves_input, 4, 3)

        input_group.setLayout(grid)
        self.main_layout.insertWidget(1, input_group)

    def _area_row(self):
        return 2

    def _add_result_widgets(self, layout):
        self.res_flow_type = QLabel("-")
        self.res_flow_type.setStyleSheet("color: #8e44ad; font-weight: bold;")
        layout.addWidget(QLabel("Flow Regime:"), 2, 0)
        layout.addWidget(self.res_flow_type, 2, 1, 1, 3)

    def _update_extra_results(self, res):
        self.res_flow_type.setText(res['Flow_Type'])

    def _get_export_results(self):
        base = super()._get_export_results()
        base["Flow Regime"] = self.res_flow_type.text()
        return base

    def add_fluid_row(self):
        row = self.comp_table.rowCount()
        self.comp_table.insertRow(row)
        
        combo = QComboBox()
        combo.addItems(self.coolprop_fluids)
        if "Methane" in self.coolprop_fluids:
            combo.setCurrentText("Methane")
            
        self.comp_table.setCellWidget(row, 0, combo)
        
        frac_input = QLineEdit("100" if row == 0 else "0")
        self.comp_table.setCellWidget(row, 1, frac_input)
        self.update_property_inputs_state()

    def remove_fluid_row(self):
        current_row = self.comp_table.currentRow()
        if current_row >= 0:
            self.comp_table.removeRow(current_row)
        self.update_property_inputs_state()

    def update_property_inputs_state(self):
        has_fluids = self.comp_table.rowCount() > 0
        self.z_input.setReadOnly(has_fluids)
        self.mw_input.setReadOnly(has_fluids)
        self.k_input.setReadOnly(has_fluids)
        
        style = "background-color: #f0f0f0; color: #7f8c8d;" if has_fluids else ""
        self.z_input.setStyleSheet(style)
        self.mw_input.setStyleSheet(style)
        self.k_input.setStyleSheet(style)

    def get_composition(self):
        comp = {}
        for row in range(self.comp_table.rowCount()):
            fluid_combo = self.comp_table.cellWidget(row, 0)
            frac_input = self.comp_table.cellWidget(row, 1)
            if fluid_combo and frac_input:
                fluid = fluid_combo.currentText()
                if fluid == "Water (Steam)":
                    fluid = "Water"
                try:
                    frac_percent = float(frac_input.text())
                    if frac_percent > 0:
                        comp[fluid] = comp.get(fluid, 0.0) + (frac_percent / 100.0)
                except ValueError:
                    pass
        return comp

    def run_calculation(self):
        try:
            comp = self.get_composition()

            flow = float(self.flow_input.text())
            p1_raw = float(self.p1_input.text())
            p2_raw = float(self.p2_input.text())
            t_raw = float(self.t_input.text())
            
            p1 = barg_to_psia(p1_raw) if self.p1_unit.currentText() == "barg" else p1_raw
            p2 = barg_to_psia(p2_raw) if self.p2_unit.currentText() == "barg" else p2_raw
            t = c_to_rankine(t_raw) if self.t_unit.currentText() == "°C" else t_raw

            if comp:
                fraction_type = "mass" if "Mass" in self.frac_type_combo.currentText() else "mole"
                z, mw, k = calculate_mixture_properties(comp, t, p1, fraction_type=fraction_type)
                self.z_input.setText(f"{z:.4f}")
                self.mw_input.setText(f"{mw:.2f}")
                self.k_input.setText(f"{k:.4f}")
            else:
                try:
                    z = float(self.z_input.text())
                    mw = float(self.mw_input.text())
                    k = float(self.k_input.text())
                except ValueError:
                    QMessageBox.warning(self, "Input Error",
                        "Gaz kompozisyonu boş olduğundan manuel Z, MW ve k değerleri gereklidir.")
                    return

            if self.flow_unit.currentText() == "kg/h":
                flow_lb_h = kg_h_to_lb_h(flow)
            elif self.flow_unit.currentText() == "kg/s":
                flow_lb_h = kg_s_to_lb_h(flow)
            elif self.flow_unit.currentText() == "m3/h":
                flow_lb_h = actual_m3_h_to_lb_h(flow, p1, t, mw, z)
            elif self.flow_unit.currentText() == "sm3/h":
                flow_lb_h = sm3_h_to_lb_h(flow, mw)
            elif self.flow_unit.currentText() == "Nm3/h":
                flow_lb_h = nm3_h_to_lb_h(flow, mw)
            else:
                flow_lb_h = flow

            num_valves = int(self.num_valves_input.text())
            if num_valves < 1:
                num_valves = 1

            sp_psig = (p1 - 14.6959) / (1.0 + 10.0 / 100.0)
            inputs = {
                'w_lb_h': flow_lb_h, 'p1_psia': p1, 'p2_psia': p2,
                't_rankine': t, 'z': z, 'mw': mw, 'k': k,
                'num_valves': num_valves,
                'valve_type': self.valve_type_combo.currentText(),
                'set_pressure_psig': sp_psig,
            }
            self.last_inputs = inputs

            self.calc_btn.setEnabled(False)
            self.progress.setVisible(True)
            self.res_area.setText("Calculating...")
            
            self.worker = GasCalcWorker(inputs)
            self.worker.finished.connect(self.on_calc_success)
            self.worker.error.connect(self.on_calc_error)
            self.worker.start()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numerical values.")
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Unexpected error: {str(e)}")


class TwoPhaseReliefTab(BaseCalcTab):
    def __init__(self):
        super().__init__("Two-Phase Relief")

    def init_inputs(self):
        input_group = QGroupBox("Inputs (Two-Phase Flashing)")
        grid = QGridLayout()

        flow_layout = QHBoxLayout()
        self.flow_input = QLineEdit("466259.5")
        self.flow_unit = QComboBox()
        self.flow_unit.addItems(["kg/h", "lb/h"])
        flow_layout.addWidget(self.flow_input)
        flow_layout.addWidget(self.flow_unit)

        p0_layout = QHBoxLayout()
        self.p0_input = QLineEdit("136.14")
        self.p0_unit = QComboBox()
        self.p0_unit.addItems(["bara", "psia"])
        p0_layout.addWidget(self.p0_input)
        p0_layout.addWidget(self.p0_unit)

        pback_layout = QHBoxLayout()
        self.pback_input = QLineEdit("14.0")
        self.pback_unit = QComboBox()
        self.pback_unit.addItems(["barg", "psia"])
        pback_layout.addWidget(self.pback_input)
        pback_layout.addWidget(self.pback_unit)

        v0_layout = QHBoxLayout()
        self.v0_input = QLineEdit("0.00841175")
        self.v0_unit = QComboBox()
        self.v0_unit.addItems(["m3/kg", "ft3/lb"])
        v0_layout.addWidget(self.v0_input)
        v0_layout.addWidget(self.v0_unit)

        v9_layout = QHBoxLayout()
        self.v9_input = QLineEdit("0.0090111")
        self.v9_unit = QComboBox()
        self.v9_unit.addItems(["m3/kg", "ft3/lb"])
        v9_layout.addWidget(self.v9_input)
        v9_layout.addWidget(self.v9_unit)

        self.kd_input = QLineEdit("0.85")
        self.num_valves_input = QLineEdit("1")

        grid.addWidget(QLabel("Mass Flow Rate (W):"), 0, 0)
        grid.addLayout(flow_layout, 0, 1)
        grid.addWidget(QLabel("Relieving Pressure (P0):"), 0, 2)
        grid.addLayout(p0_layout, 0, 3)
        grid.addWidget(QLabel("Back Pressure:"), 1, 0)
        grid.addLayout(pback_layout, 1, 1)
        grid.addWidget(QLabel("Specific Volume at Inlet (v0):"), 1, 2)
        grid.addLayout(v0_layout, 1, 3)
        grid.addWidget(QLabel("Specific Vol at 90% P0 (v9):"), 2, 0)
        grid.addLayout(v9_layout, 2, 1)
        grid.addWidget(QLabel("Discharge Coeff. (Kd):"), 2, 2)
        grid.addWidget(self.kd_input, 2, 3)
        grid.addWidget(QLabel("Number of Parallel Valves:"), 3, 0)
        grid.addWidget(self.num_valves_input, 3, 1)

        input_group.setLayout(grid)
        self.main_layout.insertWidget(0, input_group)

    def _add_result_widgets(self, layout):
        self.res_omega = QLabel("-")
        self.res_hc = QLabel("-")
        self.res_g = QLabel("-")
        layout.addWidget(QLabel("Omega Parameter (w):"), 2, 0)
        layout.addWidget(self.res_omega, 2, 1)
        layout.addWidget(QLabel("Critical Pressure Ratio (hc):"), 2, 2)
        layout.addWidget(self.res_hc, 2, 3)
        layout.addWidget(QLabel("Mass Flux (G) [lb/s/ft2]:"), 3, 0)
        layout.addWidget(self.res_g, 3, 1, 1, 3)

    def _update_extra_results(self, res):
        self.res_omega.setText(f"{res['Omega']:.5f}")
        self.res_hc.setText(f"{res['Critical_Pressure_Ratio_hc']:.5f}")
        self.res_g.setText(f"{res['Mass_Flux_G_lb_s_ft2']:.2f}")

    def _get_export_results(self):
        base = super()._get_export_results()
        base.update({
            "Omega Parameter": self.res_omega.text(),
            "Critical Pressure Ratio": self.res_hc.text(),
            "Mass Flux (G)": self.res_g.text()
        })
        return base

    def run_calculation(self):
        try:
            flow = float(self.flow_input.text())
            p0 = float(self.p0_input.text())
            pback = float(self.pback_input.text())
            v0 = float(self.v0_input.text())
            v9 = float(self.v9_input.text())
            kd = float(self.kd_input.text())

            if self.flow_unit.currentText() == "kg/h":
                flow = kg_h_to_lb_h(flow)
            
            if self.p0_unit.currentText() == "bara":
                p0 = bara_to_psia(p0)
                
            if self.pback_unit.currentText() == "barg":
                pback = barg_to_psia(pback)
                
            if self.v0_unit.currentText() == "m3/kg":
                v0 = m3_kg_to_ft3_lb(v0)
                
            if self.v9_unit.currentText() == "m3/kg":
                v9 = m3_kg_to_ft3_lb(v9)

            num_valves = int(self.num_valves_input.text())
            if num_valves < 1:
                num_valves = 1

            inputs = {'w_lb_h': flow, 'p0_psia': p0, 'p_back_psia': pback, 'v0': v0, 'v9': v9, 'kd': kd, 'num_valves': num_valves}
            self.last_inputs = inputs

            self.calc_btn.setEnabled(False)
            self.progress.setVisible(True)
            self.res_area.setText("Calculating...")
            
            self.worker = TwoPhaseCalcWorker(inputs)
            self.worker.finished.connect(self.on_calc_success)
            self.worker.error.connect(self.on_calc_error)
            self.worker.start()
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numerical values.")
        except Exception as e:
            QMessageBox.critical(self, "Calculation Error", f"Unexpected error: {str(e)}")
