# -*- mode: python ; coding: utf-8 -*-
"""
PSV Sizing Suite — PyInstaller spec
Platforms: Windows, macOS, Linux
"""
import sys, os, re as _re

block_cipher = None

# Read version from core/__init__.py without importing
# SPECPATH (spec file directory, e.g. PROJECT/config/) is injected by PyInstaller
_ver_file = os.path.join(SPECPATH, '..', 'core', '__init__.py')
VERSION = 'v2.3.0'
if os.path.exists(_ver_file):
    for _line in open(_ver_file):
        if '__version__ ' in _line and '=' in _line:
            _parts = _line.split('=', 1)
            if len(_parts) == 2:
                VERSION = 'v' + _parts[1].strip().strip('"\'')
            break

hidden_imports = [
    # Core engine
    'core', 'core.kb_coefficient', 'core.units', 'core.report',
    'core.piping', 'core.valve_types', 'core.unit_converter',
    'core.vendor_catalog', 'core.valve_selection',
    'core.liquid_relief', 'core.gas_relief', 'core.two_phase',
    'core.fire_scenarios', 'core.thermal_expansion', 'core.blowby',
    'core.advanced_sizing',
    # Desktop UI
    'desktop', 'desktop.auth', 'desktop.app', 'desktop.tabs',
    'desktop.tabs_extra', 'desktop.workers', 'desktop.vendor_window',
    'desktop.report_generator', 'desktop.graph_window',
    # GUI framework
    'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
    # Plotting
    'matplotlib', 'matplotlib.backends.backend_qt5agg',
    'matplotlib.figure', 'matplotlib.pyplot',
    # Scientific
    'numpy', 'CoolProp', 'CoolProp.CoolProp',
]

excludes = [
    'PyQt5.QtSvg', 'PyQt5.QtNetwork', 'PyQt5.QtQml',
    'PyQt5.QtSql', 'PyQt5.QtTest', 'PyQt5.QtXml',
    'PyQt5.QtWebEngine', 'PyQt5.QtWebSockets',
    'PyQt5.QtBluetooth', 'PyQt5.QtPositioning',
    'PyQt5.QtMultimedia', 'PyQt5.QtSensors',
    'unittest', 'email',
    'xml', 'xmlrpc', 'pydoc',
    'ensurepip', 'turtle', 'sqlite3',
    'scipy', 'sympy', 'pandas.io',
    'cv2', 'PIL', 'Pillow',
]
import os

a = Analysis(
    [os.path.join(SPECPATH, '..', 'main.py')],
    pathex=[os.path.join(SPECPATH, '..')],
    binaries=[],
    datas=[(os.path.join(SPECPATH, '..', 'vendor_data'), 'vendor_data')],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=f'PSV_Sizing_Suite_{VERSION}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime*.dll'],
    console=False,
    icon=os.path.join(SPECPATH, '..', 'assets', 'icon.ico')
)

coll = COLLECT(exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime*.dll'],
    name=f'PSV_Sizing_Suite_{VERSION}'
)
