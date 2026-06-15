from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def run_script(script: str, *args: str, cwd: Path) -> dict:
    proc = subprocess.run([str(ROOT / script), *args, "--project-dir", str(cwd), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return json.loads(proc.stdout)

def test_cos_skill_registry_refresh_smoke(tmp_path: Path):
    skill = tmp_path / "skills" / "demo" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: demo\ndescription: Demo.\n---\nBody not copied\n")
    payload = run_script("scripts/cos-skill-registry-refresh", cwd=tmp_path)
    assert payload["schema"] == "cos.efficiency.skill-registry.v1"
    assert Path(payload["registry_path"]).exists()
