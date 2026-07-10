"""End-to-end MCP protocol tests.

Validates:
  - Initialize handshake returns protocolVersion + serverInfo
  - tools/list enumerates all expected tools
  - tools/call round-trip for list_aircraft / create_session / step / get_telemetry / close_session
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


import subprocess
import time
import socket


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with contextlib_suppress(OSError):
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        time.sleep(0.1)
    return False


class contextlib_suppress:
    def __init__(self, *exc): self.exc = exc
    def __enter__(self): return self
    def __exit__(self, *args): return all(
        isinstance(args[1], e) for e in self.exc
    )


@pytest.fixture(scope="module")
def server_proc():
    port = _free_port()
    env = os.environ.copy()
    env["PORT"] = str(port)
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if not _wait_for_port(port, timeout=20.0):
        proc.terminate()
        stdout = proc.stdout.read(2000).decode("utf-8", errors="ignore")
        raise RuntimeError(f"server failed to start on port {port}.\nOutput:\n{stdout}")
    yield f"http://127.0.0.1:{port}"
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


def _post(url: str, payload: dict, *, session_id: str | None = None, timeout: float = 30.0) -> tuple[int, dict[str, str], str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    with httpx.Client(timeout=timeout) as c:
        r = c.post(url, json=payload, headers=headers)
        return r.status_code, dict(r.headers), r.text


def _parse_sse(text: str) -> dict:
    """Parse a minimal SSE message body of `event: message\\ndata: {json}`."""
    if text.startswith("event:"):
        for line in text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[len("data:"):].strip())
    if text.startswith("{"):
        return json.loads(text)
    return {}


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_initialize(server_proc):
    code, headers, body = _post(f"{server_proc}/mcp",
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                     "clientInfo": {"name": "test", "version": "0"}}})
    assert code == 200, f"got {code}: {body[:200]}"
    sid = headers.get("mcp-session-id")
    assert sid
    msg = _parse_sse(body)
    assert msg["id"] == 1
    assert "result" in msg
    assert msg["result"]["protocolVersion"] == "2025-06-18"
    assert msg["result"]["serverInfo"]["name"] == "jsbsim-fdm"


def test_tools_list(server_proc):
    code, headers, body = _post(f"{server_proc}/mcp",
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                     "clientInfo": {"name": "test", "version": "0"}}})
    sid = headers["mcp-session-id"]
    _post(f"{server_proc}/mcp",
          {"jsonrpc": "2.0", "method": "notifications/initialized"},
          session_id=sid)

    code, _, body = _post(f"{server_proc}/mcp",
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        session_id=sid)
    msg = _parse_sse(body)
    assert msg["id"] == 2
    tools = msg["result"]["tools"]
    names = {t["name"] for t in tools}
    expected = {
        "list_aircraft", "create_session", "close_session",
        "set_initial_conditions", "trim", "step", "get_property",
        "set_property", "get_telemetry", "execute_script",
    }
    assert expected.issubset(names), f"missing: {expected - names}"


def test_create_and_step_session(server_proc):
    code, headers, body = _post(f"{server_proc}/mcp",
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                     "clientInfo": {"name": "test", "version": "0"}}})
    sid = headers["mcp-session-id"]
    _post(f"{server_proc}/mcp",
          {"jsonrpc": "2.0", "method": "notifications/initialized"},
          session_id=sid)

    # list_aircraft
    code, _, body = _post(f"{server_proc}/mcp",
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "list_aircraft", "arguments": {}}},
        session_id=sid)
    msg = _parse_sse(body)
    aircraft = msg["result"]["structuredContent"]["aircraft"]
    assert "c172x" in aircraft

    # create_session
    code, _, body = _post(f"{server_proc}/mcp",
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "create_session",
                    "arguments": {"aircraft": "c172x",
                                  "initial_conditions": {"altitude_ft": 2500,
                                                         "airspeed_fps": 95 * 1.6878}}}},
        session_id=sid)
    msg = _parse_sse(body)
    text = msg["result"]["content"][0]["text"]
    payload = json.loads(text)
    simsid = payload["session_id"]
    assert simsid
    assert payload["aircraft"] == "c172x"

    # step
    code, _, body = _post(f"{server_proc}/mcp",
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "step", "arguments": {"session_id": simsid, "seconds": 1.0}}},
        session_id=sid)
    msg = _parse_sse(body)
    text = msg["result"]["content"][0]["text"]
    step_out = json.loads(text)
    assert step_out["frames"] >= 60
    assert step_out["sim_time"] >= 0.95

    # get_telemetry
    code, _, body = _post(f"{server_proc}/mcp",
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
         "params": {"name": "get_telemetry", "arguments": {"session_id": simsid}}},
        session_id=sid)
    msg = _parse_sse(body)
    text = msg["result"]["content"][0]["text"]
    telem = json.loads(text)
    assert 1500 < telem["alt_ft"] < 3500
    assert 50 < telem["airspeed_kt"] < 200

    # close_session
    code, _, body = _post(f"{server_proc}/mcp",
        {"jsonrpc": "2.0", "id": 7, "method": "tools/call",
         "params": {"name": "close_session", "arguments": {"session_id": simsid}}},
        session_id=sid)
    msg = _parse_sse(body)
    text = msg["result"]["content"][0]["text"]
    out = json.loads(text)
    assert out["ok"] is True
