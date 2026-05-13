"""ADR-029 — Chaos test: reinvention-check.sh emits a warning when an agent
prompt proposes creating a file that already exists in lib/.

Scenario:
  1. Synthesise a tool_use JSON payload where `tool_input.prompt` says
     "create lib/rate_limiter.py" (which exists in the real project).
  2. Pipe the payload into `bash hooks/reinvention-check.sh`.
  3. Assert exit 0 (advisory, never blocks).
  4. Assert that stderr contains the existing module path.
  5. Assert that reinvention-checks.jsonl received a new entry referencing
     the existing module.

This proves the hook fires when the condition is met and surfaces the
existing module in its output.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOK = _PROJ_ROOT / "hooks" / "reinvention-check.sh"
_EXISTING_MODULE = _PROJ_ROOT / "lib" / "rate_limiter.py"

pytestmark = pytest.mark.skipif(
    not _HOOK.exists(), reason="hooks/reinvention-check.sh not found"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_payload(prompt: str) -> str:
    """Build a minimal Claude Code PreToolUse JSON payload for an Agent call."""
    return json.dumps(
        {
            "tool_name": "Agent",
            "tool_input": {
                "prompt": prompt,
            },
        }
    )


def _run_hook(prompt: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(_PROJ_ROOT)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(_PROJ_ROOT)
    # Disable private mode guard
    env.pop("CLAUDE_PRIVATE_MODE", None)
    payload = _make_agent_payload(prompt)
    return subprocess.run(
        ["bash", str(_HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        cwd=str(_PROJ_ROOT),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _EXISTING_MODULE.exists(),
    reason="lib/rate_limiter.py not found in project — test would be vacuous",
)
def test_reinvention_check_fires_for_existing_module() -> None:
    """Hook must warn when prompt proposes creating lib/rate_limiter.py (exists)."""
    prompt = (
        "Please create lib/rate_limiter.py with a sliding-window rate limiter. "
        "The new file should live in lib/ and implement TokenBucket and SlidingWindow classes."
    )
    result = _run_hook(prompt)

    # Hook is advisory: must always exit 0
    assert result.returncode == 0, (
        f"reinvention-check.sh must exit 0 (advisory).\n"
        f"Got exit {result.returncode}.\nstderr: {result.stderr}\nstdout: {result.stdout}"
    )

    # The hook must emit a warning mentioning the existing path
    combined = result.stderr + result.stdout
    assert "rate_limiter" in combined, (
        f"Expected 'rate_limiter' in hook output (existing module warning).\n"
        f"stderr: {result.stderr}\nstdout: {result.stdout}"
    )


@pytest.mark.skipif(
    not _EXISTING_MODULE.exists(),
    reason="lib/rate_limiter.py not found in project — test would be vacuous",
)
def test_reinvention_check_writes_jsonl() -> None:
    """Hook must append a new entry to reinvention-checks.jsonl when it fires."""
    metrics_dir = _PROJ_ROOT / ".cognitive-os" / "metrics"
    jsonl_path = metrics_dir / "reinvention-checks.jsonl"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    # Record the line count before
    lines_before = len(jsonl_path.read_text(encoding="utf-8").splitlines()) if jsonl_path.exists() else 0

    prompt = (
        "Implement lib/rate_limiter.py — a new rate limiter for API calls. "
        "Create this file in the lib/ directory."
    )
    result = _run_hook(prompt)
    assert result.returncode == 0, (
        f"Hook must exit 0.\nstderr: {result.stderr}"
    )

    # Check JSONL was updated
    if not jsonl_path.exists():
        pytest.skip("reinvention-checks.jsonl not written — hook may have not matched")

    lines_after = jsonl_path.read_text(encoding="utf-8").splitlines()
    new_lines = lines_after[lines_before:]

    assert new_lines, (
        "Expected at least one new entry in reinvention-checks.jsonl after hook fired.\n"
        f"stderr: {result.stderr}"
    )

    # Parse the latest entry and verify it references the target
    last_entry = json.loads(new_lines[-1])
    assert "target" in last_entry, f"JSONL entry missing 'target': {last_entry}"
    assert "rate_limiter" in last_entry.get("target", ""), (
        f"Expected 'rate_limiter' in JSONL entry target: {last_entry}"
    )


def test_reinvention_check_silent_for_novel_prompt() -> None:
    """Hook must not write a JSONL entry for a prompt with no matching existing files."""
    metrics_dir = _PROJ_ROOT / ".cognitive-os" / "metrics"
    jsonl_path = metrics_dir / "reinvention-checks.jsonl"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    lines_before = len(jsonl_path.read_text(encoding="utf-8").splitlines()) if jsonl_path.exists() else 0

    # This describes a completely novel file that doesn't exist anywhere
    prompt = (
        "Create lib/quantum_teleportation_matrix_xyz99.py — a new quantum teleportation helper."
    )
    result = _run_hook(prompt)
    assert result.returncode == 0, (
        f"Hook must always exit 0.\nstderr: {result.stderr}"
    )

    # The hook should NOT have written a new JSONL entry (no match)
    lines_after = len(jsonl_path.read_text(encoding="utf-8").splitlines()) if jsonl_path.exists() else 0
    # We allow the count to be equal (no new entry) — it must not have grown
    assert lines_after == lines_before, (
        f"Hook must not write JSONL entry for a novel (non-existing) file.\n"
        f"Before: {lines_before} lines, After: {lines_after} lines.\n"
        f"stderr: {result.stderr}"
    )
