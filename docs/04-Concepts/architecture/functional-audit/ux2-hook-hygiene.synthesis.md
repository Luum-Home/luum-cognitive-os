---
type: concept-synthesis
source: docs/04-Concepts/architecture/functional-audit/ux2-hook-hygiene.md
provenance: "Coordinator pass resolving the code-dead hook references, the confidentiality-enforcer.sh profile regression, and the non-actionable rate-limiter.sh output flagged by scorecard-hooks.md."
---

## What it is

Executed fix sprint (D1-D5) resolving 3 code-dead hooks, a `confidentiality-enforcer.sh` full-tier profile inversion, a missing session-start sanity check, and non-actionable `rate-limiter.sh` error output.

## Key mechanics

- D1 — created `hooks/auto-verify.sh` (PostToolUse Agent: parses an `ACCEPTANCE CRITERIA:` block, runs verification commands matching patterns like `` `cmd` = N ``/`` `cmd` >= N ``/`` `cmd` exits 0 ``, logs PASS/FAIL/NO_CRITERIA to `.cognitive-os/metrics/auto-verify.jsonl`); `hooks/auto-refine.sh` (PostToolUse Agent: detects TEST_FAILURE/BUILD_ERROR/LINT_ERROR/AGENT_ERROR, tracks retry count per task fingerprint with a 3-attempt max, escalates on the 3rd failure, phase-aware: retry instructions in reconstruction/stabilization, suggestion-only in production/maintenance); `hooks/dod-gate.sh` (PostToolUse Agent, advisory-only: reads complexity, checks `rules/definition-of-done.md` criteria, phase-aware WARN/BLOCK label, never exits non-zero). All three are non-blocking siblings of the integrated `completion-gate.sh` pipeline; double-firing is acceptable since each is advisory.
- D2 — fixed the `confidentiality-enforcer.sh` regression: removed the `full`-tier early-exit no-op in `scripts/apply-efficiency-profile.sh`; `full` now regenerates as a true superset of `standard` plus the only-in-full hooks, restoring `lean ⊂ standard ⊂ full` coverage.
- D3 — created `hooks/session-sanity.sh` (SessionStart, always exits 0): checks skill-catalog size (warns below 20) and settings-vs-disk consistency (flags `.claude/settings.json` references to missing hook files), both pointing to `bash hooks/self-install.sh` as the fix.
- D4 — made `hooks/rate-limiter.sh` error output actionable while preserving the machine-parseable contract (`RATE_LIMIT_QUEUED:`, `Queue ID:`, `BLOCKED:`, `Suggestion:`, `ORCHESTRATOR ACTION:`) by inserting a human-readable UX block between the machine header and the suggestions section.
- D5 — regenerated `.claude/settings.json` via `apply-efficiency-profile.sh standard`; total hook commands dropped 56 -> 54 (expected: only-in-full hooks like `aguara-scan`, `kpi-trigger`, `mcp-scan` were dropped at `standard`, while the 5 new/fixed hooks from D1-D3 were added).

## Relations & where used

Directly resolves findings from `scorecard-hooks.md` (code-dead hooks, `confidentiality-enforcer` anomaly, rate-limiter UX). Modifies `scripts/apply-efficiency-profile.sh` and regenerates `.claude/settings.json`.

## Status / caveats

All D1-D5 acceptance criteria are listed as passing with explicit verification commands (`bash -n`, grep counts, JSON validity). To restore the "only-in-full" hook set, run `bash scripts/apply-efficiency-profile.sh full`.
