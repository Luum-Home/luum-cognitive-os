from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from lib.agent_lifecycle import prepare_agent_worktree, slugify  # noqa: E402


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


def test_slugify_removes_path_unsafe_characters() -> None:
    assert slugify("../Write License + README!") == "write-license-readme"


def test_prepare_agent_worktree_creates_branch_manifest_and_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    root = tmp_path / "agent-worktrees"

    record = prepare_agent_worktree(repo, task_id="toolu_123 Write README", session_id="s1", worktree_root=root)

    assert record.schema_version == "agent-lifecycle-worktree/v1"
    assert record.created is True
    worktree = Path(record.worktree_path)
    assert worktree.is_dir()
    assert (worktree / "README.md").read_text(encoding="utf-8") == "hello\n"
    assert record.branch.startswith("codex/agent/toolu_123-write-readme")
    manifest = repo / ".cognitive-os" / "runtime" / "agent-worktrees" / "toolu_123-write-readme.json"
    assert manifest.is_file()
