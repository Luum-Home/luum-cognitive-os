#!/usr/bin/env python3
# SCOPE: project
"""Export SO rules/ content into an adopting project's docs/08-standards/.

Part of ADR-054/055: skills emit into the 10-category convention. The
rules/ directory is the canonical source of standards ("so-slo.md",
"definition-of-done.md", "credential-management.md", ...). Adopting
projects often want a SNAPSHOT of the rules they've committed to
follow, in their own docs, so new contributors can read them without
needing access to the SO repo.

This CLI produces a single consolidated markdown file:
  docs/08-standards/rules-snapshot-<DATE>.md

The snapshot has:
  - a header with SO commit SHA (if available) and export timestamp
  - a TOC of rule names
  - concatenated bodies of each rule, with a `---` separator and a source
    note (relative SO path)

Only rules listed in --rules (or the built-in default set) are exported
— the full rules/ directory is too large to be useful as a snapshot and
includes internal protocols not relevant to adopting projects.

Usage:
  uv run python3 scripts/rules_export.py \
      --project-dir /path/to/adopting-project \
      [--rules so-slo definition-of-done credential-management] \
      [--so-root /path/to/cognitive-os-repo] \
      [--json]

Exit codes:
  0 — snapshot written
  1 — validation error (missing rule file, bad project dir)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from lib.docs_writer import write_doc  # noqa: E402

CATEGORY = "08-standards"

# Minimal default set — the rules most relevant to adopting projects.
# Keep this list short; adopters can expand via --rules.
DEFAULT_RULES = [
    "so-slo",
    "definition-of-done",
    "credential-management",
    "acceptance-criteria",
    "responsiveness",
    "adversarial-review",
]


def _read_rule(so_root: Path, name: str) -> str:
    """Read rules/<name>.md. Raise FileNotFoundError if missing."""
    path = so_root / "rules" / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"rule file not found: {path}")
    return path.read_text()


def _so_sha(so_root: Path) -> str:
    """Best-effort git SHA of SO repo. Returns 'unknown' on failure."""
    try:
        out = subprocess.run(
            ["git", "-C", str(so_root), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def build_snapshot(so_root: Path, rule_names: list[str]) -> str:
    """Compose the consolidated markdown snapshot body."""
    sha = _so_sha(so_root)
    now = datetime.now().isoformat(timespec="seconds")
    lines: list[str] = [
        "# Rules Snapshot (ADR-054/055 — category 08-standards)",
        "",
        f"**Exported**: {now}  ",
        f"**Source**: Cognitive OS `rules/` @ `{sha}`  ",
        f"**Rules included**: {len(rule_names)}",
        "",
        "> This is a point-in-time snapshot. The authoritative source is the",
        "> SO repo's `rules/` directory. Re-run `/rules-export` to refresh.",
        "",
        "## Table of Contents",
        "",
    ]
    for name in rule_names:
        lines.append(f"- [{name}](#{name.lower()})")
    lines.append("")
    lines.append("---")
    lines.append("")
    for name in rule_names:
        body = _read_rule(so_root, name)
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"_Source: `rules/{name}.md`_")
        lines.append("")
        lines.append(body.rstrip())
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export SO rules/ as a snapshot into docs/08-standards/.",
    )
    parser.add_argument("--project-dir", required=True)
    parser.add_argument(
        "--rules",
        nargs="*",
        default=None,
        help=f"Rule base names to include. Default: {DEFAULT_RULES}",
    )
    parser.add_argument(
        "--so-root",
        default=str(_HERE),
        help="Cognitive OS repo root (default: this repo).",
    )
    parser.add_argument("--slug", default="rules-snapshot")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    so_root = Path(args.so_root).expanduser().resolve()
    if not (so_root / "rules").is_dir():
        print(f"error: rules/ not found under {so_root}", file=sys.stderr)
        return 1

    rule_names = args.rules if args.rules else DEFAULT_RULES

    try:
        body = build_snapshot(so_root, rule_names)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    out = write_doc(
        project_dir=Path(args.project_dir),
        category=CATEGORY,
        slug=args.slug,
        body=body,
    )

    if args.json:
        print(json.dumps({
            "written": str(out),
            "category": CATEGORY,
            "rules_count": len(rule_names),
            "so_sha": _so_sha(so_root),
        }))
    else:
        print(f"wrote {out} ({len(rule_names)} rules)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
