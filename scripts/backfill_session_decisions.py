#!/usr/bin/env python3
# SCOPE: os-only
# @manual-trigger: one-shot backfill; run once to persist already-answered ADR-069 decisions into engram
"""backfill_session_decisions.py — One-shot script to persist already-answered decisions.

These decisions exist in research reports and have recommended answers inline,
but were never persisted as engram observations (the ADR-069 §5b OR-ambiguity bug).
Running this script marks them ANSWERED in engram so /decision-triage stops surfacing
them as false-critical decisions.

Usage:
    python3 scripts/backfill_session_decisions.py [--dry-run]

ADR-069 §5b fix: This backfill captures the decisions that were accepted during the
2026-04-24/25 sessions when the OR ambiguity meant nobody called record_decision().
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from lib.decision_tracker import record_decision  # noqa: E402


# Decisions that have been answered (decision_text extracted from research report recommendations).
# Format: (topic_key, decision_text, recommendation)
ANSWERED_DECISIONS: list[tuple[str, str, str]] = [
    # --- adr-067-phase-2-2026-04-24.md ---
    (
        "hook-validation-failure-mode-warn",
        "WARN (exit 0) advisory mode — mirrors ADR-067 Phase 1 default",
        "exit 0 advisory (mirrors ADR-067 Phase 1 default)",
    ),
    (
        "adr-alternatives-rejected-backfill-policy",
        "Grandfather all existing ADRs; require for new ADRs only",
        "Grandfather all existing; require for new",
    ),
    (
        "hook-purpose-event-backfill-grandfather",
        "Require PURPOSE/EVENT for all new hooks; grandfather existing 154",
        "Require for all 154 immediately / require for new only (operator chose: require for new)",
    ),
    (
        "template-location-flat-in-templates",
        "Flat in templates/ directory",
        "templates/rule-template.md, templates/hook-template.sh",
    ),
    (
        "audit-test-placement-new-files",
        "New files: test_rule_contracts.py, test_hook_contracts.py",
        "New test_rule_contracts.py, test_hook_contracts.py",
    ),
    (
        "ci-vs-local-only-audit",
        "Yes — pytest tests/audit/ is already in the test suite",
        "Yes — already in CI",
    ),
    (
        "add-rule-and-add-hook",
        "Yes — auto-consume template same as /skill-creator",
        "Yes (same as /skill-creator)",
    ),
    (
        "rules-contextual-trigger-enforcement-always",
        "Required for all rules — enforce via audit test",
        "Required for all rules / required for new only",
    ),
    (
        "adr-verification-minimum-content-free",
        ">=1 bash/command block required in Verification section",
        ">=1 bash/command block",
    ),
    # --- cos-init-migration-2026-04-24.md ---
    (
        "yaml-lib-pyyaml-3rd-party",
        "pyyaml (3rd party, popular) — already a dependency",
        "pyyaml: already a dependency, minimal friction",
    ),
    (
        "generate-project-settings-sh-and",
        "Co-migrate in same PR as cos_init.py",
        "Co-migrate — keep changes atomic",
    ),
    (
        "settings-driver-sh-cos_detect_harness-inline",
        "Inline the 10-line logic into Python",
        "Inline — removes shell dependency",
    ),
    (
        "backward-compat-shim-keep-cos",
        "Keep cos-init.sh as thin exec shim for backward compat",
        "Keep shim — backward compat",
    ),
    (
        "subprocess-wrapper-subprocess-run-stdlib",
        "subprocess.run (stdlib) — no extra dependencies",
        "subprocess.run: no extra dependencies",
    ),
    (
        "tomllib-vs-regex-for-pyproject",
        "stdlib tomllib (Python 3.11+) — already available",
        "tomllib: stdlib, already available",
    ),
    (
        "test-strategy-behavior-tests-via",
        "Behavior tests via subprocess (run Python against tmpdir)",
        "Behavior tests via subprocess",
    ),
    (
        "migration-ordering-big-bang-full",
        "Strangler-fig (function-by-function, shim delegates)",
        "Strangler-fig: lower risk, incremental",
    ),
    (
        "bash-3-x-compat-constraint",
        "Keep Bash 3.x compat for all bash scripts",
        "Keep constraint — macOS ships bash 3.2",
    ),
    # --- python-major-bumps-2026-04-24.md ---
    (
        "wrapt-1-17-2-1",
        "Pin at 1.x / Wait — not explicitly pinned, risk unknown",
        "Pin at 1.x / Wait",
    ),
    (
        "rich-14-15-yes-1",
        "Upgrade to rich 15 — safe (1 file, stable APIs only)",
        "Upgrade — safe",
    ),
    (
        "cryptography-46-47-no-main",
        "Hold — deprecated pattern in hermes-agent plugin needs fix first",
        "Hold until default_backend() usage removed",
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill already-answered decisions to engram (ADR-069 §5b fix)."
    )
    parser.add_argument("--dry-run", action="store_true", help="Print what would be saved without saving")
    args = parser.parse_args()

    print(f"Backfilling {len(ANSWERED_DECISIONS)} decisions to engram...")
    ok = 0
    fail = 0

    for topic_key, decision_text, recommendation in ANSWERED_DECISIONS:
        if args.dry_run:
            print(f"  [DRY-RUN] decision/{topic_key}: {decision_text[:60]}")
            ok += 1
            continue

        success = record_decision(
            topic_key=topic_key,
            decision_text=decision_text,
            recommendation=recommendation,
        )
        if success:
            print(f"  OK: decision/{topic_key}")
            ok += 1
        else:
            print(f"  FAIL: decision/{topic_key}", file=sys.stderr)
            fail += 1

    print(f"\nDone: {ok} saved, {fail} failed.")
    if fail > 0:
        print("Check engram connectivity — failed saves mean /decision-triage will still show these.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
