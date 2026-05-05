#!/usr/bin/env python3
# SCOPE: both
"""Capture a Markdown 'Key Learnings' section into COS improvement evidence."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib.key_learning_capture import append_records, build_records  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--source", default="assistant-final")
    parser.add_argument("--session-id", default=os.environ.get("COGNITIVE_OS_SESSION_ID") or os.environ.get("CODEX_SESSION_ID") or "unknown")
    parser.add_argument("--input", help="Markdown file to read; stdin when omitted")
    parser.add_argument("--out", help="Override JSONL output path")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    markdown = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    records = build_records(markdown, source=args.source, session_id=args.session_id)
    out = append_records(Path(args.project_dir), records, path=Path(args.out) if args.out else None)
    payload = {"records": len(records), "out": str(out), "ids": [record["id"] for record in records]}
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else f"captured {len(records)} key learning(s) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
