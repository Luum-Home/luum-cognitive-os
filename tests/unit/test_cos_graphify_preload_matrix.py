"""Tests for the Graphify preload matrix selector."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-graphify-preload-matrix"


def _run_json(*items: str) -> dict[str, object]:
    completed = subprocess.run(
        [str(SCRIPT), *items, "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_selects_harness_bundle_from_path() -> None:
    payload = _run_json("lib/harness_adapter/base.py")
    keys = [bundle["key"] for bundle in payload["bundles"]]

    assert keys == ["harness-events"]
    assert "lib/harness_adapter/base.py" in payload["preload_files"]
    assert any("test_harness_adapter_base.py" in command for command in payload["tests"])


def test_selects_multiple_bundles_without_duplicate_outputs() -> None:
    payload = _run_json("lib/harness_adapter/base.py", "hooks/destructive-git-blocker.sh")
    keys = [bundle["key"] for bundle in payload["bundles"]]

    assert keys == ["harness-events", "destructive-git"]
    assert len(payload["preload_files"]) == len(set(payload["preload_files"]))
    assert "hooks/destructive-git-blocker.sh" in payload["preload_files"]


def test_unknown_path_returns_empty_selection() -> None:
    payload = _run_json("docs/unknown.md")

    assert payload["bundles"] == []
    assert payload["preload_files"] == []
    assert payload["tests"] == []
