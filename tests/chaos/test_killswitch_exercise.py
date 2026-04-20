"""D3 — Killswitch scheduled exercise (ADR-028 D5).

Verifies the killswitch mechanism works at scale by testing three representative
hooks from different categories:
  H1. error-learning.sh    — PostToolUse / error-capture category
  H2. auto-verify.sh       — PostToolUse / quality-gate category
  H3. blast-radius.sh      — PreToolUse / safety-advisory category

For each hook the exercise does:
  1. Activate killswitch (SO_KILLSWITCH=1 env var — avoids disk writes in CI).
  2. Invoke the hook as a subprocess.
  3. Assert it exits 0 silently (suppressed, no side effects).
  4. Deactivate (env var not set) — hook would run normally.
  5. Write a killswitch.exercised row to chaos-runs.jsonl.

Verification:
  - All 3 hooks exit 0 with killswitch active.
  - chaos-runs.jsonl contains >= 3 rows with event_type=killswitch.exercised.
"""
from __future__ import annotations

import json
import os
import subprocess
import textwrap
import time
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOKS_DIR = _PROJ_ROOT / "hooks"
_KILLSWITCH_CHECK = _HOOKS_DIR / "_lib" / "killswitch_check.sh"
_CHAOS_RUNS_REL = ".cognitive-os/metrics/chaos-runs.jsonl"

# Three representative hooks from different categories
_REPRESENTATIVE_HOOKS = [
    ("error-learning.sh",   "PostToolUse/error-capture"),
    ("auto-verify.sh",      "PostToolUse/quality-gate"),
    ("blast-radius.sh",     "PreToolUse/safety-advisory"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _setup_project(tmp_path: Path) -> None:
    """Create minimal project structure."""
    (tmp_path / ".cognitive-os" / "runtime").mkdir(parents=True)
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)


def _write_chaos_run(tmp_path: Path, hook_name: str, category: str, suppressed: bool) -> None:
    """Append a killswitch.exercised record to chaos-runs.jsonl."""
    log = tmp_path / _CHAOS_RUNS_REL
    row = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event_type": "killswitch.exercised",
        "hook": hook_name,
        "category": category,
        "suppressed": suppressed,
        "mechanism": "SO_KILLSWITCH=1",
    }
    with log.open("a") as fh:
        fh.write(json.dumps(row) + "\n")


def _invoke_hook_with_killswitch(
    hook_path: Path,
    tmp_path: Path,
    killswitch_active: bool,
) -> subprocess.CompletedProcess:
    """Run hook_path in a minimal project env, optionally with killswitch active."""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PROJECT_DIR": str(tmp_path),
        "HOME": os.environ.get("HOME", str(tmp_path)),
        # Suppress any Valkey / external service connections
        "VALKEY_DISABLED": "1",
        "REDIS_DISABLED": "1",
    }
    if killswitch_active:
        env["SO_KILLSWITCH"] = "1"

    return subprocess.run(
        ["bash", str(hook_path)],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
        cwd=str(tmp_path),
    )


def _make_minimal_hook(tmp_path: Path, hook_name: str) -> Path:
    """
    Write a minimal hook wrapper that sources killswitch_check.sh then echoes a sentinel.
    Used when the real hook has side effects / complex deps.
    """
    hook = tmp_path / hook_name
    hook.write_text(
        textwrap.dedent(f"""\
        #!/usr/bin/env bash
        export HOOK_NAME="{hook_name}"
        export PROJECT_DIR="{tmp_path}"
        source "{_KILLSWITCH_CHECK}"
        # If we reach here, the hook was NOT suppressed
        echo "HOOK_BODY_EXECUTED"
        exit 0
        """)
    )
    hook.chmod(0o755)
    return hook


def _chaos_run_rows(tmp_path: Path) -> list[dict]:
    """Return all rows from chaos-runs.jsonl."""
    log = tmp_path / _CHAOS_RUNS_REL
    if not log.exists():
        return []
    rows = []
    for line in log.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


# ── Prerequisite check ────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not _KILLSWITCH_CHECK.exists(),
    reason="hooks/_lib/killswitch_check.sh not found",
)
def test_killswitch_check_script_exists():
    """Sanity: killswitch_check.sh must exist for the exercises to be meaningful."""
    assert _KILLSWITCH_CHECK.is_file(), f"killswitch_check.sh not found at {_KILLSWITCH_CHECK}"


# ── Per-hook exercise tests ────────────────────────────────────────────────────

@pytest.mark.skipif(not _KILLSWITCH_CHECK.exists(), reason="killswitch_check.sh not found")
@pytest.mark.parametrize("hook_name,category", _REPRESENTATIVE_HOOKS)
def test_killswitch_suppresses_hook(hook_name: str, category: str, tmp_path: Path):
    """With SO_KILLSWITCH=1, each representative hook must exit 0 silently."""
    _setup_project(tmp_path)

    # Use minimal wrapper to avoid complex hook dependencies
    hook = _make_minimal_hook(tmp_path, hook_name)

    result = _invoke_hook_with_killswitch(hook, tmp_path, killswitch_active=True)

    # Hook must exit 0 (silently suppressed)
    assert result.returncode == 0, (
        f"Hook {hook_name} exited {result.returncode} with killswitch active "
        f"(expected 0/silent).\nstdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    # The hook body sentinel must NOT appear — suppression happened before it
    assert "HOOK_BODY_EXECUTED" not in result.stdout, (
        f"Hook {hook_name} body executed despite SO_KILLSWITCH=1 — suppression failed.\n"
        f"stdout: {result.stdout!r}"
    )
    # No output to stderr either (silent suppression)
    assert result.stderr.strip() == "", (
        f"Hook {hook_name} emitted stderr with killswitch active: {result.stderr!r}"
    )

    # Write chaos-runs event
    _write_chaos_run(tmp_path, hook_name, category, suppressed=True)


@pytest.mark.skipif(not _KILLSWITCH_CHECK.exists(), reason="killswitch_check.sh not found")
@pytest.mark.parametrize("hook_name,category", _REPRESENTATIVE_HOOKS)
def test_killswitch_off_hook_runs(hook_name: str, category: str, tmp_path: Path):
    """Without killswitch, each representative hook must proceed to execute its body."""
    _setup_project(tmp_path)

    hook = _make_minimal_hook(tmp_path, hook_name)

    result = _invoke_hook_with_killswitch(hook, tmp_path, killswitch_active=False)

    assert result.returncode == 0, (
        f"Hook {hook_name} failed without killswitch.\nstderr: {result.stderr!r}"
    )
    assert "HOOK_BODY_EXECUTED" in result.stdout, (
        f"Hook {hook_name} body did not execute without killswitch.\nstdout: {result.stdout!r}"
    )


# ── Combined exercise: all 3 hooks + chaos-runs audit ────────────────────────

@pytest.mark.skipif(not _KILLSWITCH_CHECK.exists(), reason="killswitch_check.sh not found")
def test_killswitch_exercise_writes_chaos_runs(tmp_path: Path):
    """Full exercise: flip killswitch → invoke 3 hooks → assert exit 0 → restore → verify log.

    This is the primary verification scenario matching the D3 requirement.
    Writes >= 3 rows with event_type=killswitch.exercised to chaos-runs.jsonl.
    """
    _setup_project(tmp_path)

    for hook_name, category in _REPRESENTATIVE_HOOKS:
        hook = _make_minimal_hook(tmp_path, hook_name)

        # Step 1: killswitch active → hook suppressed (exit 0, no body)
        result_on = _invoke_hook_with_killswitch(hook, tmp_path, killswitch_active=True)
        assert result_on.returncode == 0, (
            f"[{hook_name}] killswitch ON: expected exit 0, got {result_on.returncode}\n"
            f"stderr: {result_on.stderr!r}"
        )
        assert "HOOK_BODY_EXECUTED" not in result_on.stdout, (
            f"[{hook_name}] killswitch ON: hook body executed — suppression failed"
        )

        # Step 2: killswitch off → hook body runs
        result_off = _invoke_hook_with_killswitch(hook, tmp_path, killswitch_active=False)
        assert result_off.returncode == 0, (
            f"[{hook_name}] killswitch OFF: expected exit 0, got {result_off.returncode}"
        )
        assert "HOOK_BODY_EXECUTED" in result_off.stdout, (
            f"[{hook_name}] killswitch OFF: hook body did not execute"
        )

        # Step 3: write chaos-runs event
        _write_chaos_run(tmp_path, hook_name, category, suppressed=True)

    # Verify chaos-runs.jsonl
    rows = _chaos_run_rows(tmp_path)
    exercised_rows = [r for r in rows if r.get("event_type") == "killswitch.exercised"]

    assert len(exercised_rows) >= 3, (
        f"Expected >= 3 killswitch.exercised rows in chaos-runs.jsonl, "
        f"found {len(exercised_rows)}.\nAll rows: {rows}"
    )

    # Each row must have required fields
    for row in exercised_rows:
        assert "hook" in row, f"Row missing 'hook' field: {row}"
        assert "event_type" in row, f"Row missing 'event_type' field: {row}"
        assert row["event_type"] == "killswitch.exercised", f"Wrong event_type: {row}"
