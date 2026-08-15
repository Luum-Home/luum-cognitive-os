"""Behavioral tests for subagent-context-injector.sh hook.

Verifies that every sub-agent receives mandatory project rules
via additionalContext. These tests execute the actual hook with
real JSON input and verify the output contains critical rules.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = PROJECT_ROOT / "hooks" / "subagent-context-injector.sh"
MANDATORY_RULES_PATH = PROJECT_ROOT / "templates" / "agent-mandatory-rules.md"


def _run_hook(stdin_json: dict, env_overrides: dict | None = None) -> dict:
    """Execute the hook with given JSON stdin and return parsed output."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(PROJECT_ROOT)
    env["COS_SESSION_DIR"] = "/tmp/cos-test-session"
    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps(stdin_json),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )

    # Hook should always exit 0
    assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"

    # Parse JSON output (may be empty if no context to inject)
    stdout = result.stdout.strip()
    if not stdout:
        return {}
    return json.loads(stdout)


def _additional_context(output: dict) -> str:
    """Return additionalContext from the ONE shape Claude Code consumes.

    The host reads ``additionalContext`` only from inside ``hookSpecificOutput``,
    alongside ``hookEventName``. There is no top-level form: a hook that prints
    ``{"additionalContext": "..."}`` at the root emits valid JSON that the host
    parses and then discards, because the field is not in the schema. The drop
    is silent — a payload starting with ``{`` that parses as valid JSON is never
    re-read as plain text, so there is no fallback either.

    Contract and citations: ``manifests/claude-code-hooks-schema.yaml``
    (``additional_context.placement``, ``stdout_parsing``).

    This helper used to fall back to the root-level key. That made it impossible
    for these tests to fail because a hook used the wrong shape — a suppressor
    that suppressed nothing, inside the very test that exists to rule that out.
    """
    hso = output.get("hookSpecificOutput")
    if not isinstance(hso, dict):
        raise AssertionError(
            "hook output has no `hookSpecificOutput` object; Claude Code reads "
            f"additionalContext only from there. Got top-level keys: "
            f"{sorted(output)}"
        )
    if hso.get("hookEventName") != "SubagentStart":
        raise AssertionError(
            "hookSpecificOutput.hookEventName must be 'SubagentStart' — the host "
            "requires the event name alongside additionalContext. Got: "
            f"{hso.get('hookEventName')!r}"
        )
    return hso.get("additionalContext", "")


class TestMandatoryRulesInjection:
    """Every sub-agent MUST receive mandatory project rules."""

    def test_hook_returns_additional_context(self):
        """The hook must return a JSON object with additionalContext."""
        output = _run_hook({"prompt": "test agent prompt"})
        assert _additional_context(output), (
            "Hook did not return additionalContext — sub-agents will not receive project rules"
        )

    def test_symlink_rules_injected(self):
        """The symlink warning MUST be in every sub-agent's context."""
        output = _run_hook({"prompt": "audit the codebase"})
        context = _additional_context(output)
        assert "readlink -f" in context, (
            "Symlink resolution rule not injected — agents will report false 'missing' files"
        )
        assert "file_exists_strict" in context or "file_checker" in context, (
            "file_checker.sh reference not injected"
        )

    def test_no_structural_tests_rule_injected(self):
        """The rule against structural-only tests MUST be injected."""
        output = _run_hook({"prompt": "write tests for the module"})
        context = _additional_context(output)
        assert "verify file existence" in context.lower() or "execute code" in context.lower(), (
            "Test quality rule not injected — agents may create structural-only tests"
        )

    def test_no_dead_metadata_rule_injected(self):
        """The rule against dead metadata MUST be injected."""
        output = _run_hook({"prompt": "add a new field to skills"})
        context = _additional_context(output)
        assert "metadata" in context.lower() and "consume" in context.lower(), (
            "Dead metadata prevention rule not injected"
        )

    def test_performance_rules_injected(self):
        """The rule against O(n) subprocess spawns MUST be injected."""
        output = _run_hook({"prompt": "create a new hook"})
        context = _additional_context(output)
        assert "python3" in context and "while" in context.lower(), (
            "Performance anti-pattern rule not injected — agents may create O(n) subprocess hooks"
        )

    def test_engram_save_rule_injected(self):
        """The rule to save discoveries to engram MUST be injected."""
        output = _run_hook({"prompt": "investigate the bug"})
        context = _additional_context(output)
        assert "engram" in context.lower() and "mem_save" in context.lower(), (
            "Engram save rule not injected — agents will not persist discoveries"
        )


class TestMandatoryRulesFileIntegrity:
    """The mandatory rules template must exist and contain all critical sections."""

    def test_template_file_exists(self):
        """templates/agent-mandatory-rules.md must exist."""
        assert MANDATORY_RULES_PATH.exists(), (
            "Mandatory rules template missing — sub-agents will use inline fallback"
        )

    def test_template_has_symlink_section(self):
        """Template must have symlink rules."""
        content = MANDATORY_RULES_PATH.read_text()
        assert "Symlinks" in content
        assert "readlink" in content

    def test_template_has_auditing_section(self):
        """Template must have auditing rules."""
        content = MANDATORY_RULES_PATH.read_text()
        assert "Auditing" in content
        assert "Cross-validate" in content or "cross-validate" in content

    def test_template_has_code_quality_section(self):
        """Template must have code quality rules."""
        content = MANDATORY_RULES_PATH.read_text()
        assert "Code Quality" in content
        assert "execute code" in content.lower() or "verify behavior" in content.lower()

    def test_template_has_performance_section(self):
        """Template must have performance rules."""
        content = MANDATORY_RULES_PATH.read_text()
        assert "Performance" in content
        assert "python3" in content


class TestMandatoryRulesEmission:
    """The template must be EMITTED intact — this tests composition, not arrival.

    Renamed from ``TestMandatoryRulesDelivery`` on 2026-08-15. The old name and
    its assertion messages claimed the rules "arrive" in the sub-agent. Nothing
    here can show that. Every test in this file runs the hook under
    ``subprocess.run`` and inspects ``result.stdout`` — that is the hook's
    output, measured one step before the host decides whether to consume it.
    Whether the host consumes it depends on the registration in
    ``.claude/settings.json`` (see ``async``) and on the event's contract, and
    neither is exercised by running the script.

    So the whole file is now scoped to what it can prove: given this stdin, the
    hook emits this JSON, in the shape the host documents, without truncation.

    Arrival is a separate, non-deterministic question measured against real
    sub-agent transcripts by ``scripts/check_subagent_context_arrival.py``.
    Deliberately NOT a pytest case: it reads ``~/.claude/projects`` and its
    result depends on what has run on this machine, so in CI it would either be
    skipped into meaninglessness or mocked — and a mocked transcript asserting
    the mock contains what the mock put there proves nothing at all.

    Deliberately NOT a content assertion either: it never names a phrase from
    the template, so rewording the rules cannot break it. What it catches is the
    composition failing — the file going missing (hook silently drops to its
    inline fallback), the composition dropping it, or the 10K truncation eating
    part of it.
    """

    def test_template_body_is_emitted_verbatim(self):
        """Every byte of the template must reach the emitted additionalContext.

        The hook loads it via `$(cat ...)`, which strips trailing newlines —
        hence the rstrip. Any other difference means the mechanism mutated or
        truncated the rules while composing them.
        """
        context = _additional_context(_run_hook({"prompt": "any task at all"}))
        body = MANDATORY_RULES_PATH.read_text().rstrip("\n")
        assert body in context, (
            "templates/agent-mandatory-rules.md was not emitted verbatim in "
            "additionalContext — the composition dropped or truncated it "
            "(check for the inline fallback or the 10K cap)"
        )

    def test_inline_fallback_is_not_in_use(self):
        """The fallback is a degraded copy; using it silently loses rules.

        The fallback text omits sections the real template carries, so a hook
        that quietly falls back still returns plausible-looking context.
        """
        context = _additional_context(_run_hook({"prompt": "any task at all"}))
        assert "## MANDATORY PROJECT RULES" in context, (
            "Hook fell back to its inline rule set — the template was not read"
        )


class TestContextBudget:
    """The composed context must fit the hook's hard cap, with margin.

    subagent-context-injector.sh caps additionalContext at
    MAX_CONTEXT_CHARS=10000. Truncation is SILENT and cuts from the end, so
    growth in the rules template degrades the preamble — a different file than
    the one anyone edited. Every sub-agent pays this corpus on every turn, so
    the budget is a real constraint, not a style preference.
    """

    MAX_CONTEXT_CHARS = 10000
    # Margin so the next rule addition fails this test rather than silently
    # truncating the preamble in production.
    RESERVE_CHARS = 250

    def test_delivered_context_is_not_truncated(self):
        context = _additional_context(_run_hook({"prompt": "any task at all"}))
        assert "[truncated at 10K chars]" not in context, (
            f"additionalContext hit the {self.MAX_CONTEXT_CHARS}-char cap and was "
            "truncated — the tail of the agent preamble is being dropped"
        )

    def test_delivered_context_keeps_headroom(self):
        context = _additional_context(_run_hook({"prompt": "any task at all"}))
        budget = self.MAX_CONTEXT_CHARS - self.RESERVE_CHARS
        assert len(context) <= budget, (
            f"Injected context is {len(context)} chars, over the "
            f"{budget}-char working budget "
            f"({self.MAX_CONTEXT_CHARS} cap - {self.RESERVE_CHARS} reserve). "
            "Every sub-agent pays this on every turn: shorten an existing rule "
            "before adding another."
        )


class TestHookDoesNotBlock:
    """The hook must never block sub-agent launch."""

    def test_exit_code_always_zero(self):
        """Hook must exit 0 even with empty input."""
        result = subprocess.run(
            ["bash", str(HOOK_PATH)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT)},
        )
        assert result.returncode == 0

    def test_exit_code_zero_with_invalid_json(self):
        """Hook must exit 0 even with invalid JSON."""
        result = subprocess.run(
            ["bash", str(HOOK_PATH)],
            input="not json at all",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT)},
        )
        assert result.returncode == 0

    def test_completes_under_3_seconds(self):
        """Hook must complete within 3 seconds."""
        import time
        start = time.time()
        _run_hook({"prompt": "test prompt"})
        elapsed = time.time() - start
        assert elapsed < 3.0, f"Hook took {elapsed:.1f}s — must be under 3s"
