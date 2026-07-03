---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-027a.md
adr: ADR-027a
status: accepted
reality_level: REAL
provenance: ADR-027 was written on 2026-04-17 without checking whether prior token-optimization work had already landed on main — commit 1ee19a4 ("Phase 2 EXCLUDED_RULES") had already added an EXCLUDED_RULES array to hooks/self-install.sh that excludes 100 of 101 rules from sub-agent context injection, making ADR-027's baseline measurement of 24,124 bytes / ~6,031 tokens for CLAUDE.md stale (actual was already ~11,125 bytes / ~1,904 tokens).
---

## Decision
Correct ADR-027's baseline and scope in place rather than re-doing already-completed work. Remove from D2: the `scripts/compact-claude-md.py` migration script (redundant — EXCLUDED_RULES already achieves the intended reduction) and the "CLAUDE.md ≤ 400 tokens" KPI (mathematically infeasible without deleting session-mandatory inline prose that can't be externalized to rule files). Keep from D2: `lib/ref_key_loader.py` (on-demand rule loading by ref-key) as complementary to EXCLUDED_RULES's wholesale exclusion. New D2 target: ≤1,200 tokens (down from ~1,904) via deduplicating redundant SDD/engram prose sub-bullets that restate content already in dedicated rule files. Add a mandatory Phase 1 prerequisite: `ws9-test-errors` (292 pytest collection errors in the queue) must be resolved to 0 before Phase 1 executes, since a broken resolver would cause the "fallback to full suite" to fire on every invocation, defeating Phase 1's purpose. Reconcile the D3 "≤18 registered hook entries" KPI against `hook-architecture-v2.md`'s per-profile counts (17/34/88) by scoping D3's ≤18 to the Agent-matcher subset only (7 → ≤2 after merging 4 PreToolUse+3 PostToolUse Agent entries into 1 each), leaving the total-entries-per-profile metric to hook-architecture-v2. Formalize that ADR-028 D1.A's >1 MiB JSONL rotation threshold takes precedence over ADR-027 D3's stale >2 MiB figure.

## Why
Every correction in this addendum traces back to the same root cause: ADR-027 was authored against a mental model of the codebase rather than a discovery pass over actual files and the existing work-queue/plan documents. Reconciliation against 20 pre-existing plan docs and the 14-item work-queue surfaced the stale baseline, the redundant script, the infeasible KPI, the undocumented Phase-1 dependency, and the two hook-count metrics that looked contradictory but actually measured different subsets.

## Consequences
The corrections prevent duplicate/wasted implementation work (compact-claude-md.py would have collided with or regressed self-install.sh's existing caching logic) and prevent chasing an infeasible KPI. Resolving the hook-count "contradiction" required no code change, only clarifying that D3 and hook-architecture-v2 measure orthogonal subsets (Agent-matcher vs total-profile). The rotation-threshold precedence rule prevents future amendments from re-litigating which ADR owns that value.

## Status & current state
Accepted and implemented — a full Resolution Log dated 2026-04-21 documents all four pending action items executed against ADR-027 itself: the D3 KPI row rewritten to the Agent-matcher-subset framing; the compact-claude-md.py D2 bullet struck through with rationale citing commit 1ee19a4; the D2 KPI target changed from ≤400 to ≤1,200 tokens with corrected baseline; and a new "Prerequisite" sub-section added to ADR-027 Phase 1 documenting the ws9-test-errors gating command. `.cognitive-os/work-queue.json` needed no edit (ws9 already resolved per queue.json:122). Smoke test: `test_cos_config_audit.py` unaffected since no config schema was touched.

## Key links
- ADR-027 (parent) — baseline, D2 task list, D3 KPI row, and Phase 1 risks all amended by this addendum
- ADR-028 D1.A — authoritative source for JSONL rotation thresholds (supersedes ADR-027 D3 on this point)
- `.cognitive-os/plans/features/hook-architecture-v2.md` — canonical per-profile hook counts
- Engram observation #11552 (`gaps/adr-027-028-reconciliation-analysis`, `gaps/adr-027-stale-baseline`)
- Commit `1ee19a4` — landed the EXCLUDED_RULES mechanism that made the original baseline stale
