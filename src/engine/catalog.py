"""Catalog — scan the bundled JSBSim `aircraft/` directory.

Used by `list_aircraft` MCP tool and `jsbsim://aircraft` resource.
Each entry is just the directory name — JSBSim itself does the heavy
lifting during load_model(). We make sure the candidate looks valid.
"""
from __future__ import annotations

import os
import re
from pathlib import Path


# JSBSim expects each aircraft dir to contain a `<name>.xml` entry,
# but practically the file is `aircraft.xml` with `name` differing.
_AIRCFG_RX = re.compile(r'name="([^"]+)"', re.MULTILINE)


def list_aircraft(root: Path) -> list[str]:
    """Return available aircraft names from root/aircraft/*.

    Skip anything that isn't a directory with at least one XML.
    """
    aircraft_dir = Path(root) / "aircraft"
    if not aircraft_dir.is_dir():
        return []
    out: list[str] = []
    for child in sorted(aircraft_dir.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        # 'aircraft_template.xml' directories are not aircraft
        if name.startswith("aircraft_template"):
            continue
        # Need at least one .xml
        if not any(child.glob("*.xml")):
            continue
        out.append(name)
    return out


def describe_aircraft(root: Path, name: str) -> dict[str, object]:
    """Parse the aircraft XML for a few common fields."""
    d = Path(root) / "aircraft" / name
    if not d.is_dir():
        return {"exists": False, "name": name}
    xml_path = next((p for p in d.glob("*.xml")), None)
    if xml_path is None:
        return {"exists": False, "name": name}
    text = xml_path.read_text(errors="ignore")
    m = _AIRCFG_RX.search(text)
    return {
        "exists": True,
        "name": name,
        "path": str(xml_path),
        "header": m.group(1) if m else None,
    }
