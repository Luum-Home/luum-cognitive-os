from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_cos_init_installs_task_closure_gate_binary_and_template(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    (project / "README.md").write_text("consumer\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "cos_init.py"), "--default", "--harness", "codex"],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    wrapper = project / ".cognitive-os" / "bin" / "cos-task-closure-gate"
    engine = project / ".cognitive-os" / "bin" / "cos_task_closure_gate.py"
    template = project / ".cognitive-os" / "templates" / "cos" / "task-closure-ledger.example.json"
    assert wrapper.exists()
    assert engine.exists()
    assert template.exists()

    ledger = project / "closure.json"
    ledger.write_text(json.dumps({
        "schemaVersion": 1,
        "contract": "cos.task-closure-ledger.v1",
        "fronts": [{
            "id": "consumer-front",
            "title": "Consumer front",
            "status": "ready_next_slice",
            "canClaimComplete": False,
            "closureGate": "python3 -c 'raise SystemExit(0)'",
            "doneEvidence": ["consumer installed gate"],
            "remaining": ["close consumer front"],
            "nextPrimitive": "Close consumer front.",
        }],
    }), encoding="utf-8")
    smoke = subprocess.run([str(wrapper), str(ledger), "--json"], cwd=project, text=True, capture_output=True, check=False)
    assert smoke.returncode == 0, smoke.stderr
    assert json.loads(smoke.stdout)["fronts"][0]["id"] == "consumer-front"
