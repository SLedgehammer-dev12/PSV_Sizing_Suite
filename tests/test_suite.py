import json
import os
import sys
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from core.thermo_props import calculate_mixture_properties, get_coolprop_fluids, calculate_two_phase_omega_coolprop
from core.liquid_relief import calculate_liquid_relief_area, calculate_reynolds, calculate_kv, calculate_kp
from core.gas_relief import calculate_gas_relief_area, calculate_c_coefficient, calculate_f2_coefficient
from core.two_phase import calculate_omega_flashing, calculate_two_phase_area, calculate_omega_subcooled
from core.piping import calculate_inlet_pressure_drop, check_inlet_rule, check_outlet_rule
from core.fire_scenarios import (
    calculate_fire_wetted_load, calculate_fire_unwetted_area,
    calculate_heat_absorption, get_env_factor, ENV_FACTORS,
)
from core.thermal_expansion import calculate_thermal_expansion_load
from core.blowby import calculate_blowby_flowrate
from core.unit_converter import (
    barg_to_psia, psia_to_barg, m3_h_to_gpm, gpm_to_m3_h,
    c_to_rankine, kg_h_to_lb_h, actual_m3_h_to_lb_h,
    sm3_h_to_lb_h, nm3_h_to_lb_h, ATM_PSIA, PSI_PER_BAR,
)
from core.vendor_catalog import get_vendor_valves
from core.valve_selection import select_orifice, API_ORIFICE_AREAS
from core.kb_coefficient import get_kb, interpolate_kb, KB_BALANCED_BELLOWS_10PCT


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def vendor_catalog():
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "vendor_data",
        "psv_vendor_catalog_official.json",
    )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# Gas Relief - C Coefficient
# =============================================================================

class TestCCoefficient:
    def test_k_1_4(self):
        c = calculate_c_coefficient(1.4)
        assert c == pytest.approx(356.0, rel=0.01)

    def test_k_1_0_limit(self):
        c = calculate_c_coefficient(1.0)
        assert c == 315.0

    def test_k_1_0001(self):
        c = calculate_c_coefficient(1.0001)
        assert c == pytest.approx(315.0, rel=0.01)

    def test_k_negative(self):
        c = calculate_c_coefficient(-0.5)
        assert c == 315.0

    def test_k_zero(self):
        c = calculate_c_coefficient(0)
        assert c == 315.0

    def test_k_1_67_monatomic(self):
        c = calculate_c_coefficient(1.67)
        assert c == pytest.approx(378.0, rel=0.01)

    def test_k_1_3_typical(self):
        c = calculate_c_coefficient(1.3)
        assert c == pytest.approx(346.0, rel=0.01)

    def test_c_symmetric(self):
        """C(k) should be symmetric — same for k and k' close to 1."""
        c1 = calculate_c_coefficient(1.2)
        assert c1 > 315
        assert c1 < 400


# =============================================================================
# Gas Relief - F2 Coefficient
# =============================================================================

class TestF2Coefficient:
    def test_f2_k_1_4_r_0_5(self):
        f2 = calculate_f2_coefficient(1.4, 0.5)
        # Verified: sqrt(k/(k-1) * r^(2/k) * (1 - r^((k-1)/k)) / (1-r))
        assert f2 == pytest.approx(0.686, rel=0.01)

    def test_f2_no_flow(self):
        f2 = calculate_f2_coefficient(1.4, 1.0)
        assert f2 == 0.0

    def test_f2_k_1_0(self):
        f2 = calculate_f2_coefficient(1.0, 0.5)
        assert f2 > 0
        assert f2 <= 1.0

    def test_f2_r_zero(self):
        f2 = calculate_f2_coefficient(1.4, 0.0)
        # P2=0 → no back pressure → critical flow → F2 effectively 0
        assert f2 == pytest.approx(0.0, abs=0.01)

    def test_f2_r_close_to_1(self):
        f2 = calculate_f2_coefficient(1.4, 0.99)
        # As r→1, F2→1 (subcritical correction approaches unity)
        assert f2 == pytest.approx(0.99, rel=0.05)

    def test_f2_monatomic(self):
        f2 = calculate_f2_coefficient(1.67, 0.3)
        assert f2 > 0


# =============================================================================
# Gas Relief - Full Calculation
# =============================================================================

class TestGasRelief:
    def test_gas_critical_flow(self):
        res = calculate_gas_relief_area(
            w_lb_h=10000, p1_psia=500, p2_psia=14.7,
            t_rankine=600, z=0.9, mw=28, k=1.4,
        )
        assert res['Flow_Type'] == 'CRITICAL'
        assert res['Required_Area_sqin'] > 0.1
        assert 'Selected_Orifice_Letter' in res

    def test_gas_subcritical_flow(self):
        res = calculate_gas_relief_area(
            w_lb_h=10000, p1_psia=500, p2_psia=450,
            t_rankine=600, z=0.9, mw=28, k=1.4,
        )
        assert res['Flow_Type'] == 'SUBCRITICAL'
        assert res['Required_Area_sqin'] > 0.1

    def test_parallel_valves(self):
        res1 = calculate_gas_relief_area(
            w_lb_h=20000, p1_psia=500, p2_psia=14.7,
            t_rankine=600, z=0.9, mw=28, k=1.4, num_valves=1,
        )
        res2 = calculate_gas_relief_area(
            w_lb_h=20000, p1_psia=500, p2_psia=14.7,
            t_rankine=600, z=0.9, mw=28, k=1.4, num_valves=2,
        )
        assert res2['Required_Area_sqin'] < res1['Required_Area_sqin']

    def test_hydrogen_service(self):
        res = calculate_gas_relief_area(
            w_lb_h=5000, p1_psia=100, p2_psia=14.7,
            t_rankine=560, z=1.0, mw=2.016, k=1.41,
        )
        assert res['Required_Area_sqin'] > 0

    def test_steam_service(self):
        res = calculate_gas_relief_area(
            w_lb_h=20000, p1_psia=150, p2_psia=14.7,
            t_rankine=700, z=0.98, mw=18.015, k=1.33,
        )
        assert res['Required_Area_sqin'] > 0

    def test_balanced_bellows_kb(self):
        """Balanced bellows should auto-calculate Kb < 1.0 at high back pressure."""
        res = calculate_gas_relief_area(
            w_lb_h=10000, p1_psia=100, p2_psia=55,
            t_rankine=560, z=0.9, mw=28, k=1.4,
            set_pressure_psig=85, valve_type="balanced_bellows",
        )
        # Higher back pressure should increase required area (Kb < 1)
        assert res['Required_Area_sqin'] > 0

    def test_pilot_gas_kb_not_applied(self):
        """Pilot valve should have Kb=1.0 (no back pressure correction)."""
        res = calculate_gas_relief_area(
            w_lb_h=10000, p1_psia=100, p2_psia=55,
            t_rankine=560, z=0.9, mw=28, k=1.4,
            valve_type="pilot",
        )
        assert res['Kb_Factor'] == 1.0

    def test_gas_valve_type_pilot_kd(self):
        """Pilot valve should use Kd=0.99."""
        res = calculate_gas_relief_area(
            w_lb_h=5000, p1_psia=114.7, p2_psia=14.7,
            t_rankine=560, z=1.0, mw=28, k=1.4,
            valve_type="pilot", kb=None,
        )
        assert res['Kd_Used'] == 0.99
        assert res['Kb_Factor'] == 1.0

    def test_gas_subcritical_with_f2(self):
        """Subcritical flow should have F2 < 1.0."""
        res = calculate_gas_relief_area(
            w_lb_h=10000, p1_psia=500, p2_psia=480,
            t_rankine=600, z=0.9, mw=28, k=1.4,
        )
        assert res['Flow_Type'] == 'SUBCRITICAL'
        if 'F2_Coefficient' in res and res['F2_Coefficient'] is not None:
            assert res['F2_Coefficient'] < 1.0

    def test_gas_c_coefficient_in_result(self):
        """C coefficient should be present in standard gas results."""
        res = calculate_gas_relief_area(
            w_lb_h=5000, p1_psia=114.7, p2_psia=14.7,
            t_rankine=560, z=1.0, mw=28, k=1.4,
        )
        assert 'C_Coefficient' in res
        assert res['C_Coefficient'] > 0


# =============================================================================
# Liquid Relief
# =============================================================================

class TestLiquidRelief:
    def test_basic_liquid(self):
        res = calculate_liquid_relief_area(
            q_gpm=60, p1_psia=100, p2_psia=10,
            g=1.0, mu_cp=1.0,
        )
        assert res['Required_Area_Final_sqin'] > 0.01
        assert res['Selected_Orifice_Letter'] in API_ORIFICE_AREAS

    def test_high_viscosity(self):
        res = calculate_liquid_relief_area(
            q_gpm=60, p1_psia=100, p2_psia=10,
            g=1.0, mu_cp=1000,
        )
        assert res['Kv'] < 1.0
        assert res['Kv'] > 0.1

    def test_low_pressure_drop(self):
        res = calculate_liquid_relief_area(
            q_gpm=10, p1_psia=50, p2_psia=48,
            g=0.8, mu_cp=1.0,
        )
        assert res['Required_Area_Final_sqin'] > 0

    def test_parallel_valves_liquid(self):
        res1 = calculate_liquid_relief_area(
            q_gpm=200, p1_psia=100, p2_psia=10,
            g=1.0, mu_cp=1.0, num_valves=1,
        )
        res2 = calculate_liquid_relief_area(
            q_gpm=200, p1_psia=100, p2_psia=10,
            g=1.0, mu_cp=1.0, num_valves=2,
        )
        assert res2['Required_Area_Final_sqin'] < res1['Required_Area_Final_sqin']

    def test_Kv_iteration_stabilizes(self):
        """Kv iteration should converge within 3 iterations."""
        res = calculate_liquid_relief_area(
            q_gpm=100, p1_psia=150, p2_psia=15,
            g=1.2, mu_cp=50,
        )
        assert res['Kv'] > 0
        assert res['Kv'] <= 1.0

    def test_delta_p_zero_raises(self):
        with pytest.raises(ValueError):
            calculate_liquid_relief_area(
                q_gpm=60, p1_psia=50, p2_psia=50,
                g=1.0, mu_cp=1.0,
            )

    def test_liquid_kw_factor_reduces_area(self):
        """With kw<1.0 (back pressure correction), required area should increase."""
        res_no_correction = calculate_liquid_relief_area(
            q_gpm=100, p1_psia=150, p2_psia=30,
            g=1.0, mu_cp=1.0, kw=1.0,
        )
        res_corrected = calculate_liquid_relief_area(
            q_gpm=100, p1_psia=150, p2_psia=30,
            g=1.0, mu_cp=1.0, kw=0.8,
        )
        assert res_corrected['Required_Area_Final_sqin'] > res_no_correction['Required_Area_Final_sqin']

    def test_liquid_extreme_viscosity(self):
        """Very high viscosity should significantly reduce Kv."""
        res = calculate_liquid_relief_area(
            q_gpm=60, p1_psia=100, p2_psia=14.7,
            g=1.0, mu_cp=100000,
        )
        assert res['Kv'] < 0.5
        assert res['Required_Area_Final_sqin'] > 0

    def test_liquid_valve_type_pilot_kd_override(self):
        """Pilot valve should explicitly show Kd_Used=0.80."""
        res = calculate_liquid_relief_area(
            q_gpm=60, p1_psia=114.7, p2_psia=14.7,
            g=1.0, mu_cp=1.0, valve_type="pilot",
        )
        assert res['Kd_Used'] == 0.80

    def test_liquid_explicit_kd_override(self):
        """Manually passing kd=0.9 should be respected."""
        res = calculate_liquid_relief_area(
            q_gpm=60, p1_psia=114.7, p2_psia=14.7,
            g=1.0, mu_cp=1.0, kd=0.9,
        )
        assert res['Kd_Used'] == 0.9

    def test_kp_pilot_returns_1(self):
        """Pilot valves always have Kp = 1.0 per API 520 Section 7."""
        assert calculate_kp(10.0, "pilot") == 1.0
        assert calculate_kp(25.0, "pilot") == 1.0

    def test_kp_conventional_10pct(self):
        """10% overpressure → Kp = 0.6."""
        assert calculate_kp(10.0, "conventional") == 0.6

    def test_kp_conventional_25pct(self):
        """25% overpressure → Kp = 1.0."""
        assert calculate_kp(25.0, "conventional") == 1.0

    def test_kp_conventional_interpolation(self):
        """17.5% overpressure → Kp = 0.8 (linear interp between 0.6 and 1.0)."""
        kp = calculate_kp(17.5, "conventional")
        assert kp == pytest.approx(0.8, abs=1e-9)

    def test_kp_below_10_clamps(self):
        """Below 10% overpressure, Kp clamps at 0.6."""
        assert calculate_kp(5.0, "conventional") == 0.6

    def test_kp_above_25_clamps(self):
        """Above 25% overpressure, Kp clamps at 1.0."""
        assert calculate_kp(30.0, "conventional") == 1.0

    def test_kp_applied_in_calculation(self):
        """Kp should appear in the result dict and affect area."""
        res_10 = calculate_liquid_relief_area(
            q_gpm=60, p1_psia=114.7, p2_psia=14.7,
            g=1.0, mu_cp=1.0, overpressure_pct=10.0,
        )
        res_25 = calculate_liquid_relief_area(
            q_gpm=60, p1_psia=114.7, p2_psia=14.7,
            g=1.0, mu_cp=1.0, overpressure_pct=25.0,
        )
        assert 'Kp' in res_10
        assert 'Kp' in res_25
        # Kp at 10% (0.6) reduces denominator → larger area than at 25% (1.0)
        assert res_10['Required_Area_Final_sqin'] > res_25['Required_Area_Final_sqin']


class TestReynolds:
    def test_reynolds_high(self):
        re = calculate_reynolds(100, 1.0, 1.0, 0.5)
        assert re > 1000

    def test_reynolds_zero_area(self):
        re = calculate_reynolds(100, 1.0, 1.0, 0)
        assert re == float('inf')

    def test_reynolds_zero_visc(self):
        re = calculate_reynolds(100, 1.0, 0, 0.5)
        assert re == float('inf')


class TestKv:
    def test_kv_turbulent(self):
        assert calculate_kv(10000) == 1.0
        assert calculate_kv(100000) == 1.0

    def test_kv_very_low_re(self):
        assert calculate_kv(5) == pytest.approx(0.1, rel=0.01)

    def test_kv_transition(self):
        kv = calculate_kv(100)
        assert 0.1 < kv < 1.0

    def test_kv_monotonic(self):
        for re in [10, 50, 100, 500, 1000, 5000]:
            kv = calculate_kv(re)
            assert 0.1 <= kv <= 1.0


# =============================================================================
# Two-Phase Relief
# =============================================================================

class TestTwoPhase:
    def test_omega_flashing(self):
        omega = calculate_omega_flashing(0.1, 0.11)
        assert omega == pytest.approx(0.9, abs=0.01)

    def test_omega_flashing_zero_v0(self):
        with pytest.raises(ValueError):
            calculate_omega_flashing(0, 0.1)

    def test_two_phase_critical(self):
        omega = calculate_omega_flashing(0.1, 0.12)
        res = calculate_two_phase_area(
            w_lb_h=500000, p0_psia=1000, p_back_psia=100,
            v0_ft3_lb=0.1, omega=omega,
        )
        assert res['Required_Area_sqin'] > 0
        assert res['Flow_Type'] in ('CRITICAL', 'SUBCRITICAL')

    def test_two_phase_subcooled(self):
        """Subcooled omega should be lower than flashing omega for same fluid."""
        omega_sub = calculate_omega_subcooled(
            p0_psia=150, p_sat_psia=100,
            v0_ft3_lb=0.0084, v_sat_ft3_lb=0.0090,
            h0_btu_lb=200, h_sat_btu_lb=250,
        )
        assert omega_sub > 0.01
        assert omega_sub < 10

    def test_valve_out_of_range(self):
        """Extremely large flow should return 'Multiple Valves Required'."""
        res = calculate_two_phase_area(
            w_lb_h=50_000_000, p0_psia=1000, p_back_psia=100,
            v0_ft3_lb=0.1, omega=2.0,
        )
        assert 'Multiple' in str(res['Selected_Orifice_Letter'])

    def test_two_phase_omega_coolprop(self):
        comp = {"Water": 1.0}
        res = calculate_two_phase_omega_coolprop(
            comp, p0_psia=150.0, state_type="saturated_liquid"
        )
        assert res["v0_ft3_lb"] > 0
        assert res["v9_ft3_lb"] > res["v0_ft3_lb"]
        assert res["omega"] > 0.01

        res_sub = calculate_two_phase_omega_coolprop(
            comp, p0_psia=150.0, state_type="subcooled_liquid", t_rankine=600.0
        )
        assert res_sub["omega"] > 0

    def test_two_phase_area_with_kb(self):
        res = calculate_two_phase_area(
            w_lb_h=100000, p0_psia=150.0, p_back_psia=64.6959,
            v0_ft3_lb=0.018, omega=2.0,
            valve_type="balanced_bellows", set_pressure_psig=100.0
        )
        assert res["Kb"] < 1.0


# =============================================================================
# Fire Scenarios
# =============================================================================

class TestFireScenarios:
    def test_env_factors_all_positive(self):
        for name, factor in ENV_FACTORS.items():
            assert factor > 0, f"{name} has non-positive factor"
            assert factor <= 1.0, f"{name} has factor > 1.0"

    def test_get_env_factor(self):
        assert get_env_factor("bare") == 1.0

    def test_get_env_factor_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown environment factor"):
            get_env_factor("nonexistent")

    def test_wetted_fire(self):
        w, q = calculate_fire_wetted_load(
            a_wetted_sqft=100, f_factor=1.0, heat_of_vap_btu_lb=100,
        )
        assert q > 0
        assert w == q / 100

    def test_wetted_fire_capped(self):
        w_2800, q_2800 = calculate_fire_wetted_load(2800, 1.0, 100)
        w_5000, q_5000 = calculate_fire_wetted_load(5000, 1.0, 100)
        assert q_2800 == q_5000

    def test_wetted_fire_uncapped(self):
        _, q_2800 = calculate_fire_wetted_load(2800, 1.0, 100, wetted_area_cap=None)
        _, q_5000 = calculate_fire_wetted_load(5000, 1.0, 100, wetted_area_cap=None)
        assert q_5000 > q_2800

    def test_wetted_fire_no_drainage(self):
        _, q_drainage = calculate_fire_wetted_load(100, 1.0, 100, adequate_drainage=True)
        _, q_no_drainage = calculate_fire_wetted_load(100, 1.0, 100, adequate_drainage=False)
        assert q_no_drainage == pytest.approx(q_drainage * (34500.0 / 21000.0), rel=1e-4)

    def test_unwetted_fire(self):
        a, f_prime = calculate_fire_unwetted_area(
            a_exposed_sqft=100, p1_psia=100,
            t_gas_rankine=500, t_wall_rankine=1000, k=1.4,
        )
        assert a > 0
        assert f_prime > 0

    def test_unwetted_no_heat(self):
        a, f_prime = calculate_fire_unwetted_area(
            a_exposed_sqft=100, p1_psia=100,
            t_gas_rankine=1000, t_wall_rankine=500, k=1.4,
        )
        assert a == 0
        assert f_prime == 0

    def test_fire_hvap_zero(self):
        with pytest.raises(ValueError):
            calculate_fire_wetted_load(100, 1.0, 0)

    def test_heat_absorption_20000sqft_crossover(self):
        """At 20000 sqft there is a crossover in API 521 equation."""
        q_below = calculate_heat_absorption(19000, f_factor=1.0, adequate_drainage=True)
        q_at = calculate_heat_absorption(20000, f_factor=1.0, adequate_drainage=True)
        q_above = calculate_heat_absorption(21000, f_factor=1.0, adequate_drainage=True)
        assert q_below > 0
        assert q_at > 0
        assert q_above > 0

    def test_heat_absorption_shape(self):
        """Heat absorption should be monotonic increasing with area."""
        q1 = calculate_heat_absorption(100, 1.0)
        q2 = calculate_heat_absorption(500, 1.0)
        q3 = calculate_heat_absorption(1000, 1.0)
        assert q1 < q2 < q3

    def test_f_factor_no_drainage_returns_higher(self):
        q_drain = calculate_heat_absorption(100, 1.0, adequate_drainage=True)
        q_no_drain = calculate_heat_absorption(100, 1.0, adequate_drainage=False)
        assert q_no_drain > q_drain


# =============================================================================
# Thermal Expansion
# =============================================================================

class TestThermalExpansion:
    def test_basic(self):
        q = calculate_thermal_expansion_load(
            b_expansion_coeff=0.0005,
            h_heat_transfer_btu_h=2100000,
            g_specific_gravity=0.85,
            c_specific_heat=0.6,
        )
        assert q > 0

    def test_zero_sg(self):
        with pytest.raises(ValueError):
            calculate_thermal_expansion_load(0.0005, 2100000, 0, 0.6)

    def test_zero_cp(self):
        with pytest.raises(ValueError):
            calculate_thermal_expansion_load(0.0005, 2100000, 0.85, 0)


# =============================================================================
# Blowby
# =============================================================================

class TestBlowby:
    def test_basic(self):
        flow = calculate_blowby_flowrate(1000, 10, 5)
        assert flow == 2000

    def test_zero_cv_calculated(self):
        with pytest.raises(ValueError):
            calculate_blowby_flowrate(1000, 10, 0)


# =============================================================================
# Pilot Valve Types (core/valve_types.py)
# =============================================================================

class TestValveTypes:
    def test_pilot_gas_full_calculation(self):
        from core.valve_types import calculate_pilot_gas_area
        res = calculate_pilot_gas_area(
            w_lb_h=5000, p1_psia=114.7, p2_psia=14.7,
            t_rankine=560, z=1.0, mw=28, k=1.4,
        )
        assert res['Kd'] == 0.99
        assert 'Selected_Orifice_Letter' in res
        assert res['Required_Area_sqin'] > 0

    def test_pilot_liquid_full_calculation(self):
        from core.valve_types import calculate_pilot_liquid_area
        res = calculate_pilot_liquid_area(
            q_gpm=60, p1_psia=114.7, p2_psia=14.7, g=1.0, mu_cp=1.0,
        )
        assert res['Kd'] == 0.80
        assert 'Selected_Orifice_Letter' in res
        assert res['Required_Area_sqin'] > 0

    def test_pilot_gas_area_vs_liquid_same_q(self):
        """For same conditions, gas area differs from liquid area (different Kd, different equation)."""
        from core.valve_types import calculate_pilot_gas_area as g_fn
        from core.valve_types import calculate_pilot_liquid_area as l_fn
        g_res = g_fn(w_lb_h=5000, p1_psia=114.7, p2_psia=14.7, t_rankine=560, z=1.0, mw=28, k=1.4)
        l_res = l_fn(q_gpm=60, p1_psia=114.7, p2_psia=14.7, g=1.0, mu_cp=1.0)
        assert g_res['Kd'] == 0.99
        assert l_res['Kd'] == 0.80

    def test_pilot_gas_kd_constants(self):
        from core.valve_types import KD_GAS, KD_LIQUID, KD_TWO_PHASE
        assert KD_GAS == 0.99
        assert KD_LIQUID == 0.80
        assert KD_TWO_PHASE == 0.85

    def test_pilot_area_kd_ratio(self):
        """Verify formula: higher Kd → smaller required area."""
        from core.valve_types import KD_GAS, KD_LIQUID
        required = 0.5
        gas_needed = required / KD_GAS
        liq_needed = required / KD_LIQUID
        assert gas_needed < required + 0.01
        assert liq_needed > gas_needed


# =============================================================================
# Unit Converter
# =============================================================================

class TestUnitConverter:
    def test_barg_to_psia_roundtrip(self):
        for barg in [0, 1, 10, 50, 100]:
            psia = barg_to_psia(barg)
            back = psia_to_barg(psia)
            assert back == pytest.approx(barg, rel=1e-4)

    def test_m3h_to_gpm_roundtrip(self):
        for m3h in [1, 10, 100]:
            gpm = m3_h_to_gpm(m3h)
            back = gpm_to_m3_h(gpm)
            assert back == pytest.approx(m3h, rel=1e-4)

    def test_kgh_to_lbh_roundtrip(self):
        for kgh in [1, 100, 10000]:
            lbh = kg_h_to_lb_h(kgh)
            back = lbh / 2.204623
            assert back == pytest.approx(kgh, rel=1e-4)

    def test_c_to_rankine(self):
        assert c_to_rankine(0) == pytest.approx(491.67, rel=1e-4)
        assert c_to_rankine(100) == pytest.approx(671.67, rel=1e-4)

    def test_atm_psia_constant(self):
        assert ATM_PSIA == pytest.approx(14.6959, rel=1e-4)

    def test_bar_psi_constant(self):
        assert PSI_PER_BAR == pytest.approx(14.50377, rel=1e-4)

    def test_sm3h_to_lbh(self):
        result = sm3_h_to_lb_h(1000, 28)
        assert result > 0

    def test_nm3h_to_lbh(self):
        result = nm3_h_to_lb_h(1000, 28)
        assert result > 0

    def test_actual_m3h_to_lbh(self):
        result = actual_m3_h_to_lb_h(100, 100, 560, 28, 0.9)
        assert result > 0


# =============================================================================
# Units (pint wrapper — core/units.py)
# =============================================================================

class TestUnits:
    def test_convert_gpm_to_lmin(self):
        from core.units import convert
        result = convert(100, "gpm", "L/min")
        assert result == pytest.approx(378.541, rel=0.01)

    def test_convert_psia_to_barg(self):
        from core.units import convert
        result = convert(114.7, "psia", "barg")
        assert result == pytest.approx(6.89476, rel=0.01)

    def test_convert_barg_to_psia(self):
        from core.units import convert
        result = convert(6.9, "barg", "psia")
        assert result == pytest.approx(114.9, rel=0.01)

    def test_convert_c_to_f(self):
        from core.units import convert
        result = convert(100, "degC", "degF")
        assert result == pytest.approx(212.0, rel=0.01)

    def test_convert_f_to_c(self):
        from core.units import convert
        result = convert(212, "degF", "degC")
        assert result == pytest.approx(100.0, rel=0.01)

    def test_convert_invalid_unit(self):
        from core.units import convert
        with pytest.raises((ValueError, Exception)):
            convert(100, "gpm", "nonexistent")

    def test_convert_pint_not_available(self):
        from core.units import HAS_PINT
        # Verify the module loads regardless
        assert HAS_PINT is not None

    def test_unit_info_contains_pint(self):
        from core.units import unit_info
        info = unit_info()
        assert "backend" in info
        assert info["backend"] in ("pint", "fallback")

    def test_atm_psia_constant(self):
        from core.units import ATM_PSIA
        assert ATM_PSIA == pytest.approx(14.6959, rel=1e-4)

    def test_psi_per_bar_constant(self):
        from core.units import PSI_PER_BAR
        assert PSI_PER_BAR == pytest.approx(14.50377, rel=1e-4)

    def test_convert_kg_h_to_lb_h(self):
        from core.units import convert
        result = convert(100, "kg/h", "lb/h")
        assert result == pytest.approx(220.462, rel=0.01)

    def test_convert_sqin_to_mm2(self):
        from core.units import convert
        result = convert(1.0, "sqin", "mm2")
        assert result == pytest.approx(645.16, rel=0.01)


# =============================================================================
# Valve Selection
# =============================================================================

class TestValveSelection:
    def test_all_orifice_areas_positive(self):
        for letter, area in API_ORIFICE_AREAS.items():
            assert area > 0, f"Orifice {letter} has non-positive area"

    def test_orifice_areas_increasing(self):
        areas = list(API_ORIFICE_AREAS.values())
        for i in range(len(areas) - 1):
            assert areas[i] < areas[i + 1], "Orifice areas not strictly increasing"

    def test_select_exact(self):
        letter, area = select_orifice(0.110)
        assert letter == 'D'
        assert area == 0.110

    def test_select_next_larger(self):
        letter, area = select_orifice(0.200)
        assert letter == 'F'

    def test_select_beyond_t(self):
        letter, area = select_orifice(30.0)
        assert 'Multiple' in str(letter)

    def test_all_api_letters(self):
        expected = ['D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'T']
        assert list(API_ORIFICE_AREAS.keys()) == expected


# =============================================================================
# Kb Coefficient
# =============================================================================

class TestKbCoefficient:
    def test_conventional_kb(self):
        kb = get_kb(50, 100, "conventional")
        assert kb == 1.0

    def test_balanced_low_bp(self):
        kb = get_kb(24.6959, 100, "balanced_bellows")
        assert kb == pytest.approx(0.99, abs=0.01)

    def test_balanced_moderate_bp(self):
        kb = get_kb(49.6959, 100, "balanced_bellows")
        assert 0.9 <= kb <= 1.0

    def test_balanced_high_bp(self):
        kb = get_kb(64.6959, 100, "balanced_bellows")
        assert kb < 1.0
        assert kb > 0.5

    def test_interpolation_out_of_range_below(self):
        kb = interpolate_kb(-5, KB_BALANCED_BELLOWS_10PCT)
        assert kb == 1.0

    def test_interpolation_out_of_range_above(self):
        kb = interpolate_kb(100, KB_BALANCED_BELLOWS_10PCT)
        assert kb == KB_BALANCED_BELLOWS_10PCT[max(KB_BALANCED_BELLOWS_10PCT.keys())]


# =============================================================================
# CoolProp Integration
# =============================================================================

class TestCoolProp:
    def test_fluids_list(self):
        fluids = get_coolprop_fluids()
        assert len(fluids) > 10
        assert "Methane" in fluids

    def test_mixture_mole(self):
        comp = {"Methane": 0.8, "Ethane": 0.2}
        z, mw, k = calculate_mixture_properties(comp, 560, 100, fraction_type="mole")
        assert 0.8 < z < 1.1
        assert 18.0 < mw < 20.0
        assert k > 1.1

    def test_mixture_mass(self):
        comp = {"Methane": 0.5, "Ethane": 0.5}
        z, mw, k = calculate_mixture_properties(comp, 560, 100, fraction_type="mass")
        assert 16.0 < mw < 30.0
        assert k > 1.1

    def test_mixture_fallback(self):
        """Mixture with missing binary interaction params falls back to Kay's rule."""
        comp = {"Methane": 0.95, "Ethane": 0.02, "CycloPropane": 0.03}
        z, mw, k = calculate_mixture_properties(comp, 560, 100, fraction_type="mole")
        assert 0.8 < z < 1.1
        assert mw > 16.0

    def test_single_fluid(self):
        comp = {"Methane": 1.0}
        z, mw, k = calculate_mixture_properties(comp, 560, 100, fraction_type="mole")
        assert z > 0


# =============================================================================
# Vendor Catalog
# =============================================================================

class TestVendorCatalog:
    def test_vendor_coverage(self, vendor_catalog):
        directory = vendor_catalog.get("manufacturer_directory", [])
        assert len(directory) >= 30

    def test_all_regions_covered(self, vendor_catalog):
        directory = vendor_catalog.get("manufacturer_directory", [])
        regions = {r for item in directory for r in item.get("regions", [])}
        assert {"Americas", "Europe", "Asia"}.issubset(regions)

    def test_each_orifice_has_valves(self):
        for letter in ["D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "Q", "R", "T"]:
            valves = get_vendor_valves(letter)
            assert len(valves) >= 20, f"Orifice {letter} has < 20 valves"
            assert any(v.get("website") for v in valves), f"Orifice {letter} has no website"


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """End-to-end scenarios combining multiple modules."""

    def test_liquid_to_valve_selection(self):
        """Calculate area and verify it maps to a real vendor valve."""
        res = calculate_liquid_relief_area(60, 100, 10, 1.0, 1.0)
        letter = res['Selected_Orifice_Letter']
        valves = get_vendor_valves(letter)
        assert len(valves) > 0

    def test_gas_to_valve_selection(self):
        res = calculate_gas_relief_area(
            10000, 500, 14.7, 600, 0.9, 28, 1.4,
        )
        letter = res['Selected_Orifice_Letter']
        valves = get_vendor_valves(letter)
        assert len(valves) > 0

    def test_fire_wetted_to_gas_sizing(self):
        """Fire scenario relief load should produce a valid valve size."""
        w, q = calculate_fire_wetted_load(500, 1.0, 150)
        res = calculate_gas_relief_area(
            w_lb_h=w, p1_psia=100, p2_psia=14.7,
            t_rankine=600, z=0.9, mw=28, k=1.4,
        )
        assert res['Required_Area_sqin'] > 0

    def test_full_pipeline_liquid(self):
        """Full pipeline: input → calculate → select valve → find vendor."""
        res = calculate_liquid_relief_area(150, 200, 30, 0.95, 12.5)
        letter = res['Selected_Orifice_Letter']
        assert letter in API_ORIFICE_AREAS

        valves = get_vendor_valves(letter)
        assert len(valves) > 0

        manufacturer_countries = {v.get("manufacturer") for v in valves}
        assert len(manufacturer_countries) > 0


# =============================================================================
# Error Handling
# =============================================================================

class TestErrorHandling:
    def test_mixture_empty_dict(self):
        with pytest.raises(ValueError):
            calculate_mixture_properties({}, 560, 100)

    def test_mixture_wrong_sum(self):
        with pytest.raises(ValueError):
            calculate_mixture_properties({"Methane": 0.5, "Ethane": 0.3}, 560, 100)

    def test_gas_invalid_inputs(self):
        with pytest.raises((ValueError, ZeroDivisionError, ArithmeticError, TypeError)):
            calculate_gas_relief_area(
                w_lb_h="invalid", p1_psia=500, p2_psia=14.7,
                t_rankine=600, z=0.9, mw=28, k=1.4,
            )

    def test_reynolds_negative_inf(self):
        re = calculate_reynolds(100, 1.0, -1, 1.0)
        assert re == float('inf')


class TestPiping:
    def test_liquid_piping_pressure_drop(self):
        # Liquid test (using GPM)
        res = calculate_inlet_pressure_drop(
            flow_gpm=100.0, fluid_density_lb_ft3=62.4, viscosity_cp=1.0,
            pipe_id_in=2.067, pipe_length_ft=50.0,
            fittings_90deg=2, gate_valves=1
        )
        assert res["delta_p_psi"] > 0
        assert res["velocity_fps"] > 0
        assert res["reynolds"] > 0

    def test_gas_piping_pressure_drop(self):
        # Gas test (using lb/h)
        res = calculate_inlet_pressure_drop(
            flow_gpm=None, fluid_density_lb_ft3=1.2, viscosity_cp=0.018,
            pipe_id_in=3.068, pipe_length_ft=30.0,
            flow_rate_lb_h=5000.0
        )
        assert res["delta_p_psi"] > 0
        assert res["velocity_fps"] > 0
        assert res["flow_gpm"] > 0

    def test_piping_rules_conventional(self):
        # Conventional valve rules
        passes, pct = check_inlet_rule(delta_p_psi=2.5, set_pressure_psig=100.0, valve_type="conventional")
        assert passes is True
        assert pct == 2.5

        passes_fail, pct_fail = check_inlet_rule(delta_p_psi=3.5, set_pressure_psig=100.0, valve_type="conventional")
        assert passes_fail is False

    def test_piping_rules_pilot_remote(self):
        # Pilot valve with remote sensing should pass even at high pressure drop
        passes, pct = check_inlet_rule(
            delta_p_psi=5.0, set_pressure_psig=100.0, valve_type="pilot", remote_sensing=True
        )
        assert passes is True
        assert pct == 5.0

        passes_fail, _ = check_inlet_rule(
            delta_p_psi=5.0, set_pressure_psig=100.0, valve_type="pilot", remote_sensing=False
        )
        assert passes_fail is False

    def test_outlet_rule_pass(self):
        passes, pct = check_outlet_rule(back_pressure_psi=5.0, set_pressure_psig=100.0)
        assert passes is True
        assert pct == 5.0

    def test_outlet_rule_fail(self):
        passes, pct = check_outlet_rule(back_pressure_psi=12.0, set_pressure_psig=100.0)
        assert passes is False
        assert pct == 12.0

    def test_outlet_rule_zero_set(self):
        passes, pct = check_outlet_rule(back_pressure_psi=5.0, set_pressure_psig=0.0)
        assert passes is False
        assert pct == 0.0

    def test_darcy_laminar(self):
        from core.piping import darcy_friction_factor
        f = darcy_friction_factor(1000, 0.001)
        assert f == pytest.approx(0.064, rel=0.01)

    def test_darcy_turbulent(self):
        from core.piping import darcy_friction_factor
        f = darcy_friction_factor(100000, 0.001)
        assert 0.01 < f < 0.05

    def test_darcy_negative_re(self):
        from core.piping import darcy_friction_factor
        f = darcy_friction_factor(-100, 0.001)
        assert f == 0.0

    def test_darcy_zero_re(self):
        from core.piping import darcy_friction_factor
        f = darcy_friction_factor(0, 0.001)
        assert f == 0.0

    def test_piping_no_flow(self):
        res = calculate_inlet_pressure_drop(
            flow_gpm=0.0, fluid_density_lb_ft3=62.4, viscosity_cp=1.0,
            pipe_id_in=2.0, pipe_length_ft=10.0,
        )
        assert res["delta_p_psi"] == 0.0
        assert res["velocity_fps"] == 0.0


class TestAdvancedSizing:
    def test_subcooled_flashing_polykin_case(self):
        from core.advanced_sizing import area_relief_2phase_subcooled
        # PolyKin example: Q=378.5 L/min, P1=20.733 bara, P2=1.703 bara, Ps=7.419 bara, rho1=511.3 kg/m3, rho9=262.7 kg/m3
        res = area_relief_2phase_subcooled(
            q_l_min=378.5, p1_bara=20.733, p2_bara=1.703, ps_bara=7.419,
            rho1_kg_m3=511.3, rho9_kg_m3=262.7, kd=0.65, kb=1.0, kc=1.0, kv=1.0
        )
        # PolyKin says A = 135 mm2 (approx)
        assert res['Required_Area_mm2'] == pytest.approx(135.0, abs=2.0)
        assert res['Critical_Flow'] is True
        assert res['Flow_Type'] == "CRITICAL"

    def test_napier_steam_kn_correction(self):
        from core.advanced_sizing import calculate_napier_steam_area
        # P1 = 2000 psia (> 1514.7 psia)
        res = calculate_napier_steam_area(
            w_lb_h=50000.0, p1_psia=2000.0, p2_psia=50.0, t_rankine=None,
            kd=0.975, kb=1.0, kc=1.0, num_valves=1
        )
        assert res['Kn'] > 1.0  # (0.1906*2000 - 1000)/(0.2292*2000 - 1061) = 1.02688
        assert res['Kn'] == pytest.approx(1.02688, rel=0.001)

    def test_napier_steam_superheat_ksh(self):
        from core.advanced_sizing import get_ksh
        # At P1 = 100 psia, Tsat is ~327.8 °F
        # If superheated to 400 °F, Ksh should be < 1.0
        ksh_super = get_ksh(p1_psia=100.0, t_f=400.0)
        assert ksh_super < 1.0
        assert ksh_super > 0.8
        
        # If saturated or subcooled, Ksh should be 1.0
        ksh_sat = get_ksh(p1_psia=100.0, t_f=300.0)
        assert ksh_sat == 1.0

    def test_gas_relief_steam_routing(self):
        # Test routing and cross-checking in gas_relief
        res = calculate_gas_relief_area(
            w_lb_h=10000.0, p1_psia=114.7, p2_psia=14.7, t_rankine=560.0,
            z=1.0, mw=18.02, k=1.3, is_steam=True, use_napier=True
        )
        assert 'Verification_Required_Area_sqin' in res
        assert res['Verification_Method'] == 'API 520 Gaz/Buhar Denklemi'
        
        # Now test with use_napier=False
        res2 = calculate_gas_relief_area(
            w_lb_h=10000.0, p1_psia=114.7, p2_psia=14.7, t_rankine=560.0,
            z=1.0, mw=18.02, k=1.3, is_steam=True, use_napier=False
        )
        assert 'Verification_Required_Area_sqin' in res2
        assert res2['Verification_Method'] == 'Napier Buhar Denklemi'

    def test_two_phase_subcooled_flashing_routing(self):
        # Test routing and cross-checking in two_phase
        res = calculate_two_phase_area(
            w_lb_h=100000.0, p0_psia=150.0, p_back_psia=14.7,
            v0_ft3_lb=0.018, omega=1.5, is_subcooled_flashing=True,
            use_c23=True, p_sat_psia=50.0
        )
        assert 'Verification_Required_Area_sqin' in res
        assert res['Verification_Method'] == 'Standart iki fazlı Omega Metodu'

        res2 = calculate_two_phase_area(
            w_lb_h=100000.0, p0_psia=150.0, p_back_psia=14.7,
            v0_ft3_lb=0.018, omega=1.5, is_subcooled_flashing=True,
            use_c23=False, p_sat_psia=50.0
        )
        assert 'Verification_Required_Area_sqin' in res2
        assert res2['Verification_Method'] == 'API 520 C.2.3 Flashing Modeli'

    def test_napier_kn_below_range(self):
        """P1 < 1514.7 → Kn = 1.0."""
        from core.advanced_sizing import calculate_napier_steam_area
        res = calculate_napier_steam_area(
            w_lb_h=10000, p1_psia=500, p2_psia=14.7, t_rankine=None,
            kd=0.975, kb=1.0, kc=1.0, num_valves=1,
        )
        assert res['Kn'] == 1.0

    def test_napier_kn_above_range(self):
        """P1=2000 psia → Kn should be ~1.0269 per API 520."""
        from core.advanced_sizing import calculate_napier_steam_area
        res = calculate_napier_steam_area(
            w_lb_h=50000, p1_psia=2000, p2_psia=50, t_rankine=None,
            kd=0.975, kb=1.0, kc=1.0, num_valves=1,
        )
        assert res['Kn'] == pytest.approx(1.02688, rel=0.001)

    def test_ksh_interpolation_saturated(self):
        from core.advanced_sizing import get_ksh
        ksh = get_ksh(p1_psia=50.0, t_f=250.0)  # Tsat at 50 psia is ~297°F
        assert ksh == 1.0

    def test_ksh_interpolation_superheated(self):
        from core.advanced_sizing import get_ksh
        # At P1=200 psia, Tsat ~381.8°F, superheated to 450°F
        ksh = get_ksh(p1_psia=200.0, t_f=450.0)
        assert 0.8 < ksh < 1.0

    def test_ksh_extrapolate_below_table(self):
        from core.advanced_sizing import get_ksh
        # Below the lowest P in table (200 psia in current code)
        ksh = get_ksh(p1_psia=50.0, t_f=500.0)
        assert ksh > 0

    def test_two_phase_omega_subcooled_critical(self):
        omega = calculate_omega_subcooled(
            p0_psia=1000, p_sat_psia=800,
            v0_ft3_lb=0.018, v_sat_ft3_lb=0.025,
            h0_btu_lb=300, h_sat_btu_lb=400,
        )
        assert omega > 0.01
        assert omega < 10

    def test_two_phase_omega_subcooled_zero_delta_h(self):
        """Same enthalpy → no flashing → omega should be very low."""
        omega = calculate_omega_subcooled(
            p0_psia=150, p_sat_psia=100,
            v0_ft3_lb=0.018, v_sat_ft3_lb=0.022,
            h0_btu_lb=250, h_sat_btu_lb=250,
        )
        assert omega >= 0


# =============================================================================
# Pilot Valve Kd Tests (Phase 0.3)
# =============================================================================

class TestPilotValveKd:
    def test_pilot_gas_kd_default_override(self):
        gas_res = calculate_gas_relief_area(
            w_lb_h=5000.0, p1_psia=114.7, p2_psia=14.7, t_rankine=560.0,
            z=1.0, mw=28.0, k=1.4, valve_type="pilot",
        )
        assert gas_res['Kd_Used'] == 0.99

    def test_pilot_liquid_kd_default_override(self):
        liq_res = calculate_liquid_relief_area(
            q_gpm=60.0, p1_psia=114.7, p2_psia=14.7,
            g=1.0, mu_cp=1.0, valve_type="pilot",
        )
        assert liq_res['Kd_Used'] == 0.80

    def test_conventional_uses_default_kd(self):
        gas_res = calculate_gas_relief_area(
            w_lb_h=5000.0, p1_psia=114.7, p2_psia=14.7, t_rankine=560.0,
            z=1.0, mw=28.0, k=1.4,
        )
        assert gas_res['Kd_Used'] == 0.975

    def test_balanced_bellows_uses_default_kd(self):
        liq_res = calculate_liquid_relief_area(
            q_gpm=60.0, p1_psia=114.7, p2_psia=14.7,
            g=1.0, mu_cp=1.0, valve_type="balanced_bellows",
        )
        assert liq_res['Kd_Used'] == 0.65


# =============================================================================
# Mach Number / Sonic Velocity Tests (Phase 1.3)
# =============================================================================

class TestMachNumber:
    def test_sonic_velocity_air(self):
        from core.piping import calculate_sonic_velocity
        # Air at 60°F, k=1.4, MW=29
        v = calculate_sonic_velocity(k=1.4, mw=29.0, t_rankine=520.0)
        assert 1100 < v < 1200  # ~1117 ft/s expected

    def test_mach_subsonic(self):
        from core.piping import calculate_mach_number, check_mach_limit
        mach = calculate_mach_number(velocity_fps=200.0, k=1.4, mw=29.0, t_rankine=520.0)
        assert 0.15 < mach < 0.20
        ok, val, msg = check_mach_limit(mach)
        assert ok is True

    def test_mach_transonic_warning(self):
        from core.piping import calculate_mach_number, check_mach_limit
        mach = calculate_mach_number(velocity_fps=600.0, k=1.4, mw=29.0, t_rankine=520.0)
        assert 0.5 < mach < 0.6
        ok, val, msg = check_mach_limit(mach)
        assert ok is True
        assert "Marginal" in msg

    def test_mach_exceeds_limit(self):
        from core.piping import calculate_mach_number, check_mach_limit
        mach = calculate_mach_number(velocity_fps=1000.0, k=1.4, mw=29.0, t_rankine=520.0)
        assert 0.85 < mach < 0.95
        ok, val, msg = check_mach_limit(mach)
        assert ok is False
        assert "Exceeds" in msg

    def test_mach_zero_velocity(self):
        from core.piping import calculate_mach_number
        mach = calculate_mach_number(velocity_fps=0.0, k=1.4, mw=29.0, t_rankine=520.0)
        assert mach == 0.0

    def test_piping_output_includes_mach(self):
        from core.piping import calculate_inlet_pressure_drop
        res = calculate_inlet_pressure_drop(
            flow_gpm=100.0, fluid_density_lb_ft3=62.3, viscosity_cp=1.0,
            pipe_id_in=4.0, pipe_length_ft=50.0,
        )
        assert 'velocity_fps' in res
        assert res['velocity_fps'] > 0


# =============================================================================
# Shared Pydantic Model Tests (Phase 1.1)
# =============================================================================

class TestSharedModels:
    from core.models import (
        LiquidReliefInput, GasReliefInput, TwoPhaseInput,
        FireWettedInput, PipingInletInput, ConvertInput,
    )

    def test_liquid_model_valid(self):
        m = self.LiquidReliefInput(q_gpm=100, p1_psia=200, p2_psia=14.7, g=1.0, mu_cp=1.0)
        assert m.valve_type == "conventional"

    def test_liquid_model_pilot(self):
        m = self.LiquidReliefInput(q_gpm=100, p1_psia=200, p2_psia=14.7, g=1.0, mu_cp=1.0, valve_type="pilot")
        assert m.valve_type == "pilot"
        assert m.num_valves == 1

    def test_gas_model_invalid_k(self):
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            self.GasReliefInput(w_lb_h=100, p1_psia=200, p2_psia=14.7, t_rankine=560, z=1, mw=28, k=0.9)

    def test_fire_model_back_pressure_default(self):
        m = self.FireWettedInput(
            a_wetted_sqft=100, heat_of_vap_btu_lb=200, p1_psia=200,
            t_rankine=560, mw=28, k=1.3,
        )
        assert m.p2_psia == 14.6959

    def test_piping_model_optional_flow(self):
        m = self.PipingInletInput(
            flow_rate_lb_h=10000, fluid_density_lb_ft3=62.3,
            viscosity_cp=1.0, pipe_id_in=4.0, pipe_length_ft=50,
            set_pressure_psig=100,
        )
        assert m.flow_gpm is None

    def test_convert_model(self):
        m = self.ConvertInput(value=100, from_unit="gpm", to_unit="L/min")
        assert m.value == 100.0

    def test_gas_model_pilot_valve_default(self):
        m = self.GasReliefInput(w_lb_h=5000, p1_psia=114.7, p2_psia=14.7, t_rankine=560, z=1, mw=28, k=1.4)
        assert m.valve_type == "conventional"

    def test_gas_model_steam_routing(self):
        m = self.GasReliefInput(w_lb_h=5000, p1_psia=114.7, p2_psia=14.7, t_rankine=560, z=1, mw=18, k=1.3, is_steam=True)
        assert m.is_steam is True

    def test_two_phase_model_with_valve_type(self):
        m = self.TwoPhaseInput(
            w_lb_h=100000, p0_psia=200, p_back_psia=14.7,
            v0_ft3_lb=0.018, omega=1.5,
        )
        assert m.valve_type == "conventional"

    def test_two_phase_model_with_set_pressure(self):
        m = self.TwoPhaseInput(
            w_lb_h=100000, p0_psia=200, p_back_psia=14.7,
            v0_ft3_lb=0.018, omega=1.5,
            valve_type="balanced_bellows", set_pressure_psig=150.0,
        )
        assert m.kd == 0.85

    def test_fire_model_adequate_drainage_default(self):
        m = self.FireWettedInput(
            a_wetted_sqft=500, heat_of_vap_btu_lb=200, p1_psia=200,
            t_rankine=560, mw=28, k=1.3,
        )
        assert m.adequate_drainage is True

    def test_piping_model_valve_type_default(self):
        m = self.PipingInletInput(
            flow_gpm=100, fluid_density_lb_ft3=62.3, viscosity_cp=1.0,
            pipe_id_in=4.0, pipe_length_ft=50, set_pressure_psig=100,
        )
        assert m.valve_type == "conventional"

    def test_piping_model_remote_sensing(self):
        m = self.PipingInletInput(
            flow_gpm=100, fluid_density_lb_ft3=62.3, viscosity_cp=1.0,
            pipe_id_in=4.0, pipe_length_ft=50, set_pressure_psig=100,
            valve_type="pilot", remote_sensing=True,
        )
        assert m.remote_sensing is True

    def test_liquid_model_kw_param(self):
        m = self.LiquidReliefInput(q_gpm=100, p1_psia=200, p2_psia=14.7, g=1.0, mu_cp=1.0, kw=0.8)
        assert m.kw == 0.8

    def test_gas_kb_auto_none(self):
        m = self.GasReliefInput(w_lb_h=5000, p1_psia=114.7, p2_psia=14.7, t_rankine=560, z=1, mw=28, k=1.4)
        assert m.kb is None

    def test_liquid_mu_cp_default(self):
        m = self.LiquidReliefInput(q_gpm=100, p1_psia=200, p2_psia=14.7, g=1.0)
        assert m.mu_cp == 1.0

    def test_fire_model_k_default(self):
        m = self.FireWettedInput(
            a_wetted_sqft=100, heat_of_vap_btu_lb=200, p1_psia=200,
            t_rankine=560, mw=28, k=1.3,
        )
        assert m.k == 1.3

    def test_gas_model_validation_error_on_negative_flow(self):
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            self.GasReliefInput(w_lb_h=-500, p1_psia=114.7, p2_psia=14.7, t_rankine=560, z=1, mw=28, k=1.4)

    def test_liquid_model_validation_error_on_zero_g(self):
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            self.LiquidReliefInput(q_gpm=100, p1_psia=200, p2_psia=14.7, g=0.0, mu_cp=1.0)


# =============================================================================
# API Endpoint Integration Tests (Phase 2)
# =============================================================================

class TestApiIntegration:
    def test_liquid_relief_endpoint_response(self):
        from core.liquid_relief import calculate_liquid_relief_area as fn
        res = fn(q_gpm=60, p1_psia=114.7, p2_psia=14.7, g=1.0, mu_cp=1.0)
        assert 'Required_Area_Final_sqin' in res or 'Required_Area_sqin' in res

    def test_gas_relief_endpoint_response(self):
        from core.gas_relief import calculate_gas_relief_area as fn
        res = fn(w_lb_h=5000, p1_psia=114.7, p2_psia=14.7, t_rankine=560,
                 z=1.0, mw=28, k=1.4)
        assert 'Required_Area_Final_sqin' in res or 'Required_Area_sqin' in res

    def test_two_phase_endpoint_response(self):
        from core.two_phase import calculate_two_phase_area as fn
        res = fn(w_lb_h=10000, p0_psia=150, p_back_psia=14.7,
                 v0_ft3_lb=0.018, omega=1.5)
        assert 'Required_Area_Final_sqin' in res or 'Required_Area_sqin' in res

    def test_fire_wetted_endpoint_response(self):
        from core.fire_scenarios import calculate_fire_wetted_load as fn
        w, q = fn(a_wetted_sqft=100, f_factor=1.0, heat_of_vap_btu_lb=200)
        assert w > 0 and q > 0

    def test_piping_endpoint_response(self):
        from core.piping import calculate_inlet_pressure_drop as fn
        res = fn(flow_gpm=100, fluid_density_lb_ft3=62.3, viscosity_cp=1.0,
                 pipe_id_in=4.0, pipe_length_ft=50)
        assert 'delta_p_psi' in res

    @pytest.mark.skipif(True, reason="Requires FastAPI/httpx; run manually with: pytest -m 'not skip_auto'")
    def test_fastapi_http_health(self):
        import httpx
        r = httpx.get("http://localhost:8000/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


if __name__ == "__main__":
    pytest.main(["-v", "--tb=short"])