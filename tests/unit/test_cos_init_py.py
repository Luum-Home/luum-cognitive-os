"""Unit tests for scripts/cos_init.py — Phase 2.1 bootstrap.

Covers detect_harness() port from scripts/_lib/settings-driver.sh::cos_detect_harness.
All tests are pure Python (no subprocess) — they test the Python logic in isolation.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure scripts/ is importable without hyphens (snake_case filename per rules/python-naming.md)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import cos_init


class TestDetectHarnessClaude:
    def test_claude_dir_only(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When only .claude/settings.json exists, detect_harness returns 'claude'."""
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{}")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "claude"

    def test_default_is_claude(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When no markers are present and no env vars set, default is 'claude'."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "claude"

    def test_both_dirs_present_defaults_to_claude(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When both .claude/settings.json AND .codex/hooks.json exist, neither
        priority-2 nor priority-3 fires — falls through to default 'claude'."""
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{}")
        (tmp_path / ".codex").mkdir()
        (tmp_path / ".codex" / "hooks.json").write_text("{}")
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "claude"


class TestDetectHarnessCodex:
    def test_codex_dir_only(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """When only .codex/hooks.json exists, detect_harness returns 'codex'."""
        (tmp_path / ".codex").mkdir()
        (tmp_path / ".codex" / "hooks.json").write_text("{}")
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "codex"

    def test_codex_env_project_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CODEX_PROJECT_DIR env var triggers codex detection."""
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.setenv("CODEX_PROJECT_DIR", str(tmp_path))
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "codex"

    def test_codex_env_session_id(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CODEX_SESSION_ID env var triggers codex detection."""
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.setenv("CODEX_SESSION_ID", "sess-abc123")
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "codex"

    def test_codex_env_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """CODEX_HOME env var triggers codex detection."""
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.setenv("CODEX_HOME", "/home/codex")
        assert cos_init.detect_harness(str(tmp_path)) == "codex"


class TestDetectHarnessExplicitOverride:
    def test_env_override_beats_filesystem(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """COGNITIVE_OS_HARNESS env var wins over filesystem markers."""
        # Set up claude markers to confirm env override beats them
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{}")
        monkeypatch.setenv("COGNITIVE_OS_HARNESS", "codex")
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        assert cos_init.detect_harness(str(tmp_path)) == "codex"

    def test_env_override_explicit_claude(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """COGNITIVE_OS_HARNESS=claude works as an explicit override."""
        monkeypatch.setenv("COGNITIVE_OS_HARNESS", "claude")
        assert cos_init.detect_harness(str(tmp_path)) == "claude"
