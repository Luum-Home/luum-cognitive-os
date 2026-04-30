#!/usr/bin/env python3
"""Measure token impact of tier_filter selective expansion.

Usage:
    python3 scripts/measure_expansion.py <buffer_file>
    cat prompt.txt | python3 scripts/measure_expansion.py -

Runs expand() with 4 tier_filter configurations and reports bytes / estimated
tokens / unexpanded-key counts per tier level.  Results are printed as an
ASCII table and also appended as one JSON line to
.cognitive-os/metrics/expansion-measurements.jsonl.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so lib/ imports work regardless of cwd.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from lib.ref_key_loader import expand, find_ref_keys  # noqa: E402


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_METRICS_DIR = _PROJECT_ROOT / ".cognitive-os" / "metrics"
_MEASUREMENTS_LOG = _METRICS_DIR / "expansion-measurements.jsonl"

_FILTER_CONFIGS: list[tuple[str, Optional[set[int]]]] = [
    ("full (None)", None),
    ("{0,1,2}", {0, 1, 2}),
    ("{0,1}", {0, 1}),
    ("{0}", {0}),
]


# ---------------------------------------------------------------------------
# Core measurement
# ---------------------------------------------------------------------------

def _count_unexpanded(expanded_text: str) -> int:
    """Count ref-key markers that remain in the expanded text."""
    return len(find_ref_keys(expanded_text))


def measure_buffer(text: str) -> dict:
    """Run all 4 tier_filter configs against text and return measurement dict."""
    results: dict[str, dict] = {}
    for label, tf in _FILTER_CONFIGS:
        expanded = expand(text, tier_filter=tf)
        b = len(expanded.encode("utf-8"))
        results[label] = {
            "bytes": b,
            "tokens_est": round(b / 4),
            "unexpanded_keys": _count_unexpanded(expanded),
        }
    return results


# ---------------------------------------------------------------------------
# Formatted table output
# ---------------------------------------------------------------------------

def _print_table(results: dict[str, dict], buffer_path: str) -> None:
    header = f"Expansion measurement: {buffer_path}"
    print()
    print(header)
    print("=" * len(header))
    col_w = [22, 10, 12, 18]
    row_fmt = "{:<22} {:>10} {:>12} {:>18}"
    print(row_fmt.format("tier_filter", "bytes", "tokens_est", "unexpanded_keys"))
    print("-" * (sum(col_w) + 3))
    for label, stats in results.items():
        print(row_fmt.format(
            label,
            stats["bytes"],
            stats["tokens_est"],
            stats["unexpanded_keys"],
        ))
    print()


# ---------------------------------------------------------------------------
# JSONL emission
# ---------------------------------------------------------------------------

def _emit_jsonl(text: str, results: dict[str, dict], buffer_path: str) -> None:
    """Append one measurement record to the metrics log."""
    _METRICS_DIR.mkdir(parents=True, exist_ok=True)

    fingerprint = text[:200]
    buffer_id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:12]

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "buffer_path": buffer_path,
        "buffer_id": buffer_id,
        "measurements": results,
    }
    with _MEASUREMENTS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    print(f"[measure_expansion] Logged to {_MEASUREMENTS_LOG.relative_to(_PROJECT_ROOT)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: measure_expansion.py <buffer_file|->\n", file=sys.stderr)
        return 2

    buffer_path = sys.argv[1]
    if buffer_path == "-":
        text = sys.stdin.read()
        display_path = "<stdin>"
    else:
        p = Path(buffer_path)
        if not p.exists():
            print(f"Error: file not found: {p}", file=sys.stderr)
            return 1
        text = p.read_text(encoding="utf-8")
        display_path = str(p)

    results = measure_buffer(text)
    _print_table(results, display_path)
    _emit_jsonl(text, results, display_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
