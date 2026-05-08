#!/usr/bin/env python3
"""Audit Engram observation topic_keys vs canonical filenames in the repo.

The convention (see rules/engram-organization.md) is that an observation
saved with topic_key "sdd/<change>/proposal" should correspond to a real
artifact in `openspec/changes/<change>/proposal.md` (or the engram-only
slot if openspec is not the active backend). Drift between topic_key and
canonical filename leads to broken `mem_search → mem_get_observation` flow.

Read-only. Reports drift; never mutates the engram store.

Usage:
    python3 scripts/audit-engram-topic-keys.py                # default db
    python3 scripts/audit-engram-topic-keys.py --db PATH      # custom db
    python3 scripts/audit-engram-topic-keys.py --json         # machine output
    python3 scripts/audit-engram-topic-keys.py --project NAME # filter
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path.home() / ".engram" / "engram.db"

# Conventional topic_key prefixes that map to repo paths.
# Each pattern: topic_key prefix → (relative-path-template, suffix)
PATTERNS = [
    # SDD artifacts: sdd/<change>/<phase> → openspec/changes/<change>/<phase>.md
    ("sdd/", "openspec/changes/", ".md"),
    # ADR observations: adr/NNN → docs/adrs/ADR-NNN-*.md
    ("adr/", "docs/adrs/", ""),
]


def expected_paths(topic_key: str, repo_root: Path) -> list[Path]:
    """Compute candidate filesystem paths a topic_key implies."""
    candidates: list[Path] = []
    for prefix, root, suffix in PATTERNS:
        if not topic_key.startswith(prefix):
            continue
        rest = topic_key[len(prefix):]
        if prefix == "sdd/":
            # sdd/<change>/<phase> → openspec/changes/<change>/<phase>.md
            parts = rest.split("/", 1)
            if len(parts) == 2:
                change, phase = parts
                candidates.append(repo_root / root / change / f"{phase}{suffix}")
        elif prefix == "adr/":
            # adr/228 → docs/adrs/ADR-228-*.md (glob match)
            num = rest.split("/", 1)[0]
            try:
                int(num)
                glob = list((repo_root / root).glob(f"ADR-{num}-*.md"))
                candidates.extend(glob)
            except ValueError:
                pass
    return candidates


def audit(db_path: Path, project: str | None, repo_root: Path) -> dict:
    if not db_path.exists():
        return {"error": f"engram db not found: {db_path}"}
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    sql = "SELECT id, project, topic_key FROM observations WHERE topic_key IS NOT NULL AND topic_key != ''"
    params: tuple = ()
    if project:
        sql += " AND project = ?"
        params = (project,)
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    drift = []
    matched = 0
    no_pattern = 0
    for rid, proj, topic in rows:
        candidates = expected_paths(topic, repo_root)
        if not candidates:
            no_pattern += 1
            continue
        if any(p.exists() for p in candidates):
            matched += 1
        else:
            drift.append({
                "id": rid,
                "project": proj,
                "topic_key": topic,
                "expected_any_of": [str(p.relative_to(repo_root)) for p in candidates],
            })

    return {
        "db": str(db_path),
        "project_filter": project,
        "total_observations_with_topic_key": len(rows),
        "matched_canonical_path": matched,
        "drift_count": len(drift),
        "no_pattern_match": no_pattern,
        "drift": drift,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--project", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args()

    report = audit(args.db, args.project, args.repo_root)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    if "error" in report:
        print(f"ERROR: {report['error']}", file=sys.stderr)
        return 2

    print(f"db: {report['db']}")
    print(f"project filter: {report['project_filter'] or '(all)'}")
    print(f"observations with topic_key: {report['total_observations_with_topic_key']}")
    print(f"  matched canonical path:    {report['matched_canonical_path']}")
    print(f"  drift (no file on disk):   {report['drift_count']}")
    print(f"  no recognised pattern:     {report['no_pattern_match']}")
    if report["drift"]:
        print()
        print("Drift entries (first 20):")
        for d in report["drift"][:20]:
            print(f"  id={d['id']:6d}  project={d['project']:25s}  topic={d['topic_key']}")
            for p in d["expected_any_of"]:
                print(f"      expected: {p}")
    return 0 if report["drift_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
