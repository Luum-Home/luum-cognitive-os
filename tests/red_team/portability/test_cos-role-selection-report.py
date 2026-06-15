from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def run_script(script: str, *args: str, cwd: Path) -> dict:
    proc = subprocess.run([str(ROOT / script), *args, "--project-dir", str(cwd), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return json.loads(proc.stdout)

def test_cos_role_selection_report_smoke(tmp_path: Path):
    payload = run_script("scripts/cos-role-selection-report", "--goal", "fix bug with tests", cwd=tmp_path)
    assert payload["schema"] == "cos.efficiency.role-selection.v1"
    assert any(role["role"] == "planner" for role in payload["roles"])
