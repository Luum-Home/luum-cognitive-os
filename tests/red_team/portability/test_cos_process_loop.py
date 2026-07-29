# SCOPE: os-only
"""Portability proof for scripts/cos_process_loop.py.

The SDD process loop runs inside consumer projects, so init → verify → verdict
must operate against a target project's .cognitive-os from an arbitrary cwd,
writing nowhere near the OS repo. Falsification probe: a genuine PASS verdict
must freeze the approval receipt *under the consumer project*, not here.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LOOP = REPO_ROOT / "scripts" / "cos_process_loop.py"

_CONTRACT = """
schemaVersion: cos.process-contract.v1
id: proc
source:
  type: issue
  ref: I-1
goal:
  statement: portability probe
selectedSkills: [plan-feature]
applyProgress:
  required: false
freshReview:
  required: false
verifyReport:
  required: true
  commands:
    - id: ok
      command: python3 -c 'raise SystemExit(0)'
      required: true
finalVerdict:
  requireVerificationPass: true
  requireNoOpenBlockingFindings: false
""".strip() + "\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _loop(project: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(LOOP), *args, "--project-dir", str(project)],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_loop_artifact_exists() -> None:
    assert LOOP.exists()


def test_process_loop_runs_against_a_consumer_project_from_arbitrary_cwd(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    _git(project, "init", "-q")
    _git(project, "config", "user.email", "t@t.com")
    _git(project, "config", "user.name", "t")
    _git(project, "checkout", "-q", "-b", "feature/loop")
    (project / "src.py").write_text("v = 1\n", encoding="utf-8")
    _git(project, "add", "src.py")
    _git(project, "commit", "-q", "-m", "base")
    (project / "contract.yaml").write_text(_CONTRACT, encoding="utf-8")

    elsewhere = tmp_path / "somewhere-else"
    elsewhere.mkdir()

    assert _loop(project, elsewhere, "process-loop", "init", "--contract", str(project / "contract.yaml"), "--json").returncode == 0
    assert _loop(project, elsewhere, "verify-report", "--process-id", "proc", "--json").returncode == 0
    verdict = _loop(project, elsewhere, "process-loop", "verdict", "--process-id", "proc", "--status", "passed", "--json")
    assert verdict.returncode == 0, verdict.stderr

    # State and the frozen approval landed under the CONSUMER project, not the OS repo.
    state = project / ".cognitive-os/process-loops/proc/state.json"
    assert state.is_file()
    assert json.loads(state.read_text())["final_verdict"] == "passed"
    approval = project / ".cognitive-os/receipts/review-approvals/feature_loop.json"
    assert approval.is_file(), "PASS verdict must freeze the approval under the target project"
