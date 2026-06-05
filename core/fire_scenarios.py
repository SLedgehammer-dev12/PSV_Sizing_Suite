import math
from typing import Dict, Tuple, Union, Optional
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
    a_wetted_sqft: float,
    f_factor: float,
    adequate_drainage: bool = True,
    wetted_area_cap: Optional[float] = 2800.0,
) -> float:
    """
    Calculate total heat absorption rate for fire exposure.

    API 521 Eq. 7:
    Q = C * F * A^0.82

    where C = 21000 if adequate drainage and firefighting exist,
    otherwise C = 34500.

    Parameters
    ----------
    a_wetted_sqft : Wetted surface area (sqft)
    f_factor : Environment factor (dimensionless)
    adequate_drainage : Whether adequate drainage and prompt firefighting are present
    wetted_area_cap : Maximum wetted surface area to consider (default 2800.0 sqft)

    Returns
    -------
    Total heat absorption (Btu/h)
    """
    if a_wetted_sqft <= 0:
        return 0.0

    c_factor = 21000.0 if adequate_drainage else 34500.0
    effective_area = a_wetted_sqft
    if wetted_area_cap is not None and wetted_area_cap > 0:
        effective_area = min(a_wetted_sqft, wetted_area_cap)

    return c_factor * f_factor * (effective_area ** 0.82)


def calculate_fire_wetted_load(
    a_wetted_sqft: float,
    f_factor: float,
    heat_of_vap_btu_lb: float,
    adequate_drainage: bool = True,
    wetted_area_cap: Optional[float] = 2800.0,
) -> Tuple[float, float]:
    """
    Calculate relief load for a wetted vessel exposed to fire (API 521).

    Parameters
    ----------
    a_wetted_sqft : Wetted surface area (sqft)
    f_factor : Environment factor (dimensionless)
    heat_of_vap_btu_lb : Latent heat of vaporization (Btu/lb)
    adequate_drainage : Whether adequate drainage and prompt firefighting are present
    wetted_area_cap : Maximum wetted surface area to consider (default 2800.0 sqft)

    Returns
    -------
    (w_lb_h, q_btu_h) — relief load (lb/h), heat absorption (Btu/h)
    """
    if heat_of_vap_btu_lb <= 0:
        raise ValueError("Heat of vaporization must be positive.")

    q_btu_h = calculate_heat_absorption(
        a_wetted_sqft, f_factor, adequate_drainage, wetted_area_cap
    )
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