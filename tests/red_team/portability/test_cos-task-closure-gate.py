# SCOPE: os-only
"""Portability proof for scripts/cos-task-closure-gate wrapper."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WRAPPER = REPO_ROOT / "scripts" / "cos-task-closure-gate"


def test_wrapper_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    ledger = project / "closure.json"
    ledger.write_text(json.dumps({
        "schemaVersion": 1,
        "contract": "cos.task-closure-ledger.v1",
        "fronts": [{
            "id": "wrapper-front",
            "title": "Wrapper front",
            "status": "ready_next_slice",
            "canClaimComplete": False,
            "closureGate": "python3 -c 'raise SystemExit(0)'",
            "doneEvidence": ["wrapper reached python implementation"],
            "remaining": ["close wrapper proof"],
            "nextPrimitive": "Close wrapper proof.",
        }],
    }), encoding="utf-8")
    env = os.environ.copy()
    env.update({"COGNITIVE_OS_PROJECT_DIR": str(project), "PYTHONPATH": str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")})

    result = subprocess.run(
        [str(WRAPPER), str(ledger), "--json"],
        cwd=project,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert payload["fronts"][0]["id"] == "wrapper-front"
