import math

w = 0.641265476511077
hc_vals = [0.6, 0.5, 0.55]
E_vals = [0.12944273449394228, -0.12667989779634808, 0.004472337609038701]

def test_eq(hc, w):
    # Eq 1
    e1 = w * math.log(1/hc) + (w - 1)*(1/hc - 1)
    # Eq 2
    e2 = hc**2 + (w - 2)*hc + 1 - w
    # Eq 3: From API 520 8th edition, two phase Annex C
    # eta_c^2 + (omega - 1) / (omega + 1) ...
    
    # Let's try to match E_vals[0] exactly. E_vals[0] = 0.12944273449394228
    
    # Leung's Omega Method choking condition:
    # G^2 = - dP / dv.
    # v = v0 * [ omega * (P0/P) + (1 - omega) ]
    # rho = 1/v
    # Gc = P0 / sqrt(v0) * sqrt( eta_c / (omega + (1-omega)*eta_c) ) ???
    
    return [e1, e2]

for hc, E_target in zip(hc_vals, E_vals):
    print(f"hc={hc}, target={E_target}")
    # Let's see if there's a simple algebraic relation: E_target + w = ?
    print(f"hc={hc}, E={hc**2 + w*(1 - 2*hc)}") # wait

    # API 520 Two Phase Omega Method Critical Pressure Ratio Eq:
    # eta_c^2 + (omega - 2 * omega * eta_c) ... no
    # Actually, Leung (1986): eta_c^2 + (omega - 1) * eta_c^2 / ...
    
    # Let's check eta_c^2 + (omega - 1)*eta_c^2 - ... no
    # Just print eta_c^2 + omega*(1 - eta_c)^2
    v1 = hc**2 + w*(1 - hc)**2
    # print(v1)
    
    # E_target = hc**2 * something?
    # E_target for hc=0.6 is 0.12944. hc^2 = 0.36. 0.36 - 0.12944 = 0.2305
    # w = 0.64126
    
    # E = hc**2 + (omega - 2*omega*hc + ...)
    pass

# We will just write the function that solves for eta_c by maximizing mass flux!
# G = P0 / sqrt(v0) * sqrt( -2 * [ omega * ln(eta) + (omega - 1)*(eta - 1) ] ) / (omega / eta + 1 - omega)
# Mass flux equation API 520:
# G = sqrt( P0 / v0 ) * sqrt( 2 * ( omega * ln(1/eta) + (omega - 1)*(1 - eta) ) ) / ( omega/eta + 1 - omega )
