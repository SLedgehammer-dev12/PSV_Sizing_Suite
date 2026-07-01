import os
import hashlib
import json
import urllib.request
import urllib.error
import ssl
import tempfile

from PyQt5.QtCore import QThread, pyqtSignal
from core.liquid_relief import calculate_liquid_relief_area
from core.gas_relief import calculate_gas_relief_area
from core.two_phase import calculate_two_phase_area, calculate_omega_flashing
from core.fire_scenarios import calculate_fire_wetted_load, calculate_fire_unwetted_area
from core.thermal_expansion import calculate_thermal_expansion_load
from core.valve_selection import select_orifice
from core.valve_types import calculate_pilot_gas_area, calculate_pilot_liquid_area, KD_GAS, KD_LIQUID, KD_TWO_PHASE
from core.kb_coefficient import get_kb


class UpdateCheckWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, url, headers=None, timeout=15):
        super().__init__()
        self.url = url
        self.headers = headers or {"Accept": "application/vnd.github.v3+json"}
        self.timeout = timeout

    def run(self):
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as response:
                data = json.loads(response.read().decode("utf-8"))
            self.finished.emit(data)
        except urllib.error.HTTPError as e:
            if e.code == 403:
                self.error.emit("GitHub API rate limit aşıldı. Lütfen daha sonra tekrar deneyin.")
            else:
                self.error.emit(f"GitHub API hatası: {e.code} {e.reason}")
        except urllib.error.URLError:
            self.error.emit("İnternet bağlantısı kontrol edilemedi.")
        except json.JSONDecodeError:
            self.error.emit("GitHub API yanıtı okunamadı.")
        except Exception as e:
            self.error.emit(f"Güncelleme kontrolü sırasında hata: {str(e)}")


class UpdateDownloadWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, expected_sha256=None, dest_dir=None):
        super().__init__()
        self.url = url
        self.expected_sha256 = expected_sha256
        self.dest_dir = dest_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            filename = self.url.rstrip('/').split('/')[-1]
            dest = self.dest_dir or os.path.join(tempfile.gettempdir(), 'PSV_Sizing_Suite_Update')
            os.makedirs(dest, exist_ok=True)
            tmp_path = os.path.join(dest, filename)

            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.url)
            with urllib.request.urlopen(req, timeout=60, context=ctx) as response:
                total = int(response.headers.get('Content-Length', 0))
                sha256 = hashlib.sha256()
                downloaded = 0
                chunk_size = 8192

                with open(tmp_path, 'wb') as f:
                    while True:
                        if self._cancelled:
                            os.remove(tmp_path)
                            self.error.emit("Indirme iptal edildi.")
                            return
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        sha256.update(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total, filename)

            if self.expected_sha256:
                actual = sha256.hexdigest()
                prefix = "sha256:"
                expected = self.expected_sha256[len(prefix):] if self.expected_sha256.startswith(prefix) else self.expected_sha256
                if actual != expected:
                    os.remove(tmp_path)
                    self.error.emit(f"SHA256 uyusmazligi: beklenen {expected}, alinan {actual}")
                    return

            self.finished.emit(tmp_path)

        except urllib.error.HTTPError as e:
            self.error.emit(f"Indirme hatasi: HTTP {e.code} {e.reason}")
        except urllib.error.URLError:
            self.error.emit("Indirme basarisiz: Internet baglantisi kontrol edilemedi.")
        except Exception as e:
            self.error.emit(f"Indirme sirasinda hata: {str(e)}")


class LiquidCalcWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, inputs):
        super().__init__()
        self.inputs = inputs

    def run(self):
        try:
            valve_type = self.inputs.get('valve_type', 'conventional')

            if valve_type == 'pilot':
                res = calculate_pilot_liquid_area(
                    q_gpm=self.inputs['q_gpm'],
                    p1_psia=self.inputs['p1_psia'],
                    p2_psia=self.inputs['p2_psia'],
                    g=self.inputs['g'],
                    mu_cp=self.inputs['mu_cp'],
                    num_valves=self.inputs.get('num_valves', 1)
                )
            else:
                res = calculate_liquid_relief_area(
                    q_gpm=self.inputs['q_gpm'],
                    p1_psia=self.inputs['p1_psia'],
                    p2_psia=self.inputs['p2_psia'],
                    g=self.inputs['g'],
                    mu_cp=self.inputs['mu_cp'],
                    kd=KD_LIQUID,
                    num_valves=self.inputs.get('num_valves', 1)
                )
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))

class GasCalcWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, inputs):
        super().__init__()
        self.inputs = inputs

    def run(self):
        try:
            valve_type = self.inputs.get('valve_type', 'conventional')
            overpressure_pct = self.inputs.get('overpressure_pct', 10.0)
            set_pressure_psig = self.inputs.get('set_pressure_psig', None)

            if valve_type == 'pilot':
                res = calculate_pilot_gas_area(
                    w_lb_h=self.inputs['w_lb_h'],
                    p1_psia=self.inputs['p1_psia'],
                    p2_psia=self.inputs['p2_psia'],
                    t_rankine=self.inputs['t_rankine'],
                    z=self.inputs['z'],
                    mw=self.inputs['mw'],
                    k=self.inputs['k'],
                    num_valves=self.inputs.get('num_valves', 1)
                )
            else:
                set_psig = set_pressure_psig or self.inputs.get('set_pressure_psig_from_p1')
                kb = get_kb(self.inputs['p2_psia'], set_psig or 100,
                           valve_type, overpressure_pct)
                res = calculate_gas_relief_area(
                    w_lb_h=self.inputs['w_lb_h'],
                    p1_psia=self.inputs['p1_psia'],
                    p2_psia=self.inputs['p2_psia'],
                    t_rankine=self.inputs['t_rankine'],
                    z=self.inputs['z'],
                    mw=self.inputs['mw'],
                    k=self.inputs['k'],
                    kd=KD_GAS,
                    kb=kb,
                    num_valves=self.inputs.get('num_valves', 1)
                )
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))

class TwoPhaseCalcWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, inputs):
        super().__init__()
        self.inputs = inputs

    def run(self):
        try:
    
            omega = calculate_omega_flashing(self.inputs['v0'], self.inputs['v9'])
            res = calculate_two_phase_area(
                w_lb_h=self.inputs['w_lb_h'],
                p0_psia=self.inputs['p0_psia'],
                p_back_psia=self.inputs['p_back_psia'],
                v0_ft3_lb=self.inputs['v0'],
                omega=omega,
                kd=self.inputs.get('kd', 0.85),
                num_valves=self.inputs.get('num_valves', 1)
            )
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))

class FireWettedWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, inputs):
        super().__init__()
        self.inputs = inputs

    def run(self):
        try:
    
            w_lb_h, q_btu_h = calculate_fire_wetted_load(
                a_wetted_sqft=self.inputs['a_wetted'],
                f_factor=self.inputs['f_factor'],
                heat_of_vap_btu_lb=self.inputs['h_vap']
            )
            valve_type = self.inputs.get('valve_type', 'conventional')
            if valve_type == 'pilot':
                res = calculate_pilot_gas_area(
                    w_lb_h=w_lb_h,
                    p1_psia=self.inputs['p1_psia'],
                    p2_psia=self.inputs.get('p2_psia', 14.7),
                    t_rankine=self.inputs['t_rankine'],
                    z=self.inputs['z'],
                    mw=self.inputs['mw'],
                    k=self.inputs['k'],
                    num_valves=self.inputs.get('num_valves', 1)
                )
            else:
                res = calculate_gas_relief_area(
                    w_lb_h=w_lb_h,
                    p1_psia=self.inputs['p1_psia'],
                    p2_psia=self.inputs.get('p2_psia', 14.7),
                    t_rankine=self.inputs['t_rankine'],
                    z=self.inputs['z'],
                    mw=self.inputs['mw'],
                    k=self.inputs['k'],
                    kd=KD_GAS,
                    kb=get_kb(self.inputs.get('p2_psia', 14.7), self.inputs.get('set_pressure_psig', 100),
                             valve_type, self.inputs.get('overpressure_pct', 10.0)),
                    num_valves=self.inputs.get('num_valves', 1)
                )
            res['Relief_Load_lb_h'] = w_lb_h
            res['Heat_Absorption_Btu_h'] = q_btu_h
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))

class FireUnwettedWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, inputs):
        super().__init__()
        self.inputs = inputs

    def run(self):
        try:
    
            a_req, f_prime = calculate_fire_unwetted_area(
                a_exposed_sqft=self.inputs['a_exposed'],
                p1_psia=self.inputs['p1_psia'],
                t_gas_rankine=self.inputs['t_gas'],
                t_wall_rankine=self.inputs['t_wall'],
                k=self.inputs['k']
            )
            letter, selected_area = select_orifice(a_req)
            res = {
                'F_Prime': f_prime,
                'Required_Area_sqin': a_req,
                'Selected_Orifice_Letter': letter,
                'Selected_Orifice_Area_sqin': selected_area
            }
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))

class ThermalWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, inputs):
        super().__init__()
        self.inputs = inputs

    def run(self):
        try:
    
            q_gpm = calculate_thermal_expansion_load(
                b_expansion_coeff=self.inputs['b'],
                h_heat_transfer_btu_h=self.inputs['h_btu'],
                g_specific_gravity=self.inputs['g'],
                c_specific_heat=self.inputs['c']
            )
            valve_type = self.inputs.get('valve_type', 'conventional')
            if valve_type == 'pilot':
                res = calculate_pilot_liquid_area(
                    q_gpm=q_gpm,
                    p1_psia=self.inputs['p1_psia'],
                    p2_psia=self.inputs['p2_psia'],
                    g=self.inputs['g'],
                    mu_cp=self.inputs['mu_cp']
                )
            else:
                res = calculate_liquid_relief_area(
                    q_gpm=q_gpm,
                    p1_psia=self.inputs['p1_psia'],
                    p2_psia=self.inputs['p2_psia'],
                    g=self.inputs['g'],
                    mu_cp=self.inputs['mu_cp'],
                    kd=KD_LIQUID
                )
            res['Relief_Load_gpm'] = q_gpm
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


class GraphCalcWorker(QThread):
    finished = pyqtSignal(list, list, float)
    error = pyqtSignal(str)

    def __init__(self, tab_name, inputs):
        super().__init__()
        self.tab_name = tab_name
        self.inputs = inputs

    def run(self):
        import numpy as np
        try:
            base_p1 = self.inputs.get('p1_psia') or self.inputs.get('p0_psia')
            if not base_p1:
                self.error.emit("No pressure value found.")
                return

            p_vals = np.linspace(base_p1 * 0.5, base_p1 * 1.5, 40)
            a_vals = []

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
                elif "Fire (Unwetted)" in self.tab_name:
                    a_req, _ = calculate_fire_unwetted_area(temp_inputs['a_exposed'], p, temp_inputs['t_gas'], temp_inputs['t_wall'], temp_inputs['k'])
                    a_vals.append(a_req)
                elif "Thermal" in self.tab_name:
                    q_gpm = calculate_thermal_expansion_load(temp_inputs['b'], temp_inputs['h_btu'], temp_inputs['g'], temp_inputs['c'])
                    res = calculate_liquid_relief_area(q_gpm, p, temp_inputs['p2_psia'], temp_inputs['g'], temp_inputs['mu_cp'], num_valves=1)
                    a_vals.append(res['Required_Area_Final_sqin'])

            self.finished.emit(p_vals.tolist(), a_vals, base_p1)
        except Exception as e:
            self.error.emit(str(e))
