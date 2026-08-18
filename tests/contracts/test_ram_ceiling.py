"""ADR-028 Phase B D2 contract: RAM ceiling.

Asserts that running `scripts/so-vitals.sh` reports a disk+agent+process
footprint within configured ceilings, AND that a fresh Python subprocess
RSS stays under a loose idle ceiling. Measuring the pytest runner itself is
intentionally avoided because loaded plugins, xdist, and prior tests make its
high-water RSS environment-dependent.

Thresholds are conservative and configurable via env:
  COS_RAM_CEILING_MIB          default 500  (OS self RSS)
  COS_VITALS_DISK_CEILING_MIB  overrides the .cognitive-os disk ceiling

The disk ceiling itself is NOT defined here. It lives in
manifests/state-retention.yaml under `global_budget.max_total_mib`, because
scripts/state_retention_audit.py enforces the same number against the same
tree; two hardcoded copies would drift. This test reads the manifest value and
keeps COS_VITALS_DISK_CEILING_MIB as the override that moves both consumers.

Platform: macOS + Linux. `resource.getrusage` behaves differently on
each (Linux=KiB, Mac=bytes); we normalise below.
"""
from __future__ import annotations

import json
import os
import resource
import subprocess
import sys
from pathlib import Path

import yaml


_ROOT = Path(__file__).resolve().parent.parent.parent
_RAM_CEILING_MIB = int(os.environ.get("COS_RAM_CEILING_MIB", "500"))


def _manifest_disk_ceiling_mib() -> float:
    """Single source of the .cognitive-os ceiling: the state-retention manifest."""
    manifest = _ROOT / "manifests" / "state-retention.yaml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    ceiling = (data.get("global_budget") or {}).get("max_total_mib")
    assert ceiling is not None, (
        f"{manifest} must declare global_budget.max_total_mib — it is the single "
        "source shared with scripts/state_retention_audit.py"
    )
    return float(ceiling)


_DISK_CEILING_MIB = float(
    os.environ.get("COS_VITALS_DISK_CEILING_MIB") or _manifest_disk_ceiling_mib()
)


def _self_rss_mib() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    raw = usage.ru_maxrss
    # macOS reports bytes; Linux reports kilobytes.
    if sys.platform == "darwin":
        return raw / (1024 * 1024)
    return raw / 1024  # KiB -> MiB


def _run_so_vitals_json() -> dict:
    script = _ROOT / "scripts" / "so-vitals.sh"
    assert script.is_file(), "so-vitals.sh missing"
    r = subprocess.run(
        ["bash", str(script), "--json"],
        capture_output=True, text=True, timeout=30,
        cwd=str(_ROOT),
    )
    assert r.returncode == 0, f"so-vitals failed: {r.stderr[:300]}"
    # so-vitals prints one MetricEvent line in json mode
    out = r.stdout.strip().splitlines()
    assert out, "so-vitals --json produced no output"
    # Take the last non-empty line (some stderr may leak to stdout)
    last = [ln for ln in out if ln.strip().startswith("{")][-1]
    return json.loads(last)


# ---------------------------------------------------------------------------


def test_fresh_python_process_rss_under_ceiling():
    probe = (
        "import json, resource, sys; "
        "raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss; "
        "rss = raw / (1024 * 1024) if sys.platform == 'darwin' else raw / 1024; "
        "print(json.dumps({'rss_mib': rss}))"
    )
    r = subprocess.run(
        [sys.executable, "-I", "-S", "-c", probe],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert r.returncode == 0, r.stderr[:300]
    rss = float(json.loads(r.stdout)["rss_mib"])
    assert rss < _RAM_CEILING_MIB, (
        f"Fresh Python process RSS {rss:.1f} MiB exceeds ceiling {_RAM_CEILING_MIB} MiB"
    )
    # Also: must be a sane positive number, not a getrusage anomaly.
    assert rss > 1.0, f"RSS implausibly small: {rss} MiB"


def test_so_vitals_reports_disk_under_ceiling():
    event = _run_so_vitals_json()
    payload = event.get("payload") or {}
    disk_mib = float(payload.get("disk_mib", 0.0))
    # 0.0 is suspicious; treat as missing data and fail.
    assert disk_mib > 0, "so-vitals reported 0 MiB for .cognitive-os — likely a measurement bug"
    assert disk_mib < _DISK_CEILING_MIB, (
        f".cognitive-os/ disk usage {disk_mib:.1f} MiB exceeds ceiling {_DISK_CEILING_MIB} MiB"
    )


def test_so_vitals_emits_valid_metric_event_shape():
    event = _run_so_vitals_json()
    assert event.get("source") == "so-vitals"
    assert event.get("event_type") == "so.vitals"
    assert "schema_version" in event
    assert "timestamp" in event
    assert "payload" in event and isinstance(event["payload"], dict)


def test_so_vitals_has_agents_count_field():
    """The agent_bus_metrics integration (ADR-028b) must populate the count
    even when zero."""
    event = _run_so_vitals_json()
    payload = event.get("payload") or {}
    assert "agents_in_flight" in payload
    assert "agents_stale" in payload
    assert isinstance(payload["agents_in_flight"], int)
    assert isinstance(payload["agents_stale"], int)
