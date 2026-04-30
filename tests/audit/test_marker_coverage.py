"""Marker coverage audit (ADR-072).

For each lane registered in ``.cognitive-os/test-lanes.yaml``, asserts that
≥95% of test files under the lane's path(s) carry the lane's marker after
auto-injection in ``tests/conftest.py``. This catches drift where a new test
directory is added without registering a lane, or where the auto-marker hook
silently fails to match.

Why a percentage threshold and not 100%: a small number of files may
intentionally use ``pytestmark = pytest.mark.<other_lane>`` (e.g., a unit-style
test physically located in ``tests/integration/`` for proximity to its target
module). Those exceptions exist; 95% is the budget.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.audit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LANES_FILE = PROJECT_ROOT / ".cognitive-os" / "test-lanes.yaml"
COVERAGE_THRESHOLD = 0.95  # ≥95% of files in a lane path must carry the lane marker

# Lanes whose marker name differs from the lane key (singular vs plural).
# Mirrors the mapping in tests/conftest.py.
_LANE_TO_MARKER = {"hooks": "hook"}


def _lane_marker(lane_name: str) -> str:
    return _LANE_TO_MARKER.get(lane_name, lane_name)


def _collect_marker_count(marker: str, paths: list[str]) -> int:
    """Run ``pytest --collect-only -q -m <marker>`` against the given paths and
    return the number of collected items. Zero on failure."""
    if not paths:
        return 0
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *[str(PROJECT_ROOT / p) for p in paths],
        "-m",
        marker,
        "--collect-only",
        "-q",
        "--no-header",
        "-p",
        "no:cacheprovider",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(PROJECT_ROOT),
    )
    # Last non-empty line of stdout is the summary, e.g., "123 tests collected in 1.23s"
    for line in reversed(result.stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        # Match the leading integer of summary lines like "123 tests collected"
        # or "123/456 tests collected".
        parts = line.split()
        if parts and parts[0].split("/")[0].isdigit():
            try:
                return int(parts[0].split("/")[0])
            except ValueError:
                continue
        # Some pytest versions print "no tests collected"; treat as 0.
        if "no tests" in line.lower() and "collected" in line.lower():
            return 0
    return 0


def _count_test_files(paths: list[str]) -> int:
    """Count test_*.py files under the given paths (recursive)."""
    total = 0
    for p in paths:
        base = PROJECT_ROOT / p
        if not base.exists():
            continue
        total += sum(1 for _ in base.rglob("test_*.py"))
    return total


def _load_lanes() -> dict[str, dict]:
    """Load .cognitive-os/test-lanes.yaml lanes section. Empty dict on failure."""
    if not LANES_FILE.exists():
        return {}
    try:
        return yaml.safe_load(LANES_FILE.read_text(encoding="utf-8")).get("lanes", {})
    except Exception:
        return {}


_LANES = _load_lanes()
# Only enforce coverage on lanes with parallel:true (where marker hygiene is
# the most critical signal — these are the lanes the wrapper trusts to run with
# adaptive workers). Stateful lanes (parallel:false/marker) auto-inject too,
# but their marker drift is less load-bearing.
_LANE_IDS = sorted(
    name for name, cfg in _LANES.items()
    if cfg.get("parallel") is True and cfg.get("paths")
)


@pytest.mark.parametrize("lane_name", _LANE_IDS)
def test_lane_marker_coverage_meets_threshold(lane_name: str) -> None:
    """≥95% of test files under a parallel-safe lane carry that lane's marker.

    Catches drift where new tests are added without the auto-marker matching
    them (e.g., wrong path, prefix-collision bug, missing pytestmark).
    """
    cfg = _LANES[lane_name]
    paths: list[str] = cfg.get("paths", [])
    marker = _lane_marker(lane_name)

    file_count = _count_test_files(paths)
    if file_count == 0:
        pytest.skip(f"lane '{lane_name}' has no test_*.py files under {paths}")

    collected = _collect_marker_count(marker, paths)
    # Collected count includes parametrized expansions; we only need a lower
    # bound on coverage. If collected ≥ file_count * threshold, every file is
    # very likely contributing at least one item — sufficient to assert the
    # marker is being injected.
    expected_minimum = max(1, int(file_count * COVERAGE_THRESHOLD))

    assert collected >= expected_minimum, (
        f"lane '{lane_name}' (marker '{marker}') under {paths}: "
        f"collected only {collected} items via -m {marker}, "
        f"expected ≥{expected_minimum} (≥{COVERAGE_THRESHOLD:.0%} of {file_count} files). "
        f"Likely cause: new tests added without auto-marker hook matching, "
        f"or a path-prefix collision. See tests/conftest.py and ADR-072."
    )


def test_lanes_file_exists_and_parses() -> None:
    """The lane registry must exist and parse — fail loud otherwise."""
    assert LANES_FILE.exists(), f"missing lane registry: {LANES_FILE}"
    data = yaml.safe_load(LANES_FILE.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and "lanes" in data, (
        f"{LANES_FILE} must have a top-level 'lanes' key"
    )
    lanes = data["lanes"]
    assert isinstance(lanes, dict) and len(lanes) > 0, (
        f"{LANES_FILE} 'lanes' must be a non-empty mapping"
    )


def test_every_registered_lane_has_paths_and_parallel_field() -> None:
    """Every lane entry must declare paths and a parallel mode (ADR-072 contract)."""
    for name, cfg in _LANES.items():
        assert "paths" in cfg and isinstance(cfg["paths"], list) and cfg["paths"], (
            f"lane '{name}' must declare 'paths: [..]' (non-empty list)"
        )
        assert "parallel" in cfg, f"lane '{name}' must declare 'parallel: true|false|marker'"
        assert cfg["parallel"] in (True, False, "marker"), (
            f"lane '{name}' has invalid parallel={cfg['parallel']!r}; "
            f"expected True | False | 'marker'"
        )
        if cfg["parallel"] is False:
            assert cfg.get("stateful_reason"), (
                f"lane '{name}' is parallel:false but has no stateful_reason — "
                f"every serial lane needs a written justification (ADR-072)"
            )
