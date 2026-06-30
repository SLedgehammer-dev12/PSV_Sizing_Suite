import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox, QLabel
from PyQt5.QtCore import Qt

from desktop.workers import GraphCalcWorker


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

        self.status_label = QLabel("Hesaplaniyor...", self)
        self.status_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.worker = GraphCalcWorker(self.tab_name, self.inputs)
        self.worker.finished.connect(self.on_calc_finished)
        self.worker.error.connect(self.on_calc_error)
        self.worker.start()

    def on_calc_finished(self, p_vals, a_vals, base_p1):
        self.status_label.hide()
        ax = self.figure.add_subplot(111)
        ax.clear()

        try:
            selected_area = self.results.get('sel_area_sqin', 0)
            if selected_area == 0:
                selected_area = self.results.get('sel_area_sqin_fallback', 0)

            ax.plot(p_vals, a_vals, 'b-', linewidth=2.5, label="Gerekli Kesit Alani (Required Area)")

            if selected_area > 0:
                ax.axhline(y=selected_area, color='r', linestyle='--', linewidth=2, label=f"Secilen API Orifis Alani ({selected_area:.4f} sq.in)")
                a_arr = np.array(a_vals)
                ax.fill_between(p_vals, a_arr, selected_area, where=(a_arr <= selected_area), color='green', alpha=0.15, label="Guvenlik Marji (Safety Margin)")
                ax.fill_between(p_vals, a_arr, selected_area, where=(a_arr > selected_area), color='red', alpha=0.15, label="Tehlike Bolgesi (Undersized)")

            calc_area = self.results.get('req_area_sqin', 0)
            if calc_area == 0:
                calc_area = self.results.get('req_area_sqin_fallback', 0)

            if calc_area > 0:
                ax.axvline(x=base_p1, color='k', linestyle=':', label=f"Hesaplanan Tahliye Basinci ({base_p1:.2f} psia)")
                ax.plot(base_p1, calc_area, 'ko', markersize=8, label="Calisma Noktasi")

            ax.set_title(f"PSV Performans ve Hassasiyet Egrisi\n{self.tab_name}", fontsize=12, fontweight='bold')
            ax.set_xlabel("Tahliye Basinci / Relieving Pressure (psia)", fontsize=10)
            ax.set_ylabel("Kesit Alani / Area (sq.inch)", fontsize=10)
            ax.grid(True, linestyle='--', alpha=0.6)
            ax.legend(loc="upper right", framealpha=0.9)

            self.figure.tight_layout()
            self.canvas.draw()

        except Exception as e:
            QMessageBox.warning(self, "Grafik Cizim Hatasi", f"Egri olusturulurken bir hata meydana geldi:\n{str(e)}")
            self.close()

    def on_calc_error(self, err_msg):
        QMessageBox.warning(self, "Grafik Hatasi", f"Hesaplama sirasinda hata:\n{err_msg}")
        self.close()
