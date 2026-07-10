"""Pydantic schemas for all MCP tool inputs and outputs.

These schemas are the single source of truth for both Pydantic validation
and JSON Schema generation that MCP clients receive.
"""
from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


# ----------------------------------------------------------------------
# create_session
# ----------------------------------------------------------------------
class CreateSessionInput(BaseModel):
    aircraft: str = Field(description="Aircraft name (e.g. 'c172x'). Use `list_aircraft` first.")
    initial_conditions: Optional[dict[str, float]] = Field(
        default=None,
        description=(
            "Initial state. Recognised keys: altitude_ft, latitude_deg, "
            "longitude_deg, airspeed_fps, heading_deg, pitch_deg, roll_deg."
        ),
    )
    dt: Optional[float] = Field(
        default=None,
        description="Fixed timestep (sec). Default 1/60. Common values: 1/120, 1/240.",
    )
    ic_path: Optional[str] = Field(
        default=None,
        description="Path to an initial-conditions XML file relative to JBSIM_ROOT.",
    )


class CreateSessionOutput(BaseModel):
    session_id: str
    aircraft: str
    dt: float
    sim_time: float
    root: str


# ----------------------------------------------------------------------
# close_session
# ----------------------------------------------------------------------
class CloseSessionInput(BaseModel):
    session_id: str


# ----------------------------------------------------------------------
# step
# ----------------------------------------------------------------------
class StepInput(BaseModel):
    session_id: str
    seconds: float = Field(gt=0.0, le=3600.0,
                           description="How many seconds of simulation to advance")


class StepOutput(BaseModel):
    session_id: str
    frames: int
    dt: float
    sim_time: float


# ----------------------------------------------------------------------
# get_property / set_property
# ----------------------------------------------------------------------
class PropertyInput(BaseModel):
    session_id: str
    path: str = Field(description="JSBSim property path, e.g. 'velocities/vc-kts'")


class GetPropertyOutput(BaseModel):
    path: str
    value: Optional[float]
    present: bool


class SetPropertyInput(BaseModel):
    session_id: str
    path: str
    value: float


class SetPropertyOutput(BaseModel):
    ok: bool
    path: str
    value: float


# ----------------------------------------------------------------------
# set_initial_conditions
# ----------------------------------------------------------------------
class SetICInput(BaseModel):
    session_id: str
    altitude_ft: Optional[float] = None
    latitude_deg: Optional[float] = None
    longitude_deg: Optional[float] = None
    airspeed_fps: Optional[float] = None
    heading_deg: Optional[float] = None
    pitch_deg: Optional[float] = None
    roll_deg: Optional[float] = None


class SetICOutput(BaseModel):
    ok: bool


# ----------------------------------------------------------------------
# trim
# ----------------------------------------------------------------------
TrimMode = Literal["longitudinal", "full", "pullup", "custom", "turn", "none"]


class TrimInput(BaseModel):
    session_id: str
    mode: TrimMode = "longitudinal"


# ----------------------------------------------------------------------
# execute_script
# ----------------------------------------------------------------------
class ExecuteScriptInput(BaseModel):
    session_id: str
    script: str = Field(
        description=(
            "Either JSBSim script XML content (string starting with "
            "'<run>') or a path relative to JBSIM_ROOT."
        )
    )


class ExecuteScriptOutput(BaseModel):
    ok: bool
    note: str


# ----------------------------------------------------------------------
# list_aircraft
# ----------------------------------------------------------------------
class ListAircraftOutput(BaseModel):
    aircraft: list[str]
    count: int
