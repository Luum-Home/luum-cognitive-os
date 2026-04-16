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
    (rules_dir / "content-policy.md").write_text("# Cost Tracking\n")
    (rules_dir / "model-routing.md").write_text("# License Policy\n")

    (tmp_path / ".claude").mkdir(parents=True)
    (tmp_path / ".claude" / "settings.json").write_text('{"hooks": {}}\n')
    (tmp_path / "cognitive-os.yaml").write_text("version: 1\n")

    return tmp_path


# ── Self-install rule namespacing tests ──────────────────────────────


class TestRuleNamespacing:
    """COS rules go to .claude/rules/cos/, not .claude/rules/."""


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


class TestMigrationFromFlatSymlinks:
    """Old flat symlinks in .claude/rules/ pointing to rules/ are cleaned up."""


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


