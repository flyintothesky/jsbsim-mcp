"""Stdio entrypoint — for Claude Code / Cursor / Codex CLI local use.

Usage:
    python run_stdio.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.server import run_stdio


if __name__ == "__main__":
    run_stdio()
