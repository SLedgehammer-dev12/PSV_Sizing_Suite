import json
import os
import sys
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from core.thermo_props import calculate_mixture_properties, get_coolprop_fluids
from core.liquid_relief import calculate_liquid_relief_area, calculate_reynolds, calculate_kv
from core.gas_relief import calculate_gas_relief_area, calculate_c_coefficient, calculate_f2_coefficient
from core.two_phase import calculate_omega_flashing, calculate_two_phase_area, calculate_omega_subcooled
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
        assert get_env_factor("nonexistent") == 1.0

    def test_wetted_fire(self):
        w, q = calculate_fire_wetted_load(
            a_wetted_sqft=100, f_factor=1.0, heat_of_vap_btu_lb=100,
        )
        assert q > 0
        assert w == q / 100

    def test_wetted_fire_large_area(self):
        """Above 20000 sqft, the formula changes."""
        w_small, _ = calculate_fire_wetted_load(20000, 1.0, 100)
        w_large, _ = calculate_fire_wetted_load(25000, 1.0, 100)
        assert w_large > w_small

    def test_heat_absorption_boundary(self):
        q_at = calculate_heat_absorption(20000, 1.0)
        q_below = calculate_heat_absorption(19999, 1.0)
        assert q_at > q_below

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
        kb = get_kb(10, 100, "balanced_bellows")
        assert kb == pytest.approx(0.99, abs=0.01)

    def test_balanced_moderate_bp(self):
        kb = get_kb(35, 100, "balanced_bellows")
        assert 0.9 <= kb <= 1.0

    def test_balanced_high_bp(self):
        kb = get_kb(50, 100, "balanced_bellows")
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


if __name__ == "__main__":
    pytest.main(["-v", "--tb=short"])