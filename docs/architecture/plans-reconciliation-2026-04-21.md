# Plans/Features Reconciliation — 2026-04-21

## Summary

- **Total plans**: 20 (17 `.md` + 3 `.json` hook-profile settings)
- **SUPERSEDED**: 11 (10 `.md` + 3 `.json` supersede bundles)
- **LIVE**: 4 `.md` (residual scope remains beyond existing ADRs)
- **STALE**: 3 `.md` (historical snapshots or one-shot audit output, no active work stream)

Settings JSONs (`hook-architecture-v2-settings*.json`) are consumed by `scripts/set-security-profile.sh` and regenerated in-place; they are SUPERSEDED-as-source-plan but still LIVE-as-runtime-artifact. Keep in place.

## Reconciliation matrix

| Plan | Status | Superseded by / Related ADR | Reconciliation reason |
|------|--------|-----------------------------|----------------------|
| `agent-escalation-capabilities.md` | LIVE | ADR-036, ADR-038 | Preamble-level escalation shipped; capability-aware horizontal escalation (model-tier upgrade + structured handoff) still open. |
| `component-scope-classification.md` | SUPERSEDED | ADR-031, ws6 (3f6a5c1, 5acb797), install scope-filter (1f5911c) | 506+ components tagged, filter wired. |
| `dead-weight-audit.md` | SUPERSEDED | ADR-041, ADR-031 | One-shot audit replaced by continuous classifier. |
| `docker-to-pip-migration.md` | SUPERSEDED | ADR-042, ADR-002 | Valkey extracted; Paperclip + Langfuse-PG are on-demand-only. |
| `docs-hook-rule-candidates.md` | STALE | — | 2026-04-11 one-shot audit; no downstream adoption. |
| `docs-rescan-results.md` | STALE | ws5 partial (a8c6c58) | Snapshot output; residual tracked elsewhere. |
| `docs-to-skills-audit.md` | LIVE | ws5 partial | 9 SKILL-CANDIDATE conversions from original 17 still parked. |
| `hook-architecture-v2.md` | SUPERSEDED | apply-efficiency-profile.sh + set-security-profile.sh (ws7, 329deb2), ADR-028a, ADR-029 | 3-profile model shipped; settings JSONs regenerated 2026-04-20. |
| `hook-architecture-v2-settings-minimal.json` | SUPERSEDED (as plan) / LIVE (as artifact) | set-security-profile.sh | Consumed at runtime; do not delete. |
| `hook-architecture-v2-settings.json` | SUPERSEDED (as plan) / LIVE (as artifact) | set-security-profile.sh | Consumed at runtime; do not delete. |
| `hook-architecture-v2-settings-paranoid.json` | SUPERSEDED (as plan) / LIVE (as artifact) | set-security-profile.sh | Consumed at runtime; do not delete. |
| `intelligent-context-compaction.md` | SUPERSEDED | ADR-044, ADR-027, ws2 (9bd895b), ws3 (15d67eb) | Three pillars (truncation, cache, payload) all have shipped components + ADR. |
| `project-audit-package.md` | SUPERSEDED | packages/project-audit/, hooks registered (92cf485), cos-config-audit (f3d4cf7) | Package built; hooks registered per ROADMAP §1.1. |
| `rules-to-hooks-refactor.md` | LIVE | ws1 (8dc4a6e, 1ee19a4, 7b13d25), ADR-029, rules/ROADMAP.md | Tactical rule→hook migrations done individually; meta-framework for tiered migration policy still not formalized in an ADR. |
| `self-optimizing-pipeline.md` | SUPERSEDED | ADR-028, ADR-031, ADR-041, WS1–WS13 shipped | MAPE-K framing replaced by SLO-based reliability framework. |
| `skill-atomicity-audit.md` | LIVE | ws4 Phase 1 (01c4c6d) | Top-3 fattest skills split; ~95 SPLIT-CANDIDATE/EMBEDDED/COUPLED skills still unprocessed. |
| `stabilization-mega-plan.md` | SUPERSEDED | ADR-028, ADR-031, ADR-041 | Principles absorbed into SLO framework; wiring-rate now continuous. |
| `status-report-april-11.md` | STALE | — | Historical snapshot, pre-dates 10 subsequent ADRs. |
| `token-optimization-masterplan.md` | SUPERSEDED | ADR-027, ADR-044, ws1/ws2/ws3 | TO-1..TO-8 substantially shipped; efficiency now measured via SLO 10/11. |
| `workflow-engine.md` | LIVE | ADR-036 (sprint primitives MVP) | Sprints cover batch-launch; DAG-with-dependencies, pipeline resumability, and SDD-pipeline-as-data remain open scope. |

## Remaining live work

### 1. `agent-escalation-capabilities.md` — Capability-aware escalation

Existing shipments (ADR-038 retry diversity, preamble escalation block) cover re-launch with same-tier agent + different approach. The plan's original scope includes:

- **Model-tier upgrade on stuck**: orchestrator detects escalation, promotes sonnet→opus for next attempt
- **Structured ESCALATION handoff**: partial progress (files touched, discoveries, error logs) serialized so the next agent starts above zero
- **Capability gap detection**: agent self-reports "I lack tool X / context window Y" so orchestrator can route accordingly

None of this is implemented as of 2026-04-21.

### 2. `docs-to-skills-audit.md` — 9 remaining doc→skill conversions

ws5 trimmed 8 SKILL-EXISTS docs to pointer stubs (commit a8c6c58). The original audit identified 17 SKILL-CANDIDATE items (docs with procedural content that should become skills); 9 are still unconverted. `status-report-april-11.md` listed these as parked. Candidates for a ws5-continuation sprint.

### 3. `rules-to-hooks-refactor.md` — Meta-policy for rule→hook migration

Individual rules have been migrated (license, content-policy, confidentiality) and `rules/ROADMAP.md §1` enumerates outstanding registrations. What's missing is a **tiering policy ADR** that declares:

- Which rules are enforceable (must become hooks) vs advisory (stay as rules)
- Migration decision criteria (false-positive tolerance, token savings threshold)
- Rollback strategy if a hook enforcement causes regressions

ADR-029 addressed one specific case; there is no general-purpose ADR.

### 4. `skill-atomicity-audit.md` — ~95 skills pending split review

ws4 Phase 1 split the 3 fattest skills into 10 atomic skills (commit 01c4c6d). The audit classified ~98 SKILL.md files; the remaining ~95 classified as SPLIT-CANDIDATE / EMBEDDED / COUPLED were never processed. This is a substantial backlog with no ADR coverage.

### 5. `workflow-engine.md` — DAG engine beyond sprints

ADR-036 shipped `cos sprint` (parallel batch launch + manifest + canonical events). The plan's additional scope:

- **Dependency graphs**: task B waits on A; A fails → B skipped
- **Pipeline resumability**: SDD pipeline crash → resume from last completed phase via on-disk state
- **Declarative SDD-as-data**: SDD phase sequence in YAML, editable without code change
- **Dashboard/visibility**: TUI showing active DAG nodes (ADR-036 defers this)

An ADR for a persistent, resumable DAG engine built on top of the sprint manifest would be the natural next step.

## Recommended actions

1. **Archive the 3 STALE plans** (`docs-hook-rule-candidates.md`, `docs-rescan-results.md`, `status-report-april-11.md`) into `.cognitive-os/plans/archive/2026-04/` — they are historical snapshots with no residual scope. Do NOT do this in the current task; flag as a cleanup item.
2. **Open work-queue.json entries** for each of the 5 LIVE residual scopes above, with explicit cross-reference to the plan file and the ADRs that partially cover the scope. The orchestrator currently has no signal that these backlogs exist.
3. **Keep the 3 JSON settings files in place** — they are regenerated by `set-security-profile.sh` and consumed at runtime; they are not plans to be archived.
4. **Reference this doc from `rules/ROADMAP.md`** so future audits find the reconciliation trail rather than re-deriving it.
5. **Consider an ADR for rules-to-hooks meta-policy** (item 3 in Residual Live Work) — the tactical migrations are working but the strategy is implicit.
