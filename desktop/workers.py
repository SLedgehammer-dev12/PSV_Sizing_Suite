from PyQt5.QtCore import QThread, pyqtSignal
from core.liquid_relief import calculate_liquid_relief_area
from core.gas_relief import calculate_gas_relief_area
from core.two_phase import calculate_two_phase_area, calculate_omega_flashing
from core.fire_scenarios import calculate_fire_wetted_load, calculate_fire_unwetted_area
from core.thermal_expansion import calculate_thermal_expansion_load

class LiquidCalcWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, inputs):
        super().__init__()
        self.inputs = inputs

    def run(self):
        try:
            res = calculate_liquid_relief_area(
                q_gpm=self.inputs['q_gpm'],
                p1_psia=self.inputs['p1_psia'],
                p2_psia=self.inputs['p2_psia'],
                g=self.inputs['g'],
                mu_cp=self.inputs['mu_cp'],
                num_valves=self.inputs.get('num_valves', 1),
                valve_type=self.inputs.get('valve_type', 'conventional'),
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
            res = calculate_gas_relief_area(
                w_lb_h=self.inputs['w_lb_h'],
                p1_psia=self.inputs['p1_psia'],
                p2_psia=self.inputs['p2_psia'],
                t_rankine=self.inputs['t_rankine'],
                z=self.inputs['z'],
                mw=self.inputs['mw'],
                k=self.inputs['k'],
                num_valves=self.inputs.get('num_valves', 1),
                valve_type=self.inputs.get('valve_type', 'conventional'),
                set_pressure_psig=self.inputs.get('set_pressure_psig'),
                overpressure_pct=self.inputs.get('overpressure_pct', 10.0),
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
            p2 = self.inputs.get('p2_psia', 14.6959)
            res = calculate_gas_relief_area(
                w_lb_h=w_lb_h,
                p1_psia=self.inputs['p1_psia'],
                p2_psia=p2,
                t_rankine=self.inputs['t_rankine'],
                z=self.inputs['z'],
                mw=self.inputs['mw'],
                k=self.inputs['k']
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
            from core.valve_selection import select_orifice
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
            res = calculate_liquid_relief_area(
                q_gpm=q_gpm,
                p1_psia=self.inputs['p1_psia'],
                p2_psia=self.inputs['p2_psia'],
                g=self.inputs['g'],
                mu_cp=self.inputs['mu_cp']
            )
            res['Relief_Load_gpm'] = q_gpm
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))
