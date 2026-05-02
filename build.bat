@echo off
echo Building PSV Sizing Suite Executable...
"D:\İş\Çalışan programlar\@Güncelleme\.venv\Scripts\pyinstaller.exe" --noconsole --onedir --name "PSV_Sizing_Suite_v2.1_Desktop" --add-data "vendor_data;vendor_data" "main.py"
"D:\İş\Çalışan programlar\@Güncelleme\.venv\Scripts\pyinstaller.exe" --noconsole --onedir --name "PSV_Sizing_Suite_v2.1_Web" --add-data "vendor_data;vendor_data" --add-data "web_app.py;." "run_streamlit.py"
echo Build Complete!
