import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox
from PyQt5.QtCore import Qt

from core.liquid_relief import calculate_liquid_relief_area
from core.gas_relief import calculate_gas_relief_area
from core.two_phase import calculate_two_phase_area, calculate_omega_flashing

class PlotWindow(QDialog):
    def __init__(self, parent, tab_name, inputs, results):
        super().__init__(parent)
        self.setWindowTitle(f"Performans ve Hassasiyet Grafiği - {tab_name}")
        self.resize(850, 650)
        self.tab_name = tab_name
        self.inputs = inputs
        self.results = results
        
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        self.plot_data()

    def plot_data(self):
        ax = self.figure.add_subplot(111)
        ax.clear()
        
        try:
            # Determine base pressure P1
            base_p1 = self.inputs.get('p1_psia')
            if not base_p1:
                base_p1 = self.inputs.get('p0_psia') # For two phase
                
            if not base_p1:
                QMessageBox.warning(self, "Grafik Hatası", "Hesaplanan bir basınç değeri bulunamadı.")
                self.close()
                return

            # X-axis array: 50% to 150% of Set Pressure
            p_vals = np.linspace(base_p1 * 0.5, base_p1 * 1.5, 40)
            a_vals = []
            
            # Extract Selected Area from result label string "Letter (Area sq.inch)"
            selected_area_str = self.results.get('res_orifice', '0').split('(')[-1].replace(' sq.inch)', '').strip()
            try:
                selected_area = float(selected_area_str)
            except ValueError:
                selected_area = 0

            # Calculate Required Area for each pressure step
            for p in p_vals:
                temp_inputs = self.inputs.copy()
                if "Liquid" in self.tab_name:
                    res = calculate_liquid_relief_area(temp_inputs['q_gpm'], p, temp_inputs['p2_psia'], temp_inputs['g'], temp_inputs['mu_cp'], num_valves=temp_inputs.get('num_valves', 1))
                    a_vals.append(res['Required_Area_Final_sqin'])
                elif "Gas" in self.tab_name or "Fire (Wetted)" in self.tab_name:
                    res = calculate_gas_relief_area(temp_inputs['w_lb_h'], p, temp_inputs.get('p2_psia', 14.7), temp_inputs['t_rankine'], temp_inputs['z'], temp_inputs['mw'], temp_inputs['k'], num_valves=temp_inputs.get('num_valves', 1))
                    a_vals.append(res['Required_Area_sqin'])
                elif "Two-Phase" in self.tab_name:
                    omega = calculate_omega_flashing(temp_inputs['v0'], temp_inputs['v9'])
                    res = calculate_two_phase_area(temp_inputs['w_lb_h'], p, temp_inputs['p_back_psia'], temp_inputs['v0'], omega, temp_inputs['kd'], num_valves=temp_inputs.get('num_valves', 1))
                    a_vals.append(res['Required_Area_sqin'])
                else:
                    QMessageBox.warning(self, "Bilgi", "Grafik modülü şu an sadece Sıvı, Gaz ve İki Fazlı akışlar için aktiftir.")
                    self.close()
                    return
            
            # Plot the Required Area Curve
            ax.plot(p_vals, a_vals, 'b-', linewidth=2.5, label="Gerekli Kesit Alanı (Required Area)")
            
            # Highlight selected area and safety margins
            if selected_area > 0:
                ax.axhline(y=selected_area, color='r', linestyle='--', linewidth=2, label=f"Seçilen API Orifis Alanı ({selected_area} sq.in)")
                ax.fill_between(p_vals, a_vals, selected_area, where=(np.array(a_vals) <= selected_area), color='green', alpha=0.15, label="Güvenlik Marjı (Safety Margin)")
                ax.fill_between(p_vals, a_vals, selected_area, where=(np.array(a_vals) > selected_area), color='red', alpha=0.15, label="Tehlike Bölgesi (Undersized)")

            # Mark the actual operation point
            calc_area = self.results_area_val()
            if calc_area > 0:
                ax.axvline(x=base_p1, color='k', linestyle=':', label=f"Hesaplanan Tahliye Basıncı ({base_p1:.2f} psia)")
                ax.plot(base_p1, calc_area, 'ko', markersize=8, label="Çalışma Noktası")

            ax.set_title(f"PSV Performans ve Hassasiyet Eğrisi\n{self.tab_name}", fontsize=12, fontweight='bold')
            ax.set_xlabel("Tahliye Basıncı / Relieving Pressure (psia)", fontsize=10)
            ax.set_ylabel("Kesit Alanı / Area (sq.inch)", fontsize=10)
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.legend(loc="upper right", framealpha=0.9)
            
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            QMessageBox.warning(self, "Grafik Çizim Hatası", f"Eğri oluşturulurken bir hata meydana geldi:\n{str(e)}")
            self.close()

    def results_area_val(self):
        val_str = self.results.get('res_area', '0').replace(' sq.inch', '').strip()
        try:
            return float(val_str)
        except ValueError:
            return 0.0
