# Deploying jsbsim-mcp to ModelScope MCP — Self-Hosted

> Recommended path: register metadata only, users run `pip install` and
> `run_stdio.py` locally. No public endpoint required.

## 1. Push code (already done in v0.1.0)

```bash
git init
git add -A
git commit -m "Initial"
git remote add origin https://github.com/<your-name>/jsbsim-mcp.git
git push
```

## 2. Register on ModelScope

https://www.modelscope.cn/mcp/create

Fill the form — for **all copy-paste content** see `docs/MAGICSTUDIO.md`.

| Field | Value |
|---|---|
| Service name | `jsbsim-fdm-local` |
| Display name | `JSBSim 飞行动力学仿真` |
| Description (zh + en) | from `docs/MAGICSTUDIO.md` |
| Tags | flight-simulation, FDM, self-hosted, developer-tools, mcp |
| Source URL | `https://github.com/flyintothesky/jsbsim-mcp` |
| Deployment | **Self-Hosted / Local stdio** |
| server_config | stdio block from MAGICSTUDIO.md |

⚠️ Do NOT pick "Hosted / streamable_http" — it requires a public URL we
don't have.

## 3. User installation

```bash
pip install "git+https://github.com/flyintothesky/jsbsim-mcp.git"
```

This installs `jsbsim == 1.3.1` (LGPL-2.1) as a dependency.

## 4. Connect to Claude Desktop / Cursor / Codex

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

Restart Claude.

## 5. License notes

Apache-2.0 (this project) + LGPL-2.1 (JSBSim dep, dynamically linked).
See `THIRD_PARTY_NOTICES.md` for full attribution.
