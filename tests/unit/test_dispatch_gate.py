"""Unit tests for hooks/dispatch-gate.sh logic.

Tests the Python slot-counting logic used by dispatch-gate.sh directly,
plus checks that the hook file exists and is executable.
"""
import json
import os
import stat
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Helpers — replicate the Python snippets embedded in dispatch-gate.sh
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "../..")
_HOOK_PATH = os.path.join(_PROJECT_ROOT, "hooks/dispatch-gate.sh")
_CHECK_PATH = os.path.join(_PROJECT_ROOT, "hooks/_lib/dispatch_gate_check.py")


def _count_in_progress(tasks_path: str) -> int:
    """Mirror the ACTIVE counting Python snippet from dispatch-gate.sh."""
    try:
        with open(tasks_path) as f:
            data = json.load(f)
        return sum(1 for t in data.get("tasks", []) if t.get("status") == "in_progress")
    except Exception:
        return 0


def _read_max_agents(cfg_path: str) -> int:
    """Mirror the MAX_AGENTS reading Python snippet from dispatch-gate.sh."""
    try:
        import yaml  # noqa: PLC0415 — optional dep, only needed for this test

        with open(cfg_path) as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("resources", {}).get("compute", {}).get("max_parallel_agents", 5)
    except Exception:
        return 5


def _is_blocked(active: int, max_agents: int) -> bool:
    """Dispatch decision: blocked when active >= max."""
    return active >= max_agents


def _iso_age(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


# ---------------------------------------------------------------------------
# Hook file existence and permissions
# ---------------------------------------------------------------------------


class TestHookFile:
    def test_hook_exists(self):
        assert os.path.isfile(_HOOK_PATH), f"Hook not found: {_HOOK_PATH}"

    def test_hook_is_executable(self):
        mode = os.stat(_HOOK_PATH).st_mode
        assert mode & stat.S_IXUSR, "Hook is not user-executable"

    def test_hook_syntax(self):
        """bash -n check: validate syntax without executing."""
        import subprocess  # noqa: PLC0415

        result = subprocess.run(
            ["bash", "-n", _HOOK_PATH],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error:\n{result.stderr}"


# ---------------------------------------------------------------------------
# Slot counting: _count_in_progress
# ---------------------------------------------------------------------------


class TestCountInProgress:
    def test_no_tasks_file_returns_zero(self, tmp_path):
        missing = str(tmp_path / "nonexistent.json")
        assert _count_in_progress(missing) == 0

    def test_empty_tasks_list(self, tmp_path):
        p = tmp_path / "active-tasks.json"
        p.write_text(json.dumps({"tasks": []}))
        assert _count_in_progress(str(p)) == 0

    def test_counts_only_in_progress(self, tmp_path):
        p = tmp_path / "active-tasks.json"
        p.write_text(
            json.dumps(
                {
                    "tasks": [
                        {"id": "t1", "status": "in_progress"},
                        {"id": "t2", "status": "completed"},
                        {"id": "t3", "status": "in_progress"},
                        {"id": "t4", "status": "pending"},
                        {"id": "t5", "status": "failed"},
                    ]
                }
            )
        )
        assert _count_in_progress(str(p)) == 2

    def test_all_in_progress(self, tmp_path):
        p = tmp_path / "active-tasks.json"
        tasks = [{"id": f"t{i}", "status": "in_progress"} for i in range(5)]
        p.write_text(json.dumps({"tasks": tasks}))
        assert _count_in_progress(str(p)) == 5

    def test_missing_tasks_key_returns_zero(self, tmp_path):
        p = tmp_path / "active-tasks.json"
        p.write_text(json.dumps({}))
        assert _count_in_progress(str(p)) == 0

    def test_malformed_json_returns_zero(self, tmp_path):
        p = tmp_path / "active-tasks.json"
        p.write_text("not valid json{{")
        assert _count_in_progress(str(p)) == 0


# ---------------------------------------------------------------------------
# Block decision: _is_blocked
# ---------------------------------------------------------------------------


class TestBlockDecision:
    def test_zero_active_not_blocked(self):
        assert _is_blocked(0, 5) is False

    def test_below_max_not_blocked(self):
        assert _is_blocked(3, 5) is False

    def test_one_below_max_not_blocked(self):
        assert _is_blocked(4, 5) is False

    def test_at_capacity_is_blocked(self):
        assert _is_blocked(5, 5) is True

    def test_over_capacity_is_blocked(self):
        assert _is_blocked(7, 5) is True

    def test_max_one_slot(self):
        assert _is_blocked(0, 1) is False
        assert _is_blocked(1, 1) is True

    def test_unlimited_slots(self):
        # max=0 means everything is blocked (0 slots allowed)
        assert _is_blocked(0, 0) is True


# ---------------------------------------------------------------------------
# Config reading: _read_max_agents
# ---------------------------------------------------------------------------


class TestReadMaxAgents:
    def test_missing_config_returns_default(self, tmp_path):
        assert _read_max_agents(str(tmp_path / "nonexistent.yaml")) == 5

    def test_reads_configured_value(self, tmp_path):
        p = tmp_path / "cognitive-os.yaml"
        p.write_text("resources:\n  compute:\n    max_parallel_agents: 10\n")
        assert _read_max_agents(str(p)) == 10

    def test_missing_key_returns_default(self, tmp_path):
        p = tmp_path / "cognitive-os.yaml"
        p.write_text("resources:\n  budget:\n    daily_alert_usd: 5\n")
        assert _read_max_agents(str(p)) == 5

    def test_empty_config_returns_default(self, tmp_path):
        p = tmp_path / "cognitive-os.yaml"
        p.write_text("")
        assert _read_max_agents(str(p)) == 5


# ---------------------------------------------------------------------------
# End-to-end: slot counting + block decision together
# ---------------------------------------------------------------------------


class TestDispatchGateEndToEnd:
    def _make_tasks(self, tmp_path, in_progress: int, other: int = 0) -> str:
        tasks = [{"id": f"ip{i}", "status": "in_progress"} for i in range(in_progress)]
        tasks += [{"id": f"ot{i}", "status": "completed"} for i in range(other)]
        p = tmp_path / "active-tasks.json"
        p.write_text(json.dumps({"tasks": tasks}))
        return str(p)

    def test_no_active_agents_allowed(self, tmp_path):
        tasks_path = self._make_tasks(tmp_path, in_progress=0)
        active = _count_in_progress(tasks_path)
        assert not _is_blocked(active, 5)

    def test_partially_filled_slots_allowed(self, tmp_path):
        tasks_path = self._make_tasks(tmp_path, in_progress=3, other=10)
        active = _count_in_progress(tasks_path)
        assert not _is_blocked(active, 5)

    def test_full_capacity_blocked(self, tmp_path):
        tasks_path = self._make_tasks(tmp_path, in_progress=5)
        active = _count_in_progress(tasks_path)
        assert _is_blocked(active, 5)

    def test_over_capacity_still_blocked(self, tmp_path):
        tasks_path = self._make_tasks(tmp_path, in_progress=8)
        active = _count_in_progress(tasks_path)
        assert _is_blocked(active, 5)

    def test_custom_max_from_config(self, tmp_path):
        # max=2, only 1 in_progress → allowed
        tasks_path = self._make_tasks(tmp_path, in_progress=1)
        active = _count_in_progress(tasks_path)
        assert not _is_blocked(active, 2)

        # max=2, now 2 in_progress → blocked
        tasks_path = self._make_tasks(tmp_path, in_progress=2)
        active = _count_in_progress(tasks_path)
        assert _is_blocked(active, 2)

    def test_dispatch_gate_check_excludes_zombie_and_stale_starting_records(self, tmp_path):
        tasks_dir = tmp_path / ".cognitive-os" / "tasks"
        tasks_dir.mkdir(parents=True)
        (tmp_path / "cognitive-os.yaml").write_text(
            "resources:\n  compute:\n    max_parallel_agents: 5\n"
        )
        (tasks_dir / "active-tasks.json").write_text(
            json.dumps(
                {
                    "tasks": [
                        {"id": "live", "status": "in_progress", "pid": os.getpid()},
                        {"id": "dead", "status": "in_progress", "pid": 99999999},
                        {
                            "id": "stale-pidless",
                            "status": "in_progress",
                            "pid": None,
                            "started_at": _iso_age(4000),
                        },
                        {
                            "id": "fresh-pidless",
                            "status": "in_progress",
                            "pid": None,
                            "started_at": _iso_age(30),
                        },
                        {"id": "pending", "status": "pending", "pid": None},
                    ]
                }
            )
        )
        env = os.environ.copy()
        env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)

        result = subprocess.run(
            ["python3", _CHECK_PATH],
            input=json.dumps({"tool_input": {"description": "test"}}),
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["active"] == 2
