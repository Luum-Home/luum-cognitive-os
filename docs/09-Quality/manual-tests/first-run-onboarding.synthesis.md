---
type: quality-synthesis
source: docs/09-Quality/manual-tests/first-run-onboarding.md
provenance: "Executable proof that a new project reaches a working Cognitive OS baseline with one installer command, visible harness selection, and explicit performance budgets."
---

## What it is
An executable proof that first-run onboarding "feels like product, not an internal script pile": a fresh project installs from local Cognitive OS source in one command, the selected harness driver is visible in output, core `.cognitive-os` artifacts exist afterward, and both install and status flows stay inside explicit time budgets.

## Key mechanics
- Run: `bash scripts/demo-first-run-onboarding.sh` (default harness), `--harness=claude` (Claude projection path), or `--keep` (retain temp project for inspection).
- **Default budgets**: install 30000ms, status 5000ms, total 40000ms — overridable via `COS_ONBOARDING_INSTALL_BUDGET_MS`, `COS_ONBOARDING_STATUS_BUDGET_MS`, `COS_ONBOARDING_TOTAL_BUDGET_MS`.
- **Automated regression**: `python3 -m pytest tests/integration/test_first_run_onboarding.py -q` — runs the Codex path specifically because Codex is called out as "the current self-hosting pressure point for this branch"; the manual proof additionally covers Claude so onboarding stays driver-aware rather than silently Codex-only.
- **Acceptance criteria**: installer exits 0 and prints success/active harness/settings driver/next checks; `.cognitive-os/hooks/cos`, `.cognitive-os/skills/cos`, `.cognitive-os/templates/cos` exist; Codex install creates `.codex/hooks.json` with `CODEX_PROJECT_DIR`; Claude install creates `.claude/settings.json` with `CLAUDE_PROJECT_DIR`; `cos-status --json` exits 0 and reports health/canonical skills/wired hooks; all three timing budgets are respected.

## Relations & where used
Narrower, performance-budgeted sibling of `five-minute-demo.md` (which runs the same install → verify → status → product-contract-tests flow without hard time budgets). Complements `consumer-project-primitive-accessibility.md`'s temp-project projection checks.

## Status / caveats
Explicitly notes a scoping decision: the proof uses `--skip-manifest-check` to measure the core first-run path without host-dependent dependency-reporting noise; the manifest check itself is called out as "important" but intentionally excluded from this timing measurement, and should be measured separately if it becomes part of the promised quick-start path. This is a deliberate, stated limitation, not an inconsistency.
