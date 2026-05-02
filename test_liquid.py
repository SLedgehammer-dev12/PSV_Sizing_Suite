from core.liquid_relief import calculate_liquid_relief_area

# Data from "FULL FLOW - LIQUID RELIEF" sheet
q_gpm = 264.1721
p1_psia = 780.302826
p2_psia = 29.00754
g = 1.1
mu_cp = 1.0

# Run calc
results = calculate_liquid_relief_area(q_gpm, p1_psia, p2_psia, g, mu_cp)

print("--- LIQUID RELIEF TEST ---")
print(f"Required Area No Visc: {results['Required_Area_No_Visc_sqin']:.4f} sq.in")
print(f"Reynolds Number:       {results['Reynolds_Number']:.2f}")
print(f"Kv:                    {results['Kv']:.4f}")
print(f"Final Required Area:   {results['Required_Area_Final_sqin']:.4f} sq.in")
print(f"Selected Orifice:      {results['Selected_Orifice_Letter']} ({results['Selected_Orifice_Area_sqin']} sq.in)")
