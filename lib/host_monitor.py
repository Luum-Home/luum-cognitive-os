# SCOPE: both
"""Host Resource Monitor — adaptive agent throttling based on system pressure.

Cross-platform (macOS Darwin + Linux). No external dependencies.

Usage:
    from lib.host_monitor import HostMonitor

    h = HostMonitor()
    print(h.format_status())
    s = h.should_launch_agent()
    if not s["allowed"]:
        print(s["reason"])

Python 3.9+ compatible. stdlib only: platform, subprocess, shutil, os, json.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone


class HostMonitor:
    """Cross-platform host resource monitor for agent throttling."""

    def __init__(self) -> None:
        self._os = platform.system()  # "Darwin" or "Linux"

    # ------------------------------------------------------------------
    # Core metrics
    # ------------------------------------------------------------------

    def get_memory(self) -> dict:
        """Return memory stats.

        Returns: {total_gb, used_gb, available_gb, usage_pct}
        macOS: vm_stat + sysctl hw.memsize
        Linux: /proc/meminfo
        """
        if self._os == "Darwin":
            return self._get_memory_macos()
        return self._get_memory_linux()

    def _get_memory_macos(self) -> dict:
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5
            )
            total_bytes = int(result.stdout.strip())
            total_gb = total_bytes / (1024 ** 3)
        except Exception:
            total_gb = 0.0

        available_gb = 0.0
        try:
            result = subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=5
            )
            page_size = 4096
            free_pages = 0
            inactive_pages = 0
            for line in result.stdout.splitlines():
                if "page size of" in line:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p == "bytes":
                            try:
                                page_size = int(parts[i - 1])
                            except (ValueError, IndexError):
                                pass
                if "Pages free:" in line:
                    free_pages = int(line.split(":")[1].strip().rstrip("."))
                elif "Pages inactive:" in line:
                    inactive_pages = int(line.split(":")[1].strip().rstrip("."))
            available_gb = (free_pages + inactive_pages) * page_size / (1024 ** 3)
        except Exception:
            pass

        used_gb = max(0.0, total_gb - available_gb)
        usage_pct = (used_gb / total_gb * 100) if total_gb > 0 else 0.0
        return {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "available_gb": round(available_gb, 2),
            "usage_pct": round(usage_pct, 1),
        }

    def _get_memory_linux(self) -> dict:
        total_kb = available_kb = 0
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        total_kb = int(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        available_kb = int(line.split()[1])
        except Exception:
            pass
        total_gb = total_kb / (1024 ** 2)
        available_gb = available_kb / (1024 ** 2)
        used_gb = max(0.0, total_gb - available_gb)
        usage_pct = (used_gb / total_gb * 100) if total_gb > 0 else 0.0
        return {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "available_gb": round(available_gb, 2),
            "usage_pct": round(usage_pct, 1),
        }

    def get_cpu(self) -> dict:
        """Return CPU load stats.

        Returns: {load_1m, load_5m, load_15m, cores, usage_pct}
        usage_pct = (load_1m / cores) * 100
        """
        load_1m, load_5m, load_15m = os.getloadavg()
        cores = os.cpu_count() or 1
        usage_pct = min((load_1m / cores) * 100, 100.0)
        return {
            "load_1m": round(load_1m, 2),
            "load_5m": round(load_5m, 2),
            "load_15m": round(load_15m, 2),
            "cores": cores,
            "usage_pct": round(usage_pct, 1),
        }

    def get_disk(self) -> dict:
        """Return disk usage for root filesystem.

        Returns: {total_gb, used_gb, free_gb, usage_pct}
        """
        usage = shutil.disk_usage("/")
        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        usage_pct = (used_gb / total_gb * 100) if total_gb > 0 else 0.0
        return {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "usage_pct": round(usage_pct, 1),
        }

    def get_docker_stats(self) -> dict | None:
        """Return Docker resource usage or None if Docker is unavailable."""
        try:
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format",
                 "{{.MemUsage}}\t{{.CPUPerc}}"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                return None
            lines = [l for l in result.stdout.strip().splitlines() if l]
            if not lines:
                return {"running_containers": 0, "total_memory_mb": 0.0, "total_cpu_pct": 0.0}
            total_mem_mb = 0.0
            total_cpu = 0.0
            for line in lines:
                parts = line.split("\t")
                if len(parts) >= 2:
                    mem_str = parts[0].split("/")[0].strip()
                    cpu_str = parts[1].strip().rstrip("%")
                    try:
                        total_cpu += float(cpu_str)
                    except ValueError:
                        pass
                    try:
                        if "GiB" in mem_str or "GB" in mem_str:
                            total_mem_mb += float(mem_str.replace("GiB", "").replace("GB", "").strip()) * 1024
                        elif "MiB" in mem_str or "MB" in mem_str:
                            total_mem_mb += float(mem_str.replace("MiB", "").replace("MB", "").strip())
                    except ValueError:
                        pass
            return {
                "running_containers": len(lines),
                "total_memory_mb": round(total_mem_mb, 1),
                "total_cpu_pct": round(total_cpu, 1),
            }
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return None

    def get_snapshot(self) -> dict:
        """Full resource snapshot."""
        return {
            "memory": self.get_memory(),
            "cpu": self.get_cpu(),
            "disk": self.get_disk(),
            "docker": self.get_docker_stats(),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "os": self._os,
        }

    # ------------------------------------------------------------------
    # Pressure & throttling
    # ------------------------------------------------------------------

    def get_pressure_level(self) -> str:
        """Classify current resource pressure.

        LOW:      RAM <70%, CPU <70%, Disk <80%
        MODERATE: RAM 70-85% OR CPU 70-85%
        HIGH:     RAM 85-95% OR CPU 85-95%
        CRITICAL: RAM >95% OR CPU >95% OR Disk >95%
        """
        mem = self.get_memory()
        cpu = self.get_cpu()
        disk = self.get_disk()
        ram_pct = mem["usage_pct"]
        cpu_pct = cpu["usage_pct"]
        disk_pct = disk["usage_pct"]

        if ram_pct > 95 or cpu_pct > 95 or disk_pct > 95:
            return "critical"
        if ram_pct > 85 or cpu_pct > 85:
            return "high"
        if ram_pct > 70 or cpu_pct > 70:
            return "moderate"
        return "low"

    def recommend_max_agents(self) -> int:
        """Recommend max parallel agents based on current resources."""
        pressure = self.get_pressure_level()
        mem = self.get_memory()
        available_gb = mem["available_gb"]

        base = {"critical": 0, "high": 1, "moderate": 3, "low": 5}[pressure]

        # RAM floor overrides
        if available_gb < 2.0:
            base = min(base, 1)
        elif available_gb < 4.0:
            base = min(base, 2)

        return base

    def should_launch_agent(self) -> dict:
        """Pre-launch check. Returns allowed, reason, pressure, max_agents, snapshot."""
        snapshot = self.get_snapshot()
        pressure = self.get_pressure_level()
        max_agents = self.recommend_max_agents()
        allowed = max_agents > 0
        reason_map = {
            "critical": "Host is under CRITICAL pressure — no new agents allowed",
            "high": "Host is under HIGH pressure — limit to 1 agent",
            "moderate": "Host is under MODERATE pressure — limit to 3 agents",
            "low": "Host resources are healthy",
        }
        return {
            "allowed": allowed,
            "reason": reason_map[pressure],
            "pressure": pressure,
            "max_agents": max_agents,
            "snapshot": snapshot,
        }

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_status(self) -> str:
        """One-line status string."""
        mem = self.get_memory()
        cpu = self.get_cpu()
        disk = self.get_disk()
        docker = self.get_docker_stats()
        pressure = self.get_pressure_level()
        max_agents = self.recommend_max_agents()

        docker_part = f"Docker {docker['running_containers']} containers | " if docker else ""
        return (
            f"Host: RAM {mem['usage_pct']}% ({mem['used_gb']:.1f}/{mem['total_gb']:.1f}GB) | "
            f"CPU {cpu['usage_pct']}% | "
            f"Disk {disk['usage_pct']}% | "
            f"{docker_part}"
            f"Pressure: {pressure.upper()} → max {max_agents} agents"
        )

    def format_warning(self) -> str | None:
        """Return warning string if HIGH/CRITICAL, None otherwise."""
        pressure = self.get_pressure_level()
        if pressure not in ("high", "critical"):
            return None
        mem = self.get_memory()
        max_agents = self.recommend_max_agents()
        return (
            f"WARNING: Host under {pressure.upper()} pressure "
            f"(RAM {mem['usage_pct']}%). "
            f"Limit to {max_agents} parallel agent{'s' if max_agents != 1 else ''}."
        )
