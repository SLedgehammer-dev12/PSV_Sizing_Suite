import math
from .valve_selection import select_orifice
from .kb_coefficient import get_kb

def calculate_c_coefficient(k):
    """
    Calculate gas constant C based on ratio of specific heats (k).
    API 520 Part I formulation.
    """
    if k <= 0:
        return 315.0
    if abs(k - 1.0) < 1e-10:
        return 315.0
    exponent = (k + 1.0) / (k - 1.0)
    return 520.0 * math.sqrt(k * ((2.0 / (k + 1.0)) ** exponent))


def calculate_f2_coefficient(k, r):
    """
    Calculate F2 coefficient for subcritical gas flow.
    r = P2 / P1 (Back pressure / Relieving pressure)
    """
    if r >= 1.0:
        return 0.0
    if r <= 0.0:
        r = 1e-10
    if abs(k - 1.0) < 1e-10:
        term = (2.0 * r ** 2.0 * math.log(1.0 / r)) / (1.0 - r ** 2.0)
        if term < 0:
            return 0.0
        return math.sqrt(term)
    
    term1 = k / (k - 1.0)
    term2 = r ** (2.0 / k)
    term3 = (1.0 - (r ** ((k - 1.0) / k))) / (1.0 - r)
    
    if term1 <= 0 or term3 <= 0:
        return 0.0
    
    return math.sqrt(term1 * term2 * term3)


def calculate_gas_relief_area(w_lb_h, p1_psia, p2_psia, t_rankine, z, mw, k, kd=0.975, kb=None, kc=1.0, num_valves=1, valve_type="conventional", set_pressure_psig=None):
    """
    Calculate required area for gas/vapor relief using API 520 formulation.
    Determines whether flow is critical or subcritical automatically.
    
    Parameters:
    w_lb_h: Mass flow rate in lb/h
    p1_psia: Relieving pressure in psia
    p2_psia: Total back pressure in psia
    t_rankine: Relieving temperature in Rankine
    z: Compressibility factor
    mw: Molecular weight
    k: Ratio of specific heats (Cp/Cv)
    kd: Discharge coefficient (default 0.975 for gas)
    kb: Back pressure correction factor (auto-calculated if None)
    kc: Combination correction factor for rupture disks (default 1.0)
    valve_type: "conventional" or "balanced_bellows"
    set_pressure_psig: Required for kb auto-calculation
    """
    # Auto-calculate Kb if not provided
    if kb is None:
        sp = set_pressure_psig if set_pressure_psig else (p1_psia - 14.6959)
        kb = get_kb(p2_psia, sp, valve_type)
    # Calculate critical flow pressure
    # P_cf = P1 * (2 / (k+1))^(k/(k-1))
    p_cf = p1_psia * ((2.0 / (k + 1.0)) ** (k / (k - 1.0)))
    
    flow_type = "CRITICAL" if p2_psia <= p_cf else "SUBCRITICAL"
    
    if flow_type == "CRITICAL":
        c = calculate_c_coefficient(k)
        # A = (W / (C * Kd * P1 * Kb * Kc)) * sqrt((Z * T) / M)
        term_sqrt = math.sqrt((z * t_rankine) / mw)
        a_req = (w_lb_h / (c * kd * p1_psia * kb * kc)) * term_sqrt
        f2 = None
    else:
        # SUBCRITICAL flow
        r = p2_psia / p1_psia
        f2 = calculate_f2_coefficient(k, r)
        c = None
        # Subcritical API formula:
        # A = W / [ 735 * F2 * Kd * Kc * sqrt( (P1 * (P1 - P2) * M) / (Z * T) ) ]
        # Rearranging as in API 520: A = (W / (735 * F2 * Kd * Kc)) * sqrt( (Z * T) / (M * P1 * (P1 - P2)) )
        term_sqrt = math.sqrt((z * t_rankine) / (mw * p1_psia * (p1_psia - p2_psia)))
        a_req = (w_lb_h / (735.0 * f2 * kd * kc)) * term_sqrt

    a_req_per_valve = a_req / num_valves
    letter, selected_area = select_orifice(a_req_per_valve)

    return {
        'Flow_Type': flow_type,
        'Critical_Pressure_psia': p_cf,
        'C_Coefficient': c,
        'F2_Coefficient': f2,
        'Required_Area_sqin': a_req_per_valve,
        'Selected_Orifice_Letter': letter,
        'Selected_Orifice_Area_sqin': selected_area,
        'Num_Valves': num_valves
    }
