"""Unified ASGI app — Dashboard FastAPI + MCP streamable_http.

Strategy
--------
FastMCP's `streamable_http_app()` returns a Starlette whose internal route
is `/mcp` (default `streamable_http_path`). If we Mount("/mcp", subapp),
Starlette's Mount *strips* the `/mcp` prefix before forwarding, which
breaks the inner `/mcp` route.

We can't cleanly make Starlette preserve prefixes, so instead we use a
custom ASGI dispatcher that:
  * routes `/mcp` (and `/mcp/...`) directly to `mcp_subapp` (no rewrite)
  * routes everything else to the dashboard FastAPI

Lifespan is driven by the parent. The MCP sub-app's lifespan is started
manually inside `_combined_lifespan` via `session_manager.run()`.
"""
from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from src.server.registry import mcp as mcp_instance, get_pool
from src.dashboard.app import app as dashboard_fastapi


# ----------------------------------------------------------------------
# Sub-apps
# ----------------------------------------------------------------------
mcp_subapp = mcp_instance.streamable_http_app()


# ----------------------------------------------------------------------
# Lifespan: drive FastMCP's StreamableHTTPSessionManager task group
# ----------------------------------------------------------------------
@asynccontextmanager
async def _combined_lifespan(app):
    sm = mcp_instance.session_manager
    async with sm.run():
        get_pool()
        yield


# ----------------------------------------------------------------------
# Parent ASGI dispatcher
# ----------------------------------------------------------------------
class Dispatcher:
    def __init__(self, mcp_app, dashboard_app):
        self.mcp_app = mcp_app
        self.dashboard_app = dashboard_app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            # Route lifespan to parent's lifespan manager only.
            while True:
                msg = await receive()
                if msg["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif msg["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
            return

        path = scope.get("path", "")
        if path == "/mcp" or path.startswith("/mcp/"):
            await self.mcp_app(scope, receive, send)
        else:
            await self.dashboard_app(scope, receive, send)


parent = Dispatcher(mcp_subapp, dashboard_fastapi)


# ----------------------------------------------------------------------
# A thin Starlette instance for uvicorn (provides proper startup/shutdown
# life-cycle events; we could call uvicorn directly with the dispatcher,
# but using Starlette gives us the `lifespan=` for free).
# ----------------------------------------------------------------------
_starlette_root = Starlette(
    routes=[],
    middleware=[Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])],
    lifespan=_combined_lifespan,
)


# Wrap so that uvicorn calls our dispatcher when ASGI is invoked.
class Root:
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    async def __call__(self, scope, receive, send):
        # Run asgi based on scope
        if scope["type"] == "lifespan":
            # The Starlette instance handles lifespan
            await _starlette_root(scope, receive, send)
        else:
            await self.dispatcher(scope, receive, send)


parent = Root(parent)


# ----------------------------------------------------------------------
# Run as:  python app.py
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "7860"))
    print(f"🚀 jsbsim-mcp listening on http://0.0.0.0:{port}")
    print(f"   Dashboard:       http://0.0.0.0:{port}/")
    print(f"   MCP JSON-RPC:    http://0.0.0.0:{port}/mcp")
    print(f"   Health:          http://0.0.0.0:{port}/healthz")
    uvicorn.run(parent, host="0.0.0.0", port=port, log_level="info")
