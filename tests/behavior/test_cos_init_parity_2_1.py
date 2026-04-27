"""Phase 2.1 parity test — Python detect_harness() must match bash cos_detect_harness output.

These tests call the Python module via --internal-call (the same path the bash shim uses)
and compare the result to a direct bash invocation of cos_detect_harness from settings-driver.sh.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.parent
COS_INIT_PY = REPO / "scripts" / "cos_init.py"
SETTINGS_DRIVER = REPO / "scripts" / "_lib" / "settings-driver.sh"


def _py_detect(project_root: Path, env: dict | None = None) -> str:
    """Call Python detect_harness via --internal-call dispatcher."""
    result = subprocess.run(
        ["python3", str(COS_INIT_PY), "--internal-call", "detect_harness", str(project_root)],
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def _bash_detect(project_root: Path, env: dict | None = None) -> str:
    """Call bash cos_detect_harness directly from settings-driver.sh."""
    script = (
        f"source {SETTINGS_DRIVER} && cos_detect_harness {project_root}"
    )
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all harness-detection env vars."""
    for var in ("COGNITIVE_OS_HARNESS", "CODEX_PROJECT_DIR", "CODEX_SESSION_ID", "CODEX_HOME"):
        monkeypatch.delenv(var, raising=False)


class TestParityDetectHarness:
    def test_parity_claude_only(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Python and bash agree when only .claude/settings.json exists."""
        _clean_env(monkeypatch)
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{}")
        py = _py_detect(tmp_path)
        bash = _bash_detect(tmp_path)
        assert py == bash, f"Parity failure: Python={py!r} Bash={bash!r}"
        assert py == "claude"

    def test_parity_codex_only(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Python and bash agree when only .codex/hooks.json exists."""
        _clean_env(monkeypatch)
        (tmp_path / ".codex").mkdir()
        (tmp_path / ".codex" / "hooks.json").write_text("{}")
        py = _py_detect(tmp_path)
        bash = _bash_detect(tmp_path)
        assert py == bash, f"Parity failure: Python={py!r} Bash={bash!r}"
        assert py == "codex"

    def test_parity_neither_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Python and bash agree when no harness markers exist (default)."""
        _clean_env(monkeypatch)
        py = _py_detect(tmp_path)
        bash = _bash_detect(tmp_path)
        assert py == bash, f"Parity failure: Python={py!r} Bash={bash!r}"

    def test_parity_explicit_env_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Python and bash agree when COGNITIVE_OS_HARNESS is set explicitly."""
        monkeypatch.setenv("COGNITIVE_OS_HARNESS", "codex")
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        monkeypatch.delenv("CODEX_HOME", raising=False)
        import os
        env = os.environ.copy()
        py = _py_detect(tmp_path, env=env)
        bash = _bash_detect(tmp_path, env=env)
        assert py == bash, f"Parity failure: Python={py!r} Bash={bash!r}"
        assert py == "codex"

    def test_parity_both_dirs_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Python and bash agree when both .claude and .codex markers exist."""
        _clean_env(monkeypatch)
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{}")
        (tmp_path / ".codex").mkdir()
        (tmp_path / ".codex" / "hooks.json").write_text("{}")
        py = _py_detect(tmp_path)
        bash = _bash_detect(tmp_path)
        assert py == bash, f"Parity failure: Python={py!r} Bash={bash!r}"
