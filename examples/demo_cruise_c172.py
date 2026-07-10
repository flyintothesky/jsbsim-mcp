"""End-to-end demo client for jsbsim-mcp.

Goal: configure a Cessna 172, trim it for cruise, run 30 simulated seconds,
and report telemetry — all through MCP JSON-RPC 2.0.

Usage:
    JBM_URL=http://localhost:7860 python examples/demo_cruise_c172.py
or via streamable_http on the deployed HF Space:
    JBM_URL=https://<you>.hf.space python examples/demo_cruise_c172.py
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

URL = os.environ.get("JBM_URL", "http://127.0.0.1:7860")
DEFAULT_FDM = "c172x"


def rpc(method: str, params: dict, session_id: str | None = None,
        url: str = URL + "/mcp"):
    """Issue a single JSON-RPC 2.0 call.

    Handles:
      - initialize handshake (no session_id required)
      - notifications (no id, no result expected)
      - streamable_http SSE response body
    """
    req = Request(url, method="POST",
                  data=json.dumps({
                      "jsonrpc": "2.0",
                      "id": uuid.uuid4().hex,
                      "method": method,
                      "params": params,
                  }).encode())
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json, text/event-stream")
    if session_id:
        req.add_header("Mcp-Session-Id", session_id)
    with urlopen(req, timeout=30) as r:
        sid = r.headers.get("Mcp-Session-Id")
        body = r.read().decode()
    # SSE body: `event: message\ndata: {json}\n\n`
    for line in body.splitlines():
        if line.startswith("data:"):
            return json.loads(line[len("data:"):].strip()), sid
    return json.loads(body), sid


def call_tool(session_id: str, name: str, args: dict):
    out, _ = rpc("tools/call",
                 {"name": name, "arguments": args},
                 session_id=session_id)
    txt = out["result"]["content"][0]["text"]
    return json.loads(txt)


def banner(s: str) -> None:
    print()
    print("=" * len(s))
    print(s)
    print("=" * len(s))


def main() -> int:
    print(f"📡 talking to {URL}")
    init, sid = rpc("initialize", {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "demo", "version": "0.1.0"},
    })
    print(f"   serverInfo: {init['result']['serverInfo']}")
    print(f"   session-id: {sid}")
    rpc("notifications/initialized", {}, session_id=sid)

    banner("Step 1 — list aircraft")
    aircraft = call_tool(sid, "list_aircraft", {})
    print(f"  found {aircraft['count']} aircraft; first 5: {aircraft['aircraft'][:5]}")

    banner(f"Step 2 — create {DEFAULT_FDM} session")
    sess = call_tool(sid, "create_session", {
        "aircraft": DEFAULT_FDM,
        "initial_conditions": {
            "altitude_ft": 8000.0,
            "airspeed_fps": 108 * 1.6878,   # ~108 kt
            "heading_deg": 0.0,
        },
    })
    sim_sid = sess["session_id"]
    print(f"  session_id={sim_sid}  dt={sess['dt']:.4f}s  aircraft={sess['aircraft']}")

    banner("Step 3 — engage cruise throttle")
    # Default c172x ICs leave the engine off; advance one frame so the
    # throttle engages. We're not building a starter kit here — users
    # who want full engine controls should use IC files that configure
    # engine state explicitly (e.g. reset00.xml for ground startup).
    call_tool(sid, "set_property", {
        "session_id": sim_sid,
        "path": "fcs/throttle-cmd-norm", "value": 0.7,
    })
    call_tool(sid, "set_property", {
        "session_id": sim_sid,
        "path": "fcs/mixture-cmd-norm", "value": 1.0,
    })
    call_tool(sid, "step", {"session_id": sim_sid, "seconds": 0.5})

    banner("Step 4 — trim longitudinal")
    trim = call_tool(sid, "trim", {"session_id": sim_sid, "mode": "longitudinal"})
    print(f"  trim report: {json.dumps(trim, indent=2)[:400]}")

    banner("Step 5 — step 30 s")
    step_out = call_tool(sid, "step", {"session_id": sim_sid, "seconds": 30.0})
    print(f"  ran {step_out['frames']} frames; sim_time={step_out['sim_time']:.2f}s")

    banner("Step 6 — telemetry snapshot")
    telem = call_tool(sid, "get_telemetry", {"session_id": sim_sid})
    print(json.dumps({k: telem[k] for k in (
        "t", "alt_ft", "airspeed_kt", "mach", "alpha_deg", "pitch_deg",
        "roll_deg", "heading_deg", "thrust_lbs", "rpm", "fuel_remaining_lbs",
        "nz_g", "engine_running",
    )}, indent=2))

    banner("Step 7 — close session")
    closed = call_tool(sid, "close_session", {"session_id": sim_sid})
    print(f"  ok={closed['ok']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
