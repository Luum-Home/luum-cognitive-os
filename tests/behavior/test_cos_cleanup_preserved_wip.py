from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "cos_cleanup_preserved_wip.py"


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check, timeout=60)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    run(["git", "init", "-b", "main"], project)
    run(["git", "config", "user.email", "test@example.invalid"], project)
    run(["git", "config", "user.name", "Test User"], project)
    (project / "README.md").write_text("root\n", encoding="utf-8")
    run(["git", "add", "README.md"], project)
    run(["git", "commit", "-m", "initial"], project)
    return project


def test_cleanup_backs_up_and_clears_stashes(repo: Path, tmp_path: Path) -> None:
    (repo / "wip.txt").write_text("preserved\n", encoding="utf-8")
    run(["git", "add", "wip.txt"], repo)
    run(["git", "stash", "push", "-m", "manual-preserve-test"], repo)

    result = run(
        [
            "python3",
            str(SCRIPT),
            "--repo",
            str(repo),
            "--backup-root",
            str(tmp_path / "backups"),
            "--drop-stashes",
            "--apply",
            "--json",
        ],
        repo,
    )
    payload = json.loads(result.stdout)

    assert payload["stashes"]["count"] == 1
    assert run(["git", "stash", "list"], repo).stdout.strip() == ""
    stash_backup = Path(payload["stashes"]["backup_dir"])
    assert (stash_backup / "stash-01.show.patch").exists()
    assert payload["stashes"]["backup_refs"]


def test_cleanup_removes_validation_capsule_after_backup(repo: Path, tmp_path: Path) -> None:
    capsule_root = tmp_path / "cos-validation-capsules"
    capsule = capsule_root / "project-validation-20260502T000000Z"
    run(["git", "worktree", "add", "--detach", str(capsule), "HEAD"], repo)
    (capsule / "generated.txt").write_text("dirty generated\n", encoding="utf-8")

    result = run(
        [
            "python3",
            str(SCRIPT),
            "--repo",
            str(repo),
            "--backup-root",
            str(tmp_path / "backups"),
            "--remove-validation-capsules",
            "--apply",
            "--json",
        ],
        repo,
    )
    payload = json.loads(result.stdout)

    assert len(payload["validation_capsules"]) == 1
    assert not capsule.exists()
    backup_dir = Path(payload["validation_capsules"][0]["backup_dir"])
    assert (backup_dir / "status.txt").exists()
    assert (backup_dir / "untracked.tgz").exists()
    assert str(capsule) not in run(["git", "worktree", "list", "--porcelain"], repo).stdout


def test_cleanup_removes_zombie_registry_sessions(repo: Path, tmp_path: Path) -> None:
    registry = repo / ".cognitive-os" / "sessions" / "active-sessions.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        '{"sessions":[{"id":"dead","pid":999999,"working_directory":"x"}]}\n',
        encoding="utf-8",
    )

    result = run(
        [
            "python3",
            str(SCRIPT),
            "--repo",
            str(repo),
            "--backup-root",
            str(tmp_path / "backups"),
            "--clean-zombie-registry",
            "--apply",
            "--json",
        ],
        repo,
    )
    payload = json.loads(result.stdout)

    assert payload["zombie_registry"]["removed"] == 1
    assert json.loads(registry.read_text(encoding="utf-8"))["sessions"] == []
    assert (Path(payload["backup_dir"]) / "active-sessions.before-clean.json").exists()
