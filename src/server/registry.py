"""MCP Server entrypoint — registers Tools, Resources, Prompts.

Designed to support BOTH transports:
- stdio (Claude Code / Cursor / Codex CLI local)
- streamable_http (remote clients including Claude Desktop & web agents)

The FastAPI app (`mcp.streamable_http_app()`) is mounted into a parent
ASGI app that also exposes the Web Dashboard. See `app.py`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.fastmcp import FastMCP

from ..engine import (
    SessionPool,
    default_root,
    list_aircraft,
    describe_aircraft,
    TelemetryFrame,
)
from .schemas import (
    CreateSessionInput,
    CreateSessionOutput,
    CloseSessionInput,
    StepInput,
    StepOutput,
    PropertyInput,
    GetPropertyOutput,
    SetPropertyInput,
    SetPropertyOutput,
    SetICInput,
    SetICOutput,
    TrimInput,
    ExecuteScriptInput,
    ExecuteScriptOutput,
    ListAircraftOutput,
)


# ----------------------------------------------------------------------
# Engine singleton (one pool per server process)
# ----------------------------------------------------------------------
POOL: SessionPool | None = None


def get_pool() -> SessionPool:
    global POOL
    if POOL is None:
        root = default_root()
        POOL = SessionPool(
            root=root,
            max_sessions=int(os.environ.get("JBM_MAX_SESSIONS", "32")),
            idle_ttl_sec=int(os.environ.get("JBM_IDLE_TTL", "300")),
        )
        POOL.start()
    return POOL


# ----------------------------------------------------------------------
# FastMCP server
# ----------------------------------------------------------------------
SERVER_NAME = os.environ.get("JBM_SERVER_NAME", "jsbsim-fdm")
SERVER_VERSION = "0.1.0"

mcp = FastMCP(SERVER_NAME)


# ----------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------
@mcp.tool(
    name="list_aircraft",
    description=(
        "List all JSBSim aircraft bundled with this server. Returns an array "
        "of names you can pass to create_session(). Call this before creating "
        "a session if unsure which planes are available."
    ),
)
def list_aircraft_tool() -> dict[str, Any]:
    root = default_root()
    names = list_aircraft(root)
    payload = ListAircraftOutput(aircraft=names, count=len(names)).model_dump()
    return payload


@mcp.tool(
    name="create_session",
    description=(
        "Create a new JSBSim simulation session. Returns a session_id you use "
        "for all subsequent calls. Each session is isolated — you can run many "
        "concurrently, e.g. one per agent branch."
    ),
)
def create_session_tool(
    aircraft: str,
    initial_conditions: dict[str, float] | None = None,
    dt: float | None = None,
    ic_path: str | None = None,
) -> dict[str, Any]:
    p = get_pool()
    ic = Path(ic_path) if ic_path else None
    sid = p.create(aircraft, ic_path=ic, dt=dt)
    s = p.get(sid)
    assert s is not None
    if initial_conditions:
        s.set_initial_conditions(**initial_conditions)
    payload = CreateSessionOutput(
        session_id=sid,
        aircraft=s.aircraft_loaded,
        dt=s.dt,
        sim_time=s.sim_time,
        root=str(p.root),
    ).model_dump()
    return payload


@mcp.tool(name="close_session",
          description="Destroy a session and free its memory.")
def close_session_tool(session_id: str) -> dict[str, Any]:
    p = get_pool()
    ok = p.close(session_id)
    return {"ok": ok, "session_id": session_id}


@mcp.tool(
    name="set_initial_conditions",
    description=(
        "Set ICs numerically. Recognised keys: altitude_ft, latitude_deg, "
        "longitude_deg, airspeed_fps, heading_deg, pitch_deg, roll_deg."
    ),
)
def set_initial_conditions_tool(
    session_id: str,
    altitude_ft: float | None = None,
    latitude_deg: float | None = None,
    longitude_deg: float | None = None,
    airspeed_fps: float | None = None,
    heading_deg: float | None = None,
    pitch_deg: float | None = None,
    roll_deg: float | None = None,
) -> dict[str, Any]:
    p = get_pool()
    s = p.get(session_id)
    if s is None:
        return {"ok": False, "error": "unknown-session"}
    ok = s.set_initial_conditions(
        altitude_ft=altitude_ft or 0.0,
        latitude_deg=latitude_deg or 0.0,
        longitude_deg=longitude_deg or 0.0,
        airspeed_fps=airspeed_fps or 0.0,
        heading_deg=heading_deg or 0.0,
        pitch_deg=pitch_deg or 0.0,
        roll_deg=roll_deg or 0.0,
    )
    return SetICOutput(ok=bool(ok)).model_dump()


@mcp.tool(name="trim",
          description=("Trim the aircraft (balance the forces). Modes: longitudinal, "
                      "full, pullup, custom, turn, none."))
def trim_tool(session_id: str, mode: str = "longitudinal") -> dict[str, Any]:
    p = get_pool()
    s = p.get(session_id)
    if s is None:
        return {"ok": False, "error": "unknown-session"}
    return s.trim(mode=mode)


@mcp.tool(
    name="step",
    description=(
        "Advance the simulation by N seconds. Internally stepped at dt "
        "(default 1/60). Useful for batch runs or scripted scenarios."
    ),
)
def step_tool(session_id: str, seconds: float) -> dict[str, Any]:
    p = get_pool()
    s = p.get(session_id)
    if s is None:
        return {"ok": False, "error": "unknown-session"}
    frames = max(1, int(round(seconds / s.dt)))
    s.step(frames)
    return StepOutput(
        session_id=session_id,
        frames=frames,
        dt=s.dt,
        sim_time=s.sim_time,
    ).model_dump()


@mcp.tool(name="get_property",
          description=("Read a single JSBSim property by its full path, e.g. "
                      "velocities/vc-kts. Returns null if not present."))
def get_property_tool(session_id: str, path: str) -> dict[str, Any]:
    p = get_pool()
    s = p.get(session_id)
    if s is None:
        return {"ok": False, "error": "unknown-session"}
    val = s.get(path)
    return GetPropertyOutput(path=path, value=val, present=val is not None).model_dump()


@mcp.tool(name="set_property",
          description=("Write a single JSBSim property. Use with care — bad "
                      "values can stall the integrator. Common: fcs/elevator-cmd-norm, "
                      "fcs/throttle-cmd-norm, fcs/rudder-cmd-norm, "
                      "fcs/aileron-cmd-norm."))
def set_property_tool(session_id: str, path: str, value: float) -> dict[str, Any]:
    p = get_pool()
    s = p.get(session_id)
    if s is None:
        return {"ok": False, "error": "unknown-session"}
    ok = s.set(path, float(value))
    return SetPropertyOutput(ok=bool(ok), path=path, value=float(value)).model_dump()


@mcp.tool(
    name="get_telemetry",
    description=(
        "Return a single telemetry frame with the most-used fields packed in one "
        "call (40+ scalars). Prefer this over many small get_property calls — "
        "one MCP round-trip vs. N."
    ),
)
def get_telemetry_tool(session_id: str) -> dict[str, Any]:
    p = get_pool()
    s = p.get(session_id)
    if s is None:
        return {"ok": False, "error": "unknown-session"}
    tf = TelemetryFrame.from_fdm(aircraft=s.aircraft_loaded, session_id=session_id, fdm=s.fdm)
    return tf.model_dump()


@mcp.tool(
    name="execute_script",
    description=(
        "Execute a JSBSim <run>...</run> script. Pass the XML literal "
        "(starting with '<run>') or a path relative to JBSIM_ROOT."
    ),
)
def execute_script_tool(session_id: str, script: str) -> dict[str, Any]:
    p = get_pool()
    s = p.get(session_id)
    if s is None:
        return {"ok": False, "error": "unknown-session"}
    if script.lstrip().startswith("<"):
        # Write to a tmp file then load_script
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(script)
            tmp = Path(f.name)
    else:
        tmp = Path(script)
        if not tmp.is_absolute():
            tmp = p.root / script
    if not tmp.exists():
        return ExecuteScriptOutput(ok=False, note=f"script not found: {tmp}").model_dump()
    try:
        s.fdm.load_script(str(tmp))
        # Run loop will pick up the script events as we step.
        s.step(frames=1)
        return ExecuteScriptOutput(ok=True, note=f"queued {tmp.name}").model_dump()
    except Exception as exc:
        return ExecuteScriptOutput(ok=False, note=f"script failed: {exc}").model_dump()


# ----------------------------------------------------------------------
# Resources
# ----------------------------------------------------------------------
@mcp.resource("jsbsim://aircraft")
def resource_aircraft() -> str:
    root = default_root()
    names = list_aircraft(root)
    return json.dumps({"count": len(names), "aircraft": names})


@mcp.resource("jsbsim://aircraft/{name}")
def resource_aircraft_detail(name: str) -> str:
    root = default_root()
    return json.dumps(describe_aircraft(root, name))


@mcp.resource("jsbsim://sessions")
def resource_sessions() -> str:
    return json.dumps(get_pool().stats())


@mcp.resource("jsbsim://sessions/{sid}/telemetry")
def resource_telemetry(sid: str) -> str:
    p = get_pool()
    s = p.get(sid)
    if s is None:
        return json.dumps({"error": "unknown-session"})
    tf = TelemetryFrame.from_fdm(aircraft=s.aircraft_loaded, session_id=sid, fdm=s.fdm)
    return tf.model_dump_json()


@mcp.resource("jsbsim://engines")
def resource_engines() -> str:
    root = default_root()
    eng_dir = root / "engines"
    if not eng_dir.is_dir():
        return json.dumps({"count": 0, "engines": []})
    items = sorted(p.name for p in eng_dir.iterdir() if p.is_dir())
    return json.dumps({"count": len(items), "engines": items})


# ----------------------------------------------------------------------
# Prompts — make LSAs productive with one click
# ----------------------------------------------------------------------
@mcp.prompt(
    name="cruise_c172",
    description="Standard 'cruise a Cessna 172 at cruise altitude' workflow.",
)
def prompt_cruise_c172() -> str:
    return (
        "Goal: cruise a Cessna 172X at 8000 ft and 108 kt.\n\n"
        "Steps:\n"
        " 1. Call list_aircraft, confirm 'c172x' is available.\n"
        " 2. Call create_session with aircraft='c172x', "
        "    initial_conditions={'altitude_ft': 8000, 'airspeed_fps': 108*1.6878, "
        "    'heading_deg': 0.0, 'latitude_deg': 37.0, 'longitude_deg': -122.0}.\n"
        " 3. Call trim mode='longitudinal'.\n"
        " 4. Step 30 seconds, then get_telemetry — report alt/airspeed/alpha/fuel.\n"
        "Reply with a one-line summary plus the raw telemetry object."
    )


@mcp.prompt(
    name="stall_recovery",
    description="Stall entry + recovery exercise.",
)
def prompt_stall_recovery() -> str:
    return (
        "Goal: from level flight at 90 kt, induce a stall with 8 deg back-stick "
        "and recover with pitch-down + full throttle.\n\n"
        "Steps:\n"
        " 1. create_session aircraft='c172x' altitude_ft=5000 airspeed_fps=90*1.6878.\n"
        " 2. trim longitudinal.\n"
        " 3. Set fcs/elevator-cmd-norm = -0.4 (pull 8 deg pitch up) and step 5 sec.\n"
        " 4. get_telemetry — if alpha > 16 deg, you're stalling: set elevator=0.4 "
        "    (nose down) and fcs/throttle-cmd-norm=1.0, step 3 sec.\n"
        " 5. get_telemetry — report final alpha, airspeed, altitude."
    )


# ----------------------------------------------------------------------
# ASGI export
# ----------------------------------------------------------------------
def get_app():
    """ASGI app exposing both MCP streamable_http + Web Dashboard (set in app.py)."""
    # Default FastMCP exposes stdio + http via mcp.run(...)
    # The streamable_http app is mounted in app.py into the parent ASGI tree.
    return mcp


def run_stdio() -> None:
    """Run the MCP server over stdio (Claude Code / Cursor etc.)."""
    mcp.run()


# ----------------------------------------------------------------------
# Manual smoke (independent of MCP SDK): can be invoked via `python -m src.server.registry`
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="jsbsim-mcp registry helpers")
    parser.add_argument("--print-tools", action="store_true")
    args = parser.parse_args()
    if args.print_tools:
        tools = []
        # FastMCP exposes a manager; for now fall back to manual listing
        for n in [
            "list_aircraft", "create_session", "close_session",
            "set_initial_conditions", "trim", "step",
            "get_property", "set_property", "get_telemetry",
            "execute_script",
        ]:
            tools.append({"name": n})
        print(json.dumps({"tools": tools}, indent=2))
