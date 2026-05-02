import math
from .valve_selection import select_orifice

def calculate_reynolds(q_gpm, g, mu_cp, area_sq_in):
    """
    Calculate Reynolds number for liquid relief.
    Re = (2800 * Q * G) / (mu * sqrt(A))
    """
    if area_sq_in <= 0 or mu_cp <= 0:
        return float('inf')
    return (2800.0 * q_gpm * g) / (mu_cp * math.sqrt(area_sq_in))

def calculate_kv(re):
    """
    Calculate Viscosity Correction Factor (Kv) based on Reynolds Number.
    Using standard API 520 curve fit approximations.
    """
    if re >= 10000:
        return 1.0
    if re <= 10:
        return 0.1 
    
    # API 520 equation for Kv numerical approximation
    kv = 1.0 / (0.9935 + (2.878 / math.sqrt(re)) + (342.75 / re))
    return min(max(kv, 0.1), 1.0)


def calculate_liquid_relief_area(q_gpm, p1_psia, p2_psia, g, mu_cp, kd=0.65, kw=1.0, num_valves=1):
    """
    Calculate required area for liquid relief using API 520 formulation.
    
    Parameters:
    q_gpm: Flow rate in US Gal/min
    p1_psia: Relieving pressure in psia
    p2_psia: Total back pressure in psia
    g: Specific gravity
    mu_cp: Viscosity in cP
    kd: Discharge coefficient (default 0.65 for liquid)
    kw: Back pressure capacity correction factor (default 1.0)
    
    Returns:
    dict containing calculated parameters.
    """
    delta_p = p1_psia - p2_psia
    if delta_p <= 0:
        raise ValueError("Relieving pressure must be greater than back pressure.")
        
    # First pass: calculate area without viscosity correction (Kv = 1.0)
    a_req_no_visc = (q_gpm / (38.0 * kd * kw * 1.0)) * math.sqrt(g / delta_p)
    a_req_no_visc_per_valve = a_req_no_visc / num_valves
    
    # Select an initial standard orifice based on uncorrected area
    letter, selected_area = select_orifice(a_req_no_visc_per_valve)
    
    # Iterate to find final area with Kv
    if isinstance(selected_area, float):
        re = calculate_reynolds(q_gpm, g, mu_cp, selected_area * num_valves)
        kv = calculate_kv(re)
        a_req_final = (q_gpm / (38.0 * kd * kw * kv)) * math.sqrt(g / delta_p)
        a_req_final_per_valve = a_req_final / num_valves
        final_letter, final_selected_area = select_orifice(a_req_final_per_valve)
        
        # Additional iterations for stabilization
        for _ in range(3):
            if isinstance(final_selected_area, float):
                re = calculate_reynolds(q_gpm, g, mu_cp, final_selected_area * num_valves)
                kv = calculate_kv(re)
                a_req_final = (q_gpm / (38.0 * kd * kw * kv)) * math.sqrt(g / delta_p)
                a_req_final_per_valve = a_req_final / num_valves
                new_letter, new_selected_area = select_orifice(a_req_final_per_valve)
                if new_letter == final_letter:
                    break
                final_letter, final_selected_area = new_letter, new_selected_area
    else:
        # Multiple valves required
        kv = 1.0
        re = float('inf')
        a_req_final = a_req_no_visc
        a_req_final_per_valve = a_req_no_visc_per_valve
        final_letter = letter
        final_selected_area = selected_area

    return {
        'Required_Area_No_Visc_sqin': a_req_no_visc_per_valve,
        'Reynolds_Number': re,
        'Kv': kv,
        'Required_Area_Final_sqin': a_req_final_per_valve,
        'Selected_Orifice_Letter': final_letter,
        'Selected_Orifice_Area_sqin': final_selected_area,
        'Num_Valves': num_valves
    }
