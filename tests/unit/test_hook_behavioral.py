"""
Behavioral tests for hooks — verify logic, thresholds, and invariants.

Adopted from Hermes test patterns (invariants, cooldowns) and Pi (settings
overrides, threshold-driven behavior).  Tests here verify LOGIC:
  - classification thresholds (blast-radius LOW vs HIGH vs CRITICAL)
  - state transitions (auto-refine retry 1 → retry 2 → escalation)
  - capture invariants (error-learning writes on failure, silent on success)
  - blocking invariants (content-policy blocks prohibited terms)

NOT tested here: file-existence smoke tests (that lives in test_hook_basics.py).
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.behavior]


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = PROJECT_ROOT / "hooks"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(
    hook_name: str,
    stdin_json: "dict | None" = None,
    env: "dict | None" = None,
    timeout: int = 15,
) -> subprocess.CompletedProcess:
    """Low-level helper — runs a hook and returns CompletedProcess."""
    hook_path = HOOKS_DIR / hook_name
    if not hook_path.exists():
        pytest.skip(f"Hook {hook_name} not found at {hook_path}")

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    stdin_str = json.dumps(stdin_json) if stdin_json is not None else ""

    return subprocess.run(
        ["bash", str(hook_path)],
        input=stdin_str,
        capture_output=True,
        text=True,
        env=run_env,
        timeout=timeout,
    )


def _agent_input(prompt: str) -> dict:
    return {"tool_name": "Agent", "tool_input": {"prompt": prompt}}


def _bash_response(command: str, stdout: str, exit_code: int) -> dict:
    """Build a mock Bash PostToolUse payload matching error-pipeline.sh's expectations.

    error-pipeline.sh reads:
      .exit_code          (top-level, string)
      .tool_input.command
      .tool_response      (full response as a single string)
    """
    return {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_response": stdout,
        "exit_code": str(exit_code),
    }


def _agent_response(prompt: str, result: str) -> dict:
    """Build a mock Agent PostToolUse payload.

    The auto-refine logic lives inside error-pipeline.sh (merged hook).
    """
    return {
        "tool_name": "Agent",
        "tool_input": {"prompt": prompt},
        "tool_response": {"result": result},
    }


# ---------------------------------------------------------------------------
# Blast-radius: classification thresholds
# ---------------------------------------------------------------------------


class TestBlastRadiusThresholds:
    """Verify that blast-radius.sh classifies prompts into the correct tier.

    Invariants (from rules/blast-radius.md):
      - LOW (0-5 files): silent output
      - MEDIUM (6-20): silent output
      - HIGH (21-50): outputs "BLAST RADIUS: HIGH"
      - CRITICAL (50+ OR infra/security): outputs "BLAST RADIUS: CRITICAL"
      - Always exits 0 (advisory only)
    """

    HOOK = "blast-radius.sh"

    def test_single_file_produces_no_warning(self, isolated_cos_home):
        """A one-file fix should be LOW — no warning output."""
        env = {
            "CLAUDE_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_SESSION_ID": "",
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
        result = _run_hook(
            self.HOOK,
            stdin_json=_agent_input("Fix the null check in internal/users/handler.go"),
            env=env,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "HIGH" not in combined
        assert "CRITICAL" not in combined

    def test_many_directory_refs_produce_high_warning(self, isolated_cos_home):
        """Many distinct directory references → HIGH or CRITICAL blast radius.

        The hook thresholds (as of the "noise > signal" rewrite):
          HIGH: file_score > 40  (each dir reference = 5 file score)
          CRITICAL: (infra AND security) OR score > 100

        9 directory references → score = 45 → HIGH.
        """
        env = {
            "CLAUDE_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_SESSION_ID": "",
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
        # 9 directories × 5 = 45 → exceeds HIGH threshold (40)
        prompt = (
            "Refactor all Go files in internal/users/, internal/orders/, "
            "internal/payments/, internal/billing/, internal/notifications/, "
            "internal/reports/, internal/audit/, internal/events/, internal/search/ "
            "to use the new error wrapping pattern."
        )
        result = _run_hook(self.HOOK, stdin_json=_agent_input(prompt), env=env)
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert any(kw in combined for kw in ("HIGH", "CRITICAL")), (
            f"Expected HIGH or CRITICAL for 9-directory prompt, got: {combined[:400]}"
        )

    def test_jwt_keyword_yields_critical(self, isolated_cos_home):
        """Security + infrastructure combined keywords must produce CRITICAL.

        The hook was updated to reduce noise: security keywords ALONE are
        no longer enough for CRITICAL (they used to be).  The new rule is:
          CRITICAL = (infra_hit AND security_hit) OR file_score > 100

        Prompt with JWT (security) + Dockerfile/deployment (infra) across all
        services satisfies the CRITICAL condition.
        """
        env = {
            "CLAUDE_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_SESSION_ID": "",
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
        # Triggers both security (jwt, auth) and infra (docker, deployment) hits
        result = _run_hook(
            self.HOOK,
            stdin_json=_agent_input(
                "Add JWT authentication and update the Dockerfile deployment pipeline"
            ),
            env=env,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "CRITICAL" in combined, (
            f"Expected CRITICAL for security+infra combined prompt: {combined[:400]}"
        )

    def test_docker_keyword_yields_critical(self, isolated_cos_home):
        """Infrastructure + security combined keywords must produce CRITICAL.

        Infrastructure keywords alone (docker, deployment) now produce LOW
        (silent) because single-keyword triggers were too noisy.  To reach
        CRITICAL, the prompt must trigger both infra AND security hits.
        This test verifies the CRITICAL classification for that combination.
        """
        env = {
            "CLAUDE_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_SESSION_ID": "",
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
        # Triggers infra (docker-compose, deployment) AND security (credentials, TLS)
        result = _run_hook(
            self.HOOK,
            stdin_json=_agent_input(
                "Update the Dockerfile and docker-compose configuration with TLS certificates and credential secrets"
            ),
            env=env,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "CRITICAL" in combined, (
            f"Expected CRITICAL for infra+security combined prompt: {combined[:400]}"
        )

    def test_non_agent_tool_is_silent(self, isolated_cos_home):
        """Bash tool input must be skipped — blast-radius only applies to Agent."""
        env = {
            "CLAUDE_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_SESSION_ID": "",
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
        result = _run_hook(
            self.HOOK,
            stdin_json={"tool_name": "Bash", "tool_input": {"command": "echo hello"}},
            env=env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_critical_writes_metrics_entry(self, isolated_cos_home):
        """CRITICAL blast radius must write an entry to blast-radius.jsonl."""
        env = {
            "CLAUDE_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_SESSION_ID": "",
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
        _run_hook(
            self.HOOK,
            stdin_json=_agent_input("Add OAuth2 authentication across all services"),
            env=env,
        )
        # Metrics are written to the global metrics dir (no session ID set)
        metrics_dir = isolated_cos_home / ".cognitive-os" / "metrics"
        blast_log = metrics_dir / "blast-radius.jsonl"
        assert blast_log.exists(), "blast-radius.jsonl should have been written"
        entries = [json.loads(line) for line in blast_log.read_text().splitlines() if line.strip()]
        assert len(entries) >= 1
        assert entries[-1]["radius"] in ("HIGH", "CRITICAL")


# ---------------------------------------------------------------------------
# Error-learning: capture invariants
# ---------------------------------------------------------------------------


# TestErrorLearningCapture is intentionally removed — those invariants are now
# covered by TestErrorPipelinePhaseGating below, which uses the correct merged
# hook (error-pipeline.sh) and correct JSON payload format.


# ---------------------------------------------------------------------------
# Error-pipeline: phase-gating and repair dispatch invariants
# ---------------------------------------------------------------------------


class TestErrorPipelinePhaseGating:
    """Verify error-pipeline.sh phase gates and error-learning output.

    Note: auto-refine.sh was archived and merged into other components.
    These tests cover the behavioral invariants that remain in error-pipeline.sh:

    Invariants:
      - TEST_FAILURE: pytest command with non-zero exit → type == TEST_FAILURE
      - LINT_ERROR: golangci-lint command with non-zero exit → type == LINT_ERROR
      - BUILD_ERROR: go build failure → type == BUILD_ERROR
      - Always exits 0 (advisory / logging hook)
      - tool_name != Bash → hook skips immediately
    """

    HOOK = "error-pipeline.sh"

    def _env(self, isolated_cos_home: Path) -> dict:
        return {
            "CLAUDE_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_SESSION_ID": "",
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }

    def _log_path(self, isolated_cos_home: Path) -> Path:
        return isolated_cos_home / ".cognitive-os" / "metrics" / "error-learning.jsonl"

    def test_pytest_failure_written_as_test_failure(self, isolated_cos_home):
        """pytest command with exit code 1 → error-learning.jsonl entry with TEST_FAILURE."""
        env = self._env(isolated_cos_home)
        payload = _bash_response(
            command="pytest tests/ -v",
            stdout="FAILED tests/test_foo.py::test_bar - AssertionError: expected 1 got 2",
            exit_code=1,
        )
        result = _run_hook(self.HOOK, stdin_json=payload, env=env)
        assert result.returncode == 0

        log = self._log_path(isolated_cos_home)
        if log.exists() and log.stat().st_size > 0:
            entry = json.loads(log.read_text().splitlines()[0])
            assert entry["type"] == "TEST_FAILURE", (
                f"pytest failure must be TEST_FAILURE, got {entry['type']}"
            )

    def test_exit_zero_writes_nothing(self, isolated_cos_home):
        """exit_code=0 must not produce any error-learning entry (success path)."""
        env = self._env(isolated_cos_home)
        payload = _bash_response(
            command="pytest tests/ -v",
            stdout="42 passed in 1.23s",
            exit_code=0,
        )
        _run_hook(self.HOOK, stdin_json=payload, env=env)

        log = self._log_path(isolated_cos_home)
        if log.exists():
            assert log.read_text().strip() == "", (
                "error-learning.jsonl must be empty for a successful command"
            )

    def test_empty_command_skipped(self, isolated_cos_home):
        """Missing command field must cause the hook to exit early without writing."""
        env = self._env(isolated_cos_home)
        payload = {
            "tool_name": "Bash",
            "tool_input": {},
            "tool_response": "FAILED: something went wrong",
            "exit_code": "1",
        }
        result = _run_hook(self.HOOK, stdin_json=payload, env=env)
        assert result.returncode == 0

        log = self._log_path(isolated_cos_home)
        if log.exists():
            assert log.read_text().strip() == ""

    def test_non_bash_tool_skipped(self, isolated_cos_home):
        """Agent tool output must not be captured (hook is Bash-only)."""
        env = self._env(isolated_cos_home)
        payload = {
            "tool_name": "Agent",
            "tool_input": {"prompt": "Do something"},
            "tool_response": {"result": "FAILED: some test failed"},
            "exit_code": "1",
        }
        _run_hook(self.HOOK, stdin_json=payload, env=env)

        log = self._log_path(isolated_cos_home)
        if log.exists():
            assert log.read_text().strip() == "", (
                "Non-Bash tool output must not be written to error-learning.jsonl"
            )

    def test_golangci_lint_failure_classified(self, isolated_cos_home):
        """golangci-lint with non-zero exit → LINT_ERROR classification."""
        env = self._env(isolated_cos_home)
        payload = _bash_response(
            command="golangci-lint run ./...",
            stdout="handler.go:42:5: error: unused variable (deadcode)",
            exit_code=1,
        )
        _run_hook(self.HOOK, stdin_json=payload, env=env)

        log = self._log_path(isolated_cos_home)
        if log.exists() and log.stat().st_size > 0:
            entry = json.loads(log.read_text().splitlines()[0])
            assert entry["type"] == "LINT_ERROR", (
                f"golangci-lint failure must be LINT_ERROR, got {entry['type']}"
            )

    def test_go_test_failure_classified(self, isolated_cos_home):
        """go test failure → TEST_FAILURE classification."""
        env = self._env(isolated_cos_home)
        payload = _bash_response(
            command="go test ./internal/users/...",
            stdout="--- FAIL: TestGetUserByID (0.01s)\nFAIL\tgithub.com/org/project/internal/users",
            exit_code=1,
        )
        _run_hook(self.HOOK, stdin_json=payload, env=env)

        log = self._log_path(isolated_cos_home)
        if log.exists() and log.stat().st_size > 0:
            entry = json.loads(log.read_text().splitlines()[0])
            assert entry["type"] == "TEST_FAILURE", (
                f"go test failure must be TEST_FAILURE, got {entry['type']}"
            )


# ---------------------------------------------------------------------------
# Content-policy: blocking invariants
# ---------------------------------------------------------------------------


class TestContentPolicyBlocking:
    """Verify content-policy.sh blocks prohibited terms and allows clean files.

    Invariants:
      - File with prohibited term → exit 2 (BLOCK)
      - File without prohibited terms → exit 0
      - Missing policy file → exit 0 (graceful degradation)
      - Non-Edit/Write tool → exit 0 (tool filter)
    """

    HOOK = "content-policy.sh"

    def _make_policy(self, cos_dir: Path, term: str = "SECRET_BANNED_TERM") -> None:
        policy = cos_dir / "content-policy.yaml"
        policy.write_text(
            "prohibited_terms:\n"
            f'  - term: "{term}"\n'
            '    reason: "Test prohibited term"\n'
        )

    def _env(self, isolated_cos_home: Path) -> dict:
        return {
            "CLAUDE_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_PROJECT_DIR": str(isolated_cos_home),
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }

    def test_clean_file_passes(self, isolated_cos_home, tmp_path):
        """A file with no prohibited content must exit 0."""
        cos_dir = isolated_cos_home / ".cognitive-os"
        self._make_policy(cos_dir)

        test_file = tmp_path / "clean.py"
        test_file.write_text("def hello():\n    return 'world'\n")

        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(test_file)},
        }
        result = _run_hook(self.HOOK, stdin_json=payload, env=self._env(isolated_cos_home))
        assert result.returncode == 0

    def test_prohibited_term_blocks(self, isolated_cos_home, tmp_path):
        """A file containing the prohibited term must be blocked (exit 2)."""
        term = "CONTENT_POLICY_TEST_BLOCKER_XYZ"
        cos_dir = isolated_cos_home / ".cognitive-os"
        self._make_policy(cos_dir, term=term)

        test_file = tmp_path / "bad.py"
        test_file.write_text(f"# This file contains {term} which is forbidden\n")

        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": str(test_file)},
        }
        result = _run_hook(self.HOOK, stdin_json=payload, env=self._env(isolated_cos_home))
        assert result.returncode == 2, (
            f"Expected BLOCK (exit 2) for prohibited term, got {result.returncode}. "
            f"stderr: {result.stderr}"
        )

    def test_missing_policy_file_passes(self, isolated_cos_home, tmp_path):
        """When content-policy.yaml does not exist, the hook must pass silently."""
        # Make sure there is NO policy file
        policy = isolated_cos_home / ".cognitive-os" / "content-policy.yaml"
        policy.unlink(missing_ok=True)

        test_file = tmp_path / "anything.py"
        test_file.write_text("FORBIDDEN_EVERYTHING = True\n")

        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(test_file)},
        }
        result = _run_hook(self.HOOK, stdin_json=payload, env=self._env(isolated_cos_home))
        assert result.returncode == 0

    def test_non_edit_write_tool_passes(self, isolated_cos_home):
        """Bash tool must be skipped by the hook's tool filter."""
        cos_dir = isolated_cos_home / ".cognitive-os"
        self._make_policy(cos_dir)

        payload = {"tool_name": "Bash", "tool_input": {"command": "echo hello"}}
        result = _run_hook(self.HOOK, stdin_json=payload, env=self._env(isolated_cos_home))
        assert result.returncode == 0

    def test_blocked_term_written_to_metrics(self, isolated_cos_home, tmp_path):
        """A policy violation must be logged to content-policy.jsonl."""
        term = "METRICS_TEST_BANNED_TERM_ABC"
        cos_dir = isolated_cos_home / ".cognitive-os"
        self._make_policy(cos_dir, term=term)

        test_file = tmp_path / "violating.py"
        test_file.write_text(f"x = '{term}'\n")

        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(test_file)},
        }
        env = {
            **self._env(isolated_cos_home),
            "COGNITIVE_OS_METRICS_DIR": str(cos_dir / "metrics"),
        }
        _run_hook(self.HOOK, stdin_json=payload, env=env)

        metrics_log = cos_dir / "metrics" / "content-policy.jsonl"
        assert metrics_log.exists(), "content-policy.jsonl should have been written"
        entry = json.loads(metrics_log.read_text().splitlines()[0])
        assert entry["violations"] >= 1
