"""Behavior tests for generator-evaluator loop logic.

Migrated from test-gen-eval-loop.sh.
"""

import time
from pathlib import Path
from typing import Optional

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Helpers: replicate the bash loop_decision and DAG state logic in Python
# ---------------------------------------------------------------------------


def loop_decision(
    verdict: str,
    has_criticals: bool,
    retry_count: int,
    max_retries: int = 3,
) -> tuple[str, int]:
    """Simulate the orchestrator's decision after verify.

    Returns (action, return_code) where action is "retry" | "archive" | "escalate".
    """
    if verdict in ("PASS", "PASS WITH WARNINGS"):
        return "archive", 0
    if verdict == "FAIL":
        if has_criticals:
            if retry_count < max_retries:
                return "retry", 0
            else:
                return "escalate", 1
        else:
            return "archive", 0
    # Unknown verdict
    return "escalate", 1


def write_dag_state(
    dag_dir: Path, change_name: str, phase: str, retry_count: int
) -> None:
    """Write DAG state to a file."""
    state_file = dag_dir / f"{change_name}.state"
    state_file.write_text(
        f"change_name={change_name}\n"
        f"phase={phase}\n"
        f"retry_count={retry_count}\n"
        f"timestamp={int(time.time())}\n"
    )


def read_dag_state(dag_dir: Path, change_name: str) -> Optional[dict]:
    """Read DAG state from a file, returning parsed key=value pairs."""
    state_file = dag_dir / f"{change_name}.state"
    if not state_file.exists():
        return None
    result = {}
    for line in state_file.read_text().strip().splitlines():
        key, _, value = line.partition("=")
        result[key] = value
    return result


# ---------------------------------------------------------------------------
# Tests: loop_decision
# ---------------------------------------------------------------------------


class TestLoopDecision:
    """Tests for the loop_decision function."""

    def test_pass_archives(self):
        action, rc = loop_decision("PASS", False, 0)
        assert action == "archive"
        assert rc == 0

    def test_pass_with_warnings_archives(self):
        action, rc = loop_decision("PASS WITH WARNINGS", False, 0)
        assert action == "archive"
        assert rc == 0

    @pytest.mark.parametrize("retry_count", [0, 1, 2])
    def test_fail_criticals_retries(self, retry_count: int):
        action, rc = loop_decision("FAIL", True, retry_count)
        assert action == "retry"
        assert rc == 0

    def test_fail_criticals_retry_3_escalates(self):
        action, rc = loop_decision("FAIL", True, 3)
        assert action == "escalate"
        assert rc == 1

    def test_fail_no_criticals_archives(self):
        action, rc = loop_decision("FAIL", False, 0)
        assert action == "archive"
        assert rc == 0


# ---------------------------------------------------------------------------
# Tests: DAG state management
# ---------------------------------------------------------------------------


class TestDagState:
    """Tests for DAG state write/read round-trip."""

    def test_roundtrip(self, tmp_path: Path):
        dag_dir = tmp_path / "dag-state"
        dag_dir.mkdir()
        write_dag_state(dag_dir, "my-change", "verify", 2)
        state = read_dag_state(dag_dir, "my-change")
        assert state is not None
        assert state["retry_count"] == "2"

    def test_increment(self, tmp_path: Path):
        dag_dir = tmp_path / "dag-state"
        dag_dir.mkdir()

        write_dag_state(dag_dir, "inc-change", "apply", 0)
        state = read_dag_state(dag_dir, "inc-change")
        assert state["retry_count"] == "0"

        write_dag_state(dag_dir, "inc-change", "verify", 1)
        state = read_dag_state(dag_dir, "inc-change")
        assert state["retry_count"] == "1"

        write_dag_state(dag_dir, "inc-change", "verify", 2)
        state = read_dag_state(dag_dir, "inc-change")
        assert state["retry_count"] == "2"

    def test_parseable_format(self, tmp_path: Path):
        dag_dir = tmp_path / "dag-state"
        dag_dir.mkdir()
        write_dag_state(dag_dir, "parse-test", "spec", 1)
        state = read_dag_state(dag_dir, "parse-test")
        assert state is not None
        for field in ("change_name", "phase", "retry_count", "timestamp"):
            assert field in state, f"Missing field: {field}"
