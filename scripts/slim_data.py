#!/usr/bin/env python3
"""Strip jsbsim_data/ of files not needed at runtime.

Usage:
    python scripts/slim_data.py [--apply]

Without --apply, prints what would be removed. With --apply, actually
deletes (after printing a summary). Run from project root.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "jsbsim_data"

REMOVE = [
    # Build + dev artifacts
    "CMakeLists.txt",
    "CMakeCache.txt",
    "cmake_install.cmake",
    "Makefile",
    "*.vcxproj*",
    "*.sln",
    "*.iss.in",
    "*.pc.in",
    "*.xsd",
    "*.xsl",
    "*.cff",
    "COPYING",
    "AUTHORS",
    "*.md",
    ".gitignore",
    ".gitattributes",
    "codecov.yml",
]

REMOVE_DIRS = [
    # Source code unrelated to runtime
    "src",
    "src/engine",
    "src/models",
    "src/simgear",
    "src/GeographicLib",
    "src/initialization",
    "src/input_output",
    "src/math",
    "src/tests",
    "engine",
    "examples",
    "doc",
    "joss_paper",
    "admin",
    # Build dirs
    "build",
    ".vscode",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Actually delete the files (default: dry-run)")
    args = parser.parse_args()

    if not DATA.is_dir():
        print(f"skip: {DATA} is not a directory")
        return

    removed_dirs = 0
    removed_files = 0
    freed_bytes = 0

    # Top-level files
    for pattern in REMOVE:
        for p in DATA.glob(pattern):
            if not p.exists():
                continue
            size = p.stat().st_size if p.is_file() else 0
            print(f"  {'rm' if args.apply else 'would rm'} {p.relative_to(ROOT)} ({size:,} B)")
            if args.apply:
                if p.is_dir():
                    shutil.rmtree(p)
                    removed_dirs += 1
                else:
                    freed_bytes += size
                    p.unlink()
                    removed_files += 1

    # Top-level dirs
    for d in REMOVE_DIRS:
        p = DATA / d
        if not p.exists():
            continue
        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        print(f"  {'rm' if args.apply else 'would rm'} {p.relative_to(ROOT)}/ (~{size:,} B)")
        if args.apply:
            shutil.rmtree(p)
            removed_dirs += 1
            freed_bytes += size

    if args.apply:
        print(f"\n  -> removed {removed_files} files and {removed_dirs} dirs")
        print(f"  -> freed ~{freed_bytes / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
