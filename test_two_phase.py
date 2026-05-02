from core.two_phase import calculate_omega_flashing, calculate_two_phase_area

v0 = 0.134746
v9 = 0.144346
p0 = 1974.543248
p_back = 217.742 # approx 14 barg
w = 1027908.96
kd = 0.85

omega = calculate_omega_flashing(v0, v9)
print(f"Calculated Omega: {omega:.6f}")

res = calculate_two_phase_area(w, p0, p_back, v0, omega, kd=kd)

print("--- TWO PHASE RELIEF TEST ---")
print(f"Flow Type: {res['Flow_Type']}")
print(f"Critical Pressure Ratio (hc): {res['Critical_Pressure_Ratio_hc']:.5f}")
print(f"Critical Pressure: {res['Critical_Pressure_psia']:.2f} psia")
print(f"Mass Flux G: {res['Mass_Flux_G_lb_s_ft2']:.2f} lb/s/ft2")
print(f"Required Area: {res['Required_Area_sqin']:.4f} sq.in")
print(f"Selected: {res['Selected_Orifice_Letter']} ({res['Selected_Orifice_Area_sqin']})\n")
