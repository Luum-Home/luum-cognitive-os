#!/usr/bin/env python3
# SCOPE: os-only
"""Audit the `skill` field of the skill telemetry streams.

Both .cognitive-os/metrics/skill-metrics.jsonl and skill-feedback.jsonl carry a
`skill` field that five KPI modules read back as a skill identifier
(cos_lib/kpi_collector.py, repetition_detector.py, component_usage_tracker.py,
singularity.py, performance_ledger.py) plus the two that act on it
(skill_failure_repair.py emits repair signals, consumer_improvement_proposals.py
emits "Review degraded skill <name>").  A value that names no skill on disk makes
those consumers report work on a skill that does not exist.

Read-only.  Exit codes: 0 = no unattributable rows, 1 = findings, 2 = error.

Usage:
    .venv/bin/python scripts/audit_skill_telemetry_names.py [--json] [--root PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# `unknown-agent` is the sentinel that packages/skill-governance/hooks/skill-tracker.sh
# writes on purpose when an Agent run cannot be attributed to any skill (see
# commit bc04ff86b).  It is honest non-attribution, not a corrupt value, so it is
# counted separately instead of being reported as a finding.
SENTINELS = {"unknown-agent"}

STREAMS = ("skill-metrics.jsonl", "skill-feedback.jsonl")


def known_skills(root: Path) -> set[str]:
    names: set[str] = set()
    for pattern in (
        "skills/*/SKILL.md",
        "packages/*/skills/*/SKILL.md",
        ".cognitive-os/skills/cos/*/SKILL.md",
    ):
        names.update(p.parent.name for p in root.glob(pattern))
    return names


def audit_stream(path: Path, known: set[str]) -> dict:
    result = {
        "path": str(path),
        "exists": path.exists(),
        "total": 0,
        "valid": 0,
        "sentinel": 0,
        "unattributable": 0,
        "unparsable": 0,
        "unattributable_names": {},
        "unattributable_first_ts": None,
        "unattributable_last_ts": None,
    }
    if not path.exists():
        return result
    bogus: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        result["total"] += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            result["unparsable"] += 1
            continue
        skill = row.get("skill")
        if skill in known:
            result["valid"] += 1
        elif skill in SENTINELS:
            result["sentinel"] += 1
        else:
            result["unattributable"] += 1
            bogus[str(skill)] += 1
            ts = row.get("timestamp")
            if ts:
                if result["unattributable_first_ts"] is None or ts < result["unattributable_first_ts"]:
                    result["unattributable_first_ts"] = ts
                if result["unattributable_last_ts"] is None or ts > result["unattributable_last_ts"]:
                    result["unattributable_last_ts"] = ts
    result["unattributable_names"] = dict(bogus.most_common(20))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=None, help="repo root (default: script's repo)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    if not root.is_dir():
        print(f"error: root not a directory: {root}", file=sys.stderr)
        return 2

    known = known_skills(root)
    if not known:
        print(f"error: no SKILL.md found under {root}", file=sys.stderr)
        return 2

    metrics_dir = root / ".cognitive-os" / "metrics"
    reports = [audit_stream(metrics_dir / name, known) for name in STREAMS]

    if args.json:
        print(json.dumps({"root": str(root), "known_skills": len(known), "streams": reports}, indent=2))
    else:
        print(f"known skills on disk: {len(known)}")
        for r in reports:
            if not r["exists"]:
                print(f"\n{r['path']}: absent")
                continue
            total = r["total"] or 1
            print(f"\n{r['path']}")
            print(f"  rows                 : {r['total']}")
            print(f"  naming a real skill  : {r['valid']} ({100 * r['valid'] / total:.1f}%)")
            print(f"  sentinel (unknown-agent): {r['sentinel']} ({100 * r['sentinel'] / total:.1f}%)")
            print(f"  unattributable       : {r['unattributable']} ({100 * r['unattributable'] / total:.1f}%)")
            if r["unparsable"]:
                print(f"  unparsable           : {r['unparsable']}")
            if r["unattributable"]:
                print(f"  window               : {r['unattributable_first_ts']} .. {r['unattributable_last_ts']}")
                print(f"  names                : {r['unattributable_names']}")

    return 1 if any(r["unattributable"] for r in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
