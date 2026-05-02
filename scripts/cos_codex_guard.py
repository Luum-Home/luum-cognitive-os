#!/usr/bin/env python3
"""Compatibility wrapper for the generic governed-tool runner on Codex."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    runner = Path(__file__).with_name("cos_governed_runner.py")
    return subprocess.run(
        [sys.executable, str(runner), "--harness", "codex", *sys.argv[1:]],
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
