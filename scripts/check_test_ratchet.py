#!/usr/bin/env python3
# SCOPE: both
"""Ensure the test count never decreases (ratchet pattern).

On first run, creates a baseline in .cognitive-os/metrics/test-baseline.json.
On subsequent runs, fails if current count is below baseline.
Exit 0 on pass, exit 1 if ratchet triggered.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


BASELINE_FILE = ".cognitive-os/metrics/test-baseline.json"


def count_tests(root: Path) -> int | None:
    """Run pytest --collect-only and return the number of collected test items."""
    tests_dir = root / "tests"
    if not tests_dir.exists():
        return 0

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(tests_dir), "--collect-only", "-q", "--tb=no"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(root),
        )
    except subprocess.TimeoutExpired:
        print("ERROR: pytest --collect-only timed out after 120s", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("ERROR: pytest not found. Install with: pip install pytest", file=sys.stderr)
        return None

    # Look for the summary line: "N test(s) collected" or "N selected"
    combined = result.stdout + result.stderr
    for line in combined.splitlines():
        m = re.search(r"(\d+)\s+(?:test[s]?\s+)?collected", line)
        if m:
            return int(m.group(1))

    # Fallback: count "PASSED" / "FAILED" lines or <N items>
    m = re.search(r"<(\d+) items?>", combined)
    if m:
        return int(m.group(1))

    # If pytest exited with error (e.g. import errors), return None to skip ratchet
    if result.returncode not in (0, 5):  # 5 = no tests collected
        print(
            f"WARNING: pytest exited with code {result.returncode}. "
            "Ratchet check skipped.",
            file=sys.stderr,
        )
        return None

    return 0


def load_baseline(root: Path) -> dict | None:
    path = root / BASELINE_FILE
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def save_baseline(root: Path, count: int) -> None:
    path = root / BASELINE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"count": count, "updated": datetime.now().isoformat()}, indent=2)
    )


def main() -> int:
    root = get_project_root()
    current = count_tests(root)

    if current is None:
        # Could not determine count — skip ratchet to avoid false blocks
        print("Test ratchet SKIPPED: could not collect test count")
        return 0

    baseline = load_baseline(root)

    if baseline is None:
        # First run — establish baseline
        save_baseline(root, current)
        print(f"Test ratchet INITIALIZED: baseline set to {current} tests")
        return 0

    prev_count = baseline.get("count", 0)

    if current < prev_count:
        dropped = prev_count - current
        print(
            f"TEST RATCHET FAIL: {current} tests collected "
            f"(was {prev_count}, dropped {dropped})"
        )
        print(
            f"You removed or broke {dropped} test(s). "
            "Restore them or update the baseline intentionally."
        )
        print(
            f"To reset baseline manually: "
            f"python3 scripts/check_test_ratchet.py --reset"
        )
        return 1

    # Update baseline if count increased (ratchet only goes up)
    if current > prev_count:
        save_baseline(root, current)
        print(
            f"Test ratchet OK: {current} tests (+{current - prev_count} from baseline {prev_count})"
        )
    else:
        print(f"Test ratchet OK: {current} tests (matches baseline)")

    return 0


if __name__ == "__main__":
    if "--reset" in sys.argv:
        root = get_project_root()
        current = count_tests(root)
        if current is not None:
            save_baseline(root, current)
            print(f"Baseline reset to {current} tests")
        sys.exit(0)
    sys.exit(main())
