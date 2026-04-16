"""Tests that hooks/inject-phase-context.sh uses Claude Code's native
hookSpecificOutput.additionalContext transport.

Gap 3 migration: hook previously printed phase context to stderr expecting the
host to scrape it; now it emits the native JSON envelope on stdout that
Claude Code splices into the agent's context window.

Backward-compat: when invoked without a valid Claude Code stdin payload, the
hook degrades to stderr so manual/test invocations still see the rules.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = REPO_ROOT / "hooks" / "inject-phase-context.sh"


def _run_hook(stdin_payload: str | None, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """Execute the hook with the given raw stdin string."""
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not found: {HOOK_PATH}")

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(REPO_ROOT)
    env["PRIVATE_MODE"] = "false"
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=stdin_payload if stdin_payload is not None else "",
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
    )


class TestInjectPhaseContextNative:
    def test_emits_hook_specific_output_json(self):
        """With a valid Claude Code Agent payload, stdout MUST be a JSON object
        carrying hookSpecificOutput.additionalContext."""
        payload = json.dumps(
            {
                "tool_name": "Agent",
                "tool_input": {"prompt": "implement a feature"},
            }
        )
        result = _run_hook(payload)
        assert result.returncode == 0, f"hook failed: {result.stderr}"
        assert result.stdout.strip(), "expected stdout JSON, got nothing"

        parsed = json.loads(result.stdout)
        assert "hookSpecificOutput" in parsed, f"missing hookSpecificOutput: {parsed}"
        hso = parsed["hookSpecificOutput"]
        assert hso.get("hookEventName") == "PreToolUse"
        assert "additionalContext" in hso
        assert isinstance(hso["additionalContext"], str)
        # Spec requires permissionDecision when present to be a known value
        assert hso.get("permissionDecision") in ("allow", "deny", "ask")

    def test_additional_context_not_empty_when_phase_active(self):
        """additionalContext must contain the project phase + phase rules so
        agents actually see the context — not just a stub envelope."""
        payload = json.dumps(
            {
                "tool_name": "Agent",
                "tool_input": {"prompt": "do some implementation work"},
            }
        )
        result = _run_hook(payload)
        assert result.returncode == 0, f"hook failed: {result.stderr}"
        parsed = json.loads(result.stdout)
        ctx = parsed["hookSpecificOutput"]["additionalContext"]

        assert "PHASE:" in ctx, f"phase header missing from additionalContext: {ctx[:200]!r}"
        assert "PHASE RULES:" in ctx, "phase rules section missing"
        assert "PROJECT:" in ctx, "project header missing"
        assert len(ctx) > 50, f"additionalContext suspiciously short: {len(ctx)} chars"

    def test_truncates_at_10k_chars(self):
        """If composed context would exceed 10K chars, it must be truncated and
        marked. This guards against blowing through Claude Code's hard cap."""
        # Build a prompt that triggers many gotchas + engram lookups so the
        # output buffer grows. We can't easily force >10K from the gotchas
        # alone, so we exercise the limit via a forced-large preamble.
        # Strategy: monkey-patch templates/agent-preamble.md to be huge for
        # this test by writing a temp version into a sandbox PROJECT dir.
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            (tmp_root / "templates").mkdir()
            (tmp_root / ".cognitive-os").mkdir()
            # Minimal cognitive-os.yaml
            (tmp_root / ".cognitive-os" / "cognitive-os.yaml").write_text(
                "project:\n  name: test\n  type: webapp\n  phase: reconstruction\n"
            )
            # Huge preamble — guaranteed to exceed 10K
            big = "X" * 15000
            (tmp_root / "templates" / "agent-preamble.md").write_text(big)
            # Copy hook lib so common.sh resolves
            shutil.copytree(REPO_ROOT / "hooks" / "_lib", tmp_root / "hooks_lib")

            payload = json.dumps(
                {"tool_name": "Agent", "tool_input": {"prompt": "anything"}}
            )
            env = os.environ.copy()
            env["CLAUDE_PROJECT_DIR"] = str(tmp_root)
            env["PRIVATE_MODE"] = "false"

            result = subprocess.run(
                ["bash", str(HOOK_PATH)],
                input=payload,
                capture_output=True,
                text=True,
                env=env,
                timeout=20,
            )
            assert result.returncode == 0, f"hook failed: {result.stderr}"
            parsed = json.loads(result.stdout)
            ctx = parsed["hookSpecificOutput"]["additionalContext"]

            assert len(ctx) <= 10000, f"additionalContext exceeded 10K cap: {len(ctx)}"
            assert "[truncated" in ctx, "missing truncation marker"

    def test_degrades_gracefully_without_claude_code(self):
        """When stdin has no tool_name (manual invocation), the hook must not
        crash and must emit the rules to stderr so a human running it from a
        terminal still sees something useful."""
        result = _run_hook("")
        assert result.returncode == 0, f"hook crashed without Claude input: {result.stderr}"
        # No JSON on stdout — that path is reserved for Claude Code transport
        assert not result.stdout.strip().startswith("{"), (
            f"hook wrote JSON to stdout without valid Claude Code input: {result.stdout[:200]!r}"
        )
        # But stderr should contain the rules so the operator can see them
        assert "PHASE" in result.stderr or "PHASE RULES" in result.stderr, (
            f"expected phase context on stderr fallback, got: {result.stderr[:300]!r}"
        )

    def test_skips_non_agent_tool_calls(self):
        """The hook should exit 0 silently for non-Agent tool calls (Bash, Read, etc.)."""
        payload = json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
            }
        )
        result = _run_hook(payload)
        assert result.returncode == 0
        # Should produce no output — neither JSON nor stderr context
        assert not result.stdout.strip(), f"unexpected stdout for non-Agent: {result.stdout!r}"
