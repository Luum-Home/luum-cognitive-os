#!/usr/bin/env python3
"""
detect_runner_capacity.py — Adaptive pytest worker count detector.

Outputs a single token to stdout: "auto", "0", or a positive integer string.
Pass --json for a full diagnostics dict.

Override semantics (highest precedence first):
  1. COS_PYTEST_WORKERS env var: "auto", "0", integer N, "detect"/unset → heuristic
  2. Heuristic table (top-to-bottom, first match wins)

Exit codes:
  0  success (including soft fallbacks like missing psutil)
  1  hard failure (Python broken, unexpected exception)

Note: explicit -n flag in the pytest command line is handled by the bash wrapper
before this script is called; it short-circuits before invoking us.
"""

import json
import os
import sys


def _get_metrics() -> dict:
    """
    Collect system metrics. Returns a dict with:
      cores, mem_available_gb, load_pct, battery_pct, on_ac, ci
    Falls back gracefully when psutil is unavailable.
    """
    cores = os.cpu_count() or 1
    ci = os.environ.get("CI", "").lower() in ("true", "1", "yes")

    # --- psutil-dependent metrics ---
    try:
        import psutil  # type: ignore

        mem = psutil.virtual_memory()
        mem_available_gb = mem.available / (1024 ** 3)

        # Load average: POSIX has os.getloadavg(); Windows needs psutil
        if sys.platform == "win32":
            # cpu_percent with interval=1 blocks for 1 s but is the best we have
            load_pct = psutil.cpu_percent(interval=1)
        else:
            try:
                load1, _, _ = os.getloadavg()
                # Normalise to percentage relative to core count
                load_pct = (load1 / max(cores, 1)) * 100.0
            except (AttributeError, OSError):
                load_pct = psutil.cpu_percent(interval=1)

        battery = psutil.sensors_battery()
        if battery is not None:
            battery_pct = battery.percent
            on_ac = battery.power_plugged
        else:
            battery_pct = None
            on_ac = True  # assume desktop / always-on

    except ImportError:
        # Soft warning — psutil not installed.  Fall through to safe defaults.
        print(
            "WARNING: psutil not installed — assuming 8 GB RAM, 0% load, no battery. "
            "Install psutil for accurate capacity detection.",
            file=sys.stderr,
        )
        mem_available_gb = 8.0
        load_pct = 0.0
        battery_pct = None
        on_ac = True

    return {
        "cores": cores,
        "mem_available_gb": round(mem_available_gb, 2),
        "load_pct": round(load_pct, 1),
        "battery_pct": battery_pct,
        "on_ac": on_ac,
        "ci": ci,
    }


def _apply_heuristic(metrics: dict) -> tuple[str, str]:
    """
    Apply the heuristic table from ADR-068.
    Returns (workers_token, rule_fired) where workers_token is "auto", "0",
    or a positive integer string.
    """
    cores = metrics["cores"]
    mem_gb = metrics["mem_available_gb"]
    load_pct = metrics["load_pct"]
    battery_pct = metrics["battery_pct"]
    on_ac = metrics["on_ac"]
    ci = metrics["ci"]

    # Row 1: tiny machine
    if cores <= 2:
        return "0", "cores_le_2"

    # Row 2: high load
    if load_pct > 70:
        return "2", "load_high"

    # Row 3: low memory
    if mem_gb < 2.0:
        return "4", "mem_low"

    # Row 4: battery present, low, not plugged in
    if battery_pct is not None and battery_pct < 30 and not on_ac:
        return "0", "battery_low"

    # Row 5: CI environment
    if ci:
        return "auto", "ci_env"

    # Row 6: default — healthy dev machine
    return "auto", "default"


def detect() -> dict:
    """
    Run capacity detection and return a full diagnostics dict.
    Keys: cores, mem_available_gb, load_pct, battery_pct, on_ac, ci,
          workers, rule_fired.
    """
    # --- Override: COS_PYTEST_WORKERS env var ---
    override = os.environ.get("COS_PYTEST_WORKERS", "").strip()
    if override and override.lower() not in ("detect", ""):
        # Validate: must be "auto", "0", or a positive integer
        if override.lower() == "auto":
            workers = "auto"
            rule = "env_override"
        else:
            try:
                n = int(override)
                workers = str(n)
                rule = "env_override"
            except ValueError:
                # Unknown value — fall through to heuristic
                workers = None
                rule = None
    else:
        workers = None
        rule = None

    metrics = _get_metrics()

    if workers is None:
        workers, rule = _apply_heuristic(metrics)

    return {
        "cores": metrics["cores"],
        "mem_available_gb": metrics["mem_available_gb"],
        "load_pct": metrics["load_pct"],
        "battery_pct": metrics["battery_pct"],
        "on_ac": metrics["on_ac"],
        "ci": metrics["ci"],
        "workers": workers,
        "rule_fired": rule,
    }


def main() -> None:
    json_mode = "--json" in sys.argv[1:]
    try:
        result = detect()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: capacity detection failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if json_mode:
        print(json.dumps(result))
    else:
        print(result["workers"])


if __name__ == "__main__":
    main()
