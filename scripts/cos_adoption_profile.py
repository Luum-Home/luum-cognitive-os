#!/usr/bin/env python3
# SCOPE: both
"""Report adoptable Cognitive OS profiles from primitive lifecycle metadata."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"
PROFILE_TIERS = {
    "core": {"core"},
    "team": {"core", "team"},
    "maintainer": {"core", "team", "maintainer"},
    "lab": {"core", "team", "maintainer", "lab"},
}
INACTIVE = {"candidate", "demoted", "archived", "deleted"}
SLO = {
    "core": {"max_default_visible": 10, "max_blocking": 8},
    "team": {"max_default_visible": 20, "max_blocking": 15},
    "maintainer": {"max_default_visible": 35, "max_blocking": 35},
    "lab": {"max_default_visible": 999, "max_blocking": 999},
}


def load_primitives(path: Path = MANIFEST) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    primitives = data.get("primitives", []) if isinstance(data, dict) else []
    return [p for p in primitives if isinstance(p, dict)]


def build_profile(profile: str, manifest: Path = MANIFEST) -> dict[str, Any]:
    if profile not in PROFILE_TIERS:
        raise ValueError(f"unknown profile {profile!r}")
    tiers = PROFILE_TIERS[profile]
    primitives = load_primitives(manifest)
    selected = [
        p for p in primitives
        if p.get("distribution") in tiers and p.get("lifecycle_state") not in INACTIVE
    ]
    hooks = [p for p in selected if p.get("kind") == "hook"]
    blocking = [p for p in selected if p.get("maturity") == "blocking"]
    advisory = [p for p in selected if p.get("maturity") == "advisory"]
    observe = [p for p in selected if p.get("maturity") == "observe"]
    default_visible = [p for p in selected if p.get("distribution") in {"core", "team"}]
    slo = SLO[profile]
    findings: list[dict[str, Any]] = []
    if len(default_visible) > slo["max_default_visible"]:
        findings.append({"id": "default-visible-over-budget", "severity": "warn", "count": len(default_visible), "budget": slo["max_default_visible"]})
    if len(blocking) > slo["max_blocking"]:
        findings.append({"id": "blocking-over-budget", "severity": "warn", "count": len(blocking), "budget": slo["max_blocking"]})
    return {
        "profile": profile,
        "status": "warn" if findings else "pass",
        "tiers": sorted(tiers),
        "primitive_count": len(selected),
        "hook_count": len(hooks),
        "default_visible_count": len(default_visible),
        "blocking_count": len(blocking),
        "advisory_count": len(advisory),
        "observe_count": len(observe),
        "slo": slo,
        "findings": findings,
        "primitives": [str(p.get("id")) for p in selected],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(PROFILE_TIERS), default="core")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--strict", action="store_true", help="return non-zero when profile SLO warnings exist")
    args = parser.parse_args(argv)
    report = build_profile(args.profile, args.manifest)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and report["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
