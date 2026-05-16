"""Tests for work-queue-sync hook and cos-work-queue CLI.

Three tests:
1. Hook script exists and is executable
2. CLI `list` prints entries from a work-queue.jsonl
3. CLI `mark-done` updates state in the JSONL file
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ── 1. Hook script check ─────────────────────────────────────────────────────

def test_work_queue_sync_hook_exists_and_executable():
    """hooks/work-queue-sync.sh must exist and be executable."""
    hook = PROJECT_ROOT / "hooks" / "work-queue-sync.sh"
    assert hook.exists(), f"Missing hook: {hook}"
    assert os.access(hook, os.X_OK), f"Hook not executable: {hook}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_queue(tmp_path: Path, entries: list[dict]) -> Path:
    """Write a work-queue.jsonl and return tmp_path as project root."""
    queue_dir = tmp_path / ".cognitive-os"
    queue_dir.mkdir(parents=True)
    queue_file = queue_dir / "work-queue.jsonl"
    lines = [json.dumps(e) for e in entries]
    queue_file.write_text("\n".join(lines) + "\n")
    return tmp_path


# ── 2. CLI list ───────────────────────────────────────────────────────────────

def test_cli_list_prints_entries(tmp_path):
    """cos_work_queue.py list must print all entries from work-queue.jsonl."""
    entries = [
        {
            "timestamp": "2026-04-20T10:00:00Z", "epoch": 1000,
            "event": "todo_write", "tool": "TodoWrite",
            "detail": {"todo_count": 3}, "source": "work-queue-sync",
        },
        {
            "timestamp": "2026-04-20T11:00:00Z", "epoch": 2000,
            "event": "agent_completion", "tool": "Agent",
            "detail": {"summary": "fixed bug"}, "source": "work-queue-sync",
        },
    ]
    project_dir = _make_queue(tmp_path, entries)

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "cos_work_queue.py"),
            "--project-dir", str(project_dir),
            "list",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    output = result.stdout
    assert "todo_write" in output
    assert "agent_completion" in output


# ── 3. CLI mark-done ──────────────────────────────────────────────────────────

def test_cli_mark_done_updates_state(tmp_path):
    """cos_work_queue.py mark-done 0 must set done=true on the newest entry."""
    entries = [
        {
            "id": "entry-001",
            "timestamp": "2026-04-20T10:00:00Z", "epoch": 1000,
            "event": "todo_write", "tool": "TodoWrite",
            "detail": {"todo_count": 2}, "source": "work-queue-sync",
        },
    ]
    project_dir = _make_queue(tmp_path, entries)

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "cos_work_queue.py"),
            "--project-dir", str(project_dir),
            "mark-done", "0",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"mark-done failed: {result.stderr}"

    queue_file = project_dir / ".cognitive-os" / "work-queue.jsonl"
    updated = [
        json.loads(line)
        for line in queue_file.read_text().splitlines()
        if line.strip()
    ]
    assert len(updated) == 1
    assert updated[0].get("done") is True
    assert "done_at" in updated[0]
