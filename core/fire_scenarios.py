from .gas_relief import calculate_c_coefficient
import math

def calculate_fire_wetted_load(a_wetted_sqft, f_factor, heat_of_vap_btu_lb):
    """
    Calculate relief load for a wetted vessel exposed to fire (API 521).
    Assumes standard prompt drainage condition (21000 constant).
    
    a_wetted_sqft: Wetted surface area in sq.ft
    f_factor: Environment factor (1.0 for bare vessel)
    heat_of_vap_btu_lb: Latent heat of vaporization in BTU/lb
    
    Returns:
    Relief load W in lb/h
    Total heat absorption in BTU/h
    """
    if heat_of_vap_btu_lb <= 0:
        raise ValueError("Heat of vaporization must be positive.")
        
    q_btu_h = 21000.0 * f_factor * (a_wetted_sqft ** 0.82)
    w_lb_h = q_btu_h / heat_of_vap_btu_lb
    
    return w_lb_h, q_btu_h


def calculate_fire_unwetted_area(a_exposed_sqft, p1_psia, t_gas_rankine, t_wall_rankine, k, kd=0.975):
    """
    Calculate required relief area for an unwetted vessel exposed to fire (API 521).
    
    a_exposed_sqft: Exposed surface area in sq.ft
    p1_psia: Relieving pressure in psia
    t_gas_rankine: Normal operating gas temperature in Rankine
    t_wall_rankine: Maximum expected wall temperature in Rankine
    k: Ratio of specific heats
    kd: Discharge coefficient
    
    Returns required area in sq.inch
    """
    if t_wall_rankine <= t_gas_rankine:
        return 0.0
        
    c = calculate_c_coefficient(k)
    
    # F' = (0.1406 / (C * Kd)) * ((Tw - T1)^1.25 / T1^0.65)
    temp_term = ((t_wall_rankine - t_gas_rankine) ** 1.25) / (t_gas_rankine ** 0.65)
    f_prime = (0.1406 / (c * kd)) * temp_term
    
    # Required Area A = (F' * A') / sqrt(P1)
    a_req = (f_prime * a_exposed_sqft) / math.sqrt(p1_psia)
    
    return a_req, f_prime
