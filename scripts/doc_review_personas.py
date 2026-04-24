#!/usr/bin/env python3
# SCOPE: both
"""/doc-review-personas — CLI.

Runs N persona lenses over a docs/ corpus in parallel, consolidates findings
into a severity-tiered report.

Examples:
  uv run python3 scripts/doc_review_personas.py --docs-dir docs/
  uv run python3 scripts/doc_review_personas.py --docs-dir docs/ \\
      --personas cfo,editor --output-file review.md
  uv run python3 scripts/doc_review_personas.py --docs-dir docs/ --json
  uv run python3 scripts/doc_review_personas.py --docs-dir docs/ --personas editor --dry-run

See skills/doc-review-personas/SKILL.md for the invocation contract.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from lib.doc_review_personas import (  # noqa: E402
    render_json,
    render_markdown,
    run_review,
)
from lib.persona_library import get_persona, list_personas  # noqa: E402


def _parse_personas(raw: str | None) -> list:
    if not raw:
        from lib.persona_library import default_persona_set
        return default_persona_set()
    names = [n.strip() for n in raw.split(",") if n.strip()]
    resolved = []
    for name in names:
        try:
            resolved.append(get_persona(name))
        except KeyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(2)
    return resolved


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="doc-review-personas",
        description=(
            "Multi-persona adversarial review of a docs/ corpus. "
            "Each persona is a different reviewer lens (CFO, Tech Lead, etc.) "
            "and findings are consolidated with severity tiers."
        ),
    )
    ap.add_argument("--docs-dir", required=True,
                    help="Path to the documentation directory (walked recursively)")
    ap.add_argument("--personas", default=None,
                    help=f"Comma-separated persona names. Available: "
                         f"{','.join(list_personas())}. Default: all 5.")
    ap.add_argument("--model", default="haiku",
                    help="Model hint for dispatch (opus|sonnet|haiku). Default: haiku.")
    ap.add_argument("--max-parallel", type=int, default=None,
                    help="Hard cap on parallel persona calls. "
                         "Default: read from cognitive-os.yaml or 5.")
    ap.add_argument("--output-file", default=None,
                    help="Write report to this file instead of stdout.")
    ap.add_argument("--json", action="store_true",
                    help="Emit JSON instead of markdown.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Skip LLM calls; output a plan of which personas "
                         "would run. Useful for CI and testing.")
    args = ap.parse_args(argv)

    docs_dir = Path(args.docs_dir)
    personas = _parse_personas(args.personas)

    try:
        report = run_review(
            docs_dir=docs_dir,
            personas=personas,
            model=args.model,
            max_parallel=args.max_parallel,
            dry_run=args.dry_run,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except NotADirectoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    payload = render_json(report) if args.json else render_markdown(report)

    if args.output_file:
        Path(args.output_file).write_text(payload, encoding="utf-8")
        print(f"wrote {args.output_file}", file=sys.stderr)
    else:
        print(payload)

    # Exit code: non-zero if any S1 finding (useful for CI gating).
    counts = report.severity_counts()
    if counts.get("S1", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
