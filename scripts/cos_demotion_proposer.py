#!/usr/bin/env python3
# SCOPE: os-only
"""cos-demotion-proposer — propose-only advisory/blocking->demoted evaluator.

ADR-180. For primitives at lifecycle_state advisory or blocking with zero
records in the last N days (default 90), emit a demotion proposal artifact.

NEVER modifies primitive-lifecycle.yaml or the registry lock.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.cos_promotion_proposer import (  # noqa: E402  (sibling import)
    _load_lifecycle,
    _skill_basename,
    _now_iso,
    _today_dir,
    _append_metric,
    _parse_time,
    _table_exists,
)

DEFAULT_DB = PROJECT_ROOT / ".cognitive-os" / "skill_store.db"
DEFAULT_LIFECYCLE = PROJECT_ROOT / "manifests" / "primitive-lifecycle.yaml"
DEFAULT_METRICS = PROJECT_ROOT / ".cognitive-os" / "metrics" / "demotion-proposals.jsonl"
DEFAULT_OUT_ROOT = PROJECT_ROOT / "docs" / "06-Daily" / "reports" / "demotion-proposals"


def _records_in_window(db_path: Path, name: str, days: int) -> int:
    """Return exact execution count within the last `days` for skill `name`."""
    if not db_path.exists():
        return 0
    import hashlib

    skill_id = hashlib.sha256(name.encode("utf-8")).hexdigest()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    uri = f"file:{db_path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        if _table_exists(conn, "skill_execution_events"):
            rows = conn.execute(
                "SELECT timestamp FROM skill_execution_events WHERE skill_id = ?",
                (skill_id,),
            ).fetchall()
            conn.close()
            return sum(
                1
                for row in rows
                if (ts := _parse_time(str(row["timestamp"] or ""))) and ts >= cutoff
            )
        row = conn.execute(
            "SELECT total_completions, last_updated FROM skill_records WHERE skill_id = ?",
            (skill_id,),
        ).fetchone()
        conn.close()
    except sqlite3.Error:
        return 0
    if not row:
        return 0
    last_updated = str(row[1] or "")
    if not last_updated:
        return 0
    parsed = _parse_time(last_updated)
    if not parsed or parsed < cutoff:
        return 0
    return int(row[0] or 0)


def _proposal_markdown(prim: Dict[str, Any], window_days: int) -> str:
    name = _skill_basename(str(prim.get("id", "unknown")))
    state = str(prim.get("lifecycle_state", "advisory"))
    target_state = "demoted"
    lines = [
        f"# Demotion Proposal — {name}",
        "",
        f"**Date**: {_now_iso()}",
        "**Status**: propose-only (operator review required)",
        "**Runtime effect**: none (no manifest mutation)",
        "",
        "## Current state",
        "",
        f"- primitive id: `{prim.get('id')}`",
        f"- lifecycle_state: `{state}`",
        f"- maturity: `{prim.get('maturity', 'unknown')}`",
        f"- distribution: `{prim.get('distribution', 'unknown')}`",
        "",
        "## Evidence summary",
        "",
        f"- record_count over last {window_days} days: **0**",
        "- This primitive has not been invoked in the demotion window.",
        "",
        "## Proposed new state",
        "",
        f"- lifecycle_state: `{target_state}`",
        "",
        "## Rollback path",
        "",
        f"- Revert `manifests/primitive-lifecycle.yaml` field `lifecycle_state` to `{state}`.",
        "",
        "## Falsifiable claim",
        "",
        "If genuinely needed, this primitive should regain at least 1 invocation",
        "within 30 days of demotion. If invocations resume, an operator should",
        "promote it back. If no invocations occur, archival is justified.",
        "",
        "## Operator action",
        "",
        "Approve by editing `manifests/primitive-lifecycle.yaml`. This script",
        "will not perform that edit.",
        "",
        "## Caveat",
        "",
        "Rare-but-important primitives (e.g. release-os, audit-integrity) may",
        "trip this rule under quiet weeks. Operator must judge whether absence",
        "of usage means decay or correct dormancy.",
        "",
    ]
    return "\n".join(lines)


def evaluate(
    primitives: Iterable[Dict[str, Any]],
    db_path: Path,
    window_days: int,
    skill_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for prim in primitives:
        state = str(prim.get("lifecycle_state", "")).strip().strip('"').strip("'")
        if state not in ("advisory", "blocking"):
            continue
        name = _skill_basename(str(prim.get("id", "")))
        if skill_filter and skill_filter not in (name, str(prim.get("id", ""))):
            continue
        recent = _records_in_window(db_path, name, window_days)
        eligible = recent == 0
        out.append({"prim": prim, "recent_records": recent, "eligible": eligible, "name": name})
    return out


def main(argv: Optional[List[str]] = None) -> int:
    if os.environ.get("DISABLE_PROMOTION_PROPOSER", "") in ("1", "true", "yes"):
        # Same killswitch covers demotion proposer (it's the same operator surface).
        print("DISABLE_PROMOTION_PROPOSER set; exiting", file=sys.stderr)
        return 0

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--lifecycle", type=Path, default=DEFAULT_LIFECYCLE)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", dest="apply_", action="store_true")
    parser.add_argument("--skill", type=str, default=None)
    parser.add_argument("--window-days", type=int, default=90)
    args = parser.parse_args(argv)

    if args.apply_:
        args.dry_run = False

    if not args.lifecycle.exists():
        print(f"lifecycle file not found: {args.lifecycle}", file=sys.stderr)
        return 1

    primitives = _load_lifecycle(args.lifecycle)
    results = evaluate(primitives, args.db, args.window_days, skill_filter=args.skill)
    eligible = [r for r in results if r["eligible"]]

    today = _today_dir()
    out_dir = args.out_root / today
    written: List[str] = []
    for r in eligible:
        md = _proposal_markdown(r["prim"], args.window_days)
        target = out_dir / f"{r['name']}.md"
        if not args.dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(md, encoding="utf-8")
            written.append(str(target))

    metric = {
        "ts": _now_iso(),
        "kind": "demotion-proposer-run",
        "evaluated": len(results),
        "eligible": len(eligible),
        "written": len(written),
        "dry_run": args.dry_run,
        "window_days": args.window_days,
        "skill_filter": args.skill,
    }
    _append_metric(args.metrics, metric)

    summary = {
        "evaluated": len(results),
        "eligible": [r["name"] for r in eligible],
        "written": written,
        "dry_run": args.dry_run,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
