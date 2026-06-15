from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def test_cos_tdd_evidence_verify_smoke_without_runner(tmp_path: Path):
    proc = subprocess.run([str(ROOT / "scripts/cos-tdd-evidence-verify"), "--project-dir", str(tmp_path), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["schema"] == "cos.efficiency.tdd-evidence.v1"
    assert payload["strict_tdd_required"] is False
