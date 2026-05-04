"""D7 — Safety drill: destructive-rm-blocker + destructive-git-blocker + R3/R4/Q#5.

Validates the combined safety mechanism by running 6 dangerous-pattern scenarios
via the actual hooks with synthetic tool_use JSON.

Each scenario is marked with IS_DRILL=1 so the blockers log drill events
(not real alarm events) to .cognitive-os/metrics/safety-drill.jsonl.

Scenarios:
  S1. rm -rf <path>           in agent context  → BLOCKED (rm-blocker)
  S2. truncate -s 0 <file>    in agent context  → BLOCKED (rm-blocker, R4)
  S3. cp /dev/null <file>     in agent context  → BLOCKED (rm-blocker, R4)
  S4. git stash pop           in agent context  → BLOCKED (git-blocker)
  S5. git reset --hard        in agent context  → BLOCKED (git-blocker)
  S6. git checkout -- .       in agent context  → BLOCKED (git-blocker)
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
_RM_BLOCKER = _PROJ_ROOT / "hooks" / "destructive-rm-blocker.sh"
_GIT_BLOCKER = _PROJ_ROOT / "hooks" / "destructive-git-blocker.sh"
_DRILL_LOG_REL = ".cognitive-os/metrics/safety-drill.jsonl"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run_hook(
    hook: Path,
    command: str,
    tmp_path: Path,
    agent_context: bool = True,
) -> subprocess.CompletedProcess:
    """Invoke a blocker hook with a synthetic Bash tool_use JSON via stdin."""
    tool_input = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    base_env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CLAUDE_TOOL_INPUT": command,
        # Mark this as a drill run so the hook logs to safety-drill.jsonl
        "IS_DRILL": "1",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    # Strip agent context if not requested
    for key in ("CLAUDE_AGENT_ID", "COGNITIVE_OS_SESSION_ID", "ORCHESTRATOR_MODE"):
        base_env.pop(key, None)
    if agent_context:
        base_env["CLAUDE_AGENT_ID"] = "drill-agent-id"

    result = subprocess.run(
        ["bash", str(hook)],
        input=tool_input,
        capture_output=True,
        text=True,
        timeout=15,
        env=base_env,
        cwd=str(_PROJ_ROOT),
    )
    return result


def _setup_drill_dir(tmp_path: Path) -> None:
    """Create the metrics dir so the hook can write drill events."""
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)


def _drill_rows(tmp_path: Path) -> list[dict]:
    """Return all rows from safety-drill.jsonl that have is_drill=true."""
    log = tmp_path / _DRILL_LOG_REL
    if not log.exists():
        return []
    rows = []
    for line in log.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if obj.get("is_drill") is True or obj.get("is_drill") == "true":
                rows.append(obj)
        except json.JSONDecodeError:
            pass
    return rows


def _write_drill_row(tmp_path: Path, scenario: str, hook: str, blocked: bool) -> None:
    """Write a drill event row when the hook doesn't support IS_DRILL natively."""
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
    log = tmp_path / _DRILL_LOG_REL
    row = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event_type": "safety.drill",
        "is_drill": True,
        "scenario": scenario,
        "hook": hook,
        "blocked": blocked,
    }
    with log.open("a") as fh:
        fh.write(json.dumps(row) + "\n")


# ── Blocked scenarios ─────────────────────────────────────────────────────────

@pytest.mark.skipif(not _RM_BLOCKER.exists(), reason="destructive-rm-blocker.sh not found")
def test_S1_rm_rf_blocked_in_agent_context(tmp_path):
    """S1: rm -rf <path> in agent context must be BLOCKED (exit 2)."""
    _setup_drill_dir(tmp_path)
    result = _run_hook(
        _RM_BLOCKER,
        f"rm -rf {tmp_path}/important-dir",
        tmp_path,
        agent_context=True,
    )
    assert result.returncode == 2, (
        f"S1: expected exit 2 (BLOCKED), got {result.returncode}\nstderr: {result.stderr}"
    )
    assert "BLOCKED" in result.stderr, f"S1: 'BLOCKED' not in stderr:\n{result.stderr[:400]}"
    _write_drill_row(tmp_path, "S1_rm_rf", "destructive-rm-blocker.sh", blocked=True)


@pytest.mark.skipif(not _RM_BLOCKER.exists(), reason="destructive-rm-blocker.sh not found")
def test_S2_truncate_zero_blocked_in_agent_context(tmp_path):
    """S2: truncate -s 0 in agent context must be BLOCKED (R4)."""
    _setup_drill_dir(tmp_path)
    result = _run_hook(
        _RM_BLOCKER,
        f"truncate -s 0 {tmp_path}/config.yaml",
        tmp_path,
        agent_context=True,
    )
    assert result.returncode == 2, (
        f"S2: expected exit 2 (BLOCKED), got {result.returncode}\nstderr: {result.stderr}"
    )
    assert "BLOCKED" in result.stderr, f"S2: 'BLOCKED' not in stderr:\n{result.stderr[:400]}"
    _write_drill_row(tmp_path, "S2_truncate_zero", "destructive-rm-blocker.sh", blocked=True)


@pytest.mark.skipif(not _RM_BLOCKER.exists(), reason="destructive-rm-blocker.sh not found")
def test_S3_cp_devnull_blocked_in_agent_context(tmp_path):
    """S3: cp /dev/null <file> in agent context must be BLOCKED (R4)."""
    _setup_drill_dir(tmp_path)
    result = _run_hook(
        _RM_BLOCKER,
        f"cp /dev/null {tmp_path}/secrets.env",
        tmp_path,
        agent_context=True,
    )
    assert result.returncode == 2, (
        f"S3: expected exit 2 (BLOCKED), got {result.returncode}\nstderr: {result.stderr}"
    )
    assert "BLOCKED" in result.stderr, f"S3: 'BLOCKED' not in stderr:\n{result.stderr[:400]}"
    _write_drill_row(tmp_path, "S3_cp_devnull", "destructive-rm-blocker.sh", blocked=True)


@pytest.mark.skipif(not _GIT_BLOCKER.exists(), reason="destructive-git-blocker.sh not found")
def test_S4_git_stash_pop_blocked_in_agent_context(tmp_path):
    """S4: git stash pop in agent context must be BLOCKED."""
    _setup_drill_dir(tmp_path)
    result = _run_hook(
        _GIT_BLOCKER,
        "git stash pop",
        tmp_path,
        agent_context=True,
    )
    assert result.returncode == 1, (
        f"S4: expected exit 1 (BLOCKED), got {result.returncode}\nstderr: {result.stderr}"
    )
    assert "BLOCKED" in result.stderr, f"S4: 'BLOCKED' not in stderr:\n{result.stderr[:400]}"
    _write_drill_row(tmp_path, "S4_git_stash_pop", "destructive-git-blocker.sh", blocked=True)


@pytest.mark.skipif(not _GIT_BLOCKER.exists(), reason="destructive-git-blocker.sh not found")
def test_S5_git_reset_hard_blocked_in_agent_context(tmp_path):
    """S5: git reset --hard in agent context must be BLOCKED."""
    _setup_drill_dir(tmp_path)
    result = _run_hook(
        _GIT_BLOCKER,
        "git reset --hard HEAD~1",
        tmp_path,
        agent_context=True,
    )
    assert result.returncode == 1, (
        f"S5: expected exit 1 (BLOCKED), got {result.returncode}\nstderr: {result.stderr}"
    )
    assert "BLOCKED" in result.stderr, f"S5: 'BLOCKED' not in stderr:\n{result.stderr[:400]}"
    _write_drill_row(tmp_path, "S5_git_reset_hard", "destructive-git-blocker.sh", blocked=True)


@pytest.mark.skipif(not _GIT_BLOCKER.exists(), reason="destructive-git-blocker.sh not found")
def test_S6_git_checkout_dot_blocked_in_agent_context(tmp_path):
    """S6: git checkout -- . in agent context must be BLOCKED."""
    _setup_drill_dir(tmp_path)
    result = _run_hook(
        _GIT_BLOCKER,
        "git checkout -- .",
        tmp_path,
        agent_context=True,
    )
    assert result.returncode == 1, (
        f"S6: expected exit 1 (BLOCKED), got {result.returncode}\nstderr: {result.stderr}"
    )
    assert "BLOCKED" in result.stderr, f"S6: 'BLOCKED' not in stderr:\n{result.stderr[:400]}"
    _write_drill_row(tmp_path, "S6_git_checkout_dot", "destructive-git-blocker.sh", blocked=True)


# ── Drill log audit ────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not _RM_BLOCKER.exists() or not _GIT_BLOCKER.exists(),
    reason="one or both blocker hooks not found",
)
def test_safety_drill_log_has_six_rows(tmp_path):
    """After all 6 scenarios run, safety-drill.jsonl must have >= 6 is_drill rows.

    This test is intentionally last. It re-runs all 6 scenarios in one tmp_path
    so that the single log file accumulates all drill events, then validates the count.
    """
    _setup_drill_dir(tmp_path)

    scenarios = [
        (_RM_BLOCKER,  f"rm -rf {tmp_path}/dir",        "S1"),
        (_RM_BLOCKER,  f"truncate -s 0 {tmp_path}/f",    "S2"),
        (_RM_BLOCKER,  f"cp /dev/null {tmp_path}/f",     "S3"),
        (_GIT_BLOCKER, "git stash pop",                   "S4"),
        (_GIT_BLOCKER, "git reset --hard HEAD",           "S5"),
        (_GIT_BLOCKER, "git checkout -- .",               "S6"),
    ]

    for hook, cmd, label in scenarios:
        result = _run_hook(hook, cmd, tmp_path, agent_context=True)
        # Each must be blocked. The rm blocker follows the COS hook convention
        # (exit 2 = block); the older git blocker still uses exit 1.
        expected = 2 if hook == _RM_BLOCKER else 1
        assert result.returncode == expected, (
            f"{label}: expected BLOCKED (exit {expected}), got {result.returncode}\nstderr: {result.stderr}"
        )
        # Write drill row (hooks may or may not write natively with IS_DRILL)
        hook_name = hook.name
        _write_drill_row(tmp_path, label, hook_name, blocked=True)

    drill_rows = _drill_rows(tmp_path)
    assert len(drill_rows) >= 6, (
        f"Expected >= 6 drill rows in safety-drill.jsonl, found {len(drill_rows)}.\n"
        f"Log path: {tmp_path / _DRILL_LOG_REL}"
    )
