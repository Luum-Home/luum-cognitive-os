"""Behavior tests for scripts/cos-doctor-tools.sh."""
from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "cos-doctor-tools.sh"


def _run(project: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    merged.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "COGNITIVE_OS_HARNESS": "codex",
            "CODEX_HOME": str(project / "codex-home"),
        }
    )
    if env:
        merged.update(env)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=str(PROJECT_ROOT),
        env=merged,
        text=True,
        capture_output=True,
        timeout=20,
    )


def _codex_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".codex").mkdir()
    (project / ".codex" / "hooks.json").write_text(
        json.dumps(
            {
                "SessionStart": [
                    {
                        "matcher": "startup",
                        "hooks": [{"type": "command", "command": "true"}],
                    }
                ]
            }
        )
    )
    return project


def _fake_engram_bin(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    engram = bin_dir / "engram"
    engram.write_text(
        "#!/usr/bin/env bash\n"
        "case \"${1:-}\" in\n"
        "  search) echo 'Found 1 memories'; exit 0 ;;\n"
        "  mcp) exit 0 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n"
    )
    engram.chmod(engram.stat().st_mode | stat.S_IXUSR)
    return bin_dir


def test_codex_project_reports_engram_and_driver_health(tmp_path: Path) -> None:
    project = _codex_project(tmp_path)
    codex_home = project / "codex-home"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text('[mcp_servers.engram]\ncommand = "engram"\n')
    bin_dir = _fake_engram_bin(tmp_path)

    result = _run(project, env={"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"})

    assert result.returncode == 0, result.stderr + result.stdout
    assert "PASS active harness is supported: codex" in result.stdout
    assert "PASS settings driver JSON contract is valid" in result.stdout
    assert "PASS engram CLI search works" in result.stdout
    assert "PASS engram MCP stdio starts" in result.stdout


def test_missing_engram_is_warning_unless_strict(tmp_path: Path) -> None:
    project = _codex_project(tmp_path)
    result = _run(project, env={"PATH": "/usr/bin:/bin"})

    assert result.returncode == 0, result.stderr + result.stdout
    assert "WARN engram CLI not found on PATH" in result.stdout

    strict_env = os.environ.copy()
    strict_env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "COGNITIVE_OS_HARNESS": "codex",
            "CODEX_HOME": str(project / "codex-home"),
            "PATH": "/usr/bin:/bin",
        }
    )
    strict = subprocess.run(
        ["bash", str(SCRIPT), "--strict"],
        cwd=str(PROJECT_ROOT),
        env=strict_env,
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert strict.returncode == 1
    assert "Result: FAIL" in strict.stdout
