"""
tests/unit/test_detect_runner_capacity.py

Unit tests for scripts/detect_runner_capacity.py — ADR-068 Phase 1.

Each test stubs psutil and os-level calls so the heuristic is exercised
in isolation, without touching real hardware.
"""

from __future__ import annotations
import importlib
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper: import the script as a module regardless of whether it lives in
# scripts/ (not a package).  We do this once per test file load.
# ---------------------------------------------------------------------------
def _import_script():
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
    scripts_dir = os.path.normpath(scripts_dir)
    script_path = os.path.join(scripts_dir, "detect_runner_capacity.py")
    spec = importlib.util.spec_from_file_location("detect_runner_capacity", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_mod = _import_script()


# ---------------------------------------------------------------------------
# Shared stub builders
# ---------------------------------------------------------------------------
def _make_psutil_stub(
    *,
    mem_available_bytes: int = 16 * 1024 ** 3,
    cpu_percent: float = 10.0,
    battery_percent: float | None = None,
    power_plugged: bool = True,
) -> types.ModuleType:
    """Return a minimal psutil stub."""
    psutil = types.ModuleType("psutil")

    # virtual_memory
    vm = MagicMock()
    vm.available = mem_available_bytes
    psutil.virtual_memory = MagicMock(return_value=vm)

    # cpu_percent (used on Windows path)
    psutil.cpu_percent = MagicMock(return_value=cpu_percent)

    # sensors_battery
    if battery_percent is not None:
        batt = MagicMock()
        batt.percent = battery_percent
        batt.power_plugged = power_plugged
        psutil.sensors_battery = MagicMock(return_value=batt)
    else:
        psutil.sensors_battery = MagicMock(return_value=None)

    return psutil


def _run_detect(
    *,
    cores: int = 8,
    load_avg: tuple[float, float, float] = (0.8, 0.8, 0.8),  # 10% on 8 cores
    mem_available_bytes: int = 16 * 1024 ** 3,
    battery_percent: float | None = None,
    power_plugged: bool = True,
    ci: bool = False,
    env_override: str | None = None,
    local_max: str | None = None,
) -> dict:
    """
    Run detect() with fully stubbed system calls.  Returns the diagnostics dict.
    """
    psutil_stub = _make_psutil_stub(
        mem_available_bytes=mem_available_bytes,
        battery_percent=battery_percent,
        power_plugged=power_plugged,
    )

    env = dict(os.environ)  # copy
    env.pop("COS_PYTEST_WORKERS", None)
    env.pop("COS_PYTEST_HEADROOM", None)
    env.pop("COS_PYTEST_LOCAL_MAX", None)
    env.pop("CI", None)

    if ci:
        env["CI"] = "true"
    if env_override is not None:
        env["COS_PYTEST_WORKERS"] = env_override
    if local_max is not None:
        env["COS_PYTEST_LOCAL_MAX"] = local_max

    with (
        patch.dict(sys.modules, {"psutil": psutil_stub}),
        patch.object(_mod, "os") as mock_os,
    ):
        # Forward real os calls that we don't want to stub out
        mock_os.environ = env
        mock_os.cpu_count = MagicMock(return_value=cores)
        mock_os.getloadavg = MagicMock(return_value=load_avg)

        # sys.platform remains real; we're on non-Windows, so getloadavg path runs
        result = _mod.detect()

    return result


# ---------------------------------------------------------------------------
# Heuristic table tests
# ---------------------------------------------------------------------------

class TestHeuristicTable(unittest.TestCase):
    """Six cases that cover every row in the ADR-068 heuristic table."""

    def test_row1_two_core_machine_outputs_serial(self):
        """Row 1: cores <= 2 -> workers = '0' (serial)."""
        result = _run_detect(cores=2)
        self.assertEqual(result["workers"], "0")
        self.assertEqual(result["rule_fired"], "cores_le_2")

    def test_row2_high_load_outputs_2(self):
        """Row 2 (ADR-068): load_pct > 70% -> workers = '2' (sharply restrict contention).

        Audit gap from 2026-04-30 plans audit: this branch existed in the script
        but had no unit test.  load_pct = (load1 / cores) * 100; 6.0/8*100 = 75%.
        """
        result = _run_detect(
            cores=8,
            load_avg=(6.0, 5.5, 5.0),  # load_pct = (6.0/8)*100 = 75% > 70%
            mem_available_bytes=16 * 1024 ** 3,
            battery_percent=80.0,
            power_plugged=True,
            ci=False,
        )
        self.assertEqual(result["workers"], "1")
        self.assertEqual(result["rule_fired"], "load_high")

    def test_row2_boundary_exactly_70_does_not_fire(self):
        """Row 2: load_pct == 70.0% must NOT trigger load_high (strictly > 70 required)."""
        # load1 = 0.70 * 8 = 5.6 exactly -> load_pct = 70.0 (not > 70)
        result = _run_detect(
            cores=8,
            load_avg=(5.6, 5.0, 4.5),  # load_pct = (5.6/8)*100 = 70.0
            mem_available_bytes=16 * 1024 ** 3,
            battery_percent=80.0,
            power_plugged=True,
            ci=False,
        )
        # Should fall through to Row 6 (default), NOT load_high
        self.assertNotEqual(result["rule_fired"], "load_high")

    def test_row3_low_memory_outputs_serial(self):
        """Row 3: mem_available < 2 GB on an otherwise healthy 8-core box -> serial."""
        result = _run_detect(
            cores=8,
            load_avg=(0.4, 0.4, 0.4),  # ~5% on 8 cores
            mem_available_bytes=int(1.5 * 1024 ** 3),  # 1.5 GB
        )
        self.assertEqual(result["workers"], "0")
        self.assertEqual(result["rule_fired"], "mem_low")

    def test_row4_battery_low_not_plugged_in(self):
        """Row 4: battery < 30%, not plugged in, healthy otherwise -> workers = '0'."""
        result = _run_detect(
            cores=8,
            load_avg=(0.4, 0.4, 0.4),
            mem_available_bytes=16 * 1024 ** 3,
            battery_percent=20.0,
            power_plugged=False,
        )
        self.assertEqual(result["workers"], "0")
        self.assertEqual(result["rule_fired"], "battery_low")

    def test_row5_ci_env_minimal_box(self):
        """Row 5: CI=true on a 4-core, 4 GB, 10%-load box -> workers = 'auto'."""
        result = _run_detect(
            cores=4,
            load_avg=(0.4, 0.4, 0.4),  # 10% on 4 cores
            mem_available_bytes=4 * 1024 ** 3,
            ci=True,
        )
        self.assertEqual(result["workers"], "auto")
        self.assertEqual(result["rule_fired"], "ci_env")

    def test_row6_default_healthy_machine(self):
        """Row 6: healthy 8-core box -> local cap keeps the laptop responsive."""
        result = _run_detect(
            cores=8,
            load_avg=(0.8, 0.8, 0.8),  # 10% on 8 cores
            mem_available_bytes=16 * 1024 ** 3,
            battery_percent=80.0,
            power_plugged=True,
            ci=False,
        )
        self.assertEqual(result["workers"], "2")
        self.assertEqual(result["rule_fired"], "default_local_cap")


# ---------------------------------------------------------------------------
# Override tests
# ---------------------------------------------------------------------------

    def test_row6_local_max_override(self):
        """COS_PYTEST_LOCAL_MAX allows deliberate use of a larger local cap."""
        result = _run_detect(cores=8, load_avg=(0.8, 0.8, 0.8), mem_available_bytes=16 * 1024 ** 3, local_max="3")
        self.assertEqual(result["workers"], "3")
        self.assertEqual(result["rule_fired"], "default_local_cap")


class TestEnvOverride(unittest.TestCase):
    """COS_PYTEST_WORKERS env var takes precedence over heuristic."""

    def test_override_auto(self):
        """COS_PYTEST_WORKERS=auto -> workers = 'auto', heuristic skipped."""
        result = _run_detect(cores=2, env_override="auto")  # would fire row 1
        self.assertEqual(result["workers"], "auto")
        self.assertEqual(result["rule_fired"], "env_override")

    def test_override_integer_8(self):
        """COS_PYTEST_WORKERS=8 -> workers = '8'."""
        result = _run_detect(env_override="8")
        self.assertEqual(result["workers"], "8")
        self.assertEqual(result["rule_fired"], "env_override")

    def test_override_zero(self):
        """COS_PYTEST_WORKERS=0 -> workers = '0' (serial via override, not heuristic)."""
        result = _run_detect(
            cores=8,
            load_avg=(0.8, 0.8, 0.8),
            mem_available_bytes=16 * 1024 ** 3,
            env_override="0",
        )
        self.assertEqual(result["workers"], "0")
        self.assertEqual(result["rule_fired"], "env_override")


# ---------------------------------------------------------------------------
# JSON output structure test
# ---------------------------------------------------------------------------

class TestJsonOutputKeys(unittest.TestCase):
    """All required keys must be present in the detect() result."""

    REQUIRED_KEYS = {
        "cores",
        "mem_available_gb",
        "load_pct",
        "battery_pct",
        "on_ac",
        "ci",
        "workers",
        "rule_fired",
    }

    def test_all_required_keys_present(self):
        result = _run_detect()
        missing = self.REQUIRED_KEYS - set(result.keys())
        self.assertFalse(missing, f"Missing keys in detect() output: {missing}")


if __name__ == "__main__":
    unittest.main()
