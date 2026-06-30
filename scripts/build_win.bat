@echo off
setlocal enabledelayedexpansion

:: Read version from core module
for /f "tokens=*" %%i in ('python -c "import sys; sys.path.insert(0,'.'); from core import __version_tag__; print(__version_tag__)"') do set VERSION=%%i
if "%VERSION%"=="" set VERSION=v2.3.0
set APPNAME=PSV_Sizing_Suite_%VERSION%

echo =============================================
echo PSV Sizing Suite %VERSION% - Windows Build
echo =============================================
echo.

:: ---------- Check Python ----------
python --version >nul 2>&1 || (
    echo [HATA] Python bulunamadi. Python 3.13+ yukleyin.
    echo   https://www.python.org/downloads/
    pause
    exit /b 1
)

:: ---------- Virtual Environment ----------
echo [1/5] Sanal ortam olusturuluyor...
if not exist ".venv" python -m venv .venv
call .venv\Scripts\activate.bat

:: ---------- Install Dependencies ----------
echo [2/5] Bagimliliklar yukleniyor...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt >nul
pip install pyinstaller >nul

:: ---------- Clean ----------
echo [3/5] Eski buildler temizleniyor...
if exist "dist\%APPNAME%" rmdir /s /q "dist\%APPNAME%"
if exist "dist\*.exe" del /q "dist\*.exe"
if exist "build" rmdir /s /q "build"

:: ---------- PyInstaller Build ----------
echo [4/5] Calistirilabilir dosya derleniyor...
pyinstaller config\psv_desktop.spec --noconfirm > build.log 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Derleme basarisiz! build.log dosyasini kontrol edin.
    echo.
    echo =============================================
    echo SON 20 SATIR:
    type build.log | findstr /v "^$"
    echo =============================================
    pause
    exit /b 1
)

:: ---------- Create NSIS Installer ----------
echo [5/5] Installer olusturuluyor...
if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
    "C:\Program Files (x86)\NSIS\makensis.exe" /DVERSION=%VERSION% installer_win.nsi >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Installer olusturuldu: dist\%APPNAME%_Setup.exe
    ) else (
        echo [UYARI] NSIS installer olusturulamadi
        echo   NSIS yuklemek icin: https://nsis.sourceforge.io/Download
    )
) else (
    echo [UYARI] NSIS bulunamadi - installer olusturulamadi
    echo   NSIS yuklemek icin: https://nsis.sourceforge.io/Download
)

:: ---------- Summary ----------
echo.
echo =============================================
echo BUILD TAMAMLANDI!
echo =============================================
echo.
echo Cikti dosyalari:
if exist "dist\%APPNAME%\%APPNAME%.exe" (
    echo   [EXE] dist\%APPNAME%\%APPNAME%.exe
)
if exist "dist\%APPNAME%_Setup.exe" (
    echo   [SETUP] dist\%APPNAME%_Setup.exe
)
echo.
echo Boyut:
if exist "dist\%APPNAME%\%APPNAME%.exe" (
    for %%F in ("dist\%APPNAME%\%APPNAME%.exe") do echo   EXE: %%~zF bytes
)
echo.
echo NOT: Bu build sertifikasizdir. Windows Defender uyarisi verebilir.
echo   Guvenli oldugunu bildiginiz icin "Yine de calistir" secin.
echo.
pause
