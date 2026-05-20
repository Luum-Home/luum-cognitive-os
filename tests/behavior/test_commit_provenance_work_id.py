from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import commit_provenance

pytestmark = pytest.mark.behavior


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    (repo / "tracked.txt").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    return repo


def test_append_provenance_includes_work_id_trailer() -> None:
    message = commit_provenance.append_provenance(
        "ship slice\n",
        session="session-123",
        kind="orchestrator",
        harness="codex",
        work_id="0123456789abcdef",
    )

    assert "X-COS-Session: session-123" in message
    assert "X-COS-Work-ID: 0123456789abcdef" in message
    assert "work_id=0123456789abcdef" in message


@pytest.mark.parametrize("env_name", ["COS_COMMIT_WORK_ID", "COS_TASK_FINGERPRINT"])
def test_apply_to_file_adds_session_and_work_id_from_operator_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, env_name: str
) -> None:
    repo = _make_repo(tmp_path)
    msg = repo / "COMMIT_EDITMSG"
    msg.write_text("implement work identity\n", encoding="utf-8")
    monkeypatch.setenv("COS_ENABLE_COMMIT_PROVENANCE", "1")
    monkeypatch.setenv("COS_COMMIT_SESSION_ID", "session-abc")
    monkeypatch.setenv("COS_COMMIT_HARNESS", "codex")
    monkeypatch.setenv("COS_COMMIT_KIND", "orchestrator")
    monkeypatch.setenv(env_name, "slice-1a-stable-work-identity")

    commit_provenance.apply_to_file(msg, repo=repo)
    content = msg.read_text(encoding="utf-8")

    assert "X-COS-Session: session-abc" in content
    assert "X-COS-Harness: codex" in content
    assert "X-COS-Work-ID:" in content
    trailer = next(line for line in content.splitlines() if line.startswith("X-COS-Work-ID:"))
    assert len(trailer.split(":", 1)[1].strip()) >= 8


def test_existing_provenance_gets_missing_work_id_without_duplicate_session() -> None:
    message = "ship\n\nX-COS-Session: existing\nX-COS-Harness: codex\n"

    updated = commit_provenance.append_provenance(
        message,
        session="new-session",
        kind="orchestrator",
        harness="codex",
        work_id="feedfacecafebeef",
    )

    assert updated.count("X-COS-Session:") == 1
    assert "X-COS-Work-ID: feedfacecafebeef" in updated
