# SCOPE: os-only
"""Portability proof for scripts/cos_task_closure_gate.py."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "cos_task_closure_gate.py"


def _ledger(project: Path, front: dict) -> Path:
    path = project / "closure.json"
    path.write_text(json.dumps({"schemaVersion": 1, "contract": "cos.task-closure-ledger.v1", "fronts": [front]}), encoding="utf-8")
    return path


def _front(**overrides: object) -> dict:
    front = {
        "id": "portable-front",
        "title": "Portable front",
        "status": "ready_next_slice",
        "canClaimComplete": False,
        "closureGate": "python3 -c 'raise SystemExit(0)'",
        "doneEvidence": ["shape validated"],
        "remaining": ["close remaining portable work"],
        "nextPrimitive": "Close next portable slice.",
    }
    front.update(overrides)
    return front


def _env(project: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(project),
        "CODEX_PROJECT_DIR": str(project),
        "CLAUDE_PROJECT_DIR": str(project),
        "PYTHONPATH": str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
    })
    return env


def test_python_gate_validates_project_local_ledger_from_arbitrary_cwd(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    ledger = _ledger(project, _front())

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(ledger), "--json"],
        cwd=tmp_path,
        env=_env(project),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["fronts"][0]["id"] == "portable-front"


def test_python_gate_can_execute_project_local_closure_gate(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    marker = project / "gate-ran.txt"
    ledger = _ledger(
        project,
        _front(
            status="closed",
            canClaimComplete=True,
            remaining=[],
            closureGate=f"python3 -c \"from pathlib import Path; Path('{marker}').write_text('ok')\"",
        ),
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(ledger), "--project-dir", str(project), "--run-closure-gates", "--json"],
        cwd=tmp_path,
        env=_env(project),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert marker.read_text() == "ok"
    assert json.loads(result.stdout)["gate_runs"][0]["returncode"] == 0


def test_python_gate_fails_false_closed_claim_without_gate_evidence(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    ledger = _ledger(project, _front(status="closed", canClaimComplete=True, remaining=[]))

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(ledger), "--require-gates-passed", "--json"],
        cwd=tmp_path,
        env=_env(project),
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 1
    findings = json.loads(result.stdout)["findings"]
    assert any(item["code"] == "closed-front-missing-gate-evidence" for item in findings)
