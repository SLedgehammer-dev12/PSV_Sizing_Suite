import math
from typing import Dict, Union
from .valve_selection import select_orifice

# 68.09 = (1/3600) * sqrt( 2 * 32.174 * 144 * 25000 )
# Unit conversion factor: lb/h → lb/s, psi→psf, g_c, 25000 for consistency
MASS_FLUX_CONSTANT = 68.09


def calculate_omega_flashing(v0: float, v9: float) -> float:
    """
    Calculate the Omega parameter for flashing two-phase systems (API 520).
    
    Parameters
    ----------
    v0 : Specific volume at inlet (ft3/lb)
    v9 : Specific volume at 90% of inlet pressure (ft3/lb)
    
    Returns
    -------
    Omega parameter (dimensionless)
    """
    if v0 <= 0:
        raise ValueError("Inlet specific volume v0 must be positive.")
    return 9.0 * ((v9 / v0) - 1.0)


def calculate_omega_subcooled(
    p0_psia: float,
    p_sat_psia: float,
    v0_ft3_lb: float,
    v_sat_ft3_lb: float,
    h0_btu_lb: float,
    h_sat_btu_lb: float,
) -> float:
    """
    Calculate effective Omega for a subcooled liquid entering the valve.
    
    API 520 Part I Section 5.8 — subcooled omega method.
    When the inlet fluid is subcooled liquid, use the saturated
    properties at P0 to determine the effective Omega.

    Parameters
    ----------
    p0_psia : Relieving pressure (psia)
    p_sat_psia : Saturation pressure at inlet temperature (psia)
    v0_ft3_lb : Specific volume at inlet (ft3/lb)
    v_sat_ft3_lb : Specific volume at saturation (ft3/lb)
    h0_btu_lb : Enthalpy at inlet (Btu/lb)
    h_sat_btu_lb : Enthalpy at saturation (Btu/lb)

    Returns
    -------
    Effective Omega (dimensionless)
    """
    if p0_psia <= 0 or p_sat_psia <= 0:
        raise ValueError("Pressures must be positive.")

    # Omega for flashing fraction
    omega_flashing = 9.0 * ((v_sat_ft3_lb / v0_ft3_lb) - 1.0)

    # Subcooling correction: lower effective Omega
    # API 520 Eq. 5.18
    subcool_ratio = (p0_psia - p_sat_psia) / p0_psia
    if subcool_ratio > 0:
        omega_effective = omega_flashing * math.exp(-4.5 * subcool_ratio)
    else:
        omega_effective = omega_flashing

    return max(omega_effective, 0.01)  # floor at 0.01


def calculate_critical_pressure_ratio(omega: float) -> float:
    """
    Calculate critical pressure ratio (eta_c) for two-phase flow
    using API 520 empirical correlation (Leung/DIERS method).

    Parameters
    ----------
    omega : Omega compressibility parameter

    Returns
    -------
    Critical pressure ratio (Pc/P0), dimensionless
    """
    if omega <= 0:
        return 0.0

    term1 = 1.0446 + 0.0093431 * math.sqrt(omega)
    term2 = omega ** -0.56261
    base = 1.0 + term1 * term2

    if omega > 0:
        power = -0.70356 + 0.014685 * math.log(omega)
    else:
        power = -0.70356

    return base ** power


def calculate_two_phase_area(
    w_lb_h: float,
    p0_psia: float,
    p_back_psia: float,
    v0_ft3_lb: float,
    omega: float,
    kd: float = 0.85,
    kb: float = 1.0,
    kc: float = 1.0,
    num_valves: int = 1,
) -> Dict[str, Union[float, str]]:
    """
    Calculate required area for two-phase flow (Omega method) per API 520.
    
    Parameters
    ----------
    w_lb_h : Mass flow rate (lb/h)
    p0_psia : Stagnation relieving pressure (psia)
    p_back_psia : Back pressure (psia)
    v0_ft3_lb : Specific volume at inlet (ft3/lb)
    omega : Omega compressibility parameter
    kd : Discharge coefficient (default 0.85 for two-phase)
    kb : Back pressure correction (default 1.0)
    kc : Combination correction (default 1.0)
    num_valves : Number of parallel valves (default 1)
    """
    eta_c = calculate_critical_pressure_ratio(omega)
    p_critical_psia = eta_c * p0_psia

    flow_type = "CRITICAL" if p_back_psia <= p_critical_psia else "SUBCRITICAL"

    if flow_type == "CRITICAL":
        g_flux = MASS_FLUX_CONSTANT * eta_c * math.sqrt(p0_psia / (v0_ft3_lb * omega))
    else:
        eta = p_back_psia / p0_psia
        term_sqrt1 = math.sqrt(p0_psia / (v0_ft3_lb * omega))

        inner = -2.0 * (omega * math.log(eta) + (omega - 1.0) * (1.0 - eta))
        if inner < 0:
            inner = 0.0

        term_sqrt2 = math.sqrt(inner)
        denominator = (omega / eta) + 1.0 - omega

        g_flux = (MASS_FLUX_CONSTANT * term_sqrt1 * term_sqrt2) / denominator

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
        'Num_Valves': num_valves,
    }
