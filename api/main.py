"""
FastAPI application for PSV Sizing Suite.

Provides REST endpoints for all core engineering calculations.
"""
import sys
import os
from typing import Dict, List, Optional, Union

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from core import __version__
from core.models import (
    LiquidReliefInput, GasReliefInput, TwoPhaseInput,
    FireWettedInput, FireUnwettedInput, ThermalExpansionInput,
    PipingInletInput, ConvertInput,
)
from core.liquid_relief import calculate_liquid_relief_area
from core.gas_relief import calculate_gas_relief_area
from core.two_phase import (
    calculate_two_phase_area,
    calculate_omega_flashing,
    calculate_omega_subcooled,
)
from core.fire_scenarios import (
    calculate_fire_wetted_load,
    calculate_fire_unwetted_area,
    calculate_heat_absorption,
    get_env_factor,
)
from core.thermal_expansion import calculate_thermal_expansion_load
from core.blowby import calculate_blowby_flowrate
from core.valve_selection import select_orifice, API_ORIFICE_AREAS
from core.vendor_catalog import get_vendor_valves
from core.kb_coefficient import get_kb, KB_BALANCED_BELLOWS_10PCT, KB_BALANCED_BELLOWS_25PCT
from core.piping import calculate_inlet_pressure_drop, check_inlet_rule, check_outlet_rule
from core.valve_types import calculate_pilot_gas_area, calculate_pilot_liquid_area
from core.units import convert, HAS_PINT

app = FastAPI(
    title="PSV Sizing Suite API",
    description="Pressure Safety Valve sizing calculations per API 520/521",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# All request/response models are imported from core.models.
# Endpoint-specific aliases kept for backward compatibility.
LiquidReliefRequest = LiquidReliefInput
GasReliefRequest = GasReliefInput
TwoPhaseRequest = TwoPhaseInput
FireWettedRequest = FireWettedInput
FireUnwettedRequest = FireUnwettedInput
ThermalExpansionRequest = ThermalExpansionInput
PipingCheckRequest = PipingInletInput
ConvertRequest = ConvertInput


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    return {
        "app": "PSV Sizing Suite API",
        "version": __version__,
        "standards": ["API 520 Part I", "API 521", "ASME Section VIII"],
        "units_backend": "pint" if HAS_PINT else "fallback",
        "endpoints": {
            "/api/v1/liquid-relief": "Liquid relief sizing",
            "/api/v1/gas-relief": "Gas/vapor relief sizing",
            "/api/v1/two-phase": "Two-phase (Omega method) sizing",
            "/api/v1/fire-wetted": "Fire wetted relief sizing",
            "/api/v1/fire-unwetted": "Fire unwetted relief sizing",
            "/api/v1/thermal-expansion": "Thermal expansion relief sizing",
            "/api/v1/piping-check": "Inlet/outlet piping pressure drop check",
            "/api/v1/convert": "Unit conversion",
            "/api/v1/orifices": "List API orifice areas",
            "/api/v1/valves/{letter}": "Vendor valves for orifice letter",
            "/api/v1/kb-curve": "Kb back pressure correction curve",
        },
    }


@app.post("/api/v1/liquid-relief")
async def liquid_relief(req: LiquidReliefRequest):
    try:
        return calculate_liquid_relief_area(
            q_gpm=req.q_gpm,
            p1_psia=req.p1_psia,
            p2_psia=req.p2_psia,
            g=req.g,
            mu_cp=req.mu_cp,
            kd=req.kd,
            kw=req.kw,
            num_valves=req.num_valves,
            valve_type=req.valve_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/gas-relief")
async def gas_relief(req: GasReliefRequest):
    try:
        return calculate_gas_relief_area(
            w_lb_h=req.w_lb_h,
            p1_psia=req.p1_psia,
            p2_psia=req.p2_psia,
            t_rankine=req.t_rankine,
            z=req.z,
            mw=req.mw,
            k=req.k,
            kd=req.kd,
            kb=req.kb,
            kc=req.kc,
            num_valves=req.num_valves,
            valve_type=req.valve_type,
            set_pressure_psig=req.set_pressure_psig,
        )
    except (ValueError, ZeroDivisionError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/two-phase")
async def two_phase(req: TwoPhaseRequest):
    try:
        if req.omega is None:
            if req.v9_ft3_lb is None:
                raise HTTPException(status_code=400, detail="Either omega or v9 must be provided")
            omega = calculate_omega_flashing(req.v0_ft3_lb, req.v9_ft3_lb)
        else:
            omega = req.omega

        return calculate_two_phase_area(
            w_lb_h=req.w_lb_h,
            p0_psia=req.p0_psia,
            p_back_psia=req.p_back_psia,
            v0_ft3_lb=req.v0_ft3_lb,
            omega=omega,
            kd=req.kd,
            num_valves=req.num_valves,
            valve_type=req.valve_type,
            set_pressure_psig=req.set_pressure_psig,
            overpressure_pct=req.overpressure_pct,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/fire-wetted")
async def fire_wetted(req: FireWettedRequest):
    try:
        w_lb_h, q_btu_h = calculate_fire_wetted_load(
            a_wetted_sqft=req.a_wetted_sqft,
            f_factor=req.f_factor,
            heat_of_vap_btu_lb=req.heat_of_vap_btu_lb,
        )

        gas_res = calculate_gas_relief_area(
            w_lb_h=w_lb_h,
            p1_psia=req.p1_psia,
            p2_psia=req.p2_psia,
            t_rankine=req.t_rankine,
            z=req.z,
            mw=req.mw,
            k=req.k,
        )
        gas_res['valve_type'] = 'conventional'
        gas_res['Relief_Load_lb_h'] = w_lb_h
        gas_res['Heat_Absorption_Btu_h'] = q_btu_h
        return gas_res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/fire-unwetted")
async def fire_unwetted(req: FireUnwettedRequest):
    try:
        a_req, f_prime = calculate_fire_unwetted_area(
            a_exposed_sqft=req.a_exposed_sqft,
            p1_psia=req.p1_psia,
            t_gas_rankine=req.t_gas_rankine,
            t_wall_rankine=req.t_wall_rankine,
            k=req.k,
            kd=req.kd,
            alpha=req.alpha,
        )
        from core.valve_selection import select_orifice as _select
        letter, selected_area = _select(a_req)
        return {
            'F_Prime': f_prime,
            'Required_Area_sqin': a_req,
            'Selected_Orifice_Letter': letter,
            'Selected_Orifice_Area_sqin': selected_area,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/thermal-expansion")
async def thermal_expansion(req: ThermalExpansionRequest):
    try:
        q_gpm = calculate_thermal_expansion_load(
            b_expansion_coeff=req.b_expansion_coeff,
            h_heat_transfer_btu_h=req.h_heat_transfer_btu_h,
            g_specific_gravity=req.g_specific_gravity,
            c_specific_heat=req.c_specific_heat,
        )
        res = calculate_liquid_relief_area(
            q_gpm=q_gpm,
            p1_psia=req.p1_psia,
            p2_psia=req.p2_psia,
            g=req.g_specific_gravity,
            mu_cp=req.mu_cp,
        )
        res['Relief_Load_gpm'] = q_gpm
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/piping-check")
async def piping_check(req: PipingCheckRequest):
    try:
        inlet = calculate_inlet_pressure_drop(
            flow_gpm=req.flow_gpm or req.flow_rate_lb_h,
            fluid_density_lb_ft3=req.fluid_density_lb_ft3,
            viscosity_cp=req.viscosity_cp,
            pipe_id_in=req.pipe_id_in,
            pipe_length_ft=req.pipe_length_ft,
            fittings_90deg=req.fittings_90deg,
            fittings_45deg=req.fittings_45deg,
            gate_valves=req.gate_valves,
        )
        passes, pct = check_inlet_rule(inlet["delta_p_psi"], req.set_pressure_psig, req.valve_type)
        return {
            **inlet,
            "api_520_rule_pass": passes,
            "delta_p_pct_of_set": pct,
            "limit_pct": 1.5 if req.valve_type == "pilot" else 3.0,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/orifices")
async def list_orifices():
    return {
        "standard": "API 526 / API 520",
        "orifices": [{"letter": k, "area_sqin": v} for k, v in API_ORIFICE_AREAS.items()],
    }


@app.get("/api/v1/valves/{api_letter}")
async def get_valves(api_letter: str):
    valves = get_vendor_valves(api_letter.upper())
    if not valves:
        raise HTTPException(status_code=404, detail=f"No valves found for orifice {api_letter}")
    return {"api_letter": api_letter.upper(), "count": len(valves), "valves": valves}


@app.get("/api/v1/kb-curve")
async def kb_curve(valve_type: str = "balanced_bellows", overpressure: float = 10.0):
    if valve_type == "conventional":
        return {"valve_type": "conventional", "kb": 1.0}
    curve = KB_BALANCED_BELLOWS_10PCT if overpressure <= 15 else KB_BALANCED_BELLOWS_25PCT
    return {"valve_type": valve_type, "overpressure_pct": overpressure, "curve": curve}


@app.post("/api/v1/convert")
async def unit_convert(req: ConvertRequest):
    try:
        result = convert(req.value, req.from_unit, req.to_unit)
        return {"value": req.value, "from": req.from_unit, "to": req.to_unit, "result": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/env-factors")
async def env_factors():
    from core.fire_scenarios import ENV_FACTORS
    return ENV_FACTORS


@app.get("/health")
async def health():
    return {"status": "healthy", "units_backend": "pint" if HAS_PINT else "fallback"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)