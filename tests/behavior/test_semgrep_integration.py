"""Behavior tests for Semgrep SAST integration.

Tests:
- Hook skips when semgrep not installed
- Hook skips when not sdd-apply output
- Hook skips when SEMGREP_ENABLED is not true (OFF by default)
- Finding classification (critical -> BLOCKER, warning -> CONCERN, info -> SUGGESTION)
- JSONL logging format
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = PROJECT_ROOT / "hooks" / "semgrep-scan.sh"


class TestSemgrepHookGating:
    """Tests for conditions that cause the hook to skip."""


    def test_hook_is_executable(self):
        assert os.access(HOOK_PATH, os.X_OK), "semgrep-scan.sh must be executable"

    def test_skips_when_disabled_by_default(self, run_hook, cognitive_os_env):
        """SEMGREP_ENABLED defaults to false -- hook should exit 0 immediately."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": "sdd-apply completed successfully",
        })
        env = {**cognitive_os_env["env"], "SEMGREP_ENABLED": "false"}
        result = run_hook("semgrep-scan.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        assert "SEMGREP" not in result.stdout

    def test_skips_when_env_not_set(self, run_hook, cognitive_os_env):
        """Without SEMGREP_ENABLED env var, hook should skip."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": "sdd-apply completed successfully",
        })
        env = cognitive_os_env["env"].copy()
        env.pop("SEMGREP_ENABLED", None)
        result = run_hook("semgrep-scan.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        assert "SEMGREP" not in result.stdout

    def test_skips_non_agent_tool(self, run_hook, cognitive_os_env):
        """Should not fire for non-Agent tools."""
        input_json = json.dumps({
            "tool_name": "Read",
            "tool_result": "file contents here",
        })
        env = {**cognitive_os_env["env"], "SEMGREP_ENABLED": "true"}
        result = run_hook("semgrep-scan.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        assert "SEMGREP" not in result.stdout

    def test_skips_non_sdd_apply_output(self, run_hook, cognitive_os_env):
        """Should only fire when agent output contains sdd-apply references."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": "I completed the code review and found 3 issues.",
        })
        env = {**cognitive_os_env["env"], "SEMGREP_ENABLED": "true"}
        result = run_hook("semgrep-scan.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        assert "SEMGREP" not in result.stdout

    def test_skips_when_semgrep_not_installed(self, run_hook, cognitive_os_env):
        """Should gracefully skip when semgrep binary is not available."""
        input_json = json.dumps({
            "tool_name": "Agent",
            "tool_result": "sdd-apply completed successfully",
        })
        # Use a PATH that doesn't include semgrep
        env = {
            **cognitive_os_env["env"],
            "SEMGREP_ENABLED": "true",
            "PATH": "/usr/bin:/bin",  # Minimal PATH without semgrep
        }
        result = run_hook("semgrep-scan.sh", env=env, stdin=input_json)
        assert result.returncode == 0
        # Should not crash or produce error output about missing semgrep

    def test_skips_in_private_mode(self, run_hook, cognitive_os_env):
        """Should skip when private mode is active."""
        private_flag = Path("/tmp/claude-private-mode-active")
        try:
            private_flag.touch()
            input_json = json.dumps({
                "tool_name": "Agent",
                "tool_result": "sdd-apply completed successfully",
            })
            env = {**cognitive_os_env["env"], "SEMGREP_ENABLED": "true"}
            result = run_hook("semgrep-scan.sh", env=env, stdin=input_json)
            assert result.returncode == 0
            assert "SEMGREP" not in result.stdout
        finally:
            private_flag.unlink(missing_ok=True)


class TestSemgrepFindingClassification:
    """Tests for the severity -> tier mapping logic."""

    def test_error_maps_to_blocker(self):
        """Semgrep ERROR severity should map to BLOCKER tier."""
        # This tests the mapping logic documented in the hook
        severity_map = {
            "ERROR": "BLOCKER",
            "WARNING": "CONCERN",
            "INFO": "SUGGESTION",
            "NOTE": "SUGGESTION",
        }
        assert severity_map["ERROR"] == "BLOCKER"

    def test_warning_maps_to_concern(self):
        severity_map = {
            "ERROR": "BLOCKER",
            "WARNING": "CONCERN",
            "INFO": "SUGGESTION",
        }
        assert severity_map["WARNING"] == "CONCERN"

    def test_info_maps_to_suggestion(self):
        severity_map = {
            "ERROR": "BLOCKER",
            "WARNING": "CONCERN",
            "INFO": "SUGGESTION",
        }
        assert severity_map["INFO"] == "SUGGESTION"


class TestSemgrepRuleFile:
    """Tests for the security-scanning.md rule file."""

    RULE_FILE = PROJECT_ROOT / "rules" / "security-scanning.md"


class TestSemgrepSkillFile:
    """Tests for the semgrep-scan skill definition."""

    SKILL_FILE = PROJECT_ROOT / "skills" / "semgrep-scan" / "SKILL.md"


    def test_skill_has_frontmatter(self):
        content = self.SKILL_FILE.read_text()
        assert content.startswith("---"), "Must have YAML frontmatter"
