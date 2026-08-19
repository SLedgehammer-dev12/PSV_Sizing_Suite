# Changelog

## v2.3.1 — Mühendislik Doğruluk Düzeltmeleri

### 🔧 Standart Uyum Düzeltmeleri (API 520/521)
- Sıvı tahliye ön boyutlandırma Kd = 0.65 (önceden yanlışlıkla pilot Kd'si 0.80 kullanılıyordu → alan ~%19 eksik)
- Gaz tahliye ön boyutlandırma Kd = 0.975 (önceden 0.99 → alan ~%1.5 eksik)
- Gaz sekmesi barg→psig dönüşümü eklendi (P1 hesaplaması düzeltildi)
- İki-faz kritik basınç oranı (ηc) — API 520 Annex C Eq.C.15 ile hizalı (DIERS örtük çözümüyle doğrulandı)
- İki-faz subkritik kütle akısı (G) — fazladan 1/√ω faktörü kaldırıldı
- Sıvı viskozite düzeltmesi Kv = (0.9935 + 2.878/Re^0.5 + 342.75/Re^1.5)^-1 (API 520 Eq.34)
- Gaz subkritik denkleminden Kb kaldırıldı (API 520'de Kb yalnız kritik akışta)
- Sıvı formülüne Kc (patlama diski düzeltme) parametresi eklendi
- Napier buhar Kn eşiği 1500 psia (önceden 1500 psig); buhar kritik oranı düzeltildi
- Yangın (wetted): yetersiz drenaj/firefighting durumu için 34500 katsayısı (`adequate_drainage`)

### 🛠️ Bakım / Profesyonellik
- `api/main.py` bozuk import/imzalar düzeltildi (artık import edilebilir ve çalışır)
- Hardcode sabitler `core.constants`'a taşındı (735.0, 38.0, 645.16, 14.6959)
- `R_PER_BARA` → `R_PSIA_FT3_LBMOL_R` (geriye dönük alias korundu)
- Sonuçlara "Orifice Loading %" ve Kd/Kc eklendi; PDF raporuna standart referans bölümü eklendi
- Fire environment faktörleri (`ENV_FACTORS`, `get_env_factor`, `calculate_heat_absorption`) eklendi
- README/AGENTS/About sürüm ve test sayısı tutarlı hale getirildi (161 test)

### 🆕 Yeni Modüller / Özellikler
- Reaksiyon kuvveti (`core/reaction_force.py`) — API 520 Part II, gaz + sıvı
- Tahliye gürültü hesabı (`core/noise.py`) — API 521 basitleştirilmiş metodoloji
- Backpressure çalışma limiti uyarıları (konvansiyonel >%50, balanced bellows >%60) ve Kb kırpma notu
- Patlama diski Kc seçeneği (Liquid + Gas sekmeleri ve worker'lar)
- Vendor DB temizliği (`scripts/clean_vendor_db.py`): 24 geçersiz kayıt silindi, Google arama placeholder'ları resmi URL'lerle değiştirildi
- Vendor tasarım tipi filtrelemesi sağlamlaştırıldı (çoklu kategori eşleme)
- CI: Windows + macOS (Apple Silicon/arm64) build'leri; Windows build'inde UPX kaldırıldı ve VERSIONINFO eklendi (AV false-positive azaltma)

## v2.3.0 (2026-06-05)

### ✨ Yeni Özellikler (v2.2.0 → v2.3.0)
- Kb back pressure correction eğrisi (balanced bellows, API 520 Fig 11-4/5)
- Subcooled two-phase flow (API 520 Section 5.8 omega metodu)
- API 521 fire environment faktörleri (10 kategori)
- Piping basınç düşümü kontrolü (API 520 Part II)
- Pilot operated valve sizing (API 520 Section 7)
- Dinamik Birim Sistemi (SI / USC geçiş)
- Napier Buhar Sizing (Kn + Ksh katsayıları)
- Alt-Soğutulmuş İki Fazlı Flashing (API 520 C.2.3)
- Alternatif/Kontrol Hesaplama (Buhar + 2-faz)
- FastAPI REST API (17 endpoint, Pydantic v2 modelleri)
- React frontend (Ant Design, 4 hesaplama formu)

### 🔧 İyileştirmeler (v2.2.0 → v2.3.0)
- Zero-dependency embedding (PolyKin/psvpy → pure Python)
- pytest migration (unittest → pytest)
- Password hashing (PBKDF2-HMAC-SHA256 + salt)
- Versiyon tek kaynağı (`core.__version__`)
- PyInstaller .spec + NSIS script + macOS DMG build

### 🐛 Bug Fixes (Phase 0)
- `desktop/workers.py:97`: Yangın back pressure sabit 14.7 → kullanıcı girişi
- `core/two_phase.py`: Function-body import'lar top-level taşındı
- `core/kb_coefficient.py`: Pilot valve Kb=1.0 (API 520 §7)
- `core/gas_relief.py`: k=1.0 için ZeroDivisionError
- `desktop/auth.py`: Düz SHA-256 → PBKDF2
- `desktop/workers.py`: Yapay 300ms gecikmeler kaldırıldı

### 🏗️ Mimari (Phase 1)
- `core/models.py`: Paylaşılan Pydantic v2 modelleri (11 input modeli)
- `api/main.py`: Local modeller → `core.models` import
- `core/piping.py`: Sonic velocity + Mach number kontrolü
- `web_app.py`: Fire→Gas routing button (Aktar ve Hesapla)

### 🧪 Test (Phase 2)
- Test sayısı: 88 → 177 (+56 yeni test)
- Pilot Kd override tests (gas + liquid)
- Sonic velocity / Mach number tests
- Shared Pydantic model validation tests
- Valve types (pilot gas/liquid area) tests
- Piping edge cases (outlet rule, Darcy laminar/turbulent/zero)
- Units (pint wrapper) tests
- Fire scenarios heat absorption shape tests
- Advanced sizing (Ksh interpolation, Kn range) tests

### 📦 Build Sistemi
- macOS: `scripts/build_mac.sh` (PyInstaller + hdiutil dmg)
- Windows: `scripts/build_win.bat` (PyInstaller + NSIS installer)
- CI/CD: `.github/workflows/release.yml` (Windows + macOS)
- Versiyon: tüm dosyalar `core.__version__` sabitinden okur

---

## v2.3.0.0 (Initial Release)
- İlk sürüm — temel PSV hesaplamaları (API 520/521)
- PyQt5 desktop uygulaması
- Streamlit web uygulaması
- CoolProp termodinamik özellik veritabanı
- Vendor kataloğu (PSV üreticileri)
