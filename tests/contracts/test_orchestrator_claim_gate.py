"""Contract tests for the cross-IDE orchestrator claim gate."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.orchestrator_claim_gate import (  # noqa: E402
    evaluate,
    extract_commit_messages,
    is_git_commit_or_push,
)


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)


def test_extract_commit_message_with_high_stakes_text() -> None:
    messages = extract_commit_messages('git commit -m "archived hooks/foo.sh"')
    assert messages == ["archived hooks/foo.sh"]
    assert is_git_commit_or_push('git commit -m "x"') == "commit"
    assert is_git_commit_or_push('git push origin main') == "push"


def test_commit_message_archive_claim_fails_when_source_present(tmp_path: Path) -> None:
    init_repo(tmp_path)
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "foo.sh").write_text("#!/usr/bin/env bash\necho live\n")
    result = evaluate(
        tmp_path,
        "pre-commit",
        command='git commit -m "archived hooks/foo.sh"',
    )
    assert result.ok is False
    assert any("unverified high-stakes claim" in f.message for f in result.findings)


def test_staged_plan_done_without_verified_fails(tmp_path: Path) -> None:
    init_repo(tmp_path)
    plans = tmp_path / ".cognitive-os" / "plans"
    plans.mkdir(parents=True)
    plan = plans / "sprint.md"
    plan.write_text("- [x] archived hooks/foo.sh\n")
    subprocess.run(["git", "add", str(plan.relative_to(tmp_path))], cwd=tmp_path, check=True)
    result = evaluate(tmp_path, "pre-commit", command='git commit -m "close plan"')
    assert result.ok is False
    assert any("verified" in f.evidence for f in result.findings)


def test_staged_plan_with_verified_marker_passes(tmp_path: Path) -> None:
    init_repo(tmp_path)
    plans = tmp_path / ".cognitive-os" / "plans"
    plans.mkdir(parents=True)
    plan = plans / "sprint.md"
    plan.write_text("- [x] archived docs only (verified: python3 -m pytest tests/contracts/test_orchestrator_claim_gate.py -q -> pass)\n")
    subprocess.run(["git", "add", str(plan.relative_to(tmp_path))], cwd=tmp_path, check=True)
    result = evaluate(tmp_path, "pre-commit", command='git commit -m "close plan"')
    assert result.ok is True


def test_cross_ide_hook_projection_contains_orchestrator_claim_gate() -> None:
    claude = (REPO / ".claude" / "settings.json").read_text()
    codex = (REPO / ".codex" / "hooks.json").read_text()
    generator = (REPO / "scripts" / "generate-project-settings.sh").read_text()
    assert "hooks/orchestrator-claim-gate.sh" in claude
    assert "hooks/orchestrator-claim-gate.sh" in codex
    assert "orchestrator-claim-gate.sh" in generator


def test_pre_push_detects_same_subject_collision_on_origin(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, stdout=subprocess.PIPE)
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", str(remote), str(repo)], check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "file.txt").write_text("base\n")
    subprocess.run(["git", "add", "file.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo, check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=repo, check=True, stdout=subprocess.PIPE)

    other = tmp_path / "other"
    subprocess.run(["git", "clone", str(remote), str(other)], check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=other, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=other, check=True)
    (other / "other.txt").write_text("remote\n")
    subprocess.run(["git", "add", "other.txt"], cwd=other, check=True)
    subprocess.run(["git", "commit", "-m", "feat: duplicate work"], cwd=other, check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "push"], cwd=other, check=True, stdout=subprocess.PIPE)

    subprocess.run(["git", "fetch", "origin"], cwd=repo, check=True)
    (repo / "local.txt").write_text("local\n")
    subprocess.run(["git", "add", "local.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "feat: duplicate work"], cwd=repo, check=True, stdout=subprocess.PIPE)

    result = evaluate(repo, "pre-push", command="git push")
    assert result.ok is False
    assert any("push collision" in finding.message for finding in result.findings)
