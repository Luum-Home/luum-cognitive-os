"""Behavior tests for scripts/check-local-privacy.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.behavior]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "check-local-privacy.sh"
PRE_COMMIT = PROJECT_ROOT / ".githooks" / "pre-commit"
RULE = PROJECT_ROOT / "rules" / "local-privacy-hygiene.md"
TEMPLATE = PROJECT_ROOT / "templates" / "local-privacy-patterns.example.txt"


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)


def run_guard(root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [str(SCRIPT), "--root", str(root), *args],
        text=True,
        capture_output=True,
        cwd=root,
        env=merged_env,
        timeout=20,
        check=False,
    )


def test_staged_scan_blocks_developer_home_path(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    doc = tmp_path / "README.md"
    leaked = str(Path("/") / "Users" / "example" / "private-project")
    doc.write_text(f"leak: {leaked}\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)

    result = run_guard(tmp_path, "--staged")

    assert result.returncode == 1
    assert "developer home path" in result.stderr
    assert leaked in result.stderr
    assert "README.md" in result.stderr


def test_staged_scan_reads_index_not_dirty_worktree(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text("Portable staged content uses $PROJECT_DIR.\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    doc.write_text(
        f"Dirty content has {Path('/') / 'Users' / 'example' / 'private-project'}.\n",
        encoding="utf-8",
    )

    result = run_guard(tmp_path, "--staged")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "privacy-guard-ok"


def test_private_pattern_file_blocks_ssh_key_filename(tmp_path: Path) -> None:
    init_git_repo(tmp_path)
    patterns = tmp_path / "patterns.txt"
    patterns.write_text("literal:deploy_customer_ed25519\n", encoding="utf-8")
    doc = tmp_path / "deploy.md"
    doc.write_text("Use key deploy_customer_ed25519 for the old host.\n", encoding="utf-8")
    subprocess.run(["git", "add", "deploy.md"], cwd=tmp_path, check=True)

    result = run_guard(
        tmp_path,
        "--staged",
        env={"COS_LOCAL_PRIVACY_PATTERNS_FILE": str(patterns)},
    )

    assert result.returncode == 1
    assert "private literal pattern" in result.stderr
    assert "deploy_customer_ed25519" in result.stderr


def test_allow_marker_permits_fictional_fixture(tmp_path: Path) -> None:
    doc = tmp_path / "fixture.md"
    doc.write_text(
        f"{Path('/') / 'Users' / 'example' / 'private-project'} # cos-allow-local-privacy-pattern\n",
        encoding="utf-8",
    )

    result = run_guard(tmp_path, str(doc))

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "privacy-guard-ok"


def test_repo_all_scan_passes() -> None:
    result = run_guard(PROJECT_ROOT, "--all")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "privacy-guard-ok"


def test_pre_commit_invokes_local_privacy_guard() -> None:
    content = PRE_COMMIT.read_text(encoding="utf-8")

    assert "scripts/check-local-privacy.sh" in content
    assert "--staged" in content


def test_rule_and_template_document_private_configuration() -> None:
    rule = RULE.read_text(encoding="utf-8")
    template = TEMPLATE.read_text(encoding="utf-8")

    assert "scripts/check-local-privacy.sh --all" in rule
    assert ".cognitive-os/private/local-privacy-patterns.txt" in rule
    assert "literal:<private-project-name>" in template
    assert "regex:github[.]com/<private-org>/<private-repo>" in template
