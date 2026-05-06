"""End-to-end smoke tests for ADR-200 retention controller preflight repair."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def run(args: list[str], cwd: Path, env: dict[str, str] | None = None, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(args, cwd=cwd, env=merged, input=input_text, text=True, capture_output=True)


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = run(["git", *args], repo, env=env)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


@pytest.fixture
def projected_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "hooks" / "_lib").mkdir(parents=True)
    (project / "scripts").mkdir()
    (project / "manifests").mkdir()
    (project / ".cognitive-os" / "tasks").mkdir(parents=True)
    for src in [
        ROOT / "hooks" / "agent-prelaunch.sh",
        ROOT / "hooks" / "_lib" / "killswitch_check.sh",
        ROOT / "hooks" / "_lib" / "task-identity.sh",
        ROOT / "scripts" / "cos_work_inventory.py",
        ROOT / "scripts" / "state_retention_audit.py",
    ]:
        dest = project / src.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        dest.chmod(0o755)
    manifest = (ROOT / "manifests" / "state-retention.yaml").read_text(encoding="utf-8")
    manifest = manifest.replace("max_age: P1H", "max_age: P0H", 1)
    (project / "manifests" / "state-retention.yaml").write_text(manifest, encoding="utf-8")
    git(project, "init")
    git(project, "config", "user.email", "test@example.com")
    git(project, "config", "user.name", "Test User")
    (project / "README.md").write_text("base\n", encoding="utf-8")
    (project / ".gitignore").write_text(".cognitive-os/\n", encoding="utf-8")
    git(project, "add", "README.md", ".gitignore", "hooks", "scripts", "manifests")
    git(project, "commit", "-m", "initial")
    return project


def make_tracked_stash(project: Path, name: str) -> None:
    target = project / "work.txt"
    if not target.exists():
        target.write_text("base\n", encoding="utf-8")
        git(project, "add", "work.txt")
        git(project, "commit", "-m", "track work")
    target.write_text(name + "\n", encoding="utf-8")
    git(project, "stash", "push", "-m", name)
    time.sleep(1.1)


def run_prelaunch(project: Path) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_name": "Agent", "tool_input": {"description": "READ_ONLY: true smoke"}, "tool_use_id": "toolu_smoke"})
    return run(
        ["bash", str(project / "hooks" / "agent-prelaunch.sh")],
        project,
        input_text=payload,
        env={
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "COGNITIVE_OS_SESSION_ID": "smoke-session",
            "COS_STASH_LEAK_TTL": "0",
            "COS_STASH_LEAK_BLOCK_TTL": "0",
            "COS_STATE_RETENTION_PREFLIGHT_COOLDOWN_SECONDS": "0",
        },
    )


def test_preflight_repairs_auto_pre_agent_stash_and_passes(projected_project: Path) -> None:
    make_tracked_stash(projected_project, "auto-pre-agent-toolu_smoke")

    result = run_prelaunch(projected_project)

    assert result.returncode == 0, result.stderr
    assert "ADR-199 PREFLIGHT REPAIR" in result.stderr
    assert "auto-pre-agent-toolu_smoke" not in git(projected_project, "stash", "list").stdout
    preserved = git(projected_project, "for-each-ref", "refs/cos-preserved-stash", "--format=%(subject)").stdout
    assert "auto-pre-agent-toolu_smoke" in preserved


def test_preflight_blocks_manual_stash_and_keeps_compact_output(projected_project: Path) -> None:
    make_tracked_stash(projected_project, "manual-preserve-important")

    result = run_prelaunch(projected_project)

    assert result.returncode == 2
    assert "manual-preserve-important" in git(projected_project, "stash", "list").stdout
    assert "ADR-116 preflight summary" in result.stderr
    assert "\"claims\"" not in result.stderr
    assert len(result.stderr) < 4000
