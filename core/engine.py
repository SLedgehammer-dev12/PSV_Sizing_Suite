"""
Unified sizing engine.

Single entry point for all relief sizing calculations. Every interface
(desktop, Streamlit, FastAPI) should call ``size_relief_case`` so that the
service phase, valve type, capacity certification and overpressure scenario
select the method and correction factors in exactly one place.

Provenance (standard edition, method, factor basis, warnings) is attached to
every result under ``Result_Meta``.
"""
from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from .constants import ATMOSPHERIC_PSIA, PRELIM_KD_GAS, PRELIM_KD_LIQUID, NONCERTIFIED_KD_LIQUID
from .gas_relief import calculate_gas_relief_area
from .liquid_relief import calculate_liquid_relief_area
from .two_phase import calculate_two_phase_area, calculate_omega_flashing
from .valve_types import calculate_pilot_gas_area, calculate_pilot_liquid_area
from .kb_coefficient import get_kb, select_kb_curve
from .advanced_sizing import calculate_napier_steam_area

STANDARD_EDITION = "API 520 Part I 10th ed. (2020) + Errata 1 (2023)"

ServiceType = Literal["gas", "liquid", "steam", "two_phase"]
ValveType = Literal["conventional", "balanced_bellows", "pilot"]


class ReliefCase(BaseModel):
    """Canonical, interface-independent relief sizing case."""

    service: ServiceType

    # Common
    p1_psia: float = Field(gt=0, description="Relieving pressure (psia)")
    p2_psia: float = Field(ge=0, description="Total back pressure (psia)")
    set_pressure_psig: Optional[float] = Field(default=None, gt=0)
    overpressure_pct: float = Field(default=10.0, ge=1.0, le=50.0)
    num_valves: int = Field(default=1, ge=1, le=100)
    valve_type: ValveType = Field(default="conventional")
    capacity_certified: bool = Field(default=True)
    kc: float = Field(default=1.0, ge=0.1, le=1.0)
    atm_psia: float = Field(default=ATMOSPHERIC_PSIA, gt=0)

    # Gas / steam
    w_lb_h: Optional[float] = Field(default=None, gt=0)
    t_rankine: Optional[float] = Field(default=None, gt=0)
    z: float = Field(default=1.0, gt=0, le=2.0)
    mw: Optional[float] = Field(default=None, gt=0)
    k: float = Field(default=1.4, gt=1.0, le=2.5)
    kd: Optional[float] = Field(default=None, ge=0.1, le=1.0)
    kb: Optional[float] = Field(default=None, ge=0.1, le=1.0)
    use_napier: bool = Field(default=False)

    # Liquid
    q_gpm: Optional[float] = Field(default=None, gt=0)
    g: Optional[float] = Field(default=None, gt=0)
    mu_cp: float = Field(default=1.0, gt=0)
    kw: Optional[float] = Field(default=None, ge=0.1, le=1.0)
    kp: Optional[float] = Field(default=None, ge=0.5, le=1.5)

    # Two-phase
    v0_ft3_lb: Optional[float] = Field(default=None, gt=0)
    v9_ft3_lb: Optional[float] = Field(default=None, gt=0)
    omega: Optional[float] = Field(default=None, gt=0)


def _require(value, name):
    if value is None:
        raise ValueError(f"{name} is required for this service")
    return value


def _gas_kb(case: ReliefCase) -> Optional[float]:
    if case.kb is not None:
        return case.kb
    if case.valve_type in ("conventional", "pilot"):
        return 1.0
    if case.set_pressure_psig:
        return get_kb(case.p2_psia, case.set_pressure_psig, case.valve_type,
                      case.overpressure_pct, case.atm_psia)
    return None


def size_relief_case(case: ReliefCase) -> Dict[str, Any]:
    """
    Route a ReliefCase to the correct sizing method and return the result
    dict enriched with provenance under ``Result_Meta``.
    """
    warnings = []
    meta: Dict[str, Any] = {
        "Standard": STANDARD_EDITION,
        "Service": case.service,
        "Valve_Type": case.valve_type,
    }

    if case.service == "steam" or (case.service == "gas" and case.use_napier):
        result = calculate_napier_steam_area(
            w_lb_h=_require(case.w_lb_h, "w_lb_h"),
            p1_psia=case.p1_psia,
            p2_psia=case.p2_psia,
            t_rankine=case.t_rankine,
            kd=case.kd if case.kd is not None else PRELIM_KD_GAS,
            kb=_gas_kb(case) or 1.0,
            kc=case.kc,
            num_valves=case.num_valves,
        )
        meta.update({
            "Method": "Napier steam (API 520 Part I 5.7, Eq 25)",
            "Kd_Basis": "0.975 preliminary (steam)",
            "Kb_Basis": "Figure 31" if case.valve_type == "balanced_bellows" else "Kb = 1.0",
        })
        if case.t_rankine is None:
            warnings.append("No steam temperature supplied; KSH = 1.0 (saturated) assumed.")
        if case.p2_psia > 0.5 * case.p1_psia:
            warnings.append("Back pressure above ~50% of relieving pressure; verify critical flow with the manufacturer.")
        return _wrap(result, meta, warnings)

    if case.service == "gas":
        w = _require(case.w_lb_h, "w_lb_h")
        t = _require(case.t_rankine, "t_rankine")
        mw = _require(case.mw, "mw")

        if case.valve_type == "pilot":
            result = calculate_pilot_gas_area(
                w_lb_h=w, p1_psia=case.p1_psia, p2_psia=case.p2_psia,
                t_rankine=t, z=case.z, mw=mw, k=case.k,
                kc=case.kc, kb=case.kb,
                set_pressure_psig=case.set_pressure_psig,
                num_valves=case.num_valves,
                overpressure_pct=case.overpressure_pct,
            )
            meta.update({
                "Method": "Pilot-operated gas (API 520 Part I 5.6 + 7)",
                "Kd_Basis": "0.99 pilot-operated (API 520 Table 13)",
                "Kb_Basis": "Kb = 1.0 (pilot capacity independent of backpressure at critical flow)",
            })
            return _wrap(result, meta, warnings)

        kb = _gas_kb(case)
        if kb is None:
            warnings.append("No set pressure supplied; Kb = 1.0 assumed. Backpressure correction may be unconservative.")
            kb = 1.0
        elif case.valve_type == "balanced_bellows":
            _, basis = select_kb_curve(case.overpressure_pct)
            meta["Kb_Basis"] = f"Figure 31 {basis} overpressure curve"
        else:
            meta["Kb_Basis"] = "Kb = 1.0 (conventional, subcritical equation accounts for backpressure)"

        result = calculate_gas_relief_area(
            w_lb_h=w, p1_psia=case.p1_psia, p2_psia=case.p2_psia,
            t_rankine=t, z=case.z, mw=mw, k=case.k,
            kd=case.kd if case.kd is not None else PRELIM_KD_GAS,
            kb=kb, kc=case.kc, num_valves=case.num_valves,
        )
        meta.update({
            "Method": "Gas/vapor (API 520 Part I 5.6, Eq 6/16)",
            "Kd_Basis": f"{case.kd if case.kd is not None else PRELIM_KD_GAS} ({'certified' if case.kd else 'preliminary 0.975'})",
        })
        if kb < 1.0 and case.p2_psia > case.atm_psia:
            warnings.append(
                "Balanced bellows backpressure correction applied. Final capacity shall be verified "
                "with the manufacturer's certified Kd and actual orifice area."
            )
        return _wrap(result, meta, warnings)

    if case.service == "liquid":
        q = _require(case.q_gpm, "q_gpm")
        g = _require(case.g, "g")

        if case.valve_type == "pilot":
            result = calculate_pilot_liquid_area(
                q_gpm=q, p1_psia=case.p1_psia, p2_psia=case.p2_psia,
                g=g, mu_cp=case.mu_cp, kw=case.kw or 1.0, num_valves=case.num_valves,
            )
            meta.update({
                "Method": "Pilot-operated liquid (API 520 Part I 5.8 + 7)",
                "Kd_Basis": "0.80 pilot-operated liquid",
                "Kv_Basis": "Kv = 1.0 (viscosity <= 100 cP per 5.8.1.3)",
            })
            return _wrap(result, meta, warnings)

        if case.capacity_certified:
            kd = case.kd if case.kd is not None else PRELIM_KD_LIQUID
            meta.update({
                "Method": "Liquid, capacity certified (API 520 Part I 5.8, Eq 32)",
                "Kd_Basis": f"{kd} (certified/preliminary)",
                "Kp_Basis": "Not used for certified liquid valves",
                "Kv_Basis": "Kv = 1.0 when mu <= 100 cP; Figure 38/Eq 34 otherwise",
            })
        else:
            kd = NONCERTIFIED_KD_LIQUID
            meta.update({
                "Method": "Liquid, capacity NOT certified (API 520 Part I 5.9, Eq 42)",
                "Kd_Basis": f"{NONCERTIFIED_KD_LIQUID} (required by 5.9)",
                "Kp_Basis": "Figure 39 (Kp = 1.0 at 25% overpressure)",
                "Kv_Basis": "Kv = 1.0 when mu <= 100 cP",
            })
            warnings.append(
                "Noncertified liquid sizing per 5.9 typically oversizes at 10% overpressure; "
                "overpressures below 10% shall be avoided."
            )

        result = calculate_liquid_relief_area(
            q_gpm=q, p1_psia=case.p1_psia, p2_psia=case.p2_psia,
            g=g, mu_cp=case.mu_cp, kd=kd, kw=case.kw, kc=case.kc,
            num_valves=case.num_valves, kp=case.kp,
            overpressure_pct=case.overpressure_pct,
            valve_type=case.valve_type,
            set_pressure_psig=case.set_pressure_psig,
            atm_psia=case.atm_psia,
            capacity_certified=case.capacity_certified,
        )
        if result.get("Kw", 1.0) < 1.0:
            warnings.append("Balanced bellows Kw correction applied (Figure 32).")
        if result.get("Re_Below_80"):
            warnings.append("Reynolds number below 80; Eq 34 validity limit (Re >= 80) exceeded — engineering review required.")
        return _wrap(result, meta, warnings)

    if case.service == "two_phase":
        w = _require(case.w_lb_h, "w_lb_h")
        v0 = _require(case.v0_ft3_lb, "v0_ft3_lb")
        if case.omega is None:
            v9 = _require(case.v9_ft3_lb, "v9_ft3_lb")
            omega = calculate_omega_flashing(v0, v9)
        else:
            omega = case.omega

        kb = case.kb
        if kb is None:
            if case.valve_type == "balanced_bellows" and case.set_pressure_psig:
                kb = get_kb(case.p2_psia, case.set_pressure_psig,
                            "balanced_bellows", case.overpressure_pct, case.atm_psia)
            else:
                kb = 1.0

        result = calculate_two_phase_area(
            w_lb_h=w, p0_psia=case.p1_psia, p_back_psia=case.p2_psia,
            v0_ft3_lb=v0, omega=omega, kd=case.kd if case.kd is not None else 0.85,
            kb=kb, kc=case.kc, num_valves=case.num_valves,
        )
        meta.update({
            "Method": "Two-phase Omega method (API 520 Part I Annex C)",
            "Kd_Basis": f"{case.kd if case.kd is not None else 0.85} (effective, no certified two-phase capacities exist)",
            "Kb_Basis": "Figure 31" if kb != 1.0 else "Kb = 1.0",
            "v9_Basis": "User flash value" if case.v9_ft3_lb is not None else "omega supplied directly",
        })
        warnings.append(
            "No PRDs have certified capacities for two-phase flow; final selection requires "
            "manufacturer/vendor confirmation."
        )
        return _wrap(result, meta, warnings)

    raise ValueError(f"Unsupported service: {case.service}")


def _wrap(result: Dict[str, Any], meta: Dict[str, Any], warnings) -> Dict[str, Any]:
    result = dict(result)
    result["Result_Meta"] = {**meta, "Warnings": list(warnings)}
    result["Verification_Status"] = "preliminary-verified" if not warnings else "review-required"
    return result


__all__ = ["ReliefCase", "size_relief_case", "STANDARD_EDITION"]
