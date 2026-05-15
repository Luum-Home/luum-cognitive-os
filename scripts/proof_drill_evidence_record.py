#!/usr/bin/env python3
# SCOPE: os-only
"""Record machine-readable proof-drill evidence rows for ACC."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "06-Daily" / "reports" / "proof-drill-evidence-latest.json"


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": "proof-drill-evidence.v1",
            "generated_at": utc_now(),
            "source_report": "manual-or-scripted-proof-drill-record",
            "rows": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def upsert_row(data: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    rows = [existing for existing in data.get("rows", []) if existing.get("id") != row["id"]]
    rows.append(row)
    data["rows"] = sorted(rows, key=lambda item: str(item.get("id", "")))
    data["generated_at"] = utc_now()
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Proof drill registry id")
    parser.add_argument("--status", required=True, choices=("passed", "failed", "skipped", "unverified"))
    parser.add_argument("--scope", required=True, choices=("os-self", "consumer-project", "both"))
    parser.add_argument("--command", required=True)
    parser.add_argument("--exit-code", type=int)
    parser.add_argument("--artifact", action="append", default=[], help="Evidence artifact path; repeatable")
    parser.add_argument("--proves", required=True)
    parser.add_argument("--does-not-prove", required=True)
    parser.add_argument("--source-report", default="manual-or-scripted-proof-drill-record")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = Path(args.out)
    data = load(out)
    data["source_report"] = args.source_report
    row = {
        "id": args.id,
        "status": args.status,
        "scope": args.scope,
        "command": args.command,
        "exit_code": args.exit_code,
        "evidence_artifacts": args.artifact,
        "proves": args.proves,
        "does_not_prove": args.does_not_prove,
        "recorded_at": utc_now(),
    }
    data = upsert_row(data, row)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    payload = {"ok": True, "out": str(out), "id": args.id, "status": args.status, "rows": len(data["rows"])}
    print(json.dumps(payload, sort_keys=True) if args.json else f"recorded {args.id} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
