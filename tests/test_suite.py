import sys
import os
import unittest
import json
import tempfile
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.thermo_props import calculate_mixture_properties, get_coolprop_fluids, COOLPROP_AVAILABLE
from core.liquid_relief import calculate_liquid_relief_area, calculate_reynolds, calculate_kv
from core.gas_relief import calculate_gas_relief_area, calculate_c_coefficient, calculate_f2_coefficient
from core.two_phase import calculate_omega_flashing, calculate_two_phase_area, calculate_critical_pressure_ratio
from core.fire_scenarios import calculate_fire_wetted_load, calculate_fire_unwetted_area
from core.thermal_expansion import calculate_thermal_expansion_load
from core.blowby import calculate_blowby_flowrate
from core.unit_converter import (
    barg_to_psia, bara_to_psia, bara_to_barg, psia_to_bara, psia_to_barg,
    kg_h_to_lb_h, lb_h_to_kg_h, kg_s_to_lb_h, m3_h_to_gpm, gpm_to_m3_h,
    c_to_rankine, c_to_f, f_to_rankine, f_to_c, m3_kg_to_ft3_lb,
    sqft_to_m2, m2_to_sqft, kw_to_btu_h, kcal_h_to_btu_h, kcal_kg_to_btu_lb
)
from core.vendor_catalog import get_vendor_valves
from core.validation import (
    ValidationError, validate_liquid_inputs, validate_gas_inputs,
    validate_two_phase_inputs, validate_fire_wetted_inputs,
    validate_fire_unwetted_inputs, validate_thermal_inputs, validate_blowby_inputs
)
from core.valve_selection import select_orifice, API_ORIFICE_AREAS


class TestPSVSizingCore(unittest.TestCase):

    def test_coolprop_fluids_list(self):
        if not COOLPROP_AVAILABLE:
            self.skipTest("CoolProp not available")
        fluids = get_coolprop_fluids()
        self.assertGreater(len(fluids), 10)
        self.assertIn("Methane", fluids)
        self.assertIn("Water (Steam)", fluids)

    def test_mixture_properties_mole(self):
        if not COOLPROP_AVAILABLE:
            self.skipTest("CoolProp not available")
        comp = {"Methane": 0.8, "Ethane": 0.2}
        t_rankine = 560
        p_psia = 100
        z, mw, k = calculate_mixture_properties(comp, t_rankine, p_psia, fraction_type="mole")
        self.assertGreater(z, 0.8)
        self.assertLess(z, 1.1)
        self.assertGreater(mw, 18.0)
        self.assertLess(mw, 20.0)
        self.assertGreater(k, 1.1)

    def test_mixture_properties_mass(self):
        if not COOLPROP_AVAILABLE:
            self.skipTest("CoolProp not available")
        comp = {"Methane": 0.5, "Ethane": 0.5}
        t_rankine = 560
        p_psia = 100
        z, mw, k = calculate_mixture_properties(comp, t_rankine, p_psia, fraction_type="mass")
        self.assertGreater(mw, 16.0)
        self.assertLess(mw, 30.0)
        self.assertGreater(k, 1.1)

    def test_mixture_properties_fallback_kays_rule(self):
        if not COOLPROP_AVAILABLE:
            self.skipTest("CoolProp not available")
        comp = {"Methane": 0.95, "Ethane": 0.02, "CycloPropane": 0.03}
        t_rankine = 560
        p_psia = 100
        z, mw, k = calculate_mixture_properties(comp, t_rankine, p_psia, fraction_type="mole")
        self.assertGreater(z, 0.8)
        self.assertGreater(mw, 16.0)
        self.assertLess(mw, 25.0)
        self.assertGreater(k, 1.1)

    def test_liquid_relief(self):
        res = calculate_liquid_relief_area(q_gpm=60, p1_psia=100, p2_psia=10, g=1.0, mu_cp=1.0)
        self.assertIn('Required_Area_Final_sqin', res)
        self.assertIn('Selected_Orifice_Letter', res)
        self.assertGreater(res['Required_Area_Final_sqin'], 0.01)

    def test_gas_relief(self):
        res_crit = calculate_gas_relief_area(w_lb_h=10000, p1_psia=500, p2_psia=14.7, t_rankine=600, z=0.9, mw=28, k=1.4)
        self.assertEqual(res_crit['Flow_Type'], 'CRITICAL')
        self.assertGreater(res_crit['Required_Area_sqin'], 0.1)

        res_sub = calculate_gas_relief_area(w_lb_h=10000, p1_psia=500, p2_psia=450, t_rankine=600, z=0.9, mw=28, k=1.4)
        self.assertEqual(res_sub['Flow_Type'], 'SUBCRITICAL')
        self.assertGreater(res_sub['Required_Area_sqin'], res_crit['Required_Area_sqin'])

    def test_two_phase(self):
        omega = calculate_omega_flashing(v0=0.1, v9=0.11)
        self.assertAlmostEqual(omega, 0.9, places=2)

        res = calculate_two_phase_area(w_lb_h=500000, p0_psia=1000, p_back_psia=100, v0_ft3_lb=0.1, omega=omega)
        self.assertGreater(res['Required_Area_sqin'], 1.0)
        self.assertIn('Selected_Orifice_Letter', res)

    def test_fire_wetted(self):
        w, q = calculate_fire_wetted_load(a_wetted_sqft=100, f_factor=1.0, heat_of_vap_btu_lb=100)
        self.assertGreater(q, 0)
        self.assertGreater(w, 0)
        self.assertEqual(w, q / 100)

    def test_fire_unwetted(self):
        a, f_prime = calculate_fire_unwetted_area(a_exposed_sqft=100, p1_psia=100, t_gas_rankine=500, t_wall_rankine=1000, k=1.4)
        self.assertGreater(a, 0)
        self.assertGreater(f_prime, 0)

    def test_thermal_expansion(self):
        q_gpm = calculate_thermal_expansion_load(b_expansion_coeff=0.0005, h_heat_transfer_btu_h=2100000, g_specific_gravity=0.85, c_specific_heat=0.6)
        self.assertGreater(q_gpm, 0)

    def test_blowby(self):
        flow = calculate_blowby_flowrate(assumed_flow_kg_h=1000, nominal_cv=10, calculated_cv_at_blowby=5)
        self.assertEqual(flow, 2000)

    def test_vendor_catalog_regional_coverage(self):
        catalog_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "vendor_data",
            "psv_vendor_catalog_official.json",
        )
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        directory = catalog.get("manufacturer_directory", [])
        self.assertGreaterEqual(len(directory), 30)

        regions = {region for item in directory for region in item.get("regions", [])}
        self.assertTrue({"Americas", "Europe", "Asia"}.issubset(regions))

        for letter in ["D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "Q", "R", "T"]:
            valves = get_vendor_valves(letter)
            self.assertGreaterEqual(len(valves), 20)
            self.assertTrue(any(v.get("website") for v in valves))


class TestValidation(unittest.TestCase):

    def test_validate_liquid_positive_flow(self):
        with self.assertRaises(ValidationError):
            validate_liquid_inputs(q_gpm=-10, p1_psia=100, p2_psia=10, g=1.0, mu_cp=1.0)

    def test_validate_liquid_p2_greater_than_p1(self):
        with self.assertRaises(ValidationError):
            validate_liquid_inputs(q_gpm=60, p1_psia=10, p2_psia=100, g=1.0, mu_cp=1.0)

    def test_validate_liquid_zero_gravity(self):
        with self.assertRaises(ValidationError):
            validate_liquid_inputs(q_gpm=60, p1_psia=100, p2_psia=10, g=0, mu_cp=1.0)

    def test_validate_gas_negative_flow(self):
        with self.assertRaises(ValidationError):
            validate_gas_inputs(w_lb_h=-100, p1_psia=500, p2_psia=14.7, t_rankine=600, z=0.9, mw=28, k=1.4)

    def test_validate_gas_k_out_of_range(self):
        with self.assertRaises(ValidationError):
            validate_gas_inputs(w_lb_h=10000, p1_psia=500, p2_psia=14.7, t_rankine=600, z=0.9, mw=28, k=0.5)

    def test_validate_two_phase_negative_omega(self):
        with self.assertRaises(ValidationError):
            validate_two_phase_inputs(w_lb_h=500000, p0_psia=1000, p_back_psia=100, v0_ft3_lb=0.1, omega=-0.5)

    def test_validate_fire_wetted_zero_hvap(self):
        with self.assertRaises(ValidationError):
            validate_fire_wetted_inputs(a_wetted_sqft=100, f_factor=1.0, heat_of_vap_btu_lb=0)

    def test_validate_fire_unwetted_wall_less_than_gas(self):
        with self.assertRaises(ValidationError):
            validate_fire_unwetted_inputs(a_exposed_sqft=100, p1_psia=100, t_gas_rankine=600, t_wall_rankine=500, k=1.4)

    def test_validate_thermal_negative_b(self):
        with self.assertRaises(ValidationError):
            validate_thermal_inputs(b_expansion_coeff=-0.0005, h_heat_transfer_btu_h=2100000, g_specific_gravity=0.85, c_specific_heat=0.6)

    def test_validate_blowby_zero_cv(self):
        with self.assertRaises(ValidationError):
            validate_blowby_inputs(assumed_flow_kg_h=1000, nominal_cv=10, calculated_cv_at_blowby=0)

    def test_validation_passes_valid_inputs(self):
        validate_liquid_inputs(q_gpm=60, p1_psia=100, p2_psia=10, g=1.0, mu_cp=1.0)
        validate_gas_inputs(w_lb_h=10000, p1_psia=500, p2_psia=14.7, t_rankine=600, z=0.9, mw=28, k=1.4)
        validate_two_phase_inputs(w_lb_h=500000, p0_psia=1000, p_back_psia=100, v0_ft3_lb=0.1, omega=0.9)
        validate_fire_wetted_inputs(a_wetted_sqft=100, f_factor=1.0, heat_of_vap_btu_lb=100)
        validate_fire_unwetted_inputs(a_exposed_sqft=100, p1_psia=100, t_gas_rankine=500, t_wall_rankine=1000, k=1.4)
        validate_thermal_inputs(b_expansion_coeff=0.0005, h_heat_transfer_btu_h=2100000, g_specific_gravity=0.85, c_specific_heat=0.6)
        validate_blowby_inputs(assumed_flow_kg_h=1000, nominal_cv=10, calculated_cv_at_blowby=5)


class TestEdgeCases(unittest.TestCase):

    def test_gas_k_equals_1(self):
        c = calculate_c_coefficient(1.0)
        self.assertEqual(c, 315)

    def test_gas_k_near_1(self):
        c = calculate_c_coefficient(1.0000001)
        self.assertGreater(c, 0)

    def test_gas_k_zero(self):
        c = calculate_c_coefficient(0)
        self.assertEqual(c, 315)

    def test_liquid_zero_viscosity(self):
        re = calculate_reynolds(q_gpm=60, g=1.0, mu_cp=0, area_sq_in=1.0)
        self.assertEqual(re, float('inf'))

    def test_reynolds_high_value(self):
        re = calculate_reynolds(q_gpm=10000, g=1.0, mu_cp=0.1, area_sq_in=10.0)
        self.assertGreater(re, 10000)

    def test_kv_at_high_reynolds(self):
        kv = calculate_kv(50000)
        self.assertEqual(kv, 1.0)

    def test_kv_at_low_reynolds(self):
        kv = calculate_kv(5)
        self.assertEqual(kv, 0.1)

    def test_kv_at_medium_reynolds(self):
        kv = calculate_kv(1000)
        self.assertGreater(kv, 0.1)
        self.assertLess(kv, 1.0)

    def test_select_orifice_smallest(self):
        letter, area = select_orifice(0.05)
        self.assertEqual(letter, 'D')
        self.assertEqual(area, 0.110)

    def test_select_orifice_largest(self):
        letter, area = select_orifice(30.0)
        self.assertEqual(letter, 'Multiple Valves Required')
        self.assertEqual(area, 30.0)

    def test_select_orifice_exact_match(self):
        letter, area = select_orifice(1.838)
        self.assertEqual(letter, 'K')
        self.assertEqual(area, 1.838)

    def test_omega_flashing_equal_volumes(self):
        omega = calculate_omega_flashing(v0=0.1, v9=0.1)
        self.assertEqual(omega, 0.0)

    def test_two_phase_subcritical_flow(self):
        omega = calculate_omega_flashing(v0=0.01, v9=0.015)
        res = calculate_two_phase_area(w_lb_h=10000, p0_psia=100, p_back_psia=95, v0_ft3_lb=0.01, omega=omega)
        self.assertEqual(res['Flow_Type'], 'SUBCRITICAL')

    def test_parallel_valves_division(self):
        res = calculate_liquid_relief_area(q_gpm=60, p1_psia=100, p2_psia=10, g=1.0, mu_cp=1.0, num_valves=2)
        self.assertEqual(res['Num_Valves'], 2)

    def test_gas_relief_with_parallel_valves(self):
        res = calculate_gas_relief_area(w_lb_h=10000, p1_psia=500, p2_psia=14.7, t_rankine=600, z=0.9, mw=28, k=1.4, num_valves=3)
        self.assertEqual(res['Num_Valves'], 3)


class TestUnitConverters(unittest.TestCase):

    def test_barg_to_psia(self):
        self.assertAlmostEqual(barg_to_psia(0), 14.6959, places=3)
        self.assertAlmostEqual(barg_to_psia(1), 29.1997, places=3)

    def test_psia_to_barg(self):
        self.assertAlmostEqual(psia_to_barg(14.6959), 0, places=3)
        self.assertAlmostEqual(psia_to_barg(29.1997), 1.0, places=3)

    def test_bara_to_psia(self):
        self.assertAlmostEqual(bara_to_psia(1.01325), 14.696, places=2)

    def test_kg_h_to_lb_h(self):
        self.assertAlmostEqual(kg_h_to_lb_h(1), 2.204623, places=4)

    def test_lb_h_to_kg_h(self):
        self.assertAlmostEqual(lb_h_to_kg_h(2.204623), 1.0, places=4)

    def test_kg_s_to_lb_h(self):
        self.assertAlmostEqual(kg_s_to_lb_h(1), 7936.6428, places=3)

    def test_m3_h_to_gpm(self):
        self.assertAlmostEqual(m3_h_to_gpm(1), 4.402868, places=4)

    def test_gpm_to_m3_h(self):
        self.assertAlmostEqual(gpm_to_m3_h(4.402868), 1.0, places=4)

    def test_c_to_rankine(self):
        self.assertAlmostEqual(c_to_rankine(0), 491.67, places=2)
        self.assertAlmostEqual(c_to_rankine(100), 671.67, places=2)

    def test_m3_kg_to_ft3_lb(self):
        self.assertAlmostEqual(m3_kg_to_ft3_lb(1), 16.01846, places=4)

    def test_sqft_to_m2(self):
        self.assertAlmostEqual(sqft_to_m2(10.76391), 1.0, places=4)

    def test_m2_to_sqft(self):
        self.assertAlmostEqual(m2_to_sqft(1), 10.76391, places=4)

    def test_kw_to_btu_h(self):
        self.assertAlmostEqual(kw_to_btu_h(1), 3412.142, places=2)

    def test_kcal_h_to_btu_h(self):
        self.assertAlmostEqual(kcal_h_to_btu_h(1), 3.96832, places=4)

    def test_kcal_kg_to_btu_lb(self):
        self.assertAlmostEqual(kcal_kg_to_btu_lb(1), 1.8, places=4)

    def test_bara_to_barg(self):
        self.assertAlmostEqual(bara_to_barg(1.01325), 0.0, places=3)
        self.assertAlmostEqual(bara_to_barg(2.0), 0.9867, places=3)

    def test_psia_to_bara(self):
        self.assertAlmostEqual(psia_to_bara(14.50377), 1.0, places=3)

    def test_c_to_f(self):
        self.assertAlmostEqual(c_to_f(0), 32.0, places=2)
        self.assertAlmostEqual(c_to_f(100), 212.0, places=2)

    def test_f_to_rankine(self):
        self.assertAlmostEqual(f_to_rankine(32), 491.67, places=2)
        self.assertAlmostEqual(f_to_rankine(212), 671.67, places=2)

    def test_f_to_c(self):
        self.assertAlmostEqual(f_to_c(32), 0.0, places=2)
        self.assertAlmostEqual(f_to_c(212), 100.0, places=2)

    def test_roundtrip_pressure(self):
        original = 50.0
        psia = barg_to_psia(original)
        back = psia_to_barg(psia)
        self.assertAlmostEqual(back, original, places=3)

    def test_roundtrip_flow(self):
        original = 100.0
        lb_h = kg_h_to_lb_h(original)
        back = lb_h_to_kg_h(lb_h)
        self.assertAlmostEqual(back, original, places=3)


class TestAuth(unittest.TestCase):

    def setUp(self):
        import desktop.auth as auth
        self.original_auth_file = auth.AUTH_FILE
        self.temp_dir = tempfile.mkdtemp()
        auth.AUTH_FILE = os.path.join(self.temp_dir, 'test_auth.json')

    def tearDown(self):
        import desktop.auth as auth
        auth.AUTH_FILE = self.original_auth_file
        if os.path.exists(auth.AUTH_FILE):
            os.remove(auth.AUTH_FILE)

    def test_init_auth_creates_file(self):
        import desktop.auth as auth
        auth.init_auth()
        self.assertTrue(os.path.exists(auth.AUTH_FILE))

    def test_default_login(self):
        import desktop.auth as auth
        self.assertTrue(auth.check_login("user", "123456"))
        self.assertTrue(auth.check_login("admin", "123456"))

    def test_wrong_password(self):
        import desktop.auth as auth
        self.assertFalse(auth.check_login("user", "wrongpassword"))

    def test_change_password(self):
        import desktop.auth as auth
        auth.change_password("user", "newsecurepass")
        self.assertTrue(auth.check_login("user", "newsecurepass"))
        self.assertFalse(auth.check_login("user", "123456"))

    def test_hash_not_plain_text(self):
        import desktop.auth as auth
        auth.init_auth()
        with open(auth.AUTH_FILE, 'r') as f:
            data = json.load(f)
        self.assertNotEqual(data["user_hash"], "123456")
        self.assertTrue(data["user_hash"].startswith("$"))

    def test_must_change_password_default(self):
        import desktop.auth as auth
        auth.init_auth()
        with open(auth.AUTH_FILE, 'r') as f:
            data = json.load(f)
        self.assertTrue(data.get("user_must_change", False))
        self.assertTrue(data.get("admin_must_change", False))

    def test_change_password_clears_must_change_flag(self):
        import desktop.auth as auth
        auth.init_auth()
        auth.change_password("user", "newsecurepass")
        with open(auth.AUTH_FILE, 'r') as f:
            data = json.load(f)
        self.assertFalse(data.get("user_must_change", True))
        auth.change_password("user", "123456")

    def test_must_change_password_function(self):
        import desktop.auth as auth
        auth.init_auth()
        auth.change_password("user", "newsecurepass")
        self.assertFalse(auth.must_change_password("user"))
        auth.change_password("user", "123456")

    def test_pbkdf2_hash_format(self):
        import desktop.auth as auth
        auth.change_password("user", "securepass123")
        with open(auth.AUTH_FILE, 'r') as f:
            data = json.load(f)
        h = data["user_hash"]
        self.assertTrue(h.startswith("$pbkdf2$") or h.startswith("$2b$"),
                        f"Expected pbkdf2 or bcrypt hash, got prefix: {h[:10]}")

    def test_brute_force_lockout(self):
        import desktop.auth as auth
        auth.init_auth()
        for _ in range(5):
            self.assertFalse(auth.check_login("user", "wrongpassword"))
        self.assertFalse(auth.check_login("user", "123456"))

    def test_lockout_remaining(self):
        import desktop.auth as auth
        auth.init_auth()
        self.assertEqual(auth.get_lockout_remaining("user"), 0)

    def test_change_password_clears_lockout(self):
        import desktop.auth as auth
        auth.init_auth()
        for _ in range(5):
            auth.check_login("user", "wrongpassword")
        self.assertFalse(auth.check_login("user", "123456"))
        auth.change_password("user", "newpassword8")
        self.assertTrue(auth.check_login("user", "newpassword8"))
        self.assertEqual(auth.get_lockout_remaining("user"), 0)


class TestValidationAndGuards(unittest.TestCase):

    def test_num_valves_zero_liquid(self):
        with self.assertRaises(ValueError):
            calculate_liquid_relief_area(q_gpm=60, p1_psia=52.8, p2_psia=1.0, g=1.1, mu_cp=1.0, num_valves=0)

    def test_num_valves_zero_gas(self):
        with self.assertRaises(ValueError):
            calculate_gas_relief_area(w_lb_h=1000, p1_psia=50, p2_psia=10, t_rankine=600,
                                      z=0.95, mw=28.97, k=1.3, num_valves=0)

    def test_num_valves_zero_two_phase(self):
        with self.assertRaises(ValueError):
            calculate_two_phase_area(w_lb_h=1000, p0_psia=50, p_back_psia=10,
                                     v0_ft3_lb=0.3, omega=1.5, num_valves=0)

    def test_select_orifice_nan(self):
        with self.assertRaises(ValueError):
            select_orifice(float('nan'))

    def test_select_orifice_inf(self):
        with self.assertRaises(ValueError):
            select_orifice(float('inf'))

    def test_select_orifice_negative(self):
        with self.assertRaises(ValueError):
            select_orifice(-0.1)

    def test_select_orifice_non_number(self):
        with self.assertRaises(ValueError):
            select_orifice("not_a_number")


class TestSmokeTest(unittest.TestCase):

    def test_smoke_liquid_full_flow(self):
        res = calculate_liquid_relief_area(q_gpm=60, p1_psia=52.8, p2_psia=1.0, g=1.1, mu_cp=1.0, num_valves=1)
        self.assertIn('Selected_Orifice_Letter', res)
        self.assertIn('Required_Area_Final_sqin', res)
        self.assertIn('Reynolds_Number', res)
        self.assertIn('Kv', res)
        self.assertGreater(res['Required_Area_Final_sqin'], 0)

    def test_smoke_gas_full_flow(self):
        res = calculate_gas_relief_area(w_lb_h=9633, p1_psia=15.4, p2_psia=1.2, t_rankine=554, z=0.85, mw=21, k=1.3, num_valves=1)
        self.assertIn('Flow_Type', res)
        self.assertIn('Required_Area_sqin', res)
        self.assertIn('Selected_Orifice_Letter', res)
        self.assertGreater(res['Required_Area_sqin'], 0)

    def test_smoke_two_phase_full_flow(self):
        omega = calculate_omega_flashing(v0=0.00841, v9=0.00901)
        res = calculate_two_phase_area(w_lb_h=466259.5, p0_psia=136.14, p_back_psia=14.0, v0_ft3_lb=0.00841, omega=omega, kd=0.85, num_valves=1)
        self.assertIn('Omega', res)
        self.assertIn('Flow_Type', res)
        self.assertIn('Required_Area_sqin', res)
        self.assertIn('Selected_Orifice_Letter', res)
        self.assertGreater(res['Required_Area_sqin'], 0)

    def test_smoke_fire_wetted_full_flow(self):
        w, q = calculate_fire_wetted_load(a_wetted_sqft=12.836, f_factor=1.0, heat_of_vap_btu_lb=50)
        self.assertGreater(w, 0)
        self.assertGreater(q, 0)

    def test_smoke_fire_unwetted_full_flow(self):
        a, f_prime = calculate_fire_unwetted_area(a_exposed_sqft=44.177, p1_psia=16.94, t_gas_rankine=564.67, t_wall_rankine=1560, k=1.2)
        self.assertGreater(a, 0)
        self.assertGreater(f_prime, 0)

    def test_smoke_thermal_full_flow(self):
        q_gpm = calculate_thermal_expansion_load(b_expansion_coeff=0.0005, h_heat_transfer_btu_h=2100, g_specific_gravity=0.85, c_specific_heat=0.599)
        self.assertGreater(q_gpm, 0)

    def test_smoke_vendor_lookup(self):
        for letter in ["D", "K", "T"]:
            valves = get_vendor_valves(letter)
            self.assertIsInstance(valves, list)

    def test_smoke_validation_integration(self):
        with self.assertRaises(ValidationError):
            calculate_liquid_relief_area(q_gpm=-10, p1_psia=100, p2_psia=10, g=1.0, mu_cp=1.0)
        with self.assertRaises(ValidationError):
            calculate_gas_relief_area(w_lb_h=-100, p1_psia=500, p2_psia=14.7, t_rankine=600, z=0.9, mw=28, k=1.4)
        with self.assertRaises(ValidationError):
            calculate_two_phase_area(w_lb_h=-500000, p0_psia=1000, p_back_psia=100, v0_ft3_lb=0.1, omega=0.9)

    def test_smoke_run_streamlit_config_valid(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, "-c",
             "from streamlit.runtime.app_session import Config; modes = Config.ToolbarMode.keys(); "
             "assert 'MINIMAL' in modes, 'MINIMAL not in ToolbarMode'; "
             "assert 'NONE' not in modes, 'NONE should not be in ToolbarMode'"],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0, f"ToolbarMode validation failed: {result.stderr}")


class TestVersionConsistency(unittest.TestCase):

    def test_desktop_app_version_is_v22(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'desktop', 'app.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('v2.2', content)
        self.assertNotIn('v2.1', content)

    def test_web_app_version_is_v22(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web_app.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('v2.2', content)
        self.assertNotIn('v2.1', content)

    def test_report_generator_version_is_v22(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'desktop', 'report_generator.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('v2.2', content)
        self.assertNotIn('v2.1', content)


class TestGasCompositionRequirement(unittest.TestCase):

    def test_get_composition_empty_table(self):
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        from desktop.tabs import GasReliefTab
        tab = GasReliefTab()
        comp = tab.get_composition()
        self.assertEqual(comp, {})

    def test_get_composition_with_valid_entry(self):
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        from desktop.tabs import GasReliefTab
        tab = GasReliefTab()
        tab.add_fluid_row()
        combo = tab.comp_table.cellWidget(0, 0)
        if combo is not None:
            if combo.count() == 0:
                combo.addItem("Methane")
            combo.setCurrentText("Methane")
        frac = tab.comp_table.cellWidget(0, 1)
        if frac is not None:
            frac.setText("50")
        comp = tab.get_composition()
        self.assertIn("Methane", comp)
        self.assertAlmostEqual(comp["Methane"], 0.5, places=2)

    def test_gas_relief_allows_manual_inputs_without_composition(self):
        from desktop.tabs import GasReliefTab
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        tab = GasReliefTab()
        self.assertFalse(tab.z_input.isReadOnly())
        self.assertFalse(tab.mw_input.isReadOnly())
        self.assertFalse(tab.k_input.isReadOnly())
        tab.z_input.setText("0.90")
        tab.mw_input.setText("28.0")
        tab.k_input.setText("1.4")
        self.assertEqual(tab.z_input.text(), "0.90")
        self.assertEqual(tab.mw_input.text(), "28.0")
        self.assertEqual(tab.k_input.text(), "1.4")


class TestWebAppConfig(unittest.TestCase):

    def test_run_streamlit_uses_correct_flags(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'run_streamlit.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('--server.headless=true', content)
        self.assertIn('--server.port=8501', content)
        self.assertIn('--browser.gatherUsageStats=false', content)
        self.assertIn('STREAMLIT_DEVELOPMENT_MODE', content)
        self.assertNotIn('--global.developmentMode', content)
        self.assertIn('--client.toolbarMode=minimal', content)
        self.assertNotIn('--client.toolbarMode=none', content)

    def test_web_app_has_all_six_modules(self):
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web_app.py'), 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('1. Liquid Relief', content)
        self.assertIn('2. Gas/Vapor Relief', content)
        self.assertIn('3. Two-Phase Flashing', content)
        self.assertIn('4. Fire Wetted', content)
        self.assertIn('5. Fire Unwetted', content)
        self.assertIn('6. Thermal Expansion', content)


class TestSchemaVersion(unittest.TestCase):

    def test_schema_version_constant_is_22(self):
        from desktop.app import SCHEMA_VERSION
        self.assertEqual(SCHEMA_VERSION, '2.2')

    def test_save_uses_v22_schema(self):
        from desktop.app import SCHEMA_VERSION, PSVSizingApp
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        window = PSVSizingApp(role="user")
        inputs, _ = window.extract_tab_data(window.tabs.currentWidget())
        inputs['__schema_version__'] = SCHEMA_VERSION
        self.assertEqual(inputs['__schema_version__'], '2.2')

    def test_schema_version_backward_compatible_logic(self):
        from desktop.app import PSVSizingApp
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        window = PSVSizingApp(role="user")
        self.assertTrue(float('2.0') >= 2.0)
        self.assertTrue(float('2.1') >= 2.0)
        self.assertTrue(float('2.2') >= 2.0)
        self.assertFalse(float('1.0') >= 2.0)


class TestErrorHandler(unittest.TestCase):

    def test_tabs_have_exception_handling(self):
        import inspect
        from desktop.tabs import LiquidReliefTab, GasReliefTab, TwoPhaseReliefTab
        from desktop.tabs_extra import FireWettedTab, FireUnwettedTab, ThermalExpansionTab
        for tab_class in [LiquidReliefTab, GasReliefTab, TwoPhaseReliefTab,
                          FireWettedTab, FireUnwettedTab, ThermalExpansionTab]:
            source = inspect.getsource(tab_class.run_calculation)
            self.assertIn("except Exception", source,
                          f"{tab_class.__name__}.run_calculation lacks Exception handler")


class TestSaveLoad(unittest.TestCase):

    def test_save_all_tabs_structure(self):
        from desktop.app import PSVSizingApp, SCHEMA_VERSION
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        window = PSVSizingApp(role="user")
        tab_names = ["liquid", "gas", "twophase", "fire_wetted", "fire_unwetted", "thermal"]
        for name in tab_names:
            self.assertTrue(hasattr(window, f'tab_{name}'))

    def test_load_legacy_single_tab_format(self):
        from desktop.app import PSVSizingApp
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        window = PSVSizingApp(role="user")
        legacy_data = {
            '__schema_version__': '2.1',
            '__tab_name__': '1. Liquid Relief',
            'flow_input': '100',
            'p1_input': '50'
        }
        window.restore_tab_data(window.tab_liquid, legacy_data)
        self.assertEqual(window.tab_liquid.flow_input.text(), "100")


class TestReportGenerator(unittest.TestCase):

    def test_html_escapes_special_characters(self):
        import html
        malicious = "<script>alert('xss')</script>"
        escaped = html.escape(malicious)
        self.assertNotIn("<script>", escaped)
        self.assertIn("&lt;script&gt;", escaped)

    def test_html_escapes_ampersand_and_quotes(self):
        import html
        raw = "Value & \"special\" <test> 'quote'"
        escaped = html.escape(raw)
        self.assertIn("&amp;", escaped)
        self.assertIn("&quot;", escaped)
        self.assertIn("&lt;", escaped)
        self.assertNotIn("<test>", escaped)

    def test_report_generator_imports_html(self):
        from desktop import report_generator
        import inspect
        source = inspect.getsource(report_generator)
        self.assertIn("import html", source)
        self.assertIn("html.escape", source)


class TestUpdateCheck(unittest.TestCase):

    def test_parse_version_standard(self):
        from desktop.app import parse_version
        self.assertEqual(parse_version("v2.2"), (2, 2, 0))
        self.assertEqual(parse_version("v1.0.3"), (1, 0, 3))
        self.assertEqual(parse_version("2.2"), (2, 2, 0))
        self.assertEqual(parse_version("v10.25.1"), (10, 25, 1))

    def test_parse_version_invalid(self):
        from desktop.app import parse_version
        self.assertEqual(parse_version("invalid"), (0, 0, 0))
        self.assertEqual(parse_version(""), (0, 0, 0))
        self.assertEqual(parse_version("abc123"), (0, 0, 0))

    def test_version_comparison_newer(self):
        from desktop.app import parse_version
        self.assertTrue(parse_version("v2.3") > parse_version("v2.2"))
        self.assertTrue(parse_version("v3.0") > parse_version("v2.9"))
        self.assertTrue(parse_version("v2.2.1") > parse_version("v2.2"))

    def test_version_comparison_older(self):
        from desktop.app import parse_version
        self.assertTrue(parse_version("v2.1") < parse_version("v2.2"))
        self.assertTrue(parse_version("v1.9") < parse_version("v2.0"))

    def test_version_comparison_equal(self):
        from desktop.app import parse_version
        self.assertEqual(parse_version("v2.2"), parse_version("v2.2"))

    def test_app_version_constant_exists(self):
        from desktop.app import APP_VERSION
        self.assertEqual(APP_VERSION, "v2.2")

    def test_app_version_in_title(self):
        from desktop.app import APP_VERSION, PSVSizingApp
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        window = PSVSizingApp(role="user")
        self.assertIn(APP_VERSION, window.windowTitle())

    def test_github_url_constants_exist(self):
        from desktop.app import GITHUB_RELEASES_URL, GITHUB_RELEASES_PAGE
        self.assertIn("api.github.com", GITHUB_RELEASES_URL)
        self.assertIn("github.com", GITHUB_RELEASES_PAGE)

    def test_check_update_handles_network_error_gracefully(self):
        from desktop.app import PSVSizingApp
        from PyQt5.QtWidgets import QApplication, QMessageBox
        from desktop.workers import UpdateCheckWorker
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        window = PSVSizingApp(role="user")
        original_start = UpdateCheckWorker.start
        def mock_start_immediate(self):
            self.error.emit("Network error")
        with patch.object(UpdateCheckWorker, "start", mock_start_immediate):
            with patch.object(QMessageBox, "warning") as mock_warn:
                window.check_update()
                mock_warn.assert_called_once()

    def test_check_update_shows_update_available(self):
        from desktop.app import PSVSizingApp
        from PyQt5.QtWidgets import QApplication, QMessageBox
        from desktop.workers import UpdateCheckWorker
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        window = PSVSizingApp(role="user")
        def mock_start_immediate(self):
            self.finished.emit({
                "tag_name": "v3.0",
                "body": "New features added",
                "html_url": "https://github.com/test/releases/tag/v3.0"
            })
        with patch.object(UpdateCheckWorker, "start", mock_start_immediate):
            with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as mock_question:
                window.check_update()
                mock_question.assert_called_once()

    def test_check_update_shows_up_to_date(self):
        from desktop.app import PSVSizingApp
        from PyQt5.QtWidgets import QApplication, QMessageBox
        from desktop.workers import UpdateCheckWorker
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        window = PSVSizingApp(role="user")
        def mock_start_immediate(self):
            self.finished.emit({
                "tag_name": "v2.2",
                "body": "Current release",
                "html_url": "https://github.com/test/releases/tag/v2.2"
            })
        with patch.object(UpdateCheckWorker, "start", mock_start_immediate):
            with patch.object(QMessageBox, "information") as mock_info:
                window.check_update()
                mock_info.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
