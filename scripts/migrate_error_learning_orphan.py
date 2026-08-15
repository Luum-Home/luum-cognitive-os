#!/usr/bin/env python3
# SCOPE: os-only
"""Inspect (and, if the operator decides, migrate) the orphan error-learning log.

Context: until 2026-08-15 this repo had two files named ``error-learning.jsonl``.
``.cognitive-os/error-learning.jsonl`` was written by
``cos_lib.evolve_task_queue`` and read by nobody;
``.cognitive-os/metrics/error-learning.jsonl`` is the path every consumer reads.
The writer has been repointed. This script exists only to answer "and the 102
old rows?" — it does NOT decide.

READ-ONLY BY DEFAULT. ``--apply`` is the only way to write, and writing touches
operator telemetry, so it is a deliberate operator action, not a script default.

Exit codes: 0 nothing to migrate / 1 rows found (findings) / 2 error.

Usage::

    python3 scripts/migrate_error_learning_orphan.py            # inspect
    python3 scripts/migrate_error_learning_orphan.py --json     # machine-readable
    python3 scripts/migrate_error_learning_orphan.py --apply    # operator only
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ORPHAN = REPO_ROOT / ".cognitive-os" / "error-learning.jsonl"
CANONICAL = REPO_ROOT / ".cognitive-os" / "metrics" / "error-learning.jsonl"

# The unit-test fixture title that produced the orphan rows. A row carrying it
# is test bleed, not an operator-visible event.
TEST_FIXTURE_MARKERS = ("Overflow proposal",)


def _read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _is_test_bleed(row: dict) -> bool:
    blob = json.dumps(row)
    return any(marker in blob for marker in TEST_FIXTURE_MARKERS)


def _to_canonical(row: dict) -> dict:
    """Translate a legacy {ts, source, message, context} row to the read schema."""
    raw_ts = str(row.get("ts", ""))
    try:
        parsed = datetime.fromisoformat(raw_ts)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        parsed = datetime.now(timezone.utc)
    message = str(row.get("message", ""))
    return {
        "timestamp": parsed.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timestamp_epoch": int(parsed.timestamp()),
        "type": "QUEUE_CAPACITY",
        "service": "evolve-queue",
        "fingerprint": hashlib.sha256(
            f"QUEUE_CAPACITY|evolve-queue|{message}".encode("utf-8")
        ).hexdigest()[:32],
        "command": "cos_lib.evolve_task_queue.enqueue",
        "message": message,
        "context": row.get("context", {}),
        "exit_code": None,
        "migrated_from": ".cognitive-os/error-learning.jsonl",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="append rows to the canonical file")
    ap.add_argument("--include-test-bleed", action="store_true",
                    help="with --apply, also migrate rows produced by unit tests")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    rows = _read_rows(ORPHAN)
    bleed = [r for r in rows if _is_test_bleed(r)]
    real = [r for r in rows if not _is_test_bleed(r)]
    by_day = collections.Counter(str(r.get("ts", ""))[:10] for r in rows)

    verdict = (
        "DO_NOT_MIGRATE" if rows and not real
        else "OPERATOR_DECISION" if real
        else "NOTHING_TO_MIGRATE"
    )

    summary = {
        "orphan_path": str(ORPHAN.relative_to(REPO_ROOT)),
        "canonical_path": str(CANONICAL.relative_to(REPO_ROOT)),
        "orphan_rows": len(rows),
        "canonical_rows": len(_read_rows(CANONICAL)),
        "test_bleed_rows": len(bleed),
        "operator_visible_rows": len(real),
        "date_range": [min(by_day), max(by_day)] if by_day else [],
        "verdict": verdict,
        "applied": False,
    }

    if args.apply:
        candidates = rows if args.include_test_bleed else real
        if not candidates:
            summary["applied"] = False
            summary["apply_note"] = (
                "nothing migrated: every orphan row is unit-test bleed. "
                "Re-run with --include-test-bleed to override."
            )
        else:
            CANONICAL.parent.mkdir(parents=True, exist_ok=True)
            with CANONICAL.open("a") as fh:
                for row in candidates:
                    fh.write(json.dumps(_to_canonical(row)) + "\n")
            summary["applied"] = True
            summary["rows_appended"] = len(candidates)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"orphan     : {summary['orphan_path']} — {summary['orphan_rows']} rows")
        print(f"canonical  : {summary['canonical_path']} — {summary['canonical_rows']} rows")
        if by_day:
            print(f"date range : {summary['date_range'][0]} → {summary['date_range'][1]}")
        print(f"test bleed : {summary['test_bleed_rows']} rows (unit-test fixture)")
        print(f"real events: {summary['operator_visible_rows']} rows")
        print(f"verdict    : {verdict}")
        if verdict == "DO_NOT_MIGRATE":
            print(
                "\n  Every orphan row was produced by tests/unit/test_evolve_task_queue.py\n"
                "  writing into the real repo. Migrating them would inject synthetic\n"
                "  saturation events into operator telemetry. Recommend: leave the file\n"
                "  in place as evidence, migrate nothing."
            )
        if not args.apply:
            print("\n(read-only run — nothing written. --apply to migrate.)")

    return 1 if rows else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
