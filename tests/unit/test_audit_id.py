"""Unit tests for lib/audit_id.py."""

import subprocess
from pathlib import Path

import pytest

from lib.audit_id import (
    AuditContext,
    enrich_jsonl_entry,
    get_current_audit_context,
    stamp_active_task,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> Path:
    """Create a minimal git repo so branch detection works."""
    subprocess.run(["git", "init", "-q"], cwd=str(path), check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=str(path), check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=str(path), check=True
    )
    (path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=str(path), check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"], cwd=str(path), check=True
    )
    return path


def _write_sprint_yaml(path: Path, sprint_id: str):
    """Create .cognitive-os/workflows/state/sprint-status.yaml."""
    state_dir = path / ".cognitive-os" / "workflows" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "sprint-status.yaml").write_text(
        f'current_sprint:\n  sprint_id: "{sprint_id}"\n'
    )


def _write_change_file(path: Path, change_id: str):
    """Create .cognitive-os/pipeline-state/current-change.txt."""
    pipeline_dir = path / ".cognitive-os" / "pipeline-state"
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    (pipeline_dir / "current-change.txt").write_text(change_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# B1 -----------------------------------------------------------------------
def test_full_audit_context(tmp_path):
    """AuditContext populated from all sources: session_id, sprint, branch."""
    repo = _init_git_repo(tmp_path)
    _write_sprint_yaml(repo, "2026-w15")

    ctx = get_current_audit_context(str(repo), session_id="sess-123")

    assert ctx.session_id == "sess-123"
    assert ctx.sprint_id == "2026-w15"
    assert ctx.branch != ""  # git branch is detected


# B2 -----------------------------------------------------------------------
def test_enrich_preserves_existing_fields(tmp_path):
    """enrich_jsonl_entry adds audit fields without overwriting existing ones."""
    entry = {"timestamp": "2026-04-10", "agent": "test-agent", "cost": 0.5}
    ctx = AuditContext(
        session_id="sess-1",
        sprint_id="2026-w15",
        change_id="auth-feature",
        branch="main",
    )
    enriched = enrich_jsonl_entry(entry, ctx)

    # Original fields preserved
    assert enriched["timestamp"] == "2026-04-10"
    assert enriched["agent"] == "test-agent"
    assert enriched["cost"] == 0.5

    # Audit fields added
    assert enriched["session_id"] == "sess-1"
    assert enriched["sprint_id"] == "2026-w15"
    assert enriched["change_id"] == "auth-feature"
    assert enriched["branch"] == "main"


# B3 -----------------------------------------------------------------------
def test_no_sprint_returns_empty_sprint_id(tmp_path):
    """Missing sprint-status.yaml yields sprint_id == '' but session_id is still set."""
    repo = _init_git_repo(tmp_path)
    # No sprint yaml written

    ctx = get_current_audit_context(str(repo), session_id="sess-1")

    assert ctx.sprint_id == ""
    assert ctx.session_id == "sess-1"


# Additional tests ---------------------------------------------------------


def test_change_id_read_from_file(tmp_path):
    """change_id comes from current-change.txt when present."""
    repo = _init_git_repo(tmp_path)
    _write_change_file(repo, "my-feature")

    ctx = get_current_audit_context(str(repo), session_id="s1")
    assert ctx.change_id == "my-feature"


def test_change_id_empty_when_file_missing(tmp_path):
    """change_id is '' when current-change.txt is absent."""
    repo = _init_git_repo(tmp_path)

    ctx = get_current_audit_context(str(repo), session_id="s1")
    assert ctx.change_id == ""


def test_enrich_does_not_overwrite_existing_audit_field(tmp_path):
    """If entry already has session_id, enrich_jsonl_entry must not overwrite it."""
    entry = {"session_id": "existing-session", "data": 42}
    ctx = AuditContext("new-session", "w10", "some-change", "feat/branch")
    enriched = enrich_jsonl_entry(entry, ctx)
    assert enriched["session_id"] == "existing-session"


def test_stamp_active_task_adds_audit_timestamp(tmp_path):
    """stamp_active_task adds audit_timestamp alongside audit fields."""
    task = {"id": "task-001", "status": "in_progress"}
    ctx = AuditContext("sess-42", "2026-w20", "my-change", "main")
    stamped = stamp_active_task(task, ctx)

    assert "audit_timestamp" in stamped
    assert stamped["audit_timestamp"]  # non-empty ISO string
    assert stamped["session_id"] == "sess-42"
    assert stamped["id"] == "task-001"  # original field preserved


def test_stamp_active_task_does_not_overwrite_existing_timestamp(tmp_path):
    """stamp_active_task preserves pre-existing audit_timestamp."""
    task = {"id": "t1", "audit_timestamp": "fixed-ts"}
    ctx = AuditContext("s", "w", "c", "b")
    stamped = stamp_active_task(task, ctx)
    assert stamped["audit_timestamp"] == "fixed-ts"


def test_enrich_returns_same_dict_object():
    """enrich_jsonl_entry mutates in place and returns the same object."""
    entry = {"x": 1}
    ctx = AuditContext("s", "w", "c", "b")
    result = enrich_jsonl_entry(entry, ctx)
    assert result is entry


def test_stamp_returns_same_dict_object():
    """stamp_active_task mutates in place and returns the same object."""
    task = {"y": 2}
    ctx = AuditContext("s", "w", "c", "b")
    result = stamp_active_task(task, ctx)
    assert result is task


def test_session_id_from_env(tmp_path, monkeypatch):
    """session_id falls back to COGNITIVE_OS_SESSION_ID env var."""
    repo = _init_git_repo(tmp_path)
    monkeypatch.setenv("COGNITIVE_OS_SESSION_ID", "env-session-99")

    ctx = get_current_audit_context(str(repo))  # no explicit session_id
    assert ctx.session_id == "env-session-99"


def test_explicit_session_id_beats_env(tmp_path, monkeypatch):
    """Explicit session_id parameter takes precedence over env var."""
    repo = _init_git_repo(tmp_path)
    monkeypatch.setenv("COGNITIVE_OS_SESSION_ID", "env-session")

    ctx = get_current_audit_context(str(repo), session_id="explicit-session")
    assert ctx.session_id == "explicit-session"
