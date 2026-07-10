# Changelog

All notable changes to `jsbsim-mcp`.

## [0.1.0] - 2026-07-11

### Added

- **Initial public release.**
- Engine: thread-safe JSBSim session pool, LRU + TTL, JBSIM_ROOT path resolver.
- Telemetry: 40+ scalar fields published through a single Pydantic frame.
- MCP server (FastMCP / StreamableHTTP):
  - 10 Tools: `list_aircraft`, `create_session`, `close_session`,
    `set_initial_conditions`, `trim`, `step`, `get_property`,
    `set_property`, `get_telemetry`, `execute_script`.
  - 7 Resources: `aircraft`, `aircraft/{name}`, `engines`, `sessions`,
    `sessions/{sid}/telemetry`, …
  - 2 Prompts: `cruise_c172`, `stall_recovery`.
- Web Dashboard (FastAPI):
  - Single-page control UI with aircraft picker.
  - SVG PFD with artificial horizon, altitude tape, airspeed tape,
    numeric readout.
  - Three.js 3D attitude indicator (with vendored fallback).
  - Plotly time-series charts (alt / kt / alpha / thrust).
  - Live WebSocket telemetry at ~20 Hz (`/ws/{sid}`).
  - Built-in MCP JSON-RPC console for hand-debugging.
- Tests:
  - 17 engine unit tests (`tests/test_core.py`).
  - 3 end-to-end MCP integration tests (`tests/test_mcp.py`).
  - 20/20 passing.
- Deployment:
  - `Dockerfile` for HF Spaces (`app_port: 7860`).
  - `requirements.txt` pinned.
  - `THIRD_PARTY_NOTICES.md` (LGPL-2.1 boundary preserved).
- Docs:
  - `docs/REQUIREMENTS.md` — functional + non-functional spec.
  - `docs/ARCHITECTURE.md` — module boundaries + data contract.
  - `docs/API.md` — JSON-RPC reference.
  - `docs/DEPLOY.md` — HF Spaces deployment walkthrough.
  - `USAGE.md` — three integration paths.

### Notes

- Tested against JSBSim v1.3.1 (LGPL-2.1) and MCP SDK 1.28.
- Python 3.10 + supported. 3.12 recommended for HF Space base.
- 60 Hz physics meets our p95 < 100 ms tool-call SLA on c172x with one
  preloaded session.
