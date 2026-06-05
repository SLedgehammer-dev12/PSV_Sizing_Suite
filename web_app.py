import streamlit as st
import html
import math
from typing import Dict, Any

from core.liquid_relief import calculate_liquid_relief_area
from core.gas_relief import calculate_gas_relief_area
from core.two_phase import calculate_two_phase_area, calculate_omega_flashing
from core.thermo_props import calculate_two_phase_omega_coolprop, get_coolprop_fluids, calculate_mixture_properties
from core.fire_scenarios import calculate_fire_wetted_load, calculate_fire_unwetted_area
from core.piping import calculate_inlet_pressure_drop, check_inlet_rule
from core.vendor_catalog import get_vendor_valves
from core import convert, c_to_rankine, barg_to_psia, psia_to_barg, gpm_to_m3_h, kg_h_to_lb_h

# Page config
st.set_page_config(
    page_title="PSV Sizing Suite - Gelişmiş Mühendislik Platformu",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling injection
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        
        /* Font configuration */
        html, body, [class*="css"], .stMarkdown, p, div, label, span, button {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }
        
        /* Main title styling */
        .main-title {
            background: linear-gradient(135deg, #1e293b, #0f172a);
            padding: 2.5rem;
            border-radius: 16px;
            color: #ffffff;
            margin-bottom: 2rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
            position: relative;
            overflow: hidden;
        }
        .main-title::after {
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, rgba(0, 0, 0, 0) 70%);
            border-radius: 50%;
        }
        .main-title h1 {
            color: #ffffff !important;
            font-weight: 800 !important;
            margin: 0;
            font-size: 2.5rem !important;
            letter-spacing: -0.05em;
        }
        .main-title p {
            color: #94a3b8 !important;
            margin: 0.5rem 0 0 0;
            font-size: 1.1rem;
            font-weight: 400;
        }
        
        /* Card styling */
        .result-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 1.75rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .result-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
        }
        .result-card h4 {
            color: #0f172a !important;
            font-weight: 700;
            margin-top: 0;
            margin-bottom: 1rem;
            font-size: 1.2rem;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 0.50rem;
        }
        
        /* Accent metrics container */
        .metric-accent {
            background: linear-gradient(135deg, #eff6ff, #dbeafe);
            border: 1px solid #bfdbfe;
            border-radius: 12px;
            padding: 1.25rem;
            text-align: center;
            margin-top: 1rem;
        }
        .metric-accent-title {
            font-size: 0.85rem;
            color: #1e40af;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.05em;
        }
        .metric-accent-value {
            font-size: 2.25rem;
            color: #1d4ed8;
            font-weight: 800;
            margin-top: 0.25rem;
            letter-spacing: -0.02em;
        }
        
        /* Status labels */
        .status-badge {
            display: inline-block;
            padding: 0.35rem 0.75rem;
            border-radius: 9999px;
            font-weight: 700;
            font-size: 0.85rem;
        }
        .status-pass {
            background-color: #dcfce7;
            color: #15803d;
            border: 1px solid #bbf7d0;
        }
        .status-fail {
            background-color: #fee2e2;
            color: #b91c1c;
            border: 1px solid #fecaca;
        }
        
        /* Forms container */
        .stNumberInput, .stTextInput, .stSelectbox {
            margin-bottom: 0.75rem !important;
        }
        
    </style>
""", unsafe_allow_html=True)

# Helper function to render a premium vendor table
def render_vendor_table(valves):
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
                f'onclick="return confirm(&quot;{confirm_message}&quot;);">Sayfayı Aç</a>'
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
        font-size: 0.9rem;
        margin-top: 1rem;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
      }}
      .vendor-table th, .vendor-table td {{
        padding: 0.75rem 1rem;
        text-align: left;
        vertical-align: middle;
      }}
      .vendor-table th {{
        background: #f8fafc;
        font-weight: 700;
        color: #475569;
        border-bottom: 2px solid #e2e8f0;
      }}
      .vendor-table td {{
        border-bottom: 1px solid #f1f5f9;
        color: #0f172a;
      }}
      .vendor-table tr:hover {{
        background: #f8fafc;
      }}
      .vendor-table a {{
        color: #2563eb;
        font-weight: 600;
        text-decoration: none;
      }}
      .vendor-table a:hover {{
        text-decoration: underline;
      }}
      .vendor-table .muted {{
        color: #94a3b8;
      }}
    </style>
    <table class="vendor-table">
      <thead><tr>{headers}</tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)


# Sidebar Module Selector
st.sidebar.markdown("### 🛡️ Navigasyon")
page = st.sidebar.radio("Hesaplama Modülü Seçimi", [
    "1. Liquid Relief (Sıvı Tahliye)", 
    "2. Gas/Vapor Relief (Gaz/Buhar Tahliye)", 
    "3. Two-Phase Flashing (İki Fazlı Akış)",
    "4. Fire Scenario (Yangın Senaryosu - API 521)",
    "5. Piping Pressure Drop (Tesisat Analizi)",
    "Hakkında"
])

st.sidebar.markdown("---")
st.sidebar.markdown("### 📏 Birim Sistemi")
unit_system = st.sidebar.radio("Birim Seçimi", ["SI (Metrik)", "USC (Amerikan)"])
is_si = (unit_system == "SI (Metrik)")

st.sidebar.markdown("---")
st.sidebar.markdown("**Standartlar:**\n- API 520 Part I & II\n- API 521\n- API 526\n- ASME Sec VIII")
st.sidebar.markdown("**Versiyon:** `v2.3.0-premium`")

# Render header
st.markdown(f"""
    <div class="main-title">
        <h1>{page}</h1>
        <p>API 520/521/526 Standartlarına Uygun Sizing Suite</p>
    </div>
""", unsafe_allow_html=True)


# 1. LIQUID RELIEF
if page == "1. Liquid Relief (Sıvı Tahliye)":
    st.markdown("### Giriş Parametreleri (Inputs)")
    col1, col2 = st.columns(2)
    
    with col1:
        if is_si:
            q_input = st.number_input("Volümetrik Debi (L/min)", min_value=0.4, value=227.1, format="%.1f")
            p1_input = st.number_input("Rölyef Basıncı P1 (barg)", min_value=0.01, value=6.9, format="%.2f")
            p2_input = st.number_input("Toplam Karşı Basınç P2 (barg)", min_value=0.0, value=0.0, format="%.2f")
            q_gpm = convert(q_input, "L/min", "gpm")
            p1_psia = convert(p1_input, "barg", "psia")
            p2_psia = convert(p2_input, "barg", "psia")
        else:
            q_gpm = st.number_input("Volümetrik Debi (US gpm)", min_value=0.1, value=60.0, format="%.2f")
            p1_psia = st.number_input("Rölyef Basıncı P1 (psia)", min_value=14.7, value=114.7, format="%.2f")
            p2_psia = st.number_input("Toplam Karşı Basınç P2 (psia)", min_value=14.7, value=14.7, format="%.2f")
            
        valve_type = st.selectbox("Vana Tipi", ["conventional", "balanced_bellows", "pilot"])

    with col2:
        g = st.number_input("Spesifik Yerçekimi (SG / Su=1)", min_value=0.01, value=1.0, format="%.3f")
        mu_cp = st.number_input("Dinamik Viskozite (cP)", min_value=0.01, value=1.0, format="%.2f")
        num_valves = st.number_input("Paralel Vana Sayısı", min_value=1, value=1, step=1)
        overpressure_pct = st.number_input("Müsaade Edilen Aşırı Basınç (%)", min_value=1.0, value=10.0, format="%.1f")

    if st.button("HESAPLA", type="primary", use_container_width=True):
        try:
            # Set pressure calc
            sp_psig = (p1_psia - 14.6959) / (1.0 + overpressure_pct / 100.0)
            
            res = calculate_liquid_relief_area(
                q_gpm=q_gpm, p1_psia=p1_psia, p2_psia=p2_psia, 
                g=g, mu_cp=mu_cp, num_valves=num_valves
            )
            
            st.markdown("### Hesaplama Sonuçları")
            res_col1, res_col2 = st.columns(2)
            
            with res_col1:
                sp_display = sp_psig / 14.50377 if is_si else sp_psig
                sp_label = "barg" if is_si else "psig"
                
                area_req = convert(res['Required_Area_Final_sqin'], "sqin", "mm2") if is_si else res['Required_Area_Final_sqin']
                area_label = "mm²" if is_si else "sq.in"

                st.markdown(f"""
                    <div class="result-card">
                        <h4>Mühendislik Sonuçları</h4>
                        <table style="width:100%; border:none;">
                            <tr><td style="font-weight:600; padding:6px 0;">Tahmini Set Basıncı:</td><td style="text-align:right;">{sp_display:.2f} {sp_label}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Sıvı Yoğunluğu (SG):</td><td style="text-align:right;">{g:.3f}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Reynolds Sayısı (Re):</td><td style="text-align:right;">{res['Reynolds_Number']:.1f}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Viskozite Düzeltme (Kv):</td><td style="text-align:right;">{res['Kv']:.3f}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Gerekli Orifis Alanı (Vana Başına):</td><td style="text-align:right; font-weight:700; color:#1d4ed8;">{area_req:.4f} {area_label}</td></tr>
                        </table>
                    </div>
                """, unsafe_allow_html=True)
                
            with res_col2:
                selected_area = convert(res['Selected_Orifice_Area_sqin'], "sqin", "mm2") if is_si else res['Selected_Orifice_Area_sqin']
                selected_area_label = "mm²" if is_si else "sq.in"

                st.markdown(f"""
                    <div class="result-card" style="height: 100%; display: flex; flex-direction: column; justify-content: center;">
                        <h4>Seçilen Standart Orifis</h4>
                        <p style="text-align:center; margin-bottom:0.25rem; font-size:0.9rem; color:#64748b; font-weight:600;">API 526 Harf Sınıfı</p>
                        <div class="metric-accent">
                            <div class="metric-accent-title">Seçilen Orifis Harfi ve Alanı</div>
                            <div class="metric-accent-value">{res['Selected_Orifice_Letter']}</div>
                            <div style="font-size: 1.1rem; color:#1e40af; font-weight:700; margin-top:0.25rem;">{selected_area:.4f} {selected_area_label}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("### Uygun Ticari Vanalar (API 526 Standart Modelleri)")
            valves = get_vendor_valves(res['Selected_Orifice_Letter'])
            if valves:
                render_vendor_table(valves)
            else:
                st.info("Seçilen orifis için veritabanında ticari vana bulunamadı.")
        except Exception as e:
            st.error(f"Hata oluştu: {str(e)}")


# 2. GAS/VAPOR RELIEF
elif page == "2. Gas/Vapor Relief (Gaz/Buhar Tahliye)":
    st.markdown("### Giriş Parametreleri (Inputs)")
    col1, col2 = st.columns(2)
    
    with col1:
        if is_si:
            w_input = st.number_input("Kütlesel Debi (kg/h)", min_value=0.1, value=4535.9, format="%.1f")
            p1_input = st.number_input("Rölyef Basıncı P1 (barg)", min_value=0.01, value=5.9, format="%.2f")
            p2_input = st.number_input("Toplam Karşı Basınç P2 (barg)", min_value=0.0, value=0.0, format="%.2f")
            w_lb_h = convert(w_input, "kg/h", "lb/h")
            p1_psia = convert(p1_input, "barg", "psia")
            p2_psia = convert(p2_input, "barg", "psia")
        else:
            w_lb_h = st.number_input("Kütlesel Debi (lb/h)", min_value=0.1, value=10000.0, format="%.1f")
            p1_psia = st.number_input("Rölyef Basıncı P1 (psia)", min_value=14.7, value=100.0, format="%.2f")
            p2_psia = st.number_input("Toplam Karşı Basınç P2 (psia)", min_value=14.7, value=14.7, format="%.2f")
            
        valve_type = st.selectbox("Vana Tipi", ["conventional", "balanced_bellows"])
        overpressure_pct = st.number_input("Aşırı Basınç (%)", min_value=1.0, value=10.0, format="%.1f")

    with col2:
        if is_si:
            t_input = st.number_input("Rölyef Sıcaklığı (°C)", min_value=-273.15, value=37.8, format="%.1f")
            t_rankine = convert(t_input, "degC", "degR")
        else:
            t_rankine = st.number_input("Rölyef Sıcaklığı (Rankine)", min_value=1.0, value=560.0, format="%.1f")
            
        z = st.number_input("Sıkışabilirlik Faktörü (Z)", min_value=0.01, max_value=2.0, value=1.0, format="%.3f")
        mw = st.number_input("Moleküler Ağırlık (MW g/mol)", min_value=1.0, value=28.0, format="%.2f")
        k = st.number_input("Spesifik Isı Oranı (k = Cp/Cv)", min_value=1.01, value=1.4, format="%.2f")
        num_valves = st.number_input("Paralel Vana Sayısı", min_value=1, value=1, step=1)

    # Alternate/verification method selections
    st.markdown("---")
    st.markdown("#### ⚙️ Buhar (Napier) Entegrasyon Seçenekleri")
    is_steam = st.checkbox("Akışkan Su Buharı (Steam - Napier Denklemi)", value=False)
    use_napier = False
    if is_steam:
        method_choice = st.selectbox("Hesaplama Yöntemi Seçimi", ["Standart Gaz/Buhar Denklemi", "Napier Buhar Denklemi"])
        use_napier = (method_choice == "Napier Buhar Denklemi")

    # CoolProp properties shortcut helper
    with st.expander("🧪 CoolProp Özellik Sorgulama"):
        st.markdown("Akışkan özelliklerini otomatik olarak hesaplamak için CoolProp'u kullanın.")
        fluids = get_coolprop_fluids()
        selected_fluid = st.selectbox("Akışkan Seçimi", fluids)
        t_c = st.number_input("Sıcaklık (°C)", value=150.0)
        p_barg = st.number_input("Basınç (barg)", value=10.0)
        if st.button("Özellikleri Getir ve Formu Doldur"):
            try:
                p_psia_val = barg_to_psia(p_barg)
                t_r_val = c_to_rankine(t_c)
                composition = {selected_fluid: 1.0}
                z_cp, mw_cp, k_cp = calculate_mixture_properties(composition, t_r_val, p_psia_val)
                
                st.session_state["gas_z"] = z_cp
                st.session_state["gas_mw"] = mw_cp
                st.session_state["gas_k"] = k_cp
                st.session_state["gas_tr"] = t_r_val
                st.success("Özellikler başarıyla yüklendi! Lütfen formu kontrol edin.")
            except Exception as ex:
                st.error(f"CoolProp sorgulama hatası: {ex}")

    # Use session states if populated
    if "gas_z" in st.session_state:
        z = st.number_input("Sıkışabilirlik Faktörü (Z)", min_value=0.01, max_value=2.0, value=st.session_state["gas_z"], format="%.3f", key="gas_z_input")
    if "gas_mw" in st.session_state:
        mw = st.number_input("Moleküler Ağırlık (MW g/mol)", min_value=1.0, value=st.session_state["gas_mw"], format="%.2f", key="gas_mw_input")
    if "gas_k" in st.session_state:
        k = st.number_input("Spesifik Isı Oranı (k = Cp/Cv)", min_value=1.01, value=st.session_state["gas_k"], format="%.2f", key="gas_k_input")
    if "gas_tr" in st.session_state:
        t_rankine = st.number_input("Rölyef Sıcaklığı (Rankine)", min_value=1.0, value=st.session_state["gas_tr"], format="%.1f", key="gas_tr_input")

    if st.button("HESAPLA", type="primary", use_container_width=True):
        try:
            sp_psig = (p1_psia - 14.6959) / (1.0 + overpressure_pct / 100.0)
            
            res = calculate_gas_relief_area(
                w_lb_h=w_lb_h, p1_psia=p1_psia, p2_psia=p2_psia,
                t_rankine=t_rankine, z=z, mw=mw, k=k,
                valve_type=valve_type, set_pressure_psig=sp_psig,
                num_valves=num_valves, overpressure_pct=overpressure_pct,
                is_steam=is_steam, use_napier=use_napier
            )
            
            st.markdown("### Hesaplama Sonuçları")
            res_col1, res_col2 = st.columns(2)
            
            with res_col1:
                sp_display = sp_psig / 14.50377 if is_si else sp_psig
                sp_label = "barg" if is_si else "psig"
                
                p_cf_display = (res['Critical_Pressure_psia'] - 14.6959) / 14.50377 if is_si else res['Critical_Pressure_psia']
                p_cf_label = "barg" if is_si else "psia"
                
                area_req = convert(res['Required_Area_sqin'], "sqin", "mm2") if is_si else res['Required_Area_sqin']
                area_label = "mm²" if is_si else "sq.in"

                st.markdown(f"""
                    <div class="result-card">
                        <h4>Mühendislik Sonuçları</h4>
                        <table style="width:100%; border:none;">
                            <tr><td style="font-weight:600; padding:6px 0;">Tahmini Set Basıncı:</td><td style="text-align:right;">{sp_display:.2f} {sp_label}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Akış Rejimi:</td><td style="text-align:right; font-weight:700; color:#1e293b;">{res['Flow_Type']}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Kritik Basınç Sınırı:</td><td style="text-align:right;">{p_cf_display:.2f} {p_cf_label}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Kb Katsayısı:</td><td style="text-align:right;">{res.get('Kb_Factor', 1.0) if 'Kb_Factor' in res else res.get('Kb', 1.0):.3f}</td></tr>
                            {"<tr><td style='font-weight:600; padding:6px 0;'>Napier Kn Katsayısı:</td><td style='text-align:right;'>" + f"{res['Kn']:.3f}" + "</td></tr>" if 'Kn' in res else ""}
                            {"<tr><td style='font-weight:600; padding:6px 0;'>Napier Ksh Katsayısı:</td><td style='text-align:right;'>" + f"{res['Ksh']:.3f}" + "</td></tr>" if 'Ksh' in res else ""}
                            <tr><td style="font-weight:600; padding:6px 0;">Gerekli Orifis Alanı (Vana Başına):</td><td style="text-align:right; font-weight:700; color:#1d4ed8;">{area_req:.4f} {area_label}</td></tr>
                        </table>
                    </div>
                """, unsafe_allow_html=True)
                
            with res_col2:
                selected_area = convert(res['Selected_Orifice_Area_sqin'], "sqin", "mm2") if is_si else res['Selected_Orifice_Area_sqin']
                selected_area_label = "mm²" if is_si else "sq.in"

                st.markdown(f"""
                    <div class="result-card" style="height: 100%; display: flex; flex-direction: column; justify-content: center;">
                        <h4>Seçilen Standart Orifis</h4>
                        <p style="text-align:center; margin-bottom:0.25rem; font-size:0.9rem; color:#64748b; font-weight:600;">API 526 Harf Sınıfı</p>
                        <div class="metric-accent">
                            <div class="metric-accent-title">Seçilen Orifis Harfi ve Alanı</div>
                            <div class="metric-accent-value">{res['Selected_Orifice_Letter']}</div>
                            <div style="font-size: 1.1rem; color:#1e40af; font-weight:700; margin-top:0.25rem;">{selected_area:.4f} {selected_area_label}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
            if is_steam:
                verif_area_display = convert(res['Verification_Required_Area_sqin'], "sqin", "mm2") if is_si else res['Verification_Required_Area_sqin']
                verif_area_label = "mm²" if is_si else "sq.in"
                
                st.markdown(f"""
                    <div class="result-card" style="margin-top: 1rem; border-left: 4px solid #10b981; background-color: #f0fdf4;">
                        <h4 style="color: #065f46;">🔍 Kontrol / Doğrulama Hesaplaması</h4>
                        <p style="font-size: 0.9rem; margin-bottom: 0.5rem;">
                            Alternatif Yöntem: <strong>{res['Verification_Method']}</strong>
                        </p>
                        <table style="width:100%; border:none;">
                            <tr><td style="font-weight:600; padding:6px 0; color:#065f46;">Gerekli Orifis Alanı:</td><td style="text-align:right; font-weight:700; color:#047857;">{verif_area_display:.4f} {verif_area_label}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0; color:#065f46;">Seçilen Orifis Sınıfı:</td><td style="text-align:right; font-weight:700; color:#047857;">{res['Verification_Orifice_Letter']}</td></tr>
                        </table>
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown("### Uygun Ticari Vanalar")
            valves = get_vendor_valves(res['Selected_Orifice_Letter'])
            if valves:
                render_vendor_table(valves)
            else:
                st.info("Seçilen orifis için veritabanında ticari vana bulunamadı.")
        except Exception as e:
            st.error(f"Hata oluştu: {str(e)}")


# 3. TWO-PHASE FLASHING
elif page == "3. Two-Phase Flashing (İki Fazlı Akış)":
    st.markdown("### Giriş Parametreleri (Inputs)")
    
    calc_mode = st.radio("Hacim Hesaplama Modu", ["Otomatik (CoolProp İzentropik Flash)", "Manuel Hacim Girişi (DIERS)"], horizontal=True)
    
    col1, col2 = st.columns(2)
    
    if calc_mode == "Otomatik (CoolProp İzentropik Flash)":
        with col1:
            if is_si:
                w_input = st.number_input("Kütlesel Debi (kg/h)", min_value=0.1, value=45359.2, format="%.1f")
                p0_input = st.number_input("Rölyef Basıncı P0 (barg)", min_value=0.01, value=9.3, format="%.2f")
                p_back_input = st.number_input("Karşı Basınç (barg)", min_value=0.0, value=0.0, format="%.2f")
                w_lb_h = convert(w_input, "kg/h", "lb/h")
                p0_psia = convert(p0_input, "barg", "psia")
                p_back = convert(p_back_input, "barg", "psia")
            else:
                w_lb_h = st.number_input("Kütlesel Debi (lb/h)", min_value=0.1, value=100000.0, format="%.1f")
                p0_psia = st.number_input("Rölyef Basıncı P0 (psia)", min_value=14.7, value=150.0, format="%.2f")
                p_back = st.number_input("Karşı Basınç (psia)", min_value=14.7, value=14.7, format="%.2f")
                
            valve_type = st.selectbox("Vana Tipi", ["conventional", "balanced_bellows"])
            
        with col2:
            fluids = get_coolprop_fluids()
            selected_fluid = st.selectbox("İki Fazlı Akışkan", fluids)
            state_type = st.selectbox("Giriş Termodinamik Durumu", ["saturated_liquid", "subcooled_liquid", "two_phase"])
            
            t_rankine_input = 600.0
            x0_input = 0.0
            if state_type == "subcooled_liquid":
                t_c = st.number_input("İnlet Sıcaklığı (°C)", value=100.0)
                t_rankine_input = convert(t_c, "degC", "degR")
            elif state_type == "two_phase":
                x0_input = st.number_input("Giriş Buhar Kalitesi (x0)", min_value=0.0, max_value=1.0, value=0.1, step=0.01)
                
            num_valves = st.number_input("Paralel Vana Sayısı", min_value=1, value=1, step=1)

        # Advanced subcooled flashing parameters
        is_subcooled_flashing = False
        use_c23 = False
        p_sat_psia = 0.0
        if state_type == "subcooled_liquid":
            st.markdown("---")
            st.markdown("#### ⚙️ Alt-soğutulmuş Sıvı Flashing (PolyKin Modeli)")
            is_subcooled_flashing = st.checkbox("Alt-soğutulmuş Sıvı Flashing Entegrasyonu (API 520 C.2.3)", value=True)
            if is_subcooled_flashing:
                model_choice = st.selectbox("Hesaplama Modeli", ["Standart İki Fazlı Omega Metodu", "API 520 C.2.3 Flashing Modeli"])
                use_c23 = (model_choice == "API 520 C.2.3 Flashing Modeli")
                if is_si:
                    p_sat_input = st.number_input("Doyma Basıncı Ps (barg)", min_value=0.0, value=3.0, format="%.2f")
                    p_sat_psia = convert(p_sat_input, "barg", "psia")
                else:
                    p_sat_psia = st.number_input("Doyma Basıncı Ps (psia)", min_value=1.0, value=44.7, format="%.2f")

        if st.button("OTOMATİK HESAPLA", type="primary", use_container_width=True):
            try:
                comp = {selected_fluid: 1.0}
                # Run isentropic flash to find specific volumes
                coolprop_res = calculate_two_phase_omega_coolprop(
                    composition_dict=comp,
                    p0_psia=p0_psia,
                    state_type=state_type,
                    t_rankine=t_rankine_input,
                    x0=x0_input
                )
                
                v0 = coolprop_res["v0_ft3_lb"]
                v9 = coolprop_res["v9_ft3_lb"]
                omega = coolprop_res["omega"]
                
                # Execute sizing
                res = calculate_two_phase_area(
                    w_lb_h=w_lb_h, p0_psia=p0_psia, p_back_psia=p_back,
                    v0_ft3_lb=v0, omega=omega,
                    valve_type=valve_type, num_valves=num_valves,
                    is_subcooled_flashing=is_subcooled_flashing,
                    use_c23=use_c23,
                    p_sat_psia=p_sat_psia
                )
                
                st.markdown("### Hesaplama Sonuçları")
                res_col1, res_col2 = st.columns(2)
                
                with res_col1:
                    v0_display = convert(v0, "ft3/lb", "m3/kg") if is_si else v0
                    v9_display = convert(v9, "ft3/lb", "m3/kg") if is_si else v9
                    v_label = "m³/kg" if is_si else "ft³/lb"
                    
                    pcf_display = (res['Critical_Pressure_psia'] - 14.6959) / 14.50377 if is_si else res['Critical_Pressure_psia']
                    pcf_label = "barg" if is_si else "psia"

                    st.markdown(f"""
                        <div class="result-card">
                            <h4>Otomatik Fiziksel Özellikler</h4>
                            <table style="width:100%; border:none;">
                                <tr><td style="font-weight:600; padding:6px 0;">Giriş Özgül Hacmi (v0):</td><td style="text-align:right;">{v0_display:.5f} {v_label}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">90% P0 Özgül Hacmi (v9):</td><td style="text-align:right;">{v9_display:.5f} {v_label}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">Omega (w) Parametresi:</td><td style="text-align:right; font-weight:700; color:#1e293b;">{res['Omega']:.3f}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">Kritik Basınç Oranı (hc):</td><td style="text-align:right;">{res['Critical_Pressure_Ratio_hc']:.4f}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">Kritik Akış Basıncı:</td><td style="text-align:right;">{pcf_display:.2f} {pcf_label}</td></tr>
                            </table>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with res_col2:
                    g_display = res['Mass_Flux_G_lb_s_ft2'] / 0.204816 if is_si else res['Mass_Flux_G_lb_s_ft2']
                    g_label = "kg/(s·m²)" if is_si else "lb/(s·ft²)"
                    
                    area_req = convert(res['Required_Area_sqin'], "sqin", "mm2") if is_si else res['Required_Area_sqin']
                    area_label = "mm²" if is_si else "sq.in"
                    
                    selected_area = convert(res['Selected_Orifice_Area_sqin'], "sqin", "mm2") if is_si else res['Selected_Orifice_Area_sqin']

                    st.markdown(f"""
                        <div class="result-card">
                            <h4>Boyutlandırma Sonuçları</h4>
                            <table style="width:100%; border:none;">
                                <tr><td style="font-weight:600; padding:6px 0;">Akış Rejimi:</td><td style="text-align:right; font-weight:700; color:#1e293b;">{res['Flow_Type']}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">Kütlesel Akı (G):</td><td style="text-align:right;">{g_display:.1f} {g_label}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">Bellows Kb Katsayısı:</td><td style="text-align:right;">{res['Kb']:.3f}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">Gerekli Orifis Alanı (Vana Başına):</td><td style="text-align:right; font-weight:700; color:#1d4ed8;">{area_req:.4f} {area_label}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">Seçilen Orifis Sınıfı:</td><td style="text-align:right; font-weight:700; color:#1d4ed8;">{res['Selected_Orifice_Letter']} ({selected_area:.4f} {area_label})</td></tr>
                            </table>
                        </div>
                    """, unsafe_allow_html=True)
                    
                if is_subcooled_flashing:
                    verif_area_display = convert(res['Verification_Required_Area_sqin'], "sqin", "mm2") if is_si else res['Verification_Required_Area_sqin']
                    verif_area_label = "mm²" if is_si else "sq.in"
                    
                    st.markdown(f"""
                        <div class="result-card" style="margin-top: 1rem; border-left: 4px solid #10b981; background-color: #f0fdf4;">
                            <h4 style="color: #065f46;">🔍 Kontrol / Doğrulama Hesaplaması</h4>
                            <p style="font-size: 0.9rem; margin-bottom: 0.5rem;">
                                Alternatif Yöntem: <strong>{res['Verification_Method']}</strong>
                            </p>
                            <table style="width:100%; border:none;">
                                <tr><td style="font-weight:600; padding:6px 0; color:#065f46;">Gerekli Orifis Alanı:</td><td style="text-align:right; font-weight:700; color:#047857;">{verif_area_display:.4f} {verif_area_label}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0; color:#065f46;">Seçilen Orifis Sınıfı:</td><td style="text-align:right; font-weight:700; color:#047857;">{res['Verification_Orifice_Letter']}</td></tr>
                            </table>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("### Uygun Ticari Vanalar")
                valves = get_vendor_valves(res['Selected_Orifice_Letter'])
                if valves:
                    render_vendor_table(valves)
                else:
                    st.info("Seçilen orifis için veritabanında ticari vana bulunamadı.")
            except Exception as e:
                st.error(f"Hesaplama hatası: {str(e)}")

    else:
        # Manual volume inputs
        with col1:
            if is_si:
                w_input = st.number_input("Kütlesel Debi (kg/h)", min_value=0.1, value=45359.2, format="%.1f")
                p0_input = st.number_input("Rölyef Basıncı P0 (barg)", min_value=0.01, value=9.3, format="%.2f")
                p_back_input = st.number_input("Karşı Basınç (barg)", min_value=0.0, value=0.0, format="%.2f")
                w_lb_h = convert(w_input, "kg/h", "lb/h")
                p0_psia = convert(p0_input, "barg", "psia")
                p_back = convert(p_back_input, "barg", "psia")
            else:
                w_lb_h = st.number_input("Kütlesel Debi (lb/h)", min_value=0.1, value=100000.0, format="%.1f")
                p0_psia = st.number_input("Rölyef Basıncı P0 (psia)", min_value=14.7, value=150.0, format="%.2f")
                p_back = st.number_input("Karşı Basınç (psia)", min_value=14.7, value=14.7, format="%.2f")
                
            num_valves = st.number_input("Paralel Vana Sayısı", min_value=1, value=1, step=1)
            
        with col2:
            if is_si:
                v0_input = st.number_input("İnlet Özgül Hacmi v0 (m³/kg)", min_value=0.00001, value=0.00112, format="%.6f")
                v9_input = st.number_input("90% P0'daki Özgül Hacim v9 (m³/kg)", min_value=0.00001, value=0.00137, format="%.6f")
                v0 = convert(v0_input, "m3/kg", "ft3/lb")
                v9 = convert(v9_input, "m3/kg", "ft3/lb")
            else:
                v0 = st.number_input("İnlet Özgül Hacmi v0 (ft³/lb)", min_value=0.0001, value=0.018, format="%.5f")
                v9 = st.number_input("90% P0'daki Özgül Hacim v9 (ft³/lb)", min_value=0.0001, value=0.022, format="%.5f")
                
            valve_type = st.selectbox("Vana Tipi", ["conventional", "balanced_bellows"], key="two_phase_manual_valve")
            overpressure_pct = st.number_input("Aşırı Basınç (%)", min_value=1.0, value=10.0, format="%.1f")

        # Advanced subcooled flashing parameters
        is_subcooled_flashing = False
        use_c23 = False
        p_sat_psia = 0.0
        st.markdown("---")
        st.markdown("#### ⚙️ Alt-soğutulmuş Sıvı Flashing (PolyKin Modeli)")
        is_subcooled_flashing = st.checkbox("Alt-soğutulmuş Sıvı Flashing Entegrasyonu (API 520 C.2.3)", value=False, key="manual_subcool_check")
        if is_subcooled_flashing:
            model_choice = st.selectbox("Hesaplama Modeli", ["Standart İki Fazlı Omega Metodu", "API 520 C.2.3 Flashing Modeli"], key="manual_model_select")
            use_c23 = (model_choice == "API 520 C.2.3 Flashing Modeli")
            if is_si:
                p_sat_input = st.number_input("Doyma Basıncı Ps (barg)", min_value=0.0, value=3.0, format="%.2f", key="manual_ps_input")
                p_sat_psia = convert(p_sat_input, "barg", "psia")
            else:
                p_sat_psia = st.number_input("Doyma Basıncı Ps (psia)", min_value=1.0, value=44.7, format="%.2f", key="manual_ps_input")

        if st.button("MANUEL HESAPLA", type="primary", use_container_width=True):
            try:
                omega = calculate_omega_flashing(v0, v9)
                res = calculate_two_phase_area(
                    w_lb_h=w_lb_h, p0_psia=p0_psia, p_back_psia=p_back,
                    v0_ft3_lb=v0, omega=omega,
                    valve_type=valve_type, num_valves=num_valves,
                    overpressure_pct=overpressure_pct,
                    is_subcooled_flashing=is_subcooled_flashing,
                    use_c23=use_c23,
                    p_sat_psia=p_sat_psia
                )
                
                st.markdown("### Hesaplama Sonuçları")
                res_col1, res_col2 = st.columns(2)
                
                with res_col1:
                    pcf_display = (res['Critical_Pressure_psia'] - 14.6959) / 14.50377 if is_si else res['Critical_Pressure_psia']
                    pcf_label = "barg" if is_si else "psia"

                    st.markdown(f"""
                        <div class="result-card">
                            <h4>Fiziksel Özellikler</h4>
                            <table style="width:100%; border:none;">
                                <tr><td style="font-weight:600; padding:6px 0;">Omega (w) Parametresi:</td><td style="text-align:right; font-weight:700; color:#1e293b;">{res['Omega']:.3f}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">Kritik Basınç Oranı (hc):</td><td style="text-align:right;">{res['Critical_Pressure_Ratio_hc']:.4f}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">Kritik Akış Basıncı:</td><td style="text-align:right;">{pcf_display:.2f} {pcf_label}</td></tr>
                            </table>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with res_col2:
                    g_display = res['Mass_Flux_G_lb_s_ft2'] / 0.204816 if is_si else res['Mass_Flux_G_lb_s_ft2']
                    g_label = "kg/(s·m²)" if is_si else "lb/(s·ft²)"
                    
                    area_req = convert(res['Required_Area_sqin'], "sqin", "mm2") if is_si else res['Required_Area_sqin']
                    area_label = "mm²" if is_si else "sq.in"
                    
                    selected_area = convert(res['Selected_Orifice_Area_sqin'], "sqin", "mm2") if is_si else res['Selected_Orifice_Area_sqin']

                    st.markdown(f"""
                        <div class="result-card">
                            <h4>Boyutlandırma Sonuçları</h4>
                            <table style="width:100%; border:none;">
                                <tr><td style="font-weight:600; padding:6px 0;">Akış Rejimi:</td><td style="text-align:right; font-weight:700; color:#1e293b;">{res['Flow_Type']}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">Kütlesel Akı (G):</td><td style="text-align:right;">{g_display:.1f} {g_label}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">Bellows Kb Katsayısı:</td><td style="text-align:right;">{res['Kb']:.3f}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">Gerekli Orifis Alanı (Vana Başına):</td><td style="text-align:right; font-weight:700; color:#1d4ed8;">{area_req:.4f} {area_label}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0;">Seçilen Orifis Sınıfı:</td><td style="text-align:right; font-weight:700; color:#1d4ed8;">{res['Selected_Orifice_Letter']} ({selected_area:.4f} {area_label})</td></tr>
                            </table>
                        </div>
                    """, unsafe_allow_html=True)
                    
                if is_subcooled_flashing:
                    verif_area_display = convert(res['Verification_Required_Area_sqin'], "sqin", "mm2") if is_si else res['Verification_Required_Area_sqin']
                    verif_area_label = "mm²" if is_si else "sq.in"
                    
                    st.markdown(f"""
                        <div class="result-card" style="margin-top: 1rem; border-left: 4px solid #10b981; background-color: #f0fdf4;">
                            <h4 style="color: #065f46;">🔍 Kontrol / Doğrulama Hesaplaması</h4>
                            <p style="font-size: 0.9rem; margin-bottom: 0.5rem;">
                                Alternatif Yöntem: <strong>{res['Verification_Method']}</strong>
                            </p>
                            <table style="width:100%; border:none;">
                                <tr><td style="font-weight:600; padding:6px 0; color:#065f46;">Gerekli Orifis Alanı:</td><td style="text-align:right; font-weight:700; color:#047857;">{verif_area_display:.4f} {verif_area_label}</td></tr>
                                <tr><td style="font-weight:600; padding:6px 0; color:#065f46;">Seçilen Orifis Sınıfı:</td><td style="text-align:right; font-weight:700; color:#047857;">{res['Verification_Orifice_Letter']}</td></tr>
                            </table>
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("### Uygun Ticari Vanalar")
                valves = get_vendor_valves(res['Selected_Orifice_Letter'])
                if valves:
                    render_vendor_table(valves)
                else:
                    st.info("Seçilen orifis için veritabanında ticari vana bulunamadı.")
            except Exception as e:
                st.error(f"Hesaplama hatası: {str(e)}")


# 4. FIRE SCENARIO (API 521)
elif page == "4. Fire Scenario (Yangın Senaryosu - API 521)":
    st.markdown("### Giriş Parametreleri (Inputs) - API 521 Bölüm 4.4")
    col1, col2 = st.columns(2)
    
    with col1:
        if is_si:
            area_input = st.number_input("Islak Yüzey Alanı A (m²)", min_value=0.1, value=139.4, format="%.2f")
            a_wetted_sqft = convert(area_input, "m2", "sqft")
        else:
            a_wetted_sqft = st.number_input("Islak Yüzey Alanı A (sqft)", min_value=0.1, value=1500.0, format="%.1f")
            
        f_factor = st.selectbox("Çevre Faktörü F (API 521 Tablo 7)", [
            "bare (Çıplak Tank) - F = 1.0",
            "insulation_1_in (1 inç İzolasyon) - F = 0.15",
            "insulation_2_in (2 inç İzolasyon) - F = 0.07",
            "insulation_4_in (4 inç İzolasyon) - F = 0.03",
            "water_spray (Su Sprinkler) - F = 0.33",
            "drainage_1_in (1 inç Drenaj) - F = 0.5",
            "fireproofing (Yangın Yalıtımı) - F = 0.2"
        ])
        
        # Parse F factor value
        f_val = 1.0
        if "bare" in f_factor: f_val = 1.0
        elif "insulation_1" in f_factor: f_val = 0.15
        elif "insulation_2" in f_factor: f_val = 0.07
        elif "insulation_4" in f_factor: f_val = 0.03
        elif "water_spray" in f_factor: f_val = 0.33
        elif "drainage" in f_factor: f_val = 0.5
        elif "fireproofing" in f_factor: f_val = 0.2

    with col2:
        if is_si:
            latent_input = st.number_input("Buharlaşma Gizli Isısı (kJ/kg)", min_value=1.0, value=279.1, format="%.1f")
            heat_of_vap_btu_lb = convert(latent_input, "kJ/kg", "Btu/lb")
        else:
            heat_of_vap_btu_lb = st.number_input("Buharlaşma Gizli Isısı (Btu/lb)", min_value=1.0, value=120.0, format="%.1f")
            
        adequate_drainage = st.checkbox("Drenaj ve İtfaiye Altyapısı Var (C = 21000)", value=True)
        
        cap_area_label = "Alan Limitini Uygula (Max 260 m² / 2800 sqft Havuz Yangını)" if is_si else "Alan Limitini Uygula (Max 2800 sqft, Havuz Yangını Sınırı)"
        apply_area_cap = st.checkbox(cap_area_label, value=True)

    if st.button("YANGIN DEBİSİNİ HESAPLA", type="primary", use_container_width=True):
        try:
            cap_val = 2800.0 if apply_area_cap else None
            w_lb_h, q_btu_h = calculate_fire_wetted_load(
                a_wetted_sqft=a_wetted_sqft,
                f_factor=f_val,
                heat_of_vap_btu_lb=heat_of_vap_btu_lb,
                adequate_drainage=adequate_drainage,
                wetted_area_cap=cap_val
            )
            
            st.markdown("### Yangın Isı Geçişi ve Debi Sonucu")
            res_col1, res_col2 = st.columns(2)
            
            with res_col1:
                c_val = 21000.0 if adequate_drainage else 34500.0
                area_cap_val = min(a_wetted_sqft, 2800.0) if apply_area_cap else a_wetted_sqft
                
                if is_si:
                    c_display_val = c_val * 3.15459  # Btu/h/ft² to W/m²
                    c_display_label = "W/m²"
                    area_display_val = convert(area_cap_val, "sqft", "m2")
                    area_display_label = "m²"
                    q_display_val = q_btu_h / 3412.142
                    q_display_label = "kW"
                else:
                    c_display_val = c_val
                    c_display_label = "Btu/h/ft²"
                    area_display_val = area_cap_val
                    area_display_label = "sqft"
                    q_display_val = q_btu_h
                    q_display_label = "Btu/h"

                st.markdown(f"""
                    <div class="result-card">
                        <h4>Mühendislik Sonuçları</h4>
                        <table style="width:100%; border:none;">
                            <tr><td style="font-weight:600; padding:6px 0;">Isı Akı Sabiti (C):</td><td style="text-align:right;">{c_display_val:.0f} {c_display_label}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Çevre Katsayısı (F):</td><td style="text-align:right;">{f_val:.2f}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Efektif Çeper Alanı:</td><td style="text-align:right;">{area_display_val:.1f} {area_display_label}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Toplam Absorbe Isı Hızı (Q):</td><td style="text-align:right; font-weight:700; color:#1d4ed8;">{q_display_val:.0f} {q_display_label}</td></tr>
                        </table>
                    </div>
                """, unsafe_allow_html=True)
                
            with res_col2:
                flow_display = w_lb_h / 2.204623 if is_si else w_lb_h
                flow_label = "kg/h" if is_si else "lb/h"
                
                st.markdown(f"""
                    <div class="result-card" style="height: 100%; display: flex; flex-direction: column; justify-content: center;">
                        <h4>Gerekli Rölyef Kapasitesi</h4>
                        <p style="text-align:center; margin-bottom:0.25rem; font-size:0.9rem; color:#64748b; font-weight:600;">Kütlesel Buharlaşma Yükü</p>
                        <div class="metric-accent" style="background: linear-gradient(135deg, #fef2f2, #fee2e2); border:1px solid #fca5a5;">
                            <div class="metric-accent-title" style="color: #991b1b;">Tahliye Kütlesel Debisi</div>
                            <div class="metric-accent-value" style="color: #dc2626;">{flow_display:.1f}</div>
                            <div style="font-size: 1.1rem; color:#991b1b; font-weight:700; margin-top:0.25rem;">{flow_label}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
            # Quick button to fill Gaz/Buhar Sizing
            st.session_state["gas_w_fire"] = w_lb_h
            st.info(f"💡 Hesaplanan yangın yükü ({flow_display:.1f} {flow_label}) Gaz/Buhar boyutlandırma modülü için hafızaya alındı!")
            
        except Exception as e:
            st.error(f"Hata: {str(e)}")


# 5. PIPING PRESSURE DROP
elif page == "5. Piping Pressure Drop (Tesisat Analizi)":
    st.markdown("### Giriş Parametreleri (Inputs) - API 520 Part II")
    
    fluid_type = st.radio("Akışkan Tipi", ["Sıvı (Liquid)", "Gaz/Buhar (Gas)"], horizontal=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if fluid_type == "Sıvı (Liquid)":
            if is_si:
                flow_input = st.number_input("Volümetrik Debi (L/min)", min_value=0.1, value=567.8, format="%.1f")
                flow_gpm = convert(flow_input, "L/min", "gpm")
            else:
                flow_gpm = st.number_input("Volümetrik Debi (US gpm)", min_value=0.1, value=150.0, format="%.1f")
            flow_rate_lb_h = None
        else:
            if is_si:
                flow_input = st.number_input("Kütlesel Debi (kg/h)", min_value=0.1, value=6803.9, format="%.1f")
                flow_rate_lb_h = convert(flow_input, "kg/h", "lb/h")
            else:
                flow_rate_lb_h = st.number_input("Kütlesel Debi (lb/h)", min_value=0.1, value=15000.0, format="%.1f")
            flow_gpm = None
            
        if is_si:
            density_input = st.number_input("Akışkan Yoğunluğu (kg/m³)", min_value=0.1, value=1000.0 if fluid_type == "Sıvı (Liquid)" else 24.0, format="%.1f")
            fluid_density = density_input * 0.062428
            
            viscosity = st.number_input("Akışkan Dinamik Viskozitesi (cP)", min_value=0.001, value=1.0 if fluid_type == "Sıvı (Liquid)" else 0.018, format="%.4f")
            
            id_input = st.number_input("Boru İç Çapı ID (mm)", min_value=1.0, value=77.9, format="%.1f")
            pipe_id_in = id_input / 25.4
            
            len_input = st.number_input("Düz Boru Uzunluğu (m)", min_value=0.0, value=7.62, format="%.2f")
            pipe_length_ft = len_input / 0.3048
        else:
            fluid_density = st.number_input("Akışkan Yoğunluğu (lb/ft³)", min_value=0.01, value=62.4 if fluid_type == "Sıvı (Liquid)" else 1.5, format="%.3f")
            viscosity = st.number_input("Akışkan Dinamik Viskozitesi (cP)", min_value=0.001, value=1.0 if fluid_type == "Sıvı (Liquid)" else 0.018, format="%.4f")
            pipe_id_in = st.number_input("Boru İç Çapı ID (inç)", min_value=0.1, value=3.068, format="%.3f")
            pipe_length_ft = st.number_input("Düz Boru Uzunluğu (ft)", min_value=0.0, value=25.0, format="%.1f")

    with col2:
        fittings_90 = st.number_input("90° Dirsek Sayısı", min_value=0, value=2, step=1)
        fittings_45 = st.number_input("45° Dirsek Sayısı", min_value=0, value=0, step=1)
        gate_valves = st.number_input("Açık Vana (Gate Valve) Sayısı", min_value=0, value=1, step=1)
        
        if is_si:
            roughness_input = st.number_input("Pürüzlülük Katsayısı (mm)", value=0.00381, format="%.5f")
            roughness_in = roughness_input / 25.4
        else:
            roughness_in = st.number_input("Pürüzlülük Katsayısı (inç)", value=0.00015, format="%.6f")
            
        st.markdown("---")
        if is_si:
            set_pressure_input = st.number_input("Vana Set Basıncı (barg)", min_value=0.01, value=6.9, format="%.2f")
            set_pressure_psig = set_pressure_input * 14.50377
        else:
            set_pressure_psig = st.number_input("Vana Set Basıncı (psig)", min_value=0.1, value=100.0, format="%.2f")
            
        valve_type = st.selectbox("Vana Tipi", ["conventional", "pilot"])
        remote_sensing = st.checkbox("Pilot Vana Uzak Algılamalı (Remote Sensing Line)", value=False)

    if st.button("BASINÇ KAYBI HESAPLA", type="primary", use_container_width=True):
        try:
            res = calculate_inlet_pressure_drop(
                flow_gpm=flow_gpm,
                fluid_density_lb_ft3=fluid_density,
                viscosity_cp=viscosity,
                pipe_id_in=pipe_id_in,
                pipe_length_ft=pipe_length_ft,
                fittings_90deg=fittings_90,
                fittings_45deg=fittings_45,
                gate_valves=gate_valves,
                roughness_in=roughness_in,
                flow_rate_lb_h=flow_rate_lb_h
            )
            
            # Run API compliance rule
            passes, pct = check_inlet_rule(
                delta_p_psi=res["delta_p_psi"],
                set_pressure_psig=set_pressure_psig,
                valve_type=valve_type,
                remote_sensing=remote_sensing
            )
            
            st.markdown("### Hesaplama Sonuçları ve Kural Uygunluğu")
            res_col1, res_col2 = st.columns(2)
            
            with res_col1:
                vel_display = res['velocity_fps'] * 0.3048 if is_si else res['velocity_fps']
                vel_label = "m/s" if is_si else "ft/s"
                
                eq_display = res['equivalent_length_ft'] * 0.3048 if is_si else res['equivalent_length_ft']
                eq_label = "m" if is_si else "ft"
                
                dp_display = res['delta_p_psi'] / 14.50377 if is_si else res['delta_p_psi']
                dp_label = "bar" if is_si else "psi"

                st.markdown(f"""
                    <div class="result-card">
                        <h4>Akış Hidroliği</h4>
                        <table style="width:100%; border:none;">
                            <tr><td style="font-weight:600; padding:6px 0;">Akış Hızı (Velocity):</td><td style="text-align:right;">{vel_display:.2f} {vel_label}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Reynolds Sayısı:</td><td style="text-align:right;">{res['reynolds']:.0f}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Sürtünme Faktörü (f):</td><td style="text-align:right;">{res['friction_factor']:.4f}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Eşdeğer Boru Boyu:</td><td style="text-align:right;">{eq_display:.2f} {eq_label}</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Toplam Basınç Kaybı (dP):</td><td style="text-align:right; font-weight:700; color:#1d4ed8;">{dp_display:.3f} {dp_label}</td></tr>
                        </table>
                    </div>
                """, unsafe_allow_html=True)
                
            with res_col2:
                # Compile compliance badge
                badge_class = "status-pass" if passes else "status-fail"
                badge_text = "UYGUN (PASS)" if passes else "UYGUNSUZ (FAIL)"
                
                limit_text = "Set basıncının %3'ü"
                if valve_type == "pilot" and remote_sensing:
                    limit_text = "Muaf (Remote Sensing Line mevcut)"
                elif valve_type == "pilot":
                    limit_text = "Set basıncının %3'ü"
                    
                st.markdown(f"""
                    <div class="result-card" style="height: 100%; display: flex; flex-direction: column; justify-content: center;">
                        <h4>API 520 Part II Giriş Basınç Kaybı Kuralı</h4>
                        <div style="text-align:center; margin-bottom:1rem;">
                            <span class="status-badge {badge_class}">{badge_text}</span>
                        </div>
                        <table style="width:100%; border:none;">
                            <tr><td style="font-weight:600; padding:6px 0;">Hesaplanan Kayıp:</td><td style="text-align:right; font-weight:700;">{pct:.2f} %</td></tr>
                            <tr><td style="font-weight:600; padding:6px 0;">Yasal Limit:</td><td style="text-align:right; color:#1e293b;">{limit_text}</td></tr>
                        </table>
                        {"<p style='color:#b91c1c; font-size:0.85rem; font-weight:600; margin-top:0.75rem; text-align:center;'>⚠️ Uyarı: Basınç kaybı limiti aşıldığı için vana chattering (titreşim) yapabilir ve kapasitesi düşebilir!</p>" if not passes else ""}
                    </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Hidrolik hesaplama hatası: {str(e)}")


# HAKKINDA
else:
    st.markdown("### Hakkında")
    st.markdown("""
        **PSV Sizing Suite**, proses emniyet sistemlerinin tasarımı ve boyutlandırılması amacıyla geliştirilmiş, uluslararası endüstriyel standartlara tam uyumlu bir mühendislik aracıdır.
        
        #### Temel Standartlar ve Uyumluluk
        - **API Standard 520 Part I (9th Edition):** Gaz, buhar, sıvı ve iki fazlı akış rölyef alanı hesaplamaları.
        - **API Standard 520 Part II (6th Edition):** Emniyet vanası tesisatı basınç kaybı kontrolü.
        - **API Standard 521 (6th Edition):** Yangın (ıslak/kuru çeper) ve termal genleşme debi tespitleri.
        - **API Standard 526 (7th Edition):** Standart emniyet vanası orifis alanları ve flanş sınıfları.
        - **ASME Boiler and Pressure Vessel Code Section VIII:** Basınçlı kap emniyet standartları.
        
        #### Özellikler
        - **CoolProp Entegrasyonu:** 120'den fazla saf akışkanın termofiziksel özelliklerinin otomatik olarak hesaplanması.
        - **İzentropik İki Fazlı Flash:** DIERS Omega metodu için otomatik hacim analizleri.
        - **Gelişmiş Üretici Veritabanı:** Crosby, Anderson Greenwood vb. üreticilerin 2000'den fazla ticari modeli ile eşleştirme.
        
        *Not: Bu platform mühendislik ön-tasarım ve kontrol faaliyetlerine yöneliktir. Kritik emniyet hesaplamalarının resmi tasarım öncesinde sertifikalı mühendisler tarafından kontrol edilmesi tavsiye edilir.*
    """)
