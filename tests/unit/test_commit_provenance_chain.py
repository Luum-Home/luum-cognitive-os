"""Tests for PPID-chain-based provenance attribution.

Covers:
- walk_parents() returns the correct PID chain
- find_owning_context() resolution: chain → env → mtime-json → legacy → None
- Backwards compat: old .current-session-<pid> plain-text files still parse
- infer_kind / infer_harness / read_current_session delegate to find_owning_context
- Atomic marker write via write_context_marker.py helper
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

# ── Module under test ─────────────────────────────────────────────────────────
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

import commit_provenance as cp
import write_context_marker as wcm


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _write_json_marker(sessions_dir: Path, pid: int, **kwargs) -> Path:
    data = {
        "session": kwargs.get("session", f"sess-{pid}"),
        "kind": kwargs.get("kind", "orchestrator"),
        "harness": kwargs.get("harness", "claude"),
        "pid": pid,
        "parent_chain": kwargs.get("parent_chain", [pid]),
    }
    marker = sessions_dir / f".context-{pid}.json"
    marker.write_text(json.dumps(data))
    return marker


def _write_legacy_marker(sessions_dir: Path, pid: int, session_id: str) -> Path:
    marker = sessions_dir / f".current-session-{pid}"
    marker.write_text(session_id)
    return marker


# ─── walk_parents ─────────────────────────────────────────────────────────────


class TestWalkParents:
    def test_includes_self(self):
        pid = os.getpid()
        chain = cp.walk_parents(pid, max_depth=3)
        assert chain[0] == pid

    def test_returns_list_of_ints(self):
        chain = cp.walk_parents(os.getpid(), max_depth=5)
        assert all(isinstance(p, int) for p in chain)

    def test_chain_length_bounded(self):
        chain = cp.walk_parents(os.getpid(), max_depth=3)
        assert len(chain) <= 4  # at most max_depth + 1 (self)

    def test_invalid_pid_returns_only_self(self):
        # PID 99999999 almost certainly doesn't exist
        chain = cp.walk_parents(99999999, max_depth=5)
        assert chain == [99999999]


# ─── find_owning_context: chain lookup ───────────────────────────────────────


class TestFindOwningContextChainLookup:
    def test_finds_own_pid_marker(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        repo = tmp_path

        pid = os.getpid()
        _write_json_marker(sessions_dir, pid, session="my-session", kind="orchestrator", harness="claude")

        ctx = cp.find_owning_context(repo)
        assert ctx is not None
        assert ctx["session"] == "my-session"
        assert ctx["kind"] == "orchestrator"
        assert ctx["harness"] == "claude"

    def test_finds_ancestor_pid_marker(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        repo = tmp_path

        # Write marker for a fake ancestor (not os.getpid, not real)
        # We patch walk_parents to return a chain containing a fake ancestor
        fake_ancestor_pid = 99998
        _write_json_marker(
            sessions_dir, fake_ancestor_pid, session="ancestor-session", kind="orchestrator", harness="codex"
        )

        with patch.object(cp, "walk_parents", return_value=[os.getpid(), fake_ancestor_pid]):
            ctx = cp.find_owning_context(repo)

        assert ctx is not None
        assert ctx["session"] == "ancestor-session"
        assert ctx["harness"] == "codex"

    def test_chain_lookup_prefers_closest_ancestor(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        repo = tmp_path

        pid_child = 10001
        pid_parent = 10002
        _write_json_marker(sessions_dir, pid_child, session="child-session", kind="subagent")
        _write_json_marker(sessions_dir, pid_parent, session="parent-session", kind="orchestrator")

        # Walk returns child before parent
        with patch.object(cp, "walk_parents", return_value=[pid_child, pid_parent]):
            ctx = cp.find_owning_context(repo)

        assert ctx["session"] == "child-session"
        assert ctx["kind"] == "subagent"

    def test_no_chain_match_falls_through_to_env(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        repo = tmp_path

        env_overrides = {
            "COS_COMMIT_SESSION_ID": "env-session-123",
            "CLAUDE_SESSION_ID": None,
            "COGNITIVE_OS_SESSION_ID": None,
            "CODEX_SESSION_ID": None,
            "COS_COMMIT_KIND": "orchestrator",
            "COS_COMMIT_HARNESS": "claude",
            # Clear env keys that would trigger chain lookup or legacy
            "CODEX_PROJECT_DIR": None,
            "CLAUDE_PROJECT_DIR": None,
            "COS_HOOK_NAME": None,
            "COS_SUBAGENT_ID": None,
            "CLAUDE_SUBAGENT_ID": None,
            "GITHUB_ACTIONS": None,
        }
        with patch.object(cp, "walk_parents", return_value=[99991, 99992]):
            with patch.dict(os.environ, {k: v for k, v in env_overrides.items() if v is not None}, clear=False):
                # Also unset None-valued keys
                for k, v in env_overrides.items():
                    if v is None:
                        os.environ.pop(k, None)
                ctx = cp.find_owning_context(repo)

        assert ctx is not None
        assert ctx["session"] == "env-session-123"
        assert ctx["_source"] == "env"


# ─── find_owning_context: mtime fallback ─────────────────────────────────────


class TestFindOwningContextMtimeFallback:
    def test_mtime_json_fallback_when_no_chain_no_env(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        repo = tmp_path

        _write_json_marker(sessions_dir, 77771, session="mtime-session", kind="cron", harness="unknown")

        clean_env = {k: None for k in [
            "COS_COMMIT_SESSION_ID", "COGNITIVE_OS_SESSION_ID",
            "CLAUDE_SESSION_ID", "CODEX_SESSION_ID", "CODEX_PROJECT_DIR",
            "CLAUDE_PROJECT_DIR", "COS_COMMIT_KIND", "COS_COMMIT_HARNESS",
            "COGNITIVE_OS_HARNESS", "COS_HOOK_NAME", "COS_SUBAGENT_ID",
            "CLAUDE_SUBAGENT_ID", "GITHUB_ACTIONS",
        ]}
        with patch.object(cp, "walk_parents", return_value=[99993, 99994]):
            with patch.dict(os.environ, {}, clear=False):
                for k in clean_env:
                    os.environ.pop(k, None)
                ctx = cp.find_owning_context(repo)

        assert ctx is not None
        assert ctx["session"] == "mtime-session"
        assert ctx["_source"] == "mtime-json-fallback"


# ─── Backwards compat: legacy .current-session-<pid> files ───────────────────


class TestLegacyMarkerBackwardsCompat:
    def test_legacy_plain_text_still_returns_session_id(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        repo = tmp_path

        _write_legacy_marker(sessions_dir, 88881, "legacy-session-id-abc")

        clean_env_keys = [
            "COS_COMMIT_SESSION_ID", "COGNITIVE_OS_SESSION_ID",
            "CLAUDE_SESSION_ID", "CODEX_SESSION_ID", "CODEX_PROJECT_DIR",
            "CLAUDE_PROJECT_DIR", "COS_COMMIT_KIND", "COS_COMMIT_HARNESS",
            "COGNITIVE_OS_HARNESS", "COS_HOOK_NAME", "COS_SUBAGENT_ID",
            "CLAUDE_SUBAGENT_ID", "GITHUB_ACTIONS",
        ]
        with patch.object(cp, "walk_parents", return_value=[99995, 99996]):
            with patch.dict(os.environ, {}, clear=False):
                for k in clean_env_keys:
                    os.environ.pop(k, None)
                ctx = cp.find_owning_context(repo)

        assert ctx is not None
        assert ctx["session"] == "legacy-session-id-abc"
        assert ctx["_source"] == "legacy-fallback"
        assert ctx.get("_legacy") is True

    def test_legacy_marker_does_not_crash_on_empty_file(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)

        empty_marker = sessions_dir / ".current-session-99997"
        empty_marker.write_text("")

        result = cp._load_legacy_marker(empty_marker)
        assert result is None

    def test_json_marker_takes_priority_over_legacy_same_repo(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        repo = tmp_path

        # Both exist; JSON (chain hit) should win
        fake_pid = 77772
        _write_json_marker(sessions_dir, fake_pid, session="json-wins", kind="orchestrator")
        _write_legacy_marker(sessions_dir, 88882, "legacy-loses")

        with patch.object(cp, "walk_parents", return_value=[fake_pid]):
            ctx = cp.find_owning_context(repo)

        assert ctx["session"] == "json-wins"


# ─── Fallback order: None when nothing exists ─────────────────────────────────


class TestFindOwningContextNoneFallback:
    def test_returns_none_when_no_markers_no_env(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        repo = tmp_path

        clean_env_keys = [
            "COS_COMMIT_SESSION_ID", "COGNITIVE_OS_SESSION_ID",
            "CLAUDE_SESSION_ID", "CODEX_SESSION_ID", "CODEX_PROJECT_DIR",
            "CLAUDE_PROJECT_DIR", "COS_COMMIT_KIND", "COS_COMMIT_HARNESS",
            "COGNITIVE_OS_HARNESS", "COS_HOOK_NAME", "COS_SUBAGENT_ID",
            "CLAUDE_SUBAGENT_ID", "GITHUB_ACTIONS",
        ]
        with patch.object(cp, "walk_parents", return_value=[99997, 99998]):
            with patch.dict(os.environ, {}, clear=False):
                for k in clean_env_keys:
                    os.environ.pop(k, None)
                ctx = cp.find_owning_context(repo)

        assert ctx is None


# ─── Public API delegates to find_owning_context ────────────────────────────


class TestPublicApiDelegation:
    def test_read_current_session_uses_chain(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        repo = tmp_path
        fake_pid = 55551
        _write_json_marker(sessions_dir, fake_pid, session="api-session")

        with patch.object(cp, "walk_parents", return_value=[fake_pid]):
            result = cp.read_current_session(repo)
        assert result == "api-session"

    def test_infer_kind_uses_chain(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        repo = tmp_path
        fake_pid = 55552
        _write_json_marker(sessions_dir, fake_pid, kind="subagent")

        with patch.object(cp, "walk_parents", return_value=[fake_pid]):
            result = cp.infer_kind(repo)
        assert result == "subagent"

    def test_infer_harness_uses_chain(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        repo = tmp_path
        fake_pid = 55553
        _write_json_marker(sessions_dir, fake_pid, harness="codex")

        with patch.object(cp, "walk_parents", return_value=[fake_pid]):
            result = cp.infer_harness(repo)
        assert result == "codex"

    def test_apply_to_file_uses_chain(self, tmp_path):
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        repo = tmp_path
        fake_pid = 55554
        _write_json_marker(
            sessions_dir, fake_pid, session="file-session", kind="orchestrator", harness="claude"
        )

        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text("Initial commit\n")

        with patch.object(cp, "walk_parents", return_value=[fake_pid]):
            with patch.object(cp, "resolve_repo", return_value=repo):
                cp.apply_to_file(msg_file)

        content = msg_file.read_text()
        assert "X-COS-Session: file-session" in content
        assert "kind=orchestrator" in content
        assert "harness=claude" in content


# ─── write_context_marker helper ─────────────────────────────────────────────


class TestWriteContextMarker:
    def test_writes_valid_json(self, tmp_path):
        repo = tmp_path
        (repo / ".cognitive-os" / "sessions").mkdir(parents=True)
        (repo / ".git").mkdir()

        with patch.object(wcm, "resolve_repo", return_value=repo):
            path = wcm.write_context_marker("orchestrator")

        assert path.exists()
        data = json.loads(path.read_text())
        assert data["kind"] == "orchestrator"
        assert data["pid"] == os.getpid()
        assert isinstance(data["parent_chain"], list)
        assert data["parent_chain"][0] == os.getpid()

    def test_rejects_invalid_kind(self, tmp_path):
        with pytest.raises(ValueError, match="Invalid kind"):
            wcm.write_context_marker("invalid-kind")

    def test_atomic_write_does_not_leave_tmp_on_success(self, tmp_path):
        repo = tmp_path
        (repo / ".cognitive-os" / "sessions").mkdir(parents=True)

        with patch.object(wcm, "resolve_repo", return_value=repo):
            wcm.write_context_marker("subagent")

        sessions_dir = repo / ".cognitive-os" / "sessions"
        tmp_files = list(sessions_dir.glob(".context-tmp-*"))
        assert tmp_files == [], f"Temp files left behind: {tmp_files}"
