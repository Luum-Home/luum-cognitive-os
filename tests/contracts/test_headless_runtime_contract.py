from __future__ import annotations

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "cos-headless-runtime-contract"
PIPELINE = PROJECT_ROOT / "scripts" / "cos-headless-pipeline"


def test_headless_runtime_contract_passes_static_manifests() -> None:
    result = subprocess.run([str(SCRIPT)], cwd=PROJECT_ROOT, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["errors"] == []


def test_headless_pipeline_runs_runtime_contract_before_docker_drill() -> None:
    text = PIPELINE.read_text(encoding="utf-8")
    assert "headless-runtime-contract" in text
    assert text.index("headless-runtime-contract") < text.index("docker-service-drill")
