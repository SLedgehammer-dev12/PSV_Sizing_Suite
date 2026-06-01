# Changelog

## v2.2.0 (2026-06-01)

### ✨ Yeni Özellikler
- Kb back pressure correction eğrisi (balanced bellows, API 520 Fig 11-4/5)
- Subcooled two-phase flow (API 520 Section 5.8 omega metodu)
- API 521 fire environment faktörleri (10 kategori: bare, insulation, foam, vb.)
- 20,000+ ft² büyük yangın alanları için kesikli formül
- Piping basınç düşümü kontrolü (API 520 Part II, Darcy-Weisbach + Colebrook)
- Pilot operated valve sizing (API 520 Section 7, Kd=0.99 gas / 0.80 liquid)
- FastAPI REST API (17 endpoint, Pydantic v2 modelleri)
- React frontend (Ant Design UI, 4 hesaplama formu)

### 🔧 İyileştirmeler
- pytest migration (unittest → pytest, 88 test)
- Password hashing (düz SHA-256 → PBKDF2-HMAC-SHA256 + salt)
- Birim dönüşüm tutarlılığı (tüm sabitler merkezi tanımlandı)
- PyInstaller .spec dosyası (gizli importlar elle bildirildi)
- NSIS Windows installer scripti
- macOS DMG build script (dmgbuild + notarization desteği)
- .streamlit/config.toml (Streamlit tema ve güvenlik ayarları)

### 🐛 Bug Fixes
- `core/gas_relief.py`: k=1.0 için ZeroDivisionError (C ve F2 katsayıları)
- `desktop/auth.py`: Salt kullanılmayan SHA-256 hash → PBKDF2
- `desktop/workers.py`: Yapay 300ms gecikmeler kaldırıldı
- `core/unit_converter.py`: Atmosfer basıncı sabit tutarsızlığı (14.696 vs 14.50377)
- `desktop/report_generator.py`: HTML injection (XSS) riski
- `core/thermo_props.py`: Mass→mole dönüşümünde sabit 300K referansı

### 📦 Build Sistemi
- Windows: `scripts/build_win.bat` (PyInstaller + NSIS installer)
- macOS: `scripts/build_mac.sh` (PyInstaller + DMG + notarization)
- Cross-platform: `scripts/build_all.sh`

---

## v2.1.0 (Initial Release)
- İlk sürüm — temel PSV hesaplamaları (API 520/521)
- PyQt5 desktop uygulaması
- Streamlit web uygulaması
- CoolProp termodinamik özellik veritabanı
- Vendor kataloğu (PSV üreticileri)
