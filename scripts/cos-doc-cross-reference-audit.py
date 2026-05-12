#!/usr/bin/env python3
# SCOPE: both
"""Doc cross-reference audit — fails if known primitives are not surfaced
where cold readers expect to find them.

Motivation: the 2026-05-12 sessions on ADR-273/274/275 surfaced repeatedly
that primitives can ship without appearing in the navigation surfaces
(MOCs, related ADRs, sibling scripts). This audit closes the meta-loop:
"built but not surfaced" is the anti-pattern we keep solving — now we
detect it programmatically.

Schema: doc-cross-reference-audit/v1.
Emits findings[] in the control-plane-audit runner shape (ADR-248).

Each contract is: "primitive X MUST be mentioned in surfaces A, B, C".
Contracts live inline (small, audited list). Easy to extend.

Usage:
  python3 scripts/cos-doc-cross-reference-audit.py             # JSON to stdout
  python3 scripts/cos-doc-cross-reference-audit.py --strict    # exit 2 if any miss
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "doc-cross-reference-audit/v1"


# Each contract: name -> {required_in: [surface paths], grep: <token to find>}
CONTRACTS: list[dict[str, Any]] = [
    {
        "primitive": "cos-pending-truth-close",
        "grep": "cos-pending-truth-close",
        "required_in": [
            "docs/00-MOCs/operations.md",
            "docs/architecture/pending-truth-architecture.md",
            "docs/adrs/ADR-275-closure-and-projection-primitives.md",
            "scripts/cos-adr-close",
        ],
    },
    {
        "primitive": "cos-adr-close",
        "grep": "cos-adr-close",
        "required_in": [
            "docs/00-MOCs/operations.md",
            "docs/architecture/pending-truth-architecture.md",
            "docs/adrs/ADR-275-closure-and-projection-primitives.md",
            "scripts/cos-pending-truth-close",
        ],
    },
    {
        "primitive": "cos-session-start-projector",
        "grep": "cos-session-start-projector",
        "required_in": [
            "docs/00-MOCs/operations.md",
            "docs/architecture/pending-truth-architecture.md",
            "docs/adrs/ADR-275-closure-and-projection-primitives.md",
        ],
    },
    {
        "primitive": "cos-closure-trust-signal",
        "grep": "cos-closure-trust-signal",
        "required_in": [
            "docs/00-MOCs/quality.md",
            "docs/architecture/pending-truth-architecture.md",
            "manifests/control-plane-audits.yaml",
        ],
    },
    {
        "primitive": "STATUS-TAXONOMY",
        "grep": "STATUS-TAXONOMY",
        "required_in": [
            "docs/00-MOCs/operations.md",
            "docs/architecture/pending-truth-architecture.md",
            "docs/adrs/ADR-274-operational-guide-required-for-capability-adrs.md",
        ],
    },
    {
        "primitive": "cos-pending-truth-aggregator",
        "grep": "cos-pending-truth-aggregator",
        "required_in": [
            "docs/00-MOCs/operations.md",
            "docs/architecture/pending-truth-architecture.md",
            "docs/adrs/ADR-273-pending-truth-ledger-and-bilateral-verification.md",
        ],
    },
    {
        "primitive": "pending-truth-architecture",
        "grep": "pending-truth-architecture.md",
        "required_in": [
            "docs/adrs/ADR-273-pending-truth-ledger-and-bilateral-verification.md",
            "docs/adrs/ADR-274-operational-guide-required-for-capability-adrs.md",
            "docs/adrs/ADR-275-closure-and-projection-primitives.md",
            "docs/00-MOCs/operations.md",
        ],
    },
    {
        "primitive": "session-pending-brief",
        "grep": "session-pending-brief",
        "required_in": [
            "docs/00-MOCs/operations.md",
            "skills/CATALOG.md",
            "skills/CATALOG-COMPACT.md",
            "skills/session-pending-close/SKILL.md",
        ],
    },
    {
        "primitive": "session-pending-close",
        "grep": "session-pending-close",
        "required_in": [
            "docs/00-MOCs/operations.md",
            "skills/CATALOG.md",
            "skills/CATALOG-COMPACT.md",
            "skills/session-pending-brief/SKILL.md",
        ],
    },
    {
        "primitive": "cos-subprocess-timeout-audit",
        "grep": "cos-subprocess-timeout-audit",
        "required_in": [
            "docs/adrs/ADR-278-subprocess-run-timeout-discipline.md",
            "manifests/control-plane-audits.yaml",
            "manifests/documentation-truth-claims.yaml",
        ],
    },
]


def _resolve_project_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    for env_var in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        if env_var in os.environ:
            return Path(os.environ[env_var]).resolve()
    return Path.cwd().resolve()


def _file_mentions(path: Path, token: str) -> bool:
    if not path.exists():
        return False
    try:
        return token in path.read_text(encoding="utf-8")
    except OSError:
        return False


def audit(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    surveyed = 0
    missing_count = 0

    for contract in CONTRACTS:
        token = contract["grep"]
        for rel in contract["required_in"]:
            surveyed += 1
            target = root / rel
            if not _file_mentions(target, token):
                missing_count += 1
                findings.append({
                    "severity": "warn",
                    "code": "missing-cross-reference",
                    "message": (
                        f"Primitive {contract['primitive']!r} is not mentioned in "
                        f"{rel} — cold readers entering through this surface will "
                        "not discover it."
                    ),
                    "details": {
                        "primitive": contract["primitive"],
                        "grep_token": token,
                        "surface": rel,
                        "surface_exists": target.exists(),
                    },
                    "stable_id": f"adr-275/doc-xref/{contract['primitive']}/{rel}",
                    "adr": "ADR-275",
                })

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "contract_count": len(CONTRACTS),
        "surfaces_surveyed": surveyed,
        "missing_count": missing_count,
        "coverage_pct": round((surveyed - missing_count) / surveyed * 100.0, 2) if surveyed else 100.0,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ADR-275 doc cross-reference audit")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 if any cross-reference is missing",
    )
    args = parser.parse_args(argv)

    root = _resolve_project_dir(args.project_dir)
    payload = audit(root)
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    if args.strict and payload["missing_count"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
