---
type: adr-synthesis
source: docs/02-Decisions/adrs/ADR-028a.md
adr: ADR-028a
status: accepted (Addendum to ADR-028)
reality_level: PARTIAL
provenance: ADR-028 was authored (2026-04-17) without consulting `.cognitive-os/plans/features/self-optimizing-pipeline.md` or `.cognitive-os/work-queue.json`; the reconciliation analysis (Engram #11552) found ADR-028's D4 fix (`test_run_inside_hook`, removing pytest from `session-init.sh:120-128` to stop 190 orphaned session-init + 187 orphaned pytest processes — "Bug 1") would silently disable WS11's anti-confirmation-bias baseline diff with no replacement, and D1.C's new agent heartbeat partially overlapped WS13's already-committed state-snapshot heartbeat (commit `65e4d0c`) without defined consumer boundaries.
---

## Decision
Four reconciliations to ADR-028 before its execution phases launch: (1) WS11 replacement — `hooks/global-verify.sh` (ADR-027 Phase 1) becomes the anti-confirmation-bias enforcer via before/after test-diff comparison, structurally preventing "tests pass" claims from attributing new failures to "pre-existing" without proof; (2) D1.C vs WS13 heartbeats — decision is KEEP BOTH: WS13's session-level `state-snapshot.json` (crash recovery, consumed by `crash-recovery.sh`) and D1.C's per-agent `.heartbeat` files (liveness monitoring, consumed by `agent-watchdog.sh`) serve different failure modes and must not read each other's files; (3) formalizes ADR-028 D1.A's 1 MiB (not 2 MiB) JSONL rotation threshold as authoritative, superseding ADR-027 D3, with a grep-based verification gate; (4) sequences two work-queue items (`smoke-test-e2e` depends on ADR-028 D6 chaos harness; `test-quality-audit` depends on ADR-028 D2 contract layer) without directly editing `work-queue.json`. A later census (§5) added D1.A.0 as a blocking prerequisite: 7 JSONL files referenced by 20+ hooks/libs were missing from disk entirely (error-learning.jsonl, repair-outcomes.jsonl, etc. — likely due to `COGNITIVE_OS_SESSION_ID` propagation failure) and 5 files had readers but no writers, permanently zeroing KPIs (trust-scores.jsonl, escalation-events.jsonl, etc.).

## Why
Disabling WS11 without a replacement would re-open a real, previously-observed quality gap: the orchestrator had attributed test failures to "pre-existing" three times in one session (12 failures that were actually caused by its own changes) — the same minimum-output bias also seen in sub-agents. Separately, the census found ADR-028's own stated motivation was partly wrong: the claimed "~40% unparseable" rows in hook-health.jsonl was false (7,692 rows, 0 bad JSON, uniform schema), while `cost-events.jsonl` did have real schema drift (62%/38% split across two incompatible shapes) — becoming the corrected, concrete migration target for `lib/metric_event.py`.

## Consequences
Preserves the anti-confirmation-bias guarantee without orphaned background processes (no bg subprocess, same behavioral guarantee via `global-verify.sh`). Prevents WS13/D1.C heartbeat conflation into a single mechanism that would lose either crash-recovery richness or per-agent liveness detection. Blocks premature D1.A.1 (MetricEvent schema) work until the more fundamental missing-file and zeroed-KPI problems are fixed, since "the new MetricEvent schema will also never land on disk" otherwise.

## Status & current state
Accepted, implemented (partially, per Resolution Log 2026-04-21): 6 of 9 action items RESOLVED (session-init.sh comment updated, ADR-028 open question #9 added, D1.C scope note added, auto-checkpoint.sh docstring added, §3 rotation verification passed with zero executable-code matches for the old 2 MiB threshold), 2 DEFERRED (work-queue.json edits — coordination lock, owned by a different agent this sprint), 1 PARTIALLY RESOLVED (D1.A.0: F-7 archive path was already aligned; F-6 test-e2e cleanup still needs `hooks/rotate-metrics.sh`, which doesn't exist yet; F-4 six of seven missing files remain absent; F-5 four of five reader-without-writer files remain unresolved — full fix deferred as a Phase-A-gated, opus-class work item). ADR-028 Phase A and Phase D both still NOT LAUNCHED as of the resolution log.

## Key links
Amends ADR-028 D1.A, D1.C, D4. Sibling: ADR-027a (slimming reconciliation addendum). References `self-optimizing-pipeline.md` §WS11/§WS13, `docs/06-Daily/reports/metrics-census.md` (447 files, 45 logical identities), Engram topic `gaps/adr-027-028-reconciliation-analysis`. Key files: `hooks/session-init.sh`, `hooks/auto-checkpoint.sh`, `hooks/global-verify.sh`, `lib/state_heartbeat.py`, `.cognitive-os/work-queue.json`.
