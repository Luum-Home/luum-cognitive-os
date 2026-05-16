"""Behavioral tests for hooks/session-wrapup-trigger.sh — ADR-030 Q1.

Tests verify the hook's closure-detection regex produces the correct
additionalContext output and stays silent on non-matching inputs.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = PROJECT_ROOT / "hooks" / "session-wrapup-trigger.sh"

pytestmark = [pytest.mark.behavior]


def run_trigger(prompt: str, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run the hook with the given prompt text as JSON stdin."""
    if not HOOK.exists():
        pytest.skip(f"Hook not found: {HOOK}")

    payload = json.dumps({"user_prompt": prompt})
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    return subprocess.run(
        ["bash", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=run_env,
        timeout=10,
    )


def parse_output(result: subprocess.CompletedProcess) -> dict | None:
    """Parse stdout as JSON if non-empty, else return None."""
    stdout = result.stdout.strip()
    if not stdout:
        return None
    return json.loads(stdout)


# ---------------------------------------------------------------------------
# Positive cases — closure intent detected
# ---------------------------------------------------------------------------


class TestPositiveTriggers:
    """Hook should emit additionalContext containing AUTO-TRIGGER and /session-wrapup."""

    def test_cerremos_sesion_triggers(self):
        result = run_trigger("close session")
        assert result.returncode == 0
        output = parse_output(result)
        assert output is not None, "Expected JSON output for closure prompt"
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "AUTO-TRIGGER" in ctx
        assert "/session-wrapup" in ctx

    def test_session_wrap_up_triggers(self):
        result = run_trigger("session wrap up please")
        assert result.returncode == 0
        output = parse_output(result)
        assert output is not None, "Expected JSON output for 'session wrap up'"
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "AUTO-TRIGGER" in ctx
        assert "/session-wrapup" in ctx

    def test_we_are_done_triggers(self):
        result = run_trigger("ok we are done for today")
        assert result.returncode == 0
        output = parse_output(result)
        assert output is not None, "Expected JSON output for 'we are done'"
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "AUTO-TRIGGER" in ctx
        assert "/session-wrapup" in ctx

    def test_close_session_triggers(self):
        result = run_trigger("I need to close the session now")
        assert result.returncode == 0
        output = parse_output(result)
        assert output is not None, "Expected JSON output for 'close session'"
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "AUTO-TRIGGER" in ctx

    def test_session_close_triggers(self):
        result = run_trigger("let's do session close")
        assert result.returncode == 0
        output = parse_output(result)
        assert output is not None, "Expected JSON output for 'session close'"
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "AUTO-TRIGGER" in ctx
        assert "/session-wrapup" in ctx

    def test_session_end_triggers(self):
        result = run_trigger("session end — please wrap up")
        assert result.returncode == 0
        output = parse_output(result)
        assert output is not None, "Expected JSON output for 'session end'"
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "AUTO-TRIGGER" in ctx


# ---------------------------------------------------------------------------
# Negative cases — no closure intent detected
# ---------------------------------------------------------------------------


class TestNegativeTriggers:
    """Hook should produce NO output (empty stdout) for non-closure prompts."""

    def test_generic_greeting_silent(self):
        result = run_trigger("hola, como iss?")
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"Unexpected output for generic greeting: {result.stdout!r}"
        )

    def test_false_positive_cerrar_archivo(self):
        """'cerremos este archivo' must NOT trigger — closes a file, not a session."""
        result = run_trigger("cerremos este archivo por ahora")
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"False-positive triggered for 'cerremos este archivo': {result.stdout!r}"
        )

    def test_unrelated_task_silent(self):
        result = run_trigger("implement the new endpoint for orders")
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_debugging_prompt_silent(self):
        result = run_trigger("debug the session init hook")
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_spanish_unrelated_silent(self):
        result = run_trigger("analyze the code and tell me what is failing")
        assert result.returncode == 0
        assert result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Edge / robustness cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Hook must handle malformed input gracefully — exit 0, no output."""

    def test_empty_json_object(self):
        """Empty JSON object → no output, exit 0."""
        if not HOOK.exists():
            pytest.skip(f"Hook not found: {HOOK}")
        result = subprocess.run(
            ["bash", str(HOOK)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_malformed_json(self):
        """Malformed JSON → exit 0, no output (must never crash)."""
        if not HOOK.exists():
            pytest.skip(f"Hook not found: {HOOK}")
        result = subprocess.run(
            ["bash", str(HOOK)],
            input="not-json-at-all{{{",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0

    def test_empty_stdin(self):
        """No stdin (empty string) → exit 0, no output."""
        if not HOOK.exists():
            pytest.skip(f"Hook not found: {HOOK}")
        result = subprocess.run(
            ["bash", str(HOOK)],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_output_is_valid_json_when_triggered(self):
        """When triggered, stdout must be valid JSON with the required keys."""
        result = run_trigger("close the session now")
        assert result.returncode == 0
        output = parse_output(result)
        assert output is not None
        assert "hookSpecificOutput" in output
        hook_out = output["hookSpecificOutput"]
        assert "hookEventName" in hook_out
        assert hook_out["hookEventName"] == "UserPromptSubmit"
        assert "additionalContext" in hook_out

    def test_prompt_key_alias_supported(self):
        """Hook should also accept 'prompt' key (not just 'user_prompt')."""
        if not HOOK.exists():
            pytest.skip(f"Hook not found: {HOOK}")
        payload = json.dumps({"prompt": "close the session"})
        result = subprocess.run(
            ["bash", str(HOOK)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        output = parse_output(result)
        assert output is not None, "Expected JSON output when using 'prompt' key"
        assert "AUTO-TRIGGER" in output["hookSpecificOutput"]["additionalContext"]
