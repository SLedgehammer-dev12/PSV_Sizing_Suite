# -*- mode: python ; coding: utf-8 -*-
"""
PSV Sizing Suite — PyInstaller spec
Platforms: Windows, macOS, Linux

Antivirus/antimalware consideration:
- UPX is DISABLED: UPX-packed executables trigger false positives.
- A Windows VERSIONINFO resource with real product metadata is embedded,
  which reduces SmartScreen/AV heuristic flags.
- onedir layout (not onefile) is used: less likely to be flagged.
"""
import sys, os, re as _re, tempfile

block_cipher = None

# Read version from core/__init__.py without importing
# SPECPATH (spec file directory, e.g. PROJECT/config/) is injected by PyInstaller
_ver_file = os.path.join(SPECPATH, '..', 'core', '__init__.py')
VERSION = 'v2.3.1'
if os.path.exists(_ver_file):
    for _line in open(_ver_file):
        if '__version__ ' in _line and '=' in _line:
            _parts = _line.split('=', 1)
            if len(_parts) == 2:
                VERSION = 'v' + _parts[1].strip().strip('"\'')
            break

_VERSION_INFO_PATH = None
def _build_version_info(version):
    """Generate a Windows VERSIONINFO resource file from the project version."""
    global _VERSION_INFO_PATH
    nums = _re.findall(r'\d+', version)
    while len(nums) < 4:
        nums.append('0')
    nums = nums[:4]
    ver_tuple = ', '.join(nums)
    content = f'''VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({ver_tuple},),
    prodvers=({ver_tuple},),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'PSV Sizing Suite'),
         StringStruct(u'FileDescription', u'PSV Sizing Suite - Pressure Safety Valve Sizing'),
         StringStruct(u'FileVersion', u'{version}'),
         StringStruct(u'InternalName', u'PSV_Sizing_Suite'),
         StringStruct(u'LegalCopyright', u'Copyright (c) 2026 PSV Sizing Suite'),
         StringStruct(u'OriginalFilename', u'PSV_Sizing_Suite_{version}.exe'),
         StringStruct(u'ProductName', u'PSV Sizing Suite'),
         StringStruct(u'ProductVersion', u'{version}')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    try:
        fd, path = tempfile.mkstemp(prefix='psv_verinfo_', suffix='.txt')
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        _VERSION_INFO_PATH = path
    except Exception:
        _VERSION_INFO_PATH = None

if sys.platform == 'win32':
    _build_version_info(VERSION)

hidden_imports = [
    # Core engine
    'core', 'core.kb_coefficient', 'core.units',
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
    # matplotlib Qt5Agg backend needs QtSvg
    'PyQt5.QtSvg',
    # Scientific
    'numpy', 'CoolProp', 'CoolProp.CoolProp',
    # Pydantic + dependencies (needed for core/models.py)
    'pydantic', 'email', 'email.mime.text', 'email.mime.multipart',
    'email.parser', 'email.header', 'email.utils', 'email.message',
    'email.policy', 'importlib.metadata',
]

excludes = [
    'PyQt5.QtNetwork', 'PyQt5.QtQml',
    'PyQt5.QtSql', 'PyQt5.QtTest', 'PyQt5.QtXml',
    'PyQt5.QtWebEngine', 'PyQt5.QtWebSockets',
    'PyQt5.QtBluetooth', 'PyQt5.QtPositioning',
    'PyQt5.QtMultimedia', 'PyQt5.QtSensors',
    'xmlrpc', 'pydoc',
    'ensurepip', 'turtle', 'sqlite3',
    'scipy', 'sympy', 'pandas.io',
    'cv2',
]

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
    upx=False,
    console=False,
    icon=os.path.join(SPECPATH, '..', 'assets', 'icon.ico'),
    version=_VERSION_INFO_PATH,
)

coll = COLLECT(exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name=f'PSV_Sizing_Suite_{VERSION}'
)