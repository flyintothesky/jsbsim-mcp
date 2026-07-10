"""Unit + smoke tests for the engine layer.

Run:  pytest tests/ -v

Prerequisites:
  source .venv/bin/activate
  The jsbsim_data/ directory must exist at the project root.
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Some test runs happen from project root; ensure cwd points there.
import os
os.chdir(ROOT)


from src.engine import (
    JSBSimSession,
    SessionPool,
    TelemetryFrame,
    describe_aircraft,
    list_aircraft,
)


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture(scope="session")
def root_path() -> Path:
    p = ROOT / "jsbsim_data"
    if not p.is_dir():
        pytest.skip(f"jsbsim_data/ not found at {p}")
    return p


@pytest.fixture
def quiet_jsbsim():
    """Redirect stdout/stderr to devnull during FDM init (it prints ~3MB of
    aircraft geometry which clutters test output)."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield


@pytest.fixture
def session(root_path, quiet_jsbsim) -> JSBSimSession:
    return JSBSimSession("c172x", root=root_path, dt=1.0 / 60.0)


@pytest.fixture
def pool(root_path) -> SessionPool:
    p = SessionPool(root=root_path, idle_ttl_sec=60, max_sessions=8)
    p.start()
    yield p
    p.stop()


# ----------------------------------------------------------------------
# catalog
# ----------------------------------------------------------------------
def test_list_aircraft_finds_c172x(root_path):
    names = list_aircraft(root_path)
    assert isinstance(names, list)
    assert "c172x" in names
    assert len(names) >= 10


def test_describe_aircraft_returns_path(root_path):
    d = describe_aircraft(root_path, "c172x")
    assert d["exists"] is True
    assert "path" in d
    assert d["path"].endswith(".xml")


def test_describe_aircraft_unknown_returns_not_exists(root_path):
    d = describe_aircraft(root_path, "definitely_not_real")
    assert d["exists"] is False


# ----------------------------------------------------------------------
# JSBSimSession
# ----------------------------------------------------------------------
def test_session_loaded_aircraft(session, root_path):
    assert session.aircraft_loaded == "c172x"


def test_session_step_advances_time(session):
    t0 = session.sim_time
    session.step(60)
    assert session.sim_time >= t0 + 0.95  # 60 frames at 1/60 = ~1 sec, allow slop


def test_session_telemetry_returns_frame(session, root_path):
    session.set_initial_conditions(altitude_ft=2000.0, airspeed_fps=80 * 1.6878)
    tf = session.telemetry()
    assert isinstance(tf, TelemetryFrame)
    assert tf.aircraft == "c172x"
    # After IC + a few steps the altitude reading should be near 2000 +/- a few hundred
    assert 1500 < tf.alt_ft < 2500


def test_session_get_set_property(session):
    assert session.set("fcs/throttle-cmd-norm", 0.5) is True
    v = session.get("fcs/throttle-cmd-norm")
    assert v is not None
    assert 0.45 < float(v) < 0.55


def test_session_get_unknown_property_returns_none(session):
    # JSBSim's get_property_value returns 0.0 for unknown paths; we treat
    # this as "not present" upstream, which is the expected contract.
    assert session.get("not/a/real/path") in (None, 0.0)


def test_session_trim_longitudinal(session):
    session.set_initial_conditions(altitude_ft=5000.0, airspeed_fps=110 * 1.6878)
    report = session.trim("longitudinal")
    assert isinstance(report, dict)
    assert "ok" in report
    # Trim report should include theta / elevator values
    if report.get("ok"):
        assert "alpha_deg" in report


def test_session_ic_keys_accepted(session):
    ok = session.set_initial_conditions(
        altitude_ft=3500.0,
        airspeed_fps=100 * 1.6878,
        heading_deg=90.0,
        pitch_deg=2.0,
        roll_deg=5.0,
    )
    assert ok is True


# ----------------------------------------------------------------------
# SessionPool
# ----------------------------------------------------------------------
def test_pool_create_and_get(root_path, pool):
    sid = pool.create("c172x")
    assert sid
    s = pool.get(sid)
    assert s is not None
    assert s.aircraft_loaded == "c172x"


def test_pool_close_removes(root_path, pool):
    sid = pool.create("c172x")
    assert pool.close(sid) is True
    assert pool.get(sid) is None


def test_pool_list_ids(root_path, pool):
    a = pool.create("c172x")
    b = pool.create("c172x")
    sids = pool.list_ids()
    assert a in sids
    assert b in sids
    pool.close(a)
    pool.close(b)


def test_pool_stats_shape(root_path, pool):
    s = pool.stats()
    assert s["active"] == 0
    pool.create("c172x")
    s = pool.stats()
    assert s["active"] == 1
    assert "max" in s and "ttl_sec" in s


def test_pool_max_evicts(root_path):
    p = SessionPool(root=root_path, max_sessions=2, idle_ttl_sec=60)
    p.start()
    p.create("c172x")
    p.create("c172x")
    p.create("c172x")  # should evict oldest
    assert p.stats()["active"] <= 2
    p.stop()


def test_pool_idle_ttl_evicts(root_path, monkeypatch):
    """Force TTL to elapse and verify GC."""
    p = SessionPool(root=root_path, max_sessions=4, idle_ttl_sec=0)
    p.start()
    sid = p.create("c172x")
    assert sid in p.list_ids()
    # Let the eviction trigger once
    import time as _t
    _t.sleep(2.0)
    removed = p.collect_garbage()
    p.stop()
    assert removed >= 1


# ----------------------------------------------------------------------
# TelemetryFrame
# ----------------------------------------------------------------------
def test_telemetry_frame_from_fdm(session):
    session.set_initial_conditions(altitude_ft=2500.0, airspeed_fps=85 * 1.6878)
    session.step(30)
    tf = TelemetryFrame.from_fdm(aircraft="c172x", session_id="x", fdm=session.fdm)
    assert tf.alt_ft > 2000
    assert 50 < tf.airspeed_kt < 200
    assert -5 < tf.alpha_deg < 20
    assert -90 <= tf.heading_deg <= 360
    assert tf.mach > 0
