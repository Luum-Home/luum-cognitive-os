"""Tests for the Graphify Phase D semantic wrapper."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-graphify-phase-d-semantic"


def test_phase_d_blocks_execute_when_backend_env_missing(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    completed = subprocess.run(
        [
            str(SCRIPT),
            "--execute",
            "--backend",
            "openai",
            "--slice",
            "skills",
            "--out-root",
            str(tmp_path / "out"),
            "--json",
        ],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert completed.returncode == 2
    assert payload["mode"] == "blocked"
    assert payload["backend_ready"] is False
    assert payload["slices"][0]["status"] == "blocked-backend-unavailable"


def test_phase_d_dry_run_records_slice_commands(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            str(SCRIPT),
            "--dry-run",
            "--backend",
            "ollama",
            "--slice",
            "rules",
            "--out-root",
            str(tmp_path / "out"),
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    command = payload["slices"][0]["command"]

    assert payload["mode"] == "dry-run"
    assert payload["slices"][0]["status"] == "dry-run"
    assert "--include-docs" in command
    assert "--dry-run" in command
