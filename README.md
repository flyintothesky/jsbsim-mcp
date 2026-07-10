---
title: jsbsim-mcp
emoji: ✈️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
app_file: app.py
pinned: false
license: apache-2.0
short_description: JSBSim flight-dynamics engine as an MCP service
---

# jsbsim-mcp

> **JSBSim as a hosted MCP service. Drive any aircraft in any AI agent.**

[JSBSim](https://github.com/JSBSim-Team/jsbsim) is the open-source
flight-dynamics engine powering FlightGear, Unreal Engine, ArduPilot, NASA
research and DARPA's AI dogfight competition. **jsbsim-mcp** exposes the
same engine through the **Model Context Protocol (MCP)**, so Claude,
Cursor, Codex or any MCP-aware agent can fly aircraft in plain English.

Built on this Space:

- 1 unified ASGI app: **MCP JSON-RPC at `/mcp`** + **Web Dashboard at `/`**
- 60Hz real-time simulation engine (`python -m jsbsim`)
- 60+ bundled aircraft (`c172x`, `A320`, `f-16`, `737`, `Concorde`, `X15`, ...)
- WebSocket telemetry to the browser
- Apache-2.0 source code; JSBSim dependency is LGPL-2.1 (C-ABI isolated)

---

## Quick Start

### 1. Install locally (stdio mode)

```bash
git clone https://github.com/<you>/jsbsim-mcp
cd jsbsim-mcp
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Bundle JSBSim aircraft data (≈30 MB)
make data           # OR:  mkdir jsbsim_data && cd jsbsim_data && \
                    #       curl -L https://github.com/JSBSim-Team/jsbsim/archive/refs/heads/master.tar.gz | tar --strip-components=1 -xz

python app.py       # → http://0.0.0.0:7860 (dashboard) / http://0.0.0.0:7860/mcp (MCP)
```

### 2. Connect a remote agent (Claude Desktop / Cursor)

```json
{
  "mcpServers": {
    "jsbsim-fdm": {
      "url": "https://<your-hf-space>.hf.space/mcp"
    }
  }
}
```

Claude will then list 10 tools (see [docs/API.md](docs/API.md)) and 7
resources (incl. full telemetry history).

### 3. Local stdio (Claude Code / Cursor local)

```bash
python run_stdio.py
```

In `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "jsbsim-fdm-local": {
      "command": "python",
      "args": ["/path/to/jsbsim-mcp/run_stdio.py"]
    }
  }
}
```

---

## HTTP endpoints

| Path | Description |
|---|---|
| `/`         | Web Dashboard (PFD, 3D attitude, time-series charts) |
| `/api/aircraft` | List bundled aircraft |
| `/api/sessions` | POST create / GET list / DELETE close |
| `/api/sessions/{sid}/step` | Advance simulation N seconds |
| `/api/sessions/{sid}/telemetry` | Latest telemetry frame |
| `/ws/{sid}` | WebSocket telemetry stream (~20 Hz) |
| `/mcp`      | MCP JSON-RPC 2.0 streamable_http endpoint |
| `/healthz`  | Health probe |

## MCP tools (10)

```
list_aircraft           create_session         close_session
set_initial_conditions  trim                   step
get_property            set_property           get_telemetry
execute_script
```

## MCP resources (7)

```
jsbsim://aircraft
jsbsim://aircraft/{name}
jsbsim://engines
jsbsim://sessions
jsbsim://sessions/{sid}/telemetry
```

## MCP prompts (2)

```
cruise_c172      Standard C172 cruise workflow
stall_recovery   Stall entry / recovery exercise
```

---

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The system is layered:

```
src/engine/    JSBSim wrapper + session pool + telemetry
src/server/    MCP protocol adapters (FastMCP tools/resources/prompts)
src/dashboard/ FastAPI dashboard + WebSocket broadcaster
app.py         ASGI dispatcher
```

License boundary: JSBSim 1.3.1 is LGPL-2.1 and is loaded as a wheel
(`pip install jsbsim`). All new code in this project is Apache-2.0.

---

## Demo

```bash
curl -X POST https://<space>.hf.space/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"demo","version":"1"}}}'
```

Then list tools, call `create_session`, etc.

---

## License

- This project: **Apache-2.0**
- JSBSim dependency: **LGPL-2.1**

See `THIRD_PARTY_NOTICES.md`.

---

## Credits

- JSBSim-Team for 25 years of open-source flight-dynamics
- Anthropic MCP for the protocol standard
- Hugging Face for Spaces hosting
