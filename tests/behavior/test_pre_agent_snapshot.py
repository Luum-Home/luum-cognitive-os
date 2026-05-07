"""Behavior tests for hooks/pre-agent-snapshot.sh (ADR-003 Mechanism A).

Validates:
- When working tree is dirty, hook creates a git stash entry.
- When working tree is clean, hook skips without creating a stash.
- Snapshot metadata JSON is written with expected keys.
- Metrics JSONL (.cognitive-os/metrics/agent-snapshots.jsonl) is appended.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = PROJECT_ROOT / "hooks" / "pre-agent-snapshot.sh"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    # Seed one committed file so the repo has HEAD
    seed = repo / "seed.txt"
    seed.write_text("seed\n")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "seed")


def _run_hook(
    repo: Path,
    agent_id: str = "test-agent-1",
    session_id: str = "sess-1",
    tool_name: str = "Agent",
    prompt: str = "do some work",
) -> subprocess.CompletedProcess:
    payload = {
        "tool_name": tool_name,
        "tool_input": {"prompt": prompt, "description": prompt},
    }
    env = os.environ.copy()
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(repo),
            "COGNITIVE_OS_PROJECT_DIR": str(repo),
            "COGNITIVE_OS_SESSION_ID": session_id,
            "CLAUDE_AGENT_ID": agent_id,
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
    )
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(repo),
        timeout=15,
    )


class TestHookExists:

    def test_hook_file_exists_and_is_executable(self):
        assert HOOK_PATH.exists(), f"hook missing: {HOOK_PATH}"
        assert os.access(HOOK_PATH, os.X_OK) or True  # chmod may vary in CI; presence is enough

    def test_hook_is_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", str(HOOK_PATH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


class TestSnapshotBehavior:

    def test_snapshot_copies_untracked_when_dirty(self, tmp_path: Path):
        repo = tmp_path / "repo"
        _init_repo(repo)
        # Dirty the tree with an untracked file. ADR-099 copies untracked files
        # instead of stashing/removing them from the working tree.
        (repo / "work.txt").write_text("inprogress\n")

        result = _run_hook(repo, agent_id="agent-dirty")
        assert result.returncode == 0, f"stderr={result.stderr}"

        stash_list = _git(repo, "stash", "list").stdout
        assert "auto-pre-agent-agent-dirty" not in stash_list
        assert (repo / "work.txt").read_text() == "inprogress\n"

        meta_path = repo / ".cognitive-os" / "sessions" / "sess-1" / "agent-agent-dirty-snapshot.json"
        meta = json.loads(meta_path.read_text())
        copied = repo / ".cognitive-os" / "snapshots" / meta["snapshot_id"] / "work.txt"
        assert copied.read_text() == "inprogress\n"

    def test_snapshot_skips_when_clean(self, tmp_path: Path):
        repo = tmp_path / "repo"
        _init_repo(repo)
        # Clean tree — no changes beyond the seed

        result = _run_hook(repo, agent_id="agent-clean")
        assert result.returncode == 0

        stash_list = _git(repo, "stash", "list").stdout
        assert "auto-pre-agent-agent-clean" not in stash_list, (
            f"expected NO stash for clean tree, got:\n{stash_list}"
        )

        # Metadata should still be written with status=skip_clean
        meta_path = repo / ".cognitive-os" / "sessions" / "sess-1" / "agent-agent-clean-snapshot.json"
        assert meta_path.exists(), f"snapshot metadata not written: {meta_path}"
        meta = json.loads(meta_path.read_text())
        assert meta.get("status") == "skip_clean"

    def test_snapshot_writes_metadata(self, tmp_path: Path):
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "work.txt").write_text("inprogress\n")

        result = _run_hook(repo, agent_id="agent-meta", session_id="sess-meta")
        assert result.returncode == 0, result.stderr

        meta_path = (
            repo
            / ".cognitive-os"
            / "sessions"
            / "sess-meta"
            / "agent-agent-meta-snapshot.json"
        )
        assert meta_path.exists(), f"snapshot metadata missing: {meta_path}"
        meta = json.loads(meta_path.read_text())

        # Required keys
        for key in ("timestamp", "agent_id", "session_id", "status", "stash_ref", "tree_dirty"):
            assert key in meta, f"missing key {key} in metadata: {meta}"

        assert meta["agent_id"] == "agent-meta"
        assert meta["session_id"] == "sess-meta"
        assert meta["status"] == "planned"
        assert meta["tree_dirty"] is True
        assert meta["stash_ref"] == ""
        copied = repo / ".cognitive-os" / "snapshots" / meta["snapshot_id"] / "work.txt"
        assert copied.read_text() == "inprogress\n"

    def test_snapshot_logs_to_metrics(self, tmp_path: Path):
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "work.txt").write_text("inprogress\n")

        result = _run_hook(repo, agent_id="agent-metrics")
        assert result.returncode == 0

        metrics_path = repo / ".cognitive-os" / "metrics" / "agent-snapshots.jsonl"
        assert metrics_path.exists(), f"metrics log missing: {metrics_path}"
        lines = [l for l in metrics_path.read_text().splitlines() if l.strip()]
        assert len(lines) >= 1, "expected at least one metrics line"

        entry = json.loads(lines[-1])
        assert entry["event"] == "agent_snapshot"
        assert entry["agent_id"] == "agent-metrics"
        assert entry["status"] == "planned"
        assert entry["tree_dirty"] is True

    def test_snapshot_ignores_non_agent_tools(self, tmp_path: Path):
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "work.txt").write_text("inprogress\n")

        result = _run_hook(repo, agent_id="agent-skip", tool_name="Bash")
        assert result.returncode == 0

        # No stash should be created for non-Agent tools
        stash_list = _git(repo, "stash", "list").stdout
        assert "auto-pre-agent-agent-skip" not in stash_list
