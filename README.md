# PSV Sizing Suite v2.3.0

Pressure Safety Valve sizing hesaplama platformu — API Standard 520 (Part I) & API Standard 521 uyumlu.

## Özellikler

- **Liquid Relief** — Sıvı tahliye alanı hesaplama (vizkozite düzeltmeli)
- **Gas/Vapor Relief** — Gaz/buhar tahliye (kritik + subkritik akış)
- **Two-Phase Flashing** — İki fazlı akış (Omega metodu, DIERS)
- **Fire Scenarios** — Yangın senaryoları (ıslak + kuru, API 521)
- **Thermal Expansion** — Termal genleşme yükü
- **Piping Pressure Drop** — İnlet/outlet basınç kaybı (API 520 Part II)
- **Pilot Operated Valves** — Pilot kontrollü vanalar (API 520 Section 7)
- **Kb Correction** — Back pressure düzeltme (balanced bellows)
- **CoolProp** — 120+ akışkanın termofiziksel özellikleri
- **Vendor DB** — 2000+ ticari PSV modeli (API D-T orifis)

## Dağıtım Seçenekleri

### 1. Desktop Uygulama (PyInstaller)

```bash
# Windows
scripts\build_win.bat

# macOS
chmod +x scripts/build_mac.sh
./scripts/build_mac.sh
```

Çıktı:
- Windows: `dist/PSV_Sizing_Suite_v2.3.0/PSV_Sizing_Suite_v2.3.0.exe` + Setup.exe
- macOS: `dist/PSV_Sizing_Suite_v2.3.0.dmg`

### 2. Streamlit Web

```bash
pip install -r requirements.txt
streamlit run web_app.py
# → http://localhost:8501
```

### 3. FastAPI Backend

```bash
pip install fastapi uvicorn
uvicorn api.main:app --reload
# → http://localhost:8000/docs (Swagger)
```

### 4. Docker

```bash
docker build -t psv-sizing .
docker run -p 8501:8501 psv-sizing
# → http://localhost:8501
```

## Gereksinimler

| Platform | Minimum |
|----------|---------|
| Windows | Windows 10 64-bit |
| macOS | macOS Sonoma 14+ (Apple Silicon / Intel) |
| RAM | 512 MB |
| Disk | 200 MB |
| Python (geliştirme) | 3.10+ |

## Geliştirme

```bash
git clone https://github.com/SLedgehammer-dev12/PSV_Sizing_Suite.git
cd PSV_Sizing_Suite
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Standartlar

- API Standard 520 Part I — Sizing and Selection
- API Standard 521 — Pressure-relieving and Depressuring Systems
- API Standard 526 — Flanged Steel Pressure Relief Valves
- ASME Boiler and Pressure Vessel Code Section VIII

## Lisans

MIT License — see [LICENSE.txt](LICENSE.txt)
