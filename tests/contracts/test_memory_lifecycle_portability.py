"""Contracts for cross-harness memory lifecycle automation.

The memory loop is part of the product surface: new sessions should recover
state, user prompts should be captured when appropriate, and session shutdown
should persist learnings without treating Claude as the only runtime host.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.contract

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = PROJECT_ROOT / "hooks"

MEMORY_HOOKS_BY_EVENT = {
    "SessionStart": {
        "engram-daemon-launcher.sh",
        "session-resume.sh",
    },
    "UserPromptSubmit": {
        "user-prompt-capture.sh",
    },
    "Stop": {
        "session-learning.sh",
        "git-context-capture.sh",
        "session-changelog.sh",
        "engram-crystallize-on-session-end.sh",
    },
}


def _load_hooks(path: Path) -> dict:
    return json.loads(path.read_text()).get("hooks", json.loads(path.read_text()))


def _commands_for(settings: dict, event: str) -> list[str]:
    return [
        hook["command"]
        for group in settings.get(event, [])
        for hook in group.get("hooks", [])
        if isinstance(hook.get("command"), str)
    ]


def test_codex_projects_memory_hooks_for_every_supported_lifecycle_event() -> None:
    """Codex must auto-load the memory loop on supported hook events."""
    settings = _load_hooks(PROJECT_ROOT / ".codex" / "hooks.json")

    for event, scripts in MEMORY_HOOKS_BY_EVENT.items():
        commands = _commands_for(settings, event)
        for script in scripts:
            assert any(script in command for command in commands), (event, script, commands)


def test_claude_projects_full_memory_lifecycle_including_claude_only_events() -> None:
    """Claude keeps richer event coverage without becoming the canonical center."""
    settings = _load_hooks(PROJECT_ROOT / ".claude" / "settings.json")

    for event, scripts in MEMORY_HOOKS_BY_EVENT.items():
        commands = _commands_for(settings, event)
        for script in scripts:
            assert any(script in command for command in commands), (event, script, commands)

    assert any(
        "pre-compaction-flush.sh" in command
        for command in _commands_for(settings, "PreCompact")
    )
    assert any(
        "engram-reinforce-on-access.sh" in command
        for command in _commands_for(settings, "PostToolUse")
    )


def test_memory_lifecycle_hooks_do_not_require_claude_project_dir() -> None:
    """Portable memory hooks must understand Codex and canonical project envs."""
    scripts = [
        "engram-daemon-launcher.sh",
        "engram-reinforce-on-access.sh",
        "git-context-capture.sh",
        "pre-compaction-flush.sh",
        "session-changelog.sh",
        "session-learning.sh",
        "session-resume.sh",
        "engram-crystallize-on-session-end.sh",
    ]

    for script in scripts:
        content = (HOOKS_DIR / script).read_text()
        assert "CODEX_PROJECT_DIR" in content, script
        assert "COGNITIVE_OS_PROJECT_DIR" in content, script


def test_session_init_bootstraps_project_profile_under_codex_without_claude_env(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "lib").symlink_to(PROJECT_ROOT / "lib")
    (project / "go.mod").write_text("module example.com/profile\n")
    session_dir = project / ".cognitive-os" / "sessions" / "codex-session"
    session_dir.mkdir(parents=True)
    (session_dir / "meta.json").write_text(
        json.dumps(
            {
                "session_id": "codex-session",
                "start_time": "2026-04-29T00:00:00Z",
                "working_directory": str(project),
            }
        )
    )

    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.update(
        {
            "CODEX_PROJECT_DIR": str(project),
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "SESSION_DIR": str(session_dir),
        }
    )

    result = subprocess.run(
        ["python3", str(HOOKS_DIR / "_lib" / "session_init_helper.py")],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        env=env,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    draft_path = project / ".cognitive-os" / "project-profile" / "draft.json"
    assert draft_path.exists()
    draft = json.loads(draft_path.read_text())
    assert any(entry["value"] == "go" for entry in draft["entries"])
    assert str(project) not in json.dumps(draft)


def test_common_project_dir_resolution_prefers_canonical_then_codex_then_claude(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / "canonical"
    codex = tmp_path / "codex"
    claude = tmp_path / "claude"
    for path in (canonical, codex, claude):
        path.mkdir()

    script = (
        "source hooks/_lib/common.sh >/dev/null 2>&1; "
        'printf "%s" "$_PROJECT_DIR"'
    )
    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(canonical),
        "CODEX_PROJECT_DIR": str(codex),
        "CLAUDE_PROJECT_DIR": str(claude),
    }
    result = subprocess.run(
        ["bash", "-lc", script],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == str(canonical)

    env.pop("COGNITIVE_OS_PROJECT_DIR")
    result = subprocess.run(
        ["bash", "-lc", script],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == str(codex)


def test_session_learning_writes_metrics_under_codex_env_without_claude(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    metrics = project / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)

    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.update(
        {
            "CODEX_PROJECT_DIR": str(project),
            "CODEX_SESSION_ID": "codex-session-1",
            "COGNITIVE_OS_SESSION_START": "2026-04-28T00:00:00Z",
        }
    )

    result = subprocess.run(
        ["bash", str(HOOKS_DIR / "session-learning.sh")],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        env=env,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    output = metrics / "session-learnings.jsonl"
    assert output.exists()
    last = json.loads(output.read_text().splitlines()[-1])
    assert last["session_id"] == "codex-session-1"


def test_session_resume_reads_codex_project_tasks_without_claude_env(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    tasks_dir = project / ".cognitive-os" / "tasks"
    tasks_dir.mkdir(parents=True)
    output_file = project / "done.txt"
    tasks_file = tasks_dir / "active-tasks.json"
    tasks_file.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "id": "task-1",
                        "description": "Recovered under Codex",
                        "status": "in_progress",
                        "expectedOutputs": [str(output_file)],
                    }
                ]
            }
        )
    )
    output_file.write_text("done")

    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    env["CODEX_PROJECT_DIR"] = str(project)

    result = subprocess.run(
        ["bash", str(HOOKS_DIR / "session-resume.sh")],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        env=env,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    if shutil.which("jq"):
        tasks = json.loads(tasks_file.read_text())
        assert tasks["tasks"][0]["status"] == "completed"
        assert "auto-marked as completed" in result.stdout


def test_engram_crystallize_logs_under_codex_project_dir_without_claude_env(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    env["CODEX_PROJECT_DIR"] = str(project)
    env["COS_SKIP_ENGRAM_CRYSTALLIZER"] = "1"

    result = subprocess.run(
        ["bash", str(HOOKS_DIR / "engram-crystallize-on-session-end.sh")],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        env=env,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    metrics = project / ".cognitive-os" / "metrics" / "crystallization-events.jsonl"
    assert metrics.exists()
    event = json.loads(metrics.read_text().splitlines()[-1])
    assert event["event"] == "crystallization_session_end"


def test_pre_compaction_flush_accepts_codex_session_directory(
    tmp_path: Path,
) -> None:
    session_dir = tmp_path / "session"
    env = os.environ.copy()
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.pop("CLAUDE_SESSION_DIR", None)
    env.update(
        {
            "CODEX_PROJECT_DIR": str(PROJECT_ROOT),
            "CODEX_SESSION_ID": "codex-compact-1",
            "CODEX_SESSION_DIR": str(session_dir),
        }
    )

    result = subprocess.run(
        ["bash", str(HOOKS_DIR / "pre-compaction-flush.sh")],
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=True,
        env=env,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    assert "mem_session_summary" in result.stdout
    assert "mem_save" in result.stdout
