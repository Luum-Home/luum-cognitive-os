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
import session_start_budget
from generate_runtime_compact_config import build_compact_config
TOKEN_DIVISOR = 4
BUDGETS = {"core": 3200, "team": 6000, "maintainer": 10000, "lab": 20000}
PROFILE_RULE_FILES = {
    "core": ["AGENTS.md", "docs/04-Concepts/architecture/core-adoption-preamble.md"],
    "team": ["AGENTS.md", "rules/RULES-COMPACT.md"],
    "maintainer": ["AGENTS.md", "rules/RULES-COMPACT.md", ".cognitive-os/generated/runtime-config.compact.yaml"],
    "lab": ["AGENTS.md", "rules/RULES-COMPACT.md", ".cognitive-os/generated/runtime-config.compact.yaml"],
}


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // TOKEN_DIVISOR)


def file_tokens(path: Path) -> int:
    try:
        return estimate_tokens(path.read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        return 0


def _compact_config_tokens(root: Path) -> int:
    generated = root / ".cognitive-os" / "generated" / "runtime-config.compact.yaml"
    if generated.exists():
        return file_tokens(generated)
    source = root / "cognitive-os.yaml"
    if not source.exists():
        return 0
    try:
        import yaml

        return estimate_tokens(yaml.safe_dump(build_compact_config(source), sort_keys=False, allow_unicode=True))
    except Exception:
        return 0


def _session_start_primitive_tokens(profile: str, root: Path) -> tuple[int, dict[str, Any]]:
    """Estimate visible startup primitive tax from actual projected hooks.

    The previous estimator charged every active primitive in the lifecycle
    manifest. That over-counted by treating registry inventory as prompt text.
    Preamble tax should track what the agent actually sees at startup: projected
    SessionStart hook summaries plus a small surcharge for synchronous blockers.
    """
    try:
        report = session_start_budget.build_report("current" if profile == "current" else profile, root)
    except Exception:
        adoption = cos_adoption_profile.build_profile(profile)
        fallback = adoption["default_visible_count"] * 35 + adoption["blocking_count"] * 45
        return fallback, {"basis": "lifecycle-fallback", "default_visible_count": adoption["default_visible_count"], "blocking_count": adoption["blocking_count"]}

    hooks = report.get("hooks", [])
    hook_count = len(hooks)
    sync_count = sum(1 for item in hooks if not item.get("async_projected"))
    candidate_count = len(report.get("candidates_to_move", []))
    tokens = hook_count * 24 + sync_count * 16 + candidate_count * 8
    return tokens, {
        "basis": "session-start-projection",
        "hook_count": hook_count,
        "sync_hook_count": sync_count,
        "candidate_to_move_count": candidate_count,
    }


def build_budget(profile: str, root: Path = REPO_ROOT) -> dict[str, Any]:
    files = PROFILE_RULE_FILES[profile]
    file_breakdown: dict[str, int] = {}
    for rel in files:
        if rel == ".cognitive-os/generated/runtime-config.compact.yaml":
            file_breakdown[rel] = _compact_config_tokens(root)
        else:
            file_breakdown[rel] = file_tokens(root / rel)
    primitive_tokens, primitive_basis = _session_start_primitive_tokens(profile, root)
    estimated = sum(file_breakdown.values()) + primitive_tokens
    budget = BUDGETS[profile]
    return {
        "profile": profile,
        "status": "pass" if estimated <= budget else "warn",
        "estimated_tokens": estimated,
        "budget_tokens": budget,
        "file_tokens": file_breakdown,
        "primitive_token_estimate": primitive_tokens,
        "primitive_token_basis": primitive_basis,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(BUDGETS), default="core")
    parser.add_argument("--strict", action="store_true", help="return non-zero when the preamble budget is exceeded")
    args = parser.parse_args(argv)
    report = build_budget(args.profile)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and report["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
