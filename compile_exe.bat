@echo off
echo =======================================================
echo PSV SIZING SUITE v2.3.0 - EXE BUILD TOOL
echo =======================================================
echo This script creates a clean venv and builds both EXEs.
echo Run from project root directory.
echo =======================================================
echo.

echo Installing dependencies...
python -m venv venv_build
call venv_build\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo.
echo Building EXEs...
pyinstaller --name PSV_Sizing_Suite_Desktop_v2.3.0_Windows --windowed --add-data "core;core" --add-data "desktop;desktop" --add-data "vendor_data;vendor_data" --hidden-import core --hidden-import core.thermo_props --hidden-import core.unit_converter --hidden-import core.vendor_catalog --hidden-import bcrypt main.py -y

pyinstaller --name PSV_Sizing_Suite_Web_v2.3.0_Windows --windowed --add-data "core;core" --add-data "web_app.py;." --add-data "vendor_data;vendor_data" --hidden-import core --hidden-import core.thermo_props --hidden-import core.unit_converter --hidden-import core.vendor_catalog --hidden-import bcrypt run_streamlit.py -y

echo.
echo Build complete! Output in dist\ directory.
pause
