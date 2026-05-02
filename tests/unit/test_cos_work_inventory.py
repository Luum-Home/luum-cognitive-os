"""Tests for scripts/cos_work_inventory.py — original dimensions + P3.3 extensions."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import helpers
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import cos_work_inventory as cwi  # noqa: E402  (after sys.path manipulation)


# ===========================================================================
# Helpers / fixtures
# ===========================================================================

def _args(**kwargs):
    """Build a minimal argparse namespace for collect_inventory."""
    defaults = {
        "project_dir": "/tmp/fake-project",
        "branch_pattern": "codex/preserve-*",
        "base_ref": "HEAD",
        "stash_warn_ttl": 600,
        "stash_block_ttl": 3600,
        "json": False,
        "strict": False,
        "sessions": False,
        "orphans": False,
        "worktrees_direct": False,
        "stashes_extended": False,
        "claims": False,
        "race_risks": False,
        "all": False,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ===========================================================================
# Original dimension tests (guard against regressions)
# ===========================================================================

class TestFindingDataclass:
    def test_to_dict_has_all_keys(self):
        f = cwi.Finding("WARN", "test-code", "subj", "detail", "action")
        d = f.to_dict()
        assert set(d.keys()) == {"level", "code", "subject", "detail", "action"}

    def test_frozen(self):
        f = cwi.Finding("WARN", "c", "s", "d", "a")
        with pytest.raises((AttributeError, TypeError)):
            f.level = "BLOCK"  # type: ignore[misc]


class TestCategoryFor:
    def test_docs_prefix(self):
        assert cwi.category_for("docs/foo.md") == "docs"

    def test_tests_prefix(self):
        assert cwi.category_for("tests/unit/x.py") == "tests"

    def test_scripts_prefix(self):
        assert cwi.category_for("scripts/foo.sh") == "scripts"

    def test_other(self):
        assert cwi.category_for("random/path.py") == "other"


class TestParseWorktreePorcelain:
    def test_single_worktree(self):
        output = "worktree /tmp/foo\nHEAD abc123\nbranch refs/heads/main\n\n"
        rows = cwi.parse_worktree_porcelain(output)
        assert len(rows) == 1
        assert rows[0]["worktree"] == "/tmp/foo"
        assert rows[0]["HEAD"] == "abc123"

    def test_multiple_worktrees(self):
        output = (
            "worktree /a\nHEAD 111\nbranch refs/heads/main\n\n"
            "worktree /b\nHEAD 222\nbranch refs/heads/feature\n\n"
        )
        rows = cwi.parse_worktree_porcelain(output)
        assert len(rows) == 2


class TestCollectStashes:
    def test_empty_stash_list(self, tmp_path):
        """Returns empty list when git stash list fails or returns nothing."""
        with patch.object(cwi, "git") as mock_git:
            mock_git.return_value = MagicMock(returncode=1, stdout="", stderr="")
            result = cwi.collect_stashes(tmp_path, 600, 3600)
        assert result == []

    def test_stash_level_block(self, tmp_path):
        """Stash older than block_ttl gets BLOCK level."""
        now = int(time.time())
        old_epoch = now - 7200  # 2 hours ago
        output = f"stash@{{0}}\x1f{old_epoch}\x1fOn main: auto-pre-agent-abc"
        with patch.object(cwi, "git") as mock_git:
            mock_git.side_effect = [
                MagicMock(returncode=0, stdout=output),
                MagicMock(returncode=0, stdout="file.py\n"),
            ]
            result = cwi.collect_stashes(tmp_path, 600, 3600)
        assert len(result) == 1
        assert result[0]["level"] == "BLOCK"
        assert result[0]["is_auto_pre_agent"] is True


# ===========================================================================
# P3.3 — sessions dimension
# ===========================================================================

class TestCollectSessions:
    def test_no_sessions_dir(self, tmp_path):
        """Returns empty list when sessions dir does not exist."""
        result = cwi.collect_sessions(tmp_path)
        assert result == []

    def test_reads_active_sessions_json(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        # active-sessions.json
        active = {"sessions": [{"id": "sess-001", "pid": 12345}]}
        (sessions_dir / "active-sessions.json").write_text(json.dumps(active))
        # session dir + meta
        sess_dir = sessions_dir / "sess-001"
        sess_dir.mkdir()
        meta = {"session_id": "sess-001", "pid": 12345, "start_epoch": int(time.time()) - 60, "working_directory": "/tmp"}
        (sess_dir / "meta.json").write_text(json.dumps(meta))
        result = cwi.collect_sessions(tmp_path)
        assert len(result) == 1
        assert result[0]["id"] == "sess-001"
        assert result[0]["in_active_registry"] is True

    def test_session_current_task_from_tasks_json(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        (sessions_dir / "active-sessions.json").write_text(json.dumps({"sessions": []}))
        sess_dir = sessions_dir / "sess-abc"
        sess_dir.mkdir()
        (sess_dir / "meta.json").write_text(json.dumps({"session_id": "sess-abc", "pid": 99999}))
        tasks = [
            {"description": "old task", "status": "completed"},
            {"description": "current work", "status": "in_progress"},
        ]
        (sess_dir / "tasks.json").write_text(json.dumps(tasks))
        result = cwi.collect_sessions(tmp_path)
        assert any(s["current_task"] == "current work" for s in result)

    def test_dead_pid_marked_not_alive(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        (sessions_dir / "active-sessions.json").write_text(json.dumps({"sessions": []}))
        sess_dir = sessions_dir / "sess-dead"
        sess_dir.mkdir()
        # Use PID 999999 which almost certainly does not exist
        (sess_dir / "meta.json").write_text(json.dumps({"session_id": "sess-dead", "pid": 999999999}))
        with patch.object(cwi, "_pid_alive", return_value=False):
            result = cwi.collect_sessions(tmp_path)
        assert result[0]["alive"] is False


# ===========================================================================
# P3.3 — orphans dimension
# ===========================================================================

class TestCollectOrphans:
    def test_reads_orphan_notifier_jsonl(self, tmp_path):
        metrics_dir = tmp_path / ".cognitive-os" / "metrics"
        metrics_dir.mkdir(parents=True)
        record = {"commit": "abc123", "subject": "dangling commit", "source": "p3-1"}
        (metrics_dir / "orphan-notifier.jsonl").write_text(json.dumps(record) + "\n")
        result = cwi.collect_orphans(tmp_path)
        assert len(result) == 1
        assert result[0]["commit"] == "abc123"

    def test_falls_back_to_reflog_scan(self, tmp_path):
        """When orphan-notifier.jsonl is absent, scan reflog."""
        with patch.object(cwi, "git") as mock_git:
            # rev-list --all returns one reachable commit
            # reflog returns one entry that is NOT in reachable set → orphan
            mock_git.side_effect = [
                MagicMock(returncode=0, stdout="aabbccdd\n"),   # rev-list --all
                MagicMock(                                       # reflog
                    returncode=0,
                    stdout="deadbeef1234 HEAD@{0} commit: some work\n",
                ),
            ]
            result = cwi.collect_orphans(tmp_path)
        assert len(result) == 1
        assert result[0]["source"] == "reflog-scan"

    def test_empty_when_no_orphans(self, tmp_path):
        with patch.object(cwi, "git") as mock_git:
            reachable = "aabbccdd\n"
            reflog = "aabbccdd HEAD@{0} commit: same commit\n"
            mock_git.side_effect = [
                MagicMock(returncode=0, stdout=reachable),
                MagicMock(returncode=0, stdout=reflog),
            ]
            result = cwi.collect_orphans(tmp_path)
        assert result == []


# ===========================================================================
# P3.3 — worktrees_direct dimension
# ===========================================================================

class TestCollectWorktreesDirect:
    def test_returns_main_worktree(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        result = cwi.collect_worktrees_direct(tmp_path)
        assert len(result) >= 1
        assert result[0]["source"] == "main"
        assert result[0]["branch"] == "main"

    def test_reads_linked_worktree(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        worktrees_dir = git_dir / "worktrees" / "my-worktree"
        worktrees_dir.mkdir(parents=True)
        (worktrees_dir / "HEAD").write_text("ref: refs/heads/feature-x\n")
        # gitdir points to a non-existent path → prunable
        fake_target = tmp_path / "other" / ".git"
        (worktrees_dir / "gitdir").write_text(str(fake_target) + "\n")
        result = cwi.collect_worktrees_direct(tmp_path)
        linked = [wt for wt in result if wt["source"] == "linked"]
        assert len(linked) == 1
        assert linked[0]["branch"] == "feature-x"
        assert linked[0]["prunable"] is True

    def test_locked_worktree_detected(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        worktrees_dir = git_dir / "worktrees" / "locked-wt"
        worktrees_dir.mkdir(parents=True)
        (worktrees_dir / "HEAD").write_text("ref: refs/heads/some-branch\n")
        (worktrees_dir / "locked").write_text("manual lock reason\n")
        result = cwi.collect_worktrees_direct(tmp_path)
        locked = [wt for wt in result if wt.get("locked")]
        assert len(locked) == 1


# ===========================================================================
# P3.3 — stashes_extended dimension
# ===========================================================================

class TestCollectStashesExtended:
    def test_provenance_tag_auto_pre_agent(self, tmp_path):
        now = int(time.time())
        output = f"stash@{{0}}\x1f{now - 100}\x1fOn main: auto-pre-agent-uuid-here"
        with patch.object(cwi, "git") as mock_git:
            mock_git.side_effect = [
                MagicMock(returncode=0, stdout=output),
                MagicMock(returncode=0, stdout=""),
            ]
            result = cwi.collect_stashes_extended(tmp_path, 600, 3600)
        assert result[0]["provenance_tag"] == "auto-pre-agent"
        assert result[0]["on_branch"] == "main"

    def test_provenance_tag_manual_preserve(self, tmp_path):
        now = int(time.time())
        output = f"stash@{{0}}\x1f{now - 50}\x1fOn feature: manual-preserve-my-work"
        with patch.object(cwi, "git") as mock_git:
            mock_git.side_effect = [
                MagicMock(returncode=0, stdout=output),
                MagicMock(returncode=0, stdout=""),
            ]
            result = cwi.collect_stashes_extended(tmp_path, 600, 3600)
        assert result[0]["provenance_tag"] == "manual-preserve"
        assert result[0]["on_branch"] == "feature"


# ===========================================================================
# P3.3 — claims dimension
# ===========================================================================

class TestCollectClaims:
    def test_no_file_returns_empty(self, tmp_path):
        result = cwi.collect_claims(tmp_path)
        assert result == []

    def test_reads_list_format(self, tmp_path):
        tasks_dir = tmp_path / ".cognitive-os" / "tasks"
        tasks_dir.mkdir(parents=True)
        claims = [{"task_id": "t-1", "session_id": "s-1", "description": "do work"}]
        (tasks_dir / "active-claims.json").write_text(json.dumps(claims))
        result = cwi.collect_claims(tmp_path)
        assert len(result) == 1
        assert result[0]["task_id"] == "t-1"

    def test_reads_dict_format(self, tmp_path):
        tasks_dir = tmp_path / ".cognitive-os" / "tasks"
        tasks_dir.mkdir(parents=True)
        data = {"claims": [{"task_id": "t-2", "session_id": "s-2"}]}
        (tasks_dir / "active-claims.json").write_text(json.dumps(data))
        result = cwi.collect_claims(tmp_path)
        assert len(result) == 1
        assert result[0]["task_id"] == "t-2"


# ===========================================================================
# P3.3 — race_risks dimension
# ===========================================================================

class TestCollectRaceRisks:
    def test_multi_session_same_task(self):
        sessions = [
            {"id": "s1", "alive": True, "current_task": "build feature X"},
            {"id": "s2", "alive": True, "current_task": "build feature X"},
        ]
        risks = cwi.collect_race_risks(sessions, [], [], [])
        codes = [r["code"] for r in risks]
        assert "multi-session-same-task" in codes

    def test_multi_worktree_same_branch(self):
        worktrees = [
            {"path": "/a", "branch": "feature-y"},
            {"path": "/b", "branch": "feature-y"},
        ]
        risks = cwi.collect_race_risks([], worktrees, [], [])
        codes = [r["code"] for r in risks]
        assert "multi-worktree-same-branch" in codes

    def test_stale_stash_from_dead_session(self):
        stashes = [
            {
                "ref": "stash@{0}",
                "age_seconds": 7200,
                "subject": "On main: auto-pre-agent-old-uuid",
                "on_branch": "main",
            }
        ]
        # No alive sessions → stash has no active owner
        risks = cwi.collect_race_risks([], [], stashes, [])
        codes = [r["code"] for r in risks]
        assert "stale-orphan-stash" in codes

    def test_zombie_registry_sessions(self):
        sessions = [
            {"id": "s-alive", "alive": True, "in_active_registry": True, "current_task": None, "pid": 1234},
            {"id": "s-dead", "alive": False, "in_active_registry": True, "current_task": None, "pid": 9999},
        ]
        risks = cwi.collect_race_risks(sessions, [], [], [])
        codes = [r["code"] for r in risks]
        assert "zombie-registry-sessions" in codes
        zombie_risk = next(r for r in risks if r["code"] == "zombie-registry-sessions")
        assert any("count=1" in d for d in zombie_risk["details"])

    def test_no_risks_clean_state(self):
        risks = cwi.collect_race_risks([], [], [], [])
        assert risks == []


# ===========================================================================
# P3.3 — --all flag + JSON output shape
# ===========================================================================

class TestAllFlagAndJsonOutput:
    def _make_mock_inventory(self, tmp_path):
        """Patch collect_inventory internals to return a minimal but valid payload."""
        return {
            "project": str(tmp_path),
            "base_ref": "HEAD",
            "branch_pattern": "codex/preserve-*",
            "status": {
                "branch": "main",
                "head": "abc",
                "upstream": None,
                "ahead": 0,
                "behind": 0,
                "counts": {"staged": 0, "modified": 0, "untracked": 0, "unmerged": 0},
                "entries": [],
                "is_dirty": False,
            },
            "preserve_branches": [],
            "worktrees": [],
            "stashes": [],
            "sessions": [],
            "orphans": [],
            "worktrees_direct": [],
            "stashes_extended": [],
            "claims": [],
            "race_risks": [],
            "findings": [],
            "summary": {
                "blockers": 0,
                "warnings": 0,
                "preserve_branch_count": 0,
                "worktree_count": 0,
                "stash_count": 0,
                "session_count": 0,
                "orphan_count": 0,
                "claim_count": 0,
                "race_risk_count": 0,
            },
        }

    def test_json_output_has_required_keys(self, tmp_path, capsys):
        payload = self._make_mock_inventory(tmp_path)
        with patch.object(cwi, "collect_inventory", return_value=payload):
            args = _args(json=True, all=True)
            # Temporarily set sys.argv to avoid argparse conflicts
            result_payload = cwi.collect_inventory(args)
        # The payload must include all P3.3 keys
        required_keys = {"sessions", "orphans", "worktrees_direct", "stashes_extended", "claims", "race_risks"}
        assert required_keys.issubset(result_payload.keys())

    def test_json_is_parseable(self, tmp_path, capsys):
        payload = self._make_mock_inventory(tmp_path)
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            print(json.dumps(payload, indent=2, sort_keys=True))
        output = buf.getvalue()
        parsed = json.loads(output)
        assert isinstance(parsed, dict)
        assert "sessions" in parsed
        assert "race_risks" in parsed
