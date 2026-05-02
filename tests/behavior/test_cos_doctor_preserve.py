from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCTOR = REPO_ROOT / "scripts" / "cos-doctor-preserve.sh"


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check, timeout=20)


@pytest.fixture
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


def commit_file(project: Path, path: str, content: str, message: str) -> str:
    target = project / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    run(["git", "add", path], project)
    run(["git", "commit", "-m", message], project)
    return run(["git", "rev-parse", "HEAD"], project).stdout.strip()


def doctor_json(project: Path, pattern: str = "codex/preserve-*") -> dict:
    result = run(["bash", str(DOCTOR), "--project-dir", str(project), "--branch-pattern", pattern, "--json"], project)
    return json.loads(result.stdout)


def row(payload: dict, branch: str) -> dict:
    rows = {item["branch"]: item for item in payload["preserve_branches"]}
    return rows[branch]


@pytest.mark.behavior
def test_detects_preserve_branch_without_manifest(repo: Path):
    run(["git", "checkout", "-b", "codex/preserve-no-manifest"], repo)
    commit_file(repo, "docs/note.md", "note\n", "preserve docs")
    run(["git", "checkout", "main"], repo)

    payload = doctor_json(repo)
    r = row(payload, "codex/preserve-no-manifest")
    assert r["manifest_exists"] is False
    assert "missing-manifest" in r["findings"]
    assert r["tip_exists_not_ancestor_of_head"] is True


@pytest.mark.behavior
def test_detects_mixed_scope_preserve_branch(repo: Path):
    run(["git", "checkout", "-b", "codex/preserve-mixed"], repo)
    commit_file(repo, "docs/note.md", "note\n", "docs change")
    commit_file(repo, "lib/tool.py", "print('x')\n", "lib change")
    run(["git", "checkout", "main"], repo)

    payload = doctor_json(repo)
    r = row(payload, "codex/preserve-mixed")
    assert r["mixed_scope"] is True
    assert set(r["categories"]) >= {"docs", "lib"}
    assert "mixed-scope" in r["findings"]


@pytest.mark.behavior
def test_detects_already_integrated_preserve_branch_and_delete_candidate(repo: Path):
    run(["git", "checkout", "-b", "codex/preserve-integrated"], repo)
    commit_file(repo, "docs/integrated.md", "ok\n", "integrated preserve")
    run(["git", "checkout", "main"], repo)
    run(["git", "merge", "--ff-only", "codex/preserve-integrated"], repo)

    payload = doctor_json(repo)
    r = row(payload, "codex/preserve-integrated")
    assert r["tip_is_ancestor_of_head"] is True
    assert r["candidate_delete"] is True
    assert "already-integrated" in r["findings"]
    assert "candidate-delete" in r["findings"]


@pytest.mark.behavior
def test_detects_commit_exists_but_not_ancestor_of_head(repo: Path):
    run(["git", "checkout", "-b", "codex/preserve-side"], repo)
    tip = commit_file(repo, "docs/side.md", "side\n", "side preserve")
    run(["git", "checkout", "main"], repo)

    assert run(["git", "cat-file", "-e", f"{tip}^{{commit}}"], repo).returncode == 0
    payload = doctor_json(repo)
    r = row(payload, "codex/preserve-side")
    assert r["tip_exists_not_ancestor_of_head"] is True
    assert "tip-exists-not-ancestor-of-base" in r["findings"]


@pytest.mark.behavior
def test_manifest_status_can_mark_candidate_delete(repo: Path):
    run(["git", "checkout", "-b", "codex/preserve-obsolete"], repo)
    commit_file(repo, "docs/obsolete.md", "old\n", "obsolete preserve")
    run(["git", "checkout", "main"], repo)

    manifest_dir = repo / ".cognitive-os" / "preserve-manifests"
    manifest_dir.mkdir(parents=True)
    manifest = {
        "branch": "codex/preserve-obsolete",
        "created_at": "2026-05-02T16:00:00Z",
        "created_by": "test",
        "source_branch": "main",
        "source_head": "HEAD",
        "reason": "test obsolete",
        "scope": "docs",
        "status": "obsolete",
        "files": ["docs/obsolete.md"],
        "integration_commit": None,
        "delete_after": None,
    }
    (manifest_dir / "codex__preserve-obsolete.json").write_text(json.dumps(manifest), encoding="utf-8")

    payload = doctor_json(repo)
    r = row(payload, "codex/preserve-obsolete")
    assert r["manifest_exists"] is True
    assert r["manifest_status"] == "obsolete"
    assert r["candidate_delete"] is True
    assert "candidate-delete" in r["findings"]


@pytest.mark.behavior
def test_project_dir_projection_supports_consumer_repo(repo: Path):
    run(["git", "checkout", "-b", "codex/preserve-consumer"], repo)
    commit_file(repo, "app/service.py", "print('consumer')\n", "consumer preserve")
    run(["git", "checkout", "main"], repo)

    payload = doctor_json(repo, "codex/preserve-consumer")
    assert payload["project"] == str(repo.resolve())
    assert payload["branch_pattern"] == "codex/preserve-consumer"
    assert row(payload, "codex/preserve-consumer")["tip_exists_not_ancestor_of_head"] is True
