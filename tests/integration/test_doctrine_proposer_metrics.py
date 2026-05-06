"""Integration test: cos_doctrine_proposer emits metrics with input_signals.

ADR-178 guarantees that every doctrine-proposer run emits one heartbeat
event to .cognitive-os/metrics/doctrine-proposals.jsonl with input_signals.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def isolated_project(tmp_path: Path) -> Path:
    """Create a minimal project copy with the bits doctrine-proposer needs."""
    proj = tmp_path / "proj"
    proj.mkdir()
    # Copy required dirs/files for the script to import successfully.
    for rel in ("scripts", "lib", "manifests"):
        src = PROJECT_ROOT / rel
        if src.exists():
            shutil.copytree(src, proj / rel, dirs_exist_ok=True)
    # external-adoption-evidence is required by claim signature audit
    ext_src = PROJECT_ROOT / "manifests" / "external-adoption-evidence.yaml"
    if ext_src.exists():
        (proj / "manifests" / "external-adoption-evidence.yaml").write_bytes(
            ext_src.read_bytes()
        )
    return proj


def test_doctrine_proposer_emits_metrics(isolated_project: Path):
    metrics_dir = isolated_project / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    script = isolated_project / "scripts" / "cos_doctrine_proposer.py"
    if not script.exists():
        pytest.skip("doctrine-proposer not present in checkout")

    result = subprocess.run(
        [sys.executable, str(script), "--project-dir", str(isolated_project), "--profile", "core"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # The proposer may emit non-zero on missing inputs; we only require
    # that the metrics file exists and contains a valid event.
    metrics_path = metrics_dir / "doctrine-proposals.jsonl"
    assert metrics_path.exists(), (
        f"doctrine-proposals.jsonl not created. stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    lines = [l for l in metrics_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert lines, "metrics file is empty"
    payload = json.loads(lines[-1])
    assert payload["kind"] == "doctrine-proposer-run"
    assert "input_signals" in payload
    sig = payload["input_signals"]
    # All four signals must be present as keys (values can be null when absent).
    for key in ("skillstore", "dogfood", "drift", "aspirational"):
        assert key in sig, f"input signal {key!r} missing"
