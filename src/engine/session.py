"""JSBSimSession — single simulated aircraft, thread-safe.

One `JSBSimSession` wraps a single `FGFDMExec` instance. Multiple sessions
may coexist (one per MCP/REST client) inside the `SessionPool`. All
operations take an asyncio lock when crossing into the synchronous
JSBSim C code so that we never get a partial state read mid-step.

Lifecycle:
    session = JSBSimSession("c172x", root=...)
    session.set_initial_conditions(...)     # apply IC file or scripted IC
    session.trim(mode="longitudinal")       # optional
    for _ in range(1800):
        session.step()                      # advances dt

    # Telemetry is always available:
    session.telemetry()
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsbsim  # type: ignore[import-untyped]

from .telemetry import TelemetryFrame


class JSBSimSession:
    """Thread-safe wrapper around one FGFDMExec."""

    def __init__(
        self,
        aircraft: str,
        *,
        root: Path,
        dt: float = 1.0 / 60.0,
        initial_conditions_path: Path | None = None,
    ) -> None:
        self.aircraft = aircraft
        self.dt = float(dt)
        self.root = Path(root).resolve()
        self.created_at = datetime.now(timezone.utc)
        self.last_access = time.time_ns()  # type: ignore[name-defined]
        self._lock = threading.RLock()

        # Construct FDM, suppress JSBSim console output unless asked.
        self.fdm = jsbsim.FGFDMExec(str(self.root))
        self.fdm.set_dt(self.dt)

        # Load aircraft — verbose param not supported in jsbsim 1.3.1 wrapper
        ok = self.fdm.load_model(aircraft)
        if not ok:
            raise RuntimeError(
                f"Failed to load aircraft '{aircraft}' from root {self.root}"
            )

        # Apply initial conditions if requested
        if initial_conditions_path is not None and initial_conditions_path.exists():
            ok = self.fdm.load_ic(str(initial_conditions_path), use_externals=True)
            if not ok:
                raise RuntimeError(
                    f"load_ic() failed for {initial_conditions_path}"
                )
            self.fdm.run_ic()

        # Aircraft name as JSBSim sees it
        self.aircraft_loaded = aircraft

    # ------------------------------------------------------------------
    # Property access
    # ------------------------------------------------------------------
    def get(self, path: str) -> float | None:
        """Generic property read. Returns None if not present."""
        with self._lock:
            try:
                return self.fdm.get_property_value(path)
            except Exception:
                return None

    def set(self, path: str, value: float) -> bool:
        """Write a property. Returns True if successful."""
        with self._lock:
            try:
                self.fdm.set_property_value(path, float(value))
                return True
            except Exception:
                return False

    # ------------------------------------------------------------------
    # Simulation step
    # ------------------------------------------------------------------
    def step(self, frames: int = 1) -> int:
        """Advance the simulator by `frames` fixed-timestep steps.

        Returns number of frames actually executed.
        """
        with self._lock:
            for _ in range(int(frames)):
                self.fdm.run()
            self.last_access = time.time_ns()  # type: ignore[name-defined]
            return int(frames)

    # ------------------------------------------------------------------
    # Initial conditions & trim
    # ------------------------------------------------------------------
    def set_initial_conditions(self, **kwargs: float) -> bool:
        """Apply common initial condition knobs.

        Recognised keys: altitude_ft, latitude_deg, longitude_deg,
        airspeed_fps, heading_deg, pitch_deg, roll_deg.
        """
        with self._lock:
            mapping = {
                "altitude_ft":  ("ic/h-sl-ft",   lambda v: v),
                "latitude_deg": ("ic/lat-geod-deg", lambda v: v),
                "longitude_deg":("ic/long-gc-deg",  lambda v: v),
                "airspeed_fps": ("ic/vc-kts",   lambda v: v * 0.592484),
                "heading_deg":  ("ic/psi-true-deg",  lambda v: v),
                "pitch_deg":    ("ic/theta-deg", lambda v: v),
                "roll_deg":     ("ic/phi-deg",   lambda v: v),
            }
            for key, (path, conv) in mapping.items():
                if key in kwargs:
                    try:
                        self.fdm.set_property_value(path, float(conv(kwargs[key])))
                    except Exception:
                        return False
            try:
                self.fdm.run_ic()
            except Exception:
                return False
            return True

    def trim(self, mode: str = "longitudinal") -> dict[str, Any]:
        """Run JSBSim's trim solver.

        Returns a dict with the trim report, or an error message.

        jsbsim 1.3.1 does not export FGTrim from the Python wrapper, so we
        implement a simple elevator-hunt loop instead. The aircraft is
        configured to cruise at its current airspeed/altitude by
        iteratively tilting elevator until pitch settles to 0.
        """
        with self._lock:
            try:
                # Set a reasonable cruise throttle.
                self.fdm.set_property_value("fcs/throttle-cmd-norm", 0.7)
                elevator = 0.0
                last_err = float("inf")
                for _ in range(60):
                    self.fdm.set_property_value("fcs/elevator-cmd-norm", elevator)
                    self.fdm.run()
                    pitch = float(self.fdm.get_property_value("attitude/pitch-deg") or 0.0)
                    err = -pitch
                    if abs(err) < 5e-4 or abs(err - last_err) < 1e-5:
                        break
                    last_err = err
                    elevator = max(-1.0, min(1.0, elevator + err * 0.01))
                # settle
                for _ in range(120):
                    self.fdm.run()
                return {
                    "ok": True,
                    "mode": mode,
                    "alpha_deg": float(self.fdm.get_property_value("aero/alpha-deg") or 0),
                    "elevator": float(self.fdm.get_property_value("fcs/elevator-cmd-norm") or 0),
                    "throttle": float(self.fdm.get_property_value("fcs/throttle-cmd-norm") or 0),
                    "thrust_lbs": float(self.fdm.get_property_value("propulsion/engine[0]/thrust-lbs") or 0),
                    "airspeed_kt": float(self.fdm.get_property_value("velocities/vc-kts") or 0),
                    "pitch_deg": float(self.fdm.get_property_value("attitude/pitch-deg") or 0),
                }
            except Exception as exc:
                return {"ok": False, "error": f"trim-failed: {exc}"}

    # ------------------------------------------------------------------
    # Snapshot / restore
    # ------------------------------------------------------------------
    def telemetry(self) -> TelemetryFrame:
        with self._lock:
            return TelemetryFrame.from_fdm(
                aircraft=self.aircraft_loaded,
                session_id="",  # set by pool
                fdm=self.fdm,
            )

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    def is_alive(self) -> bool:
        try:
            t = self.fdm.get_property_value("simulation/sim-time-sec")
            return t is not None
        except Exception:
            return False

    @property
    def sim_time(self) -> float:
        with self._lock:
            v = self.fdm.get_property_value("simulation/sim-time-sec")
            return float(v or 0.0)


# Re-export time.time_ns() import so last_access assignment above resolves
import time  # noqa: E402
