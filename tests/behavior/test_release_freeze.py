from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from lib.release_freeze import begin, end, prepare, status
from lib.history_sanitization import SanitizationError, execute

ROOT = Path(__file__).resolve().parents[2]


def run(cmd: list[str], cwd: Path, **env: str) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update(env)
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False, env=merged)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    run(["git", "init", "-b", "main"], path)
    run(["git", "config", "user.name", "Tester"], path)
    run(["git", "config", "user.email", "tester@example.com"], path)
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    run(["git", "add", "README.md"], path)
    run(["git", "commit", "-m", "init"], path)
    (path / "manifests").mkdir()
    (path / "manifests" / "release-freeze.yaml").write_text(
        """
schema_version: release-freeze/v1
expected_branch: main
runtime_dir: .cognitive-os/runtime/release-freeze
report_dir: .cognitive-os/reports/release-freeze
active_marker: .cognitive-os/runtime/release-freeze/active.json
allowed_operations: [content-history-sanitize]
checks:
  clean_worktree: {enabled: true, allowlisted_paths: []}
  branch: {enabled: true}
  task_claims:
    enabled: true
    paths: [.cognitive-os/tasks/active-claims.json]
  agent_heartbeats: {enabled: false}
  pre_public_risk_audit: {enabled: false}
  primitive_coherence: {enabled: false}
guards:
  history_sanitization:
    require_transaction_env: COS_RELEASE_TRANSACTION_ID
""".lstrip(),
        encoding="utf-8",
    )
    return path


def test_prepare_blocks_dirty_worktree(repo: Path) -> None:
    (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")

    report = prepare(repo)

    assert report["status"] == "block"
    assert any(f["code"] == "working-tree-dirty" for f in report["findings"])


def test_prepare_blocks_active_task_claim(repo: Path) -> None:
    tasks = repo / ".cognitive-os" / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "active-claims.json").write_text(json.dumps({"claims": [{"id": "claim-1", "status": "active"}]}), encoding="utf-8")
    run(["git", "add", "manifests/release-freeze.yaml"], repo)
    run(["git", "commit", "-m", "add manifest"], repo)

    report = prepare(repo)

    assert report["status"] == "block"
    assert any(f["code"] == "active-task-claims" for f in report["findings"])


def test_begin_status_end_receipt_flow(repo: Path) -> None:
    run(["git", "add", "manifests/release-freeze.yaml"], repo)
    run(["git", "commit", "-m", "add release freeze manifest"], repo)

    receipt = begin(repo, reason="test-release")

    assert receipt["status"] == "active"
    tid = receipt["transaction_id"]
    assert (repo / ".cognitive-os" / "runtime" / "release-freeze" / "active.json").exists()
    assert Path(receipt["receipt_path"]).exists()
    assert Path(receipt["report_path"]).exists()
    assert status(repo)["status"] == "active"

    ended = end(repo, transaction_id=tid)

    assert ended["status"] == "ended"
    assert status(repo)["status"] == "inactive"


def test_history_sanitize_refuses_mismatched_active_freeze(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run(["git", "add", "manifests/release-freeze.yaml"], repo)
    run(["git", "commit", "-m", "add release freeze manifest"], repo)
    receipt = begin(repo, reason="history-sanitize")
    assert receipt["status"] == "active"
    (repo / "manifests" / "history-sanitization.yaml").write_text(
        """
schema_version: history-sanitization/v1
rules:
  - id: sample
    mode: literal
    pattern: secret-token
    replacement: <redacted>
sensitive_history_patterns: []
preserve: []
execution:
  require_env: COS_ALLOW_DESTRUCTIVE_GIT
  require_env_value: "1"
""".lstrip(),
        encoding="utf-8",
    )
    run(["git", "add", "manifests/history-sanitization.yaml"], repo)
    run(["git", "commit", "-m", "add history sanitize manifest"], repo)
    monkeypatch.setenv("COS_ALLOW_DESTRUCTIVE_GIT", "1")
    monkeypatch.setenv("COS_RELEASE_TRANSACTION_ID", "wrong-id")

    with pytest.raises(SanitizationError) as exc:
        execute(repo, confirmed=True, timestamp="20260101T000000Z")

    assert exc.value.code == "release-freeze-transaction-required"
