"""Unit tests for lib/stash_ops.py — ADR-117 invariants.

Tests use a real git repo in a tmpdir so git commands execute correctly.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Ensure the package lib is importable
_LIB = Path(__file__).resolve().parent.parent.parent / "packages" / "agent-coordination" / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import stash_ops


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _init_git_repo(path: Path, session_id: str = "test-session") -> None:
    """Initialise a minimal git repo with one commit in path."""
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(path), check=True, capture_output=True)
    # Initial commit so stash can operate
    (path / "README.md").write_text("init\n")
    subprocess.run(["git", "add", "."], cwd=str(path), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(path), check=True, capture_output=True)


def _dirty(path: Path, filename: str = "dirty.txt") -> None:
    """Create an untracked + modified file so git stash has something to save."""
    (path / filename).write_text("dirty\n")
    subprocess.run(["git", "add", filename], cwd=str(path), check=True, capture_output=True)
    # Modify after staging so there is a staged change
    (path / filename).write_text("dirtier\n")


def _read_ops_jsonl(project_dir: Path) -> list[dict]:
    ops_file = project_dir / ".cognitive-os" / "metrics" / "stash-ops.jsonl"
    if not ops_file.exists():
        return []
    records = []
    for line in ops_file.read_text().splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def git_repo(tmp_path: Path):
    """A fresh git repo at tmp_path/repo."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    old_env = {}
    for var in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR", "COS_SESSION_ID"):
        old_env[var] = os.environ.get(var)
    os.environ["COGNITIVE_OS_PROJECT_DIR"] = str(repo)
    os.environ["COS_SESSION_ID"] = "test-session-abc"
    yield repo
    for var, val in old_env.items():
        if val is None:
            os.environ.pop(var, None)
        else:
            os.environ[var] = val


# ---------------------------------------------------------------------------
# Test: Invariant 1 — Named stashes with correct prefix
# ---------------------------------------------------------------------------

class TestPushNamed:
    def test_label_contains_session_hook_epoch(self, git_repo: Path):
        _dirty(git_repo)
        ref = stash_ops.push_named("my-change", hook="test-hook", project_dir=git_repo)
        # Ref must contain session:hook
        assert "test-session-abc" in ref or "test-session-abc" in _get_stash_message(git_repo, ref)

    def test_label_format_in_stash_list(self, git_repo: Path):
        _dirty(git_repo)
        stash_ops.push_named("payload", hook="pre-agent", project_dir=git_repo)
        result = subprocess.run(["git", "stash", "list"], cwd=str(git_repo), capture_output=True, text=True)
        assert "test-session-abc" in result.stdout
        assert "pre-agent" in result.stdout

    def test_returns_stash_ref_string(self, git_repo: Path):
        _dirty(git_repo)
        ref = stash_ops.push_named("x", hook="h", project_dir=git_repo)
        assert ref  # non-empty

    def test_stash_labels_are_unique_across_pushes(self, git_repo: Path):
        """Each push must produce a unique label (epoch+uuid guarantees this)."""
        _dirty(git_repo, "file1.txt")
        stash_ops.push_named("msg", hook="h", project_dir=git_repo)

        # Re-dirty to push a second stash
        _dirty(git_repo, "file2.txt")
        stash_ops.push_named("msg", hook="h", project_dir=git_repo)

        # List all stash messages — the two labels must differ
        result = subprocess.run(
            ["git", "stash", "list"], cwd=str(git_repo), capture_output=True, text=True
        )
        lines = result.stdout.splitlines()
        assert len(lines) == 2
        # Extract the label fragments (after last ": ")
        labels = [_extract_label_from_list(line) for line in lines]
        assert labels[0] != labels[1], f"Labels must be unique, got: {labels}"


# ---------------------------------------------------------------------------
# Test: Invariant 3 — audit_append writes exact ADR-117 schema
# ---------------------------------------------------------------------------

class TestAuditAppend:
    def test_exact_schema_fields(self, git_repo: Path):
        stash_ops.audit_append("my-hook", "my-stash-label", "push", "ok", project_dir=git_repo)
        records = _read_ops_jsonl(git_repo)
        assert len(records) == 1
        r = records[0]
        assert set(r.keys()) >= {"ts", "hook", "name", "action", "status"}

    def test_field_values(self, git_repo: Path):
        stash_ops.audit_append("hook-x", "label-y", "apply", "fail", project_dir=git_repo)
        records = _read_ops_jsonl(git_repo)
        r = records[-1]
        assert r["hook"] == "hook-x"
        assert r["name"] == "label-y"
        assert r["action"] == "apply"
        assert r["status"] == "fail"

    def test_ts_is_iso8601(self, git_repo: Path):
        stash_ops.audit_append("h", "n", "drop", "ok", project_dir=git_repo)
        records = _read_ops_jsonl(git_repo)
        ts = records[-1]["ts"]
        # Must be parseable as ISO-8601 (ends with Z)
        assert "T" in ts and (ts.endswith("Z") or "+" in ts)

    def test_multiple_appends_are_cumulative(self, git_repo: Path):
        stash_ops.audit_append("h", "n1", "push", "ok", project_dir=git_repo)
        stash_ops.audit_append("h", "n2", "apply", "ok", project_dir=git_repo)
        stash_ops.audit_append("h", "n3", "drop", "ok", project_dir=git_repo)
        records = _read_ops_jsonl(git_repo)
        assert len(records) == 3
        actions = [r["action"] for r in records]
        assert actions == ["push", "apply", "drop"]

    def test_extra_fields_included(self, git_repo: Path):
        stash_ops.audit_append("h", "n", "push", "ok", {"reason": "test"}, project_dir=git_repo)
        records = _read_ops_jsonl(git_repo)
        assert records[-1].get("reason") == "test"


# ---------------------------------------------------------------------------
# Test: Invariant 4 — budget_check
# ---------------------------------------------------------------------------

class TestBudgetCheck:
    def test_within_budget_when_empty(self, git_repo: Path):
        within, count = stash_ops.budget_check("test-session-abc", project_dir=git_repo)
        assert within is True
        assert count == 0

    def test_within_budget_below_limit(self, git_repo: Path):
        # Push 4 stashes (below limit of 5)
        for i in range(4):
            _dirty(git_repo, f"file{i}.txt")
            stash_ops.push_named(f"msg{i}", hook="h", project_dir=git_repo)

        within, count = stash_ops.budget_check("test-session-abc", project_dir=git_repo)
        assert within is True
        assert count == 4

    def test_budget_exceeded_at_5(self, git_repo: Path):
        # Push 5 stashes — budget is exhausted
        for i in range(5):
            _dirty(git_repo, f"file{i}.txt")
            stash_ops.push_named(f"msg{i}", hook="h", budget_check=False, project_dir=git_repo)

        within, count = stash_ops.budget_check("test-session-abc", project_dir=git_repo)
        assert within is False
        assert count >= 5

    def test_push_raises_when_budget_exceeded(self, git_repo: Path):
        for i in range(5):
            _dirty(git_repo, f"file{i}.txt")
            stash_ops.push_named(f"msg{i}", hook="h", budget_check=False, project_dir=git_repo)

        _dirty(git_repo, "overflow.txt")
        with pytest.raises(RuntimeError, match="budget exhausted"):
            stash_ops.push_named("overflow", hook="h", budget_check=True, project_dir=git_repo)

    def test_budget_warn_logged_on_exceed(self, git_repo: Path):
        for i in range(5):
            _dirty(git_repo, f"file{i}.txt")
            stash_ops.push_named(f"msg{i}", hook="h", budget_check=False, project_dir=git_repo)

        _dirty(git_repo, "overflow.txt")
        try:
            stash_ops.push_named("overflow", hook="budget-hook", budget_check=True, project_dir=git_repo)
        except RuntimeError:
            pass

        records = _read_ops_jsonl(git_repo)
        actions = [r["action"] for r in records]
        assert "budget-warn" in actions


# ---------------------------------------------------------------------------
# Test: Invariant 2 — apply_by_name NEVER uses pop
# ---------------------------------------------------------------------------

class TestApplyByName:
    def test_apply_resolves_and_succeeds(self, git_repo: Path):
        _dirty(git_repo)
        stash_ops.push_named("apply-test", hook="h", project_dir=git_repo)
        # Confirm stash exists
        result = subprocess.run(["git", "stash", "list"], cwd=str(git_repo), capture_output=True, text=True)
        assert result.stdout.strip()

        # Apply by the full label (what was embedded in stash message)
        # The label contains session:hook:epoch-uuid
        stash_list = result.stdout
        # Extract the label from the stash list
        label = _extract_label_from_list(stash_list)
        ok = stash_ops.apply_by_name(label, hook="post-h", project_dir=git_repo)
        assert ok is True

    def test_apply_logs_action(self, git_repo: Path):
        _dirty(git_repo)
        stash_ops.push_named("x", hook="h", project_dir=git_repo)

        result = subprocess.run(["git", "stash", "list"], cwd=str(git_repo), capture_output=True, text=True)
        label = _extract_label_from_list(result.stdout)
        stash_ops.apply_by_name(label, hook="post-h", project_dir=git_repo)

        records = _read_ops_jsonl(git_repo)
        apply_records = [r for r in records if r["action"] == "apply"]
        assert apply_records

    def test_apply_returns_false_for_missing_stash(self, git_repo: Path):
        ok = stash_ops.apply_by_name("nonexistent-label-xyz", hook="h", project_dir=git_repo)
        assert ok is False

    def test_apply_missing_stash_logs_skip(self, git_repo: Path):
        stash_ops.apply_by_name("nonexistent-label-xyz", hook="h", project_dir=git_repo)
        records = _read_ops_jsonl(git_repo)
        skip_records = [r for r in records if r["action"] == "apply" and r["status"] == "skip"]
        assert skip_records

    def test_stash_survives_failed_apply(self, git_repo: Path):
        """Stash entry must survive if apply fails (apply-by-name, not pop)."""
        _dirty(git_repo)
        stash_ops.push_named("survive-test", hook="h", project_dir=git_repo)

        # Create a conflict: create a conflicting uncommitted change
        (git_repo / "dirty.txt").write_text("conflict\n")
        subprocess.run(["git", "add", "dirty.txt"], cwd=str(git_repo), capture_output=True)

        result = subprocess.run(["git", "stash", "list"], cwd=str(git_repo), capture_output=True, text=True)
        label = _extract_label_from_list(result.stdout)
        # Apply may fail due to conflict
        stash_ops.apply_by_name(label, hook="post-h", project_dir=git_repo)

        # Stash must STILL be present (not dropped by pop)
        result2 = subprocess.run(["git", "stash", "list"], cwd=str(git_repo), capture_output=True, text=True)
        # stash entry is preserved regardless of apply outcome
        assert label in result2.stdout or result2.stdout.strip()


# ---------------------------------------------------------------------------
# Test: E2E — push → apply → drop, verify 3 JSONL records
# ---------------------------------------------------------------------------

class TestEndToEnd:
    def test_push_apply_drop_produces_three_records(self, git_repo: Path):
        # Push
        _dirty(git_repo)
        stash_ops.push_named("e2e-test", hook="e2e-hook", project_dir=git_repo)

        # Get the stash label for apply/drop
        result = subprocess.run(["git", "stash", "list"], cwd=str(git_repo), capture_output=True, text=True)
        label = _extract_label_from_list(result.stdout)

        # Apply
        ok = stash_ops.apply_by_name(label, hook="e2e-hook", project_dir=git_repo)
        assert ok is True

        # Drop — resolve the actual ref
        result2 = subprocess.run(["git", "stash", "list"], cwd=str(git_repo), capture_output=True, text=True)
        # After apply (not pop), stash still exists
        if result2.stdout.strip():
            actual_ref = result2.stdout.splitlines()[0].split(":")[0].strip()
            stash_ops.drop_by_ref(actual_ref, hook="e2e-hook", project_dir=git_repo)

        records = _read_ops_jsonl(git_repo)
        actions = [r["action"] for r in records]
        assert "push" in actions
        assert "apply" in actions
        assert "drop" in actions


# ---------------------------------------------------------------------------
# Internal helpers for tests
# ---------------------------------------------------------------------------

def _get_stash_message(repo: Path, ref: str) -> str:
    result = subprocess.run(
        ["git", "stash", "list"],
        cwd=str(repo), capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if line.startswith(ref + ":") or ref in line:
            return line
    return ""


def _extract_label_from_list(stash_list: str) -> str:
    """Extract the cos-label fragment from the first line of git stash list."""
    if not stash_list.strip():
        return ""
    first_line = stash_list.splitlines()[0]
    # Format: "stash@{0}: On main: <label>" or "stash@{0}: WIP on main: <label>"
    # Split on ": " and take everything after the 2nd colon-space
    parts = first_line.split(": ", 2)
    if len(parts) >= 3:
        return parts[2].strip()
    elif len(parts) == 2:
        return parts[1].strip()
    return first_line
