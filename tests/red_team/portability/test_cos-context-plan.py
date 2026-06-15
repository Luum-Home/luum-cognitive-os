from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

def run_script(script: str, *args: str, cwd: Path) -> dict:
    proc = subprocess.run([str(ROOT / script), *args, "--project-dir", str(cwd), "--json"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return json.loads(proc.stdout)

def test_cos_context_plan_smoke(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "money.py").write_text("def format_money(value): return value\n")
    payload = run_script("scripts/cos-context-plan", "--goal", "format money", cwd=tmp_path)
    assert payload["schema"] == "cos.efficiency.context-plan.v1"
    assert payload["selected_files"]
