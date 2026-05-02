def calculate_thermal_expansion_load(b_expansion_coeff, h_heat_transfer_btu_h, g_specific_gravity, c_specific_heat):
    """
    Calculate relief load due to thermal (hydraulic) expansion (API 521).
    
    b_expansion_coeff: Cubical expansion coefficient (1/°F)
    h_heat_transfer_btu_h: Total heat transfer rate (BTU/h)
    g_specific_gravity: Specific gravity of the liquid
    c_specific_heat: Specific heat capacity (BTU/lb°F)
    
    Returns:
    Required relief load Q in US GPM
    """
    if g_specific_gravity <= 0 or c_specific_heat <= 0:
        raise ValueError("Specific gravity and specific heat must be greater than zero.")
        
    q_gpm = (b_expansion_coeff * h_heat_transfer_btu_h) / (500.0 * g_specific_gravity * c_specific_heat)
    
    return q_gpm
