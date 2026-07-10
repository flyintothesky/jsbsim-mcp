# USAGE — three integration paths

```
        ┌─────────────────────────────────────────────────────────┐
        │               jsbsim-mcp (your HF Space)               │
        │   ┌──────────────┐         ┌─────────────────────┐     │
        │   │ MCP streamable│ ◄──HTTP+token ──┐              │     │
        │   │ /mcp         │                  │              │     │
        │   └──────────────┘                  │              │     │
        │   ┌──────────────────┐              │              │     │
        │   │ Web Dashboard    │ ◄── HTTPS ────┤              │     │
        │   │ / (HTML5)        │              │              │     │
        │   └──────────────────┘              │              │     │
        └─────────────────────────────────────────────────────────┘
                  ▲              ▲                  ▲
                  │              │                  │
        ┌─────────┴───┐  ┌────────┴──────────┐  ┌────┴───────────┐
        │ Claude      │  │ Claude            │  │ Browser /      │
        │ Desktop     │  │ Code / Cursor     │  │ Any MCP Agent  │
        └─────────────┘  └───────────────────┘  └────────────────┘
```

---

## Path 1 — Claude Desktop (network MCP)

In Claude Desktop's config:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "jsbsim-fdm": {
      "url": "https://<your-space>.hf.space/mcp"
    }
  }
}
```

Restart Claude Desktop. The "Tools" menu will list:

- list_aircraft, create_session, close_session, set_initial_conditions,
  trim, step, get_property, set_property, get_telemetry, execute_script

Then in Claude:

> "Configure a Cessna 172 at 8000 ft and cruise at 95kt. Trim and report
> the telemetry each minute."

---

## Path 2 — Claude Code / Cursor / Codex CLI (local stdio)

```json
{
  "mcpServers": {
    "jsbsim-fdm-local": {
      "command": "python",
      "args": ["/abs/path/to/jsbsim-mcp/run_stdio.py"],
      "env": { "JBSIM_ROOT": "/abs/path/to/jsbsim-mcp/jsbsim_data" }
    }
  }
}
```

After restart, tools become available locally.

---

## Path 3 — Web browser (WebSocket visualization)

Open `https://<your-space>.hf.space/` (or `http://localhost:7860/` for
local dev).

- Pick an aircraft from the dropdown.
- Set initial conditions (altitude, airspeed, heading).
- Click **Create session** → WebSocket opens, telemetry streams live.
- Click **Step** to advance simulated time manually.
- Click **Trim** to balance aerodynamic forces.
- Watch the PFD, 3D attitude and time-series charts.

The MCP JSON-RPC console at the bottom-left lets you hand-test
JSON-RPC 2.0 messages against `/mcp` directly.

---

## Token economy tips

- `get_telemetry` returns 40+ scalars in ONE call — use this instead of
  many `get_property` calls (saves tokens and round-trips).
- `jsbsim://sessions/{sid}/telemetry` is a Resource (one read).
- Path aliases save typing: prefer `alpha_deg` over
  `aero/alpha-deg`, etc. (planned Phase 2).

---

## Programmatic clients

### Python

```python
import httpx, json, uuid

URL = "https://<your>.hf.space"
SID = None

def rpc(method, params):
    r = httpx.post(f"{URL}/mcp", json={
        "jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": method, "params": params,
    }, headers={"Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"})
    data = r.text.split("data: ", 1)[-1]
    return json.loads(data)
```

---

## FAQ

**Q: Why is it sometimes slow on first request?**
A: JSBSim aircraft tables parse on first model load (~30 MB resident).
The HF Space caches them in memory after the first call.

**Q: Can two clients share one session?**
A: Not safely — concurrent stepping from two clients would interleave.
Use one session per client; sessions are isolated.

**Q: What happens after HF Space sleeps?**
A: The pool is reinitialised empty; clients get a 404 on `/api/sessions`
and should re-create their session.

---

## Privacy / security

- Token never logged.
- Session ids are random 12-char hex (96 bits entropy).
- Telemetry is sampled — no PII.
- No outbound network except to the JSBSim data path (which is local).
- See `THIRD_PARTY_NOTICES.md` for license boundaries.
