"""test_hook_pipe.py — Audit tests for the hook composition (pipe) library.

Phase 4 of hook-architecture-v2. Tests verify:
  - hooks/_lib/hook-pipe.sh exists
  - hook_emit and hook_read functions are defined
  - clarification-gate.sh emits clarification_score to the pipe
  - blast-radius.sh reads clarification_score from the pipe
  - hook-pipe.sh is documented in docs/05-Methodology/root/hooks.md
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.parent

# ── Helpers ───────────────────────────────────────────────────────────────────


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.audit
def test_hook_pipe_library_exists():
    """hooks/_lib/hook-pipe.sh must exist."""
    pipe_lib = REPO / "hooks" / "_lib" / "hook-pipe.sh"
    assert pipe_lib.exists(), (
        f"hooks/_lib/hook-pipe.sh not found at {pipe_lib}. "
        "Phase 4 requires creating this library file."
    )


@pytest.mark.audit
def test_hook_pipe_functions_defined():
    """hook_emit and hook_read must be defined in hook-pipe.sh."""
    pipe_lib = REPO / "hooks" / "_lib" / "hook-pipe.sh"
    if not pipe_lib.exists():
        pytest.skip("hook-pipe.sh does not exist — see test_hook_pipe_library_exists")

    content = _read(pipe_lib)
    assert "hook_emit()" in content, (
        "hook_emit() function not found in hook-pipe.sh"
    )
    assert "hook_read()" in content, (
        "hook_read() function not found in hook-pipe.sh"
    )


@pytest.mark.audit
def test_hook_pipe_clear_function_defined():
    """hook_pipe_clear must also be defined in hook-pipe.sh."""
    pipe_lib = REPO / "hooks" / "_lib" / "hook-pipe.sh"
    if not pipe_lib.exists():
        pytest.skip("hook-pipe.sh does not exist")

    content = _read(pipe_lib)
    assert "hook_pipe_clear()" in content, (
        "hook_pipe_clear() function not found in hook-pipe.sh"
    )


@pytest.mark.audit
def test_clarification_gate_emits_score():
    """clarification-gate.sh must source hook-pipe.sh and call hook_emit with clarification_score."""
    gate = REPO / "hooks" / "clarification-gate.sh"
    assert gate.exists(), "hooks/clarification-gate.sh not found"

    content = _read(gate)
    assert "hook-pipe.sh" in content, (
        "clarification-gate.sh does not source hook-pipe.sh. "
        "Phase 4 requires adding: source \"$(dirname \"$0\")/_lib/hook-pipe.sh\""
    )
    assert "hook_emit" in content, (
        "clarification-gate.sh does not call hook_emit. "
        "Phase 4 requires emitting clarification_score to the pipe."
    )
    assert "clarification_score" in content, (
        "clarification-gate.sh does not emit 'clarification_score'. "
        "The key name must match what blast-radius.sh reads."
    )


@pytest.mark.audit
def test_blast_radius_reads_clarification_score():
    """blast-radius.sh must source hook-pipe.sh and read clarification_score."""
    blast = REPO / "hooks" / "blast-radius.sh"
    assert blast.exists(), "hooks/blast-radius.sh not found"

    content = _read(blast)
    assert "hook-pipe.sh" in content, (
        "blast-radius.sh does not source hook-pipe.sh. "
        "Phase 4 requires adding: source \"$(dirname \"$0\")/_lib/hook-pipe.sh\""
    )
    assert "hook_read" in content, (
        "blast-radius.sh does not call hook_read. "
        "Phase 4 requires reading clarification_score from the pipe."
    )
    assert "clarification_score" in content, (
        "blast-radius.sh does not reference 'clarification_score'. "
        "Must read the score emitted by clarification-gate.sh."
    )


@pytest.mark.audit
def test_blast_radius_adjusts_threshold_from_pipe():
    """blast-radius.sh must apply a different HIGH threshold based on clarification_score."""
    blast = REPO / "hooks" / "blast-radius.sh"
    if not blast.exists():
        pytest.skip("blast-radius.sh not found")

    content = _read(blast)
    # Should reference a variable threshold (not a hardcoded 40 only)
    assert "HIGH_THRESHOLD" in content, (
        "blast-radius.sh does not use a HIGH_THRESHOLD variable. "
        "Phase 4 requires dynamically adjusting this threshold based on clarification_score."
    )


@pytest.mark.audit
def test_hook_pipe_documented_in_hooks_md():
    """docs/05-Methodology/root/hooks.md must document the hook composition / pipe library."""
    hooks_doc = REPO / "docs" / "05-Methodology" / "root" / "hooks.md"
    assert hooks_doc.exists(), "docs/05-Methodology/root/hooks.md not found"

    content = _read(hooks_doc)
    assert "hook-pipe.sh" in content, (
        "docs/05-Methodology/root/hooks.md does not mention hook-pipe.sh. "
        "Phase 4 requires documenting the pipe library in docs/05-Methodology/root/hooks.md."
    )
    assert "hook_emit" in content, (
        "docs/05-Methodology/root/hooks.md does not document hook_emit. "
        "Phase 4 requires documenting both hook_emit and hook_read."
    )
    assert "hook_read" in content, (
        "docs/05-Methodology/root/hooks.md does not document hook_read."
    )


@pytest.mark.audit
def test_hook_pipe_syntax_valid():
    """hook-pipe.sh must pass bash -n syntax check."""
    pipe_lib = REPO / "hooks" / "_lib" / "hook-pipe.sh"
    if not pipe_lib.exists():
        pytest.skip("hook-pipe.sh does not exist")

    result = subprocess.run(
        ["bash", "-n", str(pipe_lib)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"hook-pipe.sh failed bash -n syntax check:\n{result.stderr}"
    )


@pytest.mark.audit
def test_clarification_gate_syntax_still_valid():
    """clarification-gate.sh must still pass bash -n after Phase 4 changes."""
    gate = REPO / "hooks" / "clarification-gate.sh"
    if not gate.exists():
        pytest.skip("clarification-gate.sh not found")

    result = subprocess.run(
        ["bash", "-n", str(gate)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"clarification-gate.sh failed bash -n:\n{result.stderr}"
    )


@pytest.mark.audit
def test_blast_radius_syntax_still_valid():
    """blast-radius.sh must still pass bash -n after Phase 4 changes."""
    blast = REPO / "hooks" / "blast-radius.sh"
    if not blast.exists():
        pytest.skip("blast-radius.sh not found")

    result = subprocess.run(
        ["bash", "-n", str(blast)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"blast-radius.sh failed bash -n:\n{result.stderr}"
    )
