"""
Venting noise estimation for pressure relief valves.

Simplified methodology per API 521 (Pressure-relieving and Depressuring
Systems). For a sonic (critical) jet discharging to atmosphere, the sound
pressure level at a distance r from the vent is estimated from the acoustic
power of the jet:

    L_p(r) = 10 * log10( (W * a^2) / (4 * pi * r^2 * I_ref) )

where
    W      mass flow rate [kg/s]
    a      speed of sound at relieving conditions [m/s]
    r      distance from the vent [m]
    I_ref  reference sound intensity 10^-12 W/m^2

This is an order-of-magnitude screening estimate. Detailed analysis (jet
noise models, attenuation, bundling, absorption) is outside its scope.
"""
import math

GC = 32.174
# Universal gas constant in ft.lbf/(lbmol.degR)
R_UNIVERSAL = 1545.0
FT_TO_M = 0.3048
LB_TO_KG = 0.45359237
I_REF = 1e-12


def calculate_sonic_velocity_fps(k, mw, t_rankine):
    """Speed of sound [ft/s] for an ideal gas at relieving conditions."""
    r_gas = R_UNIVERSAL / mw  # ft.lbf/(lbm.degR)
    return math.sqrt(k * r_gas * t_rankine * GC)


def calculate_noise_level(w_lb_h, k, mw, t_rankine, distance_ft, num_valves=1):
    """
    Estimate the sound pressure level [dB] at `distance_ft` from an
    atmospheric relief valve vent.

    Parameters
    ----------
    w_lb_h : Total mass flow rate (lb/h)
    k : Specific heat ratio (Cp/Cv)
    mw : Molecular weight (lb/lbmol)
    t_rankine : Relieving temperature (degR)
    distance_ft : Distance from the vent (ft)
    num_valves : Number of parallel valves sharing the flow
    """
    if w_lb_h <= 0:
        raise ValueError("Mass flow rate must be positive.")
    if distance_ft <= 0:
        raise ValueError("Distance must be positive.")
    if k <= 0 or mw <= 0 or t_rankine <= 0:
        raise ValueError("k, MW and temperature must be positive.")

    a_ft_s = calculate_sonic_velocity_fps(k, mw, t_rankine)
    a_m_s = a_ft_s * FT_TO_M

    w_lb_s = (w_lb_h / 3600.0) / max(num_valves, 1)
    w_kg_s = w_lb_s * LB_TO_KG

    r_m = distance_ft * FT_TO_M
    intensity = (w_kg_s * a_m_s ** 2) / (4.0 * math.pi * r_m ** 2)
    if intensity <= 0:
        raise ValueError("Computed sound intensity is not positive.")

    spl_db = 10.0 * math.log10(intensity / I_REF)
    return {
        'Sound_Pressure_Level_dB': spl_db,
        'Sonic_Velocity_fps': a_ft_s,
        'Distance_ft': distance_ft,
        'Flow_per_Valve_lb_h': (w_lb_h / max(num_valves, 1)),
    }