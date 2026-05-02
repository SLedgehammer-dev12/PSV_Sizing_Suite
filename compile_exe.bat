@echo off
echo =======================================================
echo PSV SIZING SUITE v2.1 - EXE OLUSTURMA ARACI
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
pyinstaller --noconsole --onedir --name "PSV_Sizing_Suite_v2.1_Desktop" --add-data "vendor_data;vendor_data" "main.py"
pyinstaller --noconsole --onedir --name "PSV_Sizing_Suite_v2.1_Web" --add-data "vendor_data;vendor_data" --add-data "web_app.py;." "run_streamlit.py"

echo Islemler tamamlandi. Sonuclari 'dist' klasorunde bulabilirsiniz.
pause
