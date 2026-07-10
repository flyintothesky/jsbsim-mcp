"""Property paths commonly read from JSBSim for telemetry.

Each entry is a (jsbsim-path, friendly-name, unit) tuple. The list is
intentionally short and curated — these are the fields a UI/dashboard or
LLM most commonly needs. Anything outside this set can still be read by
the generic `get_property` MCP tool using the full JSBSim path.
"""
from __future__ import annotations

# (jsbsim_path, friendly, unit, precision)
TELEMETRY_PROPERTIES: list[tuple[str, str, str, int]] = [
    # Position
    ("position/latitude-deg",      "lat_deg",           "deg", 6),
    ("position/longitude-deg",     "lon_deg",           "deg", 6),
    ("position/h-sl-ft",           "alt_ft",            "ft", 2),
    ("position/altitude-agl-ft",   "altitude_agl_ft",   "ft", 2),

    # Attitude
    ("attitude/pitch-deg",         "pitch_deg",         "deg", 2),
    ("attitude/roll-deg",          "roll_deg",          "deg", 2),
    ("attitude/heading-true-deg",  "heading_deg",       "deg", 2),

    # Velocities
    ("velocities/vc-fps",          "airspeed_fps",      "ft/s", 2),
    ("velocities/vc-kts",          "airspeed_kt",       "kt",  2),
    ("velocities/vg-fps",          "ground_speed_fps",  "ft/s", 2),
    ("velocities/mach",            "mach",              "-",   3),
    ("velocities/u-fps",           "u_fps",             "ft/s", 2),
    ("velocities/v-fps",           "v_fps",             "ft/s", 2),
    ("velocities/w-fps",           "w_fps",             "ft/s", 2),

    # Aerodynamics
    ("aero/alpha-deg",             "alpha_deg",         "deg", 2),
    ("aero/beta-deg",              "beta_deg",          "deg", 2),
    ("aero/cl-squared",            "cl",                "-",   4),

    # Forces
    ("forces/lift-lbs",            "lift_lbs",          "lbs", 2),
    ("forces/drag-lbs",            "drag_lbs",          "lbs", 2),
    ("forces/side-lbs",            "side_lbs",          "lbs", 2),

    # Engine 0 (single-engine aircraft like c172x)
    ("propulsion/engine[0]/thrust-lbs",  "thrust_lbs",  "lbs", 2),
    ("propulsion/engine[0]/n1",          "n1",         "%",   1),
    ("propulsion/engine[0]/rpm",         "rpm",        "rpm", 0),
    ("propulsion/engine[0]/running",     "engine_running", "bool", 0),

    # Fuel — sum of all tanks (read separately if needed)
    ("propulsion/total-fuel-lbs",  "fuel_remaining_lbs", "lbs", 2),

    # Acceleration
    ("accelerations/nz",           "nz_g",              "g",   2),

    # Wind — north/east/down body frame
    ("velocities/wind-north-fps",  "wind_north_fps",    "ft/s", 2),
    ("velocities/wind-east-fps",   "wind_east_fps",     "ft/s", 2),
    ("velocities/wind-down-fps",   "wind_down_fps",     "ft/s", 2),

    # Gear
    ("gear/gear[0]/wow",           "wow_nose",          "bool", 0),
    ("gear/gear[1]/wow",           "wow_main_l",        "bool", 0),
    ("gear/gear[2]/wow",           "wow_main_r",        "bool", 0),
    ("gear/gear[1]/compression-ft", "gear_comp_main_ft", "ft", 3),
]


# Properties that should be coerced to bool (0/1 from JSBSim)
_BOOL_FIELDS = {"engine_running", "wow_nose", "wow_main_l", "wow_main_r"}


def path_for(name: str) -> str | None:
    """Return JSBSim path for a friendly field name."""
    for path, friendly, _unit, _prec in TELEMETRY_PROPERTIES:
        if friendly == name:
            return path
    return None


def friendly_names() -> list[str]:
    return [row[1] for row in TELEMETRY_PROPERTIES]


def is_bool_field(name: str) -> bool:
    return name in _BOOL_FIELDS
