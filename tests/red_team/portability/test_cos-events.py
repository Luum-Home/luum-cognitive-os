# SCOPE: both
# scope: both
"""
Portability probes for scripts/cos-events.sh / lib/event_bus.py — P1.3.

These tests invoke the CLI against temporary, non-SO project directories to
prove that the event bus does not depend on repository-local runtime state or
require a running Cognitive OS stack.

Run with:
    python3 -m pytest tests/red_team/portability/test_cos-events.py -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PYTHON = sys.executable
# The CLI entry point (bash wrapper delegates to inline Python using sys.executable)
CLI_SH = REPO_ROOT / "scripts" / "cos-events.sh"


def run_cli(bus_path: Path, *args: str) -> "subprocess.CompletedProcess[str]":
    """Run cos-events.sh with EVENTS_BUS_PATH overridden."""
    env = {**os.environ, "EVENTS_BUS_PATH": str(bus_path)}
    return subprocess.run(
        ["bash", str(CLI_SH), *args],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
        env=env,
    )


# ---------------------------------------------------------------------------
# Proof 1: emit + tail work without a .cognitive-os tree
# ---------------------------------------------------------------------------

def test_emit_tail_without_cogos_tree(tmp_path: Path) -> None:
    """Bus works in a plain empty directory (no .cognitive-os directory)."""
    bus = tmp_path / "events.jsonl"
    # There is no .cognitive-os here — the bus must create the file itself.

    result = run_cli(bus, "emit", "task_completed", "--payload", '{"task_id":"portability-1"}')
    assert result.returncode == 0, f"emit failed: {result.stderr}"

    result2 = run_cli(bus, "tail")
    assert result2.returncode == 0, f"tail failed: {result2.stderr}"

    events = [json.loads(l) for l in result2.stdout.splitlines() if l.strip()]
    assert len(events) == 1
    assert events[0]["event_type"] == "task_completed"
    assert events[0]["payload"]["task_id"] == "portability-1"


# ---------------------------------------------------------------------------
# Proof 2: stats returns zero-count gracefully on a fresh bus
# ---------------------------------------------------------------------------

def test_stats_on_empty_bus(tmp_path: Path) -> None:
    """stats subcommand exits 0 and emits a 'no events' notice for empty bus."""
    bus = tmp_path / "events.jsonl"

    result = run_cli(bus, "stats", "--window", "60")
    assert result.returncode == 0, f"stats failed: {result.stderr}"
    # Output should contain the no-events message or be blank.
    assert "no events" in result.stdout.lower() or result.stdout.strip() == ""


# ---------------------------------------------------------------------------
# Proof 3: unknown event_type rejected with non-zero exit + no file pollution
# ---------------------------------------------------------------------------

def test_unknown_event_type_rejected(tmp_path: Path) -> None:
    """Emitting an unknown event_type must exit non-zero and leave no data."""
    bus = tmp_path / "events.jsonl"

    result = run_cli(bus, "emit", "totally_unknown_type", "--payload", "{}")
    assert result.returncode != 0, "Expected non-zero exit for unknown event_type"

    # The bus file should either not exist or be empty (no partial record).
    if bus.exists():
        content = bus.read_text("utf-8").strip()
        assert content == "", f"Bus file should be empty, got: {content!r}"
