"""Integration tests for lib/host_monitor.py — uses real system calls.

These tests verify actual behaviour on the running machine (macOS or Linux).
They do not mock anything; they require a real OS environment.
"""

from __future__ import annotations

import platform

import pytest

from lib.host_monitor import HostMonitor


@pytest.fixture(scope="module")
def monitor() -> HostMonitor:
    return HostMonitor()


class TestLiveSnapshot:
    def test_live_snapshot(self, monitor: HostMonitor):
        snap = monitor.get_snapshot()
        assert isinstance(snap, dict)
        assert "memory" in snap
        assert "cpu" in snap
        assert "disk" in snap
        assert "timestamp" in snap
        assert "os" in snap
        assert snap["os"] in ("Darwin", "Linux", "Windows")

    def test_live_snapshot_memory_has_values(self, monitor: HostMonitor):
        snap = monitor.get_snapshot()
        mem = snap["memory"]
        assert mem["total_gb"] > 0
        assert mem["usage_pct"] >= 0
        assert mem["usage_pct"] <= 100

    def test_live_snapshot_cpu_has_values(self, monitor: HostMonitor):
        snap = monitor.get_snapshot()
        cpu = snap["cpu"]
        assert cpu["cores"] >= 1
        assert cpu["usage_pct"] >= 0
        assert cpu["load_1m"] >= 0

    def test_live_snapshot_disk_has_values(self, monitor: HostMonitor):
        snap = monitor.get_snapshot()
        disk = snap["disk"]
        assert disk["total_gb"] > 0
        assert 0 <= disk["usage_pct"] <= 100


class TestLivePressure:
    def test_live_pressure(self, monitor: HostMonitor):
        pressure = monitor.get_pressure_level()
        assert pressure in ("low", "moderate", "high", "critical")

    def test_live_pressure_consistent_with_memory(self, monitor: HostMonitor):
        """If RAM > 90%, pressure must be critical."""
        mem = monitor.get_memory()
        pressure = monitor.get_pressure_level()
        if mem["usage_pct"] > 90:
            assert pressure == "critical"

    def test_live_pressure_consistent_with_cpu(self, monitor: HostMonitor):
        """If CPU > 90%, pressure must be critical."""
        cpu = monitor.get_cpu()
        pressure = monitor.get_pressure_level()
        if cpu["usage_pct"] > 90:
            assert pressure == "critical"


class TestLiveFormatStatus:
    def test_live_format_status(self, monitor: HostMonitor):
        status = monitor.format_status()
        assert isinstance(status, str)
        assert len(status) > 20

    def test_live_format_status_readable(self, monitor: HostMonitor):
        status = monitor.format_status()
        assert "RAM" in status
        assert "CPU" in status
        assert "%" in status

    def test_live_format_status_has_pressure(self, monitor: HostMonitor):
        status = monitor.format_status()
        assert any(p in status for p in ("LOW", "MODERATE", "HIGH", "CRITICAL"))


class TestLiveRecommend:
    def test_live_recommend(self, monitor: HostMonitor):
        max_agents = monitor.recommend_max_agents()
        assert isinstance(max_agents, int)
        assert 0 <= max_agents <= 5

    def test_live_recommend_consistent_with_pressure(self, monitor: HostMonitor):
        pressure = monitor.get_pressure_level()
        max_agents = monitor.recommend_max_agents()
        if pressure == "critical":
            assert max_agents == 0
        elif pressure == "high":
            assert max_agents <= 1
        elif pressure == "moderate":
            assert max_agents <= 3
        else:
            assert max_agents <= 5

    def test_live_should_launch(self, monitor: HostMonitor):
        result = monitor.should_launch_agent()
        assert "allowed" in result
        assert "reason" in result
        assert "pressure" in result
        assert "max_agents" in result
        assert isinstance(result["allowed"], bool)

    def test_live_format_warning_returns_string_or_none(self, monitor: HostMonitor):
        warning = monitor.format_warning()
        assert warning is None or isinstance(warning, str)

    def test_live_os_detected(self, monitor: HostMonitor):
        """Verify the OS was detected correctly."""
        expected = platform.system()
        assert monitor._os == expected
