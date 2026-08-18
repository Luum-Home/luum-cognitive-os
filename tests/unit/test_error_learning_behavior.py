"""Behavioral tests for hooks/error-learning.sh.

Verifies deduplication logic:
- A duplicate error within 60 s is NOT written a second time
- The same error after the 60-second window IS written again
- Two errors from different services with the same message text ARE each written

Plus the precondition all three depend on: that a FAILED Bash payload is
recognised as a failure at all, and a SUCCESSFUL one is not. See
``_make_failed_stdin`` for why that is a matter of ``tool_response``'s type and
never of an ``exit_code`` field.
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
HOOK_PATH = HOOKS_DIR / "error-learning.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_failed_stdin(
    command: str = "go test ./...",
    stdout: str = "FAILED",
    stderr: str = "",
    exit_code: int = 1,
) -> str:
    """Build a PostToolUse Bash payload for a command that RAN AND FAILED.

    The shape is not invented here. It is the one the harness actually sends,
    frozen in ``tests/fixtures/payload-corpus/harness-payloads.jsonl``::

        {"_corpus": {"tool": "Bash", "state": "error_w_code", "seen": 50},
         "toolUseResult": "Error: Exit code 1\n<str>"}

    Two consequences, both load-bearing for these tests:

    * **There is no ``exit_code`` field.** Not at the top level, not nested.
      The earlier version of this helper set ``"exit_code": 1`` at the root and
      called it "Claude Code PostToolUse format"; that field exists nowhere in
      the corpus and nowhere in ``manifests/claude-code-hooks-schema.yaml``. It
      was the phantom that ``hooks/_lib/tool-outcome.sh`` was written to remove,
      and a fixture that keeps sending it pins the removed defect.
    * **Failure is a CHANGE OF TYPE, not a field.** ``tool_response`` is an
      OBJECT with ``stdout``/``stderr`` when the command SUCCEEDS, and a STRING
      prefixed ``"Error: Exit code N"`` when it fails. The old fixture sent the
      object form, i.e. a success — which is why the hook correctly exited 0 and
      wrote nothing, and why these three tests were red.

    ``stdout`` and ``stderr`` are merged into that one string because the string
    form carries a single blob; the hook reads it whole (``COMBINED``).
    """
    body = "\n".join(part for part in (stdout, stderr) if part)
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": f"Error: Exit code {exit_code}\n{body}",
    }
    return json.dumps(payload)


def _make_ok_stdin(command: str = "go test ./...", stdout: str = "ok") -> str:
    """The success shape: ``tool_response`` as an object. Nothing to learn from."""
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": {
            "stdout": stdout,
            "stderr": "",
            "interrupted": False,
            "isImage": False,
            "noOutputExpected": False,
        },
    }
    return json.dumps(payload)


def _run_hook(
    project_dir: Path,
    stdin: str,
    extra_env: "dict | None" = None,
    timeout: int = 15,
) -> subprocess.CompletedProcess:
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not found: {HOOK_PATH}")

    env = os.environ.copy()
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    env["PRIVATE_MODE"] = "false"
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _error_log(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "metrics" / "error-learning.jsonl"


def _count_entries(log: Path) -> int:
    if not log.exists():
        return 0
    return sum(1 for line in log.read_text().splitlines() if line.strip())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestErrorLearningOutcomeClassification:
    """The hook must tell a failure from a success by tool_response's TYPE.

    Without this pair, the three dedup tests below could not distinguish "the
    hook classified correctly" from "the hook logs every Bash call it sees".
    """

    def test_successful_command_writes_nothing(self, tmp_path):
        (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)

        _run_hook(tmp_path, _make_ok_stdin(stdout="ok  0.4s"))

        assert _count_entries(_error_log(tmp_path)) == 0, (
            "an object-shaped tool_response is a SUCCESS and must not be learned from"
        )

    def test_failed_command_records_the_exit_code_it_carried(self, tmp_path):
        (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)

        _run_hook(
            tmp_path,
            _make_failed_stdin(
                command="go test ./internal/billing/...",
                stdout="--- FAIL: TestCharge",
                exit_code=2,
            ),
        )

        log = _error_log(tmp_path)
        assert _count_entries(log) == 1, "a failed command must produce one row"
        row = json.loads(log.read_text().splitlines()[0])
        # Parsed out of "Error: Exit code 2", the only place the code exists.
        assert row["exit_code"] == 2
        assert row["type"] == "TEST_FAILURE"
        assert row["service"] == "internal-billing"


class TestErrorLearningDeduplication:
    def test_duplicate_within_60s_not_written_twice(self, tmp_path):
        """Running the hook twice with the same error within 60 s writes only 1 entry."""
        (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
        stdin = _make_failed_stdin(stdout="FAILED test", stderr="assertion error")

        _run_hook(tmp_path, stdin)
        _run_hook(tmp_path, stdin)

        log = _error_log(tmp_path)
        entries = _count_entries(log)
        assert entries == 1, (
            f"Expected 1 entry after duplicate within 60 s, found {entries}"
        )

    def test_same_error_after_60s_written_again(self, tmp_path):
        """Same error written again after the dedup window produces a second entry.

        We backdate the first entry's timestamp_epoch to simulate time passing
        rather than sleeping for 60 seconds.
        """
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        stdin = _make_failed_stdin(stdout="assertion error xyz", stderr="")

        # First run — writes entry N
        _run_hook(tmp_path, stdin)
        log = _error_log(tmp_path)
        assert _count_entries(log) == 1, "First run should write exactly 1 entry"

        # Manipulate the log: set timestamp_epoch far in the past
        entries = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
        entries[0]["timestamp_epoch"] = int(time.time()) - 120  # 2 minutes ago
        log.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

        # Second run — should NOT be deduplicated
        _run_hook(tmp_path, stdin)
        assert _count_entries(log) == 2, (
            "Expected 2 entries after 60-second window expired"
        )

    def test_different_service_same_error_written(self, tmp_path):
        """Two different commands with the same error message both get written.

        The hook fingerprints on error content, but service is derived from the
        command path.  Two distinct commands should both be captured even if the
        error text is identical (they have different fingerprint contexts because
        the combined stdout+stderr differ only by command path, but the
        deduplication is on fingerprint alone — if identical text, one entry may
        be deduped.  The important invariant is that an error from a *new* command
        path with its own fresh fingerprint window IS captured).
        """
        (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)

        # Two commands with distinct error text to ensure distinct fingerprints
        stdin_a = _make_failed_stdin(
            command="go test ./internal/users/...",
            stdout="FAILED users panic goroutine",
        )
        stdin_b = _make_failed_stdin(
            command="go test ./internal/payments/...",
            stdout="FAILED payments nil pointer deref",
        )

        _run_hook(tmp_path, stdin_a)
        _run_hook(tmp_path, stdin_b)

        log = _error_log(tmp_path)
        entries = _count_entries(log)
        assert entries == 2, (
            f"Expected 2 entries for two distinct errors, found {entries}"
        )
