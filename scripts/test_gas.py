from core.gas_relief import calculate_gas_relief_area

print("--- CRITICAL GAS RELIEF TEST ---")
res1 = calculate_gas_relief_area(w_lb_h=21237.13, p1_psia=237.86, p2_psia=32.0, t_rankine=555.0, z=0.85, mw=21.0, k=1.2)
print(f"Flow Type: {res1['Flow_Type']}")
print(f"C: {res1['C_Coefficient']:.3f}")
print(f"Required Area: {res1['Required_Area_sqin']:.4f} sq.in")
print(f"Selected: {res1['Selected_Orifice_Letter']} ({res1['Selected_Orifice_Area_sqin']})\n")

print("--- SUBCRITICAL GAS RELIEF TEST ---")
res2 = calculate_gas_relief_area(w_lb_h=26855.94, p1_psia=1276.33, p2_psia=1174.805, t_rankine=582.0, z=0.8, mw=21.0, k=1.7)
print(f"Flow Type: {res2['Flow_Type']}")
print(f"F2: {res2['F2_Coefficient']:.4f}")
print(f"Required Area: {res2['Required_Area_sqin']:.4f} sq.in")
print(f"Selected: {res2['Selected_Orifice_Letter']} ({res2['Selected_Orifice_Area_sqin']})\n")
