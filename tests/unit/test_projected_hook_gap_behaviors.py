from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_hook(path: str, payload: dict | None = None, *, project_dir: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = {**os.environ, **(env or {})}
    if project_dir is not None:
        merged["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
        merged["CLAUDE_PROJECT_DIR"] = str(project_dir)
    merged.setdefault("COGNITIVE_OS_SESSION_ID", "pytest-session")
    return subprocess.run(
        ["bash", str(PROJECT_ROOT / path)],
        input=json.dumps(payload or {}),
        text=True,
        capture_output=True,
        env=merged,
        check=False,
    )


def test_git_commit_scope_guard_blocks_bare_commit_and_allows_scoped_commit() -> None:
    # hooks/git-commit-scope-guard.sh: bare commit is unsafe under ADR-089.
    bare = run_hook(
        "hooks/git-commit-scope-guard.sh",
        {"tool_name": "Bash", "tool_input": {"command": "git commit -m unsafe"}},
    )
    scoped = run_hook(
        "hooks/git-commit-scope-guard.sh",
        {"tool_name": "Bash", "tool_input": {"command": "git commit --only -- scripts/docs_execution_audit.py -m safe"}},
    )

    assert bare.returncode == 2
    assert "bare `git commit`" in bare.stderr
    assert scoped.returncode == 0, scoped.stderr


def test_query_tailored_context_inject_skips_non_agent_tool() -> None:
    # hooks/query-tailored-context-inject.sh: only Agent/task/delegate calls should be processed.
    result = run_hook(
        "hooks/query-tailored-context-inject.sh",
        {"tool_name": "Bash", "tool_input": {"command": "echo hi"}},
        project_dir=PROJECT_ROOT,
    )

    assert result.returncode == 0
    assert result.stdout == ""


def test_edit_lock_pre_tool_acquires_lock_and_session_end_releases_it(tmp_path: Path) -> None:
    # hooks/edit-lock-pre-tool.sh + hooks/edit-lock-session-end.sh: first edit self-acquires, Stop releases.
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy2(PROJECT_ROOT / "scripts" / "edit-coop.sh", scripts_dir / "edit-coop.sh")
    (scripts_dir / "edit-coop.sh").chmod(0o755)
    (tmp_path / "cognitive-os.yaml").write_text("project:\n  phase: reconstruction\n", encoding="utf-8")

    payload = {"tool_name": "Edit", "tool_input": {"file_path": "docs/example.md"}}
    acquired = run_hook(
        "hooks/edit-lock-pre-tool.sh",
        payload,
        project_dir=tmp_path,
        env={"COS_EDIT_LOCK_NO_PID_CHECK": "1"},
    )
    lock_dir = tmp_path / ".cognitive-os" / "runtime" / "edit-locks" / "docs--example.md"

    assert acquired.returncode == 0, acquired.stderr
    assert lock_dir.exists(), "edit-lock-pre-tool.sh should acquire a file lock"

    released = run_hook("hooks/edit-lock-session-end.sh", {}, project_dir=tmp_path, env={"COS_EDIT_LOCK_NO_PID_CHECK": "1"})
    assert released.returncode == 0
    assert not lock_dir.exists(), "edit-lock-session-end.sh should release this session's locks"


def test_review_spawner_skips_short_agent_output_without_dispatch(tmp_path: Path) -> None:
    # hooks/review-spawner.sh and packages/agent-lifecycle/hooks/review-spawner.sh should not dispatch tiny outputs.
    payload = {"tool_name": "Agent", "tool_result": "too short", "tool_input": {"prompt": "review me"}}
    for hook in ("hooks/review-spawner.sh", "packages/agent-lifecycle/hooks/review-spawner.sh"):
        result = run_hook(hook, payload, project_dir=tmp_path)
        assert result.returncode == 0, f"{hook}: {result.stderr}"
        assert not (tmp_path / ".cognitive-os" / "metrics" / "review-findings.jsonl").exists()


def test_stop_hooks_noop_when_inputs_absent_or_empty(tmp_path: Path) -> None:
    # hooks/skill-failure-monitor.sh: no skill-feedback log -> no repair queue, but cooldown is recorded.
    failure = run_hook("hooks/skill-failure-monitor.sh", {}, project_dir=tmp_path)
    assert failure.returncode == 0, failure.stderr
    assert (tmp_path / ".cognitive-os" / "runtime" / "skill-failure-monitor-last").exists()
    assert not (tmp_path / ".cognitive-os" / "metrics" / "skill-repair-queue.jsonl").exists()

    # hooks/skill-synthesis-scanner.sh: no tool-sequences log -> no queue, but cooldown is recorded.
    synthesis = run_hook("hooks/skill-synthesis-scanner.sh", {}, project_dir=tmp_path)
    assert synthesis.returncode == 0, synthesis.stderr
    assert (tmp_path / ".cognitive-os" / "runtime" / "skill-synthesis-scanner-last").exists()
    assert not (tmp_path / ".cognitive-os" / "metrics" / "skill-synthesis-queue.jsonl").exists()
