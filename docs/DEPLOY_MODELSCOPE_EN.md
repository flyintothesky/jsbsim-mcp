# Deploying jsbsim-mcp to ModelScope MCP

> English version. Push this repo to GitHub first, then create a Hosted MCP entry on ModelScope.

## 0. Prerequisites

- A public GitHub repository for this project
- A ModelScope account
- ≈10 min

## 1. Push the code

```bash
git init
git add -A
git commit -m "Initial: jsbsim-mcp v0.1.0"
git branch -M main
git remote add origin https://github.com/<your-name>/jsbsim-mcp.git
git push -u origin main
```

## 2. Create MCP service on ModelScope

URL: https://www.modelscope.cn/mcp/create

Fill the form:

| Field | Value |
|---|---|
| Service name (CN) | JSBSim 飞行动力学仿真 |
| Service name (EN) | `jsbsim-fdm` |
| Description | See "Description template" below |
| Tags | `flight-simulation`, `FDM`, `aircraft`, `physics`, `simulation`, `developer-tools` |
| Repository | `https://github.com/<your-name>/jsbsim-mcp` |
| Deployment | **Hosted MCP (streamable_http)** |
| URL | `https://<your-deployment>.example.com/mcp` |
| Auth | `none` |
| License | `Apache-2.0` |

### Description template

```
JSBSim Flight Dynamics Model as a hosted MCP service.

Wraps the industry-standard open-source 6-DoF FDM (JSBSim v1.3.1)
behind the Model Context Protocol so any MCP-aware agent
(Claude / Cursor / Codex / Claude Code) can drive real-time
flight simulation in plain English.

Bundles 60 aircraft (C172, A320, F-16, 737, Concorde, X-15 …) and a Web Dashboard.

Tools (10):
- list_aircraft / create_session / close_session
- set_initial_conditions / trim / step
- get_property / set_property / get_telemetry
- execute_script

Resources (7):
- jsbsim://aircraft
- jsbsim://aircraft/{name}
- jsbsim://engines
- jsbsim://sessions
- jsbsim://sessions/{sid}/telemetry

Prompts (2):
- cruise_c172
- stall_recovery

License: Apache-2.0 (this code) + LGPL-2.1 (JSBSim dependency)
```

## 3. After deployment

You will receive a hash-based URL of the form:

```
https://mcp.api-inference.modelscope.net/<hash>/mcp
```

Use it in any MCP client.

## 4. Connection examples

### Claude Desktop / Cursor

```json
{
  "mcpServers": {
    "jsbsim-fdm": {
      "url": "https://mcp.api-inference.modelscope.net/<your-hash>/mcp"
    }
  }
}
```

### Claude Code / Codex CLI (local stdio fallback)

```bash
git clone https://github.com/<your-name>/jsbsim-mcp
cd jsbsim-mcp
pip install -r requirements.txt
python make-data.py
python run_stdio.py
```

## 5. (Advanced) Combine with `unreal-engine-mcp`

In a single `mcpServers` JSON, register both — Claude Agent
will orchestrate them in a ReAct loop:

```json
{
  "mcpServers": {
    "jsbsim-fdm":        { "url": "https://mcp.api-inference.modelscope.net/<a>/mcp" },
    "unreal-engine-mcp": { "command": "npx", "args": ["-y", "unreal-engine-mcp-server@0.5.13"] }
  }
}
```

## 6. License Notes

This project is **Apache-2.0**; the bundled JSBSim library is **LGPL-2.1**.
JSBSim is dynamically linked (loaded via `pip install jsbsim`), preserving LGPL
compatibility. See `THIRD_PARTY_NOTICES.md`.
