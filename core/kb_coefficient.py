import math
from typing import Dict, List, Tuple

# API 520 Part I Fig. 11-4: Balanced Bellows Kb curves (10% overpressure)
# Digitized points from published chart
# key: back_pressure_pct, value: Kb
KB_BALANCED_BELLOWS_10PCT: Dict[float, float] = {
    0.0: 1.000,
    5.0: 0.995,
    10.0: 0.990,
    15.0: 0.985,
    20.0: 0.975,
    25.0: 0.965,
    30.0: 0.950,
    35.0: 0.930,
    40.0: 0.900,
    45.0: 0.870,
    50.0: 0.830,
}

# API 520 Part I Fig. 11-5: Balanced Bellows Kb (25% overpressure)
KB_BALANCED_BELLOWS_25PCT: Dict[float, float] = {
    0.0: 1.000,
    10.0: 0.995,
    20.0: 0.985,
    30.0: 0.965,
    40.0: 0.940,
    50.0: 0.890,
}

# Conventional valves have Kb = 1.0
KB_CONVENTIONAL: Dict[float, float] = {}


def interpolate_kb(bp_pct: float, curve: Dict[float, float]) -> float:
    """
    Linear interpolation between digitized Kb curve points.

    Parameters
    ----------
    bp_pct : Back pressure as percentage of set gauge pressure (0-100)
    curve : Dict of {bp_pct: Kb} digitized points

    Returns
    -------
    Kb value at the given back pressure percentage
    """
    if not curve:
        return 1.0

    sorted_points = sorted(curve.items())
    points: List[Tuple[float, float]] = [(k, v) for k, v in sorted_points]

    if bp_pct <= points[0][0]:
        return points[0][1]
    if bp_pct >= points[-1][0]:
        return points[-1][1]

    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        if x1 <= bp_pct <= x2:
            ratio = (bp_pct - x1) / (x2 - x1)
            return y1 + ratio * (y2 - y1)

    return 1.0


def get_kb(
    back_pressure_psia: float,
    set_pressure_psig: float,
    valve_type: str = "conventional",
    overpressure_pct: float = 10.0,
) -> float:
    """
    Calculate back pressure correction factor Kb per API 520 Part I.

    Parameters
    ----------
    back_pressure_psia : Total back pressure at relieving conditions (psia)
    set_pressure_psig : Set pressure (psig)
    valve_type : "conventional" or "balanced_bellows"
    overpressure_pct : Percent overpressure (10 or 25)

    Returns
    -------
    Kb capacity correction factor (dimensionless)
    """
    if set_pressure_psig <= 0:
        return 1.0

    bp_gauge = max(back_pressure_psia - 14.6959, 0.0)
    bp_pct = (bp_gauge / set_pressure_psig) * 100.0

    if valve_type in ("conventional", "pilot"):
        return 1.0

    if overpressure_pct <= 15:
        curve = KB_BALANCED_BELLOWS_10PCT
    else:
        curve = KB_BALANCED_BELLOWS_25PCT

    return interpolate_kb(bp_pct, curve)


# Gas critical back pressure ratio per API 520
def get_critical_back_pressure_ratio(valve_type: str = "conventional") -> float:
    """
    Return the critical back pressure ratio (P2/P1) for flow regime determination.

    Conventional: 0.5 (50% of set gauge)
    Balanced bellows: 0.6 (60% of set gauge)
    """
    if valve_type == "balanced_bellows":
        return 0.6
    return 0.5