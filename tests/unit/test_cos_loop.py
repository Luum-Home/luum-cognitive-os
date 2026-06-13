from __future__ import annotations

import json
from pathlib import Path

from scripts import cos_loop


def write_contract(tmp_path: Path, *, command: str = "python3 -c 'raise SystemExit(0)'", max_tool_repetitions: int = 2) -> Path:
    path = tmp_path / "loop-contract.yaml"
    path.write_text(
        f"""
schemaVersion: cos.loop-contract.v1
id: loop-a
trigger:
  type: manual
goal:
  statement: Test loop runtime.
stopConditions:
  maxIterations: 4
  maxRetries: 1
  maxNoProgressIterations: 2
  maxToolRepetitions: {max_tool_repetitions}
  requireVerification: true
allowedTools:
  - name: shell
    mode: write
verificationCommands:
  - id: ok
    command: {json.dumps(command)}
    required: true
memoryPolicy:
  write: observations
budgetPolicy:
  maxIterations: 4
  maxRetries: 1
  maxVerificationSeconds: 30
  maxObservationBytes: 10000
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return path


def test_run_persists_state_trace_and_report(tmp_path: Path) -> None:
    contract = write_contract(tmp_path)
    rc = cos_loop.main([
        "run",
        "--project-dir",
        str(tmp_path),
        "--contract",
        str(contract),
        "--observation",
        "implemented first step",
        "--decision",
        "continue",
        "--tool",
        "shell",
        "--json",
    ])
    assert rc == 0
    state_path = tmp_path / ".cognitive-os" / "loops" / "loop-a" / "state.json"
    trace_path = tmp_path / ".cognitive-os" / "loops" / "loop-a" / "trace.jsonl"
    assert state_path.exists()
    assert trace_path.exists()
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["iterations"] == 1
    report = cos_loop.report_for(tmp_path, "loop-a")
    assert report["tool_repetition"] == {"shell": 1}


def test_false_completion_requires_verification(tmp_path: Path) -> None:
    contract = write_contract(tmp_path, command="python3 -c 'raise SystemExit(1)'")
    rc = cos_loop.main([
        "run",
        "--project-dir",
        str(tmp_path),
        "--contract",
        str(contract),
        "--observation",
        "claiming done",
        "--status",
        "complete",
        "--run-verification",
        "--json",
    ])
    assert rc == 2
    state = json.loads((tmp_path / ".cognitive-os" / "loops" / "loop-a" / "state.json").read_text(encoding="utf-8"))
    assert state["status"] == "false_completion_risk"
    assert "false-completion-risk" in state["stop_reasons"]


def test_guard_detects_ping_pong_and_no_progress(tmp_path: Path) -> None:
    contract = write_contract(tmp_path, max_tool_repetitions=1)
    for idx in range(2):
        cos_loop.main([
            "run",
            "--project-dir",
            str(tmp_path),
            "--contract",
            str(contract),
            "--observation",
            "same blocker",
            "--tool",
            "shell",
            "--no-progress",
        ])
    rows = cos_loop.load_jsonl(tmp_path / ".cognitive-os" / "loops" / "loop-a" / "trace.jsonl")
    payload = cos_loop.guard_from_rows(cos_loop.load_contract(contract), rows)
    kinds = {issue["kind"] for issue in payload["issues"]}
    assert "ping-pong" in kinds
    assert "no-progress" in kinds


def test_eval_export_writes_regression_fixture(tmp_path: Path) -> None:
    contract = write_contract(tmp_path)
    cos_loop.main([
        "run",
        "--project-dir",
        str(tmp_path),
        "--contract",
        str(contract),
        "--observation",
        "capture decision",
        "--decision",
        "verify next",
    ])
    rc = cos_loop.main(["eval", "--project-dir", str(tmp_path), "--loop-id", "loop-a", "--json"])
    assert rc == 0
    eval_path = tmp_path / ".cognitive-os" / "evals" / "agent-loops" / "loop-a.json"
    payload = json.loads(eval_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "cos.loop-eval.v1"
    assert payload["cases"][0]["decision"] == "verify next"
