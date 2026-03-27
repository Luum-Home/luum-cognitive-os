"""Unit tests for hooks/_lib/circuit-breaker.sh

Validates circuit breaker state machine: CLOSED -> OPEN -> HALF-OPEN transitions,
failure counting, cooldown behavior, success resets, global budget enforcement,
and status output formatting.
"""
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LIB_DIR = PROJECT_ROOT / "hooks" / "_lib"
CB_LIB = LIB_DIR / "circuit-breaker.sh"
JSONL_LIB = LIB_DIR / "safe-jsonl.sh"


@pytest.fixture
def cb_env(tmp_path):
    """Set up a circuit breaker test environment with sourced libraries."""
    project_dir = tmp_path / "project"
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)

    env = {
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        "COGNITIVE_OS_SESSION_ID": "",
        "COGNITIVE_OS_CB_MAX_FAILURES": "2",
        "COGNITIVE_OS_CB_COOLDOWN": "5",
        "COGNITIVE_OS_CB_HOURLY_CAP": "10",
    }

    preamble = (
        f'_SAFE_JSONL_LOADED=""\n'
        f'source "{JSONL_LIB}"\n'
        f'source "{CB_LIB}"\n'
    )

    return {
        "env": env,
        "project_dir": project_dir,
        "metrics_dir": metrics_dir,
        "preamble": preamble,
    }


def _run(cb_env, script_body: str) -> subprocess.CompletedProcess:
    """Run a bash script with the circuit breaker environment."""
    full_script = cb_env["preamble"] + script_body
    run_env = {**os.environ, **cb_env["env"]}
    return subprocess.run(
        ["bash", "-c", full_script],
        capture_output=True, text=True, env=run_env,
    )


class TestCbCheckClosedNoState:
    """cb_check returns 0 (CLOSED) when there is no prior state."""

    def test_returns_zero(self, cb_env):
        result = _run(cb_env, 'cb_check "TEST" "service-a"; exit $?')
        assert result.returncode == 0


class TestRecordFailureIncrements:
    """cb_record_failure increments the consecutive_failures counter."""

    def test_first_failure_sets_counter_to_one(self, cb_env):
        result = _run(cb_env, '''
            cb_record_failure "TEST" "service-a"
            state_dir=$(_cb_state_dir)
            key=$(_cb_key "TEST" "service-a")
            jq -r '.consecutive_failures' "$state_dir/$key.json"
        ''')
        assert result.stdout.strip() == "1"


class TestTwoFailuresTripBreaker:
    """Two consecutive failures transition the breaker to OPEN state."""

    def test_state_is_open(self, cb_env):
        result = _run(cb_env, '''
            cb_record_failure "BUILD" "service-b"
            cb_record_failure "BUILD" "service-b"
            state_dir=$(_cb_state_dir)
            key=$(_cb_key "BUILD" "service-b")
            jq -r '.state' "$state_dir/$key.json"
        ''')
        assert result.stdout.strip() == "open"


class TestCheckReturnsOneWhenOpen:
    """cb_check returns 1 when the breaker is in OPEN state."""

    def test_returns_one(self, cb_env):
        result = _run(cb_env, '''
            cb_record_failure "LINT" "service-c"
            cb_record_failure "LINT" "service-c"
            cb_check "LINT" "service-c"
            exit $?
        ''')
        assert result.returncode == 1


class TestCooldownHalfOpen:
    """After cooldown expires, breaker transitions from OPEN to HALF-OPEN."""

    def test_check_returns_zero_after_cooldown(self, cb_env):
        """cb_check returns 0 (allowing a probe) after cooldown period."""
        result = _run(cb_env, '''
            cb_record_failure "TEST" "service-d"
            cb_record_failure "TEST" "service-d"
            state_dir=$(_cb_state_dir)
            key=$(_cb_key "TEST" "service-d")
            past_epoch=$(( $(date +%s) - 10 ))
            _cb_write_state "$state_dir/$key.json" "open" 2 "$past_epoch"
            cb_check "TEST" "service-d"
            exit $?
        ''')
        assert result.returncode == 0

    def test_state_is_half_open(self, cb_env):
        """State file shows half-open after cooldown probe."""
        result = _run(cb_env, '''
            cb_record_failure "TEST" "service-d"
            cb_record_failure "TEST" "service-d"
            state_dir=$(_cb_state_dir)
            key=$(_cb_key "TEST" "service-d")
            past_epoch=$(( $(date +%s) - 10 ))
            _cb_write_state "$state_dir/$key.json" "open" 2 "$past_epoch"
            cb_check "TEST" "service-d"
            jq -r '.state' "$state_dir/$key.json"
        ''')
        assert result.stdout.strip() == "half-open"


class TestRecordSuccessResets:
    """cb_record_success resets the breaker to CLOSED with zero failures."""

    def test_state_closed_and_failures_zero(self, cb_env):
        result = _run(cb_env, '''
            cb_record_failure "BUILD" "service-e"
            cb_record_success "BUILD" "service-e"
            state_dir=$(_cb_state_dir)
            key=$(_cb_key "BUILD" "service-e")
            echo "$(jq -r '.state' "$state_dir/$key.json")"
            echo "$(jq -r '.consecutive_failures' "$state_dir/$key.json")"
        ''')
        lines = result.stdout.strip().split("\n")
        assert lines[0] == "closed"
        assert lines[1] == "0"


class TestResetClearsState:
    """cb_reset removes the state file entirely."""

    def test_state_file_removed(self, cb_env):
        result = _run(cb_env, '''
            cb_record_failure "TEST" "service-f"
            cb_reset "TEST" "service-f"
            state_dir=$(_cb_state_dir)
            key=$(_cb_key "TEST" "service-f")
            if [ ! -f "$state_dir/$key.json" ]; then
                echo "REMOVED"
            else
                echo "EXISTS"
            fi
        ''')
        assert result.stdout.strip() == "REMOVED"

    def test_check_returns_zero_after_reset(self, cb_env):
        result = _run(cb_env, '''
            cb_record_failure "TEST" "service-f"
            cb_reset "TEST" "service-f"
            cb_check "TEST" "service-f"
            exit $?
        ''')
        assert result.returncode == 0


class TestGlobalBudget:
    """cb_global_budget_ok enforces the hourly repair cap."""

    def test_ok_with_no_outcomes(self, cb_env):
        """Budget is OK when no outcomes file exists."""
        result = _run(cb_env, 'cb_global_budget_ok; exit $?')
        assert result.returncode == 0

    def test_exceeded_with_many_entries(self, cb_env):
        """Budget is exceeded when entries surpass the hourly cap."""
        outcomes_file = cb_env["metrics_dir"] / "repair-outcomes.jsonl"
        now_epoch = int(time.time())
        with open(outcomes_file, "w") as f:
            for i in range(11):
                entry = {
                    "timestamp_epoch": now_epoch,
                    "error_type": "TEST",
                    "service": "svc",
                    "outcome": "failure",
                }
                f.write(json.dumps(entry) + "\n")

        result = _run(cb_env, '''
            export COGNITIVE_OS_CB_HOURLY_CAP=10
            source "''' + str(CB_LIB) + '''"
            cb_global_budget_ok
            exit $?
        ''')
        assert result.returncode == 1


class TestStatusOutput:
    """cb_status produces correctly formatted output."""

    def test_header_present(self, cb_env):
        """Output contains the 'Circuit Breaker Status' header."""
        result = _run(cb_env, 'cb_status 2>&1')
        assert "Circuit Breaker Status" in result.stdout

    def test_shows_open_breaker(self, cb_env):
        """Output shows OPEN state after tripping a breaker."""
        result = _run(cb_env, '''
            cb_record_failure "TEST" "svc-g"
            cb_record_failure "TEST" "svc-g"
            cb_status 2>&1
        ''')
        assert "OPEN" in result.stdout
