#!/usr/bin/env python3
"""Create a keep/harden/demote/delete backlog from audit outputs."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.script_io import load_json_or_empty as load_json


@dataclass(frozen=True)
class BacklogItem:
    priority: str
    action: str
    source: str
    item: str
    reason: str


def build_backlog(row_audit: dict, claim_audit: dict) -> list[BacklogItem]:
    items: list[BacklogItem] = []
    for row in row_audit.get("rows", []):
        severity = row.get("severity")
        status = row.get("status")
        if severity == "high" and status == "aspirational":
            action = "delete-or-wire"
            priority = "P1"
        elif severity == "high":
            action = "harden"
            priority = "P1"
        elif status == "aspirational":
            action = "demote-or-archive"
            priority = "P2"
        else:
            continue
        items.append(
            BacklogItem(
                priority=priority,
                action=action,
                source="primitive-row-audit",
                item=f"{row.get('family')}:{row.get('path')}",
                reason=f"{status}/{severity}: {row.get('evidence')} -> {row.get('next_action')}",
            )
        )
    for row in claim_audit.get("rows", []):
        if row.get("status") == "unmapped":
            items.append(
                BacklogItem(
                    priority="P2",
                    action="demote-or-prove-claim",
                    source="claim-proof-audit",
                    item=f"{row.get('path')}:{row.get('line')}",
                    reason=str(row.get("claim")),
                )
            )
        elif row.get("status") == "weak-proof":
            items.append(
                BacklogItem(
                    priority="P2",
                    action="add-proof-link",
                    source="claim-proof-audit",
                    item=f"{row.get('path')}:{row.get('line')}",
                    reason=str(row.get("claim")),
                )
            )
    return items


def write_markdown(items: list[BacklogItem], path: Path) -> None:
    lines = ["# Reduction Sprint Backlog — Latest", "", "| Priority | Action | Source | Item | Reason |", "|---|---|---|---|---|"]
    for item in items[:250]:
        reason = item.reason.replace("|", "\\|")[:260]
        lines.append(f"| {item.priority} | {item.action} | {item.source} | `{item.item}` | {reason} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate reduction sprint backlog")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--row-audit", default="docs/06-Daily/reports/primitive-row-audit-latest.json")
    parser.add_argument("--claim-audit", default="docs/06-Daily/reports/claim-proof-latest.json")
    parser.add_argument("--json-out", default="docs/06-Daily/reports/reduction-backlog-latest.json")
    parser.add_argument("--md-out", default="docs/06-Daily/reports/reduction-backlog-latest.md")
    parser.add_argument(
        "--fail-nonzero",
        action="store_true",
        help="Exit non-zero when the generated reduction backlog contains any item.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    items = build_backlog(load_json(root / args.row_audit), load_json(root / args.claim_audit))
    payload = {"items": [asdict(item) for item in items]}
    json_path = root / args.json_out
    md_path = root / args.md_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(items, md_path)
    print(json.dumps({"items": len(items), "json": str(json_path), "markdown": str(md_path)}, sort_keys=True))
    if args.fail_nonzero and items:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
