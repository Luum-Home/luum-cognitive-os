from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TASK = REPO / "benchmarks" / "improvement" / "skip-classification-mini"


def run_cmd(args: list[str], cwd: Path) -> dict:
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


def test_cos_improve_scripts_run_feedback_and_context(tmp_path: Path) -> None:
    run = run_cmd(
        [
            str(REPO / "scripts" / "cos-improve-run"),
            "--project-dir",
            str(tmp_path),
            "--task-dir",
            str(TASK),
            "--run-id",
            "behavior-smoke",
            "--max-gen",
            "1",
            "--json",
        ],
        REPO,
    )
    assert run["run_id"] == "behavior-smoke"
    assert run["generations"][0]["passed"] is True

    feedback = run_cmd(
        [str(REPO / "scripts" / "cos-improve-feedback"), "--project-dir", str(tmp_path), "--run-id", "behavior-smoke", "--json"],
        REPO,
    )
    assert feedback["gate"]["auto_apply"] is False

    context = run_cmd(
        [str(REPO / "scripts" / "cos-improve-context"), "--project-dir", str(tmp_path), "--run-id", "behavior-smoke", "--json"],
        REPO,
    )
    assert context["context_path"].endswith(".cognitive-os/improvement-runs/behavior-smoke/context.md")
