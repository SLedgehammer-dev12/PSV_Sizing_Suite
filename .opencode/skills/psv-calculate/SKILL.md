---
name: psv-calculate
description: Validates a specific PSV sizing calculation end-to-end. Traces input through unit conversion, validation, core calculation, valve selection, and output. USE FOR: verify calculation, check sizing, validate formula, trace calculation, test a scenario, engineering verification, check result.
---

# PSV Sizing Suite — Calculation Verification

## Overview
Trace a specific PSV sizing scenario through the full pipeline: input → unit conversion → validation → core calculation → orifice selection → output. Verify that every step produces the expected result per API 520/521.

## Supported calculation types
1. **Liquid Relief** (`core/liquid_relief.py`) — Reynolds + Kv iterative sizing
2. **Gas/Vapor Relief** (`core/gas_relief.py`) — Critical/subcritical with C and F2 coefficients
3. **Two-Phase Flashing** (`core/two_phase.py`) — Omega method, eta_c, mass flux G
4. **Fire Wetted** (`core/fire_scenarios.py` + `core/gas_relief.py`) — Heat absorption → gas relief
5. **Fire Unwetted** (`core/fire_scenarios.py`) — Wall-to-gas temperature-driven
6. **Thermal Expansion** (`core/thermal_expansion.py` + `core/liquid_relief.py`) — Thermal load → liquid relief

## Workflow

### Step 1: Identify the calculation path
Read the relevant core module(s) to understand the formula chain.

### Step 2: Trace inputs
For each input parameter:
- What unit does the user enter? (barg, kg/h, °C, m3/kg, etc.)
- Which converter function transforms it?
- What is the expected output unit? (psia, lb/h, °R, ft3/lb, etc.)

### Step 3: Verify conversion
Check the converter function for correctness:
```python
from core.unit_converter import barg_to_psia
result = barg_to_psia(1.0)  # Should be 14.6959 + 14.50377 = 29.19967 ???
# Actually: barg_to_psia(barg) = (barg * PSIA_PER_BAR) + ATMOSPHERIC_PSIA
# 1.0 barg → (1.0 * 14.50377) + 14.6959 = 29.19967 psia ✓
```

### Step 4: Verify validation
Check that `validation.py` catches invalid inputs:
- Negative flow rates
- P2 >= P1
- Out-of-range k, Z, Kd, Kw
- Zero viscosity (should be rejected now)

### Step 5: Verify core formula
Compare the implemented formula against the API 520/521 standard:
```
API 520 Liquid Relief (US units):
A = (Q / (38 * Kd * Kw * Kv)) * sqrt(G / (P1 - P2))
```

### Step 6: Verify orifice selection
Check that `valve_selection.py` selects the correct next-largest API orifice:
- Area 0.05 → 'D' (0.110 sq.in)
- Area 0.15 → 'E' (0.196 sq.in)
- Area 10.0 → 'Q' (11.05 sq.in)
- Area 30.0 → 'Multiple Valves Required'

### Step 7: Cross-check with known test cases
Compare against existing test cases in `tests/test_suite.py`:
- `test_liquid_relief` → liquid calculation
- `test_gas_relief` → gas calculation
- `test_two_phase` → two-phase calculation
- `test_fire_wetted` / `test_fire_unwetted` → fire scenarios
- `test_thermal_expansion` → thermal relief

## Known constants (from `core/constants.py`)
| Constant | Value | Source |
|----------|-------|--------|
| LIQUID_FORMULA_CONSTANT | 38.0 | API 520 eq. 28 (US units) |
| GAS_FORMULA_CONSTANT | 520.0 | API 520 eq. 32 C coefficient |
| GAS_SUBCRITICAL_CONSTANT | 735.0 | API 520 eq. 34 F2 factor |
| TWO_PHASE_CRITICAL_CONSTANT | 68.09 | API 520 eq. C.2 |
| TWO_PHASE_AREA_CONSTANT | 25.0 | API 520 eq. C.3 denominator |
| FIRE_WETTED_HEAT_CONSTANT | 21000.0 | API 521 eq. 18 |
| FIRE_UNWETTED_COEFF | 0.1406 | API 521 eq. 20 |
| PSIA_PER_BAR | 14.50377 | 1 bar = 14.50377 psi |
| ATMOSPHERIC_PSIA | 14.6959 | 1 atm at sea level |

## Checking unit correctness
The most common bugs are unit errors. Always verify:
1. Pressure: barg → psia (add ATMOSPHERIC_PSIA), bara → psia (multiply by PSIA_PER_BAR), bara → barg (subtract 1 atm in bar units)
2. Temperature: °C → °R (multiply by 1.8, add 491.67)
3. Flow: kg/h → lb/h (multiply by 2.204623), m3/h → gpm (multiply by 4.402868)
4. Density: m3/kg → ft3/lb (multiply by 16.01846)
5. Energy: kW → Btu/h (multiply by 3412.142), kcal/h → Btu/h (multiply by 3.96832)
