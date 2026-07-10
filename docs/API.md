# jsbsim-mcp — API Reference (v0.1.0)

> Stable API. JSON-RPC 2.0 over streamable_http OR stdio.

---

## Endpoint

| Transport | URL |
|---|---|
| stdio (Claude Code / Cursor / Codex CLI) | spawn `python run_stdio.py` |
| streamable_http (Claude Desktop, web agents, browser) | `POST /mcp` on the service |

Protocol version: `2025-06-18`.

---

## Tools (10)

### `list_aircraft`
```
{
  "aircraft": ["c172x", "a320", "f16", ...],
  "count": 60
}
```

### `create_session`
Input:
```
{
  "aircraft": "c172x",
  "initial_conditions": {
    "altitude_ft": 2500,
    "airspeed_fps": 95 * 1.6878,
    "heading_deg": 0
  },
  "dt": 0.0167,                  // default 1/60
  "ic_path": "aircraft/c172x/reset00.xml"   // optional, overrides numeric ICs
}
```
Output:
```
{
  "session_id": "abc12345",
  "aircraft": "c172x",
  "dt": 0.0167,
  "sim_time": 0.0,
  "root": "/abs/path/jsbsim_data"
}
```

### `close_session`
Input: `{ "session_id": "abc..." }`
Output: `{ "ok": true, "session_id": "..." }`

### `set_initial_conditions`
Input:
```
{
  "session_id": "abc",
  "altitude_ft": 5000,
  "airspeed_fps": 110 * 1.6878,
  "heading_deg": 90.0,
  "pitch_deg": 2.0,
  "roll_deg": 0.0
}
```
All fields optional. Outputs `{ "ok": true }`.

### `trim`
Modes: `longitudinal | full | pullup | custom | turn | none`
Input: `{ "session_id": "abc", "mode": "longitudinal" }`
Output:
```
{
  "ok": true,
  "alpha_deg": 2.34,
  "elevator": -0.05,
  "throttle": 0.6,
  "thrust_lbs": 240.5,
  "airspeed_fps": 110
}
```

### `step`
Input: `{ "session_id": "abc", "seconds": 1.0 }`
Output: `{ "session_id": "abc", "frames": 60, "dt": 0.0167, "sim_time": 1.0 }`

### `get_property`
Input: `{ "session_id": "abc", "path": "velocities/vc-kts" }`
Output: `{ "path": "velocities/vc-kts", "value": 95.0, "present": true }`

### `set_property`
Input: `{ "session_id": "abc", "path": "fcs/throttle-cmd-norm", "value": 0.7 }`
Output: `{ "ok": true, "path": "...", "value": 0.7 }`

Common paths to write:
- `fcs/elevator-cmd-norm`
- `fcs/aileron-cmd-norm`
- `fcs/rudder-cmd-norm`
- `fcs/throttle-cmd-norm`

### `get_telemetry`
Input: `{ "session_id": "abc" }`
Output: see [TelemetryFrame](#telemetryframe) below.

### `execute_script`
Input:
```
{
  "session_id": "abc",
  "script": "<run> ... </run>"     // OR path "scripts/hold_heading.xml"
}
```
Output: `{ "ok": true, "note": "queued my_script.xml" }`

---

## Resources (7)

| URI | Description |
|---|---|
| `jsbsim://aircraft` | Returns `{"count":60, "aircraft":[...]}` |
| `jsbsim://aircraft/{name}` | Single aircraft metadata + XML path |
| `jsbsim://engines` | List of bundled engine models |
| `jsbsim://sessions` | Active session pool stats |
| `jsbsim://sessions/{sid}/telemetry` | Latest telemetry frame |
| `jsbsim://sessions/{sid}/telemetry/stream` | SSE stream (Phase 2) |
| `jsbsim://sessions/{sid}/trajectory` | Full trajectory post-run |

---

## Prompts (2)

### `cruise_c172`
Workflow guide: create c172x → IC 8000ft → trim longitudinal → step → report.

### `stall_recovery`
Workflow guide: pull 8° nose-up → watch alpha → recover.

---

## TelemetryFrame (40+ fields)

```
{
  "wall_ms": 1783701234567,
  "aircraft": "c172x",
  "session_id": "abc",
  "t": 30.0,

  "lat_deg": 37.0, "lon_deg": -122.0, "alt_ft": 8000.0,
  "altitude_agl_ft": 8000.0,

  "pitch_deg": 0.0, "roll_deg": 0.0, "heading_deg": 90.0,

  "airspeed_fps": 154.5, "airspeed_kt": 95.0, "ground_speed_fps": 154.0,
  "mach": 0.139, "u_fps": 145.0, "v_fps": 0.0, "w_fps": 0.0,

  "alpha_deg": 4.5, "beta_deg": 0.0, "cl": 0.42,

  "lift_lbs": 2300, "drag_lbs": 80, "side_lbs": 0,

  "thrust_lbs": 240, "n1": 80, "rpm": 2350, "engine_running": true,
  "fuel_remaining_lbs": 246.0, "nz_g": 1.0,

  "wind_north_fps": 0, "wind_east_fps": 0, "wind_down_fps": 0,

  "wow_nose": false, "wow_main_l": false, "wow_main_r": false,
  "gear_comp_main_ft": 0.0
}
```

---

## Error handling

| Code | Reason |
|---|---|
| 400 | Invalid JSON / schema |
| 404 | Unknown session |
| 422 | Property path malformed |
| 500 | FDM exception (caught & logged) |
| 503 | Engine pool exhausted (`max_sessions` hit) |

---

## Versioning

`jsbsim-mcp` follows SemVer. Tools and resources MAY be added in minor
versions without breaking changes. Removal happens only in major.

JBSIM CORE API is JSBSim v1.3.1 (LGPL-2.1).
