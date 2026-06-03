#!/usr/bin/env python3
"""Compatibility wrapper for the shared Cognitive OS DoD checker."""
from __future__ import annotations

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
runpy.run_path(str(ROOT / "scripts" / "dod_check.py"), run_name="__main__")
