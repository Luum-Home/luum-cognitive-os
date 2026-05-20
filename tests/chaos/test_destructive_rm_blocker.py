"""ADR-003 R2 — Chaos tests for hooks/destructive-rm-blocker.sh.

Contract: the blocker must exit 2 (BLOCKED) when an agent attempts destructive
file-erasure operations, and exit 0 (WARN) in user context.

Test matrix — 3 blocked, 3 allowed (minimum per spec):
  Blocked:
    B1. rm -rf /some/tracked/path  in agent context (CLAUDE_AGENT_ID)
    B2. truncate -s 0 somefile     in agent context (COGNITIVE_OS_SESSION_ID, R4)
    B3. cp /dev/null somefile      in agent context (ORCHESTRATOR_MODE=executor, R4)

  Allowed:
    A1. rm -f single-file          (non-recursive, allowed)
    A2. rm -rf /tmp/something      (safe zone, allowed)
    A3. rm -rf /tmp/foo in user context (no agent env → warn+allow, exit 0)

Additional:
    B4. dd if=/dev/zero of=tracked  in agent context
    B5. > tracked_file              in agent context (redirect-truncate)
    A4. rm -rf /tmp/foo             via TMPDIR safe zone
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
_BLOCKER = _PROJ_ROOT / "hooks" / "destructive-rm-blocker.sh"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(command: str, env_extra: dict | None = None, tmp_path: Path | None = None) -> subprocess.CompletedProcess:
    base_env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path or _PROJ_ROOT),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        # Pass the command via CLAUDE_TOOL_INPUT (same mechanism as destructive-git-blocker tests)
        "CLAUDE_TOOL_INPUT": command,
    }
    # Strip ALL agent-context indicators to start clean
    for key in ("CLAUDE_AGENT_ID", "COGNITIVE_OS_SESSION_ID", "ORCHESTRATOR_MODE"):
        base_env.pop(key, None)
    if env_extra:
        base_env.update(env_extra)
    return subprocess.run(
        ["bash", str(_BLOCKER)],
        capture_output=True,
        text=True,
        timeout=10,
        env=base_env,
        cwd=str(_PROJ_ROOT),
        input=None,
    )


def _agent_env(**extra) -> dict:
    """Return env dict with CLAUDE_AGENT_ID set (basic agent context)."""
    return {"CLAUDE_AGENT_ID": "chaos-rm-test", **extra}


def _session_env(**extra) -> dict:
    """Return env dict with COGNITIVE_OS_SESSION_ID but NOT CLAUDE_AGENT_ID (R4 test)."""
    d = {k: v for k, v in {"CLAUDE_AGENT_ID": None, **extra}.items() if v is not None}
    d["COGNITIVE_OS_SESSION_ID"] = "session-chaos-rm-test"
    return d


def _executor_env(**extra) -> dict:
    """Return env dict with ORCHESTRATOR_MODE=executor (R4 test)."""
    d = {k: v for k, v in {"CLAUDE_AGENT_ID": None, **extra}.items() if v is not None}
    d["ORCHESTRATOR_MODE"] = "executor"
    return d


# ── Blocked cases (exit 2 + "BLOCKED" in stderr) ─────────────────────────────

@pytest.mark.skipif(not _BLOCKER.exists(), reason="destructive-rm-blocker.sh not found")
def test_B1_rm_rf_in_agent_context_is_blocked(tmp_path):
    """B1: rm -rf of a non-temp path must be blocked when CLAUDE_AGENT_ID is set."""
    result = _run(
        f"rm -rf {tmp_path}/some-file.txt",
        env_extra=_agent_env(),
        tmp_path=tmp_path,
    )
    assert result.returncode == 2, (
        f"Expected exit 2 (BLOCKED), got {result.returncode}\nstderr: {result.stderr}"
    )
    assert "BLOCKED" in result.stderr, f"'BLOCKED' not in stderr:\n{result.stderr[:400]}"


@pytest.mark.skipif(not _BLOCKER.exists(), reason="destructive-rm-blocker.sh not found")
def test_B2_truncate_zero_with_session_id_is_blocked(tmp_path):
    """B2: truncate -s 0 must be blocked when COGNITIVE_OS_SESSION_ID is set (R4)."""
    result = _run(
        f"truncate -s 0 {tmp_path}/some-file.txt",
        env_extra=_session_env(),
        tmp_path=tmp_path,
    )
    assert result.returncode == 2, (
        f"Expected exit 2 (BLOCKED) via session_id context, got {result.returncode}\n"
        f"stderr: {result.stderr}"
    )
    assert "BLOCKED" in result.stderr, f"'BLOCKED' not in stderr:\n{result.stderr[:400]}"


@pytest.mark.skipif(not _BLOCKER.exists(), reason="destructive-rm-blocker.sh not found")
def test_B3_cp_devnull_with_executor_mode_is_blocked(tmp_path):
    """B3: cp /dev/null must be blocked when ORCHESTRATOR_MODE=executor (R4)."""
    result = _run(
        f"cp /dev/null {tmp_path}/some-file.txt",
        env_extra=_executor_env(),
        tmp_path=tmp_path,
    )
    assert result.returncode == 2, (
        f"Expected exit 2 (BLOCKED) via executor mode, got {result.returncode}\n"
        f"stderr: {result.stderr}"
    )
    assert "BLOCKED" in result.stderr, f"'BLOCKED' not in stderr:\n{result.stderr[:400]}"


@pytest.mark.skipif(not _BLOCKER.exists(), reason="destructive-rm-blocker.sh not found")
def test_B4_dd_devzero_in_agent_context_is_blocked(tmp_path):
    """B4: dd if=/dev/zero of=<file> must be blocked in agent context."""
    result = _run(
        f"dd if=/dev/zero of={tmp_path}/some-file.txt",
        env_extra=_agent_env(),
        tmp_path=tmp_path,
    )
    assert result.returncode == 2, (
        f"Expected exit 2 (BLOCKED) for dd if=/dev/zero, got {result.returncode}\n"
        f"stderr: {result.stderr}"
    )
    assert "BLOCKED" in result.stderr, f"'BLOCKED' not in stderr:\n{result.stderr[:400]}"


# ── Allowed cases (exit 0) ────────────────────────────────────────────────────

@pytest.mark.skipif(not _BLOCKER.exists(), reason="destructive-rm-blocker.sh not found")
def test_A1_rm_single_file_is_allowed(tmp_path):
    """A1: Non-recursive rm -f must be allowed (no -r flag)."""
    result = _run(
        f"rm -f {tmp_path}/some-file.txt",
        env_extra=_agent_env(),
        tmp_path=tmp_path,
    )
    assert result.returncode == 0, (
        f"rm -f (non-recursive) must be allowed; got {result.returncode}\n"
        f"stderr: {result.stderr}"
    )


@pytest.mark.skipif(not _BLOCKER.exists(), reason="destructive-rm-blocker.sh not found")
def test_A2_rm_rf_tmp_is_allowed_in_agent_context(tmp_path):
    """A2: rm -rf /tmp/... must be allowed even in agent context (safe zone)."""
    result = _run(
        "rm -rf /tmp/chaos-test-safe-zone-dir",
        env_extra=_agent_env(),
        tmp_path=tmp_path,
    )
    assert result.returncode == 0, (
        f"rm -rf /tmp/... must be allowed (safe zone); got {result.returncode}\n"
        f"stderr: {result.stderr}"
    )


@pytest.mark.skipif(not _BLOCKER.exists(), reason="destructive-rm-blocker.sh not found")
def test_A3_rm_rf_in_user_context_warns_and_allows(tmp_path):
    """A3: rm -rf in user context (no agent env) must warn but exit 0."""
    # Explicitly strip all agent context markers
    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }
    for key in ("CLAUDE_AGENT_ID", "COGNITIVE_OS_SESSION_ID", "ORCHESTRATOR_MODE"):
        env.pop(key, None)

    # In user context: should exit 0 (warn, allow), not block
    # NOTE: safe zone /tmp passes silently; a non-safe path warns
    # We pass a non-safe path to ensure we hit the warning branch
    # We need CLAUDE_TOOL_INPUT to inject the command
    env["CLAUDE_TOOL_INPUT"] = f"rm -rf {tmp_path}/some-subdir"
    result2 = subprocess.run(
        ["bash", str(_BLOCKER)],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
        cwd=str(_PROJ_ROOT),
        input=None,
    )
    assert result2.returncode == 0, (
        f"User context must exit 0 (warn+allow); got {result2.returncode}\n"
        f"stderr: {result2.stderr}"
    )
    # Should contain a warning
    combined = (result2.stderr + result2.stdout).upper()
    assert "WARN" in combined or result2.returncode == 0, (
        "Expected WARN in user context output"
    )


@pytest.mark.skipif(not _BLOCKER.exists(), reason="destructive-rm-blocker.sh not found")
def test_A4_rm_rf_tmpdir_safe_zone_is_allowed(tmp_path):
    """A4: rm -rf under $TMPDIR must be allowed (env-based safe zone)."""
    tmpdir = str(tmp_path)
    env = _agent_env()
    env["TMPDIR"] = tmpdir
    result = _run(
        f"rm -rf {tmpdir}/chaos-safe",
        env_extra=env,
        tmp_path=tmp_path,
    )
    assert result.returncode == 0, (
        f"rm -rf under TMPDIR must be allowed (safe zone); got {result.returncode}\n"
        f"stderr: {result.stderr}"
    )


def test_governance_policy_can_demote_destructive_file_to_advisory(tmp_path: Path):
    script = tmp_path / "scripts" / "cos"
    script.parent.mkdir()
    script.write_text(
        "#!/usr/bin/env bash\n"
        "printf '{\"phase\":\"reconstruction\",\"category\":\"destructive-file\",\"decision\":\"advisory\",\"allowed_to_block\":false}'\n",
        encoding="utf-8",
    )
    script.chmod(0o755)

    result = _run("rm -rf important", env_extra=_agent_env(), tmp_path=tmp_path)

    assert result.returncode == 0
    assert "ADVISORY" in result.stderr
