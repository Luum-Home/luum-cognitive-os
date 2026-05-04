from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "acc_pipeline.py"
REPORT = REPO_ROOT / "docs" / "acc" / "latest.json"
COMPACT = REPO_ROOT / "docs" / "acc" / "latest-compact.md"


def test_repository_acc_pipeline_generates_report() -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--project-dir", str(REPO_ROOT)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(REPORT.read_text())
    assert payload["schema_version"] == "acc.report.v1"
    assert payload["capabilities"]
    assert payload["mapping_statuses"] == ["aligned", "missing", "overexposed", "partial", "stale", "unverified"]
    assert "consumer_accessibility" in payload["capabilities"][0]
    assert "persistence" in payload
    assert payload["persistence"]["engram"]["status"] in {"unavailable", "ok"}
    for adapter in ("readiness:scripts", "readiness:hooks", "readiness:skills", "readiness:rules"):
        assert payload["adapters"][adapter]["status"] == "ok"
    assert payload["adapters"]["harness_projection"]["status"] == "ok"
    assert payload["harness_projection"]["claude"]["status"] == "implemented"
    assert payload["harness_projection"]["codex"]["status"] == "implemented"
    assert payload["harness_projection"]["cursor"]["status"] == "planned"
    assert COMPACT.exists()
    assert "Context Diet Rule" in COMPACT.read_text()


def test_harness_projection_manifest_declares_named_ides() -> None:
    manifest = yaml.safe_load((REPO_ROOT / "manifests" / "harness-projection.yaml").read_text())
    ids = {item["id"] for item in manifest["harnesses"]}
    required = {"claude", "codex", "cursor", "windsurf", "vscode-copilot", "opencode", "google-antigravity", "shell-ci"}

    assert required <= ids
    implemented = {item["id"] for item in manifest["harnesses"] if item["status"] == "implemented"}
    assert implemented == {"claude", "codex"}
