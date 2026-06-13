# SCOPE: os-only
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WRAPPERS = ["cos-process-loop", "cos-apply-progress", "cos-fresh-review", "cos-verify-report", "cos-skill-selection-report"]


def write_contract(tmp_path: Path) -> Path:
    path = tmp_path / "process-contract.yaml"
    path.write_text(
        """
schemaVersion: cos.process-contract.v1
id: portable-process
source:
  type: spec
  ref: specs/demo.md
  status: approved
  requiredStatus: approved
goal:
  statement: Prove process-loop portability.
selectedSkills: [plan-feature]
skillSelection:
  required: true
verifyReport:
  required: true
  commands:
    - id: ok
      command: python3 -c 'raise SystemExit(0)'
      required: true
finalVerdict:
  requireVerificationPass: true
  requireNoOpenBlockingFindings: true
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return path


def run_wrapper(name: str, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(ROOT / "scripts" / name), *args], cwd=cwd, text=True, capture_output=True, timeout=30, check=False)


def test_wrappers_exist_and_are_valid_bash() -> None:
    for name in WRAPPERS:
        artifact = ROOT / "scripts" / name
        assert artifact.exists(), name
        assert artifact.stat().st_mode & 0o111, name
        subprocess.run(["bash", "-n", str(artifact)], cwd=ROOT, check=True)


def test_process_wrappers_run_from_arbitrary_consumer_cwd(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    contract = write_contract(project)
    outside = tmp_path / "outside"
    outside.mkdir()

    init = run_wrapper("cos-process-loop", outside, "init", "--project-dir", str(project), "--contract", str(contract), "--json")
    assert init.returncode == 0, init.stderr + init.stdout
    assert json.loads(init.stdout)["process_id"] == "portable-process"

    (project / "package.json").write_text('{"dependencies":{"react":"latest"}}\n', encoding="utf-8")
    selection = run_wrapper("cos-skill-selection-report", outside, "--project-dir", str(project), "--process-id", "portable-process", "--changed-file", "src/App.tsx", "--json")
    assert selection.returncode == 0, selection.stderr + selection.stdout
    selection_payload = json.loads(selection.stdout)
    assert "frontend" in selection_payload["stack_signals"]
    assert any(item["name"] == "frontend-dod" for item in selection_payload["recommended_skills"])

    apply = run_wrapper("cos-apply-progress", outside, "--project-dir", str(project), "--process-id", "portable-process", "--task-id", "T1", "--title", "implement", "--status", "done", "--json")
    assert apply.returncode == 0, apply.stderr + apply.stdout

    review = run_wrapper("cos-fresh-review", outside, "--project-dir", str(project), "--process-id", "portable-process", "--severity", "major", "--command", "python3 -c 'raise SystemExit(0)'", "--json")
    assert review.returncode == 0, review.stderr + review.stdout

    verify = run_wrapper("cos-verify-report", outside, "--project-dir", str(project), "--process-id", "portable-process", "--json")
    assert verify.returncode == 0, verify.stderr + verify.stdout
    assert json.loads(verify.stdout)["all_required_passed"] is True

    verdict = run_wrapper("cos-process-loop", outside, "verdict", "--project-dir", str(project), "--process-id", "portable-process", "--status", "passed", "--summary", "done", "--json")
    assert verdict.returncode == 0, verdict.stderr + verdict.stdout
    assert json.loads(verdict.stdout)["verdict"] == "passed"

    report = run_wrapper("cos-process-loop", outside, "report", "--project-dir", str(project), "--process-id", "portable-process", "--json")
    assert report.returncode == 0, report.stderr + report.stdout
    payload = json.loads(report.stdout)
    assert payload["source"]["ref"] == "specs/demo.md"
    assert payload["apply_progress"]["done"] == 1
    assert payload["verification"]["all_required_passed"] is True
    assert payload["next_recommended"]["action"] == "done"
