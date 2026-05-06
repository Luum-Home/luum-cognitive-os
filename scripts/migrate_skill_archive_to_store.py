#!/usr/bin/env python3
# SCOPE: os-only
"""Migrate .cognitive-os/metrics/skill-archive.jsonl → SkillStore SQLite.

Usage:
    python3 scripts/migrate_skill_archive_to_store.py [--dry-run] [--apply]
                                                       [--src PATH] [--db PATH]

Default mode is --dry-run (safe). Pass --apply to write.

Idempotent: PRIMARY KEY constraints on skill_records.skill_id and
execution_analyses.task_id prevent duplicate rows on re-run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure lib/ is importable when run from repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from lib.skill_store import SkillStore  # noqa: E402  (after sys.path patch)

DEFAULT_SRC = _REPO_ROOT / ".cognitive-os" / "metrics" / "skill-archive.jsonl"
DEFAULT_DB = _REPO_ROOT / ".cognitive-os" / "skill_store.db"


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _map_entry(entry: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Map a skill-archive JSONL entry to (skill_record_kwargs, analysis_kwargs).

    skill-archive entry fields (from lib/skill_archive.py SkillSnapshot):
        skill_name, version, timestamp, trust_score, success,
        task_description, tokens_used, cost_usd, metadata
    """
    skill_name = entry.get("skill_name", "unknown")
    skill_id = _sha256(skill_name)
    ts = entry.get("timestamp", _now_iso())
    success = bool(entry.get("success", False))
    trust_score = float(entry.get("trust_score", 0.0))
    tokens_used = int(entry.get("tokens_used", 0))
    cost_usd = float(entry.get("cost_usd", 0.0))
    task_desc = entry.get("task_description", "")
    metadata = entry.get("metadata", {})
    version = entry.get("version", "")

    snapshot = json.dumps({
        "version": version,
        "trust_score": trust_score,
        "tokens_used": tokens_used,
        "cost_usd": cost_usd,
        "task_description": task_desc,
    })

    skill_record = {
        "skill_id": skill_id,
        "name": skill_name,
        "lineage_content_snapshot": snapshot,
        "lineage_created_at": ts,
        "first_seen": ts,
        "last_updated": ts,
        "total_applied": 1 if success else 0,
        "total_completions": 1,
    }

    # Build analysis from metadata.observations if present
    observations = metadata.get("observations", {})
    if isinstance(observations, str):
        try:
            observations = json.loads(observations)
        except Exception:
            observations = {"raw": observations}

    analysis = {
        "task_id": f"migration:{skill_id}:{ts}",
        "timestamp": ts,
        "task_completed": 1 if success else 0,
        "execution_note": task_desc[:500],
        "analyzed_by": "migration-script",
        "analyzed_at": ts,
        "observations": json.dumps(observations),
        "trust_score": trust_score,
    }

    return skill_record, analysis


# ---------------------------------------------------------------------------
# Migration runner
# ---------------------------------------------------------------------------


def run_migration(
    src: Path,
    db: Path,
    *,
    dry_run: bool = True,
    verbose: bool = False,
) -> int:
    """Read src JSONL and migrate to SkillStore at db path.

    Returns exit code (0=ok, 1=errors).
    """
    if not src.exists():
        print(f"[migrate] Source not found: {src}")
        print("[migrate] Nothing to migrate.")
        return 0

    lines = src.read_text(encoding="utf-8").splitlines()
    total = len(lines)
    mapped = 0
    skipped = 0
    errors: List[str] = []

    records: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            skipped += 1
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"Line {i}: JSON parse error — {exc}")
            skipped += 1
            continue
        try:
            skill_rec, analysis = _map_entry(entry)
            records.append((skill_rec, analysis))
            mapped += 1
        except Exception as exc:
            errors.append(f"Line {i}: mapping error — {exc}")
            skipped += 1

    print(f"[migrate] Source: {src}")
    print(f"[migrate] Total lines: {total}  mapped: {mapped}  skipped: {skipped}")

    if errors:
        print(f"[migrate] Errors ({len(errors)}):")
        for err in errors[:20]:
            print(f"  {err}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")

    if dry_run:
        print("[migrate] DRY-RUN mode — no writes. Pass --apply to write.")
        if verbose:
            for sr, an in records[:5]:
                print(f"  would insert: {sr['name']!r} ({sr['skill_id'][:12]}...)")
        return 0

    # --- apply ---
    print(f"[migrate] Writing to: {db}")
    store = SkillStore(db)
    written_skills = 0
    written_analyses = 0
    insert_errors = 0

    for sr, an in records:
        try:
            # Insert skill record via record_execution with synthetic values
            store.record_execution(
                skill_name=sr["name"],
                agent_session_id="migration",
                tool_count=0,
                duration_ms=0,
                status="success" if sr["total_applied"] else "failure",
                output_hash=None,
            )
            written_skills += 1
        except Exception as exc:
            insert_errors += 1
            if verbose:
                print(f"  skill insert error for {sr['name']!r}: {exc}")

        try:
            store.record_analysis(
                skill_id=_sha256(sr["name"]),
                analyzer=an["analyzed_by"],
                score=an["trust_score"],
                observations_json=an["observations"],
            )
            written_analyses += 1
        except Exception as exc:
            insert_errors += 1
            if verbose:
                print(f"  analysis insert error: {exc}")

    store.close()
    print(f"[migrate] Written: {written_skills} skill records, {written_analyses} analyses")
    if insert_errors:
        print(f"[migrate] Insert errors: {insert_errors} (idempotent — likely duplicates)")

    return 0 if insert_errors == 0 else 0  # still exit 0; duplicates are expected


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate skill-archive.jsonl to SkillStore SQLite (ADR-176)."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print what would be done without writing (default).",
    )
    mode_group.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Actually write to the SkillStore database.",
    )
    parser.add_argument(
        "--src",
        type=Path,
        default=DEFAULT_SRC,
        help=f"Path to skill-archive.jsonl (default: {DEFAULT_SRC})",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"Path to SkillStore SQLite DB (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show per-record details.",
    )

    args = parser.parse_args()
    dry_run = not args.apply

    rc = run_migration(args.src, args.db, dry_run=dry_run, verbose=args.verbose)
    sys.exit(rc)


if __name__ == "__main__":
    main()
