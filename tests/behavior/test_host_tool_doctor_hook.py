"""Behavior tests for hooks/host-tool-doctor.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.behavior, pytest.mark.timeout(30)]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK = PROJECT_ROOT / "hooks" / "host-tool-doctor.sh"


def _make_source(tmp_path: Path, *, exit_code: int = 0) -> Path:
    source = tmp_path / "cos-source"
    scripts = source / "scripts"
    scripts.mkdir(parents=True)
    doctor = scripts / "cos-doctor-tools.sh"
    doctor.write_text(
        "#!/usr/bin/env bash\n"
        "set -u\n"
        "counter=\"$COS_FAKE_DOCTOR_COUNTER\"\n"
        "count=0\n"
        "[ -f \"$counter\" ] && count=$(cat \"$counter\")\n"
        "count=$((count + 1))\n"
        "printf '%s\\n' \"$count\" > \"$counter\"\n"
        "echo \"fake doctor profile=${2:-missing} project=$COGNITIVE_OS_PROJECT_DIR\"\n"
        f"exit {exit_code}\n"
    )
    doctor.chmod(0o755)
    return source


def _make_project(tmp_path: Path, source: Path) -> Path:
    project = tmp_path / "project"
    (project / ".cognitive-os").mkdir(parents=True)
    (project / ".codex").mkdir()
    (project / ".codex" / "hooks.json").write_text("{}\n")
    (project / ".cognitive-os" / "install-meta.json").write_text(
        json.dumps(
            {
                "source": str(source),
                "harness": "codex",
                "settings_driver": ".codex/hooks.json",
            }
        )
    )
    return project


def _run_hook(project: Path, counter: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "COGNITIVE_OS_HARNESS": "codex",
            "COS_FAKE_DOCTOR_COUNTER": str(counter),
            "COS_HOST_TOOL_DOCTOR_FOREGROUND": "1",
        }
    )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK)],
        cwd=str(project),
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )


def test_session_start_doctor_runs_from_install_metadata_source(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    project = _make_project(tmp_path, source)
    counter = tmp_path / "counter.txt"

    result = _run_hook(project, counter, {"COS_HOST_TOOL_DOCTOR_FORCE": "1"})

    assert result.returncode == 0, result.stderr + result.stdout
    assert counter.read_text().strip() == "1"
    report = project / ".cognitive-os" / "reports" / "host-tools" / "latest.txt"
    state = project / ".cognitive-os" / "runtime" / "host-tool-doctor.state.json"
    assert "fake doctor profile=default" in report.read_text()
    payload = json.loads(state.read_text())
    assert payload["status"] == "pass"
    assert payload["exit_code"] == 0


def test_session_start_doctor_cache_prevents_repeated_runs(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    project = _make_project(tmp_path, source)
    counter = tmp_path / "counter.txt"

    first = _run_hook(project, counter, {"COS_HOST_TOOL_DOCTOR_FORCE": "1"})
    second = _run_hook(project, counter)

    assert first.returncode == 0
    assert second.returncode == 0
    assert counter.read_text().strip() == "1"


def test_session_start_doctor_is_advisory_when_doctor_fails(tmp_path: Path) -> None:
    source = _make_source(tmp_path, exit_code=7)
    project = _make_project(tmp_path, source)
    counter = tmp_path / "counter.txt"

    result = _run_hook(project, counter, {"COS_HOST_TOOL_DOCTOR_FORCE": "1"})

    assert result.returncode == 0, "SessionStart hook must not block startup"
    state = project / ".cognitive-os" / "runtime" / "host-tool-doctor.state.json"
    payload = json.loads(state.read_text())
    assert payload["status"] == "fail"
    assert payload["exit_code"] == 7
