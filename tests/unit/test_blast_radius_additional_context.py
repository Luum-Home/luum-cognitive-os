"""
Behavioral tests for blast-radius.sh additionalContext migration (ADR-023).

Previously blast-radius wrote human-readable warnings to stdout/stderr.
After ADR-023 it must emit a structured hookSpecificOutput payload with
permissionDecision=allow + additionalContext, so Claude Code surfaces the
warning to the orchestrator without treating it as an exception.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.behavior]

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = PROJECT_ROOT / "hooks" / "blast-radius.sh"


def _run(stdin_payload: dict, env_extra: dict | None = None, timeout: int = 10):
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not found at {HOOK_PATH}")
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = env.get("CLAUDE_PROJECT_DIR", str(PROJECT_ROOT))
    # Avoid heartbeat side effects + force the global metrics path so the test
    # doesn't have to plumb a session ID through.
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    env["COGNITIVE_OS_SESSION_ID"] = ""
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps(stdin_payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _agent_payload(prompt: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"prompt": prompt},
    }


def _last_json_line(stdout: str) -> dict:
    """blast-radius emits a single JSON object on stdout. Tolerate trailing
    blank lines from echo/printf."""
    line = next(
        (ln for ln in reversed(stdout.splitlines()) if ln.strip().startswith("{")),
        "",
    )
    assert line, f"Expected a JSON line on stdout, got {stdout!r}"
    return json.loads(line)


# ---------------------------------------------------------------------------
# additionalContext behavior
# ---------------------------------------------------------------------------


class TestBlastRadiusAdditionalContext:
    def test_warning_in_additional_context(self, tmp_path: Path) -> None:
        """A high-impact prompt must produce a hookSpecificOutput with the
        BLAST RADIUS warning in additionalContext (NOT in plain stdout
        prose, NOT in stderr)."""
        prompt = (
            "Refactor every endpoint in internal/users/, internal/orders/, "
            "internal/payments/, internal/billing/, internal/notifications/ "
            "to use the new error wrapping pattern."
        )
        result = _run(
            _agent_payload(prompt),
            env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)},
        )
        assert result.returncode == 0
        data = _last_json_line(result.stdout)
        hso = data["hookSpecificOutput"]
        assert hso["permissionDecision"] == "allow"
        ctx = hso.get("additionalContext") or data.get("additionalContext", "")
        assert "BLAST RADIUS" in ctx
        assert any(level in ctx for level in ("HIGH", "CRITICAL"))

    def test_security_keyword_emits_critical_context(self, tmp_path: Path) -> None:
        """Security keywords combined with broad scope (across all services) must
        trigger at least a HIGH or CRITICAL blast radius warning.

        Note: the hook was updated (comment: "Noise > signal") so security
        keywords ALONE no longer trigger CRITICAL — a high file-score is also
        required.  A prompt with "across all services" (+50 score) combined with
        security keywords satisfies the new HIGH threshold (score > 40).
        CRITICAL requires (infra AND security) OR score > 100.
        """
        result = _run(
            _agent_payload("Add OAuth2 authentication across all services"),
            env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)},
        )
        assert result.returncode == 0
        data = _last_json_line(result.stdout)
        ctx = data["hookSpecificOutput"].get("additionalContext", "") or data.get(
            "additionalContext", ""
        )
        # Accept HIGH or CRITICAL — both are valid warnings for this prompt
        assert any(level in ctx for level in ("HIGH", "CRITICAL")), (
            f"Expected HIGH or CRITICAL blast radius for security+scope prompt, got: {ctx!r}"
        )
        assert "BLAST RADIUS" in ctx

    def test_still_allows_execution(self, tmp_path: Path) -> None:
        """blast-radius is advisory only. Even on CRITICAL it must:
        - exit 0
        - emit permissionDecision=allow (never 'deny' or 'ask')."""
        result = _run(
            _agent_payload("Migrate all services to the new docker-compose stack"),
            env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)},
        )
        assert result.returncode == 0, (
            "blast-radius must exit 0 (advisory), "
            f"got {result.returncode} stderr={result.stderr!r}"
        )
        if result.stdout.strip():
            data = _last_json_line(result.stdout)
            assert data["hookSpecificOutput"]["permissionDecision"] == "allow"

    def test_low_radius_is_silent(self, tmp_path: Path) -> None:
        """A trivial single-file fix must NOT emit any hookSpecificOutput —
        we only want to surface context when there is something useful to
        say. Emitting an empty additionalContext is noise."""
        result = _run(
            _agent_payload("Fix the null check in internal/users/handler.go"),
            env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)},
        )
        assert result.returncode == 0
        # Stdout must not contain a hookSpecificOutput envelope.
        assert "hookSpecificOutput" not in result.stdout
        assert "BLAST RADIUS" not in result.stdout
        assert "BLAST RADIUS" not in result.stderr

    def test_non_agent_tool_is_silent(self, tmp_path: Path) -> None:
        """blast-radius only inspects Agent dispatches. A Bash payload must
        be a no-op."""
        result = _run(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "echo hello"},
            },
            env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)},
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""
