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
MEMORY_SCRIPT = PROJECT_ROOT / "scripts" / "cos-doctor-memory-lifecycle.sh"


def _codex_memory_hooks() -> dict:
    def entry(script: str) -> dict:
        return {
            "matcher": "cos",
            "hooks": [
                {
                    "type": "command",
                    "command": f'bash "$CODEX_PROJECT_DIR/.cognitive-os/hooks/cos/{script}"',
                }
            ],
        }

    return {
        "SessionStart": [
            entry("engram-daemon-launcher.sh"),
            entry("session-resume.sh"),
        ],
        "UserPromptSubmit": [entry("user-prompt-capture.sh")],
        "Stop": [
            entry("session-learning.sh"),
            entry("git-context-capture.sh"),
            entry("session-changelog.sh"),
            entry("engram-crystallize-on-session-end.sh"),
        ],
    }


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


def _write_manifest(tmp_path: Path, *, required: list[str] | None = None) -> Path:
    manifest = tmp_path / "dependencies.yaml"
    required = required or []
    tools = [
        {
            "name": name,
            "criticality": "required",
            "check": f"{name} --version",
            "install": {"any": f"install {name}"},
        }
        for name in required
    ]
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "python": {"required": ["pyyaml>=6.0"], "groups": {}},
                "tools": tools,
                "mcp_servers": [],
                "profiles": {
                    "default": {
                        "python_groups": [],
                        "tools_required": required,
                        "tools_recommended": [],
                        "mcp_servers_recommended": [],
                    },
                    "full": {
                        "python_groups": [],
                        "tools_required": required,
                        "tools_recommended": [],
                        "mcp_servers_recommended": [],
                    },
                },
            }
        )
    )
    return manifest


def _codex_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".codex").mkdir()
    (project / ".codex" / "hooks.json").write_text(json.dumps(_codex_memory_hooks()))
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
        "  serve) echo '{\"status\":\"ok\"}'; exit 0 ;;\n"
        "  *) exit 0 ;;\n"
        "esac\n"
    )
    engram.chmod(engram.stat().st_mode | stat.S_IXUSR)
    return bin_dir


def test_codex_project_reports_engram_and_driver_health(tmp_path: Path) -> None:
    project = _codex_project(tmp_path)
    manifest = _write_manifest(tmp_path)
    codex_home = project / "codex-home"
    codex_home.mkdir()
    (codex_home / "config.toml").write_text('[mcp_servers.engram]\ncommand = "engram"\n')
    bin_dir = _fake_engram_bin(tmp_path)

    result = _run(
        project,
        env={
            "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
            "COS_MANIFEST_PATH": str(manifest),
        },
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "PASS active harness is supported: codex" in result.stdout
    assert "PASS settings driver JSON contract is valid" in result.stdout
    assert "PASS dependency manifest loaded for profile: default" in result.stdout
    assert "PASS required tools present" in result.stdout
    assert "PASS engram CLI search works" in result.stdout
    assert "PASS engram MCP stdio starts" in result.stdout
    assert "PASS memory lifecycle doctor passed" in result.stdout


def test_missing_engram_is_warning_unless_strict(tmp_path: Path) -> None:
    project = _codex_project(tmp_path)
    manifest = _write_manifest(tmp_path)
    result = _run(
        project,
        env={"PATH": "/usr/bin:/bin", "COS_MANIFEST_PATH": str(manifest)},
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "WARN engram CLI not found on PATH" in result.stdout

    strict_env = os.environ.copy()
    strict_env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "COGNITIVE_OS_HARNESS": "codex",
            "CODEX_HOME": str(project / "codex-home"),
            "PATH": "/usr/bin:/bin",
            "COS_MANIFEST_PATH": str(manifest),
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


def test_missing_required_manifest_tool_fails_core_check(tmp_path: Path) -> None:
    project = _codex_project(tmp_path)
    manifest = _write_manifest(tmp_path, required=["definitely-missing-cos-tool"])

    result = _run(
        project,
        env={"PATH": "/usr/bin:/bin", "COS_MANIFEST_PATH": str(manifest)},
    )

    assert result.returncode == 1
    assert "FAIL required tools missing: definitely-missing-cos-tool" in result.stdout


def test_memory_lifecycle_doctor_proves_codex_session_without_claude_env(
    tmp_path: Path,
) -> None:
    project = _codex_project(tmp_path)
    bin_dir = _fake_engram_bin(tmp_path)
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.pop("CLAUDE_SESSION_ID", None)
    env.update(
        {
            "COGNITIVE_OS_HARNESS": "codex",
            "CODEX_PROJECT_DIR": str(project),
            "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        }
    )

    result = subprocess.run(
        ["bash", str(MEMORY_SCRIPT), "--harness", "codex"],
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "PASS Engram launcher hook can run for a new codex session" in result.stdout
    assert "PASS session-resume detects and recovers pending tasks" in result.stdout
    assert "PASS session-learning saves session summary metrics" in result.stdout
    assert "PASS session-changelog saves resumable changelog" in result.stdout
    assert "PASS pre-compaction flush emits durable memory reminder" in result.stdout
