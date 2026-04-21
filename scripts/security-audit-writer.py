#!/usr/bin/env python3
# SCOPE: both
"""CLI sidecar for the security-audit skill (ADR-054/055).

The /security-audit skill is READ-ONLY and produces a markdown report in the
agent's response. When the user wants that report persisted into an adopting
project's `docs/04-seguridad/` directory (per the 10-category convention),
they invoke this CLI with --project-dir.

The CLI does NOT run the audit itself (that stays inside the skill). It
reads the audit report body from stdin or --report-file and writes it to
disk under the correct category.

Usage:
  uv run python3 scripts/security-audit-writer.py \
      --project-dir /path/to/adopting-project \
      --report-file /tmp/audit-report.md \
      [--slug initial-audit] \
      [--json]

  # Or pipe from stdin
  cat report.md | uv run python3 scripts/security-audit-writer.py \
      --project-dir ./myproj

Exit codes:
  0 — report written
  1 — validation error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib.docs_writer import write_doc  # noqa: E402


CATEGORY = "04-seguridad"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Persist a security-audit report into docs/04-seguridad/.",
    )
    parser.add_argument(
        "--project-dir",
        required=True,
        help="Adopting project root (must contain or allow creation of docs/).",
    )
    parser.add_argument(
        "--report-file",
        help="Path to report markdown. If omitted, reads from stdin.",
    )
    parser.add_argument(
        "--slug",
        default="security-audit",
        help="Filename slug (default: security-audit).",
    )
    parser.add_argument(
        "--filename",
        help="Override filename entirely (skips timestamp suffix).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    args = parser.parse_args()

    # Source the body
    if args.report_file:
        report_path = Path(args.report_file).expanduser()
        if not report_path.exists():
            print(f"error: report file not found: {report_path}", file=sys.stderr)
            return 1
        body = report_path.read_text()
    else:
        body = sys.stdin.read()

    if not body.strip():
        print("error: empty report body", file=sys.stderr)
        return 1

    out = write_doc(
        project_dir=Path(args.project_dir),
        category=CATEGORY,
        slug=args.slug,
        body=body,
        filename=args.filename,
    )

    if args.json:
        print(json.dumps({"written": str(out), "category": CATEGORY, "bytes": len(body)}))
    else:
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
