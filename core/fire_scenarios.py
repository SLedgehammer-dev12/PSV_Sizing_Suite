from .gas_relief import calculate_c_coefficient
from .validation import validate_fire_wetted_inputs, validate_fire_unwetted_inputs
from .constants import (
    FIRE_WETTED_HEAT_CONSTANT, FIRE_WETTED_AREA_EXPONENT,
    FIRE_UNWETTED_COEFF, FIRE_UNWETTED_WALL_EXPONENT, FIRE_UNWETTED_GAS_EXPONENT,
)
import math

def calculate_fire_wetted_load(a_wetted_sqft, f_factor, heat_of_vap_btu_lb):
    validate_fire_wetted_inputs(a_wetted_sqft, f_factor, heat_of_vap_btu_lb)

    q_btu_h = FIRE_WETTED_HEAT_CONSTANT * f_factor * (a_wetted_sqft ** FIRE_WETTED_AREA_EXPONENT)
    w_lb_h = q_btu_h / heat_of_vap_btu_lb

    return w_lb_h, q_btu_h


def calculate_fire_unwetted_area(a_exposed_sqft, p1_psia, t_gas_rankine, t_wall_rankine, k, kd=0.975):
    validate_fire_unwetted_inputs(a_exposed_sqft, p1_psia, t_gas_rankine, t_wall_rankine, k)

    c = calculate_c_coefficient(k)

    temp_term = ((t_wall_rankine - t_gas_rankine) ** FIRE_UNWETTED_WALL_EXPONENT) / (t_gas_rankine ** FIRE_UNWETTED_GAS_EXPONENT)
    f_prime = (FIRE_UNWETTED_COEFF / (c * kd)) * temp_term

    a_req = (f_prime * a_exposed_sqft) / math.sqrt(p1_psia)

    return a_req, f_prime
