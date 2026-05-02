import sys
import os
import unittest

# Add root project path to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.thermo_props import calculate_mixture_properties, get_coolprop_fluids
from core.liquid_relief import calculate_liquid_relief_area
from core.gas_relief import calculate_gas_relief_area
from core.two_phase import calculate_omega_flashing, calculate_two_phase_area
from core.fire_scenarios import calculate_fire_wetted_load, calculate_fire_unwetted_area
from core.thermal_expansion import calculate_thermal_expansion_load
from core.blowby import calculate_blowby_flowrate
from core.unit_converter import m3_h_to_gpm, barg_to_psia

class TestPSVSizingCore(unittest.TestCase):
    
    def test_coolprop_fluids_list(self):
        """Test if CoolProp fluid list is retrieved successfully and Water alias exists."""
        fluids = get_coolprop_fluids()
        self.assertGreater(len(fluids), 10)
        self.assertIn("Methane", fluids)
        self.assertIn("Water (Steam)", fluids)

    def test_mixture_properties_mole(self):
        """Test CoolProp mixture thermodynamics calculation using Mole %."""
        # 80% Methane, 20% Ethane by mole
        comp = {"Methane": 0.8, "Ethane": 0.2}
        t_rankine = 560  # Approx 100 F
        p_psia = 100
        
        z, mw, k = calculate_mixture_properties(comp, t_rankine, p_psia, fraction_type="mole")
        
        self.assertGreater(z, 0.8)
        self.assertLess(z, 1.1)
        self.assertGreater(mw, 18.0)
        self.assertLess(mw, 20.0)
        self.assertGreater(k, 1.1)

    def test_mixture_properties_mass(self):
        """Test CoolProp mixture thermodynamics calculation using Mass %."""
        # 50% Methane, 50% Ethane by mass
        comp = {"Methane": 0.5, "Ethane": 0.5}
        t_rankine = 560
        p_psia = 100
        
        z, mw, k = calculate_mixture_properties(comp, t_rankine, p_psia, fraction_type="mass")
        
        # MW should be exactly average if 50/50 mole. But 50/50 mass gives more moles of Methane.
        # So MW should be between 16 and 30, leaning closer to 16.
        self.assertGreater(mw, 16.0)
        self.assertLess(mw, 30.0)
        self.assertGreater(k, 1.1)

    def test_mixture_properties_fallback_kays_rule(self):
        """Test CoolProp fallback for mixtures lacking binary interaction parameters."""
        comp = {"Methane": 0.95, "Ethane": 0.02, "CycloPropane": 0.03}
        t_rankine = 560
        p_psia = 100
        
        # This should not raise an exception now.
        z, mw, k = calculate_mixture_properties(comp, t_rankine, p_psia, fraction_type="mole")
        
        self.assertGreater(z, 0.8)
        self.assertGreater(mw, 16.0)
        self.assertLess(mw, 25.0)
        self.assertGreater(k, 1.1)

    def test_liquid_relief(self):
        """Test basic Liquid Relief calculations."""
        res = calculate_liquid_relief_area(q_gpm=60, p1_psia=100, p2_psia=10, g=1.0, mu_cp=1.0)
        self.assertIn('Required_Area_Final_sqin', res)
        self.assertIn('Selected_Orifice_Letter', res)
        self.assertGreater(res['Required_Area_Final_sqin'], 0.01)

    def test_gas_relief(self):
        """Test basic Gas/Vapor Relief calculations."""
        res_crit = calculate_gas_relief_area(w_lb_h=10000, p1_psia=500, p2_psia=14.7, t_rankine=600, z=0.9, mw=28, k=1.4)
        self.assertEqual(res_crit['Flow_Type'], 'CRITICAL')
        self.assertGreater(res_crit['Required_Area_sqin'], 0.1)

        res_sub = calculate_gas_relief_area(w_lb_h=10000, p1_psia=500, p2_psia=450, t_rankine=600, z=0.9, mw=28, k=1.4)
        self.assertEqual(res_sub['Flow_Type'], 'SUBCRITICAL')
        self.assertGreater(res_sub['Required_Area_sqin'], res_crit['Required_Area_sqin'])

    def test_two_phase(self):
        """Test Two-Phase Omega Method calculations."""
        omega = calculate_omega_flashing(v0=0.1, v9=0.11)
        self.assertAlmostEqual(omega, 0.9, places=2)
        
        res = calculate_two_phase_area(w_lb_h=500000, p0_psia=1000, p_back_psia=100, v0_ft3_lb=0.1, omega=omega)
        self.assertGreater(res['Required_Area_sqin'], 1.0)
        self.assertIn('Selected_Orifice_Letter', res)

    def test_fire_wetted(self):
        """Test Fire Wetted calculations."""
        w, q = calculate_fire_wetted_load(a_wetted_sqft=100, f_factor=1.0, heat_of_vap_btu_lb=100)
        self.assertGreater(q, 0)
        self.assertGreater(w, 0)
        self.assertEqual(w, q / 100)

    def test_fire_unwetted(self):
        """Test Fire Unwetted calculations."""
        a, f_prime = calculate_fire_unwetted_area(a_exposed_sqft=100, p1_psia=100, t_gas_rankine=500, t_wall_rankine=1000, k=1.4)
        self.assertGreater(a, 0)
        self.assertGreater(f_prime, 0)

    def test_thermal_expansion(self):
        """Test Thermal Expansion calculations."""
        q_gpm = calculate_thermal_expansion_load(b_expansion_coeff=0.0005, h_heat_transfer_btu_h=2100000, g_specific_gravity=0.85, c_specific_heat=0.6)
        self.assertGreater(q_gpm, 0)

    def test_blowby(self):
        """Test Control Valve Blow-by flow rate."""
        flow = calculate_blowby_flowrate(assumed_flow_kg_h=1000, nominal_cv=10, calculated_cv_at_blowby=5)
        self.assertEqual(flow, 2000)

if __name__ == "__main__":
    unittest.main(verbosity=2)
