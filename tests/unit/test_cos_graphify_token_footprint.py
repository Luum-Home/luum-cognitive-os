"""Tests for Graphify token-footprint estimation."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-graphify-token-footprint"


def test_estimates_harness_preload_reduction() -> None:
    completed = subprocess.run(
        [str(SCRIPT), "lib/harness_adapter/base.py", "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["bundle_keys"] == ["harness-events"]
    assert payload["baseline"]["estimated_tokens"] > payload["preload"]["estimated_tokens"]
    assert payload["estimated_reduction_ratio"] > 1
    assert "lib/harness_adapter/base.py" in payload["preload"]["token_by_file"]


def test_unknown_path_has_zero_reduction() -> None:
    completed = subprocess.run(
        [str(SCRIPT), "docs/unknown.md", "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["bundle_keys"] == []
    assert payload["baseline"]["estimated_tokens"] == 0
    assert payload["preload"]["estimated_tokens"] == 0
    assert payload["estimated_reduction_ratio"] == 0
