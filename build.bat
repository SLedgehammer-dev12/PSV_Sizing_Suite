@echo off
echo Building PSV Sizing Suite v2.3.0 Executables...
echo NOTE: Run this from an activated virtual environment with pyinstaller installed.
echo.

echo [1/2] Building Desktop...
pyinstaller --name PSV_Sizing_Suite_Desktop_v2.3.0_Windows --windowed --add-data "core;core" --add-data "desktop;desktop" --add-data "vendor_data;vendor_data" --hidden-import core --hidden-import core.thermo_props --hidden-import core.unit_converter --hidden-import core.vendor_catalog --hidden-import bcrypt main.py -y

echo.
echo [2/2] Building Web...
pyinstaller --name PSV_Sizing_Suite_Web_v2.3.0_Windows --windowed --add-data "core;core" --add-data "web_app.py;." --add-data "vendor_data;vendor_data" --hidden-import core --hidden-import core.thermo_props --hidden-import core.unit_converter --hidden-import core.vendor_catalog --hidden-import bcrypt run_streamlit.py -y

echo.
echo Build Complete! Output in dist\ directory.
pause
