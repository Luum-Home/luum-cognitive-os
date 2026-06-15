from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def run_script(script: str, *args: str, cwd: Path) -> dict:
    proc = subprocess.run([str(ROOT / script), *args, "--project-dir", str(cwd), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return json.loads(proc.stdout)

def test_cos_adapter_capabilities_smoke(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text("agents")
    payload = run_script("scripts/cos-adapter-capabilities", cwd=tmp_path)
    assert payload["schema"] == "cos.efficiency.adapter-capabilities.v1"
    assert any(a["adapter"] == "generic" for a in payload["adapters"])
