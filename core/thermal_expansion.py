from .validation import validate_thermal_inputs
from .constants import THERMAL_EXPANSION_CONSTANT

def calculate_thermal_expansion_load(b_expansion_coeff, h_heat_transfer_btu_h, g_specific_gravity, c_specific_heat):
    validate_thermal_inputs(b_expansion_coeff, h_heat_transfer_btu_h, g_specific_gravity, c_specific_heat)

    q_gpm = (b_expansion_coeff * h_heat_transfer_btu_h) / (THERMAL_EXPANSION_CONSTANT * g_specific_gravity * c_specific_heat)

    return q_gpm
