from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def run_script(script: str, *args: str, cwd: Path) -> dict:
    proc = subprocess.run([str(ROOT / script), *args, "--project-dir", str(cwd), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return json.loads(proc.stdout)

def test_cos_projection_transaction_smoke(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text("agents")
    payload = run_script("scripts/cos-projection-transaction", "--path", "AGENTS.md", cwd=tmp_path)
    assert payload["schema"] == "cos.efficiency.projection-transaction.v1"
    assert payload["receipts"][0]["exists"] is True
