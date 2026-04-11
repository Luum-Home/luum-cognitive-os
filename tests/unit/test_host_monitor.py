"""Unit tests for lib/host_monitor.py — all subprocess/platform calls mocked."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from lib.host_monitor import HostMonitor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _monitor(os_name: str = "Darwin") -> HostMonitor:
    m = HostMonitor.__new__(HostMonitor)
    m._os = os_name
    return m


def _make_mem(usage_pct: float, total_gb: float = 16.0, available_gb: float | None = None) -> dict:
    if available_gb is None:
        available_gb = total_gb * (1 - usage_pct / 100)
    used_gb = total_gb - available_gb
    return {
        "total_gb": total_gb,
        "used_gb": round(used_gb, 2),
        "available_gb": round(available_gb, 2),
        "usage_pct": round(usage_pct, 1),
    }


def _make_cpu(usage_pct: float) -> dict:
    return {"load_1m": usage_pct / 100, "load_5m": 0.5, "load_15m": 0.3, "cores": 8, "usage_pct": usage_pct}


def _make_disk(usage_pct: float) -> dict:
    total = 500.0
    used = total * usage_pct / 100
    return {"total_gb": total, "used_gb": round(used, 2), "free_gb": round(total - used, 2), "usage_pct": round(usage_pct, 1)}


# ---------------------------------------------------------------------------
# get_memory
# ---------------------------------------------------------------------------

class TestGetMemory:
    def test_get_memory_returns_dict(self):
        m = _monitor("Darwin")
        with patch.object(m, "_get_memory_macos", return_value=_make_mem(55.0)):
            result = m.get_memory()
        assert "total_gb" in result
        assert "available_gb" in result
        assert "usage_pct" in result
        assert result["usage_pct"] == 55.0

    def test_get_memory_linux_returns_dict(self):
        m = _monitor("Linux")
        with patch.object(m, "_get_memory_linux", return_value=_make_mem(40.0)):
            result = m.get_memory()
        assert "total_gb" in result
        assert "available_gb" in result
        assert "usage_pct" in result

    def test_macos_memory_dispatches_correctly(self):
        m = _monitor("Darwin")
        with patch.object(m, "_get_memory_macos", return_value=_make_mem(50.0)) as mock_mac, \
             patch.object(m, "_get_memory_linux", return_value=_make_mem(50.0)) as mock_linux:
            m.get_memory()
        mock_mac.assert_called_once()
        mock_linux.assert_not_called()

    def test_linux_memory_dispatches_correctly(self):
        m = _monitor("Linux")
        with patch.object(m, "_get_memory_macos", return_value=_make_mem(50.0)) as mock_mac, \
             patch.object(m, "_get_memory_linux", return_value=_make_mem(50.0)) as mock_linux:
            m.get_memory()
        mock_mac.assert_not_called()
        mock_linux.assert_called_once()


# ---------------------------------------------------------------------------
# get_cpu
# ---------------------------------------------------------------------------

class TestGetCpu:
    def test_get_cpu_returns_dict(self):
        m = _monitor()
        with patch("os.getloadavg", return_value=(3.2, 2.5, 2.0)), \
             patch("os.cpu_count", return_value=8):
            result = m.get_cpu()
        assert "load_1m" in result
        assert "cores" in result
        assert "usage_pct" in result
        assert result["load_1m"] == 3.2
        assert result["cores"] == 8

    def test_cpu_usage_pct_calculation(self):
        m = _monitor()
        with patch("os.getloadavg", return_value=(4.0, 3.0, 2.0)), \
             patch("os.cpu_count", return_value=8):
            result = m.get_cpu()
        assert result["usage_pct"] == 50.0

    def test_cpu_usage_capped_at_100(self):
        m = _monitor()
        with patch("os.getloadavg", return_value=(16.0, 14.0, 12.0)), \
             patch("os.cpu_count", return_value=8):
            result = m.get_cpu()
        assert result["usage_pct"] == 100.0


# ---------------------------------------------------------------------------
# get_disk
# ---------------------------------------------------------------------------

class TestGetDisk:
    def test_get_disk_returns_dict(self):
        m = _monitor()
        fake_usage = MagicMock()
        fake_usage.total = 500 * (1024 ** 3)
        fake_usage.used = 300 * (1024 ** 3)
        fake_usage.free = 200 * (1024 ** 3)
        with patch("shutil.disk_usage", return_value=fake_usage):
            result = m.get_disk()
        assert "free_gb" in result
        assert "usage_pct" in result
        assert result["usage_pct"] == pytest.approx(60.0, abs=0.1)


# ---------------------------------------------------------------------------
# get_pressure_level
# ---------------------------------------------------------------------------

class TestPressureLevel:
    def _patch(self, m: HostMonitor, ram: float, cpu: float, disk: float = 50.0):
        m.get_memory = lambda: _make_mem(ram)
        m.get_cpu = lambda: _make_cpu(cpu)
        m.get_disk = lambda: _make_disk(disk)

    def test_pressure_low(self):
        m = _monitor()
        self._patch(m, ram=50.0, cpu=50.0, disk=70.0)
        assert m.get_pressure_level() == "low"

    def test_pressure_moderate_ram(self):
        m = _monitor()
        self._patch(m, ram=75.0, cpu=30.0)
        assert m.get_pressure_level() == "moderate"

    def test_pressure_moderate_cpu(self):
        m = _monitor()
        self._patch(m, ram=30.0, cpu=75.0)
        assert m.get_pressure_level() == "moderate"

    def test_pressure_high_ram(self):
        m = _monitor()
        self._patch(m, ram=90.0, cpu=30.0)
        assert m.get_pressure_level() == "high"

    def test_pressure_high_cpu(self):
        m = _monitor()
        self._patch(m, ram=30.0, cpu=90.0)
        assert m.get_pressure_level() == "high"

    def test_pressure_critical_ram(self):
        m = _monitor()
        self._patch(m, ram=96.0, cpu=30.0)
        assert m.get_pressure_level() == "critical"

    def test_pressure_critical_cpu(self):
        m = _monitor()
        self._patch(m, ram=30.0, cpu=96.0)
        assert m.get_pressure_level() == "critical"

    def test_pressure_critical_disk(self):
        m = _monitor()
        self._patch(m, ram=50.0, cpu=50.0, disk=96.0)
        assert m.get_pressure_level() == "critical"

    def test_pressure_boundary_exactly_70(self):
        """70% is NOT moderate — must be >70 to trigger."""
        m = _monitor()
        self._patch(m, ram=70.0, cpu=70.0)
        assert m.get_pressure_level() == "low"

    def test_pressure_boundary_just_over_70(self):
        m = _monitor()
        self._patch(m, ram=70.1, cpu=59.0)
        assert m.get_pressure_level() == "moderate"

    def test_80_percent_is_moderate_not_high(self):
        """80% RAM should be MODERATE, not HIGH (old threshold was too aggressive)."""
        m = _monitor()
        self._patch(m, ram=80.0, cpu=30.0)
        assert m.get_pressure_level() == "moderate"


# ---------------------------------------------------------------------------
# recommend_max_agents
# ---------------------------------------------------------------------------

class TestRecommendMaxAgents:
    def test_recommend_agents_low(self):
        m = _monitor()
        m.get_pressure_level = lambda: "low"
        m.get_memory = lambda: _make_mem(50.0, available_gb=8.0)
        assert m.recommend_max_agents() == 5

    def test_recommend_agents_moderate(self):
        m = _monitor()
        m.get_pressure_level = lambda: "moderate"
        m.get_memory = lambda: _make_mem(70.0, available_gb=5.0)
        assert m.recommend_max_agents() == 3

    def test_recommend_agents_high(self):
        m = _monitor()
        m.get_pressure_level = lambda: "high"
        m.get_memory = lambda: _make_mem(85.0, available_gb=4.5)
        assert m.recommend_max_agents() == 1

    def test_recommend_agents_critical(self):
        m = _monitor()
        m.get_pressure_level = lambda: "critical"
        m.get_memory = lambda: _make_mem(95.0, available_gb=0.5)
        assert m.recommend_max_agents() == 0

    def test_recommend_agents_low_ram_under_2gb(self):
        """Available RAM < 2GB overrides pressure-based recommendation."""
        m = _monitor()
        m.get_pressure_level = lambda: "low"
        m.get_memory = lambda: _make_mem(50.0, total_gb=16.0, available_gb=1.5)
        assert m.recommend_max_agents() == 1

    def test_recommend_agents_low_ram_under_4gb(self):
        """Available RAM < 4GB but >= 2GB → max 2."""
        m = _monitor()
        m.get_pressure_level = lambda: "low"
        m.get_memory = lambda: _make_mem(50.0, total_gb=16.0, available_gb=3.0)
        assert m.recommend_max_agents() == 2

    def test_recommend_agents_critical_low_ram_stays_zero(self):
        """Critical pressure stays 0 even with RAM floor logic."""
        m = _monitor()
        m.get_pressure_level = lambda: "critical"
        m.get_memory = lambda: _make_mem(95.0, available_gb=3.0)
        assert m.recommend_max_agents() == 0


# ---------------------------------------------------------------------------
# should_launch_agent
# ---------------------------------------------------------------------------

class TestShouldLaunchAgent:
    def test_should_launch_critical_not_allowed(self):
        m = _monitor()
        m.get_snapshot = lambda: {}
        m.get_pressure_level = lambda: "critical"
        m.recommend_max_agents = lambda: 0
        result = m.should_launch_agent()
        assert result["allowed"] is False

    def test_should_launch_low_allowed(self):
        m = _monitor()
        m.get_snapshot = lambda: {}
        m.get_pressure_level = lambda: "low"
        m.recommend_max_agents = lambda: 5
        result = m.should_launch_agent()
        assert result["allowed"] is True

    def test_should_launch_returns_required_keys(self):
        m = _monitor()
        m.get_snapshot = lambda: {"memory": {}}
        m.get_pressure_level = lambda: "moderate"
        m.recommend_max_agents = lambda: 3
        result = m.should_launch_agent()
        assert "allowed" in result
        assert "reason" in result
        assert "pressure" in result
        assert "max_agents" in result
        assert "snapshot" in result

    def test_should_launch_reason_not_empty(self):
        m = _monitor()
        m.get_snapshot = lambda: {}
        m.get_pressure_level = lambda: "high"
        m.recommend_max_agents = lambda: 1
        result = m.should_launch_agent()
        assert len(result["reason"]) > 0


# ---------------------------------------------------------------------------
# format_status
# ---------------------------------------------------------------------------

class TestFormatStatus:
    def test_format_status_contains_pct(self):
        m = _monitor()
        m.get_memory = lambda: _make_mem(72.0, total_gb=16.0, available_gb=4.5)
        m.get_cpu = lambda: _make_cpu(45.0)
        m.get_disk = lambda: _make_disk(68.0)
        m.get_docker_stats = lambda: None
        m.get_pressure_level = lambda: "moderate"
        m.recommend_max_agents = lambda: 3
        status = m.format_status()
        assert "%" in status
        assert "RAM" in status
        assert "CPU" in status

    def test_format_status_includes_pressure(self):
        m = _monitor()
        m.get_memory = lambda: _make_mem(72.0, total_gb=16.0, available_gb=4.5)
        m.get_cpu = lambda: _make_cpu(45.0)
        m.get_disk = lambda: _make_disk(68.0)
        m.get_docker_stats = lambda: None
        m.get_pressure_level = lambda: "moderate"
        m.recommend_max_agents = lambda: 3
        status = m.format_status()
        assert "MODERATE" in status

    def test_format_status_with_docker(self):
        m = _monitor()
        m.get_memory = lambda: _make_mem(50.0, total_gb=16.0, available_gb=8.0)
        m.get_cpu = lambda: _make_cpu(30.0)
        m.get_disk = lambda: _make_disk(40.0)
        m.get_docker_stats = lambda: {"running_containers": 5, "total_memory_mb": 2048, "total_cpu_pct": 10.0}
        m.get_pressure_level = lambda: "low"
        m.recommend_max_agents = lambda: 5
        status = m.format_status()
        assert "Docker" in status
        assert "5" in status


# ---------------------------------------------------------------------------
# get_docker_stats
# ---------------------------------------------------------------------------

class TestDockerStats:
    def test_docker_unavailable_returns_none(self):
        m = _monitor()
        with patch("subprocess.run", side_effect=FileNotFoundError("docker not found")):
            result = m.get_docker_stats()
        assert result is None

    def test_docker_non_zero_exit_returns_none(self):
        m = _monitor()
        fake = MagicMock()
        fake.returncode = 1
        fake.stdout = ""
        with patch("subprocess.run", return_value=fake):
            result = m.get_docker_stats()
        assert result is None

    def test_docker_empty_output_returns_zero_containers(self):
        m = _monitor()
        fake = MagicMock()
        fake.returncode = 0
        fake.stdout = ""
        with patch("subprocess.run", return_value=fake):
            result = m.get_docker_stats()
        assert result is not None
        assert result["running_containers"] == 0

    def test_docker_timeout_returns_none(self):
        m = _monitor()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 5)):
            result = m.get_docker_stats()
        assert result is None


# ---------------------------------------------------------------------------
# Cross-platform detection
# ---------------------------------------------------------------------------

class TestCrossPlatformDetection:
    def test_cross_platform_detection_darwin(self):
        with patch("platform.system", return_value="Darwin"):
            m = HostMonitor()
        assert m._os == "Darwin"

    def test_cross_platform_detection_linux(self):
        with patch("platform.system", return_value="Linux"):
            m = HostMonitor()
        assert m._os == "Linux"

    def test_linux_proc_meminfo_parsing(self):
        m = _monitor("Linux")
        meminfo = "MemTotal:       16384000 kB\nMemAvailable:    8192000 kB\n"
        with patch("builtins.open", MagicMock(return_value=MagicMock(
            __enter__=lambda s, *a: iter(meminfo.splitlines(keepends=True)),
            __exit__=MagicMock(return_value=False),
        ))):
            result = m._get_memory_linux()
        assert result["total_gb"] == pytest.approx(16384000 / (1024 ** 2), rel=0.01)
        assert result["usage_pct"] == pytest.approx(50.0, abs=1.0)
