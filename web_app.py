import streamlit as st
import html

from core.liquid_relief import calculate_liquid_relief_area
from core.gas_relief import calculate_gas_relief_area
from core.two_phase import calculate_two_phase_area, calculate_omega_flashing
from core.vendor_catalog import get_vendor_valves


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

st.set_page_config(page_title="PSV Sizing Suite v2.1", layout="wide")

st.sidebar.title("PSV Sizing Suite")
st.sidebar.markdown("Mühendislik Hesaplama Platformu (v2.1)")

page = st.sidebar.radio("Modül Seçimi", [
    "1. Liquid Relief (Sıvı Tahliye)", 
    "2. Gas/Vapor Relief (Gaz Tahliye)", 
    "3. Two-Phase Flashing (İki Fazlı)",
    "Hakkında"
])

st.title(page)

if page == "1. Liquid Relief (Sıvı Tahliye)":
    st.markdown("### Girdiler (Inputs)")
    col1, col2 = st.columns(2)
    
    with col1:
        q_gpm = st.number_input("Flow Rate (US gpm)", value=60.0, format="%.2f")
        p1_psia = st.number_input("Relieving Pressure P1 (psia)", value=52.8, format="%.2f")
        p2_psia = st.number_input("Back Pressure P2 (psia)", value=1.0, format="%.2f")
        
    with col2:
        g = st.number_input("Specific Gravity (G)", value=1.1, format="%.2f")
        mu_cp = st.number_input("Viscosity (cP)", value=1.0, format="%.2f")
        num_valves = st.number_input("Number of Parallel Valves", min_value=1, value=1, step=1)
        
    if st.button("HESAPLA", type="primary"):
        res = calculate_liquid_relief_area(q_gpm, p1_psia, p2_psia, g, mu_cp, num_valves)
        
        st.markdown("### Sonuçlar")
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("Gerekli Alan (sq.inch)", f"{res['Required_Area_Final_sqin']:.4f}")
        res_col2.metric("Seçilen Orifis", f"{res['Selected_Orifice_Letter']} ({res['Selected_Orifice_Area_sqin']} sq.in)")
        res_col3.metric("Reynolds & Kv", f"Re: {res['Reynolds_Number']:.1f} | Kv: {res['Kv']:.3f}")
        
        st.markdown("### Uygun Ticari Vanalar (Vendor DB)")
        valves = get_vendor_valves(res['Selected_Orifice_Letter'])
        if valves:
            render_vendor_table(valves)
        else:
            st.info("Bu orifis için veritabanında ticari vana bulunamadı veya Paralel Vana sayısı yetersiz.")

elif page == "2. Gas/Vapor Relief (Gaz Tahliye)":
    st.markdown("### Girdiler (Inputs)")
    col1, col2 = st.columns(2)
    
    with col1:
        w_lb_h = st.number_input("Mass Flow Rate (lb/h)", value=9633.0, format="%.1f")
        p1_psia = st.number_input("Relieving Pressure P1 (psia)", value=15.4, format="%.2f")
        p2_psia = st.number_input("Back Pressure P2 (psia)", value=1.2, format="%.2f")
        t_rankine = st.number_input("Relieving Temp (Rankine)", value=554.0, format="%.1f")
        
    with col2:
        z = st.number_input("Compressibility (Z)", value=0.85, format="%.3f")
        mw = st.number_input("Molecular Weight (MW)", value=21.0, format="%.1f")
        k = st.number_input("Specific Heat Ratio (k)", value=1.3, format="%.2f")
        num_valves = st.number_input("Number of Parallel Valves", min_value=1, value=1, step=1)
        
    if st.button("HESAPLA", type="primary"):
        res = calculate_gas_relief_area(w_lb_h, p1_psia, p2_psia, t_rankine, z, mw, k, num_valves)
        
        st.markdown("### Sonuçlar")
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("Gerekli Alan (sq.inch)", f"{res['Required_Area_sqin']:.4f}")
        res_col2.metric("Seçilen Orifis", f"{res['Selected_Orifice_Letter']} ({res['Selected_Orifice_Area_sqin']} sq.in)")
        res_col3.metric("Akış Rejimi", res['Flow_Type'])
        
        st.markdown("### Uygun Ticari Vanalar (Vendor DB)")
        valves = get_vendor_valves(res['Selected_Orifice_Letter'])
        if valves:
            render_vendor_table(valves)
        else:
            st.info("Bu orifis için veritabanında ticari vana bulunamadı veya Paralel Vana sayısı yetersiz.")

elif page == "3. Two-Phase Flashing (İki Fazlı)":
    st.markdown("### Girdiler (Inputs)")
    col1, col2 = st.columns(2)
    
    with col1:
        w_lb_h = st.number_input("Mass Flow Rate (lb/h)", value=466259.5, format="%.1f")
        p0_psia = st.number_input("Relieving Pressure P0 (psia)", value=136.14, format="%.2f")
        p_back = st.number_input("Back Pressure (psia)", value=14.0, format="%.2f")
        
    with col2:
        v0 = st.number_input("Specific Vol at Inlet (v0)", value=0.00841, format="%.5f")
        v9 = st.number_input("Specific Vol at 90% P0 (v9)", value=0.00901, format="%.5f")
        kd = st.number_input("Discharge Coeff (Kd)", value=0.85, format="%.2f")
        num_valves = st.number_input("Number of Parallel Valves", min_value=1, value=1, step=1)

    if st.button("HESAPLA", type="primary"):
        omega = calculate_omega_flashing(v0, v9)
        res = calculate_two_phase_area(w_lb_h, p0_psia, p_back, v0, omega, kd, num_valves)
        
        st.markdown("### Sonuçlar")
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("Gerekli Alan (sq.inch)", f"{res['Required_Area_sqin']:.4f}")
        res_col2.metric("Seçilen Orifis", f"{res['Selected_Orifice_Letter']} ({res['Selected_Orifice_Area_sqin']} sq.in)")
        res_col3.metric("Omega (w)", f"{res['Omega']:.3f}")
        
        st.markdown("### Uygun Ticari Vanalar (Vendor DB)")
        valves = get_vendor_valves(res['Selected_Orifice_Letter'])
        if valves:
            render_vendor_table(valves)
        else:
            st.info("Bu orifis için veritabanında ticari vana bulunamadı veya Paralel Vana sayısı yetersiz.")

else:
    st.markdown("### Hakkında")
    st.write("PSV Sizing Suite - Gelişmiş Web Tabanlı Mühendislik Platformu.")
    st.write("Hesaplamalar API 520 Bölüm 1 yönergelerine göre yapılmaktadır.")
