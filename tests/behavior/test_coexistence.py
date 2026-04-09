"""Behavior tests for Cognitive OS coexistence with existing project configs.

Tests that COS safely coexists with projects that already have .claude/
configuration: rules are namespaced under cos/, settings.json is merged
(not overwritten), and project files are never touched.

Related files:
  - hooks/self-install.sh (rule namespacing + migration)
  - scripts/merge-settings.sh (settings merge helper)
  - install.sh (conflict detection + merge)
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = PROJECT_ROOT / "hooks" / "self-install.sh"
MERGE_SCRIPT = PROJECT_ROOT / "scripts" / "merge-settings.sh"


def _run_hook(project_dir: str, env_overrides: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = project_dir
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        capture_output=True, text=True, env=env, timeout=5,
    )


def _run_merge(existing: str, cos_hooks: str, output: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(MERGE_SCRIPT), existing, cos_hooks, output],
        capture_output=True, text=True, timeout=5,
    )


def _setup_cos_project(tmp_path: Path) -> Path:
    """Create a self-hosted luum-agent-os structure (for self-install.sh tests)."""
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "self-install.sh").write_text("#!/usr/bin/env bash\nexit 0\n")

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "trust-score.md").write_text("# Trust Score\n")
    (rules_dir / "cost-tracking.md").write_text("# Cost Tracking\n")
    (rules_dir / "license-policy.md").write_text("# License Policy\n")

    (tmp_path / ".claude").mkdir(parents=True)
    (tmp_path / ".claude" / "settings.json").write_text('{"hooks": {}}\n')
    (tmp_path / "cognitive-os.yaml").write_text("version: 1\n")

    return tmp_path


# ── Self-install rule namespacing tests ──────────────────────────────


class TestRuleNamespacing:
    """COS rules go to .claude/rules/cos/, not .claude/rules/."""

    def test_rules_go_to_cos_subdirectory(self, tmp_path):
        project = _setup_cos_project(tmp_path)
        _run_hook(str(project))

        cos_rules = project / ".claude" / "rules" / "cos"
        assert cos_rules.is_dir()
        assert (cos_rules / "trust-score.md").is_symlink()
        assert (cos_rules / "cost-tracking.md").is_symlink()
        assert (cos_rules / "license-policy.md").is_symlink()

    def test_rules_not_in_flat_rules_dir(self, tmp_path):
        project = _setup_cos_project(tmp_path)
        _run_hook(str(project))

        # COS rules should NOT be flat in .claude/rules/
        flat_rules = project / ".claude" / "rules"
        flat_symlinks = [
            f for f in flat_rules.iterdir()
            if f.is_symlink() and f.suffix == ".md"
        ]
        assert len(flat_symlinks) == 0, "COS rules should not be flat in .claude/rules/"

    def test_project_rules_untouched(self, tmp_path):
        project = _setup_cos_project(tmp_path)

        # Pre-existing project rule
        project_rules = project / ".claude" / "rules"
        project_rules.mkdir(parents=True, exist_ok=True)
        arch_rule = project_rules / "architecture.md"
        arch_rule.write_text("# My Project Architecture\nSpecific to my project.\n")

        _run_hook(str(project))

        # Project rule still there, untouched
        assert arch_rule.exists()
        assert not arch_rule.is_symlink()
        assert "My Project Architecture" in arch_rule.read_text()

    def test_mixed_rules_both_accessible(self, tmp_path):
        project = _setup_cos_project(tmp_path)

        # Pre-existing project rule
        project_rules = project / ".claude" / "rules"
        project_rules.mkdir(parents=True, exist_ok=True)
        (project_rules / "architecture.md").write_text("# Architecture\n")

        _run_hook(str(project))

        # Both project and COS rules accessible
        assert (project / ".claude" / "rules" / "architecture.md").exists()
        assert (project / ".claude" / "rules" / "cos" / "trust-score.md").exists()


class TestMigrationFromFlatSymlinks:
    """Old flat symlinks in .claude/rules/ pointing to rules/ are cleaned up."""

    def test_old_flat_symlinks_removed(self, tmp_path):
        project = _setup_cos_project(tmp_path)

        # Simulate old-style flat symlinks
        rules_dir = project / ".claude" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        old_link = rules_dir / "trust-score.md"
        old_link.symlink_to(project / "rules" / "trust-score.md")
        assert old_link.is_symlink()

        _run_hook(str(project))

        # Old flat symlink removed
        assert not old_link.exists()
        # New namespaced symlink created
        assert (rules_dir / "cos" / "trust-score.md").is_symlink()

    def test_migration_preserves_project_files(self, tmp_path):
        project = _setup_cos_project(tmp_path)

        # Project has a regular file AND old COS symlinks
        rules_dir = project / ".claude" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        (rules_dir / "my-project-rule.md").write_text("# My Rule\n")
        old_link = rules_dir / "cost-tracking.md"
        old_link.symlink_to(project / "rules" / "cost-tracking.md")

        _run_hook(str(project))

        # Project file preserved
        assert (rules_dir / "my-project-rule.md").exists()
        assert not (rules_dir / "my-project-rule.md").is_symlink()
        # Old symlink removed
        assert not (rules_dir / "cost-tracking.md").is_symlink() or \
               not (rules_dir / "cost-tracking.md").exists()
        # New location
        assert (rules_dir / "cos" / "cost-tracking.md").is_symlink()

    def test_migration_ignores_symlinks_to_other_targets(self, tmp_path):
        project = _setup_cos_project(tmp_path)

        # Symlink pointing somewhere else (not our rules/)
        rules_dir = project / ".claude" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        other_target = tmp_path / "other" / "some-rule.md"
        other_target.parent.mkdir(parents=True)
        other_target.write_text("# Other\n")
        external_link = rules_dir / "some-rule.md"
        external_link.symlink_to(other_target)

        _run_hook(str(project))

        # External symlink preserved (it doesn't point to our rules/)
        assert external_link.is_symlink()
        assert external_link.exists()

    def test_old_relative_symlinks_removed(self, tmp_path):
        """Bug fix: old symlinks used relative paths (../../rules/X.md) but
        cleanup only matched absolute paths. Verify relative symlinks are
        also cleaned up after the fix."""
        project = _setup_cos_project(tmp_path)

        rules_dir = project / ".claude" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        old_link = rules_dir / "trust-score.md"
        # Create relative symlink — this is what self-install.sh historically created
        old_link.symlink_to(Path("../../rules/trust-score.md"))
        assert old_link.is_symlink()

        _run_hook(str(project))

        # Old relative symlink must be removed
        assert not old_link.exists(), (
            "Relative symlink ../../rules/trust-score.md was not cleaned up"
        )
        # New namespaced symlink created
        assert (rules_dir / "cos" / "trust-score.md").is_symlink()

    def test_double_run_idempotent_after_migration(self, tmp_path):
        project = _setup_cos_project(tmp_path)

        # First run with old symlinks
        rules_dir = project / ".claude" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        (rules_dir / "trust-score.md").symlink_to(project / "rules" / "trust-score.md")

        r1 = _run_hook(str(project))
        assert "FIXED" in r1.stdout

        r2 = _run_hook(str(project))
        # Second run should not add new symlinks (migration already complete)
        assert "added" not in r2.stdout or "added 0" in r2.stdout


# ── Settings merge tests ──────────────────────────────────────────────


class TestSettingsMerge:
    """Tests for scripts/merge-settings.sh."""

    @pytest.fixture
    def has_jq(self):
        result = subprocess.run(["which", "jq"], capture_output=True)
        if result.returncode != 0:
            pytest.skip("jq not installed")

    def _write_json(self, path: Path, data: dict):
        path.write_text(json.dumps(data, indent=2))

    def test_merge_preserves_project_hooks(self, tmp_path, has_jq):
        existing = tmp_path / "existing.json"
        cos = tmp_path / "cos.json"
        output = tmp_path / "merged.json"

        self._write_json(existing, {
            "hooks": {
                "SessionStart": [{
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "bash my-project-hook.sh"}
                    ]
                }]
            }
        })

        self._write_json(cos, {
            "hooks": {
                "SessionStart": [{
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/session-init.sh\""}
                    ]
                }]
            }
        })

        result = _run_merge(str(existing), str(cos), str(output))
        assert result.returncode == 0, f"stderr: {result.stderr}"

        merged = json.loads(output.read_text())
        session_hooks = merged["hooks"]["SessionStart"][0]["hooks"]
        commands = [h["command"] for h in session_hooks]

        # Both preserved
        assert "bash my-project-hook.sh" in commands
        assert 'bash "$CLAUDE_PROJECT_DIR/hooks/session-init.sh"' in commands

    def test_merge_no_duplicates_on_double_run(self, tmp_path, has_jq):
        existing = tmp_path / "existing.json"
        cos = tmp_path / "cos.json"
        output = tmp_path / "merged.json"

        self._write_json(existing, {
            "hooks": {
                "SessionStart": [{
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/session-init.sh\""}
                    ]
                }]
            }
        })

        self._write_json(cos, {
            "hooks": {
                "SessionStart": [{
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/session-init.sh\""}
                    ]
                }]
            }
        })

        _run_merge(str(existing), str(cos), str(output))
        merged = json.loads(output.read_text())
        session_hooks = merged["hooks"]["SessionStart"][0]["hooks"]

        # No duplicate
        assert len(session_hooks) == 1

    def test_merge_preserves_extra_settings_keys(self, tmp_path, has_jq):
        existing = tmp_path / "existing.json"
        cos = tmp_path / "cos.json"
        output = tmp_path / "merged.json"

        self._write_json(existing, {
            "permissions": {"allow": ["Bash", "Edit"]},
            "env": {"MY_VAR": "value"},
            "hooks": {
                "SessionStart": [{
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "bash project-start.sh"}
                    ]
                }]
            }
        })

        self._write_json(cos, {
            "hooks": {
                "SessionStart": [{
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/self-install.sh\""}
                    ]
                }]
            }
        })

        _run_merge(str(existing), str(cos), str(output))
        merged = json.loads(output.read_text())

        # Extra keys preserved
        assert merged["permissions"] == {"allow": ["Bash", "Edit"]}
        assert merged["env"] == {"MY_VAR": "value"}

    def test_merge_adds_new_lifecycle_events(self, tmp_path, has_jq):
        existing = tmp_path / "existing.json"
        cos = tmp_path / "cos.json"
        output = tmp_path / "merged.json"

        # Project only has SessionStart
        self._write_json(existing, {
            "hooks": {
                "SessionStart": [{
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "bash project-start.sh"}
                    ]
                }]
            }
        })

        # COS has SessionStart + PostToolUse
        self._write_json(cos, {
            "hooks": {
                "SessionStart": [{
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/self-install.sh\""}
                    ]
                }],
                "PostToolUse": [{
                    "matcher": "Bash",
                    "hooks": [
                        {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/error-pipeline.sh\""}
                    ]
                }]
            }
        })

        _run_merge(str(existing), str(cos), str(output))
        merged = json.loads(output.read_text())

        assert "SessionStart" in merged["hooks"]
        assert "PostToolUse" in merged["hooks"]
        assert len(merged["hooks"]["PostToolUse"]) == 1

    def test_merge_adds_new_matcher_groups(self, tmp_path, has_jq):
        existing = tmp_path / "existing.json"
        cos = tmp_path / "cos.json"
        output = tmp_path / "merged.json"

        # Project has PostToolUse for Bash only
        self._write_json(existing, {
            "hooks": {
                "PostToolUse": [{
                    "matcher": "Bash",
                    "hooks": [
                        {"type": "command", "command": "bash my-bash-hook.sh"}
                    ]
                }]
            }
        })

        # COS has PostToolUse for Bash + Agent
        self._write_json(cos, {
            "hooks": {
                "PostToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/error-pipeline.sh\""}
                        ]
                    },
                    {
                        "matcher": "Agent",
                        "hooks": [
                            {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/agent-checkpoint.sh\""}
                        ]
                    }
                ]
            }
        })

        _run_merge(str(existing), str(cos), str(output))
        merged = json.loads(output.read_text())

        post_tool = merged["hooks"]["PostToolUse"]
        matchers = [g["matcher"] for g in post_tool]
        assert "Bash" in matchers
        assert "Agent" in matchers

        # Bash group has both hooks
        bash_group = next(g for g in post_tool if g["matcher"] == "Bash")
        cmds = [h["command"] for h in bash_group["hooks"]]
        assert "bash my-bash-hook.sh" in cmds
        assert 'bash "$CLAUDE_PROJECT_DIR/hooks/error-pipeline.sh"' in cmds

    def test_merge_empty_existing(self, tmp_path, has_jq):
        existing = tmp_path / "existing.json"
        cos = tmp_path / "cos.json"
        output = tmp_path / "merged.json"

        self._write_json(existing, {})

        self._write_json(cos, {
            "hooks": {
                "SessionStart": [{
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/self-install.sh\""}
                    ]
                }]
            }
        })

        _run_merge(str(existing), str(cos), str(output))
        merged = json.loads(output.read_text())

        assert "SessionStart" in merged["hooks"]

    def test_merge_invalid_json_fails(self, tmp_path, has_jq):
        existing = tmp_path / "existing.json"
        cos = tmp_path / "cos.json"
        output = tmp_path / "merged.json"

        existing.write_text("not json")
        self._write_json(cos, {"hooks": {}})

        result = _run_merge(str(existing), str(cos), str(output))
        assert result.returncode != 0


# ── Fresh install tests (no existing config) ──────────────────────────


class TestFreshInstall:
    """When no .claude/ exists, self-install.sh creates everything from scratch."""

    def test_fresh_install_creates_cos_dir(self, tmp_path):
        project = _setup_cos_project(tmp_path)
        # Remove pre-created .claude to simulate fresh
        import shutil
        shutil.rmtree(project / ".claude")

        _run_hook(str(project))

        assert (project / ".claude" / "rules" / "cos").is_dir()
        assert (project / ".claude" / "rules" / "cos" / "trust-score.md").is_symlink()

    def test_fresh_install_no_flat_rules(self, tmp_path):
        project = _setup_cos_project(tmp_path)
        import shutil
        shutil.rmtree(project / ".claude")

        _run_hook(str(project))

        # No flat .md symlinks in .claude/rules/ (only cos/ subdir)
        flat_md = [
            f for f in (project / ".claude" / "rules").iterdir()
            if f.is_file() or (f.is_symlink() and f.suffix == ".md")
        ]
        assert len(flat_md) == 0


# ── Idempotency tests ────────────────────────────────────────────────


class TestIdempotency:
    """Double install/run produces identical results."""

    def test_self_install_idempotent(self, tmp_path):
        project = _setup_cos_project(tmp_path)

        _run_hook(str(project))
        cos_rules_1 = list((project / ".claude" / "rules" / "cos").glob("*.md"))

        r2 = _run_hook(str(project))
        cos_rules_2 = list((project / ".claude" / "rules" / "cos").glob("*.md"))

        # Idempotency: rule count must not change on re-run
        assert len(cos_rules_1) == len(cos_rules_2)
        # No new rules were added on second run (added count should be 0)
        assert "added" not in r2.stdout or "added 0" in r2.stdout

    def test_settings_merge_idempotent(self, tmp_path):
        """Merging the same COS hooks twice doesn't duplicate."""
        has_jq = subprocess.run(["which", "jq"], capture_output=True).returncode == 0
        if not has_jq:
            pytest.skip("jq not installed")

        existing = tmp_path / "settings.json"
        cos = tmp_path / "cos.json"
        output = tmp_path / "merged.json"

        settings = {
            "hooks": {
                "SessionStart": [{
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "bash project-hook.sh"}
                    ]
                }]
            }
        }
        cos_hooks = {
            "hooks": {
                "SessionStart": [{
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/self-install.sh\""},
                        {"type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/hooks/session-init.sh\""}
                    ]
                }]
            }
        }

        existing.write_text(json.dumps(settings))
        cos.write_text(json.dumps(cos_hooks))

        # First merge
        _run_merge(str(existing), str(cos), str(output))
        first = json.loads(output.read_text())

        # Second merge (use first result as existing)
        existing.write_text(json.dumps(first))
        _run_merge(str(existing), str(cos), str(output))
        second = json.loads(output.read_text())

        # Same result
        first_cmds = [h["command"] for h in first["hooks"]["SessionStart"][0]["hooks"]]
        second_cmds = [h["command"] for h in second["hooks"]["SessionStart"][0]["hooks"]]
        assert first_cmds == second_cmds
        assert len(second_cmds) == 3  # 1 project + 2 COS


# ── Rule count in status ──────────────────────────────────────────────


class TestStatusCounts:
    """Status line reflects the namespaced rule count."""

    def test_rule_count_reflects_cos_dir(self, tmp_path):
        project = _setup_cos_project(tmp_path)
        result = _run_hook(str(project))
        # 3 rules in our test setup
        assert "3 rules" in result.stdout
