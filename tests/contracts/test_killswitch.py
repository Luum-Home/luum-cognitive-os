"""
test_killswitch.py — ADR-028 D5 behavioral tests for the emergency kill-switch.

Tests:
  1. test_killswitch_flag_created          — so-emergency-stop.sh writes valid JSON flag.
  2. test_killswitch_check_suppresses_non_critical — non-critical hook exits 0 silently when flag is present.
  3. test_killswitch_check_allows_critical — credential-guard.sh is NOT suppressed when flag is present.
  4. test_killswitch_restoration           — after deleting the flag, hook proceeds normally.
"""
from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

import pytest

# ── Fixtures ─────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
EMERGENCY_STOP = REPO_ROOT / "scripts" / "so-emergency-stop.sh"
KILLSWITCH_CHECK = REPO_ROOT / "hooks" / "_lib" / "killswitch_check.sh"


@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Set up a minimal fake project dir with the necessary structure."""
    # Replicate directory skeleton
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".cognitive-os" / "runtime").mkdir(parents=True)
    (tmp_path / ".cognitive-os" / "metrics").mkdir()
    # Minimal settings.json so set-security-profile.sh won't crash
    settings = tmp_path / ".claude" / "settings.json"
    settings.write_text('{"hooks": []}')
    # Stub scripts that so-emergency-stop.sh calls, so they don't touch the real repo
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    _write_stub(scripts_dir / "so-reaper.sh", exit_code=0)
    _write_stub(scripts_dir / "set-security-profile.sh", exit_code=0)
    return tmp_path


def _write_stub(path: Path, exit_code: int = 0) -> None:
    path.write_text(f"#!/usr/bin/env bash\nexit {exit_code}\n")
    path.chmod(0o755)


def _run_emergency_stop(project: Path, reason: str = "test") -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(project), "PROJECT_DIR": str(project)}
    return subprocess.run(
        ["bash", str(EMERGENCY_STOP), reason],
        capture_output=True,
        text=True,
        cwd=str(project),
        env=env,
    )


def _flag_path(project: Path) -> Path:
    return project / ".cognitive-os" / "runtime" / "hook-killswitch.flag"


# ── Test 1: flag is created with valid JSON ───────────────────────────

def test_killswitch_flag_created(tmp_project: Path) -> None:
    """Running so-emergency-stop.sh must create the flag file with valid JSON."""
    result = _run_emergency_stop(tmp_project, "unit-test reason")

    assert result.returncode == 0, f"Script exited non-zero:\n{result.stderr}"

    flag = _flag_path(tmp_project)
    assert flag.exists(), "Flag file was not created"
    assert flag.stat().st_size > 0, "Flag file is empty"

    data = json.loads(flag.read_text())
    assert "timestamp" in data, "Flag JSON missing 'timestamp' key"
    assert "reason" in data, "Flag JSON missing 'reason' key"
    assert data["reason"] == "unit-test reason", f"Unexpected reason: {data['reason']}"
    assert "activated_by" in data, "Flag JSON missing 'activated_by' key"


def test_emergency_stop_is_codex_safe_without_claude_profile_projection(tmp_path: Path) -> None:
    """Codex-hosted projects get the core kill-switch without Claude profile writes."""
    project = tmp_path / "codex-project"
    (project / ".codex").mkdir(parents=True)
    (project / ".cognitive-os" / "runtime").mkdir(parents=True)
    (project / ".cognitive-os" / "metrics").mkdir(parents=True)
    (project / ".codex" / "hooks.json").write_text('{"hooks": {}}\n')

    scripts_dir = project / "scripts"
    scripts_dir.mkdir()
    _write_stub(scripts_dir / "so-reaper.sh", exit_code=0)

    marker = project / "set-security-profile-called"
    set_profile = scripts_dir / "set-security-profile.sh"
    set_profile.write_text(
        "#!/usr/bin/env bash\n"
        f"echo called > {marker}\n"
        "exit 0\n"
    )
    set_profile.chmod(0o755)

    result = subprocess.run(
        ["bash", str(EMERGENCY_STOP), "codex emergency"],
        capture_output=True,
        text=True,
        cwd=str(project),
        env={
            **os.environ,
            "PROJECT_DIR": str(project),
            "COGNITIVE_OS_HARNESS": "codex",
        },
    )

    assert result.returncode == 0, result.stderr
    assert _flag_path(project).exists(), "Core kill-switch flag was not created"
    assert (project / ".codex" / "hooks.json.bak").exists(), "Codex settings driver was not backed up"
    assert not marker.exists(), "Claude-only set-security-profile path ran for a Codex project"
    assert "minimal security profile projection is Claude-driver-only" in result.stdout


# ── Test 2: non-critical hook is suppressed ───────────────────────────

def test_killswitch_check_suppresses_non_critical(tmp_project: Path) -> None:
    """A non-critical hook that sources killswitch_check.sh must exit 0 silently when flag is present."""
    # Plant the flag
    flag = _flag_path(tmp_project)
    flag.write_text('{"timestamp":"2026-04-20T00:00:00Z","reason":"test"}')

    # Write a mock hook that sources killswitch_check.sh, then echoes a sentinel
    mock_hook = tmp_project / "mock-non-critical-hook.sh"
    mock_hook.write_text(
        textwrap.dedent(f"""\
        #!/usr/bin/env bash
        export HOOK_NAME="some-non-critical.sh"
        export PROJECT_DIR="{tmp_project}"
        source "{KILLSWITCH_CHECK}"
        # If we reach here the hook was NOT suppressed
        echo "HOOK_EXECUTED"
        exit 0
        """)
    )
    mock_hook.chmod(0o755)

    result = subprocess.run(
        ["bash", str(mock_hook)],
        capture_output=True,
        text=True,
        cwd=str(tmp_project),
    )

    assert result.returncode == 0, f"Non-critical hook exited non-zero: {result.returncode}\n{result.stderr}"
    assert "HOOK_EXECUTED" not in result.stdout, (
        "Non-critical hook body executed despite killswitch — suppression failed"
    )


# ── Test 3: critical hook is NOT suppressed ───────────────────────────

def test_killswitch_check_allows_critical(tmp_project: Path) -> None:
    """credential-guard.sh must not be suppressed even when the kill-switch flag is present."""
    flag = _flag_path(tmp_project)
    flag.write_text('{"timestamp":"2026-04-20T00:00:00Z","reason":"test"}')

    mock_hook = tmp_project / "credential-guard.sh"
    mock_hook.write_text(
        textwrap.dedent(f"""\
        #!/usr/bin/env bash
        export HOOK_NAME="credential-guard.sh"
        export PROJECT_DIR="{tmp_project}"
        source "{KILLSWITCH_CHECK}"
        # Critical hook — must reach here
        echo "HOOK_EXECUTED"
        exit 0
        """)
    )
    mock_hook.chmod(0o755)

    result = subprocess.run(
        ["bash", str(mock_hook)],
        capture_output=True,
        text=True,
        cwd=str(tmp_project),
    )

    assert result.returncode == 0, f"Critical hook exited non-zero:\n{result.stderr}"
    assert "HOOK_EXECUTED" in result.stdout, (
        "Critical hook (credential-guard.sh) was suppressed — it must NOT be"
    )


# ── Test 4: flag removed → hook runs normally ────────────────────────

def test_killswitch_restoration(tmp_project: Path) -> None:
    """After removing the flag file, a previously-suppressed hook must execute normally."""
    flag = _flag_path(tmp_project)

    # Ensure flag is absent (or remove it)
    flag.unlink(missing_ok=True)
    assert not flag.exists(), "Pre-condition: flag must be absent"

    mock_hook = tmp_project / "mock-hook-restored.sh"
    mock_hook.write_text(
        textwrap.dedent(f"""\
        #!/usr/bin/env bash
        export HOOK_NAME="some-non-critical.sh"
        export PROJECT_DIR="{tmp_project}"
        source "{KILLSWITCH_CHECK}"
        echo "HOOK_EXECUTED"
        exit 0
        """)
    )
    mock_hook.chmod(0o755)

    result = subprocess.run(
        ["bash", str(mock_hook)],
        capture_output=True,
        text=True,
        cwd=str(tmp_project),
    )

    assert result.returncode == 0, f"Restored hook exited non-zero:\n{result.stderr}"
    assert "HOOK_EXECUTED" in result.stdout, (
        "Hook did not execute after killswitch flag was removed — restoration failed"
    )


# ── Test 5 (bonus): idempotency — running stop twice is safe ─────────

def test_killswitch_idempotent(tmp_project: Path) -> None:
    """Running so-emergency-stop.sh twice must exit 0 both times without error."""
    r1 = _run_emergency_stop(tmp_project, "first run")
    r2 = _run_emergency_stop(tmp_project, "second run (idempotent)")

    assert r1.returncode == 0, f"First run failed:\n{r1.stderr}"
    assert r2.returncode == 0, f"Second run failed:\n{r2.stderr}"

    # Flag must still be valid JSON after second run
    flag = _flag_path(tmp_project)
    data = json.loads(flag.read_text())
    assert "timestamp" in data
    assert data["reason"] == "second run (idempotent)"


# ── Test 6 (R3): safety blockers are never suppressed by killswitch ───────────

def test_killswitch_never_suppresses_safety_blockers(tmp_project: Path) -> None:
    """R3: destructive-git-blocker.sh must NOT be suppressed when killswitch is active.

    The killswitch critical whitelist must include the safety blocker hooks so that
    flipping the killswitch does not disable git/rm protection.
    """
    # Plant the flag
    flag = _flag_path(tmp_project)
    flag.write_text('{"timestamp":"2026-04-20T00:00:00Z","reason":"r3-test"}')

    # Test each safety blocker hook name
    for hook_name in ("destructive-git-blocker.sh", "destructive-rm-blocker.sh", "secret-detector.sh"):
        mock_hook = tmp_project / f"mock-{hook_name}"
        mock_hook.write_text(
            textwrap.dedent(f"""\
            #!/usr/bin/env bash
            export HOOK_NAME="{hook_name}"
            export PROJECT_DIR="{tmp_project}"
            source "{KILLSWITCH_CHECK}"
            # Safety blocker — must reach here even with killswitch
            echo "HOOK_EXECUTED"
            exit 0
            """)
        )
        mock_hook.chmod(0o755)

        result = subprocess.run(
            ["bash", str(mock_hook)],
            capture_output=True,
            text=True,
            cwd=str(tmp_project),
        )

        assert result.returncode == 0, (
            f"Safety hook {hook_name} exited non-zero with killswitch active:\n{result.stderr}"
        )
        assert "HOOK_EXECUTED" in result.stdout, (
            f"Safety hook {hook_name} was suppressed by killswitch — it MUST NOT be. "
            f"stdout: {result.stdout!r}"
        )


# ── Test 7 (Q#5): SO_KILLSWITCH env-var triggers suppression ─────────────────

def test_so_killswitch_env_var_triggers_suppression(tmp_project: Path) -> None:
    """Q#5: SO_KILLSWITCH=1 env var must activate killswitch without flag file.

    This is the ADR-028 Q#5 fallback for when the disk is full and the flag
    file cannot be written.
    """
    # Ensure flag does NOT exist — we want only the env-var to trigger
    flag = _flag_path(tmp_project)
    flag.unlink(missing_ok=True)
    assert not flag.exists(), "Pre-condition: flag must be absent for env-var test"

    mock_hook = tmp_project / "mock-non-critical-env.sh"
    mock_hook.write_text(
        textwrap.dedent(f"""\
        #!/usr/bin/env bash
        export HOOK_NAME="some-non-critical.sh"
        export PROJECT_DIR="{tmp_project}"
        source "{KILLSWITCH_CHECK}"
        # If we reach here the hook was NOT suppressed
        echo "HOOK_EXECUTED"
        exit 0
        """)
    )
    mock_hook.chmod(0o755)

    result = subprocess.run(
        ["bash", str(mock_hook)],
        capture_output=True,
        text=True,
        cwd=str(tmp_project),
        env={**os.environ, "SO_KILLSWITCH": "1", "PROJECT_DIR": str(tmp_project)},
    )

    assert result.returncode == 0, (
        f"Non-critical hook with SO_KILLSWITCH=1 exited non-zero: {result.returncode}\n"
        f"stderr: {result.stderr}"
    )
    assert "HOOK_EXECUTED" not in result.stdout, (
        "Non-critical hook executed despite SO_KILLSWITCH=1 — env-var suppression failed. "
        f"stdout: {result.stdout!r}"
    )
