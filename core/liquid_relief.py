import math
from .valve_selection import select_orifice
from .validation import validate_liquid_inputs
from .constants import (
    LIQUID_FORMULA_CONSTANT, REYNOLDS_CONSTANT,
    KV_A, KV_B, KV_C,
)


def calculate_reynolds(q_gpm, g, mu_cp, area_sq_in):
    if area_sq_in <= 0 or mu_cp <= 0:
        return float('inf')
    return (REYNOLDS_CONSTANT * q_gpm * g) / (mu_cp * math.sqrt(area_sq_in))

def calculate_kv(re):
    """API 520 Part I (9th/10th ed.) Eq. (34): Kv = (0.9935 + 2.878/Re^0.5 + 342.75/Re^1.5)^-1."""
    if re <= 0 or math.isinf(re):
        return 1.0
    kv = 1.0 / (KV_A + KV_B / re ** 0.5 + KV_C / re ** 1.5)
    return min(kv, 1.0)


def calculate_liquid_relief_area(q_gpm, p1_psia, p2_psia, g, mu_cp, kd=0.65, kw=1.0, kc=1.0, num_valves=1):
    """
    API 520 Part I Section 5.8 — Liquid relief valve sizing.

    Uses Reynolds-number-dependent iterative sizing with Kv viscosity
    correction factor. Returns required area, selected orifice, Re, and Kv.
    """
    validate_liquid_inputs(q_gpm, p1_psia, p2_psia, g, mu_cp, kd, kw)
    if num_valves < 1:
        raise ValueError("num_valves must be >= 1")

    delta_p = p1_psia - p2_psia

    a_req_no_visc = (q_gpm / (LIQUID_FORMULA_CONSTANT * kd * kw * kc)) * math.sqrt(g / delta_p)
    a_req_no_visc_per_valve = a_req_no_visc / num_valves

    letter, selected_area = select_orifice(a_req_no_visc_per_valve)

    re = calculate_reynolds(q_gpm / num_valves, g, mu_cp, selected_area)
    kv = calculate_kv(re)
    a_req_final = (q_gpm / (LIQUID_FORMULA_CONSTANT * kd * kw * kc * kv)) * math.sqrt(g / delta_p)
    a_req_final_per_valve = a_req_final / num_valves
    final_letter, final_selected_area = select_orifice(a_req_final_per_valve)

    prev_letter = final_letter
    for iteration in range(10):
        re = calculate_reynolds(q_gpm / num_valves, g, mu_cp, final_selected_area)
        kv = calculate_kv(re)
        a_req_final = (q_gpm / (LIQUID_FORMULA_CONSTANT * kd * kw * kc * kv)) * math.sqrt(g / delta_p)
        a_req_final_per_valve = a_req_final / num_valves
        new_letter, new_selected_area = select_orifice(a_req_final_per_valve)
        if new_letter == prev_letter:
            final_letter, final_selected_area = new_letter, new_selected_area
            break
        prev_letter = new_letter
        final_letter, final_selected_area = new_letter, new_selected_area

    loading_pct = (a_req_final_per_valve / final_selected_area * 100.0
                   if isinstance(final_selected_area, (int, float)) else None)

    return {
        'Required_Area_No_Visc_sqin': a_req_no_visc_per_valve,
        'Reynolds_Number': re,
        'Kv': kv,
        'Required_Area_Final_sqin': a_req_final_per_valve,
        'Selected_Orifice_Letter': final_letter,
        'Selected_Orifice_Area_sqin': final_selected_area,
        'Orifice_Loading_Pct': loading_pct,
        'Kd': kd,
        'Kc': kc,
        'Num_Valves': num_valves
    }
