# Atmospheric pressure constants
ATM_PSIA = 14.6959
PSI_PER_BAR = 14.50377
R_PSIA_FT3_LBMOL_R = 10.7316

def barg_to_psia(barg):
    return (barg * PSI_PER_BAR) + ATM_PSIA

def bara_to_psia(bara):
    return bara * PSI_PER_BAR

def psia_to_barg(psia):
    return (psia - ATM_PSIA) / PSI_PER_BAR

def kg_h_to_lb_h(kg_h):
    return kg_h * 2.204623

def lb_h_to_kg_h(lb_h):
    return lb_h / 2.204623

def kg_s_to_lb_h(kg_s):
    return kg_s * 3600.0 * 2.204623

def m3_h_to_gpm(m3_h):
    return m3_h * 4.402868

def gpm_to_m3_h(gpm):
    return gpm / 4.402868

def c_to_rankine(c):
    return (c * 1.8) + 491.67

def c_to_f(c):
    return (c * 1.8) + 32.0

def m3_kg_to_ft3_lb(m3_kg):
    return m3_kg * 16.01846

def kg_m3_to_lb_ft3(kg_m3):
    return kg_m3 * 0.062428

def kcal_h_to_btu_h(kcal_h):
    return kcal_h * 3.96832

def kw_to_btu_h(kw):
    return kw * 3412.142

def m2_to_sqft(m2):
    return m2 * 10.76391

def sqft_to_m2(sqft):
    return sqft / 10.76391

def kcal_kg_to_btu_lb(kcal_kg):
    return kcal_kg * 1.8

def kj_kgK_to_btu_lbF(kj_kgK):
    return kj_kgK * 0.238846

def actual_m3_h_to_lb_h(m3_h, p_psia, t_rankine, mw, z):
    """Convert actual m3/h at relieving conditions to mass flow lb/h."""
    rho_lb_ft3 = (p_psia * mw) / (z * R_PSIA_FT3_LBMOL_R * t_rankine)
    ft3_h = m3_h * 35.31467
    return ft3_h * rho_lb_ft3

def sm3_h_to_lb_h(sm3_h, mw):
    """Convert Standard m3/h (60°F, 14.696 psia) to mass flow lb/h."""
    rho_std_lb_ft3 = (ATM_PSIA * mw) / (1.0 * R_PSIA_FT3_LBMOL_R * 519.67)
    ft3_h = sm3_h * 35.31467
    return ft3_h * rho_std_lb_ft3

def nm3_h_to_lb_h(nm3_h, mw):
    """Convert Normal m3/h (0°C, 1.01325 bar) to mass flow lb/h."""
    rho_norm_lb_ft3 = (ATM_PSIA * mw) / (1.0 * R_PSIA_FT3_LBMOL_R * 491.67)
    ft3_h = nm3_h * 35.31467
    return ft3_h * rho_norm_lb_ft3