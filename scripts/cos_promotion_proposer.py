#!/usr/bin/env python3
# SCOPE: os-only
"""cos-promotion-proposer — propose-only sandbox->advisory lifecycle promoter.

ADR-180. Reads lib.skill_store.SkillStore + manifests/primitive-lifecycle.yaml.
For sandbox primitives meeting evidence thresholds, emits a proposal artifact
under docs/reports/promotion-proposals/<date>/<name>.md.

NEVER modifies primitive-lifecycle.yaml or agentic-primitive-registry.lock.yaml.
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

DEFAULT_DB = PROJECT_ROOT / ".cognitive-os" / "skill_store.db"
DEFAULT_LIFECYCLE = PROJECT_ROOT / "manifests" / "primitive-lifecycle.yaml"
DEFAULT_METRICS = PROJECT_ROOT / ".cognitive-os" / "metrics" / "promotion-proposals.jsonl"
DEFAULT_OUT_ROOT = PROJECT_ROOT / "docs" / "reports" / "promotion-proposals"


# ---------------------------------------------------------------------------
# Lifecycle YAML reader (no external deps; tolerant of pyyaml absence)
# ---------------------------------------------------------------------------


def _load_lifecycle(path: Path) -> List[Dict[str, Any]]:
    """Return list of primitives with at least id/lifecycle_state.

    Uses PyYAML if available, else a minimal line-oriented parser sufficient
    for the well-formed manifest in this repo.
    """
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        return list(data.get("primitives", []))
    except Exception:
        return _fallback_parse(text)


def _fallback_parse(text: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    in_primitives = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("primitives:"):
            in_primitives = True
            continue
        if not in_primitives:
            continue
        if line.startswith("- "):
            if current is not None:
                items.append(current)
            current = {}
            rest = line[2:]
            if ":" in rest:
                k, _, v = rest.partition(":")
                current[k.strip()] = v.strip()
            continue
        if current is None:
            continue
        if line.startswith("  ") and ":" in line and not line.lstrip().startswith("- "):
            k, _, v = line.strip().partition(":")
            current[k.strip()] = v.strip()
    if current is not None:
        items.append(current)
    return items


# ---------------------------------------------------------------------------
# SkillStore evidence query
# ---------------------------------------------------------------------------


def _parse_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _skill_evidence(db_path: Path, name: str, window_days: int = 30) -> Dict[str, Any]:
    """Return dict with windowed record_count, success_rate, judge_avg.

    All values default to 0.0 / 0 if the skill is absent or DB does not exist.
    """
    out = {"record_count": 0, "success_rate": 0.0, "judge_avg": 0.0, "judgments": 0}
    if not db_path.exists():
        return out
    import hashlib

    skill_id = hashlib.sha256(name.encode("utf-8")).hexdigest()
    uri = f"file:{db_path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        if _table_exists(conn, "skill_execution_events"):
            cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
            rows = conn.execute(
                "SELECT timestamp, applied FROM skill_execution_events WHERE skill_id = ?",
                (skill_id,),
            ).fetchall()
            recent = [
                row for row in rows
                if (ts := _parse_time(str(row["timestamp"] or ""))) and ts >= cutoff
            ]
            total = len(recent)
            applied = sum(int(row["applied"] or 0) for row in recent)
            out["record_count"] = total
            out["success_rate"] = (applied / total) if total > 0 else 0.0
        else:
            row = conn.execute(
                "SELECT total_completions, total_applied FROM skill_records WHERE skill_id = ?",
                (skill_id,),
            ).fetchone()
            if row:
                total = int(row["total_completions"] or 0)
                applied = int(row["total_applied"] or 0)
                out["record_count"] = total
                out["success_rate"] = (applied / total) if total > 0 else 0.0
        # Judgments: skill_judgments rows for this skill_id; skill_applied=1 = positive
        jrows = conn.execute(
            "SELECT skill_applied FROM skill_judgments WHERE skill_id = ?",
            (skill_id,),
        ).fetchall()
        if jrows:
            out["judgments"] = len(jrows)
            out["judge_avg"] = sum(int(r["skill_applied"]) for r in jrows) / len(jrows)
        conn.close()
    except sqlite3.Error:
        return out
    return out


# ---------------------------------------------------------------------------
# Proposal generation
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_dir() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _skill_basename(prim_id: str) -> str:
    """Extract a usable name from a primitive id like 'hooks/foo.sh' or 'skills/foo'."""
    base = prim_id.rsplit("/", 1)[-1]
    if base.endswith(".sh") or base.endswith(".py"):
        base = base.rsplit(".", 1)[0]
    return base


def _proposal_markdown(prim: Dict[str, Any], evidence: Dict[str, Any], thresholds: Dict[str, float]) -> str:
    name = _skill_basename(str(prim.get("id", "unknown")))
    lines = [
        f"# Promotion Proposal — {name}",
        "",
        f"**Date**: {_now_iso()}",
        "**Status**: propose-only (operator review required)",
        "**Runtime effect**: none (no manifest mutation, no routing change)",
        "",
        "## Current state",
        "",
        f"- primitive id: `{prim.get('id')}`",
        f"- lifecycle_state: `{prim.get('lifecycle_state', 'sandbox')}`",
        f"- maturity: `{prim.get('maturity', 'unknown')}`",
        f"- distribution: `{prim.get('distribution', 'unknown')}`",
        f"- owner_adr: `{prim.get('owner_adr', 'unknown')}`",
        "",
        "## Evidence summary (SkillStore)",
        "",
        f"- record_count: **{evidence['record_count']}** (threshold ≥ {int(thresholds['records'])})",
        f"- success_rate: **{evidence['success_rate']:.3f}** (threshold ≥ {thresholds['success']:.2f})",
        f"- judge_avg: **{evidence['judge_avg']:.3f}** over {evidence['judgments']} judgments (threshold ≥ {thresholds['judge']:.2f})",
        "",
        "## Proposed new state",
        "",
        "- lifecycle_state: `advisory`",
        "- distribution: unchanged",
        "- routing: enter advisory routing canon (operator action)",
        "",
        "## Rollback path",
        "",
        "- Revert `manifests/primitive-lifecycle.yaml` field `lifecycle_state` to `sandbox`.",
        "- No code changes are required to roll back.",
        "- This proposal does not move skill files.",
        "",
        "## Falsifiable claim",
        "",
        "If promoted to advisory, this primitive should sustain success_rate ≥",
        f"{thresholds['success']:.2f} for the next 30 days. If success_rate drops below",
        "0.7 over any 30-day window after promotion, generate a demotion proposal.",
        "",
        "## Operator action",
        "",
        "Approve by editing `manifests/primitive-lifecycle.yaml` and changing this",
        "primitive's `lifecycle_state` from `sandbox` to `advisory`. This script",
        "will not perform that edit.",
        "",
    ]
    return "\n".join(lines)


def _append_metric(metrics_path: Path, payload: Dict[str, Any]) -> None:
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with metrics_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def evaluate(
    primitives: Iterable[Dict[str, Any]],
    db_path: Path,
    thresholds: Dict[str, float],
    skill_filter: Optional[str] = None,
    window_days: int = 30,
) -> List[Dict[str, Any]]:
    """Return list of {prim, evidence, eligible} for sandbox primitives."""
    out: List[Dict[str, Any]] = []
    for prim in primitives:
        state = str(prim.get("lifecycle_state", "")).strip().strip('"').strip("'")
        if state != "sandbox":
            continue
        name = _skill_basename(str(prim.get("id", "")))
        if skill_filter and skill_filter not in (name, str(prim.get("id", ""))):
            continue
        ev = _skill_evidence(db_path, name, window_days=window_days)
        eligible = (
            ev["record_count"] >= thresholds["records"]
            and ev["success_rate"] >= thresholds["success"]
            and ev["judge_avg"] >= thresholds["judge"]
        )
        out.append({"prim": prim, "evidence": ev, "eligible": eligible, "name": name})
    return out


def main(argv: Optional[List[str]] = None) -> int:
    if os.environ.get("DISABLE_PROMOTION_PROPOSER", "") in ("1", "true", "yes"):
        print("DISABLE_PROMOTION_PROPOSER set; exiting", file=sys.stderr)
        return 0

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--lifecycle", type=Path, default=DEFAULT_LIFECYCLE)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", dest="apply_", action="store_true",
                        help="write proposal artifacts (does NOT modify manifest)")
    parser.add_argument("--skill", type=str, default=None)
    parser.add_argument("--threshold-records", type=int, default=50)
    parser.add_argument("--threshold-success", type=float, default=0.85)
    parser.add_argument("--threshold-judge", type=float, default=0.8)
    parser.add_argument("--window-days", type=int, default=30)
    args = parser.parse_args(argv)

    if args.apply_:
        args.dry_run = False

    thresholds = {
        "records": args.threshold_records,
        "success": args.threshold_success,
        "judge": args.threshold_judge,
    }

    if not args.lifecycle.exists():
        print(f"lifecycle file not found: {args.lifecycle}", file=sys.stderr)
        return 1

    primitives = _load_lifecycle(args.lifecycle)
    results = evaluate(primitives, args.db, thresholds, skill_filter=args.skill, window_days=args.window_days)

    eligible = [r for r in results if r["eligible"]]
    today = _today_dir()
    out_dir = args.out_root / today

    written: List[str] = []
    for r in eligible:
        md = _proposal_markdown(r["prim"], r["evidence"], thresholds)
        target = out_dir / f"{r['name']}.md"
        if not args.dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(md, encoding="utf-8")
            written.append(str(target))

    metric = {
        "ts": _now_iso(),
        "kind": "promotion-proposer-run",
        "evaluated": len(results),
        "eligible": len(eligible),
        "written": len(written),
        "dry_run": args.dry_run,
        "thresholds": thresholds,
        "skill_filter": args.skill,
        "window_days": args.window_days,
        "lifecycle_path": str(args.lifecycle),
        "db_path": str(args.db),
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
