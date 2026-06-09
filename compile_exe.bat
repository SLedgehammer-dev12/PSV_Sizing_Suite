@echo off
:: Read version from core module
for /f "tokens=*" %%i in ('python -c "import sys; sys.path.insert(0,'.'); from core import __version_tag__; print(__version_tag__)"') do set VERSION=%%i
if "%VERSION%"=="" set VERSION=v2.2.0

echo =======================================================
echo PSV SIZING SUITE %VERSION% - EXE OLUSTURMA ARACI
echo =======================================================
echo UYARI: Eger bu klasor yolunda (D:\Is\Calisan...) Turkce 
echo karakterler varsa PyInstaller hata verecektir.
echo Bu klasoru kopyalayip C:\PSV_Sizing gibi Turkce 
echo karakter icermeyen bir yere tasiyip bu dosyayi 
echo orada calistirmaniz tavsiye edilir.
echo =======================================================
pause

echo Gerekli kutuphaneler yukleniyor...
python -m venv venv_build
call venv_build\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo EXE Derleniyor...
pyinstaller --noconsole --onedir --name "PSV_Sizing_Suite_%VERSION%_Desktop" --hidden-import "core.advanced_sizing" --add-data "vendor_data;vendor_data" "main.py"
pyinstaller --noconsole --onedir --name "PSV_Sizing_Suite_%VERSION%_Web" --hidden-import "core.advanced_sizing" --add-data "vendor_data;vendor_data" --add-data "web_app.py;." "run_streamlit.py"

echo Islemler tamamlandi. Sonuclari 'dist' klasorunde bulabilirsiniz.
pause
