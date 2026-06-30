# PSV Sizing Suite — Agent Instructions

## Project Overview
Advanced engineering calculation platform for Pressure Safety Valve (PSV) sizing based on API 520 Part I and API 521 standards. Contains 6 calculation modules, a PyQt5 desktop app, and a Streamlit web app.

## Repository
- **GitHub**: https://github.com/SLedgehammer-dev12/PSV_Sizing_Suite
- **Current version**: v2.2

## Codebase Conventions

### Language & Style
- Python 3.12+
- English variable names, Turkish UI labels
- Minimal comments — code should be self-documenting
- Use `core.constants` for all magic numbers, never hardcode
- Import unit converters from `core.unit_converter`, never use raw conversion factors

### Directory Structure
```
core/           Engineering calculation engine (API 520/521 formulas)
desktop/        PyQt5 desktop application (tabs, workers, auth, reports)
tests/          Pytest test suite (100 tests in test_suite.py)
vendor_data/    PSV vendor catalog JSON
scripts/        Utility scripts (moved from root)
releases/       Build artifacts (ZIP files)
```

### Testing
- Run: `python -m pytest tests/test_suite.py -v`
- Must be 100/100 passing before any build
- Smoke tests cover full calculation flows
- Auth tests use temporary auth.json

### Build
- Desktop: `pyinstaller --name PSV_Sizing_Suite_Desktop_v2.2_Windows --windowed --add-data "core;core" --add-data "desktop;desktop" --add-data "vendor_data;vendor_data" --hidden-import core ... main.py -y`
- Web: `pyinstaller --name PSV_Sizing_Suite_Web_v2.2_Windows --windowed --add-data "core;core" --add-data "web_app.py;." --hidden-import core ... run_streamlit.py -y`

## Key Decisions Made
1. **Deferred BaseCalcTab refactor** — Too risky, ~1000 lines duplicated acceptable for now
2. **urllib over requests** — No external deps for update check
3. **PBKDF2 over SHA-256** — Password hashing fallback when bcrypt unavailable
4. **8-char min password** — Enforced at password change
5. **5-attempt lockout** — 5 min lockout after 5 failed login attempts

## Sensitive Areas
- `desktop/auth.py` — Do NOT weaken password policies or remove brute-force protection
- `core/unit_converter.py` — Do NOT change converter formulas without verifying against API standards
- `core/constants.py` — Constants must match API 520/521 exactly
- `desktop/report_generator.py` — Must always use `html.escape()` on user data

## When Making Changes
1. Read surrounding code to match existing patterns
2. Run test suite after every change batch
3. Never commit secrets, auth.json, or build artifacts
4. Use `core.constants` imports, never hardcode conversion factors
5. Turkish UI strings: use English characters (no ı, ş, ç, ğ, ü, ö) for cross-platform compatibility

## Available Agents
- `psv-core` — Engineering calculation expert
- `psv-desktop` — PyQt5 desktop app expert
- `psv-auditor` — Security/code quality auditor

## Available Skills
- `psv-audit` — Full project audit (launches all 3 agents)
- `psv-verify` — Run tests and analyze results
- `psv-build` — Build EXEs and create GitHub release
- `psv-calculate` — Trace a calculation through the full pipeline
