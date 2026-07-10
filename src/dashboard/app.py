"""Web Dashboard — FastAPI entrypoint.

Mounted into the parent ASGI tree with the MCP streamable_http app:
- /mcp       — JSON-RPC 2.0 (streamable HTTP)
- /dashboard (or /) — single-page web UI
- /ws        — WebSocket telemetry stream
- /api/*     — convenience REST endpoints (mirrors MCP tools)
- /healthz   — health probe
"""
from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from ..engine import SessionPool, default_root, list_aircraft, TelemetryFrame


# ----------------------------------------------------------------------
# Lifecycle
# ----------------------------------------------------------------------
POOL: SessionPool | None = None


def _get_pool() -> SessionPool:
    global POOL
    if POOL is None:
        POOL = SessionPool(root=default_root())
        POOL.start()
    return POOL


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    pool = _get_pool()
    pool.start()
    try:
        yield
    finally:
        # Don't fully stop the pool — let the daemon thread keep GC'ing
        pass


# ----------------------------------------------------------------------
# ASGI App
# ----------------------------------------------------------------------
app = FastAPI(
    title="jsbsim-mcp Dashboard",
    version="0.1.0",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


STATIC_DIR = Path(__file__).parent / "static"


# ----------------------------------------------------------------------
# Health / readiness
# ----------------------------------------------------------------------
@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    pool = _get_pool()
    return {
        "status": "ok",
        "time": time.time(),
        "pool": pool.stats(),
        "pool_alive": True,
    }


@app.get("/readyz")
async def readyz() -> dict[str, Any]:
    return {"status": "ready"}


# ----------------------------------------------------------------------
# Convenience REST API (mirrors MCP tools but goes through same Pool)
# ----------------------------------------------------------------------
@app.get("/api/aircraft")
async def api_aircraft() -> dict[str, Any]:
    return {"aircraft": list_aircraft(default_root())}


@app.post("/api/sessions")
async def api_create(body: dict[str, Any]) -> dict[str, Any]:
    pool = _get_pool()
    aircraft = body["aircraft"]
    dt = body.get("dt")
    ic_path = body.get("ic_path")
    ic_path_p = Path(ic_path) if ic_path else None
    sid = pool.create(aircraft, ic_path=ic_path_p, dt=dt)
    s = pool.get(sid)
    assert s is not None
    ic = body.get("initial_conditions") or {}
    if ic:
        s.set_initial_conditions(**ic)
    return {
        "session_id": sid,
        "aircraft": s.aircraft_loaded,
        "dt": s.dt,
        "sim_time": s.sim_time,
    }


@app.delete("/api/sessions/{sid}")
async def api_close(sid: str) -> dict[str, Any]:
    pool = _get_pool()
    ok = pool.close(sid)
    return {"ok": ok}


@app.get("/api/sessions")
async def api_sessions() -> dict[str, Any]:
    pool = _get_pool()
    sids = pool.list_ids()
    return {"sessions": [pool.describe(s) for s in sids]}


@app.post("/api/sessions/{sid}/step")
async def api_step(sid: str, body: dict[str, Any]) -> dict[str, Any]:
    pool = _get_pool()
    s = pool.get(sid)
    if s is None:
        raise HTTPException(404)
    seconds = float(body.get("seconds", 1.0 / 60.0))
    frames = max(1, int(round(seconds / s.dt)))
    s.step(frames)
    return {"frames": frames, "sim_time": s.sim_time}


@app.post("/api/sessions/{sid}/trim")
async def api_trim(sid: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    pool = _get_pool()
    s = pool.get(sid)
    if s is None:
        raise HTTPException(404)
    mode = (body or {}).get("mode", "longitudinal")
    return s.trim(mode=mode)


@app.get("/api/sessions/{sid}/telemetry")
async def api_telemetry(sid: str) -> dict[str, Any]:
    pool = _get_pool()
    s = pool.get(sid)
    if s is None:
        raise HTTPException(404)
    return TelemetryFrame.from_fdm(aircraft=s.aircraft_loaded, session_id=sid, fdm=s.fdm).model_dump()


# ----------------------------------------------------------------------
# WebSocket — telemetry broadcaster
# ----------------------------------------------------------------------
class _WSBroadcaster:
    """Multiplexes active sessions across subscribers."""

    def __init__(self) -> None:
        self.subs: dict[str, set[WebSocket]] = {}
        self.locks: dict[str, asyncio.Lock] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    async def ensure_streaming(self, sid: str) -> None:
        if sid in self._tasks and not self._tasks[sid].done():
            return
        self._tasks[sid] = asyncio.create_task(self._drive(sid))

    async def _drive(self, sid: str) -> None:
        pool = _get_pool()
        s = pool.get(sid)
        if s is None:
            return
        async with (self.locks.setdefault(sid, asyncio.Lock())):
            while True:
                subs = self.subs.get(sid, set())
                if not subs:
                    break
                tf = TelemetryFrame.from_fdm(
                    aircraft=s.aircraft_loaded,
                    session_id=sid,
                    fdm=s.fdm,
                ).model_dump()
                msg = json.dumps({"type": "telemetry", "frame": tf})
                dead: list[WebSocket] = []
                for ws in subs:
                    try:
                        await ws.send_text(msg)
                    except Exception:
                        dead.append(ws)
                for d in dead:
                    subs.discard(d)
                # 20Hz default
                await asyncio.sleep(0.05)

    async def subscribe(self, sid: str, ws: WebSocket) -> None:
        await ws.accept()
        self.subs.setdefault(sid, set()).add(ws)
        await self.ensure_streaming(sid)
        try:
            while True:
                # We don't expect inbound; just keep the channel alive
                msg = await ws.receive_text()
                if msg == "ping":
                    await ws.send_text("pong")
        except WebSocketDisconnect:
            pass
        finally:
            self.subs.get(sid, set()).discard(ws)


broadcaster = _WSBroadcaster()


@app.websocket("/ws/{sid}")
async def ws_telemetry(ws: WebSocket, sid: str) -> None:
    pool = _get_pool()
    if pool.get(sid) is None:
        await ws.close(code=4404)
        return
    await broadcaster.subscribe(sid, ws)


# ----------------------------------------------------------------------
# Static UI
# ----------------------------------------------------------------------
@app.get("/")
async def root_dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@app.get("/favicon.ico")
async def favicon() -> FileResponse:
    f = STATIC_DIR / "favicon.ico"
    if not f.exists():
        raise HTTPException(404)
    return FileResponse(f)
