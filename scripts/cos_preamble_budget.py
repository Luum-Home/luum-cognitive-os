#!/usr/bin/env python3
# SCOPE: both
"""Estimate prompt/preamble budget for an adoption profile."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import cos_adoption_profile
TOKEN_DIVISOR = 4
BUDGETS = {"core": 3200, "team": 5000, "maintainer": 8000, "lab": 20000}
PROFILE_RULE_FILES = {
    "core": ["AGENTS.md", "docs/04-Concepts/architecture/core-adoption-preamble.md"],
    "team": ["AGENTS.md", "rules/RULES-COMPACT.md"],
    "maintainer": ["AGENTS.md", "rules/RULES-COMPACT.md", "cognitive-os.yaml"],
    "lab": ["AGENTS.md", "rules/RULES-COMPACT.md", "cognitive-os.yaml"],
}


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // TOKEN_DIVISOR)


def file_tokens(path: Path) -> int:
    try:
        return estimate_tokens(path.read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        return 0


def build_budget(profile: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    adoption = cos_adoption_profile.build_profile(profile)
    files = PROFILE_RULE_FILES[profile]
    file_breakdown = {rel: file_tokens(root / rel) for rel in files}
    primitive_tokens = adoption["default_visible_count"] * 35 + adoption["blocking_count"] * 45
    estimated = sum(file_breakdown.values()) + primitive_tokens
    budget = BUDGETS[profile]
    return {
        "profile": profile,
        "status": "pass" if estimated <= budget else "warn",
        "estimated_tokens": estimated,
        "budget_tokens": budget,
        "file_tokens": file_breakdown,
        "primitive_token_estimate": primitive_tokens,
        "default_visible_count": adoption["default_visible_count"],
        "blocking_count": adoption["blocking_count"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(BUDGETS), default="core")
    args = parser.parse_args(argv)
    report = build_budget(args.profile)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
