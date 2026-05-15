#!/usr/bin/env python3
# SCOPE: os-only
"""Backfill cost-events.jsonl to MetricEvent schema (ADR-028 D1.A.1).

Reads existing cost-events.jsonl, converts rows that pre-date MetricEvent
(i.e. rows lacking ``schema_version``) using ``normalize_legacy_row``, and
writes the result to cost-events.jsonl.new.  An atomic rename is performed
only after the full file is processed successfully.

Usage:
    python3 scripts/backfill_cost_events.py [path-to-cost-events.jsonl]

If no path is given, defaults to .cognitive-os/metrics/cost-events.jsonl
relative to the current directory.

Decision: backfill is OPTIONAL — consumers already tolerate mixed schema
(missing fields default to 0 / empty string).  Run this once to homogenise
an existing file; new rows written after migration are already MetricEvent-
shaped so the file converges over time without any backfill.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.metric_event import normalize_legacy_row


def _guess_source(row: dict) -> str:
    """Heuristic: infer writer source from row fields."""
    if "action" in row:
        return "token_budget_monitor"
    if "agent" in row:
        return "record_completion"
    return "unknown"


def backfill(path: str) -> None:
    src = Path(path)
    if not src.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    dest = Path(str(src) + ".new")
    before = 0
    after = 0
    skipped = 0

    with src.open("r", encoding="utf-8") as fin, dest.open("w", encoding="utf-8") as fout:
        for raw_line in fin:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            before += 1
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError:
                # Pass through unparseable lines unchanged
                fout.write(raw_line + "\n")
                skipped += 1
                continue

            if "schema_version" in row:
                # Already MetricEvent-shaped — passthrough
                fout.write(raw_line + "\n")
                after += 1
                continue

            source = _guess_source(row)
            normalised = normalize_legacy_row(row, source=source, event_type="cost.recorded")
            fout.write(json.dumps(normalised, separators=(",", ":"), sort_keys=True) + "\n")
            after += 1

    # Atomic rename
    os.replace(dest, src)
    print(f"Backfill complete: {before} rows read, {after} rows written, {skipped} unparseable passthrough.")
    print(f"Output: {src}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else ".cognitive-os/metrics/cost-events.jsonl"
    backfill(target)
