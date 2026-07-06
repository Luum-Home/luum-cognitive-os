#!/usr/bin/env python3
# SCOPE: os-only
"""Validate Open Knowledge Format (OKF) frontmatter on knowledge pages.

Deterministic, LLM-free gate for the ADR knowledge-base pilot (and its rollout
to other doc buckets): every OKF page (`docs/**/*.synthesis.md` by default) must
carry valid YAML frontmatter conforming to `scripts/okf-schema.json`.

OKF itself requires only a `type` field; the Cognitive OS `adr-synthesis`
profile additionally requires source/adr/status/reality_level/provenance. The
schema is a plain JSON Schema (draft-07), so external tools (`check-jsonschema`,
`ajv-cli`, GitHub Actions) can enforce the same contract as this script.

Usage::

    python3 scripts/validate_okf.py                 # validate docs/**/*.synthesis.md
    python3 scripts/validate_okf.py --path docs/04-Concepts
    python3 scripts/validate_okf.py --glob '**/*.okf.md'
    python3 scripts/validate_okf.py --json

Exit code 0 when every page validates, 1 when any page fails (so it works as a
pre-commit hook and a CI gate).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - dependency is present in this repo
    print("validate_okf: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

try:
    from jsonschema import Draft7Validator
except ImportError:  # pragma: no cover - dependency is present in this repo
    print("validate_okf: jsonschema is required (pip install jsonschema)", file=sys.stderr)
    sys.exit(2)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_SCHEMA = _REPO_ROOT / "scripts" / "okf-schema.json"


def extract_frontmatter(text: str) -> tuple[dict | None, str | None]:
    """Return (frontmatter_dict, error). Frontmatter is the YAML block delimited
    by the first two lines that are exactly ``---``."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "no YAML frontmatter (file must open with '---')"
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, "unterminated frontmatter (missing closing '---')"
    block = "\n".join(lines[1:end])
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        return None, f"invalid YAML frontmatter: {exc}"
    if not isinstance(data, dict):
        return None, "frontmatter is not a YAML mapping"
    return data, None


def validate_page(path: Path, validator: Draft7Validator) -> list[str]:
    """Return a list of human-readable errors for one page (empty == valid)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read file: {exc}"]
    fm, err = extract_frontmatter(text)
    if err:
        return [err]
    errors = sorted(validator.iter_errors(fm), key=lambda e: list(e.path))
    out = []
    for e in errors:
        loc = ".".join(str(p) for p in e.path) or "(root)"
        out.append(f"{loc}: {e.message}")
    return out


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate OKF frontmatter on knowledge pages against scripts/okf-schema.json.",
    )
    parser.add_argument("--path", default="docs", help="Root directory to scan (default: docs).")
    parser.add_argument(
        "--glob",
        default="**/*.synthesis.md",
        help="Glob (relative to --path) selecting OKF pages (default: **/*.synthesis.md).",
    )
    parser.add_argument("--schema", default=str(_DEFAULT_SCHEMA), help="Path to the OKF JSON Schema.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report instead of text.")
    parser.add_argument("paths", nargs="*", help="Explicit page paths (overrides --path/--glob).")
    args = parser.parse_args(argv)

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)

    if args.paths:
        pages = [Path(p) for p in args.paths]
    else:
        pages = sorted((_REPO_ROOT / args.path).glob(args.glob))

    results = {}
    for page in pages:
        rel = page.relative_to(_REPO_ROOT) if page.is_absolute() and str(page).startswith(str(_REPO_ROOT)) else page
        errs = validate_page(page, validator)
        if errs:
            results[str(rel)] = errs

    total = len(pages)
    failed = len(results)

    if args.json:
        print(json.dumps({"scanned": total, "failed": failed, "violations": results}, indent=2))
    else:
        if failed == 0:
            print(f"OKF validation: PASS — {total} page(s) valid.")
        else:
            print(f"OKF validation: FAIL — {failed}/{total} page(s) invalid:\n", file=sys.stderr)
            for f, errs in results.items():
                for e in errs:
                    print(f"  {f}: {e}", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
