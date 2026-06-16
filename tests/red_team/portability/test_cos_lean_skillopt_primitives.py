# SCOPE: os-only
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WRAPPERS = [
    "cos-lean-review", "cos-lean-audit", "cos-lean-debt",
    "cos-skill-opt-run", "cos-skill-edit-gate", "cos-skill-proposal-stage",
    "cos-skill-adopt", "cos-skill-rejected-buffer", "cos-skill-slow-update", "cos-skill-sleep",
]


def run_wrapper(name: str, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(ROOT / "scripts" / name), *args], cwd=cwd, text=True, capture_output=True, timeout=30, check=False)


def test_lean_skillopt_wrappers_exist_and_are_valid_bash() -> None:
    for name in WRAPPERS:
        artifact = ROOT / "scripts" / name
        assert artifact.exists(), name
        assert artifact.stat().st_mode & 0o111, name
        subprocess.run(["bash", "-n", str(artifact)], cwd=ROOT, check=True)


def test_lean_skillopt_wrappers_run_from_arbitrary_consumer_cwd(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    skill = project / "skills/demo/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: demo\n---\n\n# Demo\n", encoding="utf-8")
    src = project / "src/demo.py"
    src.parent.mkdir()
    src.write_text("class DemoManager:\n    pass\n# cos-lean: tiny impl; upgrade: second backend appears\n", encoding="utf-8")

    audit = run_wrapper("cos-lean-audit", outside, "--project-dir", str(project), "--json")
    assert audit.returncode == 0, audit.stderr + audit.stdout
    assert json.loads(audit.stdout)["finding_count"] >= 1

    debt = run_wrapper("cos-lean-debt", outside, "--project-dir", str(project), "--json")
    assert debt.returncode == 0, debt.stderr + debt.stdout
    assert json.loads(debt.stdout)["count"] == 1

    opt = run_wrapper("cos-skill-opt-run", outside, "--project-dir", str(project), "--run-id", "r", "--skill", str(skill), "--edit-add", "Validate before adopting.", "--baseline-score", "0.1", "--candidate-score", "0.2", "--json")
    assert opt.returncode == 0, opt.stderr + opt.stdout
    assert (project / ".cognitive-os/skill-opt/r/staging/proposed_SKILL.md").exists()

    adopt = run_wrapper("cos-skill-adopt", outside, "--project-dir", str(project), "--run-id", "r", "--apply", "--json")
    assert adopt.returncode == 0, adopt.stderr + adopt.stdout
    assert "Validate before adopting" in skill.read_text(encoding="utf-8")

    sleep = run_wrapper("cos-skill-sleep", outside, "--project-dir", str(project), "--run-id", "night", "--skill", str(skill), "--json")
    assert sleep.returncode == 0, sleep.stderr + sleep.stdout
    assert json.loads(sleep.stdout)["run_id"] == "night"
