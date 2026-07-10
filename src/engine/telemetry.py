"""Telemetry frame model — what a UI/MCP consumer sees.

`TelemetryFrame` is the canonical unit of data published:
- via MCP `get_telemetry` tool
- via MCP `jsbsim://sessions/{sid}/telemetry` resource
- via WebSocket to Web Dashboard

Values are pulled from JSBSim property tree (see `properties.py`).
Numbers are rounded to (precision) decimals to keep payload small —
LLMs & browsers don't need more than that.
"""
from __future__ import annotations

import time
from typing import Optional

from pydantic import BaseModel, Field

from .properties import TELEMETRY_PROPERTIES, is_bool_field


class TelemetryFrame(BaseModel):
    """One frame of aircraft telemetry."""

    # Wall clock at server
    wall_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
    # Aircraft identity
    aircraft: str
    session_id: str
    # Simulation time
    t: float = 0.0

    # === Filled below from properties ===
    lat_deg: float = 0.0
    lon_deg: float = 0.0
    alt_ft: float = 0.0
    altitude_agl_ft: Optional[float] = None

    pitch_deg: float = 0.0
    roll_deg: float = 0.0
    heading_deg: float = 0.0

    airspeed_fps: float = 0.0
    airspeed_kt: float = 0.0
    ground_speed_fps: float = 0.0
    mach: float = 0.0
    u_fps: float = 0.0
    v_fps: float = 0.0
    w_fps: float = 0.0

    alpha_deg: float = 0.0
    beta_deg: float = 0.0
    cl: float = 0.0

    lift_lbs: float = 0.0
    drag_lbs: float = 0.0
    side_lbs: float = 0.0

    thrust_lbs: float = 0.0
    n1: float = 0.0
    rpm: float = 0.0
    engine_running: bool = False

    fuel_remaining_lbs: float = 0.0
    nz_g: float = 1.0

    wind_north_fps: float = 0.0
    wind_east_fps: float = 0.0
    wind_down_fps: float = 0.0

    wow_nose: bool = False
    wow_main_l: bool = False
    wow_main_r: bool = False
    gear_comp_main_ft: float = 0.0

    @classmethod
    def from_fdm(cls, *, aircraft: str, session_id: str, fdm) -> "TelemetryFrame":
        """Build a TelemetryFrame from an FGFDMExec instance."""
        payload: dict[str, object] = {
            "aircraft": aircraft,
            "session_id": session_id,
        }
        # sim-time
        try:
            t = fdm.get_property_value("simulation/sim-time-sec")
            payload["t"] = float(t) if t is not None else 0.0
        except Exception:
            payload["t"] = 0.0

        for path, friendly, _unit, precision in TELEMETRY_PROPERTIES:
            try:
                raw = fdm.get_property_value(path)
            except Exception:
                continue
            if raw is None:
                continue
            if is_bool_field(friendly):
                payload[friendly] = bool(raw)
            elif precision == 0:
                payload[friendly] = int(round(float(raw)))
            else:
                payload[friendly] = round(float(raw), precision)

        return cls(**payload)
