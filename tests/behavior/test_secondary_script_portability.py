"""Behavior tests for secondary script portability.

These tests cover user-facing support scripts that should follow Cognitive OS
runtime/env contracts even though they are not the primary bootstrap path.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run_script(
    script: Path,
    args: list[str] | None = None,
    *,
    cwd: Path | None = None,
    env_overrides: dict[str, str] | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(script), *(args or [])],
        capture_output=True,
        text=True,
        cwd=str(cwd or PROJECT_ROOT),
        env=env,
        timeout=timeout,
    )


def test_secondary_scripts_have_valid_bash_syntax():
    """Secondary user-facing scripts should stay shell-parseable."""
    scripts = [
        PROJECT_ROOT / "scripts" / "component-lint.sh",
        PROJECT_ROOT / "scripts" / "startup-benchmark.sh",
        PROJECT_ROOT / "scripts" / "benchmark-hooks.sh",
        PROJECT_ROOT / "scripts" / "cos-usage-report.sh",
        PROJECT_ROOT / "scripts" / "cos-sessions.sh",
        PROJECT_ROOT / "scripts" / "engram-sync.sh",
        PROJECT_ROOT / "scripts" / "session-leak-diagnostic.sh",
    ]

    for script in scripts:
        result = subprocess.run(
            ["bash", "-n", str(script)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"{script}: {result.stderr}"


def test_set_security_profile_refuses_non_claude_driver(tmp_path):
    """set-security-profile must not pretend to manage Codex hook settings."""
    project = tmp_path / "project"
    (project / ".codex").mkdir(parents=True)
    (project / ".codex" / "hooks.json").write_text('{"hooks": {}}\n')

    result = _run_script(
        PROJECT_ROOT / "scripts" / "set-security-profile.sh",
        ["minimal"],
        env_overrides={
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "COGNITIVE_OS_HARNESS": "codex",
        },
    )

    assert result.returncode == 1
    assert "Claude settings driver only" in result.stderr
    assert "Active driver: .codex/hooks.json" in result.stderr


def test_cos_sessions_uses_canonical_project_dir(tmp_path):
    """cos-sessions should read metrics from COGNITIVE_OS_PROJECT_DIR first."""
    project = tmp_path / "project"
    metrics = project / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "session-log.jsonl").write_text(
        json.dumps(
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "project": "canonical-project",
                "session_id": "sess-1",
            }
        )
        + "\n"
    )

    result = _run_script(
        PROJECT_ROOT / "scripts" / "cos-sessions.sh",
        ["--json"],
        env_overrides={
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "CODEX_PROJECT_DIR": "",
            "CLAUDE_PROJECT_DIR": "",
        },
    )

    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["count"] == 1
    assert data["sessions"][0]["session_id"] == "sess-1"


def test_benchmark_hooks_reads_codex_settings_driver(tmp_path):
    """benchmark-hooks should use the active Codex settings driver for hook discovery."""
    project = tmp_path / "project"
    hooks_dir = project / ".cognitive-os" / "hooks" / "cos"
    hooks_dir.mkdir(parents=True)
    hook = hooks_dir / "fast-hook.sh"
    hook.write_text("#!/usr/bin/env bash\nexit 0\n")
    hook.chmod(0o755)

    codex_dir = project / ".codex"
    codex_dir.mkdir()
    (codex_dir / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {
                            "matcher": "*",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": f'bash "{hook}"',
                                }
                            ],
                        }
                    ]
                }
            }
        )
    )

    result = _run_script(
        PROJECT_ROOT / "scripts" / "benchmark-hooks.sh",
        ["--warn-ms", "1000", "--fail-ms", "5000"],
        env_overrides={
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "CODEX_PROJECT_DIR": "",
            "CLAUDE_PROJECT_DIR": "",
        },
    )

    assert result.returncode == 0, result.stderr
    assert "Hooks tested:     1" in result.stdout
    assert (project / ".cognitive-os" / "metrics" / "hook-benchmark.json").exists()
