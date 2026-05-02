import math
from .valve_selection import select_orifice

def calculate_omega_flashing(v0, v9):
    """
    Calculate the Omega parameter for flashing two-phase systems.
    v0: Specific volume at inlet (ft3/lb)
    v9: Specific volume at 90% of inlet pressure (ft3/lb)
    """
    return 9.0 * ((v9 / v0) - 1.0)


def calculate_critical_pressure_ratio(omega):
    """
    Calculate critical pressure ratio (eta_c) for two-phase flow
    using API 520 empirical correlation.
    """
    if omega <= 0:
        return 0.0
    
    term1 = 1.0446 + 0.0093431 * math.sqrt(omega)
    term2 = omega ** -0.56261
    base = 1.0 + term1 * term2
    
    power = -0.70356 + 0.014685 * math.log(omega)
    
    return base ** power


def calculate_two_phase_area(w_lb_h, p0_psia, p_back_psia, v0_ft3_lb, omega, kd=0.85, kb=1.0, kc=1.0, num_valves=1):
    """
    Calculate required area for two-phase flow (Omega method) using API 520.
    
    w_lb_h: Mass flow rate in lb/h
    p0_psia: Stagnation relieving pressure in psia
    p_back_psia: Back pressure in psia
    v0_ft3_lb: Specific volume at inlet in ft3/lb
    omega: Compressibility parameter
    """
    eta_c = calculate_critical_pressure_ratio(omega)
    p_critical_psia = eta_c * p0_psia
    
    flow_type = "CRITICAL" if p_back_psia <= p_critical_psia else "SUBCRITICAL"
    
    # Calculate mass flux G (lb/s/ft2)
    if flow_type == "CRITICAL":
        # Critical flow mass flux
        g_flux = 68.09 * eta_c * math.sqrt(p0_psia / (v0_ft3_lb * omega))
    else:
        # Subcritical flow mass flux
        eta = p_back_psia / p0_psia
        term_sqrt1 = math.sqrt(p0_psia / (v0_ft3_lb * omega))
        
        # Inner terms
        # -2 * [ omega * ln(eta) + (omega - 1) * (1 - eta) ]
        inner = -2.0 * (omega * math.log(eta) + (omega - 1.0) * (1.0 - eta))
        if inner < 0:
            inner = 0 # failsafe
            
        term_sqrt2 = math.sqrt(inner)
        denominator = (omega / eta) + 1.0 - omega
        
        g_flux = (68.09 * term_sqrt1 * term_sqrt2) / denominator

    # Required Area in sq.inch
    # A = W / (25 * G * Kd * Kb * Kc)
    a_req = w_lb_h / (25.0 * g_flux * kd * kb * kc)
    
    a_req_per_valve = a_req / num_valves
    
    letter, selected_area = select_orifice(a_req_per_valve)
    
    return {
        'Omega': omega,
        'Critical_Pressure_Ratio_hc': eta_c,
        'Critical_Pressure_psia': p_critical_psia,
        'Flow_Type': flow_type,
        'Mass_Flux_G_lb_s_ft2': g_flux,
        'Required_Area_sqin': a_req_per_valve,
        'Selected_Orifice_Letter': letter,
        'Selected_Orifice_Area_sqin': selected_area,
        'Num_Valves': num_valves
    }
