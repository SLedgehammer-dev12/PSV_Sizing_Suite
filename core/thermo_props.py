import CoolProp.CoolProp as CP

def calculate_mixture_properties(composition_dict, t_rankine, p_psia, fraction_type="mole"):
    """
    composition_dict: dict of fluid fractions (0 to 1) e.g. {'Methane': 0.8, 'Ethane': 0.2}
    t_rankine: Temperature in Rankine
    p_psia: Pressure in psia
    fraction_type: "mole" or "mass"
    Returns: Z (Compressibility), MW (Molecular Weight g/mol), k (Specific Heat Ratio)
    """
    if not composition_dict:
        raise ValueError("No composition provided.")
        
    t_k = t_rankine * 5.0 / 9.0
    p_pa = p_psia * 6894.757
    
    # Normalize fractions (in case of tiny floating point errors)
    total_input = sum(composition_dict.values())
    if abs(total_input - 1.0) > 1e-3:
        raise ValueError(f"Sum of fractions must be 1.0 (or 100%). Current sum: {total_input*100:.2f}%")
        
    composition_normalized = {k: v/total_input for k, v in composition_dict.items()}

    # Convert mass fractions to mole fractions if needed
    if fraction_type.lower() == "mass":
        mole_fractions = {}
        total_moles = 0.0
        for fluid, mass_frac in composition_normalized.items():
            try:
                mw_pure = CP.PropsSI('molar_mass', 'T', t_k, 'P', p_pa, fluid)
                moles = mass_frac / mw_pure
                mole_fractions[fluid] = moles
                total_moles += moles
            except Exception as e:
                raise ValueError(f"Could not get properties for {fluid}: {str(e)}")
        
        composition_normalized = {k: v/total_moles for k, v in mole_fractions.items()}

    # Single pure fluid
    if len(composition_normalized) == 1:
        fluid = list(composition_normalized.keys())[0]
        fluid_str = fluid
    else:
        # Format for CoolProp: HEOS::Fluid1[frac1]&Fluid2[frac2]
        fluid_str = "HEOS::" + "&".join([f"{f}[{v}]" for f, v in composition_normalized.items()])

    try:
        z = CP.PropsSI('Z', 'T', t_k, 'P', p_pa, fluid_str)
        mw = CP.PropsSI('molar_mass', 'T', t_k, 'P', p_pa, fluid_str) * 1000.0
        cp = CP.PropsSI('Cpmass', 'T', t_k, 'P', p_pa, fluid_str)
        cv = CP.PropsSI('Cvmass', 'T', t_k, 'P', p_pa, fluid_str)
        k = cp / cv
        return z, mw, k
    except Exception as e:
        error_msg = str(e).lower()
        if "binary pair" in error_msg or "interaction" in error_msg or "not match" in error_msg:
            # Fallback to Kay's Rule (Ideal Mixture of Real Gases)
            return calculate_ideal_mixture_properties(composition_normalized, t_k, p_pa)
        raise ValueError(f"CoolProp Error: {str(e)}")

def calculate_ideal_mixture_properties(mole_fractions, t_k, p_pa):
    """Fallback calculation using linear combination (Kay's rule) for missing interaction params."""
    z_mix = 0.0
    mw_mix = 0.0
    cp_mix = 0.0
    cv_mix = 0.0
    
    for fluid, y in mole_fractions.items():
        try:
            z_i = CP.PropsSI('Z', 'T', t_k, 'P', p_pa, fluid)
            mw_i = CP.PropsSI('molar_mass', 'T', t_k, 'P', p_pa, fluid) * 1000.0
            cp_i = CP.PropsSI('Cpmolar', 'T', t_k, 'P', p_pa, fluid)
            cv_i = CP.PropsSI('Cvmolar', 'T', t_k, 'P', p_pa, fluid)
            
            z_mix += y * z_i
            mw_mix += y * mw_i
            cp_mix += y * cp_i
            cv_mix += y * cv_i
        except Exception as pure_err:
            raise ValueError(f"Could not calculate pure properties for {fluid} at this state: {pure_err}")
            
    k_mix = cp_mix / cv_mix
    return z_mix, mw_mix, k_mix

def get_coolprop_fluids():
    """Return a sorted list of all available CoolProp pure fluids."""
    fluids_str = CP.get_global_param_string("FluidsList")
    fluids = sorted(fluids_str.split(","))
    # We can alias water so users easily find steam
    if "Water" in fluids:
        fluids[fluids.index("Water")] = "Water (Steam)"
    return fluids


def calculate_two_phase_omega_coolprop(
    composition_dict: dict,
    p0_psia: float,
    state_type: str = "saturated_liquid",  # "subcooled_liquid", "saturated_liquid", "two_phase"
    t_rankine: float = None,
    x0: float = None,
    fraction_type: str = "mole",
) -> dict:
    """
    Calculate two-phase specific volumes v0, v9 and the Omega parameter
    using CoolProp to perform an isentropic flash from p0 to p9 = 0.9 * p0.
    """
    if not composition_dict:
        raise ValueError("No composition provided.")
        
    p0_pa = p0_psia * 6894.757
    p9_pa = 0.9 * p0_pa
    
    # Normalize composition
    total_input = sum(composition_dict.values())
    if abs(total_input - 1.0) > 1e-3:
        raise ValueError(f"Sum of fractions must be 1.0. Current sum: {total_input*100:.2f}%")
    comp_norm = {k: v/total_input for k, v in composition_dict.items()}
    
    # Clean Water alias if present
    comp_cleaned = {}
    for k, v in comp_norm.items():
        name = k
        if "Water (Steam)" in k or k == "Water":
            name = "Water"
        comp_cleaned[name] = v
    comp_norm = comp_cleaned

    if fraction_type.lower() == "mass":
        mole_fractions = {}
        total_moles = 0.0
        for fluid, mass_frac in comp_norm.items():
            try:
                # We can use a dummy state to get molar mass
                mw_pure = CP.PropsSI('molar_mass', 'T', 300.0, 'P', 1e5, fluid)
                moles = mass_frac / mw_pure
                mole_fractions[fluid] = moles
                total_moles += moles
            except Exception as e:
                raise ValueError(f"Could not get molar mass for {fluid}: {str(e)}")
        comp_norm = {k: v/total_moles for k, v in mole_fractions.items()}
        
    if len(comp_norm) == 1:
        fluid_str = list(comp_norm.keys())[0]
    else:
        fluid_str = "HEOS::" + "&".join([f"{f}[{v}]" for f, v in comp_norm.items()])
        
    try:
        if state_type == "subcooled_liquid":
            if t_rankine is None:
                raise ValueError("Temperature is required for subcooled liquid state.")
            t_k = t_rankine * 5.0 / 9.0
            rho0 = CP.PropsSI('D', 'T', t_k, 'P', p0_pa, fluid_str)
            s0 = CP.PropsSI('S', 'T', t_k, 'P', p0_pa, fluid_str)
        elif state_type == "saturated_liquid":
            rho0 = CP.PropsSI('D', 'P', p0_pa, 'Q', 0.0, fluid_str)
            s0 = CP.PropsSI('S', 'P', p0_pa, 'Q', 0.0, fluid_str)
        elif state_type == "two_phase":
            if x0 is None:
                raise ValueError("Quality x0 is required for two-phase state.")
            rho0 = CP.PropsSI('D', 'P', p0_pa, 'Q', x0, fluid_str)
            s0 = CP.PropsSI('S', 'P', p0_pa, 'Q', x0, fluid_str)
        else:
            raise ValueError(f"Unknown state_type: {state_type}")
            
        v0_m3_kg = 1.0 / rho0
        
        # Isentropic flash to p9 = 0.9 * p0
        rho9 = CP.PropsSI('D', 'P', p9_pa, 'S', s0, fluid_str)
        v9_m3_kg = 1.0 / rho9
        
        # Convert to ft3/lb (1 m3/kg = 16.01846 ft3/lb)
        v0_ft3_lb = v0_m3_kg * 16.01846
        v9_ft3_lb = v9_m3_kg * 16.01846
        
        omega = 9.0 * ((v9_ft3_lb / v0_ft3_lb) - 1.0)
        
        return {
            "v0_ft3_lb": v0_ft3_lb,
            "v9_ft3_lb": v9_ft3_lb,
            "omega": max(omega, 0.01)
        }
    except Exception as e:
        raise ValueError(f"CoolProp iki fazlı özellik hesaplama hatası: {str(e)}")
