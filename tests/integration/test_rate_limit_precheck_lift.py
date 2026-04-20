"""Integration tests: rate-limit-precheck.sh sidecar lookup (D45 gap B).

Tests that the precheck hook:
  1. Matches a queued entry by command_hash, removes it, and returns retry_count+1.
  2. Returns nothing (empty) for a command not in the queue.
  3. Handles corrupt queue file gracefully (no crash, no retry lift).
  4. Handles a missing queue file gracefully.
  5. Hash collision: removes only one entry per run (first match wins).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))

from lib.rate_limiter import RateLimitQueue  # noqa: E402

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helper: invoke the Python block of rate-limit-precheck.sh in-process
# ---------------------------------------------------------------------------

def _run_precheck_python(queue_file: str, cmd_hash: str) -> str:
    """Run the Python inline from rate-limit-precheck.sh and return stdout."""
    import subprocess as sp

    # Read the python3 -c "..." block from the hook
    hook_path = _PROJ_ROOT / "hooks" / "rate-limit-precheck.sh"
    source = hook_path.read_text()

    # Extract the python3 -c block
    start_marker = 'RESULT=$(python3 -c "\n'
    end_marker = '" "$QUEUE_FILE" "$CMD_HASH" 2>/dev/null)'

    if start_marker not in source:
        raise ValueError("Could not find python3 -c block in precheck hook")
    start = source.index(start_marker) + len(start_marker)
    end = source.index(end_marker, start)
    py_code = source[start:end]

    result = sp.run(
        ["python3", "-c", py_code, queue_file, cmd_hash],
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.stdout.strip()


def _write_queue(queue_file: Path, items: list) -> None:
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    with open(queue_file, "w") as f:
        json.dump(items, f)


def _read_queue(queue_file: Path) -> list:
    with open(queue_file) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Test 1: match lifts retry_count and removes entry
# ---------------------------------------------------------------------------

def test_precheck_match_lifts_retry_and_removes_entry(tmp_path: Path) -> None:
    """A queued entry matching command_hash is removed and retry_count+1 returned."""
    queue_file = tmp_path / "rate-limit-queue.json"
    _write_queue(queue_file, [
        {
            "queue_id": "abc12345",
            "action_type": "bash_command",
            "context": {"command": "echo hello", "command_hash": "deadbeef01234567"},
            "priority": 5,
            "enqueued_at": time.time() - 10,
            "eligible_at": time.time() - 1,
            "retry_count": 2,
        }
    ])

    result = _run_precheck_python(str(queue_file), "deadbeef01234567")
    assert result == "3", f"Expected retry_count+1=3, got {result!r}"

    # Entry must be removed from queue
    remaining = _read_queue(queue_file)
    assert len(remaining) == 0, f"Entry not removed: {remaining}"


# ---------------------------------------------------------------------------
# Test 2: no match — passthrough, queue unchanged
# ---------------------------------------------------------------------------

def test_precheck_no_match_passthrough(tmp_path: Path) -> None:
    """When no entry matches command_hash, output is empty and queue unchanged."""
    queue_file = tmp_path / "rate-limit-queue.json"
    item = {
        "queue_id": "abc12345",
        "action_type": "bash_command",
        "context": {"command": "echo hello", "command_hash": "aaaa0000bbbb1111"},
        "priority": 5,
        "enqueued_at": time.time(),
        "eligible_at": time.time() + 60,
        "retry_count": 1,
    }
    _write_queue(queue_file, [item])

    result = _run_precheck_python(str(queue_file), "0000000000000000")
    assert result == "", f"Expected empty output for no match, got {result!r}"

    remaining = _read_queue(queue_file)
    assert len(remaining) == 1, "Queue should be unchanged"


# ---------------------------------------------------------------------------
# Test 3: corrupt queue — no crash, empty output
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("corrupt_content", [
    "not json at all",
    '{"not": "a list"}',
    "",
])
def test_precheck_corrupt_queue_no_crash(tmp_path: Path, corrupt_content: str) -> None:
    """Corrupt queue file must not crash the hook; output is empty."""
    queue_file = tmp_path / "rate-limit-queue.json"
    queue_file.write_text(corrupt_content)

    result = _run_precheck_python(str(queue_file), "deadbeef01234567")
    assert result == "", f"Expected empty output for corrupt queue, got {result!r}"


# ---------------------------------------------------------------------------
# Test 4: missing queue file — no crash, empty output
# ---------------------------------------------------------------------------

def test_precheck_missing_queue_no_crash(tmp_path: Path) -> None:
    """Non-existent queue file must not crash the hook; output is empty."""
    queue_file = tmp_path / "nonexistent-queue.json"
    result = _run_precheck_python(str(queue_file), "deadbeef01234567")
    assert result == "", f"Expected empty output for missing queue, got {result!r}"


# ---------------------------------------------------------------------------
# Test 5: hash collision — only one entry removed per run
# ---------------------------------------------------------------------------

def test_precheck_hash_collision_removes_one(tmp_path: Path) -> None:
    """When two entries share the same command_hash, only the first is removed."""
    queue_file = tmp_path / "rate-limit-queue.json"
    shared_hash = "cafecafe12345678"
    _write_queue(queue_file, [
        {
            "queue_id": "first001",
            "action_type": "bash_command",
            "context": {"command": "echo first", "command_hash": shared_hash},
            "priority": 5,
            "enqueued_at": time.time() - 20,
            "eligible_at": time.time() - 1,
            "retry_count": 1,
        },
        {
            "queue_id": "second02",
            "action_type": "bash_command",
            "context": {"command": "echo second", "command_hash": shared_hash},
            "priority": 5,
            "enqueued_at": time.time() - 10,
            "eligible_at": time.time() - 1,
            "retry_count": 0,
        },
    ])

    result = _run_precheck_python(str(queue_file), shared_hash)
    assert result == "2", f"Expected retry_count+1=2 from first match, got {result!r}"

    remaining = _read_queue(queue_file)
    assert len(remaining) == 1, f"Expected 1 remaining item, got {len(remaining)}"
    assert remaining[0]["queue_id"] == "second02", "Wrong entry was removed"
