#!/bin/bash
set -euo pipefail

# Read version from core module (suppress WeasyPrint warnings on stderr)
VERSION=$(python3 -c "import sys; sys.path.insert(0,'.'); from core import __version_tag__; print(__version_tag__)" 2>&1 | grep -E '^v[0-9]' || echo "v2.3.0")
APPNAME="PSV_Sizing_Suite_${VERSION}"

echo "============================================="
echo "PSV Sizing Suite ${VERSION} - macOS Build"
echo "============================================="
echo ""

ARCH=$(uname -m)
echo "Architecture: ${ARCH}"

# ---------- Check Python ----------
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found. Install Python 3.13+"
    echo "  brew install python@3.13"
    exit 1
fi

# ---------- Virtual Environment ----------
echo "[1/6] Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# ---------- Install Dependencies ----------
echo "[2/6] Installing dependencies..."
pip3 install --upgrade pip --quiet
pip3 install -r requirements.txt --quiet
pip3 install pyinstaller --quiet
pip3 install dmgbuild --quiet

# ---------- Clean ----------
echo "[3/6] Cleaning previous builds..."
rm -rf "dist/${APPNAME}" build "dist/${APPNAME}.app" "dist/${APPNAME}.dmg" "*.spec"

# ---------- PyInstaller Build ----------
echo "[4/6] Building .app bundle (this may take several minutes)..."

pyinstaller --noconsole \
    --name "${APPNAME}" \
    --icon "assets/icon.icns" \
    --add-data "vendor_data:vendor_data" \
    --osx-bundle-identifier "com.psv.sizing-suite" \
    --target-arch "${ARCH}" \
    --hidden-import desktop.auth \
    --hidden-import desktop.tabs \
    --hidden-import desktop.tabs_extra \
    --hidden-import desktop.workers \
    --hidden-import desktop.graph_window \
    --hidden-import desktop.vendor_window \
    --hidden-import desktop.report_generator \
    --hidden-import core.kb_coefficient \
    --hidden-import core.units \
    --hidden-import core.report \
    --hidden-import core.piping \
    --hidden-import core.valve_types \
    --hidden-import core.advanced_sizing \
    --exclude-module PyQt5.QtSvg \
    --exclude-module PyQt5.QtSql \
    --exclude-module PyQt5.QtQml \
    --exclude-module PyQt5.QtNetwork \
    --exclude-module PyQt5.QtTest \
    --exclude-module PyQt5.QtXml \
    main.py 2>&1 | tail -5

if [ ! -d "dist/${APPNAME}.app" ]; then
    echo "[ERROR] Build failed. Check output above."
    exit 1
fi
echo "  ✓ .app bundle created"

# ---------- Code Sign (optional) ----------
echo "[5/6] Code signing..."
if security find-identity -v -p basic 2>/dev/null | grep -q "Developer ID"; then
    codesign --deep --force --verify --verbose \
        --options runtime \
        --sign "Developer ID Application" \
        "dist/${APPNAME}.app" 2>&1 | tail -3
    echo "  ✓ Signed with Developer ID"
else
    echo "  - No Developer ID certificate found — skipping sign (Gatekeeper warning expected)"
fi

# ---------- Create DMG ----------
echo "[6/6] Creating DMG (hdiutil)..."
rm -f "dist/${APPNAME}.dmg"
hdiutil create -srcfolder "dist/${APPNAME}.app" \
    -volname "${APPNAME}" \
    -fs HFS+ -format UDRW -size 500m \
    "dist/${APPNAME}-tmp.dmg"
hdiutil convert "dist/${APPNAME}-tmp.dmg" \
    -format UDZO -imagekey zlib-level=9 \
    -o "dist/${APPNAME}.dmg"
rm -f "dist/${APPNAME}-tmp.dmg"
echo "  ✓ DMG created: dist/${APPNAME}.dmg"

if [ ! -f "dist/${APPNAME}.dmg" ]; then
    echo "[ERROR] DMG creation failed"
    exit 1
fi

# ---------- Notarize (optional) ----------
if [ -n "${APPLE_ID:-}" ] && [ -n "${APPLE_PASSWORD:-}" ] && [ -n "${APPLE_TEAM_ID:-}" ]; then
    echo "[+] Notarizing with Apple..."
    xcrun notarytool submit "dist/${APPNAME}.dmg" \
        --apple-id "${APPLE_ID}" \
        --password "${APPLE_PASSWORD}" \
        --team-id "${APPLE_TEAM_ID}" \
        --wait 2>&1 | tail -5
    xcrun stapler staple "dist/${APPNAME}.dmg" 2>&1
    echo "  ✓ Notarized"
else
    echo "  - Apple ID not configured — skipping notarization"
    echo "  - To enable: export APPLE_ID, APPLE_PASSWORD, APPLE_TEAM_ID"
fi

# ---------- Summary ----------
echo ""
echo "============================================="
echo "BUILD COMPLETE!"
echo "============================================="
echo ""
echo "Output:"
ls -lh "dist/${APPNAME}.dmg" 2>/dev/null || echo "  DMG not found"
echo ""
echo "NOTE: This build is unsigned. macOS Gatekeeper may show a warning."
echo "  To run: Right-click → Open, then click 'Open' in the dialog."
echo ""
