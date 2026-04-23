"""Unit tests for lib/paths.py project and runtime resolvers.

Covers the four key requirements stated in the Lote-3 R1 task:
1. CLAUDE_PROJECT_DIR env var honored when set.
2. Fallback behavior when CLAUDE_PROJECT_DIR is absent.
3. Returns a pathlib.Path (not a str).
4. Idempotent (repeated calls return equal values).

See also: TestLibPathsProjectRoot in tests/unit/test_project_dir_resolution.py,
which mirrors Pattern A (the characterisation spec) directly against the legacy
``project_root()`` helper.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
    monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("COGNITIVE_OS_SESSION_ID", raising=False)
    monkeypatch.delenv("CODEX_SESSION_ID", raising=False)


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


class TestRuntimeProjectRoot:
    """The new canonical runtime precedence is COGNITIVE_OS -> CODEX -> CLAUDE."""

    def test_cognitive_os_wins_over_codex_and_claude(self, monkeypatch):
        from lib.paths import runtime_project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/cognitive-wins")
        monkeypatch.setenv("CODEX_PROJECT_DIR", "/codex-loses")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude-loses")
        assert runtime_project_root() == Path("/cognitive-wins")

    def test_codex_wins_when_cognitive_os_unset(self, monkeypatch):
        from lib.paths import runtime_project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CODEX_PROJECT_DIR", "/codex-wins")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude-loses")
        assert runtime_project_root() == Path("/codex-wins")

    def test_claude_used_as_compatibility_fallback(self, monkeypatch):
        from lib.paths import runtime_project_root

        _clear_env(monkeypatch)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/claude-only")
        assert runtime_project_root() == Path("/claude-only")

    def test_runtime_project_root_or_cwd(self, monkeypatch, tmp_path):
        from lib.paths import runtime_project_root_or_cwd

        _clear_env(monkeypatch)
        monkeypatch.chdir(tmp_path)
        assert runtime_project_root_or_cwd() == tmp_path


class TestRuntimeSessionId:
    """Canonical session resolution is COGNITIVE_OS -> CODEX -> CLAUDE."""

    def test_cognitive_os_session_id_wins(self, monkeypatch):
        from lib.paths import runtime_session_id

        _clear_env(monkeypatch)
        monkeypatch.setenv("COGNITIVE_OS_SESSION_ID", "cos-sess")
        monkeypatch.setenv("CODEX_SESSION_ID", "codex-sess")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "claude-sess")
        assert runtime_session_id() == "cos-sess"

    def test_codex_session_id_is_fallback(self, monkeypatch):
        from lib.paths import runtime_session_id

        _clear_env(monkeypatch)
        monkeypatch.setenv("CODEX_SESSION_ID", "codex-sess")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "claude-sess")
        assert runtime_session_id() == "codex-sess"

    def test_default_returned_when_all_unset(self, monkeypatch):
        from lib.paths import runtime_session_id

        _clear_env(monkeypatch)
        assert runtime_session_id("default-sess") == "default-sess"


class TestArtifactContractPaths:
    """Canonical artifact paths are additive and do not replace projections yet."""

    def test_canonical_skills_dir_uses_runtime_root(self, monkeypatch):
        from lib.paths import canonical_skills_dir

        _clear_env(monkeypatch)
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", "/proj")
        assert canonical_skills_dir() == Path("/proj/.cognitive-os/skills/cos")

    def test_canonical_rules_dir_uses_explicit_root(self):
        from lib.paths import canonical_rules_dir

        assert canonical_rules_dir("/proj") == Path("/proj/.cognitive-os/rules/cos")

    def test_claude_projection_dirs(self):
        from lib.paths import claude_rules_projection_dir, claude_skills_projection_dir

        assert claude_skills_projection_dir("/proj") == Path("/proj/.claude/skills")
        assert claude_rules_projection_dir("/proj") == Path("/proj/.claude/rules/cos")

    def test_skill_lookup_candidates_preserve_current_precedence(self, tmp_path):
        from lib.paths import skill_lookup_candidates

        candidates = skill_lookup_candidates("demo", tmp_path)
        assert candidates[0] == tmp_path / "skills" / "demo" / "SKILL.md"
        assert candidates[-2] == tmp_path / ".claude" / "skills" / "demo" / "SKILL.md"
        assert candidates[-1] == tmp_path / ".cognitive-os" / "skills" / "cos" / "demo" / "SKILL.md"

    def test_canonical_first_skill_lookup_swaps_projection_order(self, tmp_path):
        from lib.paths import canonical_first_skill_lookup_candidates

        candidates = canonical_first_skill_lookup_candidates("demo", tmp_path)
        assert candidates[0] == tmp_path / "skills" / "demo" / "SKILL.md"
        assert candidates[-2] == tmp_path / ".cognitive-os" / "skills" / "cos" / "demo" / "SKILL.md"
        assert candidates[-1] == tmp_path / ".claude" / "skills" / "demo" / "SKILL.md"

    def test_preferred_rules_dirs_are_canonical_first(self, tmp_path):
        from lib.paths import preferred_rules_dirs

        dirs = preferred_rules_dirs(tmp_path)
        assert dirs[0] == tmp_path / ".cognitive-os" / "rules" / "cos"
        assert dirs[1] == tmp_path / ".claude" / "rules" / "cos"
        assert dirs[2] == tmp_path / ".claude" / "rules"
        assert dirs[3] == tmp_path / "rules"
