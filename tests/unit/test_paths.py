"""Unit tests for lib/paths.py::project_root().

Covers the four key requirements stated in the Lote-3 R1 task:
1. CLAUDE_PROJECT_DIR env var honored when set.
2. Fallback behavior when CLAUDE_PROJECT_DIR is absent.
3. Returns a pathlib.Path (not a str).
4. Idempotent (repeated calls return equal values).

See also: TestLibPathsProjectRoot in tests/unit/test_project_dir_resolution.py,
which mirrors Pattern A (the characterisation spec) directly against this module.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)


class TestProjectRootEnvVarHonoring:
    """CLAUDE_PROJECT_DIR is honored when set."""

    def test_claude_project_dir_returned_as_path(self, monkeypatch):
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/explicit/project")
        result = project_root()
        assert result == Path("/explicit/project")

    def test_claude_project_dir_wins_over_cognitive_os(self, monkeypatch):
        """CLAUDE_PROJECT_DIR takes priority over COGNITIVE_OS_PROJECT_DIR."""
        from lib.paths import project_root

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude-wins")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/cognitive-loses")
        result = project_root()
        assert result == Path("/claude-wins")

    def test_claude_project_dir_with_trailing_slash(self, monkeypatch):
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/some/dir/")
        result = project_root()
        # Path normalises trailing slashes
        assert result is not None
        assert str(result).rstrip("/") == "/some/dir"

    def test_claude_project_dir_relative_path(self, monkeypatch):
        """Relative paths are accepted as-is (no absolutisation)."""
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "relative/project")
        result = project_root()
        assert result == Path("relative/project")


class TestProjectRootFallback:
    """Fallback behavior when CLAUDE_PROJECT_DIR is absent or empty."""

    def test_falls_back_to_cognitive_os_when_claude_unset(self, monkeypatch):
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/cognitive-only")
        result = project_root()
        assert result == Path("/cognitive-only")

    def test_falls_back_to_cognitive_os_when_claude_empty(self, monkeypatch):
        """Empty CLAUDE_PROJECT_DIR is falsy — falls through to COGNITIVE_OS."""
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/cognitive-fallback")
        result = project_root()
        assert result == Path("/cognitive-fallback")

    def test_both_unset_returns_none(self, monkeypatch):
        """Both env vars absent → None (signals 'not configured')."""
        from lib.paths import project_root

        _clear_env(monkeypatch)
        assert project_root() is None

    def test_both_empty_returns_none(self, monkeypatch):
        """Both env vars present but empty → None (same as unset)."""
        from lib.paths import project_root

        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "")
        assert project_root() is None

    def test_none_is_falsy(self, monkeypatch):
        """None must be falsy so ``if project_dir:`` gates work correctly."""
        from lib.paths import project_root

        _clear_env(monkeypatch)
        result = project_root()
        assert not result


class TestProjectRootReturnType:
    """Returns a pathlib.Path (not a str) when a project dir is configured."""

    def test_returns_path_instance(self, monkeypatch):
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/typed")
        result = project_root()
        assert isinstance(result, Path), f"Expected pathlib.Path, got {type(result)!r}"

    def test_not_a_string(self, monkeypatch):
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/typed-cog")
        result = project_root()
        assert not isinstance(result, str), "project_root() must not return a str"

    def test_none_when_unset_not_empty_string(self, monkeypatch):
        """When unset, must return None — not '', '.', or Path('')."""
        from lib.paths import project_root

        _clear_env(monkeypatch)
        result = project_root()
        assert result is None, f"Expected None, got {result!r}"


class TestProjectRootIdempotency:
    """Repeated calls with the same env vars return equal values."""

    def test_idempotent_with_claude_set(self, monkeypatch):
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/stable")
        first = project_root()
        second = project_root()
        assert first == second

    def test_idempotent_when_unset(self, monkeypatch):
        from lib.paths import project_root

        _clear_env(monkeypatch)
        first = project_root()
        second = project_root()
        assert first == second  # both None

    def test_idempotent_with_cognitive_os_set(self, monkeypatch):
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/cog-stable")
        assert project_root() == project_root()


class TestProjectRootCallerCompatibility:
    """Callers use ``if project_dir: os.path.join(project_dir, ...)`` — must work."""

    def test_can_use_in_os_path_join(self, monkeypatch):
        """os.path.join accepts Path objects — migration to Path is safe."""
        import os

        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/root")
        result = project_root()
        joined = os.path.join(result, "cognitive-os.yaml")
        assert joined == "/root/cognitive-os.yaml"

    def test_truthiness_gate_works_when_set(self, monkeypatch):
        from lib.paths import project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/gated")
        assert project_root()  # truthy — gate opens

    def test_truthiness_gate_works_when_unset(self, monkeypatch):
        from lib.paths import project_root

        _clear_env(monkeypatch)
        assert not project_root()  # falsy — gate stays closed
