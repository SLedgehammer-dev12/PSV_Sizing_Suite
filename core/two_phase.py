import math
from typing import Dict, Union, Optional
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
    kb: Optional[float] = None,
    kc: float = 1.0,
    num_valves: int = 1,
    valve_type: str = "conventional",
    set_pressure_psig: Optional[float] = None,
    overpressure_pct: float = 10.0,
    is_subcooled_flashing: bool = False,
    use_c23: bool = False,
    p_sat_psia: float = 0.0,
) -> Dict[str, Union[float, str]]:
    """
    Calculate required area for two-phase flow (Omega method) per API 520.
    Determines whether flow is critical or subcritical automatically.
    
    If is_subcooled_flashing is True, it also calculates relief area per API 520 Appendix C.2.3.
    """
    from .kb_coefficient import get_kb
    from .advanced_sizing import area_relief_2phase_subcooled

    if kb is None:
        if valve_type == "balanced_bellows":
            if set_pressure_psig:
                sp = set_pressure_psig
            else:
                p0_gauge = max(p0_psia - 14.6959, 0.0)
                sp = p0_gauge / (1.0 + overpressure_pct / 100.0)
            kb = get_kb(p_back_psia, sp, valve_type, overpressure_pct)
        else:
            kb = 1.0

    # Standard two-phase Omega method calculation
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

    res_standard = {
        'Omega': omega,
        'Critical_Pressure_Ratio_hc': eta_c,
        'Critical_Pressure_psia': p_critical_psia,
        'Flow_Type': flow_type,
        'Mass_Flux_G_lb_s_ft2': g_flux,
        'Required_Area_sqin': a_req_per_valve,
        'Selected_Orifice_Letter': letter,
        'Selected_Orifice_Area_sqin': selected_area,
        'Num_Valves': num_valves,
        'Kb': kb,
    }

    if is_subcooled_flashing:
        # Reconstruct variables for API 520 C.2.3 subcooled flashing liquid model
        # Q (L/min) = W (lb/h) * v0 (ft3/lb) * 0.4719474
        q_l_min = w_lb_h * v0_ft3_lb * 0.4719474
        p1_bara = p0_psia * 0.06894757
        p2_bara = p_back_psia * 0.06894757
        ps_bara = p_sat_psia * 0.06894757
        rho1_kg_m3 = 1.0 / (v0_ft3_lb * 0.01601846)
        rho9_kg_m3 = rho1_kg_m3 / (1.0 + omega / 9.0)

        # For subcooled flashing liquid, Kd defaults to 0.65 (API 520 C.2.3.2)
        kd_subcooled = 0.65

        res_c23_raw = area_relief_2phase_subcooled(
            q_l_min=q_l_min,
            p1_bara=p1_bara,
            p2_bara=p2_bara,
            ps_bara=ps_bara,
            rho1_kg_m3=rho1_kg_m3,
            rho9_kg_m3=rho9_kg_m3,
            kd=kd_subcooled,
            kb=kb,
            kc=kc,
            kv=1.0,
            num_valves=num_valves
        )

        res_c23 = {
            'Omega': res_c23_raw['Omega_s'],
            'Critical_Pressure_Ratio_hc': res_c23_raw['Transition_Ratio'],
            'Critical_Pressure_psia': res_c23_raw['Critical_Pressure_bara'] / 0.06894757 if not math.isnan(res_c23_raw['Critical_Pressure_bara']) else 0.0,
            'Flow_Type': res_c23_raw['Flow_Type'],
            'Mass_Flux_G_lb_s_ft2': res_c23_raw['Mass_Flux_G_kg_s_m2'] * 0.204816,
            'Required_Area_sqin': res_c23_raw['Required_Area_sqin'],
            'Selected_Orifice_Letter': res_c23_raw['Selected_Orifice_Letter'],
            'Selected_Orifice_Area_sqin': res_c23_raw['Selected_Orifice_Area_sqin'],
            'Num_Valves': res_c23_raw['Num_Valves'],
            'Kb': res_c23_raw['Kb'],
            'High_Subcooling': res_c23_raw['High_Subcooling'],
        }

        if use_c23:
            res_main = res_c23.copy()
            res_main['Verification_Required_Area_sqin'] = res_standard['Required_Area_sqin']
            res_main['Verification_Orifice_Letter'] = res_standard['Selected_Orifice_Letter']
            res_main['Verification_Method'] = 'Standart iki fazlı Omega Metodu'
            return res_main
        else:
            res_main = res_standard.copy()
            res_main['Verification_Required_Area_sqin'] = res_c23['Required_Area_sqin']
            res_main['Verification_Orifice_Letter'] = res_c23['Selected_Orifice_Letter']
            res_main['Verification_Method'] = 'API 520 C.2.3 Flashing Modeli'
            return res_main

    return res_standard

