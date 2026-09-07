# Changelog

## v2.3.6 — API 520/521 Standart Uyumu ve Hesaplama Motoru Düzeltmeleri

### 🔧 Standart Uyum ve Fiziksel Modelleme
- **API 520 Part I Sıvı Düzeltme Faktörleri ($K_p$ ve $K_w$):**
  - API 520 Eq. 30 uyarınca %10'dan farklı aşırı basınçlar için zorunlu $K_p$ kapasite düzeltme faktörü (`calculate_kp`) API 520 Şekil 38 eğrisine göre eklendi.
  - Dengelenmiş körüklü vanalarda sıvı karşı basıncı için $K_w$ katsayısı (`calculate_kw_liquid`) API 520 Şekil 37 eğrisiyle modellendi.
  - `calculate_liquid_relief_area` fonksiyonu geriye dönük uyumluluk korunarak `kp`, `overpressure_pct` ve `valve_type` parametrelerini alacak şekilde güncellendi.
- **API 521 §5.8.10 Akustik Gürültü Verimi ($\eta_a$):**
  - Mekanik kinetik enerjinin %100'ünün sese dönüştüğü varsayımı düzeltildi; API 521 ve Lighthill türbülanslı jet teorisine uygun $\eta_a$ akustik verim modeli entegre edildi.
  - Akustik güç ($W$) ve verim ($\eta_a$) çıktı parametrelerine eklendi, ses seviyesi (SPL) fiziksel standart değer olan 99.1 dB'e getirildi.
- **Gaz/Buhar Subkritik Akışında Asimptotik Limit ($k \to 1.0$):**
  - İzoentropik üs $k \to 1.0$ limitine yaklaştığında $(k - 1)$ paydası kaynaklı sıfıra bölme ve `NaN` hatası analitik limit ($\lim_{k \to 1} \frac{k}{k-1}[1 - r^{(k-1)/k}] = -\ln r$) ile giderildi.
- **Termodinamik Karışım Faz Güvenliği (CoolProp):**
  - Bileşen eşleştirmede `"Water (Steam)"` girdisi `"Water"` olarak normalize edildi.
  - Kay kuralı ile buhar karışımı özelliklerinde, sıcaklığın saf bileşenin kaynama noktasının altında kalması durumunda sıvı $C_p$'sinin buhar karışımını bozması engellendi.

### 🐛 Bug Fixes & Stabiliteler
- **FastAPI Endpoint Hatası:** `/api/v1/thermal-expansion` ve `/api/v1/liquid-relief` endpoint'lerinde `valve_type` aktarımından kaynaklanan 500 Internal Server Error (`TypeError`) düzeltildi.
- **Masaüstü Grafik Çökmesi:** Yüksek karşı basınç durumlarında ($P_{back} > 0.8 P_{set}$) grafiğin eksi basınca inip GUI'yi çökertmesi $P_{min} > P_{back}$ alt sınır korumasıyla engellendi.
- **Yangın Senaryosu:** `FireWettedWorker` varsayılan aşırı basınç oranı API 521'e uygun olarak %21'e ayarlandı.
- **Kod Temizliği:** `core/unit_converter.py` içindeki mükerrer `sqft_to_m2` kaldırıldı; `core/constants.py` içine `PSIA_PER_KPA` sabit eklendi.

### 🧪 Test
- 6 yeni mühendislik ve uçtan uca test (`TestV236Improvements`) eklendi. Toplam test sayısı 185'ten **191**'e yükseltildi, tümü geçiyor.

## v2.3.5 — macOS Grafik Düzeltmesi (PyQt5.QtSvg Build)

### 🐛 Bug Fixes
- macOS'ta "Grafik Göster" açılırken `ImportError: cannot import name 'QtSvg' from 'PyQt5'` düzeltildi
  - Kök neden: `release.yml` macOS build'i `--exclude-module PyQt5.QtSvg` ile PyQt5 QtSvg Python binding'ini paket dışı bırakıyordu; matplotlib Qt5Agg backend'i (`qt_compat._setup_pyqt5plus`) QtSvg'yi import ediyor
  - `.github/workflows/release.yml`: `PyQt5.QtSvg` exclude kaldırıldı, `--hidden-import PyQt5.QtSvg` eklendi (`scripts/build_mac.sh` ile tutarlı)
  - Bu, v2.3.2'deki ilk SIGABRT çökmesinin de asıl kök nedeniydi; v2.3.3'teki global excepthook çökmeyi önleyip gerçek hatayı görünür kıldı

### 🧪 Test
- Test sayısı 185 (değişmedi), tümü geçiyor

## v2.3.4 — Güncelleme Kontrolü SSL Sertifika Düzeltmesi

### 🐛 Bug Fixes
- "Güncelleme kontrolü"nde yanıltıcı "İnternet bağlantısı kontrol edilemedi." hatası düzeltildi
  - Kök neden: macOS'ta Python'un default OpenSSL CA yolu boştu; `ssl.create_default_context()` `CERTIFICATE_VERIFY_FAILED` fırlatıyordu (ağ sorunu değil)
  - `desktop/workers.py`: `_ssl_context()` helper'ı eklendi — `certifi` CA bundle'ını kullanıyor (kaynak ve PyInstaller bundle'ında çalışır)
  - `_format_url_error()`: SSL sertifika hataları artık ayrı ve açıklayıcı mesaj gösteriyor
- `requirements.txt`: `certifi` bağımlılığı eklendi
- `config/psv_desktop.spec`: `certifi` hidden_imports'a eklendi (frozen build'de paketleme garantisi)

### 🧪 Test
- Test sayısı 185 (değişmedi), tümü geçiyor

## v2.3.3 — macOS Çökme Düzeltmesi (Grafik Menüsü)

### 🐛 Bug Fixes
- macOS'ta "Grafik Göster" menüsünden kaynaklanan SIGABRT çökmesi düzeltildi
  - Kök neden: menü slot'unda yakalanmayan Python exception'ı PyQt5'in `qFatal()` → `abort()` çağrısını tetikliyordu
  - `main.py`'ye global `sys.excepthook` eklendi; PyQt5 artık çökmek yerine hatayı log dosyasına yazıp kullanıcıya gösteriyor
- `desktop/app.py`: `show_graph`, `save_state`, `generate_report`, `check_update`, `show_about`, `change_user_pw` slotları try/except + log ile korundu
- `desktop/graph_window.py`: matplotlib import'u ve render hataları log'a yazılıyor; seçili orifis alanı/çalışma noktası artık doğru kaynaktan (`_get_graph_results`) çiziliyor

### 🧪 Test
- Test sayısı 185 (değişmedi), tümü geçiyor

## v2.3.2 — Reaksiyon Kuvveti, Gürültü ve Bakım

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
