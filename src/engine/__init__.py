"""Engine package — JSBSim wrapper + session pool + telemetry."""
from .session import JSBSimSession
from .pool import SessionPool, default_root
from .catalog import list_aircraft, describe_aircraft
from .telemetry import TelemetryFrame
from .properties import TELEMETRY_PROPERTIES, path_for, friendly_names

__all__ = [
    "JSBSimSession",
    "SessionPool",
    "default_root",
    "list_aircraft",
    "describe_aircraft",
    "TelemetryFrame",
    "TELEMETRY_PROPERTIES",
    "path_for",
    "friendly_names",
]
