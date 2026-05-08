"""Behavior test for ADR-218 execute slice (round-trip on a fixture repo).

Builds a tiny throwaway git repo with operator-shaped strings in commit
content, runs the full execute() flow against it (with backup mirror,
filter-repo subprocess, tombstone branch creation, report writing), and
verifies the post-rewrite repo:

  - has the same commit count as pre-rewrite
  - has zero hits of the original strings
  - retains the preserve patterns
  - has a tombstone branch
  - has a schema-versioned JSON report on disk
  - the backup mirror exists and passes git fsck
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lib.history_sanitization import SanitizationError, execute


pytestmark = pytest.mark.skipif(
    shutil.which("git-filter-repo") is None,
    reason="git-filter-repo not installed; behavior test requires it",
)


SECRET_EMAIL = "operator-test@example.invalid"
SECRET_NAME = "Operator Test Fixture"
SECRET_HOME = "/synthetic-home/test-operator-fixture"
COS_TRAILER = "X-COS-Session: fixture-session-123"
PRESERVE_MARKER = "FSL-1.1-MIT"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)


def _make_fixture_repo(repo_path: Path) -> None:
    repo_path.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "--initial-branch=main"], repo_path)
    _run(["git", "config", "user.email", SECRET_EMAIL], repo_path)
    _run(["git", "config", "user.name", SECRET_NAME], repo_path)

    # Commit 1: secret email in a tracked file
    (repo_path / "README.md").write_text(
        f"# Fixture\n\nContact: {SECRET_EMAIL}\n",
        encoding="utf-8",
    )
    _run(["git", "add", "README.md"], repo_path)
    _run(["git", "commit", "-m", "initial commit with operator email", "-m", COS_TRAILER], repo_path)

    # Commit 2: home prefix in a config file
    (repo_path / "config.txt").write_text(
        f"path={SECRET_HOME}/some/path\n",
        encoding="utf-8",
    )
    _run(["git", "add", "config.txt"], repo_path)
    _run(["git", "commit", "-m", "add config with home path"], repo_path)

    # Commit 3: preserve pattern (license transition)
    (repo_path / "LICENSE").write_text(
        f"License: {PRESERVE_MARKER}\nThis transition is honest history.\n",
        encoding="utf-8",
    )
    _run(["git", "add", "LICENSE"], repo_path)
    _run(["git", "commit", "-m", "license transition"], repo_path)


def _write_fixture_manifest(repo_path: Path) -> None:
    """Place a manifest at repo/manifests/history-sanitization.yaml.

    Replacement rules use literal env var lookups so the test can seed
    them; preserve rules cover the LICENSE marker.
    """
    manifest_path = repo_path / "manifests" / "history-sanitization.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        f"""\
schema_version: history-sanitization/v1
status: active

execution:
  require_env: COS_ALLOW_DESTRUCTIVE_GIT
  require_env_value: "1"

scan:
  per_rule_timeout_seconds: 30

rules:
  - id: operator-email
    mode: literal
    value_env: TEST_OPERATOR_EMAIL
    replacement: 2144218+MatiasNAmendola@users.noreply.github.com
    rationale: test fixture
  - id: operator-name
    mode: literal
    value_env: TEST_OPERATOR_NAME
    replacement: Maintainer
    rationale: test fixture
  - id: operator-home-prefix
    mode: literal
    value_env: TEST_OPERATOR_HOME
    replacement: "<home>"
    rationale: test fixture

preserve:
  - id: license-transition
    mode: literal
    pattern: "{PRESERVE_MARKER}"
    rationale: license narrative
""",
        encoding="utf-8",
    )


def test_execute_round_trip_on_fixture(tmp_path, monkeypatch) -> None:
    fixture = tmp_path / "fixture-repo"
    _make_fixture_repo(fixture)
    _write_fixture_manifest(fixture)
    _run(["git", "add", "manifests/history-sanitization.yaml"], fixture)
    _run(["git", "commit", "-m", "add sanitize manifest"], fixture)

    monkeypatch.setenv("TEST_OPERATOR_EMAIL", SECRET_EMAIL)
    monkeypatch.setenv("TEST_OPERATOR_NAME", SECRET_NAME)
    monkeypatch.setenv("TEST_OPERATOR_HOME", SECRET_HOME)
    monkeypatch.setenv("COS_ALLOW_DESTRUCTIVE_GIT", "1")
    # Redirect backup destination to tmp so we don't pollute ~/.cognitive-os
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))

    pre_count_proc = _run(["git", "rev-list", "--count", "--all"], fixture)
    pre_count = int(pre_count_proc.stdout.strip())
    assert pre_count == 4, f"fixture should have 4 commits (3 content + manifest), got {pre_count}"

    pre_grep_email = _run(["git", "log", "--all", "--pretty=fuller", "-p"], fixture)
    assert SECRET_EMAIL in pre_grep_email.stdout, "fixture should contain secret email pre-rewrite"
    assert SECRET_NAME in pre_grep_email.stdout, "fixture should contain secret name pre-rewrite"
    assert COS_TRAILER in pre_grep_email.stdout, "fixture should contain COS trailer pre-rewrite"

    result = execute(fixture, confirmed=True)

    assert result["status"] in {"ok", "completed-with-warnings"}
    assert result["pre_rewrite"]["commit_count"] == pre_count
    assert result["post_rewrite"]["commit_count"] == pre_count
    assert result["pre_rewrite"]["head"] != result["post_rewrite"]["head"]

    # Tombstone branch exists and points at post-rewrite HEAD
    branch_check = _run(["git", "rev-parse", result["tombstone_branch"]], fixture)
    assert branch_check.returncode == 0, f"tombstone branch missing: {branch_check.stderr}"
    assert branch_check.stdout.strip() == result["post_rewrite"]["head"]

    # Backup mirror exists and passes fsck
    backup_path = Path(result["backup_mirror"])
    assert backup_path.exists(), f"backup mirror missing at {backup_path}"
    fsck = _run(["git", "fsck", "--no-progress"], backup_path)
    assert fsck.returncode == 0, f"backup mirror fsck failed: {fsck.stderr}"

    # Post-rewrite history must NOT contain the secret email or home path
    post_grep_email = _run(["git", "log", "--all", "--pretty=fuller", "-p"], fixture)
    assert SECRET_EMAIL not in post_grep_email.stdout, "secret email still present after rewrite"
    assert SECRET_NAME not in post_grep_email.stdout, "secret name still present after rewrite"
    assert SECRET_HOME not in post_grep_email.stdout, "secret home path still present after rewrite"
    assert COS_TRAILER not in post_grep_email.stdout, "COS trailer still present after rewrite"

    # Preserve marker must remain
    assert PRESERVE_MARKER in post_grep_email.stdout, "license-transition preserve pattern was scrubbed"

    # Report file exists, is JSON, and has schema_version
    report_path = Path(result["report_path"])
    assert report_path.exists(), f"report missing at {report_path}"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "history-sanitization-report/v1"
    assert payload["pre_rewrite"]["commit_count"] == pre_count
    assert payload["post_rewrite"]["commit_count"] == pre_count
    assert payload["verification"]["commit_count_preserved"] is True
    assert payload["verification"]["all_replacements_resolved_to_zero"] is True


def test_execute_refuses_without_confirmation(tmp_path) -> None:
    fixture = tmp_path / "fixture-repo"
    _make_fixture_repo(fixture)
    _write_fixture_manifest(fixture)

    with pytest.raises(SanitizationError) as excinfo:
        execute(fixture, confirmed=False)
    assert excinfo.value.code == "operator-confirmation-required"


def test_execute_refuses_with_dirty_worktree(tmp_path, monkeypatch) -> None:
    fixture = tmp_path / "fixture-repo"
    _make_fixture_repo(fixture)
    _write_fixture_manifest(fixture)
    (fixture / "untracked.txt").write_text("dirty", encoding="utf-8")
    _run(["git", "add", "untracked.txt"], fixture)  # stage but don't commit

    monkeypatch.setenv("COS_ALLOW_DESTRUCTIVE_GIT", "1")
    monkeypatch.setenv("TEST_OPERATOR_EMAIL", SECRET_EMAIL)
    monkeypatch.setenv("TEST_OPERATOR_NAME", SECRET_NAME)
    monkeypatch.setenv("TEST_OPERATOR_HOME", SECRET_HOME)
    monkeypatch.setenv("HOME", str(tmp_path / "fake-home"))
    (tmp_path / "fake-home").mkdir()

    with pytest.raises(SanitizationError) as excinfo:
        execute(fixture, confirmed=True)
    assert excinfo.value.code == "working-tree-not-clean"


def test_execute_refuses_without_destructive_env(tmp_path, monkeypatch) -> None:
    fixture = tmp_path / "fixture-repo"
    _make_fixture_repo(fixture)
    _write_fixture_manifest(fixture)
    monkeypatch.delenv("COS_ALLOW_DESTRUCTIVE_GIT", raising=False)
    monkeypatch.setenv("TEST_OPERATOR_EMAIL", SECRET_EMAIL)
    monkeypatch.setenv("TEST_OPERATOR_NAME", SECRET_NAME)
    monkeypatch.setenv("TEST_OPERATOR_HOME", SECRET_HOME)
    monkeypatch.setenv("HOME", str(tmp_path / "fake-home"))
    (tmp_path / "fake-home").mkdir()

    with pytest.raises(SanitizationError) as excinfo:
        execute(fixture, confirmed=True)
    assert excinfo.value.code == "destructive-git-env-missing"
