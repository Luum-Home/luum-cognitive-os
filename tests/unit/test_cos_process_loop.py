from __future__ import annotations

import json
from pathlib import Path

from scripts import cos_process_loop


def write_contract(tmp_path: Path, *, command: str = "python3 -c 'raise SystemExit(0)'") -> Path:
    path = tmp_path / "process-contract.yaml"
    path.write_text(
        f"""
schemaVersion: cos.process-contract.v1
id: process-a
source:
  type: issue
  ref: ISSUE-1
goal:
  statement: Test the process loop.
selectedSkills:
  - plan-feature
  - dod-check
applyProgress:
  required: true
freshReview:
  required: true
  blockOnSeverities: [blocker, critical]
verifyReport:
  required: true
  timeoutSeconds: 30
  commands:
    - id: ok
      command: {json.dumps(command)}
      required: true
fixReviewLoop:
  requiredForBlockingFindings: true
finalVerdict:
  requireVerificationPass: true
  requireNoOpenBlockingFindings: true
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return path


def test_process_contract_records_progress_review_verify_and_verdict(tmp_path: Path) -> None:
    contract = write_contract(tmp_path)
    assert cos_process_loop.main(["process-loop", "init", "--project-dir", str(tmp_path), "--contract", str(contract), "--json"]) == 0
    assert cos_process_loop.main([
        "apply-progress", "--project-dir", str(tmp_path), "--process-id", "process-a", "--task-id", "T1", "--title", "implement", "--status", "done", "--evidence", "unit test", "--json",
    ]) == 0
    assert cos_process_loop.main([
        "fresh-review", "--project-dir", str(tmp_path), "--process-id", "process-a", "--finding-id", "R1", "--severity", "critical", "--status", "open", "--summary", "fresh review blocker", "--json",
    ]) == 0
    assert cos_process_loop.main(["verify-report", "--project-dir", str(tmp_path), "--process-id", "process-a", "--json"]) == 0
    assert cos_process_loop.main(["process-loop", "verdict", "--project-dir", str(tmp_path), "--process-id", "process-a", "--status", "passed", "--summary", "done", "--json"]) == 2

    assert cos_process_loop.main([
        "fresh-review", "--project-dir", str(tmp_path), "--process-id", "process-a", "--finding-id", "R1", "--severity", "critical", "--status", "resolved", "--summary", "fixed", "--json",
    ]) == 0
    assert cos_process_loop.main(["process-loop", "verdict", "--project-dir", str(tmp_path), "--process-id", "process-a", "--status", "passed", "--summary", "done", "--json"]) == 0

    state = json.loads((tmp_path / ".cognitive-os/process-loops/process-a/state.json").read_text(encoding="utf-8"))
    assert state["apply_progress"]["done"] == 1
    assert state["review_findings"]["blocking_open"] == 0
    assert state["verification"]["all_required_passed"] is True
    assert state["final_verdict"] == "passed"


def test_verify_failure_blocks_pass_verdict(tmp_path: Path) -> None:
    contract = write_contract(tmp_path, command="python3 -c 'raise SystemExit(1)'")
    assert cos_process_loop.main(["process-loop", "init", "--project-dir", str(tmp_path), "--contract", str(contract)]) == 0
    assert cos_process_loop.main(["verify-report", "--project-dir", str(tmp_path), "--process-id", "process-a", "--json"]) == 2
    assert cos_process_loop.main(["process-loop", "verdict", "--project-dir", str(tmp_path), "--process-id", "process-a", "--status", "passed", "--json"]) == 2
    verdict = json.loads((tmp_path / ".cognitive-os/process-loops/process-a/final-verdict.json").read_text(encoding="utf-8"))
    assert verdict["verdict"] == "blocked"
    assert "verification-not-passed" in verdict["blockers"]


def test_process_report_summarizes_contract_state(tmp_path: Path) -> None:
    contract = write_contract(tmp_path)
    cos_process_loop.main(["process-loop", "init", "--project-dir", str(tmp_path), "--contract", str(contract)])
    cos_process_loop.main(["apply-progress", "--project-dir", str(tmp_path), "--process-id", "process-a", "--task-id", "T1", "--title", "implement", "--status", "blocked"])
    paths = cos_process_loop.process_paths(tmp_path, "process-a")
    contract_data = cos_process_loop.normalize_contract(cos_process_loop.load_json(paths["contract"]))
    state = cos_process_loop.refresh_state(paths, contract_data, cos_process_loop.load_state(paths, contract_data, "process-a"))
    assert state["source"]["ref"] == "ISSUE-1"
    assert state["selected_skills"] == ["plan-feature", "dod-check"]
    assert state["apply_progress"]["blocked"] == 1
