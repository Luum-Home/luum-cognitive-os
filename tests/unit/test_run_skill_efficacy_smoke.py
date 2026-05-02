from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "run_skill_efficacy_smoke.py"


def test_run_skill_efficacy_smoke_generates_report(tmp_path: Path) -> None:
    tasks = tmp_path / "tasks.json"
    archive = tmp_path / "archive.jsonl"
    report = tmp_path / "report.md"
    tasks.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "id": "s1",
                        "skill_name": "s",
                        "task": "fix",
                        "baseline": {"success": False, "cost_usd": 0.0},
                        "with_skill": {"success": True, "cost_usd": 0.0},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        ["python3", str(SCRIPT), "--tasks", str(tasks), "--archive", str(archive), "--report", str(report), "--reset"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "high-value" in report.read_text(encoding="utf-8")
