"""Behavior tests for SDD state transitions.

Migrated from test-sdd-transitions.sh.
"""

import time
from pathlib import Path
from typing import Optional

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Transition map
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[str, set[str]] = {
    "proposal": {"spec", "design"},
    "spec": {"tasks", "design"},
    "design": {"tasks"},
    "tasks": {"apply"},
    "apply": {"verify"},
    "verify": {"archive", "apply"},
}


def validate_transition(current: str, next_phase: str) -> tuple[str, int]:
    """Check if a phase transition is valid.

    Returns (next_phase, 0) if valid, ("invalid", 1) if not.
    """
    allowed = VALID_TRANSITIONS.get(current, set())
    if next_phase in allowed:
        return next_phase, 0
    return "invalid", 1


# ---------------------------------------------------------------------------
# DAG state helpers
# ---------------------------------------------------------------------------


def write_phase_state(dag_dir: Path, change_name: str, phase: str) -> None:
    state_file = dag_dir / f"{change_name}.state"
    state_file.write_text(
        f"change_name={change_name}\n"
        f"phase={phase}\n"
        f"timestamp={int(time.time())}\n"
    )


def read_phase(dag_dir: Path, change_name: str) -> Optional[str]:
    state_file = dag_dir / f"{change_name}.state"
    if not state_file.exists():
        return None
    for line in state_file.read_text().strip().splitlines():
        key, _, value = line.partition("=")
        if key == "phase":
            return value
    return None


# ---------------------------------------------------------------------------
# Tests: Valid transitions
# ---------------------------------------------------------------------------


class TestValidTransitions:

    @pytest.mark.parametrize(
        "current,next_phase",
        [
            ("proposal", "spec"),
            ("proposal", "design"),
            ("spec", "design"),
            ("design", "tasks"),
            ("tasks", "apply"),
            ("apply", "verify"),
            ("verify", "archive"),
            ("verify", "apply"),
        ],
    )
    def test_valid_transition(self, current: str, next_phase: str):
        output, rc = validate_transition(current, next_phase)
        assert output == next_phase
        assert rc == 0


# ---------------------------------------------------------------------------
# Tests: Invalid transitions
# ---------------------------------------------------------------------------


class TestInvalidTransitions:

    @pytest.mark.parametrize(
        "current,next_phase",
        [
            ("proposal", "apply"),
            ("spec", "archive"),
            ("archive", "proposal"),
            ("tasks", "archive"),
            ("design", "verify"),
        ],
    )
    def test_invalid_transition(self, current: str, next_phase: str):
        output, rc = validate_transition(current, next_phase)
        assert output == "invalid"
        assert rc == 1


# ---------------------------------------------------------------------------
# Tests: DAG state management
# ---------------------------------------------------------------------------


class TestPhaseState:

    def test_roundtrip(self, tmp_path: Path):
        dag_dir = tmp_path / "dag-state"
        dag_dir.mkdir()
        write_phase_state(dag_dir, "my-feature", "spec")
        assert read_phase(dag_dir, "my-feature") == "spec"

    def test_progression(self, tmp_path: Path):
        dag_dir = tmp_path / "dag-state"
        dag_dir.mkdir()

        write_phase_state(dag_dir, "my-feature", "proposal")
        assert read_phase(dag_dir, "my-feature") == "proposal"

        write_phase_state(dag_dir, "my-feature", "spec")
        assert read_phase(dag_dir, "my-feature") == "spec"

        write_phase_state(dag_dir, "my-feature", "tasks")
        assert read_phase(dag_dir, "my-feature") == "tasks"
