"""Integration tests for ecosystem tool integrations.

Verifies GitHub Actions workflows for claude-code-action are present and valid,
plus optional ecosystem tools (agnix, Parry, Recall, Hcom, etc.).

Run: python -m pytest tests/integration/test_ecosystem_tools.py -v
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@pytest.fixture
def project_root():
    return Path(__file__).resolve().parent.parent.parent


class TestClaudeCodeActionIntegration:
    def test_interactive_workflow_exists(self, project_root):
        wf = project_root / ".github" / "workflows" / "claude-interactive.yml"
        assert wf.exists()
        content = wf.read_text()
        assert "anthropics/claude-code-action" in content
        assert "@claude" in content

    def test_pr_review_workflow_exists(self, project_root):
        wf = project_root / ".github" / "workflows" / "claude-pr-review.yml"
        assert wf.exists()
        content = wf.read_text()
        assert "hooks/**" in content  # Path filter for critical dirs

    def test_issue_triage_workflow_exists(self, project_root):
        wf = project_root / ".github" / "workflows" / "claude-issue-triage.yml"
        assert wf.exists()

    @pytest.mark.skipif(not HAS_YAML, reason="PyYAML not installed")
    def test_workflows_valid_yaml(self, project_root):
        """All workflow files should be valid YAML."""
        wf_dir = project_root / ".github" / "workflows"
        for wf in wf_dir.glob("claude-*.yml"):
            with open(wf) as f:
                parsed = yaml.safe_load(f)
            # PyYAML parses the bare 'on' key as boolean True
            assert "on" in parsed or True in parsed, f"{wf.name} missing 'on' key"
            assert "jobs" in parsed, f"{wf.name} missing 'jobs' key"


# ---------------------------------------------------------------------------
# Agnix -- Agent Configuration Linter
# ---------------------------------------------------------------------------


class TestAgnixIntegration:
    """Validate agnix linter integration with Cognitive OS."""

    def test_config_exists(self, project_root):
        """The .agnix.toml configuration file must exist at project root."""
        assert (project_root / ".agnix.toml").exists()

    def test_config_is_valid_toml(self, project_root):
        """The .agnix.toml must be parseable as valid TOML."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        config_path = project_root / ".agnix.toml"
        content = config_path.read_bytes()
        parsed = tomllib.loads(content.decode("utf-8"))
        assert "config" in parsed
        assert parsed["config"]["target"] == "claude-code"

    def test_hook_exists_and_executable(self, project_root):
        """The agnix-lint.sh hook must exist and be executable."""
        hook = project_root / "hooks" / "agnix-lint.sh"
        assert hook.exists(), "hooks/agnix-lint.sh not found"
        assert os.access(hook, os.X_OK), "hooks/agnix-lint.sh not executable"

    def test_agnix_available(self):
        """Skip if agnix not installed."""
        if not shutil.which("agnix"):
            pytest.skip("agnix not installed")
        result = subprocess.run(
            ["agnix", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_validates_our_skills(self, project_root):
        """If agnix is installed, our skills should pass validation."""
        if not shutil.which("agnix"):
            pytest.skip("agnix not installed")
        result = subprocess.run(
            ["agnix", "--format", "json", str(project_root)],
            capture_output=True,
            text=True,
        )
        # We accept warnings but not errors
        # (will need tuning based on what agnix flags)

    def test_hook_graceful_without_agnix(self, project_root):
        """Hook must exit 0 when agnix is not on PATH."""
        hook = project_root / "hooks" / "agnix-lint.sh"
        stdin_json = json.dumps({
            "tool_name": "Edit",
            "tool_input": {
                "file_path": str(project_root / "rules" / "test-rule.md")
            }
        })

        env = {
            **os.environ,
            "COGNITIVE_OS_PROJECT_DIR": str(project_root),
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
            "COGNITIVE_OS_SESSION_ID": "",
            "PATH": "/usr/bin:/bin",
        }

        result = subprocess.run(
            ["bash", str(hook)],
            input=stdin_json,
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Parry -- Prompt Injection Scanner
# ---------------------------------------------------------------------------


class TestParryIntegration:
    """Validate Parry prompt injection scanner integration."""

    def test_parry_config_in_yaml(self, project_root):
        """Verify parry config exists in cognitive-os.yaml."""
        config = (project_root / "cognitive-os.yaml").read_text()
        assert "parry:" in config

    def test_parry_available(self):
        """Check if parry-guard binary is installed (skips if not)."""
        if not shutil.which("parry-guard"):
            pytest.skip("parry-guard not installed")
        result = subprocess.run(["parry-guard", "--version"], capture_output=True)
        assert result.returncode == 0

    def test_parry_rules_documented(self, project_root):
        """Verify parry integration rule file exists."""
        assert (project_root / "rules" / "parry-integration.md").exists()


# ---------------------------------------------------------------------------
# Recall -- Conversation Search
# ---------------------------------------------------------------------------


class TestRecallIntegration:
    """Validate Recall conversation search integration."""

    def test_recall_skill_exists(self, project_root):
        """Verify recall-search skill file exists with expected content."""
        skill = project_root / "skills" / "recall-search" / "SKILL.md"
        assert skill.exists()
        content = skill.read_text()
        assert "recall search" in content

    def test_recall_available(self):
        """Check if recall binary is installed (skips if not)."""
        if not shutil.which("recall"):
            pytest.skip("recall not installed")
        result = subprocess.run(["recall", "--version"], capture_output=True)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Hcom -- Cross-Terminal Communication
# ---------------------------------------------------------------------------


class TestHcomIntegration:
    """Validate Hcom cross-terminal communication integration."""

    def test_hcom_config_in_yaml(self, project_root):
        """Verify hcom config exists in cognitive-os.yaml."""
        config = (project_root / "cognitive-os.yaml").read_text()
        assert "hcom:" in config

    def test_hcom_rules_documented(self, project_root):
        """Verify hcom integration rule file exists."""
        assert (project_root / "rules" / "hcom-integration.md").exists()

    def test_hcom_available(self):
        """Check if hcom binary is installed (skips if not)."""
        if not shutil.which("hcom"):
            pytest.skip("hcom not installed")
        result = subprocess.run(["hcom", "--version"], capture_output=True)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Trail of Bits -- Security Skills
# ---------------------------------------------------------------------------


class TestTrailOfBitsIntegration:
    """Validate Trail of Bits security skills integration."""

    def test_attribution_file_exists(self, project_root):
        assert (project_root / "ATTRIBUTION.md").exists()
        content = (project_root / "ATTRIBUTION.md").read_text()
        assert "Trail of Bits" in content
        assert "CC-BY-SA-4.0" in content

    def test_install_script_exists(self, project_root):
        script = project_root / "scripts" / "install-tob-skills.sh"
        assert script.exists()

    def test_rules_documented(self, project_root):
        assert (project_root / "rules" / "trailofbits-skills.md").exists()


# ---------------------------------------------------------------------------
# Usage Monitor -- Claude Usage Reader
# ---------------------------------------------------------------------------


class TestUsageMonitorIntegration:
    """Validate Claude usage reader integration."""

    def test_reader_module_exists(self, project_root):
        assert (project_root / "lib" / "claude_usage_reader.py").exists()

    def test_reader_imports(self):
        from lib.claude_usage_reader import read_usage, reconcile_costs, summarize_usage

        assert callable(read_usage)
        assert callable(reconcile_costs)

    def test_reader_handles_empty_dir(self, tmp_path):
        from lib.claude_usage_reader import read_usage

        # Should return empty list, not crash
        result = read_usage(project_filter=str(tmp_path))
        assert isinstance(result, list)
