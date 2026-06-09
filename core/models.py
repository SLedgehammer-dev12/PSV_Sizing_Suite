from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any, Literal


# =============================================================================
# Input Models
# =============================================================================

class LiquidReliefInput(BaseModel):
    q_gpm: float = Field(gt=0, description="Flow rate (US GPM)")
    p1_psia: float = Field(gt=0, description="Relieving pressure (psia)")
    p2_psia: float = Field(ge=0, description="Back pressure (psia)")
    g: float = Field(gt=0, description="Specific gravity")
    mu_cp: float = Field(default=1.0, gt=0, description="Viscosity (cP)")
    kd: float = Field(default=0.65, ge=0.1, le=1.0, description="Discharge coefficient")
    kw: float = Field(default=1.0, ge=0.1, le=1.0, description="Back pressure capacity correction")
    num_valves: int = Field(default=1, ge=1, le=100, description="Number of parallel valves")
    valve_type: Literal["conventional", "balanced_bellows", "pilot"] = Field(default="conventional", description="Valve type")


class GasReliefInput(BaseModel):
    w_lb_h: float = Field(gt=0, description="Mass flow rate (lb/h)")
    p1_psia: float = Field(gt=0, description="Relieving pressure (psia)")
    p2_psia: float = Field(ge=0, description="Back pressure (psia)")
    t_rankine: float = Field(gt=0, description="Relieving temperature (Rankine)")
    z: float = Field(default=1.0, gt=0, le=3.0, description="Compressibility factor")
    mw: float = Field(gt=0, description="Molecular weight")
    k: float = Field(gt=1.0, le=2.0, description="Specific heat ratio (Cp/Cv)")
    kd: float = Field(default=0.975, ge=0.1, le=1.0, description="Discharge coefficient")
    kb: Optional[float] = Field(None, description="Back pressure correction (auto if None)")
    kc: float = Field(default=1.0, ge=0.1, le=1.0, description="Combination correction factor")
    num_valves: int = Field(default=1, ge=1, le=100, description="Number of parallel valves")
    valve_type: Literal["conventional", "balanced_bellows", "pilot"] = Field(default="conventional")
    set_pressure_psig: Optional[float] = Field(None, description="Set pressure for Kb calculation")
    overpressure_pct: float = Field(default=10.0, ge=1.0, le=50.0, description="Percent overpressure")
    is_steam: bool = Field(default=False, description="Use Napier steam formula")
    use_napier: bool = Field(default=False, description="Use Napier as primary sizing method")


class TwoPhaseInput(BaseModel):
    w_lb_h: float = Field(gt=0, description="Mass flow rate (lb/h)")
    p0_psia: float = Field(gt=0, description="Stagnation relieving pressure (psia)")
    p_back_psia: float = Field(ge=0, description="Back pressure (psia)")
    v0_ft3_lb: float = Field(gt=0, description="Specific volume at inlet (ft3/lb)")
    v9_ft3_lb: Optional[float] = Field(None, description="Specific vol at 90% P0 (ft3/lb)")
    omega: Optional[float] = Field(None, ge=0.01, description="Omega parameter (calc from v0/v9 if None)")
    kd: float = Field(default=0.85, ge=0.1, le=1.0, description="Discharge coefficient")
    num_valves: int = Field(default=1, ge=1, le=100)
    valve_type: Literal["conventional", "balanced_bellows", "pilot"] = Field(default="conventional")
    set_pressure_psig: Optional[float] = Field(None)
    overpressure_pct: float = Field(default=10.0, ge=1.0, le=50.0)


class FireWettedInput(BaseModel):
    a_wetted_sqft: float = Field(gt=0, description="Wetted surface area (sqft)")
    f_factor: float = Field(default=1.0, gt=0, le=1.0, description="Environment factor")
    heat_of_vap_btu_lb: float = Field(gt=0, description="Latent heat of vaporization (Btu/lb)")
    p1_psia: float = Field(gt=0, description="Relieving pressure (psia)")
    p2_psia: float = Field(default=14.6959, ge=0, description="Back pressure (psia)")
    t_rankine: float = Field(gt=0, description="Gas temperature (Rankine)")
    z: float = Field(default=0.9, gt=0, le=3.0, description="Compressibility")
    mw: float = Field(gt=0, description="Molecular weight")
    k: float = Field(gt=1.0, le=2.0, description="Specific heat ratio")
    adequate_drainage: bool = Field(default=True, description="Adequate drainage and firefighting")
    wetted_area_cap: Optional[float] = Field(default=2800.0, description="Max wetted area cap (sqft)")


class FireUnwettedInput(BaseModel):
    a_exposed_sqft: float = Field(gt=0, description="Exposed area (sqft)")
    p1_psia: float = Field(gt=0, description="Relieving pressure (psia)")
    t_gas_rankine: float = Field(gt=0, description="Gas temperature (Rankine)")
    t_wall_rankine: float = Field(gt=0, description="Wall temperature (Rankine)")
    k: float = Field(gt=1.0, le=2.0, description="Specific heat ratio")
    kd: float = Field(default=0.975, ge=0.1, le=1.0, description="Discharge coefficient")
    alpha: float = Field(default=0.5, ge=0.1, le=1.0, description="Radiation absorptivity")


class ThermalExpansionInput(BaseModel):
    b_expansion_coeff: float = Field(gt=0, description="Cubical expansion coefficient (1/°F)")
    h_heat_transfer_btu_h: float = Field(gt=0, description="Heat transfer rate (BTU/h)")
    g_specific_gravity: float = Field(gt=0, description="Specific gravity")
    c_specific_heat: float = Field(gt=0, description="Specific heat (BTU/lb°F)")
    mu_cp: float = Field(default=1.0, gt=0, description="Viscosity (cP)")
    p1_psia: float = Field(gt=0, description="Relieving pressure (psia)")
    p2_psia: float = Field(ge=0, description="Back pressure (psia)")


class PipingInletInput(BaseModel):
    flow_gpm: Optional[float] = Field(None, ge=0, description="Volumetric flow (US GPM)")
    flow_rate_lb_h: Optional[float] = Field(None, gt=0, description="Mass flow (lb/h)")
    fluid_density_lb_ft3: float = Field(gt=0, description="Fluid density (lb/ft3)")
    viscosity_cp: float = Field(gt=0, description="Fluid viscosity (cP)")
    pipe_id_in: float = Field(gt=0, description="Pipe inner diameter (inches)")
    pipe_length_ft: float = Field(ge=0, description="Straight pipe length (ft)")
    set_pressure_psig: float = Field(gt=0, description="Valve set pressure (psig)")
    fittings_90deg: int = Field(default=0, ge=0, description="Number of 90° elbows")
    fittings_45deg: int = Field(default=0, ge=0, description="Number of 45° elbows")
    gate_valves: int = Field(default=0, ge=0, description="Number of gate valves")
    roughness_in: float = Field(default=0.00015, ge=0, description="Pipe roughness (inches)")
    valve_type: Literal["conventional", "pilot"] = Field(default="conventional")
    remote_sensing: bool = Field(default=False, description="Remote sensing line for pilot valve")


class ConvertInput(BaseModel):
    value: float
    from_unit: str
    to_unit: str


# =============================================================================
# Output Models
# =============================================================================

class ReliefOutput(BaseModel):
    Required_Area_sqin: float
    Selected_Orifice_Letter: str
    Selected_Orifice_Area_sqin: float
    Num_Valves: int = 1


class LiquidReliefOutput(ReliefOutput):
    Required_Area_No_Visc_sqin: float
    Reynolds_Number: float
    Kv: float


class GasReliefOutput(ReliefOutput):
    Flow_Type: str
    Critical_Pressure_psia: float
    C_Coefficient: Optional[float] = None
    F2_Coefficient: Optional[float] = None
    Kb_Factor: float = 1.0


class TwoPhaseOutput(ReliefOutput):
    Omega: float
    Critical_Pressure_Ratio_hc: float
    Critical_Pressure_psia: float
    Flow_Type: str
    Mass_Flux_G_lb_s_ft2: float
    Kb: float = 1.0


class FireWettedOutput(BaseModel):
    Heat_Absorption_Btu_h: float
    Relief_Load_lb_h: float
    Required_Area_sqin: float
    Selected_Orifice_Letter: str
    Selected_Orifice_Area_sqin: float
    Flow_Type: str
    C_Coefficient: Optional[float] = None
    Kb_Factor: float = 1.0


class PipingOutput(BaseModel):
    delta_p_psi: float
    velocity_fps: float
    reynolds: float
    friction_factor: float
    equivalent_length_ft: float
    flow_gpm: Optional[float] = None
    flow_rate_lb_h: Optional[float] = None
    api_520_rule_pass: bool
    delta_p_pct_of_set: float
    limit_pct: float


class HealthOutput(BaseModel):
    status: str
    units_backend: str


__all__ = [
    "LiquidReliefInput", "GasReliefInput", "TwoPhaseInput",
    "FireWettedInput", "FireUnwettedInput", "ThermalExpansionInput",
    "PipingInletInput", "ConvertInput",
    "ReliefOutput", "LiquidReliefOutput", "GasReliefOutput",
    "TwoPhaseOutput", "FireWettedOutput", "PipingOutput", "HealthOutput",
]
