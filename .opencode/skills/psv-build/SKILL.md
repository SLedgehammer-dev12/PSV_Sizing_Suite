---
name: psv-build
description: Builds PSV Sizing Suite Desktop and Web EXEs with PyInstaller, creates release ZIPs, and updates the GitHub release. USE FOR: build exe, create release, deploy, package, compile, release v2.3.0, build desktop, build web, upload release.
---

# PSV Sizing Suite — Build & Release

## Overview
Build the PSV Sizing Suite into distributable Windows executables using PyInstaller, create release ZIP archives, and update the GitHub release.

## Prerequisites
- PyInstaller installed (`pip install pyinstaller`)
- `gh` CLI authenticated (`gh auth status`)
- All tests passing (use `psv-verify` skill first)
- Working directory: project root

## Workflow

### Step 1: Verify tests pass
```bash
python -m pytest tests/test_suite.py -v
```
Must be 100/100 passing before building.

### Step 2: Clean previous builds
```bash
Remove-Item -Recurse -Force "dist", "build" -ErrorAction SilentlyContinue
```

### Step 3: Build Desktop EXE
```bash
pyinstaller --name PSV_Sizing_Suite_Desktop_v2.3.0_Windows --windowed --add-data "core;core" --add-data "desktop;desktop" --add-data "vendor_data;vendor_data" --hidden-import core --hidden-import core.thermo_props --hidden-import core.unit_converter --hidden-import core.vendor_catalog --hidden-import bcrypt main.py -y
```

### Step 4: Build Web EXE
```bash
pyinstaller --name PSV_Sizing_Suite_Web_v2.3.0_Windows --windowed --add-data "core;core" --add-data "web_app.py;." --hidden-import core --hidden-import core.thermo_props --hidden-import core.unit_converter --hidden-import core.vendor_catalog --hidden-import bcrypt run_streamlit.py -y
```

### Step 5: Create release ZIPs
```bash
Compress-Archive -Path "dist\PSV_Sizing_Suite_Desktop_v2.3.0_Windows\*" -DestinationPath "releases\PSV_Sizing_Suite_Desktop_v2.3.0_Windows.zip" -Force
Compress-Archive -Path "dist\PSV_Sizing_Suite_Web_v2.3.0_Windows\*" -DestinationPath "releases\PSV_Sizing_Suite_Web_v2.3.0_Windows.zip" -Force
```

### Step 6: Update GitHub release
First delete old assets, then upload new ones:
```bash
gh release delete-asset v2.3.0 "PSV_Sizing_Suite_Desktop_v2.3.0_Windows.zip" --yes
gh release delete-asset v2.3.0 "PSV_Sizing_Suite_Web_v2.3.0_Windows.zip" --yes
gh release upload v2.3.0 "releases\PSV_Sizing_Suite_Desktop_v2.3.0_Windows.zip" "releases\PSV_Sizing_Suite_Web_v2.3.0_Windows.zip" --clobber
```

### Step 7: Update release notes
```bash
gh release edit v2.3.0 --notes "<release notes markdown>"
```

Include in release notes:
- Version number (v2.3.0)
- What's New section with features and fixes
- Security improvements
- Engineering fixes
- Test status (100/100)
- Build verification

## Troubleshooting
- **ImportError during build**: Add missing modules to `--hidden-import`
- **vendor_data not found at runtime**: Verify `--add-data "vendor_data;vendor_data"` is present
- **bcrypt not found**: Verify `--hidden-import bcrypt` and bcrypt >= 4.1 installed
- **gh CLI not authenticated**: Run `gh auth login` first
- **Asset already exists**: Use `--clobber` flag with `gh release upload`
