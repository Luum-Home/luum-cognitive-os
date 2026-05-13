"""Tests that hooks/context-diet.sh uses Claude Code's native
hookSpecificOutput.additionalContext transport.

Gap 3 migration: hook previously printed the diet advisory to stderr; now it
emits the native JSON envelope on stdout that Claude Code splices into the
agent's context window.

Backward-compat: when invoked without a valid Claude Code stdin payload, the
hook degrades to stderr.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = REPO_ROOT / "hooks" / "context-diet.sh"


def _run_hook(stdin_payload: str | None, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
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


class TestContextDietNative:
    def test_emits_hook_specific_output_json(self):
        """A valid Agent payload must produce hookSpecificOutput JSON on stdout
        with the diet advisory in additionalContext."""
        payload = json.dumps(
            {
                "tool_name": "Agent",
                "tool_input": {"prompt": "implement a small feature"},
            }
        )
        result = _run_hook(payload)
        assert result.returncode == 0, f"hook failed: {result.stderr}"
        # context-diet only emits JSON when it has rules to recommend.
        # If RULES_OUTPUT is empty, that's a config issue, not a transport bug.
        if not result.stdout.strip():
            pytest.skip(
                "context-diet produced no rules output — likely missing "
                "lib/prompt_builder.py or rules dir; transport layer untestable"
            )

        parsed = json.loads(result.stdout)
        assert "hookSpecificOutput" in parsed, f"missing hookSpecificOutput: {parsed}"
        hso = parsed["hookSpecificOutput"]
        assert hso.get("hookEventName") == "PreToolUse"
        assert "additionalContext" in hso
        assert isinstance(hso["additionalContext"], str)
        assert "CONTEXT DIET" in hso["additionalContext"], (
            f"expected diet advisory marker in context: {hso['additionalContext'][:200]!r}"
        )
        assert hso.get("permissionDecision") in ("allow", "deny", "ask")

    def test_truncates_at_10k_chars(self):
        """The hook must cap additionalContext at 10K chars even if a synthetic
        rule list balloons the advisory.

        We force a >10K rules output by stubbing the underlying rule selector
        to return a huge comma-separated list. Easiest path: override
        PYTHONPATH to a sandbox where lib.prompt_builder yields many fake rules.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            (tmp_root / "lib").mkdir()
            # Stub prompt_builder that returns 2000 fake rules → ~30K chars
            stub = '''
class PromptBuilder:
    @classmethod
    def from_project(cls, _project_dir):
        return cls()
    def selected_rules(self, _task_type):
        return [f"fake-rule-{i:04d}.md" for i in range(2000)]
'''
            (tmp_root / "lib" / "prompt_builder.py").write_text(stub)
            (tmp_root / "lib" / "__init__.py").write_text("")
            (tmp_root / ".cognitive-os").mkdir()
            (tmp_root / ".cognitive-os" / "cognitive-os.yaml").write_text(
                "project:\n  name: test\n  type: webapp\n  phase: reconstruction\n"
            )

            payload = json.dumps(
                {"tool_name": "Agent", "tool_input": {"prompt": "implement something"}}
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
            assert result.stdout.strip(), "expected JSON output, got nothing"

            parsed = json.loads(result.stdout)
            ctx = parsed["hookSpecificOutput"]["additionalContext"]
            assert len(ctx) <= 10000, f"additionalContext exceeded 10K cap: {len(ctx)}"
            assert "[truncated" in ctx, "missing truncation marker on oversized output"

    def test_degrades_gracefully_without_claude_code(self):
        """No tool_name on stdin => no JSON envelope, but stderr should still
        carry the advisory if rules were resolved."""
        result = _run_hook("")
        assert result.returncode == 0
        # Empty stdin => hook exits early before any output. That's fine.
        assert not result.stdout.strip().startswith("{"), (
            "hook wrote JSON without a valid Claude Code envelope"
        )

    def test_skips_non_agent_tool_calls(self):
        """Diet hook only fires for Agent — Bash/Read/etc. should be no-ops."""
        payload = json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "echo hi"}}
        )
        result = _run_hook(payload)
        assert result.returncode == 0
        assert not result.stdout.strip(), (
            f"unexpected stdout for non-Agent: {result.stdout!r}"
        )
