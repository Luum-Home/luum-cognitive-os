"""Behavior tests for git-context-capture.sh Stop hook."""

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior


def _make_commits(project_dir: Path, count: int = 2):
    """Create N commits in the git repo, return list of short SHAs (oldest first)."""
    shas = []
    # Configure git identity for the temp repo
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(project_dir),
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(project_dir),
        capture_output=True,
    )
    for i in range(count):
        test_file = project_dir / f"file{i}.txt"
        test_file.write_text(f"content {i}")
        subprocess.run(
            ["git", "add", str(test_file)],
            cwd=str(project_dir),
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"commit {i}"],
            cwd=str(project_dir),
            capture_output=True,
        )
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
        ).stdout.strip()
        shas.append(sha)
    return shas


class TestGitContextHook:

    def test_writes_git_context_json(self, run_hook, cognitive_os_env):
        """E1: Hook writes git-context.json with branch and commits fields."""
        project_dir = cognitive_os_env["project_dir"]
        session_id = cognitive_os_env["session_id"]
        cos_dir = cognitive_os_env["cos_dir"]

        # Make 2 commits
        shas = _make_commits(project_dir, 2)
        start_commit = shas[0]  # session started after first commit

        # Write meta.json with start_commit
        session_dir = cos_dir / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "session_id": session_id,
            "start_time": "2026-04-10T10:00:00Z",
            "start_commit": start_commit,
        }
        (session_dir / "meta.json").write_text(json.dumps(meta))

        # Run the Stop hook (no stdin needed)
        result = run_hook(
            "git-context-capture.sh",
            env=cognitive_os_env["env"],
            stdin="",
        )

        assert result.returncode == 0, f"Hook failed: {result.stderr}"

        git_context_file = session_dir / "git-context.json"
        assert git_context_file.exists(), "git-context.json was not created"

        data = json.loads(git_context_file.read_text())
        assert "branch" in data, "branch field missing"
        assert "commits" in data, "commits field missing"
        assert isinstance(data["commits"], list)

    def test_enriches_meta_json_with_branch(self, run_hook, cognitive_os_env):
        """E2: Hook enriches meta.json with git_branch field."""
        project_dir = cognitive_os_env["project_dir"]
        session_id = cognitive_os_env["session_id"]
        cos_dir = cognitive_os_env["cos_dir"]

        # Make 2 commits
        shas = _make_commits(project_dir, 2)
        start_commit = shas[0]

        session_dir = cos_dir / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "session_id": session_id,
            "start_time": "2026-04-10T10:00:00Z",
            "start_commit": start_commit,
        }
        (session_dir / "meta.json").write_text(json.dumps(meta))

        result = run_hook(
            "git-context-capture.sh",
            env=cognitive_os_env["env"],
            stdin="",
        )

        assert result.returncode == 0, f"Hook failed: {result.stderr}"

        updated_meta = json.loads((session_dir / "meta.json").read_text())
        assert "git_branch" in updated_meta, "git_branch field not added to meta.json"
        assert updated_meta["git_branch"] != "", "git_branch should not be empty"

    def test_exits_zero_without_session_id(self, run_hook, cognitive_os_env):
        """Hook exits 0 when no SESSION_ID is set."""
        env = cognitive_os_env["env"].copy()
        env.pop("COGNITIVE_OS_SESSION_ID", None)
        env["COGNITIVE_OS_SESSION_ID"] = ""

        result = run_hook("git-context-capture.sh", env=env, stdin="")
        assert result.returncode == 0

    def test_writes_session_audit_jsonl(self, run_hook, cognitive_os_env):
        """Hook appends an entry to session-audit.jsonl."""
        project_dir = cognitive_os_env["project_dir"]
        session_id = cognitive_os_env["session_id"]
        cos_dir = cognitive_os_env["cos_dir"]

        _make_commits(project_dir, 1)

        session_dir = cos_dir / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        meta = {"session_id": session_id, "start_time": "2026-04-10T10:00:00Z"}
        (session_dir / "meta.json").write_text(json.dumps(meta))

        result = run_hook(
            "git-context-capture.sh",
            env=cognitive_os_env["env"],
            stdin="",
        )
        assert result.returncode == 0

        audit_file = cos_dir / "metrics" / "session-audit.jsonl"
        assert audit_file.exists(), "session-audit.jsonl was not created"
        lines = [l for l in audit_file.read_text().splitlines() if l.strip()]
        assert len(lines) >= 1
        entry = json.loads(lines[-1])
        assert entry["session_id"] == session_id
        assert "branch" in entry
