#!/usr/bin/env python3
# SCOPE: os-only
"""Render docs/adoption-tiers.md from template + live data sources.

Data sources:
  - templates/security-profiles/{minimal,standard,paranoid}.json  (hook counts)
  - templates/adoption-tiers.md.j2                                 (narrative template)
  - git HEAD sha                                                    (generation notice)

Usage:
  python3 scripts/render_adoption_tiers.py                 # regenerate in-place
  python3 scripts/render_adoption_tiers.py --output /tmp/out.md
  python3 scripts/render_adoption_tiers.py --check         # exit 1 if doc is stale
  python3 scripts/render_adoption_tiers.py --json          # emit adoption matrix JSON
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "templates" / "adoption-tiers.md.j2"
PROFILES_DIR = ROOT / "templates" / "security-profiles"
DEFAULT_OUTPUT = ROOT / "docs" / "adoption-tiers.md"

# Profile slug -> JSON filename + tier key
PROFILE_MAP = {
    "lean": ("minimal.json", "minimal"),
    "standard": ("standard.json", "standard"),
    "strict": ("paranoid.json", "paranoid"),
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _load_profile(json_filename: str) -> dict:
    path = PROFILES_DIR / json_filename
    return json.loads(path.read_text(encoding="utf-8"))


def _git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def build_tier_data() -> dict:
    """Return a dict keyed by lean/standard/strict with profile metadata."""
    tiers: dict[str, dict] = {}
    for tier_key, (json_file, profile_slug) in PROFILE_MAP.items():
        profile = _load_profile(json_file)
        tiers[tier_key] = {
            "json_file": json_file,
            "profile_name": profile_slug,
            "hook_count": profile["_hook_count"],
            "description": profile.get("_description", ""),
        }
    return tiers


# ---------------------------------------------------------------------------
# Template rendering (stdlib string.Template — no Jinja2 dep)
#
# The .j2 template uses {{ var }} and {{ obj.attr }} syntax.  We do a two-pass
# approach:
#   1. Build a flat substitution map from the nested tier dict.
#   2. Replace {{ key }} tokens via a simple regex substitution.
# ---------------------------------------------------------------------------


def _flatten(prefix: str, value: object, out: dict) -> None:
    """Recursively flatten nested dicts into dotted keys."""
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(f"{prefix}.{k}" if prefix else k, v, out)
    else:
        out[prefix] = str(value)


def render_template(
    template_text: str,
    tiers: dict,
    generated_sha: str,
    generated_at: str,
) -> str:
    import re

    # Build flat context
    ctx: dict[str, str] = {}
    _flatten("tiers", tiers, ctx)
    ctx["generated_sha"] = generated_sha
    ctx["generated_at"] = generated_at

    def replace_token(m: re.Match) -> str:
        key = m.group(1).strip()
        if key in ctx:
            return ctx[key]
        # Return original if unknown — avoids silently dropping template vars
        return m.group(0)

    # Replace {{ key }} tokens (handles spaces around key name)
    result = re.sub(r"\{\{\s*([\w.]+)\s*\}\}", replace_token, template_text)
    return result


# ---------------------------------------------------------------------------
# JSON matrix output
# ---------------------------------------------------------------------------


def build_json_matrix(tiers: dict) -> dict:
    return {
        "schema_version": "1",
        "tiers": {
            tier_key: {
                "profile": meta["profile_name"],
                "profile_file": f"templates/security-profiles/{meta['json_file']}",
                "hook_count": meta["hook_count"],
            }
            for tier_key, meta in tiers.items()
        },
    }


# ---------------------------------------------------------------------------
# Diff helper
# ---------------------------------------------------------------------------


_GENERATION_NOTICE_PREFIX = "<!-- Generated from"


def _strip_generation_notice(text: str) -> str:
    """Remove the trailing generation notice comment and any blank lines before it."""
    lines = text.splitlines(keepends=True)
    # Walk backwards, dropping the notice line and surrounding blank lines/separators
    while lines and lines[-1].strip() in ("", "---"):
        lines.pop()
    if lines and lines[-1].strip().startswith(_GENERATION_NOTICE_PREFIX):
        lines.pop()
    # Trim trailing blank lines
    while lines and lines[-1].strip() == "":
        lines.pop()
    return "".join(lines)


def _diff_text(a: str, b: str) -> str:
    """Return a unified diff of a vs b (after stripping generation notices)."""
    import difflib

    a_clean = _strip_generation_notice(a)
    b_clean = _strip_generation_notice(b)

    lines_a = a_clean.splitlines(keepends=True)
    lines_b = b_clean.splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(
            lines_a,
            lines_b,
            fromfile="committed",
            tofile="regenerated",
        )
    )
    return "".join(diff)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render docs/adoption-tiers.md from template + data sources."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output path (default: docs/adoption-tiers.md)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compare regen output to existing file; exit non-zero if they differ.",
    )
    parser.add_argument(
        "--json",
        dest="emit_json",
        action="store_true",
        help="Emit machine-readable adoption matrix JSON to stdout instead of MD.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    tiers = build_tier_data()

    if args.emit_json:
        print(json.dumps(build_json_matrix(tiers), indent=2))
        return 0

    template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
    sha = _git_sha()
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    rendered = render_template(template_text, tiers, sha, now)

    if args.check:
        existing = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        diff = _diff_text(existing, rendered)
        if diff:
            print(
                f"ERROR: {args.output} is out of sync with rendered output.\n"
                "Run `python3 scripts/render_adoption_tiers.py` to regenerate.\n",
                file=sys.stderr,
            )
            print(diff, file=sys.stderr)
            return 1
        print(f"OK: {args.output} matches rendered output.")
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Written: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
