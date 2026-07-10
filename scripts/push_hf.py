#!/usr/bin/env python3
"""Push jsbsim-mcp to a Hugging Face Space.

Usage:
    HF_TOKEN=hf_xxx HF_USERNAME=<you> HF_SPACE=jsbsim-mcp python scripts/push_hf.py

This script:
 1. Runs scripts/slim_data.py --apply to trim JSBSim data.
 2. Creates or updates the HF Space git repo.
 3. Pushes only the runtime-needed files (skips tests, venv, etc.).

Prereq:
    pip install huggingface_hub
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HF_USERNAME = os.environ.get("HF_USERNAME")
HF_SPACE = os.environ.get("HF_SPACE", "jsbsim-mcp")
HF_TOKEN = os.environ.get("HF_TOKEN")

if not HF_USERNAME or not HF_TOKEN:
    print("Set HF_USERNAME and HF_TOKEN environment variables.")
    sys.exit(1)

ALLOWED_FILES = [
    "app.py",
    "run_stdio.py",
    "src/",
    "jsbsim_data/",
    "docs/",
    "README.md",
    "Dockerfile",
    "requirements.txt",
    ".gitignore",
    "THIRD_PARTY_NOTICES.md",
    "CHANGELOG.md",
    "USAGE.md",
    "Makefile",
]


def step(cmd: list[str], cwd: Path | None = None) -> int:
    print(f"$ {' '.join(cmd)}  (cwd={cwd})")
    return subprocess.call(cmd, cwd=cwd)


def main() -> None:
    # 1. slim data
    print("== slim data ==")
    step([sys.executable, "scripts/slim_data.py", "--apply"], cwd=ROOT)

    # 2. clone the space
    space_url = f"https://{HF_USERNAME}:{HF_TOKEN}@huggingface.co/spaces/{HF_USERNAME}/{HF_SPACE}"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        ret = step(["git", "clone", space_url, str(tmp_path / "space")])
        if ret != 0:
            # Try to create the Space via HF API
            try:
                from huggingface_hub import HfApi
                HfApi(token=HF_TOKEN).create_repo(
                    repo_id=f"{HF_USERNAME}/{HF_SPACE}",
                    repo_type="space",
                    space_sdk="docker",
                    exist_ok=True,
                )
            except Exception as exc:
                print(f"Failed to create Space: {exc}")
                sys.exit(1)
            step(["git", "clone", space_url, str(tmp_path / "space")])

        target = tmp_path / "space"

        # 3. copy allowed files
        print("== copying runtime files ==")
        for entry in ALLOWED_FILES:
            src = ROOT / entry
            dst = target / entry
            if src.is_dir():
                # skip if dst exists
                step(["rsync", "-a", "--delete", str(src) + "/", str(dst) + "/"])
            elif src.exists():
                step(["cp", str(src), str(dst)])

        # 4. commit + push
        print("== committing and pushing ==")
        step(["git", "add", "-A"], cwd=target)
        step(["git", "commit", "-m", "Deploy jsbsim-mcp"], cwd=target)
        step(["git", "push"], cwd=target)
        print(f"\n  ==> Space pushed: https://huggingface.co/spaces/{HF_USERNAME}/{HF_SPACE}")


if __name__ == "__main__":
    main()
