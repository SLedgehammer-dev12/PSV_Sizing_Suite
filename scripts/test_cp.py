import CoolProp.CoolProp as CP

try:
    z = CP.PropsSI('Z', 'T', 300, 'P', 101325, 'HEOS::Methane[0.5]&Ethane[0.5]')
    mw = CP.PropsSI('molar_mass', 'T', 300, 'P', 101325, 'HEOS::Methane[0.5]&Ethane[0.5]')
    cp = CP.PropsSI('Cpmass', 'T', 300, 'P', 101325, 'HEOS::Methane[0.5]&Ethane[0.5]')
    cv = CP.PropsSI('Cvmass', 'T', 300, 'P', 101325, 'HEOS::Methane[0.5]&Ethane[0.5]')
    
    print(f"Z={z}")
    print(f"MW={mw * 1000} g/mol")
    print(f"k={cp/cv}")
except Exception as e:
    print(f"Error: {e}")
