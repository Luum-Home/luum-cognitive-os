"""
Behavioral tests for secret-detector.sh PreToolUse mode (ADR-023).

The hook must REDACT detected secrets via hookSpecificOutput.updatedInput
instead of blocking the call (exit 2). Blocking is reserved as a fallback
when the redaction would leave the command meaningless.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.behavior]

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = PROJECT_ROOT / "hooks" / "secret-detector.sh"


def _run(stdin_payload: dict, env_extra: dict | None = None, timeout: int = 10):
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not found at {HOOK_PATH}")
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = env.get("CLAUDE_PROJECT_DIR", str(PROJECT_ROOT))
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


def _pre_payload(tool: str, tool_input: dict) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
    }


# ---------------------------------------------------------------------------
# Redaction behavior
# ---------------------------------------------------------------------------


class TestSecretDetectorUpdatedInput:
    def test_redacts_aws_key_in_command(self, tmp_path: Path) -> None:
        """An AWS access key embedded in a Bash command must be redacted in
        place; the call must still be allowed."""
        payload = _pre_payload(
            "Bash",
            {"command": "aws s3 ls --access-key AKIAIOSFODNN7EXAMPLE --region us-east-1"},
        )
        result = _run(payload, env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert result.returncode == 0, f"Hook must not block, got {result.returncode}: {result.stderr}"

        out = result.stdout.strip()
        assert out, "Hook must emit JSON when secrets are found"
        data = json.loads(out)

        hso = data["hookSpecificOutput"]
        assert hso["hookEventName"] == "PreToolUse"
        assert hso["permissionDecision"] == "allow"
        updated_cmd = hso["updatedInput"]["command"]
        assert "AKIAIOSFODNN7EXAMPLE" not in updated_cmd
        assert "[REDACTED]" in updated_cmd
        # The non-secret structure of the command must survive redaction.
        assert "aws s3 ls" in updated_cmd
        assert "us-east-1" in updated_cmd

        ctx = data.get("additionalContext", "")
        assert "redact" in ctx.lower() or "Redact" in ctx

    def test_redacts_github_token(self, tmp_path: Path) -> None:
        """GitHub PATs (ghp_...) must be redacted in tool_input.command."""
        token = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"
        payload = _pre_payload(
            "Bash",
            {"command": f"curl -H 'Authorization: token {token}' https://api.github.com/user"},
        )
        result = _run(payload, env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert result.returncode == 0
        data = json.loads(result.stdout.strip())
        updated_cmd = data["hookSpecificOutput"]["updatedInput"]["command"]
        assert token not in updated_cmd
        assert "[REDACTED]" in updated_cmd
        # Surrounding command structure is preserved.
        assert "Authorization" in updated_cmd
        assert "api.github.com" in updated_cmd

    def test_redacts_secret_in_write_content(self, tmp_path: Path) -> None:
        """An Edit/Write that wants to persist a secret to disk must be
        redacted in tool_input.content (so [REDACTED] lands in the file
        instead of the literal credential)."""
        payload = _pre_payload(
            "Write",
            {
                "file_path": str(tmp_path / "config.py"),
                "content": "AWS_SECRET = 'AKIAIOSFODNN7EXAMPLE'\nDEBUG = True\n",
            },
        )
        result = _run(payload, env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert result.returncode == 0
        data = json.loads(result.stdout.strip())
        updated_content = data["hookSpecificOutput"]["updatedInput"]["content"]
        assert "AKIAIOSFODNN7EXAMPLE" not in updated_content
        assert "[REDACTED]" in updated_content
        assert "DEBUG = True" in updated_content

    def test_allows_after_redaction(self, tmp_path: Path) -> None:
        """The hook MUST exit 0 after redaction (ADR-023: mutate, do not
        block). Returning 2 here would defeat the whole point of the
        migration — the user wants the command to proceed in its safe form."""
        payload = _pre_payload(
            "Bash",
            {"command": "echo AKIAIOSFODNN7EXAMPLE && echo done"},
        )
        result = _run(payload, env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert result.returncode == 0, (
            "Hook must allow execution after redaction, "
            f"got {result.returncode} with stderr={result.stderr!r}"
        )
        # And it must not be exit 2 specifically (the legacy block code).
        assert result.returncode != 2

    def test_emits_hook_specific_output_json(self, tmp_path: Path) -> None:
        """The stdout payload must conform to the Claude Code
        hookSpecificOutput contract — a single JSON object with the
        expected keys, parseable by jq/json.loads."""
        payload = _pre_payload(
            "Bash",
            {"command": "deploy --token ghp_abcdefghijklmnopqrstuvwxyz0123456789"},
        )
        result = _run(payload, env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert result.returncode == 0
        out = result.stdout.strip()
        assert out, "stdout must contain the hookSpecificOutput JSON"

        data = json.loads(out)
        assert "hookSpecificOutput" in data
        hso = data["hookSpecificOutput"]
        assert hso.get("hookEventName") == "PreToolUse"
        assert hso.get("permissionDecision") == "allow"
        assert "updatedInput" in hso
        assert isinstance(hso["updatedInput"], dict)
        # additionalContext is required so the orchestrator can surface
        # WHICH secrets were redacted.
        assert "additionalContext" in data
        assert isinstance(data["additionalContext"], str)
        assert len(data["additionalContext"]) > 0


    def test_redacts_anthropic_key(self, tmp_path: Path) -> None:
        """Anthropic API keys must be redacted before Bash execution."""
        token = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123456789_FAKEKEYFORTEST0"
        payload = _pre_payload("Bash", {"command": f"echo {token} && echo done"})
        result = _run(payload, env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert result.returncode == 0
        data = json.loads(result.stdout.strip())
        updated_cmd = data["hookSpecificOutput"]["updatedInput"]["command"]
        assert token not in updated_cmd
        assert "[REDACTED]" in updated_cmd
        assert "echo done" in updated_cmd

    def test_redacts_slack_webhook_url(self, tmp_path: Path) -> None:
        """Slack incoming webhook URLs must be redacted before persistence."""
        webhook = "https://hooks.slack.com/services/T00000000/B00000000/abcdefghijklmnopqrstuvwxyz"
        payload = _pre_payload(
            "Write",
            {"file_path": str(tmp_path / "note.md"), "content": f"webhook={webhook}\n"},
        )
        result = _run(payload, env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert result.returncode == 0
        data = json.loads(result.stdout.strip())
        updated_content = data["hookSpecificOutput"]["updatedInput"]["content"]
        assert webhook not in updated_content
        assert "[REDACTED]" in updated_content

    def test_no_secret_no_output(self, tmp_path: Path) -> None:
        """A clean command must produce no stdout (silent allow). Emitting
        an empty hookSpecificOutput would spam Claude with noise."""
        payload = _pre_payload(
            "Bash",
            {"command": "ls -la /tmp && echo done"},
        )
        result = _run(payload, env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert result.returncode == 0
        assert result.stdout.strip() == "", (
            f"Expected silent allow, got stdout={result.stdout!r}"
        )

    def test_meaningless_after_redaction_blocks(self, tmp_path: Path) -> None:
        """Fallback contract: when the entire payload IS the secret, redaction
        would leave nothing meaningful — the hook must block (exit 2) with a
        helpful message instead of running an empty command."""
        payload = _pre_payload(
            "Bash",
            {"command": "AKIAIOSFODNN7EXAMPLE"},
        )
        result = _run(payload, env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert result.returncode == 2, (
            "Hook must block when redaction would yield an empty command, "
            f"got {result.returncode}"
        )
        assert "BLOCKED" in result.stderr or "blocked" in result.stderr.lower()
