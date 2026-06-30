import math
from .valve_selection import select_orifice
from .validation import validate_liquid_inputs
from .constants import (
    LIQUID_FORMULA_CONSTANT, REYNOLDS_CONSTANT,
    REYNOLDS_UPPER_BOUND, REYNOLDS_LOWER_BOUND,
    KV_UPPER, KV_LOWER, KV_COEFF_A, KV_COEFF_B, KV_COEFF_C,
)


def calculate_reynolds(q_gpm, g, mu_cp, area_sq_in):
    if area_sq_in <= 0 or mu_cp <= 0:
        return float('inf')
    return (REYNOLDS_CONSTANT * q_gpm * g) / (mu_cp * math.sqrt(area_sq_in))

def calculate_kv(re):
    if re >= REYNOLDS_UPPER_BOUND:
        return KV_UPPER
    if re <= REYNOLDS_LOWER_BOUND:
        return KV_LOWER

    kv = KV_UPPER / (KV_COEFF_A + (KV_COEFF_B / math.sqrt(re)) + (KV_COEFF_C / re))
    return min(max(kv, KV_LOWER), KV_UPPER)


def calculate_liquid_relief_area(q_gpm, p1_psia, p2_psia, g, mu_cp, kd=0.65, kw=1.0, num_valves=1):
    """
    API 520 Part I Section 5.8 — Liquid relief valve sizing.

    Uses Reynolds-number-dependent iterative sizing with Kv viscosity
    correction factor. Returns required area, selected orifice, Re, and Kv.
    """
    validate_liquid_inputs(q_gpm, p1_psia, p2_psia, g, mu_cp, kd, kw)
    if num_valves < 1:
        raise ValueError("num_valves must be >= 1")

    delta_p = p1_psia - p2_psia

    a_req_no_visc = (q_gpm / (LIQUID_FORMULA_CONSTANT * kd * kw * KV_UPPER)) * math.sqrt(g / delta_p)
    a_req_no_visc_per_valve = a_req_no_visc / num_valves

    letter, selected_area = select_orifice(a_req_no_visc_per_valve)

    re = calculate_reynolds(q_gpm / num_valves, g, mu_cp, selected_area)
    kv = calculate_kv(re)
    a_req_final = (q_gpm / (LIQUID_FORMULA_CONSTANT * kd * kw * kv)) * math.sqrt(g / delta_p)
    a_req_final_per_valve = a_req_final / num_valves
    final_letter, final_selected_area = select_orifice(a_req_final_per_valve)

    prev_letter = final_letter
    for iteration in range(10):
        re = calculate_reynolds(q_gpm / num_valves, g, mu_cp, final_selected_area)
        kv = calculate_kv(re)
        a_req_final = (q_gpm / (LIQUID_FORMULA_CONSTANT * kd * kw * kv)) * math.sqrt(g / delta_p)
        a_req_final_per_valve = a_req_final / num_valves
        new_letter, new_selected_area = select_orifice(a_req_final_per_valve)
        if new_letter == prev_letter:
            final_letter, final_selected_area = new_letter, new_selected_area
            break
        prev_letter = new_letter
        final_letter, final_selected_area = new_letter, new_selected_area

    return {
        'Required_Area_No_Visc_sqin': a_req_no_visc_per_valve,
        'Reynolds_Number': re,
        'Kv': kv,
        'Required_Area_Final_sqin': a_req_final_per_valve,
        'Selected_Orifice_Letter': final_letter,
        'Selected_Orifice_Area_sqin': final_selected_area,
        'Num_Valves': num_valves
    }
