---
name: psv-verify
description: Runs the PSV Sizing Suite test suite and verifies correctness. Checks for test failures, evaluates test quality, identifies coverage gaps, and suggests new tests. USE FOR: run tests, check tests, verify code, test suite, validate changes, regression check, coverage analysis, test quality.
---

# PSV Sizing Suite — Test & Verification

## Overview
Run the complete test suite and analyze results. Identify failing tests, missing coverage, and brittle tests.

## Workflow

### Step 1: Run the test suite
```bash
python -m pytest tests/test_suite.py -v
```

### Step 2: Analyze results
Check for:
- **FAILURES**: Exact test names and failure reasons
- **ERRORS**: Import errors, missing dependencies
- **SKIPS**: Tests that are skipped (check if intentional)
- **PASS count**: Should be 100/100

### Step 3: If failures found
1. Read the failing test code in `tests/test_suite.py`
2. Identify the root cause (code change vs test fragility)
3. Fix the code OR fix the test (never fix a correct test to match broken code)
4. Re-run until 100/100 pass

### Step 4: Test quality evaluation
After all pass, evaluate:
- **Brittle tests**: Tests that grep source code strings rather than testing behavior
- **Missing assertions**: Tests that pass but don't actually verify correctness
- **Coverage gaps**: Untested modules, functions, and edge cases
- **Negative tests**: Error paths not exercised

### Step 5: Smoke test (optional)
For web app changes:
```bash
# Start streamlit in background, check port 8501 responds
python run_streamlit.py &
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501
```

## Key test files
- `tests/test_suite.py` — 116 tests covering core, validation, edge cases, converters, auth, smoke, version, save/load, report, update check

## Known test categories
| Class | Tests | Focus |
|-------|-------|-------|
| TestPSVSizingCore | 12 | Core calculations + vendor catalog |
| TestValidation | 11 | Input validation edge cases |
| TestEdgeCases | 15 | Numerical boundary conditions |
| TestUnitConverters | 17 | Unit conversion correctness |
| TestAuth | 8 | Authentication flow |
| TestSmokeTest | 9 | End-to-end calculation flows |
| TestVersionConsistency | 3 | Version string checks |
| TestGasCompositionRequirement | 3 | Gas composition handling |
| TestWebAppConfig | 2 | Streamlit configuration |
| TestSchemaVersion | 3 | Schema versioning |
| TestErrorHandler | 1 | Exception handling pattern |
| TestSaveLoad | 2 | Save/load project |
| TestReportGenerator | 3 | HTML report safety |
| TestUpdateCheck | 10 | GitHub update check logic |
