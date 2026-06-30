import streamlit as st
import html

from core.liquid_relief import calculate_liquid_relief_area
from core.gas_relief import calculate_gas_relief_area
from core.two_phase import calculate_two_phase_area, calculate_omega_flashing
from core.fire_scenarios import calculate_fire_wetted_load, calculate_fire_unwetted_area
from core.thermal_expansion import calculate_thermal_expansion_load
from core.vendor_catalog import get_vendor_valves
from core.unit_converter import (
    barg_to_psia, bara_to_psia, kg_h_to_lb_h, lb_h_to_kg_h,
    m3_h_to_gpm, gpm_to_m3_h, c_to_rankine, m3_kg_to_ft3_lb,
    sqft_to_m2, m2_to_sqft, kw_to_btu_h, kcal_h_to_btu_h,
    kcal_kg_to_btu_lb
)
from desktop.auth import check_login


def render_vendor_table(valves):
    """Render vendor rows with browser-side confirmation before opening links."""
    columns = [
        ("manufacturer", "Üretici"),
        ("series", "Seri"),
        ("model_code", "Model Kodu"),
        ("design_type", "Dizayn"),
        ("inlet_outlet_size_in", "Giriş/Çıkış Çapı"),
        ("actual_area_mm2", "Gerçek Alan (mm²)"),
    ]

    rows = []
    for valve in valves:
        cells = []
        for key, _ in columns:
            value = valve.get(key, "")
            cells.append(f"<td>{html.escape(str(value))}</td>")

        website = str(valve.get("website", "")).strip()
        manufacturer = str(valve.get("manufacturer", "üretici")).strip() or "üretici"
        if website:
            confirm_message = html.escape(
                f"{manufacturer} üreticisinin sayfasını açmak istiyor musunuz?",
                quote=True,
            )
            link = (
                f'<a href="{html.escape(website, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer" '
                f'onclick="return confirm(&quot;{confirm_message}&quot;);">Sayfayı aç</a>'
            )
        else:
            link = '<span class="muted">Web sitesi yok</span>'

        cells.append(f"<td>{link}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")

    headers = "".join(f"<th>{label}</th>" for _, label in columns) + "<th>Üretici Sayfası</th>"
    table_html = f"""
    <style>
      .vendor-table {{
        border-collapse: collapse;
        width: 100%;
        font-size: 0.92rem;
      }}
      .vendor-table th, .vendor-table td {{
        border: 1px solid #d9dee7;
        padding: 0.45rem 0.55rem;
        text-align: left;
        vertical-align: top;
      }}
      .vendor-table th {{
        background: #f4f6fa;
        font-weight: 600;
      }}
      .vendor-table a {{
        color: #0b66c3;
        font-weight: 600;
        text-decoration: none;
      }}
      .vendor-table a:hover {{
        text-decoration: underline;
      }}
      .vendor-table .muted {{
        color: #667085;
      }}
    </style>
    <table class="vendor-table">
      <thead><tr>{headers}</tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)


def display_results(res, area_key='Required_Area_Final_sqin'):
    st.markdown("### Sonuçlar")
    res_col1, res_col2, res_col3 = st.columns(3)
    req_area = res.get(area_key, res.get('Required_Area_sqin', 0))
    res_col1.metric("Gerekli Alan (sq.inch)", f"{req_area:.4f}")
    letter = res.get('Selected_Orifice_Letter', '-')
    sel_area = res.get('Selected_Orifice_Area_sqin', 0)
    if isinstance(sel_area, (int, float)):
        res_col2.metric("Seçilen Orifis", f"{letter} ({sel_area:.4f} sq.in)")
    else:
        res_col2.metric("Seçilen Orifis", letter)
    return letter


st.set_page_config(page_title="PSV Sizing Suite v2.2", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("PSV Sizing Suite v2.2 - Giris")
    col1, col2 = st.columns([1, 2])
    with col1:
        username = st.text_input("Kullanici Adi")
        password = st.text_input("Sifre", type="password")
        if st.button("Giris Yap", type="primary"):
            if check_login(username, password):
                st.session_state.authenticated = True
                st.session_state.role = username
                st.rerun()
            else:
                st.error("Hatali kullanici adi veya sifre!")
    st.stop()

st.sidebar.title("PSV Sizing Suite")
st.sidebar.markdown("Muhendislik Hesaplama Platformu (v2.2)")

page = st.sidebar.radio("Modül Seçimi", [
    "1. Liquid Relief (Sıvı Tahliye)",
    "2. Gas/Vapor Relief (Gaz Tahliye)",
    "3. Two-Phase Flashing (İki Fazlı)",
    "4. Fire Wetted (Yangın Islak Yüzey)",
    "5. Fire Unwetted (Yangın Kuru Yüzey)",
    "6. Thermal Expansion (Termal Genleşme)",
    "Hakkında"
])

st.title(page)

if page == "1. Liquid Relief (Sıvı Tahliye)":
    st.markdown("### Girdiler (Inputs)")
    col1, col2 = st.columns(2)

    with col1:
        flow_unit = st.selectbox("Flow Rate Unit", ["US gpm", "m3/h"])
        if flow_unit == "US gpm":
            q_gpm = st.number_input("Flow Rate (US gpm)", value=60.0, format="%.2f")
        else:
            q_m3h = st.number_input("Flow Rate (m3/h)", value=13.6, format="%.2f")
            q_gpm = m3_h_to_gpm(q_m3h)

        p1_unit = st.selectbox("P1 Unit", ["psia", "barg"])
        if p1_unit == "barg":
            p1_barg = st.number_input("Relieving Pressure P1 (barg)", value=2.64, format="%.2f")
            p1_psia = barg_to_psia(p1_barg)
        else:
            p1_psia = st.number_input("Relieving Pressure P1 (psia)", value=52.8, format="%.2f")

    with col2:
        p2_unit = st.selectbox("P2 Unit", ["psia", "barg"])
        if p2_unit == "barg":
            p2_barg = st.number_input("Back Pressure P2 (barg)", value=0.07, format="%.2f")
            p2_psia = barg_to_psia(p2_barg)
        else:
            p2_psia = st.number_input("Back Pressure P2 (psia)", value=1.0, format="%.2f")

        g = st.number_input("Specific Gravity (G)", value=1.1, format="%.2f")
        mu_cp = st.number_input("Viscosity (cP)", value=1.0, format="%.2f")
        num_valves = st.number_input("Number of Parallel Valves", min_value=1, value=1, step=1)

    if st.button("HESAPLA", type="primary"):
        try:
            res = calculate_liquid_relief_area(q_gpm, p1_psia, p2_psia, g, mu_cp, num_valves=num_valves)
            letter = display_results(res)
            st.markdown("### Uygun Ticari Vanalar (Vendor DB)")
            valves = get_vendor_valves(letter)
            if valves:
                render_vendor_table(valves)
            else:
                st.info("Bu orifis için veritabanında ticari vana bulunamadı veya Paralel Vana sayısı yetersiz.")
        except Exception as e:
            st.error(f"Hesaplama hatası: {e}")

elif page == "2. Gas/Vapor Relief (Gaz Tahliye)":
    st.markdown("### Girdiler (Inputs)")
    col1, col2 = st.columns(2)

    with col1:
        flow_unit = st.selectbox("Flow Rate Unit", ["lb/h", "kg/h"], key="gas_flow")
        if flow_unit == "kg/h":
            w_kg_h = st.number_input("Mass Flow Rate (kg/h)", value=4369.0, format="%.1f")
            w_lb_h = kg_h_to_lb_h(w_kg_h)
        else:
            w_lb_h = st.number_input("Mass Flow Rate (lb/h)", value=9633.0, format="%.1f")

        p1_unit = st.selectbox("P1 Unit", ["psia", "barg"], key="gas_p1")
        if p1_unit == "barg":
            p1_barg = st.number_input("Relieving Pressure P1 (barg)", value=0.06, format="%.2f")
            p1_psia = barg_to_psia(p1_barg)
        else:
            p1_psia = st.number_input("Relieving Pressure P1 (psia)", value=15.4, format="%.2f")

    with col2:
        p2_unit = st.selectbox("P2 Unit", ["psia", "barg"], key="gas_p2")
        if p2_unit == "barg":
            p2_barg = st.number_input("Back Pressure P2 (barg)", value=0.01, format="%.2f")
            p2_psia = barg_to_psia(p2_barg)
        else:
            p2_psia = st.number_input("Back Pressure P2 (psia)", value=1.2, format="%.2f")

        t_unit = st.selectbox("Temperature Unit", ["Rankine", "°C"], key="gas_t")
        if t_unit == "°C":
            t_c = st.number_input("Relieving Temp (°C)", value=35.0, format="%.1f")
            t_rankine = c_to_rankine(t_c)
        else:
            t_rankine = st.number_input("Relieving Temp (Rankine)", value=554.0, format="%.1f")

        z = st.number_input("Compressibility (Z)", value=0.85, format="%.3f")
        mw = st.number_input("Molecular Weight (MW)", value=21.0, format="%.1f")
        k = st.number_input("Specific Heat Ratio (k)", value=1.3, format="%.2f")
        num_valves = st.number_input("Number of Parallel Valves", min_value=1, value=1, step=1, key="gas_nv")

    if st.button("HESAPLA", type="primary"):
        try:
            res = calculate_gas_relief_area(w_lb_h, p1_psia, p2_psia, t_rankine, z, mw, k, num_valves=num_valves)
            letter = display_results(res, 'Required_Area_sqin')
            st.info(f"Akış Rejimi: {res['Flow_Type']}")
            st.markdown("### Uygun Ticari Vanalar (Vendor DB)")
            valves = get_vendor_valves(letter)
            if valves:
                render_vendor_table(valves)
            else:
                st.info("Bu orifis için veritabanında ticari vana bulunamadı veya Paralel Vana sayısı yetersiz.")
        except Exception as e:
            st.error(f"Hesaplama hatası: {e}")

elif page == "3. Two-Phase Flashing (İki Fazlı)":
    st.markdown("### Girdiler (Inputs)")
    col1, col2 = st.columns(2)

    with col1:
        flow_unit = st.selectbox("Flow Rate Unit", ["lb/h", "kg/h"], key="tp_flow")
        if flow_unit == "kg/h":
            w_kg_h = st.number_input("Mass Flow Rate (kg/h)", value=211500.0, format="%.1f")
            w_lb_h = kg_h_to_lb_h(w_kg_h)
        else:
            w_lb_h = st.number_input("Mass Flow Rate (lb/h)", value=466259.5, format="%.1f")

        p0_unit = st.selectbox("P0 Unit", ["psia", "bara"], key="tp_p0")
        if p0_unit == "bara":
            p0_bara = st.number_input("Relieving Pressure P0 (bara)", value=9.39, format="%.2f")
            p0_psia = p0_bara * 14.50377
        else:
            p0_psia = st.number_input("Relieving Pressure P0 (psia)", value=136.14, format="%.2f")

    with col2:
        pback_unit = st.selectbox("Back Pressure Unit", ["psia", "barg"], key="tp_bp")
        if pback_unit == "barg":
            pback_barg = st.number_input("Back Pressure (barg)", value=0.0, format="%.2f")
            p_back = barg_to_psia(pback_barg)
        else:
            p_back = st.number_input("Back Pressure (psia)", value=14.0, format="%.2f")

        v0_unit = st.selectbox("v0 Unit", ["ft3/lb", "m3/kg"], key="tp_v0")
        if v0_unit == "m3/kg":
            v0_m3kg = st.number_input("Specific Vol at Inlet v0 (m3/kg)", value=0.000134, format="%.6f")
            v0 = m3_kg_to_ft3_lb(v0_m3kg)
        else:
            v0 = st.number_input("Specific Vol at Inlet v0 (ft3/lb)", value=0.00841, format="%.5f")

        v9_unit = st.selectbox("v9 Unit", ["ft3/lb", "m3/kg"], key="tp_v9")
        if v9_unit == "m3/kg":
            v9_m3kg = st.number_input("Specific Vol at 90% P0 v9 (m3/kg)", value=0.000144, format="%.6f")
            v9 = m3_kg_to_ft3_lb(v9_m3kg)
        else:
            v9 = st.number_input("Specific Vol at 90% P0 v9 (ft3/lb)", value=0.00901, format="%.5f")

        kd = st.number_input("Discharge Coeff (Kd)", value=0.85, format="%.2f")
        num_valves = st.number_input("Number of Parallel Valves", min_value=1, value=1, step=1, key="tp_nv")

    if st.button("HESAPLA", type="primary"):
        try:
            omega = calculate_omega_flashing(v0, v9)
            res = calculate_two_phase_area(w_lb_h, p0_psia, p_back, v0, omega, kd, num_valves=num_valves)
            letter = display_results(res, 'Required_Area_sqin')
            st.info(f"Omega (w): {res['Omega']:.3f} | Akış: {res['Flow_Type']}")
            st.markdown("### Uygun Ticari Vanalar (Vendor DB)")
            valves = get_vendor_valves(letter)
            if valves:
                render_vendor_table(valves)
            else:
                st.info("Bu orifis için veritabanında ticari vana bulunamadı veya Paralel Vana sayısı yetersiz.")
        except Exception as e:
            st.error(f"Hesaplama hatası: {e}")

elif page == "4. Fire Wetted (Yangın Islak Yüzey)":
    st.markdown("### Girdiler (Inputs)")
    col1, col2 = st.columns(2)

    with col1:
        area_unit = st.selectbox("Wetted Area Unit", ["sq.ft", "m2"])
        if area_unit == "m2":
            area_m2 = st.number_input("Wetted Area (m2)", value=1.19, format="%.3f")
            area = m2_to_sqft(area_m2)
        else:
            area = st.number_input("Wetted Area (sq.ft)", value=12.836, format="%.3f")

        hvap_unit = st.selectbox("Heat of Vap Unit", ["Btu/lb", "kcal/kg"])
        if hvap_unit == "kcal/kg":
            hvap_kcal = st.number_input("Latent Heat of Vap (kcal/kg)", value=27.8, format="%.1f")
            hvap = kcal_kg_to_btu_lb(hvap_kcal)
        else:
            hvap = st.number_input("Latent Heat of Vap (Btu/lb)", value=50.0, format="%.1f")

        f_factor = st.number_input("Environment Factor (F)", value=1.0, format="%.2f", min_value=0.1, max_value=1.0)

    with col2:
        p1_unit = st.selectbox("P1 Unit", ["psia", "barg"], key="fw_p1")
        if p1_unit == "barg":
            p1_barg = st.number_input("Relieving Pressure P1 (barg)", value=0.64, format="%.2f")
            p1_psia = barg_to_psia(p1_barg)
        else:
            p1_psia = st.number_input("Relieving Pressure P1 (psia)", value=16.94, format="%.2f")

        p2_unit = st.selectbox("P2 Unit", ["psia", "barg"], key="fw_p2")
        if p2_unit == "barg":
            p2_barg = st.number_input("Back Pressure P2 (barg)", value=0.0, format="%.2f")
            p2_psia = barg_to_psia(p2_barg)
        else:
            p2_psia = st.number_input("Back Pressure P2 (psia)", value=14.7, format="%.2f")

        t_rankine = st.number_input("Gas Temp (°R)", value=564.67, format="%.2f")
        z = st.number_input("Compressibility (Z)", value=0.92, format="%.3f")
        mw = st.number_input("Molecular Weight (MW)", value=21.0, format="%.1f")
        k = st.number_input("Spec. Heat Ratio (k)", value=1.3, format="%.2f")

    if st.button("HESAPLA", type="primary"):
        try:
            w_lb_h, q_btu_h = calculate_fire_wetted_load(area, f_factor, hvap)
            res = calculate_gas_relief_area(w_lb_h, p1_psia, p2_psia, t_rankine, z, mw, k)
            letter = display_results(res, 'Required_Area_sqin')
            st.metric("Heat Absorption (Btu/h)", f"{q_btu_h:.2f}")
            st.metric("Relief Load (lb/h)", f"{w_lb_h:.2f}")
            st.markdown("### Uygun Ticari Vanalar (Vendor DB)")
            valves = get_vendor_valves(letter)
            if valves:
                render_vendor_table(valves)
            else:
                st.info("Bu orifis için veritabanında ticari vana bulunamadı.")
        except Exception as e:
            st.error(f"Hesaplama hatası: {e}")

elif page == "5. Fire Unwetted (Yangın Kuru Yüzey)":
    st.markdown("### Girdiler (Inputs)")
    col1, col2 = st.columns(2)

    with col1:
        area_unit = st.selectbox("Exposed Area Unit", ["sq.ft", "m2"], key="fu_area")
        if area_unit == "m2":
            area_m2 = st.number_input("Exposed Area (m2)", value=4.1, format="%.3f")
            area = m2_to_sqft(area_m2)
        else:
            area = st.number_input("Exposed Area (sq.ft)", value=44.177, format="%.3f")

        p1_unit = st.selectbox("P1 Unit", ["psia", "barg"], key="fu_p1")
        if p1_unit == "barg":
            p1_barg = st.number_input("Relieving Pressure P1 (barg)", value=0.64, format="%.2f")
            p1_psia = barg_to_psia(p1_barg)
        else:
            p1_psia = st.number_input("Relieving Pressure P1 (psia)", value=16.94, format="%.2f")

    with col2:
        t_gas = st.number_input("Gas Temp (°R)", value=564.67, format="%.2f")
        t_wall = st.number_input("Wall Temp (°R)", value=1560.0, format="%.1f")
        k = st.number_input("Spec. Heat Ratio (k)", value=1.2, format="%.2f")

    if st.button("HESAPLA", type="primary"):
        try:
            a_req, f_prime = calculate_fire_unwetted_area(area, p1_psia, t_gas, t_wall, k)
            from core.valve_selection import select_orifice
            letter, sel_area = select_orifice(a_req)
            st.markdown("### Sonuçlar")
            r1, r2, r3 = st.columns(3)
            r1.metric("F' Factor", f"{f_prime:.5f}")
            r2.metric("Gerekli Alan (sq.inch)", f"{a_req:.4f}")
            r3.metric("Seçilen Orifis", f"{letter} ({sel_area} sq.in)")
            st.markdown("### Uygun Ticari Vanalar (Vendor DB)")
            valves = get_vendor_valves(letter)
            if valves:
                render_vendor_table(valves)
            else:
                st.info("Bu orifis için veritabanında ticari vana bulunamadı.")
        except Exception as e:
            st.error(f"Hesaplama hatası: {e}")

elif page == "6. Thermal Expansion (Termal Genleşme)":
    st.markdown("### Girdiler (Inputs)")
    col1, col2 = st.columns(2)

    with col1:
        h_unit = st.selectbox("Heat Transfer Unit", ["BTU/h", "kW", "kcal/h"])
        if h_unit == "kW":
            h_kw = st.number_input("Heat Transfer (kW)", value=0.615, format="%.3f")
            h = kw_to_btu_h(h_kw)
        elif h_unit == "kcal/h":
            h_kcal = st.number_input("Heat Transfer (kcal/h)", value=529.2, format="%.1f")
            h = kcal_h_to_btu_h(h_kcal)
        else:
            h = st.number_input("Heat Transfer (BTU/h)", value=2100.0, format="%.1f")

        b = st.number_input("Expansion Coeff (B) [1/°F]", value=0.0005, format="%.6f")
        g = st.number_input("Specific Gravity (G)", value=0.85, format="%.2f")

    with col2:
        c = st.number_input("Specific Heat (C) [Btu/lb°F]", value=0.599, format="%.3f")
        mu_cp = st.number_input("Viscosity (cP)", value=51.0, format="%.1f")

        p1_unit = st.selectbox("P1 Unit", ["psia", "barg"], key="te_p1")
        if p1_unit == "barg":
            p1_barg = st.number_input("Relieving Pressure P1 (barg)", value=0.64, format="%.2f")
            p1_psia = barg_to_psia(p1_barg)
        else:
            p1_psia = st.number_input("Relieving Pressure P1 (psia)", value=16.94, format="%.2f")

        p2_unit = st.selectbox("P2 Unit", ["psia", "barg"], key="te_p2")
        if p2_unit == "barg":
            p2_barg = st.number_input("Back Pressure P2 (barg)", value=0.5, format="%.2f")
            p2_psia = barg_to_psia(p2_barg)
        else:
            p2_psia = st.number_input("Back Pressure P2 (psia)", value=1.0, format="%.2f")

    if st.button("HESAPLA", type="primary"):
        try:
            q_gpm = calculate_thermal_expansion_load(b, h, g, c)
            st.metric("Relief Load (US GPM)", f"{q_gpm:.3f}")
            res = calculate_liquid_relief_area(q_gpm, p1_psia, p2_psia, g, mu_cp)
            letter = display_results(res)
            st.markdown("### Uygun Ticari Vanalar (Vendor DB)")
            valves = get_vendor_valves(letter)
            if valves:
                render_vendor_table(valves)
            else:
                st.info("Bu orifis için veritabanında ticari vana bulunamadı.")
        except Exception as e:
            st.error(f"Hesaplama hatası: {e}")

else:
    st.markdown("### Hakkında")
    st.write("PSV Sizing Suite - Gelişmiş Web Tabanlı Mühendislik Platformu v2.2")
    st.write("Hesaplamalar API 520 Bölüm 1 ve API 521 yönergelerine göre yapılmaktadır.")
    st.write("6 modül: Liquid Relief, Gas/Vapor Relief, Two-Phase Flashing, Fire Wetted, Fire Unwetted, Thermal Expansion")
