# SCOPE: os-only
"""Portability proofs for the cos-loop-* agent loop primitives."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WRAPPERS = ["cos-loop-run", "cos-loop-report", "cos-loop-replay", "cos-loop-guard", "cos-loop-eval"]


def write_contract(tmp_path: Path) -> Path:
    path = tmp_path / "loop-contract.yaml"
    path.write_text(
        """
schemaVersion: cos.loop-contract.v1
id: portable-loop
trigger:
  type: manual
goal:
  statement: Prove wrapper portability.
stopConditions:
  maxIterations: 3
  maxRetries: 1
  maxNoProgressIterations: 2
  maxToolRepetitions: 3
  requireVerification: false
allowedTools:
  - name: shell
    mode: write
verificationCommands: []
memoryPolicy:
  write: observations
budgetPolicy:
  maxIterations: 3
  maxObservationBytes: 10000
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return path


def run_wrapper(name: str, tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(ROOT / "scripts" / name), *args],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )


def test_wrappers_exist_and_are_valid_bash() -> None:
    for name in WRAPPERS:
        artifact = ROOT / "scripts" / name
        assert artifact.exists(), name
        assert artifact.stat().st_mode & 0o111, name
        subprocess.run(["bash", "-n", str(artifact)], cwd=ROOT, check=True)


def test_loop_run_report_replay_guard_eval_from_arbitrary_cwd(tmp_path: Path) -> None:
    contract = write_contract(tmp_path)
    run = run_wrapper(
        "cos-loop-run",
        tmp_path,
        "--project-dir",
        str(tmp_path),
        "--contract",
        str(contract),
        "--observation",
        "portable observation",
        "--decision",
        "continue",
        "--tool",
        "shell",
        "--json",
    )
    assert run.returncode == 0, run.stderr or run.stdout
    assert json.loads(run.stdout)["loop_id"] == "portable-loop"

    report = run_wrapper("cos-loop-report", tmp_path, "--project-dir", str(tmp_path), "--loop-id", "portable-loop", "--json")
    assert report.returncode == 0, report.stderr or report.stdout
    assert json.loads(report.stdout)["iterations"] == 1

    replay = run_wrapper("cos-loop-replay", tmp_path, "--project-dir", str(tmp_path), "--loop-id", "portable-loop", "--json")
    assert replay.returncode == 0, replay.stderr or replay.stdout
    assert json.loads(replay.stdout)["events"][0]["decision"] == "continue"

    guard = run_wrapper("cos-loop-guard", tmp_path, "--project-dir", str(tmp_path), "--contract", str(contract), "--loop-id", "portable-loop", "--strict", "--json")
    assert guard.returncode == 0, guard.stderr or guard.stdout
    assert json.loads(guard.stdout)["status"] == "pass"

    ev = run_wrapper("cos-loop-eval", tmp_path, "--project-dir", str(tmp_path), "--loop-id", "portable-loop", "--json")
    assert ev.returncode == 0, ev.stderr or ev.stdout
    output = Path(json.loads(ev.stdout)["output"])
    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == "cos.loop-eval.v1"


def test_python_entrypoint_help_runs_from_arbitrary_cwd(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "cos_loop.py"), "--help"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert proc.returncode == 0
    assert "agent loop" in proc.stdout.lower()
