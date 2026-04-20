"""Contract tests for hooks/reinvention-check.sh — ADR-029.

Verifies the hook's behavioral contract:
  - Advisory-only (always exits 0)
  - Emits warning to stderr when existing module path matches
  - stderr output contains the existing module path (serves as additionalContext)
  - Does NOT fire for prompts with no creation intent
  - Does NOT fire for prompts not referencing lib/ or hooks/
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parents[2]
_HOOK = _PROJ_ROOT / "hooks" / "reinvention-check.sh"


pytestmark = pytest.mark.skipif(
    not _HOOK.exists(), reason="hooks/reinvention-check.sh not found"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(prompt: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    """Run reinvention-check.sh with a synthetic Agent tool_use payload."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(_PROJ_ROOT)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(_PROJ_ROOT)
    env.pop("CLAUDE_PRIVATE_MODE", None)
    if env_extra:
        env.update(env_extra)
    payload = json.dumps({
        "tool_name": "Agent",
        "tool_input": {"prompt": prompt},
    })
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
# Contract 1: always advisory (exit 0)
# ---------------------------------------------------------------------------


def test_hook_always_exits_zero_on_match() -> None:
    """reinvention-check must always exit 0, even when a match is found."""
    # Use a file we know exists: lib/rate_limiter.py or lib/metric_event.py
    candidate = "rate_limiter.py"
    if not (_PROJ_ROOT / "lib" / candidate).exists():
        candidate = "metric_event.py"
    if not (_PROJ_ROOT / "lib" / candidate).exists():
        pytest.skip("No known lib/*.py file to test against")

    prompt = f"Create lib/{candidate} with a new implementation."
    result = _run_hook(prompt)
    assert result.returncode == 0, (
        f"reinvention-check.sh must always exit 0 (advisory).\n"
        f"Got exit {result.returncode}.\nstderr: {result.stderr}"
    )


def test_hook_always_exits_zero_on_no_match() -> None:
    """reinvention-check must exit 0 when no existing file matches."""
    prompt = "Create lib/totally_novel_zzz_module_xyz.py with new logic."
    result = _run_hook(prompt)
    assert result.returncode == 0, (
        f"reinvention-check.sh must always exit 0.\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Contract 2: stderr contains existing module path when match found
# ---------------------------------------------------------------------------


def test_stderr_contains_existing_module_path() -> None:
    """When a match is found, stderr must contain the path to the existing module.

    This is what the plan calls 'additionalContext contains existing module path':
    the hook writes its warning to stderr, which Claude Code injects into the
    agent's context as additional information.

    Uses lib/rate_limiter.py as the probe because it is a real file (not a symlink)
    and the hook's `find -type f` resolves it reliably.
    """
    # rate_limiter.py is a known real (non-symlink) file in lib/
    # confirmed by the chaos test that also uses it.
    target = _PROJ_ROOT / "lib" / "rate_limiter.py"
    if not target.exists():
        # Fallback: find any non-symlink .py in lib/
        candidates = [p for p in (_PROJ_ROOT / "lib").glob("*.py") if not p.is_symlink()]
        if not candidates:
            pytest.skip("No non-symlink lib/*.py files found in project")
        target = candidates[0]

    base_name = target.stem  # e.g. "rate_limiter"

    prompt = (
        f"Please implement lib/{target.name} from scratch. "
        f"This is a new file in lib/ that I want to create."
    )
    result = _run_hook(prompt)

    assert result.returncode == 0, f"Hook must exit 0.\nstderr: {result.stderr}"

    # The hook should emit the path of the existing file in stderr
    combined = result.stderr + result.stdout
    assert str(target) in combined or base_name in combined, (
        f"Expected existing module path '{target}' or name '{base_name}' "
        f"in hook output (additionalContext).\n"
        f"stderr: {result.stderr}\nstdout: {result.stdout}"
    )


# ---------------------------------------------------------------------------
# Contract 3: no output for prompts without creation intent
# ---------------------------------------------------------------------------


def test_no_warning_without_creation_intent() -> None:
    """Hook must not fire for prompts that don't mention create/implement/write/add."""
    prompt = "Review lib/rate_limiter.py and suggest improvements."
    result = _run_hook(prompt)
    assert result.returncode == 0
    # No warning should be emitted (nothing to reinvent — not creating anything)
    combined = result.stderr + result.stdout
    assert "REINVENTION CHECK" not in combined, (
        f"Hook must not warn for non-creation prompts.\n"
        f"stderr: {result.stderr}\nstdout: {result.stdout}"
    )


# ---------------------------------------------------------------------------
# Contract 4: no output for prompts without lib/ or hooks/ reference
# ---------------------------------------------------------------------------


def test_no_warning_without_lib_or_hooks_reference() -> None:
    """Hook must not fire if the prompt doesn't reference lib/ or hooks/."""
    prompt = "Create a new rate limiter in the services directory."
    result = _run_hook(prompt)
    assert result.returncode == 0
    combined = result.stderr + result.stdout
    assert "REINVENTION CHECK" not in combined, (
        f"Hook must not warn when prompt doesn't reference lib/ or hooks/.\n"
        f"stderr: {result.stderr}\nstdout: {result.stdout}"
    )
