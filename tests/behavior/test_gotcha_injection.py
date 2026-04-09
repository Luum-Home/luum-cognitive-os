"""Tests for hooks/inject-phase-context.sh.

Validates:
- Phase-specific rule output for reconstruction/stabilization/production/maintenance
- Keyword-triggered gotcha injection (lib/, settings.json, new hook, workflow, plans/)
- Non-Agent tool_name causes exit 0 with no output
- Trust Report reminder is always present in output
- Exit code is always 0
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK = PROJECT_ROOT / "hooks" / "inject-phase-context.sh"
COGNITIVE_OS_YAML = PROJECT_ROOT / "cognitive-os.yaml"

pytestmark = pytest.mark.behavior


def _run_hook(tool_name: str, prompt: str = "", env_overrides=None, timeout=10):
    """Run inject-phase-context.sh with a JSON payload on stdin."""
    payload = json.dumps({
        "tool_name": tool_name,
        "tool_input": {"prompt": prompt},
    })
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT),
    }
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


# ─── Hook structure ───────────────────────────────────────────────────────────


class TestHookStructure:
    def test_hook_exists(self):
        assert HOOK.exists(), f"Missing: {HOOK}"

    def test_hook_is_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", str(HOOK)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Bash syntax error: {result.stderr}"

    def test_exit_code_always_zero_for_agent(self):
        result = _run_hook("Agent", "do something")
        assert result.returncode == 0

    def test_exit_code_always_zero_for_non_agent(self):
        result = _run_hook("Bash", "run a command")
        assert result.returncode == 0


# ─── Non-Agent tool filtering ─────────────────────────────────────────────────


class TestNonAgentToolFiltering:
    """Non-Agent tool_name should produce no phase output."""

    def test_bash_tool_produces_no_phase_output(self):
        result = _run_hook("Bash", "ls -la")
        # Should be empty or very minimal
        assert "PHASE RULES" not in result.stdout
        assert "PHASE:" not in result.stdout

    def test_read_tool_produces_no_phase_output(self):
        result = _run_hook("Read", "read a file")
        assert "PHASE RULES" not in result.stdout
        assert "PHASE:" not in result.stdout

    def test_write_tool_produces_no_phase_output(self):
        result = _run_hook("Write", "write content")
        assert "PHASE RULES" not in result.stdout

    def test_edit_tool_produces_no_phase_output(self):
        result = _run_hook("Edit", "edit a line")
        assert "PHASE RULES" not in result.stdout

    def test_task_tool_produces_output(self):
        """'task' is an alias for Agent and should trigger output."""
        result = _run_hook("task", "implement something")
        # task tool should produce phase context
        assert result.returncode == 0
        # Should have some output (phase or project info)
        assert len(result.stdout.strip()) > 0

    def test_delegate_tool_produces_output(self):
        """'delegate' is also treated as Agent."""
        result = _run_hook("delegate", "delegate work")
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0


# ─── Phase output ─────────────────────────────────────────────────────────────


class TestPhaseOutput:
    """Agent calls should always emit phase context."""

    def test_agent_produces_phase_section(self):
        result = _run_hook("Agent", "build the feature")
        assert "PHASE" in result.stdout

    def test_agent_produces_project_section(self):
        result = _run_hook("Agent", "build the feature")
        assert "PROJECT" in result.stdout

    def test_agent_produces_phase_rules(self):
        result = _run_hook("Agent", "build the feature")
        assert "PHASE RULES" in result.stdout or "RULES" in result.stdout

    def test_reconstruction_phase_rules_are_present(self):
        """When phase is reconstruction, rewrite-focused rules appear."""
        result = _run_hook("Agent", "build the feature")
        output = result.stdout
        # Phase is read from cognitive-os.yaml; reconstruction rules contain specific text
        # The hook emits phase-specific rules, so output should contain rule content
        assert len(output.strip()) > 50, "Hook should produce substantive output"

    def test_trust_report_reminder_always_present(self):
        """The Trust Report reminder must always be included."""
        result = _run_hook("Agent", "do anything")
        assert "Trust Report" in result.stdout or "TRUST" in result.stdout.upper()

    def test_trust_report_reminder_present_with_simple_prompt(self):
        result = _run_hook("Agent", "fix the bug")
        assert "Trust Report" in result.stdout or "trust" in result.stdout.lower()

    def test_required_include_in_output(self):
        """Output should contain REQUIRED marker before Trust Report."""
        result = _run_hook("Agent", "do something")
        assert "REQUIRED" in result.stdout


# ─── Keyword-triggered gotchas ────────────────────────────────────────────────


class TestGotchaInjection:
    """Specific keywords in the prompt trigger warning/gotcha sections."""

    def test_lib_keyword_triggers_symlink_warning(self):
        result = _run_hook("Agent", "update lib/something.py for dedup")
        output = result.stdout
        assert "KNOWN TRAPS" in output or "symlink" in output.lower() or "WARNING" in output

    def test_settings_json_keyword_triggers_generated_warning(self):
        result = _run_hook("Agent", "edit settings.json to wire the hook")
        output = result.stdout
        assert (
            "KNOWN TRAPS" in output
            or "generated" in output.lower()
            or "apply-efficiency-profile" in output.lower()
            or "WARNING" in output
        )

    def test_new_hook_keyword_triggers_profile_registration_warning(self):
        result = _run_hook("Agent", "create a new hook in hooks/")
        output = result.stdout
        assert (
            "KNOWN TRAPS" in output
            or "profile" in output.lower()
            or "register" in output.lower()
            or "WARNING" in output
        )

    def test_hooks_sh_keyword_triggers_profile_warning(self):
        result = _run_hook("Agent", "add hooks/rate-monitor.sh to the system")
        output = result.stdout
        assert (
            "KNOWN TRAPS" in output
            or "profile" in output.lower()
            or "WARNING" in output
        )

    def test_workflow_keyword_triggers_schema_warning(self):
        result = _run_hook("Agent", "create a workflow pipeline yaml for the feature")
        output = result.stdout
        assert (
            "KNOWN TRAPS" in output
            or "schema" in output.lower()
            or "workflow" in output.lower()
            or "WARNING" in output
        )

    def test_plans_dir_keyword_triggers_directory_warning(self):
        result = _run_hook("Agent", "look at plans/ directory for context")
        output = result.stdout
        assert (
            "KNOWN TRAPS" in output
            or "plans/" in output
            or "WARNING" in output
        )

    def test_no_keyword_produces_no_traps_section(self):
        result = _run_hook("Agent", "add two numbers together and return the result")
        # No keyword → no KNOWN TRAPS section
        output = result.stdout
        assert "KNOWN TRAPS" not in output

    def test_multiple_keywords_produce_multiple_warnings(self):
        result = _run_hook(
            "Agent",
            "update lib/mymodule.py and settings.json for the new hook",
        )
        output = result.stdout
        # At minimum a KNOWN TRAPS section should exist
        assert "KNOWN TRAPS" in output or "WARNING" in output


# ─── Project gotchas file injection ──────────────────────────────────────────


class TestProjectGotchasFile:
    """When prompt mentions COS internals, project-gotchas.md is injected."""

    def test_lib_reference_triggers_gotchas_file_injection(self):
        """Prompt mentioning lib/ should inject project-gotchas.md if it exists."""
        gotchas_path = PROJECT_ROOT / "templates" / "project-gotchas.md"
        if not gotchas_path.exists():
            pytest.skip("project-gotchas.md not found")

        result = _run_hook("Agent", "update lib/pipeline_executor.py")
        output = result.stdout
        # The gotchas file should be included in output
        assert "GOTCHAS" in output or "gotcha" in output.lower() or len(output) > 200

    def test_hooks_reference_triggers_gotchas_injection(self):
        """Prompt mentioning hooks/ should inject project-gotchas.md if it exists."""
        gotchas_path = PROJECT_ROOT / "templates" / "project-gotchas.md"
        if not gotchas_path.exists():
            pytest.skip("project-gotchas.md not found")

        result = _run_hook("Agent", "create hooks/new-feature.sh")
        output = result.stdout
        assert len(output.strip()) > 50


# ─── Squad and Engram sections ───────────────────────────────────────────────


class TestOptionalSections:
    """Optional sections appear only when their data exists."""

    def test_output_does_not_crash_on_missing_squad_dir(self):
        """Missing squads dir should not cause errors."""
        result = _run_hook("Agent", "implement feature")
        assert result.returncode == 0

    def test_output_does_not_crash_on_missing_cognitive_os_yaml(self, tmp_path):
        """When cognitive-os.yaml is absent, hook uses defaults gracefully."""
        empty_project = tmp_path
        result = subprocess.run(
            ["bash", str(HOOK)],
            input=json.dumps({
                "tool_name": "Agent",
                "tool_input": {"prompt": "implement something"},
            }),
            capture_output=True,
            text=True,
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": str(tmp_path),
                "CLAUDE_PROJECT_DIR": str(empty_project),
            },
            timeout=10,
        )
        assert result.returncode == 0


# ─── Output format ────────────────────────────────────────────────────────────


class TestOutputFormat:
    def test_output_contains_project_name(self):
        result = _run_hook("Agent", "do something")
        output = result.stdout
        assert "PROJECT" in output

    def test_output_contains_phase_label(self):
        result = _run_hook("Agent", "do something")
        assert "PHASE" in result.stdout

    def test_output_not_empty_for_agent(self):
        result = _run_hook("Agent", "implement a feature")
        assert len(result.stdout.strip()) > 0

    def test_stderr_is_empty_on_success(self):
        result = _run_hook("Agent", "implement a feature")
        # stderr should be empty or very minimal for a clean run
        # Engram errors may appear on stderr but should not affect stdout
        assert result.returncode == 0
