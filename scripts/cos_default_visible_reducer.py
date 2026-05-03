#!/usr/bin/env python3
# SCOPE: both
"""Recommend demotions to shrink default-visible primitive surface."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"
CORE_KEEP = {
    "hooks/secret-detector.sh",
    "hooks/destructive-git-blocker.sh",
    "hooks/destructive-rm-blocker.sh",
    "hooks/direct-main-guard.sh",
    "hooks/concurrent-write-guard.sh",
    "hooks/agent-prelaunch.sh",
    "hooks/edit-lock-pre-tool.sh",
    "hooks/symlink-mutation-guard.sh",
    "hooks/scope-marker-portability-gate.sh",
    "hooks/confidentiality-enforcer.sh",
    "hooks/content-policy.sh",
}


def load(path: Path = MANIFEST) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [p for p in data.get("primitives", []) if isinstance(p, dict)]


def build_recommendations(manifest: Path = MANIFEST) -> dict[str, Any]:
    primitives = load(manifest)
    recommendations: list[dict[str, Any]] = []
    for p in primitives:
        pid = str(p.get("id"))
        dist = p.get("distribution")
        maturity = p.get("maturity")
        if dist == "core" and pid not in CORE_KEEP and maturity != "blocking":
            recommendations.append({"primitive_id": pid, "from": "core", "to": "lab", "reason": "non-blocking primitive is not part of core killer set"})
        elif dist == "team" and maturity != "blocking":
            recommendations.append({"primitive_id": pid, "from": "team", "to": "lab", "reason": "advisory team primitive should be opt-in until usage proves value"})
    return {
        "status": "warn" if recommendations else "pass",
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args(argv)
    report = build_recommendations(args.manifest)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
