from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QPushButton, QLabel, QMessageBox, QGroupBox,
                             QProgressBar, QScrollArea, QComboBox)
from PyQt5.QtGui import QFont

from desktop.vendor_window import VendorTableWidget
from desktop.report_generator import generate_and_open_report
from desktop.graph_window import PlotWindow


class BaseCalcTab(QWidget):
    """Base class for all calculation tabs. Provides common UI patterns,
    result display, vendor table, buttons, and unit conversion."""

    def __init__(self, tab_name, calc_button_text="HESAPLA (CALCULATE)",
                 calc_button_color="#2980b9"):
        super().__init__()
        self.tab_name = tab_name
        self.calc_button_text = calc_button_text
        self.calc_button_color = calc_button_color
        self.last_inputs = None
        self.last_res = None
        self.main_layout = QVBoxLayout()
        self._build_ui()

    def _build_ui(self):
        self.init_inputs()
        self._setup_buttons()
        self._setup_result_group()
        self._setup_vendor_group()
        self._wrap_in_scroll()

    def init_inputs(self):
        """Override in subclass to create input widgets."""
        pass

    def _setup_buttons(self):
        self.btn_layout = QHBoxLayout()
        self.calc_btn = QPushButton(self.calc_button_text)
        self.calc_btn.setMinimumHeight(45)
        self.calc_btn.setStyleSheet(
            f"font-weight: bold; font-size: 14px; background-color: {self.calc_button_color}; "
            f"color: white; border-radius: 5px;"
        )
        self.calc_btn.clicked.connect(self.run_calculation)

        self.pdf_btn = QPushButton("PDF ÇIKTISI (EXPORT PDF)")
        self.pdf_btn.setMinimumHeight(45)
        self.pdf_btn.setStyleSheet(
            "font-weight: bold; font-size: 14px; background-color: #27ae60; "
            "color: white; border-radius: 5px;"
        )
        self.pdf_btn.clicked.connect(self.export_report)

        self.graph_btn = QPushButton("GRAFİK (SHOW GRAPH)")
        self.graph_btn.setMinimumHeight(45)
        self.graph_btn.setStyleSheet(
            "font-weight: bold; font-size: 14px; background-color: #8e44ad; "
            "color: white; border-radius: 5px;"
        )
        self.graph_btn.clicked.connect(self.show_graph)

        self.btn_layout.addWidget(self.calc_btn)
        self.btn_layout.addWidget(self.pdf_btn)
        self.btn_layout.addWidget(self.graph_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)

        self.main_layout.addWidget(self.progress)
        self.main_layout.addLayout(self.btn_layout)

    def _setup_result_group(self):
        result_group = QGroupBox("Results")
        result_group.setStyleSheet(
            "QGroupBox { background-color: #f8f9fa; border: 1px solid #dcdde1; "
            "border-radius: 5px; margin-top: 10px; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; "
            "font-weight: bold; color: #2c3e50; }"
        )
        res_layout = QGridLayout()

        self.res_area = QLabel("-")
        self.res_orifice = QLabel("-")

        res_font = QFont("Arial", 11, QFont.Bold)
        self.res_area.setFont(res_font)
        self.res_orifice.setFont(res_font)
        self.res_area.setStyleSheet("color: #27ae60;")
        self.res_orifice.setStyleSheet("color: #c0392b;")

        self.res_area_unit = QComboBox()
        self.res_area_unit.addItems(["mm²", "sq.inch"])
        self.res_area_unit.currentTextChanged.connect(self.update_result_units)

        self._add_result_widgets(res_layout)

        res_layout.addWidget(QLabel("<b>Required Area:</b>"), self._area_row(), 0)
        res_layout.addWidget(self.res_area, self._area_row(), 1)
        res_layout.addWidget(QLabel("<b>Unit:</b>"), self._area_row(), 2)
        res_layout.addWidget(self.res_area_unit, self._area_row(), 3)

        res_layout.addWidget(QLabel("<b>Selected API Orifice:</b>"), self._area_row() + 1, 0)
        res_layout.addWidget(self.res_orifice, self._area_row() + 1, 1, 1, 3)

        result_group.setLayout(res_layout)
        self.main_layout.addWidget(result_group)

    def _area_row(self):
        """Override if extra result widgets are added before the area row."""
        return 0

    def _add_result_widgets(self, layout):
        """Override in subclass to add extra result labels before area/orifice."""
        pass

    def _setup_vendor_group(self):
        vendor_group = QGroupBox("Uygun Ticari Vanalar (Vendor DB)")
        vendor_layout = QVBoxLayout()
        self.vendor_table_widget = VendorTableWidget()
        vendor_layout.addWidget(self.vendor_table_widget)
        vendor_group.setLayout(vendor_layout)
        self.main_layout.addWidget(vendor_group)
        self.main_layout.addStretch()

    def _wrap_in_scroll(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        container = QWidget()
        container.setLayout(self.main_layout)
        scroll.setWidget(container)

        wrapper = QVBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)
        self.setLayout(wrapper)

    def run_calculation(self):
        """Override in subclass to collect inputs and start worker."""
        pass

    def get_worker_class(self):
        """Override in subclass to return the worker class."""
        pass

    def on_calc_success(self, res):
        self.calc_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.last_res = res
        self.update_result_units()
        self._update_extra_results(res)
        self.vendor_table_widget.update_valves(
            res['Selected_Orifice_Letter'],
            self.last_inputs.get('valve_type') if hasattr(self, 'last_inputs') else None
        )

    def _update_extra_results(self, res):
        """Override in subclass to update extra result labels."""
        pass

    def update_result_units(self):
        if not hasattr(self, 'last_res') or self.last_res is None:
            return
        res = self.last_res
        unit = self.res_area_unit.currentText()
        mult = 645.16 if unit == "mm²" else 1.0

        req_area = res.get('Required_Area_Final_sqin', res.get('Required_Area_sqin', 0)) * mult
        sel_area = res.get('Selected_Orifice_Area_sqin', 0)
        if isinstance(sel_area, (int, float)):
            sel_area *= mult

        self.res_area.setText(f"{req_area:.4f} {unit}")

        letter = res.get('Selected_Orifice_Letter', '-')
        if "Multiple" in str(letter):
            self.res_orifice.setStyleSheet(
                "color: white; background-color: #e74c3c; font-weight: bold; "
                "padding: 2px; border-radius: 3px;"
            )
            self.res_orifice.setText(
                "DİKKAT: 'T' Orifisini aştı! Lütfen Paralel Vana Sayısını artırın."
            )
        elif letter != '-':
            self.res_orifice.setStyleSheet("color: #c0392b; font-weight: bold;")
            self.res_orifice.setText(f"{letter} ({sel_area:.2f} {unit})")
        else:
            self.res_orifice.setText("-")

    def export_report(self):
        if not hasattr(self, 'last_res') or self.last_res is None:
            QMessageBox.warning(self, "Uyarı", "Lutfen once HESAPLA butonuna basin.")
            return
        unit_system = "SI" if self.res_area_unit.currentText() == "mm²" else "USC"
        results = self._get_export_results()
        generate_and_open_report(self.tab_name, self.last_inputs, results, unit_system)

    def _get_export_results(self):
        """Override in subclass to return result dict for PDF export."""
        return {
            "Required Area": self.res_area.text(),
            "Selected API Orifice": self.res_orifice.text()
        }

    def show_graph(self):
        if not hasattr(self, 'last_res') or self.last_res is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce HESAPLA butonuna basın.")
            return
        results = self._get_graph_results()
        self.plot_win = PlotWindow(self, self.tab_name, self.last_inputs, results)
        self.plot_win.exec_()

    def _get_graph_results(self):
        """Override in subclass to return result dict for graph window."""
        return {
            "res_area": self.res_area.text(),
            "res_orifice": self.res_orifice.text(),
            "req_area_sqin": self.last_res.get('Required_Area_Final_sqin',
                                               self.last_res.get('Required_Area_sqin', 0)),
            "sel_area_sqin": self.last_res.get('Selected_Orifice_Area_sqin', 0)
        }

    def on_calc_error(self, err_msg):
        self.calc_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.res_area.setText("Error")
        QMessageBox.critical(self, "Calculation Error", err_msg)
