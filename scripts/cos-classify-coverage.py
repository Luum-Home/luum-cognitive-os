#!/usr/bin/env python3
"""cos-classify-coverage — Tier classifier for dormant/aspirational components.

Reads .cognitive-os/metrics/aspirational-audit.jsonl, applies path + content
heuristics to assign each DORMANT/ASPIRATIONAL component to a coverage tier,
and writes .cognitive-os/coverage-tiers.json.

Tiers (defined in ADR-041):
  A  Safety-critical: blockers, secret detection, killswitch, rate-limiters, etc.
  B  Infrastructure: monitors, daemons, schedulers, heartbeats, capture hooks.
  C  Advisory/feature-gated: mlflow, valkey, onboarding, feature-flag gated.
  D  Skills + rules metadata: SKILL.md files, rules/*.md, templates.

Usage:
  python3 scripts/cos-classify-coverage.py [--summary] [--project-dir PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path


# ── Tier heuristics (evaluated in order; first match wins) ────────────────────

# Tier A: safety-critical components — destructive blockers, secret/credential
# detection, killswitch, rate-limiters, policy enforcers, verify/refine loops.
_TIER_A_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    r"/blocker/",
    r"credential",
    r"secret",
    r"killswitch",
    r"destructive",
    r"disk[_-]?full",
    r"content[_-]?policy",
    r"rate[_-]?limit",
    r"auto[_-]?rollback",
    r"auto[_-]?refine",
    r"auto[_-]?verify",
    r"guardrail",
    r"license[_-]?guard",
    r"license[_-]?policy",
    r"concurrent[_-]?write",
    r"release[_-]?guard",
    r"global[_-]?verify",
    r"error[_-]?pipeline",
    r"error[_-]?learning",
]]

# Tier B: infrastructure — monitors, daemons, schedulers, heartbeats, reapers.
_TIER_B_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    r"monitor",
    r"scheduler",
    r"daemon",
    r"scanner",
    r"heartbeat",
    r"reaper",
    r"executor",
    r"registry",
    r"capture",
    r"session[_-]?init",
    r"session[_-]?end",
    r"session[_-]?hygiene",
    r"session[_-]?cleanup",
    r"session[_-]?resume",
    r"session[_-]?wrapup",
    r"metrics[_-]?rotation",
    r"usage[_-]?health",
    r"wiring[_-]?check",
    r"registration[_-]?check",
    r"dispatch[_-]?gate",
]]

# Tier D: skills + rules metadata — SKILL.md files, rule markdowns, templates.
_TIER_D_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    r"skills/[^/]+/SKILL\.md$",
    r"rules/[^/]+\.md$",
    r"templates/[^/]+",
]]

# Tier C: advisory / feature-gated (also the default for unclassified).
_TIER_C_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    r"mlflow",
    r"valkey",
    r"onboarding",
    r"advisory",
    r"audit[_-]?weekly",
    r"paperclip",
    r"parry",
    r"aguara",
    r"langfuse",
    r"singularity",
]]

# Content-based override marker (first 20 lines of the file)
_TIER_OVERRIDE_RE = re.compile(r"TIER_OVERRIDE:\s*([ABCD])", re.IGNORECASE)


def _read_tier_override(component_path: str, project_dir: Path) -> str | None:
    """Return explicit tier from TIER_OVERRIDE comment in file, or None."""
    full_path = project_dir / component_path
    if not full_path.is_file():
        return None
    try:
        lines = full_path.read_text(errors="replace").splitlines()[:20]
        for line in lines:
            m = _TIER_OVERRIDE_RE.search(line)
            if m:
                return m.group(1).upper()
    except OSError:
        pass
    return None


def classify_component(component: str, project_dir: Path) -> str:
    """Return tier letter (A/B/C/D) for the given component path.

    Evaluation order:
      1. TIER_OVERRIDE comment in file
      2. Tier A path heuristics
      3. Tier B path heuristics
      4. Tier D path heuristics (skills/rules metadata)
      5. Tier C path heuristics
      6. Default: Tier C
    """
    # 1. Explicit override
    override = _read_tier_override(component, project_dir)
    if override:
        return override

    # Tier D must be checked FIRST for SKILL.md / rules / templates — these are
    # metadata files and their path keywords (e.g. "auto-refine" in SKILL.md)
    # must not be promoted to Tier A by name matching.
    for pattern in _TIER_D_PATTERNS:
        if pattern.search(component):
            return "D"

    # 2-4. Path heuristics (A before B before C)
    for pattern in _TIER_A_PATTERNS:
        if pattern.search(component):
            return "A"

    for pattern in _TIER_B_PATTERNS:
        if pattern.search(component):
            return "B"

    for pattern in _TIER_C_PATTERNS:
        if pattern.search(component):
            return "C"

    # Default
    return "C"


def load_dormant_components(audit_file: Path) -> list[str]:
    """Return unique component paths classified as DORMANT or ASPIRATIONAL."""
    if not audit_file.exists():
        return []
    seen: set[str] = set()
    components: list[str] = []
    with audit_file.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = record.get("payload", {})
            classification = payload.get("classification", "")
            if classification in ("DORMANT", "ASPIRATIONAL"):
                comp = payload.get("component", "")
                if comp and comp not in seen:
                    seen.add(comp)
                    components.append(comp)
    return components


def classify_all(
    project_dir: Path,
    audit_file: Path | None = None,
) -> dict[str, str]:
    """Classify all dormant/aspirational components. Returns {component: tier}."""
    if audit_file is None:
        audit_file = project_dir / ".cognitive-os" / "metrics" / "aspirational-audit.jsonl"

    components = load_dormant_components(audit_file)
    return {comp: classify_component(comp, project_dir) for comp in components}


def write_tiers_json(tiers: dict[str, str], output_path: Path) -> None:
    """Write tiers mapping to JSON file (sorted by component path)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_tiers = dict(sorted(tiers.items()))
    output_path.write_text(json.dumps(sorted_tiers, indent=2) + "\n")


def print_summary(tiers: dict[str, str]) -> None:
    """Print tier count summary in the format: A:N B:N C:N D:N."""
    counts = Counter(tiers.values())
    parts = [f"{tier}:{counts.get(tier, 0)}" for tier in ("A", "B", "C", "D")]
    print("  ".join(parts))
    print(f"  Total: {sum(counts.values())}")

    # Breakdown per tier
    by_tier: dict[str, list[str]] = {"A": [], "B": [], "C": [], "D": []}
    for comp, tier in sorted(tiers.items()):
        by_tier.setdefault(tier, []).append(comp)

    for tier in ("A", "B", "C", "D"):
        items = by_tier.get(tier, [])
        if items:
            label = {
                "A": "Safety-critical",
                "B": "Infrastructure",
                "C": "Advisory/feature-gated",
                "D": "Skills+rules metadata",
            }[tier]
            print(f"\nTier {tier} — {label} ({len(items)}):")
            for c in items[:20]:
                print(f"  {c}")
            if len(items) > 20:
                print(f"  ... and {len(items) - 20} more")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify dormant/aspirational components into coverage tiers (A/B/C/D)."
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print tier count summary after classification.",
    )
    parser.add_argument(
        "--project-dir",
        default=None,
        help="Project root directory (default: git root or current directory).",
    )
    parser.add_argument(
        "--audit-file",
        default=None,
        help="Path to aspirational-audit.jsonl (default: <project-dir>/.cognitive-os/metrics/aspirational-audit.jsonl).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: <project-dir>/.cognitive-os/coverage-tiers.json).",
    )
    args = parser.parse_args()

    # Resolve project directory
    if args.project_dir:
        project_dir = Path(args.project_dir).resolve()
    else:
        # Try to find git root
        cwd = Path.cwd()
        candidate = cwd
        while candidate != candidate.parent:
            if (candidate / ".git").exists():
                project_dir = candidate
                break
            candidate = candidate.parent
        else:
            project_dir = cwd

    audit_file = Path(args.audit_file).resolve() if args.audit_file else None
    output_path = (
        Path(args.output).resolve()
        if args.output
        else project_dir / ".cognitive-os" / "coverage-tiers.json"
    )

    tiers = classify_all(project_dir, audit_file)

    if not tiers:
        print("No dormant/aspirational components found.", file=sys.stderr)
        sys.exit(1)

    write_tiers_json(tiers, output_path)
    print(f"Wrote {len(tiers)} component tiers to {output_path}")

    if args.summary:
        print_summary(tiers)


if __name__ == "__main__":
    main()
