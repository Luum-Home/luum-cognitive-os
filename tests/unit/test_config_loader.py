"""Tests for lib/config_loader.py — the three public variants.

Covers:
    * find_config_path()         — search-path order (Variant 3)
    * read_top_level_int()       — hot-path regex reader (Variant 1)
    * read_int_from_file()       — single-file helper used by sites 1 & 2
    * load_structured()          — full YAML parse (Variant 2)
    * D2.2 env-var precedence    — COGNITIVE_OS_PROJECT_DIR treated as fallback
                                   (regression test for site-3 bug fixed in Lote 4)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# Make the project's lib/ importable without installing anything.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from lib import config_loader as cl  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ===========================================================================
# Variant 3 — find_config_path()
# ===========================================================================


class TestFindConfigPath:
    """Search-path order for find_config_path()."""

    def test_returns_none_when_no_candidate_exists(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        assert cl.find_config_path() is None

    def test_cwd_yaml_wins_when_no_project_dir_env(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        _write(tmp_path / "cognitive-os.yaml", "x: 1\n")
        assert cl.find_config_path() == "cognitive-os.yaml"

    def test_cognitive_os_dir_used_as_fallback_for_cwd(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        _write(tmp_path / ".cognitive-os" / "cognitive-os.yaml", "x: 1\n")
        result = cl.find_config_path()
        assert result == os.path.join(".cognitive-os", "cognitive-os.yaml")

    def test_runtime_project_dir_takes_precedence_over_cwd(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        _write(tmp_path / "cognitive-os.yaml", "x: 1\n")
        proj = tmp_path / "proj"
        proj_cfg = _write(proj / "cognitive-os.yaml", "x: 2\n")
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(proj))
        assert cl.find_config_path() == str(proj_cfg)

    def test_cognitive_os_project_dir_used_when_claude_unset(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        proj = tmp_path / "proj"
        proj_cfg = _write(proj / "cognitive-os.yaml", "x: 3\n")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(proj))
        assert cl.find_config_path() == str(proj_cfg)

    def test_cognitive_os_project_dir_wins_over_claude_project_dir(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        cp = tmp_path / "cp"
        op = tmp_path / "op"
        _write(cp / "cognitive-os.yaml", "x: claude\n")
        op_cfg = _write(op / "cognitive-os.yaml", "x: cognitive\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(cp))
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(op))
        assert cl.find_config_path() == str(op_cfg)

    def test_codex_project_dir_used_before_claude_project_dir(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        cp = tmp_path / "cp"
        xp = tmp_path / "xp"
        _write(cp / "cognitive-os.yaml", "x: claude\n")
        xp_cfg = _write(xp / "cognitive-os.yaml", "x: codex\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(cp))
        monkeypatch.setenv("CODEX_PROJECT_DIR", str(xp))
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        assert cl.find_config_path() == str(xp_cfg)


# ===========================================================================
# Variant 1 — read_top_level_int() and read_int_from_file()
# ===========================================================================


class TestReadTopLevelInt:
    """Regex hot-path reader — verify all key behaviours."""

    def test_happy_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        cfg = _write(tmp_path / "cognitive-os.yaml", "max_parallel_agents: 8\n")
        assert cl.read_top_level_int("max_parallel_agents", 5, str(cfg)) == 8

    def test_key_missing_returns_default(self, tmp_path):
        cfg = _write(tmp_path / "c.yaml", "project:\n  phase: x\n")
        assert cl.read_top_level_int("max_parallel_agents", 5, str(cfg)) == 5

    def test_no_path_returns_default(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        assert cl.read_top_level_int("max_parallel_agents", 5) == 5

    def test_nonexistent_path_returns_default(self, tmp_path):
        missing = tmp_path / "nope.yaml"
        assert cl.read_top_level_int("max_parallel_agents", 5, str(missing)) == 5

    def test_nested_key_still_matches_first(self, tmp_path):
        # Documents first-match-wins divergence from YAML semantics.
        cfg = _write(
            tmp_path / "c.yaml",
            "resources:\n  compute:\n    max_parallel_agents: 7\n",
        )
        assert cl.read_top_level_int("max_parallel_agents", 5, str(cfg)) == 7

    def test_inline_comment_tolerated(self, tmp_path):
        cfg = _write(
            tmp_path / "c.yaml",
            "max_parallel_agents: 10  # cap for laptops\n",
        )
        assert cl.read_top_level_int("max_parallel_agents", 5, str(cfg)) == 10

    def test_empty_file_returns_default(self, tmp_path):
        cfg = _write(tmp_path / "c.yaml", "")
        assert cl.read_top_level_int("max_parallel_agents", 5, str(cfg)) == 5

    def test_zero_is_returned_not_coerced_to_default(self, tmp_path):
        cfg = _write(tmp_path / "c.yaml", "max_parallel_agents: 0\n")
        assert cl.read_top_level_int("max_parallel_agents", 5, str(cfg)) == 0

    def test_indented_key_matches(self, tmp_path):
        cfg = _write(tmp_path / "c.yaml", "      max_parallel_agents: 4\n")
        assert cl.read_top_level_int("max_parallel_agents", 5, str(cfg)) == 4

    def test_custom_key_and_default(self, tmp_path):
        cfg = _write(tmp_path / "c.yaml", "agent_timeout_seconds: 600\n")
        assert cl.read_top_level_int("agent_timeout_seconds", 300, str(cfg)) == 600


class TestReadIntFromFile:
    """Single-file helper — returns None when key is absent."""

    def test_returns_value_when_key_present(self, tmp_path):
        cfg = _write(tmp_path / "c.yaml", "max_parallel_agents: 12\n")
        assert cl.read_int_from_file("max_parallel_agents", str(cfg)) == 12

    def test_returns_none_when_key_absent(self, tmp_path):
        cfg = _write(tmp_path / "c.yaml", "project:\n  phase: x\n")
        assert cl.read_int_from_file("max_parallel_agents", str(cfg)) is None

    def test_returns_none_for_nonexistent_file(self, tmp_path):
        missing = tmp_path / "nope.yaml"
        assert cl.read_int_from_file("max_parallel_agents", str(missing)) is None

    def test_returns_zero_not_none_for_zero_value(self, tmp_path):
        cfg = _write(tmp_path / "c.yaml", "max_parallel_agents: 0\n")
        assert cl.read_int_from_file("max_parallel_agents", str(cfg)) == 0


# ===========================================================================
# Variant 2 — load_structured()
# ===========================================================================


class TestLoadStructured:
    """Full YAML parse — basic contracts."""

    def test_returns_dict_for_valid_yaml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        cfg = _write(
            tmp_path / "cognitive-os.yaml",
            "resources:\n  compute:\n    max_parallel_agents: 9\n",
        )
        result = cl.load_structured(str(cfg))
        assert result["resources"]["compute"]["max_parallel_agents"] == 9

    def test_empty_file_returns_empty_dict(self, tmp_path):
        cfg = _write(tmp_path / "c.yaml", "")
        assert cl.load_structured(str(cfg)) == {}

    def test_missing_file_returns_empty_dict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        assert cl.load_structured() == {}

    def test_nonexistent_explicit_path_returns_empty_dict(self, tmp_path):
        missing = tmp_path / "nope.yaml"
        assert cl.load_structured(str(missing)) == {}

    def test_raises_yaml_error_for_malformed_yaml(self, tmp_path):
        """Malformed YAML propagates to the caller (not silently swallowed).

        This contract exists so that dispatch_gate_check.py's except-block
        can record the error in result["error"] — a locked behavior from the
        characterisation tests (TestDispatchGateCheckYaml.test_malformed_yaml_records_error_and_keeps_default).
        """
        import yaml  # noqa: PLC0415

        cfg = _write(
            tmp_path / "c.yaml",
            "resources:\n  compute:\n    max_parallel_agents: [unclosed\n",
        )
        with pytest.raises(yaml.YAMLError):
            cl.load_structured(str(cfg))

    def test_inline_comment_stripped(self, tmp_path):
        cfg = _write(
            tmp_path / "c.yaml",
            "max_parallel_agents: 6  # six is enough\n",
        )
        result = cl.load_structured(str(cfg))
        assert result["max_parallel_agents"] == 6

    def test_nested_key_requires_exact_path(self, tmp_path):
        # Unlike the regex reader, load_structured requires the full nested
        # path (resources.compute.max_parallel_agents), not a top-level match.
        cfg = _write(tmp_path / "c.yaml", "max_parallel_agents: 17\n")
        result = cl.load_structured(str(cfg))
        # top-level key IS present in the dict
        assert result.get("max_parallel_agents") == 17
        # but the nested path resources.compute is absent
        assert result.get("resources", {}).get("compute", {}).get(
            "max_parallel_agents", 5
        ) == 5


# ===========================================================================
# D2.2 Regression — env-var precedence (site-3 bug fixed in Lote 4)
# ===========================================================================


class TestEnvVarPrecedence:
    """Verify canonical runtime project-root precedence for config loading.

    The config loader now uses the cross-harness runtime precedence:
    COGNITIVE_OS_PROJECT_DIR -> CODEX_PROJECT_DIR -> CLAUDE_PROJECT_DIR -> cwd.
    """

    def test_cognitive_os_project_dir_finds_config_when_claude_unset(
        self, tmp_path, monkeypatch
    ):
        """COGNITIVE_OS_PROJECT_DIR is used to locate the YAML file."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        proj = tmp_path / "proj"
        _write(proj / "cognitive-os.yaml", "max_parallel_agents: 42\n")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(proj))

        # find_config_path should locate the file via COGNITIVE_OS_PROJECT_DIR
        path = cl.find_config_path()
        assert path is not None
        assert "42" in Path(path).read_text()

    def test_cognitive_os_project_dir_value_read_when_claude_unset(
        self, tmp_path, monkeypatch
    ):
        """Value from COGNITIVE_OS_PROJECT_DIR beats the cwd fallback."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        # cwd has a config with value 5 (the default)
        _write(tmp_path / "cognitive-os.yaml", "max_parallel_agents: 5\n")

        # project dir (via COGNITIVE_OS) has value 99
        proj = tmp_path / "proj"
        _write(proj / "cognitive-os.yaml", "max_parallel_agents: 99\n")
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(proj))

        # find_config_path returns the project-dir file (inserted at index 0)
        result = cl.read_top_level_int("max_parallel_agents", 5)
        assert result == 99, (
            "COGNITIVE_OS_PROJECT_DIR must win over cwd cognitive-os.yaml "
            "(D2.2 regression: env var precedence fix)"
        )

    def test_codex_project_dir_is_used_when_cognitive_os_unset(
        self, tmp_path, monkeypatch
    ):
        """CODEX_PROJECT_DIR is used before the Claude compatibility fallback."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        proj = tmp_path / "proj"
        _write(proj / "cognitive-os.yaml", "max_parallel_agents: 88\n")
        monkeypatch.setenv("CODEX_PROJECT_DIR", str(proj))

        result = cl.read_top_level_int("max_parallel_agents", 5)
        assert result == 88

    def test_cognitive_os_project_dir_beats_codex_and_claude(
        self, tmp_path, monkeypatch
    ):
        """COGNITIVE_OS_PROJECT_DIR is the canonical runtime winner."""
        monkeypatch.chdir(tmp_path)
        cp = tmp_path / "claude"
        xp = tmp_path / "codex"
        op = tmp_path / "cos"
        _write(cp / "cognitive-os.yaml", "max_parallel_agents: 11\n")
        _write(xp / "cognitive-os.yaml", "max_parallel_agents: 22\n")
        _write(op / "cognitive-os.yaml", "max_parallel_agents: 33\n")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(cp))
        monkeypatch.setenv("CODEX_PROJECT_DIR", str(xp))
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(op))

        result = cl.read_top_level_int("max_parallel_agents", 5)
        assert result == 33

    def test_both_env_vars_absent_falls_back_to_cwd(
        self, tmp_path, monkeypatch
    ):
        """When both env vars are unset, cwd cognitive-os.yaml is used."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("COGNITIVE_OS_PROJECT_DIR", raising=False)
        _write(tmp_path / "cognitive-os.yaml", "max_parallel_agents: 7\n")

        result = cl.read_top_level_int("max_parallel_agents", 5)
        assert result == 7
