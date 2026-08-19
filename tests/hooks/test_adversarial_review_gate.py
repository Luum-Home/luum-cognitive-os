# SCOPE: os-only
"""Behavioural test for the adversarial review gate.

Audited on 2026-08-19 as one of three registered hooks with no behaviour test.
It is a PostToolUse *warn* hook: it can never block (`exit 0` on every path), so
what has to be pinned is the warning itself and, just as important, its silence.

The telemetry that motivated these cases: 176 recorded invocations across the
live and archived hook-timing ledgers, every one of them `exit_code=0` with
`stdout_bytes=0`, and a log file of exactly 0 bytes — including the `pass`
branch, which writes unconditionally. A gate that has never written a single
line in 176 runs is not a quiet gate, it is a gate reading the wrong field:
Claude Code delivers the agent output under `.tool_response`, and the hook only
looked at `.tool_result` / `.output`.

Covered in both directions:
  * a review that closes with "looks good" and zero findings MUST warn;
  * a review with no severity marker at all MUST warn;
  * a review that carries a real finding MUST stay silent and log `pass`;
  * a non-review agent call and an empty output MUST leave no trace at all;
  * every one of those MUST exit 0 — promoting this gate to a blocker would
    change a PostToolUse warning into a workflow stop.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_REL = "hooks/adversarial-review-gate.sh"
HOOK_BASENAME = "adversarial-review-gate.sh"
LOG_REL = ".cognitive-os/metrics/adversarial-review-gate.jsonl"
WARNING_MARK = "WARNING [adversarial-review-gate]"

REVIEW_PROMPT = {"description": "code review of the dispatcher", "prompt": "review the change"}
LGTM_OUTPUT = "I reviewed the dispatcher change. Looks good, nothing to flag."
BLAND_OUTPUT = "I reviewed the dispatcher change and walked every branch of the code."
FINDING_OUTPUT = (
    "Review of the dispatcher change.\n"
    "S2 CONCERN: the retry counter is read before the queue lock is taken."
)
NON_REVIEW_OUTPUT = "Implemented the parser and added three unit tests for it."


def _hook_source() -> Path:
    """Where to copy the hook from — overridable only for the falsification run."""
    override = os.environ.get("COS_TEST_HOOK_SOURCE_DIR")
    base = Path(override) if override else REPO_ROOT
    return base / HOOK_REL


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    repo = (tmp_path / "repo").resolve()
    (repo / "hooks").mkdir(parents=True)
    shutil.copy(_hook_source(), repo / HOOK_REL)
    (repo / HOOK_REL).chmod(0o755)
    shutil.copytree(REPO_ROOT / "hooks" / "_lib", repo / "hooks" / "_lib")
    (repo / ".cognitive-os" / "metrics").mkdir(parents=True)
    return repo


def run_hook(
    repo: Path,
    output: str,
    tool: str = "Agent",
    output_field: str = "tool_result",
    tool_input: dict | None = None,
) -> subprocess.CompletedProcess:
    payload = {
        "tool_name": tool,
        "tool_input": REVIEW_PROMPT if tool_input is None else tool_input,
        output_field: output,
    }
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env.pop("DISABLE_HOOK_ADVERSARIAL_REVIEW_GATE", None)
    return subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo),
        timeout=60,
    )


def log_entries(repo: Path) -> list[dict]:
    path = repo / LOG_REL
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# --- must warn ---------------------------------------------------------------


def test_lgtm_review_is_warned_and_logged(repo: Path) -> None:
    result = run_hook(repo, LGTM_OUTPUT)

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK in result.stdout, f"gate stayed silent on an LGTM review: {result.stdout!r}"
    entries = log_entries(repo)
    assert entries and entries[-1]["severity"] == "prohibited_phrase_no_findings"
    assert entries[-1]["prohibited_phrase"] is True
    assert entries[-1]["has_finding"] is False


def test_review_without_any_severity_marker_is_warned(repo: Path) -> None:
    result = run_hook(repo, BLAND_OUTPUT)

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK in result.stdout
    entries = log_entries(repo)
    assert entries and entries[-1]["severity"] == "no_findings"
    assert entries[-1]["prohibited_phrase"] is False


def test_claude_code_payload_field_is_seen(repo: Path) -> None:
    """Claude Code delivers agent output under `.tool_response`.

    176 recorded invocations produced zero output because the gate only read
    `.tool_result`. If this case goes red again, the gate is blind in the very
    harness it is registered in.
    """
    result = run_hook(repo, LGTM_OUTPUT, output_field="tool_response")

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK in result.stdout, "gate is blind to the Claude Code payload field"
    assert log_entries(repo), "nothing was logged for a Claude Code shaped payload"


def test_log_is_one_json_object_per_line(repo: Path) -> None:
    """`safe_jsonl_append` takes ONE line; pretty JSON makes the ledger unreadable."""
    run_hook(repo, LGTM_OUTPUT)
    run_hook(repo, FINDING_OUTPUT)

    lines = (repo / LOG_REL).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2, f"two events wrote {len(lines)} lines: {lines!r}"
    for line in lines:
        json.loads(line)


def test_review_detected_from_the_prompt_alone(repo: Path) -> None:
    """The trigger reads tool_input too — an output that never says "review"."""
    result = run_hook(repo, "All good on my side.", tool_input={"description": "adversarial audit"})

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK in result.stdout


# --- must stay silent --------------------------------------------------------


def test_review_with_a_real_finding_is_not_warned(repo: Path) -> None:
    result = run_hook(repo, FINDING_OUTPUT)

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK not in result.stdout, f"gate warned on a review that had a finding: {result.stdout!r}"
    entries = log_entries(repo)
    assert entries and entries[-1]["severity"] == "pass"
    assert entries[-1]["has_finding"] is True


def test_non_review_agent_call_leaves_no_trace(repo: Path) -> None:
    result = run_hook(repo, NON_REVIEW_OUTPUT, tool_input={"description": "implement the parser"})

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK not in result.stdout
    assert log_entries(repo) == [], "a non-review agent call was logged"


def test_empty_output_leaves_no_trace(repo: Path) -> None:
    result = run_hook(repo, "")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""
    assert log_entries(repo) == []


def test_non_agent_tool_is_ignored(repo: Path) -> None:
    result = run_hook(repo, LGTM_OUTPUT, tool="Bash", tool_input={"command": "git status"})

    assert result.returncode == 0, result.stderr
    assert WARNING_MARK not in result.stdout
    assert log_entries(repo) == []


# --- must never block --------------------------------------------------------


@pytest.mark.parametrize(
    "output", [LGTM_OUTPUT, BLAND_OUTPUT, FINDING_OUTPUT, NON_REVIEW_OUTPUT, ""]
)
def test_gate_never_blocks(repo: Path, output: str) -> None:
    result = run_hook(repo, output)
    assert result.returncode == 0, (
        f"the gate blocked — it is a PostToolUse warning, not a stop: {result.stderr}"
    )


def test_killswitch_env_silences_the_gate(repo: Path) -> None:
    env = dict(os.environ)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    env["DISABLE_HOOK_ADVERSARIAL_REVIEW_GATE"] = "true"
    result = subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input=json.dumps({"tool_name": "Agent", "tool_input": REVIEW_PROMPT, "tool_result": LGTM_OUTPUT}),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo),
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert WARNING_MARK not in result.stdout
    assert log_entries(repo) == []
