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
import yaml

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

        ctx = data.get("hookSpecificOutput", {}).get("additionalContext", "")
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
        assert "additionalContext" in hso
        assert isinstance(hso["additionalContext"], str)
        assert len(hso["additionalContext"]) > 0


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

    def test_meaningless_after_redaction_denies_and_exits_2(self, tmp_path: Path) -> None:
        """Fallback contract: when the entire payload IS the secret, redaction
        would leave nothing meaningful, so the call must be DENIED.

        Regression guard. The branch used to emit permissionDecision "block" —
        a value no harness accepts (Claude Code takes allow|deny|ask|defer,
        Codex takes deny) — on exit 0 and with no backstop. Per the hooks
        contract, JSON that fails schema validation on exit 0 is a non-blocking
        error and the tool call proceeds: the guard failed open on every run.
        Both signals are asserted because either one alone blocks, and exit 2
        is the one that survives a future schema change."""
        payload = _pre_payload(
            "Bash",
            {"command": "AKIAIOSFODNN7EXAMPLE"},
        )
        result = _run(payload, env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert result.returncode == 2, (
            "Hook must block with exit 2 when the whole input is a secret, "
            f"got {result.returncode} with stdout={result.stdout!r}"
        )
        data = json.loads(result.stdout.strip())
        hso = data["hookSpecificOutput"]
        assert hso["permissionDecision"] == "deny"
        assert hso["permissionDecisionReason"]

    def test_emitted_permission_decision_is_a_value_the_host_accepts(
        self, tmp_path: Path
    ) -> None:
        """Every decision the hook emits must belong to the host's accepted
        set, read from the transcribed contract instead of hardcoded here: the
        defect this guards against was a decision string that looked plausible
        and that the host silently discarded."""
        schema = yaml.safe_load(
            (PROJECT_ROOT / "manifests/claude-code-hooks-schema.yaml").read_text(
                encoding="utf-8"
            )
        )
        allowed = set(schema["events"]["PreToolUse"]["permission_decision_values"])
        assert allowed, "the contract must enumerate the accepted decision values"

        seen = []
        for command in ("AKIAIOSFODNN7EXAMPLE", "echo AKIAIOSFODNN7EXAMPLE && echo ok"):
            result = _run(
                _pre_payload("Bash", {"command": command}),
                env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)},
            )
            data = json.loads(result.stdout.strip())
            decision = data["hookSpecificOutput"]["permissionDecision"]
            seen.append(decision)
            assert decision in allowed, (
                f"{decision!r} is not one of {sorted(allowed)}; the host would "
                "discard the decision and let the tool call through"
            )
        assert "deny" in seen and "allow" in seen, f"both paths must run, saw {seen}"

    def test_private_key_in_content_is_redacted(self, tmp_path: Path) -> None:
        """A PEM private key in Write content must be redacted.

        Regression guard: the pattern starts with five dashes, so
        `grep -oE "$pattern"` read it as an option string and failed with the
        error swallowed by 2>/dev/null. The pre-check then saw no match and the
        hook exited silently, letting the key reach disk verbatim. The fix is
        the `--` end-of-options marker on both grep calls."""
        pem = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEowIBAAKCAQEAxSbJ0KEYBODYFORTESTONLY0123456789abcdef\n"
            "-----END RSA PRIVATE KEY-----\n"
        )
        payload = _pre_payload(
            "Write",
            {"file_path": str(tmp_path / "id_rsa"), "content": pem + "trailing = 1\n"},
        )
        result = _run(payload, env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path)})
        assert result.returncode == 0, (
            f"the redaction path must allow, got {result.returncode}"
        )
        assert result.stdout.strip(), (
            "hook stayed silent on a PEM private key — the pattern is inert again"
        )
        data = json.loads(result.stdout.strip())
        hso = data["hookSpecificOutput"]
        assert hso["permissionDecision"] == "allow"
        updated = hso["updatedInput"]["content"]
        assert "-----BEGIN RSA PRIVATE KEY-----" not in updated
        assert "[REDACTED]" in updated
        # The rest of the file survives redaction.
        assert "trailing = 1" in updated
