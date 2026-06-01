import math
from typing import Dict, Tuple, Union
from .gas_relief import calculate_c_coefficient

# API 521 Table 7 — Environment factors (F)
# For wetted vessels exposed to open fire with prompt drainage
ENV_FACTORS: Dict[str, float] = {
    "bare": 1.0,
    "drainage_1_in": 0.5,
    "drainage_4_in": 0.3,
    "insulation_1_in": 0.15,
    "insulation_2_in": 0.07,
    "insulation_4_in": 0.03,
    "foam": 0.65,
    "depressurization": 0.5,
    "water_spray": 0.33,
    "fireproofing": 0.2,
}


def get_env_factor(description: str = "bare") -> float:
    """Look up environment factor from API 521 Table 7."""
    return ENV_FACTORS.get(description, 1.0)


def calculate_heat_absorption(
    a_wetted_sqft: float, f_factor: float
) -> float:
    """
    Calculate total heat absorption rate for fire exposure.

    API 521 Eq. 7:
    Q = 21000 * F * A^0.82          for A <= 20000 sqft
    Q = 21000 * F * 20000^0.82
        + CGA * F * (A - 20000)     for A > 20000 sqft

    where CGA = 21000 Btu/h/ft2 (conservative default).

    Parameters
    ----------
    a_wetted_sqft : Wetted surface area (sqft)
    f_factor : Environment factor (dimensionless)

    Returns
    -------
    Total heat absorption (Btu/h)
    """
    if a_wetted_sqft <= 0:
        return 0.0

    base_heat = 21000.0 * f_factor * (a_wetted_sqft ** 0.82)

    if a_wetted_sqft > 20000:
        excess = a_wetted_sqft - 20000
        cga_factor = 21000.0  # conservative for general hydrocarbon
        base_heat = (
            21000.0 * f_factor * (20000.0 ** 0.82)
            + cga_factor * f_factor * excess
        )

    return base_heat


def calculate_fire_wetted_load(
    a_wetted_sqft: float,
    f_factor: float,
    heat_of_vap_btu_lb: float,
) -> Tuple[float, float]:
    """
    Calculate relief load for a wetted vessel exposed to fire (API 521).

    Parameters
    ----------
    a_wetted_sqft : Wetted surface area (sqft)
    f_factor : Environment factor (dimensionless)
    heat_of_vap_btu_lb : Latent heat of vaporization (Btu/lb)

    Returns
    -------
    (w_lb_h, q_btu_h) — relief load (lb/h), heat absorption (Btu/h)
    """
    if heat_of_vap_btu_lb <= 0:
        raise ValueError("Heat of vaporization must be positive.")

    q_btu_h = calculate_heat_absorption(a_wetted_sqft, f_factor)
    w_lb_h = q_btu_h / heat_of_vap_btu_lb

    return w_lb_h, q_btu_h


def calculate_fire_unwetted_area(
    a_exposed_sqft: float,
    p1_psia: float,
    t_gas_rankine: float,
    t_wall_rankine: float,
    k: float,
    kd: float = 0.975,
    alpha: float = 0.5,
) -> Tuple[float, float]:
    """
    Calculate required relief area for unwetted (gas-filled) vessel
    exposed to fire (API 521 Section 4.4.13).

    Parameters
    ----------
    a_exposed_sqft : Exposed surface area (sqft)
    p1_psia : Relieving pressure (psia)
    t_gas_rankine : Operating gas temperature (Rankine)
    t_wall_rankine : Maximum wall temperature (Rankine)
    k : Ratio of specific heats (Cp/Cv)
    kd : Discharge coefficient (default 0.975)
    alpha : Radiation absorptivity (default 0.5)

    Returns
    -------
    (a_req, f_prime) — required area (sqin), F' factor (dimensionless)
    """
    if t_wall_rankine <= t_gas_rankine:
        return 0.0, 0.0

    c = calculate_c_coefficient(k)

    temp_term = (
        (t_wall_rankine - t_gas_rankine) ** 1.25
    ) / (t_gas_rankine ** 0.65)
    f_prime = (0.1406 / (c * kd)) * temp_term

    a_req = (f_prime * a_exposed_sqft) / math.sqrt(p1_psia)

    # Adjust for absorptivity (alpha = 0.5 for bare carbon steel)
    # API 521 recommends alpha = 0.5 for most carbon/low-alloy steels
    a_req_adjusted = a_req * (alpha / 0.5)

    return a_req_adjusted, f_prime