@echo off
echo Building PSV Sizing Suite Executable...
"D:\İş\Çalışan programlar\@Güncelleme\.venv\Scripts\pyinstaller.exe" --noconsole --onedir --name "PSV_Sizing_Suite_v2.0" --add-data "vendor_data;vendor_data" "main.py"
echo Build Complete!
