import sys

with open('desktop/tabs.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add imports if not present
if "from desktop.report_generator import generate_and_open_report" not in code:
    code = code.replace("from desktop.vendor_window import VendorTableWidget", 
                        "from desktop.vendor_window import VendorTableWidget\nfrom desktop.report_generator import generate_and_open_report\nfrom desktop.graph_window import PlotWindow")

# Replace buttons
liquid_btn_old = """        self.calc_btn = QPushButton("HESAPLA (CALCULATE)")
        self.calc_btn.setMinimumHeight(45)
        self.calc_btn.setStyleSheet("font-weight: bold; font-size: 14px; background-color: #2980b9; color: white; border-radius: 5px;")
        self.calc_btn.clicked.connect(self.run_calculation)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)

        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.calc_btn)"""

btn_new = """        self.btn_layout = QHBoxLayout()

        self.calc_btn = QPushButton("HESAPLA (CALCULATE)")
        self.calc_btn.setMinimumHeight(45)
        self.calc_btn.setStyleSheet("font-weight: bold; font-size: 14px; background-color: #2980b9; color: white; border-radius: 5px;")
        self.calc_btn.clicked.connect(self.run_calculation)

        self.pdf_btn = QPushButton("PDF ÇIKTISI (EXPORT PDF)")
        self.pdf_btn.setMinimumHeight(45)
        self.pdf_btn.setStyleSheet("font-weight: bold; font-size: 14px; background-color: #27ae60; color: white; border-radius: 5px;")
        self.pdf_btn.clicked.connect(self.export_pdf)
        
        self.graph_btn = QPushButton("GRAFİK (SHOW GRAPH)")
        self.graph_btn.setMinimumHeight(45)
        self.graph_btn.setStyleSheet("font-weight: bold; font-size: 14px; background-color: #8e44ad; color: white; border-radius: 5px;")
        self.graph_btn.clicked.connect(self.show_graph)

        self.btn_layout.addWidget(self.calc_btn)
        self.btn_layout.addWidget(self.pdf_btn)
        self.btn_layout.addWidget(self.graph_btn)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)

        main_layout.addWidget(self.progress)
        main_layout.addLayout(self.btn_layout)"""

code = code.replace(liquid_btn_old, btn_new)

# Update the generic update_result_units
old_update_units = """    def update_result_units(self):
        if not hasattr(self, 'last_res'): return
        res = self.last_res
        unit = self.res_area_unit.currentText()
        mult = 645.16 if unit == "mm²" else 1.0
        
        req_area = res.get('Required_Area_Final_sqin', res.get('Required_Area_sqin', 0)) * mult
        sel_area = res.get('Selected_Orifice_Area_sqin', 0) * mult
        
        self.res_area.setText(f"{req_area:.4f} {unit}")
        if res.get('Selected_Orifice_Letter', '-') != '-':
            self.res_orifice.setText(f"{res['Selected_Orifice_Letter']} ({sel_area:.2f} {unit})")
        else:
            self.res_orifice.setText("-")"""

new_update_units_liquid = """    def update_result_units(self):
        if not hasattr(self, 'last_res'): return
        res = self.last_res
        unit = self.res_area_unit.currentText()
        mult = 645.16 if unit == "mm²" else 1.0
        
        req_area = res.get('Required_Area_Final_sqin', res.get('Required_Area_sqin', 0)) * mult
        sel_area = res.get('Selected_Orifice_Area_sqin', 0)
        if isinstance(sel_area, (int, float)): sel_area *= mult
        
        self.res_area.setText(f"{req_area:.4f} {unit}")
        
        letter = res.get('Selected_Orifice_Letter', '-')
        if "Multiple" in str(letter):
            self.res_orifice.setStyleSheet("color: white; background-color: #e74c3c; font-weight: bold; padding: 2px; border-radius: 3px;")
            self.res_orifice.setText(f"DİKKAT: 'T' Orifisini aştı! Lütfen Paralel Vana Sayısını artırın.")
        elif letter != '-':
            self.res_orifice.setStyleSheet("color: #c0392b; font-weight: bold;")
            self.res_orifice.setText(f"{letter} ({sel_area:.2f} {unit})")
        else:
            self.res_orifice.setText("-")

    def export_pdf(self):
        if not hasattr(self, 'last_res'):
            QMessageBox.warning(self, "Uyarı", "Lütfen önce HESAPLA butonuna basın.")
            return
        results = {
            "Required Area": self.res_area.text(),
            "Selected API Orifice": self.res_orifice.text(),
            "Reynolds Number (Re)": self.res_re.text(),
            "Viscosity Corr. (Kv)": self.res_kv.text()
        }
        generate_and_open_report("Liquid Relief", self.last_inputs, results)

    def show_graph(self):
        if not hasattr(self, 'last_res'):
            QMessageBox.warning(self, "Uyarı", "Lütfen önce HESAPLA butonuna basın.")
            return
        results = {"res_area": self.res_area.text(), "res_orifice": self.res_orifice.text()}
        self.plot_win = PlotWindow(self, "Liquid Relief", self.last_inputs, results)
        self.plot_win.exec_()"""

new_update_units_gas = new_update_units_liquid.replace("Liquid Relief", "Gas/Vapor Relief").replace(
    '"Reynolds Number (Re)": self.res_re.text(),\n            "Viscosity Corr. (Kv)": self.res_kv.text()',
    '"Flow Regime": self.res_flow_type.text()'
)

new_update_units_two = new_update_units_liquid.replace("Liquid Relief", "Two-Phase Relief").replace(
    '"Reynolds Number (Re)": self.res_re.text(),\n            "Viscosity Corr. (Kv)": self.res_kv.text()',
    '"Omega Parameter": self.res_omega.text(),\n            "Critical Pressure Ratio": self.res_hc.text(),\n            "Mass Flux (G)": self.res_g.text()'
)

# Replace the first occurrence (Liquid)
code = code.replace(old_update_units, new_update_units_liquid, 1)
# Replace the second occurrence (Gas)
code = code.replace(old_update_units, new_update_units_gas, 1)
# Replace the third occurrence (TwoPhase)
code = code.replace(old_update_units, new_update_units_two, 1)

with open('desktop/tabs.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Updated tabs.py successfully")
