import math
from typing import Optional
from .valve_selection import select_orifice
from .kb_coefficient import get_kb
from .advanced_sizing import calculate_napier_steam_area

# API 520 Section 7 — Pilot-operated discharge coefficients
KD_GAS_PILOT = 0.99
KD_LIQUID_PILOT = 0.80

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


def calculate_gas_relief_area(
    w_lb_h, p1_psia, p2_psia, t_rankine, z, mw, k,
    kd=0.975, kb=None, kc=1.0, num_valves=1,
    valve_type="conventional", set_pressure_psig=None, overpressure_pct=10.0,
    is_steam=False, use_napier=False
):
    """
    Calculate required area for gas/vapor relief using API 520 formulation.
    Determines whether flow is critical or subcritical automatically.
    
    If is_steam is True, it also performs Napier steam calculation.
    Depending on use_napier, it uses either Napier or API Gas as primary sizing,
    with the other as a verification check.
    
    For pilot-operated valves (valve_type="pilot"), uses Kd = 0.99 (API 520 Section 7).
    """
    # Pilot valve Kd override (API 520 Section 7)
    if valve_type == "pilot" and not is_steam:
        kd = KD_GAS_PILOT

    # Auto-calculate Kb if not provided
    if kb is None:
        if set_pressure_psig:
            sp = set_pressure_psig
        else:
            p1_gauge = max(p1_psia - 14.6959, 0.0)
            sp = p1_gauge / (1.0 + overpressure_pct / 100.0)
        kb = get_kb(p2_psia, sp, valve_type, overpressure_pct)

    # Standard gas calculation
    p_cf = p1_psia * ((2.0 / (k + 1.0)) ** (k / (k - 1.0)))
    flow_type = "CRITICAL" if p2_psia <= p_cf else "SUBCRITICAL"
    
    if flow_type == "CRITICAL":
        c = calculate_c_coefficient(k)
        term_sqrt = math.sqrt((z * t_rankine) / mw)
        a_req_gas = (w_lb_h / (c * kd * p1_psia * kb * kc)) * term_sqrt
        f2 = None
    else:
        r = p2_psia / p1_psia
        f2 = calculate_f2_coefficient(k, r)
        c = None
        term_sqrt = math.sqrt((z * t_rankine) / (mw * p1_psia * (p1_psia - p2_psia)))
        a_req_gas = (w_lb_h / (735.0 * f2 * kd * kc)) * term_sqrt

    a_req_gas_per_valve = a_req_gas / num_valves
    letter_gas, selected_area_gas = select_orifice(a_req_gas_per_valve)

    res_gas = {
        'Flow_Type': flow_type,
        'Critical_Pressure_psia': p_cf,
        'C_Coefficient': c,
        'F2_Coefficient': f2,
        'Required_Area_sqin': a_req_gas_per_valve,
        'Selected_Orifice_Letter': letter_gas,
        'Selected_Orifice_Area_sqin': selected_area_gas,
        'Num_Valves': num_valves,
        'Kb_Factor': kb,
        'Kd_Used': kd,
    }

    if is_steam:
        # Perform Napier steam calculation
        res_napier = calculate_napier_steam_area(
            w_lb_h=w_lb_h, p1_psia=p1_psia, p2_psia=p2_psia,
            t_rankine=t_rankine, kd=kd, kb=kb, kc=kc, num_valves=num_valves
        )
        
        if use_napier:
            # Napier is primary
            res_main = res_napier.copy()
            res_main['Verification_Required_Area_sqin'] = res_gas['Required_Area_sqin']
            res_main['Verification_Orifice_Letter'] = res_gas['Selected_Orifice_Letter']
            res_main['Verification_Method'] = 'API 520 Gaz/Buhar Denklemi'
            res_main['API_Gas_Flow_Type'] = res_gas['Flow_Type']
            res_main['API_Gas_Critical_Pressure_psia'] = res_gas['Critical_Pressure_psia']
            return res_main
        else:
            # Standard gas is primary
            res_main = res_gas.copy()
            res_main['Verification_Required_Area_sqin'] = res_napier['Required_Area_sqin']
            res_main['Verification_Orifice_Letter'] = res_napier['Selected_Orifice_Letter']
            res_main['Verification_Method'] = 'Napier Buhar Denklemi'
            res_main['Kn'] = res_napier['Kn']
            res_main['Ksh'] = res_napier['Ksh']
            return res_main

    return res_gas

