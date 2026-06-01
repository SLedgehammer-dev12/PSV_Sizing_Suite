#!/bin/bash
set -euo pipefail

echo "============================================="
echo "PSV Sizing Suite - Cross-Platform Build Runner"
echo "============================================="
echo ""

OS="$(uname -s)"
case "$OS" in
    Linux*)   PLATFORM="linux" ;;
    Darwin*)  PLATFORM="macos" ;;
    MINGW*|MSYS*|CYGWIN*) PLATFORM="windows" ;;
    *)        echo "Unknown OS: $OS"; exit 1 ;;
esac

echo "Detected platform: ${PLATFORM}"
echo ""

case "${PLATFORM}" in
    windows)
        echo "Windows build requires:"
        echo "  - Python 3.13+"
        echo "  - NSIS (optional, for installer)"
        echo ""
        echo "Run manually:"
        echo "  scripts\\build_win.bat"
        ;;
    macos)
        chmod +x scripts/build_mac.sh
        scripts/build_mac.sh
        ;;
    linux)
        echo "Linux build not yet supported"
        echo "Run via Docker instead:"
        echo "  docker build -t psv-sizing ."
        exit 1
        ;;
esac
