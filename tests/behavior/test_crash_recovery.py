"""Behavior tests for crash recovery system.

Validates that hooks exist, are valid bash, are registered in settings,
rule exists, documentation exists, and checkpoint directory is created.

Run with: pytest tests/behavior/test_crash_recovery.py -v

Author: luum
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Hook existsnce and validity
# ---------------------------------------------------------------------------


class TestAutoCheckpointHook:


    def test_hook_is_valid_bash(self):
        """auto-checkpoint.sh is valid bash syntax."""
        hook_path = PROJECT_ROOT / "hooks" / "auto-checkpoint.sh"
        result = subprocess.run(
            ["bash", "-n", str(hook_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Bash syntax error: {result.stderr}"

    def test_hook_has_shebang(self):
        """auto-checkpoint.sh starts with bash shebang."""
        hook_path = PROJECT_ROOT / "hooks" / "auto-checkpoint.sh"
        content = hook_path.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Missing bash shebang"

    def test_hook_exits_cleanly_outside_git(self, tmp_path):
        """auto-checkpoint.sh exits 0 when not in a git repo."""
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
        result = subprocess.run(
            ["bash", str(PROJECT_ROOT / "hooks" / "auto-checkpoint.sh")],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert result.returncode == 0


class TestCrashRecoveryHook:


    def test_hook_is_valid_bash(self):
        """crash-recovery.sh is valid bash syntax."""
        hook_path = PROJECT_ROOT / "hooks" / "crash-recovery.sh"
        result = subprocess.run(
            ["bash", "-n", str(hook_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Bash syntax error: {result.stderr}"

    def test_hook_has_shebang(self):
        """crash-recovery.sh starts with bash shebang."""
        hook_path = PROJECT_ROOT / "hooks" / "crash-recovery.sh"
        content = hook_path.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Missing bash shebang"

    def test_hook_exits_cleanly_no_stashes(self, tmp_path):
        """crash-recovery.sh exits 0 when no cos- stashes exist."""
        # Init a git repo with no stashes
        subprocess.run(
            ["git", "init", "-q"],
            cwd=str(tmp_path),
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(tmp_path),
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(tmp_path),
            capture_output=True,
        )
        (tmp_path / "README.md").write_text("# test\n")
        subprocess.run(
            ["git", "add", "."],
            cwd=str(tmp_path),
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "init", "-q"],
            cwd=str(tmp_path),
            capture_output=True,
        )

        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
        result = subprocess.run(
            ["bash", str(PROJECT_ROOT / "hooks" / "crash-recovery.sh")],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Rule and documentation existence
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Settings integration
# ---------------------------------------------------------------------------


class TestHooksRegistered:

    def test_auto_checkpoint_in_settings(self):
        """auto-checkpoint.sh is registered in .claude/settings.json."""
        settings_path = PROJECT_ROOT / ".claude" / "settings.json"
        assert settings_path.exists(), ".claude/settings.json does not exist"

        with open(settings_path) as f:
            settings = json.load(f)

        # Check PostToolUse hooks
        post_hooks = settings.get("hooks", {}).get("PostToolUse", [])
        found = False
        for group in post_hooks:
            matcher = group.get("matcher", "")
            if "Bash" in matcher or "Edit" in matcher or "Write" in matcher:
                for hook in group.get("hooks", []):
                    cmd = hook.get("command", "")
                    if "auto-checkpoint.sh" in cmd:
                        found = True
                        break
        assert found, "auto-checkpoint.sh not registered in PostToolUse"

    def test_crash_recovery_in_settings(self):
        """crash-recovery.sh is registered in .claude/settings.json."""
        settings_path = PROJECT_ROOT / ".claude" / "settings.json"
        with open(settings_path) as f:
            settings = json.load(f)

        # Check SessionStart hooks
        start_hooks = settings.get("hooks", {}).get("SessionStart", [])
        found = False
        for group in start_hooks:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                if "crash-recovery.sh" in cmd:
                    found = True
                    break
        assert found, "crash-recovery.sh not registered in SessionStart"


# ---------------------------------------------------------------------------
# Checkpoint directory
# ---------------------------------------------------------------------------


class TestCheckpointDirectory:

    def test_checkpoint_dir_created_on_use(self, tmp_path):
        """CheckpointManager creates checkpoint dir when needed."""
        from lib.checkpoint_manager import CheckpointManager

        mgr = CheckpointManager(
            checkpoint_dir=".cognitive-os/checkpoints",
            project_dir=str(tmp_path),
        )
        # Init git repo
        subprocess.run(
            ["git", "init", "-q"],
            cwd=str(tmp_path),
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(tmp_path),
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(tmp_path),
            capture_output=True,
        )
        (tmp_path / "f.txt").write_text("x\n")
        subprocess.run(
            ["git", "add", "."],
            cwd=str(tmp_path),
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "init", "-q"],
            cwd=str(tmp_path),
            capture_output=True,
        )

        cp_dir = tmp_path / ".cognitive-os" / "checkpoints"
        assert not cp_dir.exists()

        mgr.create_checkpoint(note="test")
        assert cp_dir.exists()
