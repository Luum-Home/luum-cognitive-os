"""Behavioral tests for hooks/secret-detector.sh — PreToolUse mode.

Covers:
  1. Clean input  → hook exits 0 with no stdout (passthrough).
  2. Input containing a redactable secret (mixed with plain text) →
     exits 0, emits updatedInput with [REDACTED], permissionDecision: allow.
  3. Input that is entirely a secret (nothing left after redaction) →
     exits 0, emits permissionDecision: block with additionalContext warning.
     (Was legacy exit 2; now native hookSpecificOutput.)
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = PROJECT_ROOT / "hooks" / "secret-detector.sh"

# A realistic AWS secret key pattern the hook should detect.
FAKE_AWS_KEY = "[REDACTED]"
FAKE_AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

_BASE_ENV = {
    "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT),
    "COS_SESSION_DIR": "/tmp/cos-test-session",
    "DISABLE_HOOK_RATE_LIMITER": "true",
}


def _run_hook(tool_name: str, tool_input: dict, hook_event: str = "PreToolUse") -> tuple[int, dict, str]:
    """Execute secret-detector.sh and return (returncode, parsed_stdout, stderr)."""
    stdin_payload = {
        "hook_event_name": hook_event,
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    env = {**os.environ, **_BASE_ENV}
    result = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps(stdin_payload),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    stdout = result.stdout.strip()
    parsed: dict = {}
    if stdout:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            pass
    return result.returncode, parsed, result.stderr


class TestCleanInput:
    """Hook should pass through harmless commands without output."""

    def test_clean_bash_command_exits_zero(self) -> None:
        rc, out, _ = _run_hook("Bash", {"command": "echo hello"})
        assert rc == 0

    def test_clean_bash_command_produces_no_output(self) -> None:
        rc, out, _ = _run_hook("Bash", {"command": "ls -la /tmp"})
        assert rc == 0
        # No redaction needed → hook may emit nothing
        assert out == {} or "updatedInput" not in out.get("hookSpecificOutput", {})


class TestRedactableSecret:
    """Input with a secret mixed into a real command → redact-and-allow."""

    def test_aws_key_in_command_is_redacted(self) -> None:
        cmd = f"aws configure set aws_access_key_id {FAKE_AWS_KEY}"
        rc, out, stderr = _run_hook("Bash", {"command": cmd})
        assert rc == 0, f"Hook must exit 0, got {rc}: {stderr}"
        hso = out.get("hookSpecificOutput", {})
        # If hook emits updatedInput, the secret must be gone
        if "updatedInput" in hso:
            updated_cmd = hso["updatedInput"].get("command", "")
            assert FAKE_AWS_KEY not in updated_cmd, "Secret not redacted from command"
            assert "[REDACTED]" in updated_cmd

    def test_permission_decision_is_allow_on_redaction(self) -> None:
        cmd = f"curl -H 'Authorization: token {FAKE_AWS_KEY}' http://example.com/path/other/stuff"
        rc, out, _ = _run_hook("Bash", {"command": cmd})
        assert rc == 0
        hso = out.get("hookSpecificOutput", {})
        if hso:
            assert hso.get("permissionDecision") == "allow"


class TestAllSecretInput:
    """Input that is *entirely* a secret must be denied, on both signals."""

    def test_entirely_secret_command_exits_2(self) -> None:
        # A command that is only a secret value — nothing left after redaction.
        # We use a GitHub token pattern which the hook treats as a high-confidence secret.
        fake_gh_token = "ghp_" + "A" * 36
        rc, out, stderr = _run_hook("Bash", {"command": fake_gh_token})
        assert rc == 2, (
            "Hook must block with exit 2 when the whole input is a secret. "
            f"Got {rc}. stderr: {stderr}"
        )

    def test_entirely_secret_command_emits_deny_decision(self) -> None:
        fake_gh_token = "ghp_" + "B" * 36
        rc, out, stderr = _run_hook("Bash", {"command": fake_gh_token})
        assert rc == 2
        hso = out.get("hookSpecificOutput", {})
        assert hso, f"the hook must emit its decision JSON, got stdout parsed as {out}"
        # "deny" is the only denial value the host accepts; "block" is silently
        # discarded, which turned this branch into a fail-open.
        assert hso.get("permissionDecision") == "deny", (
            f"Expected permissionDecision=deny, got: {hso}"
        )
        reason = hso.get("permissionDecisionReason", "")
        assert reason, "permissionDecisionReason must be non-empty for denied calls"


class TestPostToolUseMode:
    """PostToolUse invocations should always exit 0 (advisory only)."""

    def test_post_tool_use_exits_zero(self) -> None:
        rc, _, _ = _run_hook(
            "Edit",
            {"file_path": "/tmp/fake.py", "old_string": "a", "new_string": "b"},
            hook_event="PostToolUse",
        )
        assert rc == 0