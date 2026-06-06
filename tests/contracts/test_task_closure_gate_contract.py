from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]


def test_task_closure_gate_is_lifecycle_declared_consumer_surface() -> None:
    lifecycle = yaml.safe_load((REPO / "manifests" / "primitive-lifecycle.yaml").read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in lifecycle["primitives"] if isinstance(item, dict)}

    wrapper = by_id["scripts/cos-task-closure-gate"]
    engine = by_id["scripts/cos_task_closure_gate.py"]
    assert wrapper["owner_adr"] == "ADR-335"
    assert wrapper["distribution"] == "core"
    assert wrapper["consumer_accessibility"] == "lifecycle-declared-shared-surface"
    assert "scripts/cos_task_closure_gate.py" in wrapper["projection_targets"]
    assert engine["owner_adr"] == "ADR-335"


def test_task_closure_template_matches_cli_schema() -> None:
    template = REPO / "templates" / "task-closure-ledger.example.json"
    payload = json.loads(template.read_text(encoding="utf-8"))
    assert payload["contract"] == "cos.task-closure-ledger.v1"

    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "cos_task_closure_gate.py"), str(template), "--json"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "pass"
    assert report["fronts"][0]["id"] == "example-front"


def test_task_closure_docs_reference_contract_and_installed_binary() -> None:
    text = (REPO / "docs" / "04-Concepts" / "architecture" / "task-closure-ledger-gate.md").read_text(encoding="utf-8")
    assert "cos.task-closure-ledger.v1" in text
    assert ".cognitive-os/bin/cos-task-closure-gate" in text
    assert "canClaimComplete=true" in text
