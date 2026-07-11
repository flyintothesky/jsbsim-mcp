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
short_description: JSBSim flight-dynamics engine as a self-hosted MCP service
---

# jsbsim-mcp — Self-Hosted MCP Service

> **JSBSim flight dynamics, exposed as an MCP service you run locally.**
> Bring your own compute — `pip install` or `docker run`, plug into any MCP-aware agent.

This is the **Self-Hosted distribution** of jsbsim-mcp.
It is **not** a hosted endpoint — you deploy it locally and bind it as an
MCP stdio server to Claude Desktop / Claude Code / Cursor / Codex.

For the deployed hosted version, see the HF Space mirror (separate project).

---

## 1. Install

### Option A — pip (recommended for Claude Desktop / Cursor / Codex)

```bash
pip install -e .
# or:
# pip install git+https://github.com/flyintothesky/jsbsim-mcp.git
```

Requires Python ≥ 3.10 and `jsbsim == 1.3.1`.

### Option B — Docker (recommended for sandboxing)

```bash
docker build -t jsbsim-mcp .
docker run --rm -it jsbsim-mcp stdio
```

### Option C — From this repo

```bash
git clone https://github.com/flyintothesky/jsbsim-mcp
cd jsbsim-mcp
pip install -r requirements.txt
python -m scripts.slim_data    # optional, ~24 MB → saves MB
python run_stdio.py
```

## 2. Wire into Claude Desktop / Cursor / Codex

`claude_desktop_config.json` (or its equivalent for your client):

```json
{
  "mcpServers": {
    "jsbsim-fdm-local": {
      "command": "python",
      "args": ["/abs/path/to/jsbsim-mcp/run_stdio.py"]
    }
  }
}
```

Restart Claude. Tools list appears:

```
list_aircraft        create_session      close_session
set_initial_conditions    trim           step
get_property        set_property        get_telemetry
execute_script
```

## 3. (Optional) Run the bundled web dashboard

Want a browser UI for the simulation? Run the same code as an HTTP server:

```bash
python app.py      # → http://localhost:7860/
```

- Live PFD
- 3D attitude indicator
- Time-series charts (altitude / speed / alpha / thrust)
- WebSocket telemetry at ~20 Hz
- Browser-side MCP JSON-RPC console

Works inside Docker as well:

```bash
docker run --rm -p 7860:7860 jsbsim-mcp
# then visit http://localhost:7860/
```

## 4. Tool reference (10 tools)

| Tool | Summary |
|---|---|
| `list_aircraft` | List 60+ bundled aircraft names |
| `create_session` | Spin up a session, return `session_id` |
| `close_session` | Tear it down |
| `set_initial_conditions` | Apply altitude / airspeed / heading etc. |
| `trim` | Iteratively balances elevator for level flight |
| `step` | Advance N simulated seconds |
| `get_property` | Read any JSBSim property by path |
| `set_property` | Write any JSBSim property |
| `get_telemetry` | One-shot 40+ scalar frame |
| `execute_script` | Load a `<run>` JSBSim script |

Full schema: `docs/API.md`.

## 5. Architecture

```
src/engine/    JSBSim wrapper + session pool + telemetry
src/server/    MCP protocol adapter (FastMCP, stdio + HTTP)
src/dashboard/ FastAPI dashboard + WebSocket broadcaster
app.py         Combined ASGI dispatcher (HTTP + WS + MCP)
run_stdio.py   Stdio entry for local Claude clients
```

LGPL-2.1 boundary preserved (JSBSim is dynamically linked). See
`THIRD_PARTY_NOTICES.md`.

---

## Why Self-Hosted?

JSBSim's open-source license permits redistribution, but the model
files (60 aircraft, ~30 MB) and C++ simulator itself are heavy. The
practical way to consume this in agents is:

1. `pip install` once.
2. Run **per-developer** as an MCP server via stdio.
3. Optionally start the dashboard for human-in-the-loop.

This avoids round-tripping 60 aircraft over a public MCP endpoint and
keeps your proprietary IC files local.

If you want a centrally hosted version for a team, see the
self-hosted Docker recipe in `docs/DEPLOY_MODELSCOPE.md` — point your
own HF Space / Render / Fly.io at the same source.

---

## License

- This project: **Apache-2.0**
- JSBSim dependency: **LGPL-2.1**

See `LICENSE` and `THIRD_PARTY_NOTICES.md`.
