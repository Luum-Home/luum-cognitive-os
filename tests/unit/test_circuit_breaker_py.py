"""Unit tests for lib/circuit_breaker.py

Validates the Python CircuitBreaker state machine:
  CLOSED → OPEN on consecutive failures
  OPEN   → HALF_OPEN after cooldown
  HALF_OPEN → CLOSED on success
  can_launch() returns False only when OPEN and cooldown still active
  State persistence: write and read back from JSON
"""
import json
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cb(tmp_path: Path, failure_threshold: int = 3, cooldown_seconds: int = 3600):
    """Create a CircuitBreaker backed by a temp file."""
    from lib.circuit_breaker import CircuitBreaker

    state_file = tmp_path / "circuit-breaker-state.json"
    return CircuitBreaker(
        state_file=state_file,
        failure_threshold=failure_threshold,
        cooldown_seconds=cooldown_seconds,
    )


# ---------------------------------------------------------------------------
# Tests: initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    def test_can_launch_unknown_type_returns_true(self, tmp_path):
        cb = _make_cb(tmp_path)
        assert cb.can_launch("never-seen-before") is True

    def test_get_status_empty_initially(self, tmp_path):
        cb = _make_cb(tmp_path)
        assert cb.get_status() == {}


# ---------------------------------------------------------------------------
# Tests: failure counting and OPEN transition
# ---------------------------------------------------------------------------


class TestFailureCounting:
    def test_single_failure_stays_closed(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=3)
        cb.record_failure("sdd-apply")
        assert cb.can_launch("sdd-apply") is True

    def test_two_failures_stay_closed_when_threshold_is_3(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=3)
        cb.record_failure("sdd-apply")
        cb.record_failure("sdd-apply")
        assert cb.can_launch("sdd-apply") is True

    def test_three_failures_open_circuit(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=3)
        cb.record_failure("sdd-apply")
        cb.record_failure("sdd-apply")
        cb.record_failure("sdd-apply")
        status = cb.get_status()
        assert status["sdd-apply"]["state"] == "open"

    def test_can_launch_returns_false_when_open(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=3, cooldown_seconds=9999)
        for _ in range(3):
            cb.record_failure("sdd-apply")
        assert cb.can_launch("sdd-apply") is False

    def test_failure_count_tracked(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=10)
        for _ in range(4):
            cb.record_failure("build")
        assert cb.get_status()["build"]["failure_count"] == 4

    def test_opened_at_set_when_tripped(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=2)
        cb.record_failure("t")
        cb.record_failure("t")
        assert cb.get_status()["t"]["opened_at"] is not None

    def test_threshold_of_1_opens_on_first_failure(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=1)
        cb.record_failure("fragile-task")
        assert cb.get_status()["fragile-task"]["state"] == "open"
        assert cb.can_launch("fragile-task") is False


# ---------------------------------------------------------------------------
# Tests: cooldown → HALF_OPEN
# ---------------------------------------------------------------------------


class TestCooldown:
    def test_open_with_expired_cooldown_transitions_to_half_open(self, tmp_path):
        """When the cooldown has elapsed, can_launch() returns True and
        the circuit moves to HALF_OPEN."""
        cb = _make_cb(tmp_path, failure_threshold=2, cooldown_seconds=1)
        cb.record_failure("slow-task")
        cb.record_failure("slow-task")
        assert cb.can_launch("slow-task") is False  # just opened, cooldown not elapsed

        # Manually backdate opened_at to simulate elapsed cooldown
        from lib.circuit_breaker import _now_epoch
        circuit = cb._circuits["slow-task"]
        from datetime import datetime, timezone
        past = datetime.fromtimestamp(_now_epoch() - 10, tz=timezone.utc)
        circuit.opened_at = past.strftime("%Y-%m-%dT%H:%M:%SZ")
        cb._save()

        # Re-load from disk to prove persistence round-trip
        cb2 = _make_cb(tmp_path, failure_threshold=2, cooldown_seconds=1)
        assert cb2.can_launch("slow-task") is True

    def test_state_becomes_half_open_after_cooldown(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=2, cooldown_seconds=1)
        cb.record_failure("slow-task")
        cb.record_failure("slow-task")

        from lib.circuit_breaker import _now_epoch
        from datetime import datetime, timezone
        circuit = cb._circuits["slow-task"]
        past = datetime.fromtimestamp(_now_epoch() - 10, tz=timezone.utc)
        circuit.opened_at = past.strftime("%Y-%m-%dT%H:%M:%SZ")
        cb._save()

        cb2 = _make_cb(tmp_path, failure_threshold=2, cooldown_seconds=1)
        cb2.can_launch("slow-task")  # triggers transition
        assert cb2.get_status()["slow-task"]["state"] == "half_open"

    def test_open_within_cooldown_still_blocked(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=2, cooldown_seconds=9999)
        cb.record_failure("t")
        cb.record_failure("t")
        assert cb.can_launch("t") is False


# ---------------------------------------------------------------------------
# Tests: success resets circuit
# ---------------------------------------------------------------------------


class TestSuccessReset:
    def test_success_after_failures_resets_to_closed(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=3)
        cb.record_failure("sdd-verify")
        cb.record_failure("sdd-verify")
        cb.record_failure("sdd-verify")
        assert cb.get_status()["sdd-verify"]["state"] == "open"

        cb.record_success("sdd-verify")
        assert cb.get_status()["sdd-verify"]["state"] == "closed"

    def test_success_resets_failure_count(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=3)
        for _ in range(3):
            cb.record_failure("t")
        cb.record_success("t")
        assert cb.get_status()["t"]["failure_count"] == 0

    def test_success_after_half_open_closes_circuit(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=2, cooldown_seconds=1)
        cb.record_failure("t")
        cb.record_failure("t")
        # Simulate cooldown expiry
        from lib.circuit_breaker import _now_epoch
        from datetime import datetime, timezone
        circuit = cb._circuits["t"]
        past = datetime.fromtimestamp(_now_epoch() - 10, tz=timezone.utc)
        circuit.opened_at = past.strftime("%Y-%m-%dT%H:%M:%SZ")
        cb._save()

        cb2 = _make_cb(tmp_path, failure_threshold=2, cooldown_seconds=1)
        cb2.can_launch("t")  # → HALF_OPEN
        assert cb2.get_status()["t"]["state"] == "half_open"
        cb2.record_success("t")
        assert cb2.get_status()["t"]["state"] == "closed"

    def test_can_launch_returns_true_after_success_reset(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=2, cooldown_seconds=9999)
        cb.record_failure("t")
        cb.record_failure("t")
        cb.record_success("t")
        assert cb.can_launch("t") is True


# ---------------------------------------------------------------------------
# Tests: persistence (write + read back)
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_state_persists_across_instances(self, tmp_path):
        state_file = tmp_path / "cb.json"
        from lib.circuit_breaker import CircuitBreaker

        cb1 = CircuitBreaker(state_file=state_file, failure_threshold=2)
        cb1.record_failure("pipeline")
        cb1.record_failure("pipeline")
        assert cb1.get_status()["pipeline"]["state"] == "open"

        cb2 = CircuitBreaker(state_file=state_file, failure_threshold=2)
        assert cb2.get_status()["pipeline"]["state"] == "open"
        assert cb2.can_launch("pipeline") is False

    def test_state_file_is_valid_json(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=2)
        cb.record_failure("x")
        raw = (tmp_path / "circuit-breaker-state.json").read_text()
        data = json.loads(raw)
        assert "x" in data

    def test_corrupt_state_file_starts_fresh(self, tmp_path):
        state_file = tmp_path / "cb.json"
        state_file.write_text("NOT JSON {{{{")
        from lib.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker(state_file=state_file)
        assert cb.get_status() == {}
        assert cb.can_launch("any-task") is True


# ---------------------------------------------------------------------------
# Tests: format_status
# ---------------------------------------------------------------------------


class TestFormatStatus:
    def test_empty_status_message(self, tmp_path):
        cb = _make_cb(tmp_path)
        msg = cb.format_status()
        assert "no circuits tracked" in msg

    def test_status_contains_task_type(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=3)
        cb.record_failure("my-task")
        msg = cb.format_status()
        assert "my-task" in msg

    def test_status_shows_open(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=2)
        cb.record_failure("t")
        cb.record_failure("t")
        msg = cb.format_status()
        assert "OPEN" in msg

    def test_status_shows_closed(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=3)
        cb.record_failure("t")
        msg = cb.format_status()
        assert "CLOSED" in msg

    def test_circuit_breaker_status_header(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=2)
        cb.record_failure("t")
        cb.record_failure("t")
        msg = cb.format_status()
        assert "Circuit Breaker Status" in msg


# ---------------------------------------------------------------------------
# Tests: multiple task types are independent
# ---------------------------------------------------------------------------


class TestIndependentTaskTypes:
    def test_failure_in_one_type_does_not_affect_another(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=2)
        cb.record_failure("type-a")
        cb.record_failure("type-a")
        assert cb.can_launch("type-a") is False
        assert cb.can_launch("type-b") is True

    def test_success_in_one_type_does_not_affect_another(self, tmp_path):
        cb = _make_cb(tmp_path, failure_threshold=2)
        cb.record_failure("type-a")
        cb.record_failure("type-a")
        cb.record_failure("type-b")
        cb.record_success("type-a")
        assert cb.can_launch("type-a") is True
        assert cb.can_launch("type-b") is True  # only 1 failure, still closed
