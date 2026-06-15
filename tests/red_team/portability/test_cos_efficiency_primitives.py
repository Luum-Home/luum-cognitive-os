from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def test_cos_efficiency_primitives_shared_cli_smoke(tmp_path: Path):
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/cos_efficiency_primitives.py"), "status", "--project-dir", str(tmp_path), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["schema"] == "cos.efficiency.status.v1"
