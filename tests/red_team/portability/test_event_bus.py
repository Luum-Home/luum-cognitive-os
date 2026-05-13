# SCOPE: os-only
# scope: both
"""
Portability proofs for packages/agent-coordination/lib/event_bus.py (symlinked
as lib/event_bus.py) — P1.3 / ADR-116.

These tests exercise the library directly (no OS-specific paths, no Cognitive
OS stack) to prove the primitive is portable across environments.

Run with:
    python3 -m pytest tests/red_team/portability/test_event_bus.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON = sys.executable
CLI_SH = REPO_ROOT / "scripts" / "cos-events.sh"

sys.path.insert(0, str(REPO_ROOT))

from lib.event_bus import emit, tail, EVENT_TYPES  # noqa: E402


# ---------------------------------------------------------------------------
# Proof 1: library works in an arbitrary temp directory (no .cognitive-os)
# ---------------------------------------------------------------------------

def test_emit_tail_plain_directory(tmp_path: Path) -> None:
    """emit + tail work when there is no .cognitive-os tree present."""
    bus = tmp_path / "events.jsonl"
    emit("session_started", {"env": "portability-test"}, session_id="port-1", bus_path=bus)

    events = list(tail(bus_path=bus))
    assert len(events) == 1
    ev = events[0]
    assert ev["event_type"] == "session_started"
    assert ev["session_id"] == "port-1"
    assert ev["payload"]["env"] == "portability-test"


# ---------------------------------------------------------------------------
# Proof 2: CLI emit + tail work without a .cognitive-os tree
# ---------------------------------------------------------------------------

def test_cli_emit_tail_plain_directory(tmp_path: Path) -> None:
    """CLI subcommands work outside the SO working directory."""
    bus = tmp_path / "events.jsonl"
    env = {**os.environ, "EVENTS_BUS_PATH": str(bus)}

    result = subprocess.run(
        ["bash", str(CLI_SH), "emit", "commit_landed",
         "--payload", '{"sha":"portability"}'],
        text=True, capture_output=True, timeout=10, check=False, env=env,
    )
    assert result.returncode == 0, f"emit failed: {result.stderr}"

    result2 = subprocess.run(
        ["bash", str(CLI_SH), "tail"],
        text=True, capture_output=True, timeout=10, check=False, env=env,
    )
    assert result2.returncode == 0
    events = [json.loads(l) for l in result2.stdout.splitlines() if l.strip()]
    assert any(e["event_type"] == "commit_landed" for e in events)


# ---------------------------------------------------------------------------
# Proof 3: EVENT_TYPES is a closed frozenset (falsification probe)
# ---------------------------------------------------------------------------

def test_event_types_is_closed_frozenset(tmp_path: Path) -> None:
    """Unknown event types are rejected; known ones are all accepted."""
    bus = tmp_path / "events.jsonl"

    # All valid types must emit without error.
    for et in EVENT_TYPES:
        emit(et, {}, bus_path=bus)

    events = list(tail(bus_path=bus))
    assert len(events) == len(EVENT_TYPES)

    # An unknown type must raise ValueError — the type set is closed.
    import pytest  # noqa: PLC0415
    with pytest.raises(ValueError):
        emit("__not_a_real_type__", {}, bus_path=bus)
