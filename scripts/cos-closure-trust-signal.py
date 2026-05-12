#!/usr/bin/env python3
# SCOPE: both
"""ADR-275 §10 Phase 3 — closure-trail trust signal.

Quantifies "unaudited closures": ledger items whose status is
verified-done but for which no closure-trail entry exists.

Per ADR-244 + ADR-275 §3 (trust-score integration): a closure receipt is
a HIGH trust signal; manual edits to the source surface without going
through scripts/cos-pending-truth-close produce a verified-done status
but leave the closure-trail untouched. This script makes the asymmetry
quantifiable.

Output (JSON to stdout):
  {
    "schema_version": "closure-trust-signal/v1",
    "generated_at": "...",
    "total_verified_done":  <int>,
    "audited_closures":     <int>,    # have closure-trail entry
    "unaudited_closures":   <int>,    # done but no trail
    "audit_coverage_pct":   <float>,  # 0-100
    "trust_signal":         "HIGH" | "MEDIUM" | "LOW" | "ZERO",
    "details": [<list of unaudited item ids, capped at 20>],
  }

Trust bands:
  HIGH   >= 90% audited
  MEDIUM 70-90%
  LOW    50-70%
  ZERO   <50% (or no closures at all)

Exit codes:
  0 — emitted JSON (regardless of trust band)
  2 — required inputs missing (ledger absent)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LEDGER_PATH = "docs/reports/pending-truth-latest.json"
TRAIL_PATH = ".cognitive-os/audit/closure-trail.jsonl"
SCHEMA_VERSION = "closure-trust-signal/v1"


def _resolve_project_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    for env_var in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        if env_var in os.environ:
            return Path(os.environ[env_var]).resolve()
    return Path.cwd().resolve()


def _load_audited_ids(trail_path: Path) -> set[str]:
    """Return the set of ledger ids that appear in the closure trail."""
    if not trail_path.exists():
        return set()
    audited: set[str] = set()
    try:
        for line in trail_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("dry_run"):
                continue
            entry_id = entry.get("id")
            if entry_id:
                audited.add(entry_id)
    except OSError:
        pass
    return audited


def compute(root: Path) -> dict[str, Any]:
    ledger_path = root / LEDGER_PATH
    if not ledger_path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "error": "ledger not found",
            "ledger_path": LEDGER_PATH,
        }

    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "error": f"ledger parse error: {exc}",
        }

    audited = _load_audited_ids(root / TRAIL_PATH)
    items = ledger.get("items", []) or []
    done = [it for it in items if it.get("status") == "verified-done"]

    audited_done = [it for it in done if it.get("id") in audited]
    unaudited = [it for it in done if it.get("id") not in audited]

    total_done = len(done)
    audit_pct = (len(audited_done) / total_done * 100.0) if total_done else 0.0

    if total_done == 0:
        signal = "ZERO"  # no closures yet — empty trust
    elif audit_pct >= 90:
        signal = "HIGH"
    elif audit_pct >= 70:
        signal = "MEDIUM"
    elif audit_pct >= 50:
        signal = "LOW"
    else:
        signal = "ZERO"

    # findings[] in the control-plane-audit runner shape (ADR-248).
    # One warn finding per unaudited closure (capped at 20). Promoted to
    # block via --strict for CI gates.
    findings: list[dict[str, Any]] = []
    severity = "warn"
    if signal in {"LOW", "ZERO"} and total_done > 0:
        for it in unaudited[:20]:
            findings.append({
                "severity": severity,
                "code": "unaudited-closure",
                "message": f"Item {it.get('id')!r} is verified-done but has no closure-trail entry (manual closure)",
                "details": {
                    "id": it.get("id"),
                    "type": it.get("type"),
                    "source": it.get("source"),
                },
                "stable_id": f"adr-275/closure-trust/{it.get('id')}",
                "adr": "ADR-275",
            })

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_verified_done": total_done,
        "audited_closures": len(audited_done),
        "unaudited_closures": len(unaudited),
        "audit_coverage_pct": round(audit_pct, 2),
        "trust_signal": signal,
        "details": [it.get("id") for it in unaudited[:20]],
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ADR-275 Phase 3 closure trust signal")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 if trust signal is LOW or ZERO",
    )
    args = parser.parse_args(argv)

    root = _resolve_project_dir(args.project_dir)
    payload = compute(root)

    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if "error" in payload:
        return 2

    if args.strict and payload["trust_signal"] in {"LOW", "ZERO"}:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
