from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "commit_provenance.py"
spec = importlib.util.spec_from_file_location("commit_provenance", MODULE_PATH)
assert spec and spec.loader
commit_provenance = importlib.util.module_from_spec(spec)
sys.modules["commit_provenance"] = commit_provenance
spec.loader.exec_module(commit_provenance)


def test_append_provenance_is_idempotent() -> None:
    message = "feat: demo\n"
    first = commit_provenance.append_provenance(message, session="s1", kind="orchestrator", harness="codex")
    second = commit_provenance.append_provenance(first, session="s2", kind="manual", harness="unknown")

    assert first == second
    assert "X-COS-Origin: kind=orchestrator session=s1 harness=codex" in first
    assert "X-COS-Session: s1" in first
    assert "X-COS-Harness: codex" in first


def test_apply_to_file_reads_current_session_marker(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path
    marker_dir = repo / ".cognitive-os" / "sessions"
    marker_dir.mkdir(parents=True)
    (marker_dir / ".current-session-123").write_text("marker-session\n")
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text("fix: thing\n")
    monkeypatch.delenv("COGNITIVE_OS_SESSION_ID", raising=False)
    monkeypatch.setenv("CODEX_PROJECT_DIR", str(repo))
    monkeypatch.setenv("COS_ENABLE_COMMIT_PROVENANCE", "1")

    commit_provenance.apply_to_file(msg, repo=repo)

    text = msg.read_text()
    assert "X-COS-Session: marker-session" in text
    assert "X-COS-Harness: codex" in text


def test_prepare_commit_msg_hook_adds_trailers_in_real_git_repo(tmp_path: Path) -> None:
    source_hook = Path(__file__).resolve().parents[2] / ".githooks" / "prepare-commit-msg"
    source_script = Path(__file__).resolve().parents[2] / "scripts" / "commit_provenance.py"
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=repo, check=True)
    (repo / ".githooks").mkdir()
    (repo / "scripts").mkdir()
    (repo / ".githooks" / "prepare-commit-msg").write_text(source_hook.read_text())
    (repo / ".githooks" / "prepare-commit-msg").chmod(0o755)
    (repo / "scripts" / "commit_provenance.py").write_text(source_script.read_text())
    (repo / "scripts" / "commit_provenance.py").chmod(0o755)
    (repo / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    env = {
        **os.environ,
        "COS_ENABLE_COMMIT_PROVENANCE": "1",
        "COGNITIVE_OS_SESSION_ID": "git-session",
        "COGNITIVE_OS_HARNESS": "codex",
    }

    subprocess.run(["git", "commit", "-m", "feat: provenance"], cwd=repo, env=env, check=True, stdout=subprocess.DEVNULL)

    body = subprocess.check_output(["git", "log", "-1", "--format=%B"], cwd=repo, text=True)
    assert "X-COS-Origin: kind=orchestrator session=git-session harness=codex" in body
    assert "X-COS-Session: git-session" in body



def test_apply_to_file_is_off_by_default(tmp_path: Path, monkeypatch) -> None:
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text("fix: public-history-default\n")
    monkeypatch.delenv("COS_ENABLE_COMMIT_PROVENANCE", raising=False)
    monkeypatch.setenv("COGNITIVE_OS_SESSION_ID", "should-not-appear")

    commit_provenance.apply_to_file(msg, repo=tmp_path)

    assert msg.read_text() == "fix: public-history-default\n"


def test_apply_to_file_respects_disable_env(tmp_path: Path, monkeypatch) -> None:
    msg = tmp_path / "COMMIT_EDITMSG"
    msg.write_text("fix: public-history-cleanup\n")
    monkeypatch.setenv("COS_DISABLE_COMMIT_PROVENANCE", "1")
    monkeypatch.setenv("COGNITIVE_OS_SESSION_ID", "should-not-appear")

    commit_provenance.apply_to_file(msg, repo=tmp_path)

    assert msg.read_text() == "fix: public-history-cleanup\n"


def test_prepare_commit_msg_hook_respects_disable_env_in_real_git_repo(tmp_path: Path) -> None:
    source_hook = Path(__file__).resolve().parents[2] / ".githooks" / "prepare-commit-msg"
    source_script = Path(__file__).resolve().parents[2] / "scripts" / "commit_provenance.py"
    repo = tmp_path / "repo-disable"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=repo, check=True)
    (repo / ".githooks").mkdir()
    (repo / "scripts").mkdir()
    (repo / ".githooks" / "prepare-commit-msg").write_text(source_hook.read_text())
    (repo / ".githooks" / "prepare-commit-msg").chmod(0o755)
    (repo / "scripts" / "commit_provenance.py").write_text(source_script.read_text())
    (repo / "scripts" / "commit_provenance.py").chmod(0o755)
    (repo / "file.txt").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    env = {
        **os.environ,
        "COS_DISABLE_COMMIT_PROVENANCE": "1",
        "COGNITIVE_OS_SESSION_ID": "git-session",
        "COGNITIVE_OS_HARNESS": "codex",
    }

    subprocess.run(["git", "commit", "-m", "feat: no provenance"], cwd=repo, env=env, check=True, stdout=subprocess.DEVNULL)

    body = subprocess.check_output(["git", "log", "-1", "--format=%B"], cwd=repo, text=True)
    assert "X-COS-" not in body
