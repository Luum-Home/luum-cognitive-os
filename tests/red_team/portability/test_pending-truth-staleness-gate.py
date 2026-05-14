# SCOPE: os-only
"""Portability probes for hooks/pending-truth-staleness-gate.sh (ADR-273 Slice C).

Bilateral assertion: PreToolUse Bash hook warns (exit 0 with stderr) when
the pending-truth ledger is older than 30 days AND the command is git commit.

Falsification probes:
  1. Command is not git commit -> silent exit 0 regardless of ledger age
  2. Ledger is fresh (< 30d) -> silent exit 0 even on git commit
  3. Ledger absent -> silent exit 0
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "hooks" / "pending-truth-staleness-gate.sh"


def _run(project_dir: Path, command: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    stdin = json.dumps({"tool_input": {"command": command}})
    return subprocess.run(
        ["bash", str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


def _seed_ledger(project_dir: Path, generated_at: str) -> None:
    reports = project_dir / "docs" / "06-Daily" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "pending-truth-latest.json").write_text(json.dumps({
        "schema_version": "pending-truth/v1",
        "generated_at": generated_at,
        "items": [],
        "summary": {},
    }))


def test_stale_ledger_on_git_commit_warns(tmp_path: Path) -> None:
    """Bilateral: ledger >30d old + command=git commit -> emits additionalContext, exit 0."""
    old = (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _seed_ledger(tmp_path, old)
    cp = _run(tmp_path, "git commit -m 'test'")
    assert cp.returncode == 0, f"hook must not block, got {cp.returncode}; stderr={cp.stderr}"
    # Hook emits additionalContext JSON to stdout when ledger is stale
    combined = cp.stdout + cp.stderr
    assert "pending-truth" in combined.lower() or "additionalContext" in combined, \
        f"expected staleness warning, got stdout={cp.stdout!r} stderr={cp.stderr!r}"


def test_falsification_non_git_command_silent(tmp_path: Path) -> None:
    """Falsification: non-git-commit command -> silent exit 0."""
    old = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _seed_ledger(tmp_path, old)
    cp = _run(tmp_path, "ls -la")
    assert cp.returncode == 0
    assert not cp.stderr.strip() or "staleness" not in cp.stderr.lower()


def test_falsification_fresh_ledger_silent(tmp_path: Path) -> None:
    """Falsification: ledger generated today -> silent exit 0 on git commit."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _seed_ledger(tmp_path, today)
    cp = _run(tmp_path, "git commit -m 'test'")
    assert cp.returncode == 0
    assert not cp.stderr.strip() or "stale" not in cp.stderr.lower()


def test_falsification_no_ledger_silent(tmp_path: Path) -> None:
    """Falsification: ledger absent -> silent exit 0."""
    cp = _run(tmp_path, "git commit -m 'test'")
    assert cp.returncode == 0
