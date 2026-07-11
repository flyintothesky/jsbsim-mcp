"""SessionPool — LRU + TTL-bounded sessions.

Concurrency model
-----------------
Concurrent MCP/REST clients each get a session_id (UUID4). The pool keeps
sessions keyed by id. Each session has its own RLock so two clients stepping
the *same* session would still be linearised (rare; mainly there for fast
telemetry reads).

Idle sessions auto-close after `idle_ttl_sec` (default 300).
Hard limit `max_sessions` defaults to 64 (HF Spaces friendly).
"""
from __future__ import annotations

import os
import threading
import time as _time
import uuid
from pathlib import Path
from typing import Any, Optional

from .session import JSBSimSession


class SessionPool:
    def __init__(
        self,
        *,
        root: Path,
        max_sessions: int = 64,
        idle_ttl_sec: int = 300,
        dt_default: float = 1.0 / 60.0,
    ) -> None:
        self.root = Path(root).resolve()
        self.max_sessions = max_sessions
        self.idle_ttl_sec = idle_ttl_sec
        self.dt_default = dt_default
        self._sessions: dict[str, tuple[JSBSimSession, int]] = {}
        self._lock = threading.Lock()
        self._ttl_thread: Optional[threading.Thread] = None
        self._stop = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._ttl_thread is None or not self._ttl_thread.is_alive():
            self._stop = False
            self._ttl_thread = threading.Thread(target=self._ttl_loop, daemon=True)
            self._ttl_thread.start()

    def stop(self) -> None:
        self._stop = True

    def _ttl_loop(self) -> None:
        while not self._stop:
            _time.sleep(15)
            try:
                self.collect_garbage()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def create(
        self,
        aircraft: str,
        *,
        ic_path: Optional[Path] = None,
        dt: Optional[float] = None,
    ) -> str:
        with self._lock:
            if len(self._sessions) >= self.max_sessions:
                self._evict_oldest()
            sid = uuid.uuid4().hex[:12]
            session = JSBSimSession(
                aircraft,
                root=self.root,
                dt=dt or self.dt_default,
                initial_conditions_path=ic_path,
            )
            self._sessions[sid] = (session, _time.time_ns())
            self.start()
            return sid

    def get(self, sid: str) -> JSBSimSession | None:
        with self._lock:
            entry = self._sessions.get(sid)
            if entry is None:
                return None
            session, _ = entry
            self._sessions[sid] = (session, _time.time_ns())
            return session

    def close(self, sid: str) -> bool:
        with self._lock:
            entry = self._sessions.pop(sid, None)
            if entry is None:
                return False
            return True

    def list_ids(self) -> list[str]:
        with self._lock:
            return list(self._sessions.keys())

    def describe(self, sid: str) -> dict[str, Any] | None:
        s = self.get(sid)
        if s is None:
            return None
        return {
            "session_id": sid,
            "aircraft": s.aircraft_loaded,
            "dt": s.dt,
            "sim_time": s.sim_time,
            "created_at": s.created_at.isoformat(),
            "last_access_ns": s.last_access,
        }

    # ------------------------------------------------------------------
    # GC
    # ------------------------------------------------------------------
    def _evict_oldest(self) -> None:
        if not self._sessions:
            return
        oldest = min(self._sessions.items(), key=lambda kv: kv[1][1])[0]
        self._sessions.pop(oldest, None)

    def collect_garbage(self) -> int:
        """Close sessions older than idle_ttl_sec. Returns removed count."""
        cutoff = _time.time_ns() - self.idle_ttl_sec * 1_000_000_000
        removed = 0
        with self._lock:
            stale = [sid for sid, (_, t) in self._sessions.items() if t < cutoff]
            for sid in stale:
                if self._sessions.pop(sid, None) is not None:
                    removed += 1
        return removed

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active": len(self._sessions),
                "max": self.max_sessions,
                "ids": list(self._sessions.keys()),
                "root": str(self.root),
                "ttl_sec": self.idle_ttl_sec,
            }


def default_root() -> Path:
    env = os.environ.get("JBSIM_ROOT")
    if env:
        return Path(env)
    # project-relative fallback: look in current working dir, then
    # walked-up parents for jsbsim_data/.
    here = Path.cwd()
    for _ in range(5):
        candidate = here / "jsbsim_data"
        if candidate.is_dir():
            return candidate
        here = here.parent
    return Path(".")


# ----------------------------------------------------------------------
# Singleton: BOTH the MCP server and the dashboard app must reference
# the SAME pool instance, otherwise sessions created over MCP are not
# visible to the dashboard's REST endpoints (or vice versa).
# ----------------------------------------------------------------------
_SHARED_POOL: SessionPool | None = None
_SHARED_LOCK = None


def _lock():
    global _SHARED_LOCK
    if _SHARED_LOCK is None:
        import threading as _t
        _SHARED_LOCK = _t.Lock()
    return _SHARED_LOCK


def shared_pool() -> SessionPool:
    """Return the process-wide singleton SessionPool.

    Created lazily on first call. Backed by a thread-safe lazy init so
    that multiple modules (MCP server, dashboard) get the same instance.
    """
    global _SHARED_POOL
    if _SHARED_POOL is not None:
        return _SHARED_POOL
    with _lock():
        if _SHARED_POOL is None:
            _SHARED_POOL = SessionPool(root=default_root())
            _SHARED_POOL.start()
        return _SHARED_POOL


def reset_shared_pool() -> None:
    """Tests only. Resets the singleton so a new pool can be created."""
    global _SHARED_POOL
    with _lock():
        _SHARED_POOL = None
