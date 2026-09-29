# PSV Sizing Suite v2.4.0

Pressure Safety Valve sizing hesaplama platformu — API Standard 520 Part I (10. baskı + Errata 1), API Standard 520 Part II (7. baskı) ve API Standard 521 (7. baskı) esas alınır.

> **Kapsam notu:** Sonuçlar ön boyutlandırma (preliminary sizing) içindir. Nihai vana seçimi; üretici sertifikalı kapasitesi, gerçek orifis alanı, malzeme, basınç sınıfı ve trim doğrulaması gerektirir.

## Özellikler

- **Liquid Relief** — Sertifikalı (§5.8) ve sertifikasız (§5.9) yöntem ayrımı, Reynolds–Kv iterasyonu, Figure 32 Kw ve Figure 39 Kp eğrileri
- **Gas/Vapor Relief** — Kritik + subkritik akış (C/F2), Figure 31 Kb (10/16/21% aşırı basınç)
- **Steam** — Napier denklemi (51.5), KN ve KSH düzeltmeleri
- **Two-Phase Flashing** — Annex C Omega metodu (C.14/C.15, 68.09, 0.04 alan sabiti)
- **Fire Scenarios** — API 521 Eq (7)/Eq (8) (21,000 / 34,500) ve unwetted Eq (10)
- **Thermal Expansion** — API 521 hidrolik genleşme yükü
- **Piping Pressure Drop** — API 520 Part II §7.3.4 %3 inlet kuralı, muafiyet durumları
- **Pilot Operated Valves** — API 520 Section 7 (Kd 0.99 gaz / 0.80 sıvı)
- **Reaction Forces** — API 520 Part II §5.8.2 Eq (1) gaz ve Eq (2) iki faz
- **Unified Engine** — Tüm arayüzler tek `ReliefCase` yönlendiricisini kullanır ve yöntem/kaynak provenansı döndürür
- **CoolProp** — 120+ akışkanın termofiziksel özellikleri
- **Vendor DB** — 434 katalog kaydı (doğrulanmış ve tarama amaçlı kayıtlar ayrı etiketlenir)

## Dağıtım Seçenekleri

### 1. Desktop Uygulama (PyInstaller)

```bash
scripts/build_win.bat          # Windows
chmod +x scripts/build_mac.sh && ./scripts/build_mac.sh   # macOS
```

### 2. Streamlit Web

```bash
pip install -r requirements.txt
streamlit run web_app.py
# → http://localhost:8501
```

### 3. FastAPI Backend

```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
# → http://127.0.0.1:8000/docs (Swagger)
```

Birleşik uç nokta: `POST /api/v1/size` (`ReliefCase` gövdesi; service, valve_type, capacity_certified).

### 4. Docker

```bash
docker build -t psv-sizing .
docker run -p 8501:8501 psv-sizing
# → http://localhost:8501
```

## Güvenlik

- `PSV_AUTH_FILE` ortam değişkeni ile kimlik dosyası konumu değiştirilebilir.
- Streamlit arayüzü varsayılan parola ile girişte parola değişimini zorunlu kılar ve oturum kapatma sunar.
- FastAPI CORS izinleri `PSV_CORS_ORIGINS` ile kısıtlanır; varsayılan bağlantı adresi `127.0.0.1`'dir.
- Güncelleme indirmelerinde SHA-256 doğrulaması desteklenir.

## Gereksinimler

| Platform | Minimum |
|----------|---------|
| Windows | Windows 10 64-bit |
| macOS | macOS Sonoma 14+ (Apple Silicon / Intel) |
| Python (geliştirme) | 3.12+ |

## Geliştirme

```bash
git clone https://github.com/SLedgehammer-dev12/PSV_Sizing_Suite.git
cd PSV_Sizing_Suite
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Testler (izole kimlik dosyası ile)
PSV_AUTH_FILE="$(mktemp -d)/auth.json" python -m pytest tests/test_suite.py -q
```

## Standartlar

- API Standard 520 Part I — Sizing and Selection (10th ed. + Errata 1)
- API Standard 520 Part II — Installation (7th ed.)
- API Standard 521 — Pressure-relieving and Depressuring Systems (7th ed.)
- API Standard 526 — Flanged Steel Pressure Relief Valves
- ASME Boiler and Pressure Vessel Code Section VIII

## Lisans

MIT License — see [LICENSE.txt](LICENSE.txt)
