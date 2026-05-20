"""Shell-level tests for ADR-038 Trust Report hook wiring."""

import json


def _agent_result(output: str) -> dict:
    return {
        "tool_name": "Agent",
        "tool_input": {"prompt": "Implement a small change"},
        "tool_result": output,
    }


def test_trust_score_validator_logs_structured_report(run_hook, mock_project):
    output = """Implemented change.
TRUST_REPORT: SCORE=82 STATUS=MEDIUM EVIDENCE=2 UNCERTAINTIES=1
---
WHAT I VERIFIED:
  - Ran unit tests
  - Checked hook syntax
UNSURE ABOUT:
  - Integration coverage not run
HUMAN SHOULD CHECK:
  - Review diff
"""

    result = run_hook(
        "trust-score-validator.sh",
        stdin_json=_agent_result(output),
        env=mock_project["env"],
    )

    assert result.returncode == 0, result.stdout + result.stderr
    log = mock_project["cos_dir"] / "metrics" / "trust-scores.jsonl"
    entries = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    assert entries[-1]["score"] == 82
    assert entries[-1]["status"] == "MEDIUM"
    assert entries[-1]["format"] == "structured"
    assert entries[-1]["uncertainty_count"] == 1


def test_trust_score_validator_blocks_malformed_structured_report(run_hook, mock_project):
    output = """Implemented change.
TRUST_REPORT: SCORE=95 STATUS=LOW EVIDENCE=2 UNCERTAINTIES=1
---
WHAT I VERIFIED:
  - Ran unit tests
UNSURE ABOUT:
  - Integration coverage not run
"""

    result = run_hook(
        "trust-score-validator.sh",
        stdin_json=_agent_result(output),
        env=mock_project["env"],
    )

    assert result.returncode == 2
    combined = result.stdout + result.stderr
    assert "malformed Trust Report" in combined
    assert "BAND_MISMATCH" in combined


def test_trust_score_validator_accepts_legacy_with_warning(run_hook, mock_project):
    output = """Implemented change.
TRUST REPORT:
  Score: 65/100
  EVIDENCE PROVIDED:
    [check] Read the code
  WHAT I'M UNSURE ABOUT:
    - Tests were not run
"""

    result = run_hook(
        "trust-score-validator.sh",
        stdin_json=_agent_result(output),
        env=mock_project["env"],
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Legacy Trust Report format accepted" in result.stdout
    log = mock_project["cos_dir"] / "metrics" / "trust-scores.jsonl"
    entries = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    assert entries[-1]["score"] == 65
    assert entries[-1]["format"] == "legacy"
