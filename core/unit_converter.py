# unit_converter.py

def barg_to_psia(barg):
    return (barg * 14.50377) + 14.6959

def bara_to_psia(bara):
    return bara * 14.50377

def psia_to_barg(psia):
    return (psia - 14.6959) / 14.50377

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

# --- Gas Volumetric to Mass Flow Converters ---
# Gas constant R in (psia * ft3) / (lb-mol * °R) is 10.7316

def actual_m3_h_to_lb_h(m3_h, p_psia, t_rankine, mw, z):
    """Convert actual m3/h at relieving conditions to mass flow lb/h."""
    rho_lb_ft3 = (p_psia * mw) / (z * 10.7316 * t_rankine)
    ft3_h = m3_h * 35.31467
    return ft3_h * rho_lb_ft3

def sm3_h_to_lb_h(sm3_h, mw):
    """Convert Standard m3/h (60°F / 15.56°C, 14.696 psia) to mass flow lb/h. Assume Z=1 at standard."""
    rho_std_lb_ft3 = (14.696 * mw) / (1.0 * 10.7316 * 519.67)
    ft3_h = sm3_h * 35.31467
    return ft3_h * rho_std_lb_ft3

def nm3_h_to_lb_h(nm3_h, mw):
    """Convert Normal m3/h (0°C, 1.01325 bar) to mass flow lb/h. Assume Z=1 at normal."""
    # 0 C = 491.67 R, 1.01325 bar = 14.696 psia
    rho_norm_lb_ft3 = (14.696 * mw) / (1.0 * 10.7316 * 491.67)
    ft3_h = nm3_h * 35.31467
    return ft3_h * rho_norm_lb_ft3
