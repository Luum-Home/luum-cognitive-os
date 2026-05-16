# COS Duplication Audit — 2026-04-30

> Read-only investigation. No files modified.

---

## A. Inventory Summary

### Plan locations

| Location | Files | Indexed by startup hook? |
|---|---|---|
| `.cognitive-os/plans/features/` | 16 | YES (`session-startup-protocol.sh`) |
| `.cognitive-os/plans/research/` | 2 | NO (hook only scans `features/`) |
| `docs/04-Concepts/architecture/plans/` | 5 | NO |
| `docs/plans/` (legacy) | 1 (`SO-RELIABILITY-MEGA-PLAN.md`) | NO |
| `docs/99-Archive/archive/plans/` | 1+ (`self-optimizing-pipeline.md`) | NO |
| `docs/roadmaps/` | 1 (`adr-049-050-051-mega-plan.md`) | NO |

**Total tracked plans: 26+** — only 16 are indexed by the startup hook.

### ADRs

| Range | Count |
|---|---|
| ADR-027 → ADR-081 (present in `docs/02-Decisions/adrs/`) | 58 files (including sub-ADRs: 027a, 028a/b/c, 029b, 033b, 055b) |
| ADRs referenced by plans but NOT in `docs/02-Decisions/adrs/` | 2 (ADR-002, ADR-012) |

---

## B. Confirmed Duplications

### 1. ADR-081 ↔ `docs/04-Concepts/architecture/plans/adr-064-implementation-plan.md` (the triggering case)

ADR-081 is the Codex harness adapter decision. The 9-task implementation plan for the exact same work (Task 1.1 in the plan) was drafted 2026-04-28 and NOT indexed. ADR-081 was drafted 2026-04-30 independently.

**Evidence:**
- Plan: `"Task 1.1 — lib/harness_adapter/codex.py (1 session, ~3h)"` with full acceptance criteria
- ADR-081: `"1. Implement lib/harness_adapter/codex.py (Plan Task 1.1)"` — mirrors the same criteria

ADR-081 does explicitly reference the plan after the fact (`Consumes-plan:` frontmatter). The duplication is acknowledged and reconciled, but only because it was caught this session.

### 2. ADR-028 ↔ `docs/plans/SO-RELIABILITY-MEGA-PLAN.md`

ADR-028 was authored without consulting the pre-existing mega-plan. ADR-028a is a remediation addendum that explicitly documents the conflict.

**Evidence:**
- Mega-plan: lives in `docs/plans/` (a third, non-indexed location)
- ADR-028a: `"ADR-028 was authored on 2026-04-17 without consulting .cognitive-os/plans/features/self-optimizing-pipeline.md or the work-queue at .cognitive-os/work-queue.json"`

This exact duplication pattern is a confirmed recurrence of the ADR-081 incident.

### 3. `docs/04-Concepts/architecture/plans/adr-064-implementation-plan.md` ↔ ADR-064

ADR-064 contains an inline task list and acceptance criteria for Phase 2 work (Surface 1–4 gap analysis). The implementation plan re-derives the same surface breakdown with overlapping acceptance criteria.

**Evidence:**
- ADR-064 body: `"lib/harness_adapter/cursor.py`) are not yet implemented. The verification suite this ADR mandates... does not exist"`
- Plan Section 1: re-states the same surface-by-surface inventory with nearly identical file lists

The plan is additive (more detail, estimates, ordering), not strictly duplicate — but the surface inventory is re-derived rather than referenced.

---

## C. Suspected Duplications (needs human review)

### 1. `governed-self-improvement-roadmap.md` ↔ ADR-074 / ADR-075

`docs/04-Concepts/architecture/plans/governed-self-improvement-roadmap.md` (date: 2026-04-29, no ADR refs) describes a self-improvement loop and workstreams. ADR-074 (Tier-0 Learning-Loop Closure, 2026-04-30) and ADR-075 (Stage 2 Selective Expansion) address adjacent/overlapping territory. The roadmap has no `Consumes-plan:` backlink in any ADR. **Risk: a future ADR in this space re-derives the roadmap's decisions.**

### 2. `workflow-engine.md` ↔ ADR-036

The plan explicitly notes `"Related ADRs: ADR-036 (sprint orchestration primitives)"`. ADR-036 covers "batch launching (sprint YAML → parallel agents)" and the plan covers "DAG-with-dependencies, resumability, SDD-pipeline-as-data." The boundary is described but not formally cross-linked in ADR-036. If ADR-036 is ever extended, the workflow-engine plan's scope may be silently overlapped.

### 3. `test-runner-ergonomics-{proposal,spec,design,tasks}.md` — internal family duplication

Four files for the same feature exist in `.cognitive-os/plans/features/`. These are SDD pipeline artifacts (proposal → spec → design → tasks) and are by design sequential, not duplicate. However, all four reference both ADR-068 and ADR-069, and all four appear as separate entries in the startup hook's plan count. The startup hook reports "16 plans" when 4 of those are one SDD chain — inflating the apparent plan count.

### 4. `docs/04-Concepts/architecture/plans/runtime-comparison-benchmark-plan.md` and `headless-clustered-runtime-plan.md` — both orphan-reference ADR-027

Both plans reference ADR-027 but are not referenced back from ADR-027. ADR-027 is about SO Slimming; both plans cover runtime/cluster concerns. The link may be incidental (ADR-027 as a broad-scope anchor) but should be confirmed — these plans may belong under a different (possibly not-yet-written) ADR.

---

## D. Orphans

### D1. Plans referencing ADRs that do not exist in `docs/02-Decisions/adrs/`

| Plan | Missing ADR |
|---|---|
| `.cognitive-os/plans/features/docker-to-pip-migration.md` | ADR-002, ADR-012 |
| `.cognitive-os/plans/features/docs-to-skills-audit.md` | ADR-012 |

ADR-002 and ADR-012 are referenced but have no corresponding file in `docs/02-Decisions/adrs/`. These are likely pre-numbering-convention decisions that were never formalized as files, or the files were deleted. The plans that reference them cannot be validated.

### D2. ADRs that reference plans where the path doesn't resolve

| ADR | Referenced path | Exists? |
|---|---|---|
| ADR-027a, ADR-028 | `docs/plans/features/hook-architecture-v2.md` | NO — correct path is `.cognitive-os/plans/features/hook-architecture-v2.md` |
| ADR-028a | `.cognitive-os/plans/features/self-optimizing-pipeline.md` | NO — file is at `docs/99-Archive/archive/plans/self-optimizing-pipeline.md` (archived) |

ADR-027a contains a stale path (`docs/plans/features/hook-architecture-v2.md`) that resolves to a non-existent location. The actual file is in `.cognitive-os/plans/features/`. This is a documentation correctness issue.

### D3. Plans in the wrong directory (convention drift)

| Plan | Current location | Should arguably be in |
|---|---|---|
| `adr-064-implementation-plan.md` | `docs/04-Concepts/architecture/plans/` | `.cognitive-os/plans/features/` (operational plan, not architecture doc) |
| `governed-self-improvement-roadmap.md` | `docs/04-Concepts/architecture/plans/` | Could be either; no ADR, so arguably premature for `docs/04-Concepts/architecture/plans/` |
| `SO-RELIABILITY-MEGA-PLAN.md` | `docs/plans/` (third location) | `docs/99-Archive/archive/plans/` (its content is superseded by ADR-028) |
| `self-optimizing-pipeline.md` | `docs/99-Archive/archive/plans/` | Correctly archived, but ADR-028a still refers to it as `.cognitive-os/plans/features/` |

### D4. Plans with no corresponding ADR (orphan plans)

| Plan | ADR refs | Risk |
|---|---|---|
| `governed-self-improvement-roadmap.md` | None | No ADR = decisions untracked; easy to re-derive |
| `project-audit-package.md` | None | Orphaned, no ADR backlink |
| `skill-atomicity-audit.md` | None | Orphaned, no ADR backlink |
| `cos-test-extension-notes.md` | None | Reconnaissance notes, arguably not a plan |
| `security-tools-landscape.md` | None | Research, no ADR follow-up |
| `sessionstart-deep-audit.md` | ADR-080 only | ADR-080 is Proposed; plan has no Accepted ADR yet |
| `headless-clustered-runtime-plan.md` | ADR-027 only (incidental) | No dedicated ADR |
| `runtime-comparison-benchmark-plan.md` | ADR-027 only (incidental) | No dedicated ADR |

---

## E. Convention Drift

### What the conventions say

- `inject-phase-context.sh` (hook) contains a hardcoded warning: `"plans/ at root has structure but no content. Active plans are in .cognitive-os/plans/. Both exist intentionally."` — but this is injected into agent prompts only, not documented.
- `session-startup-protocol.sh` scans only `.cognitive-os/plans/features/` — `research/` and all `docs/04-Concepts/architecture/plans/` are invisible to the startup summary.
- ADR-054 (Project Documentation Convention) assigns category `09-execution-plan` for roadmaps/sprints but does not specify which filesystem path plans should live in.
- No README, CONTRIBUTING.md, or AGENTS.md in the root project mentions plan directory conventions.

### Conclusion

There are **at least four distinct plan locations** (`.cognitive-os/plans/features/`, `.cognitive-os/plans/research/`, `docs/04-Concepts/architecture/plans/`, `docs/plans/`). Only one is indexed. The split appears to be **accidental** for `docs/04-Concepts/architecture/plans/` (files placed there by agents that didn't know about `.cognitive-os/plans/`) and **intentional-but-undocumented** for `docs/plans/` (the SO-RELIABILITY-MEGA-PLAN predates the convention). The `research/` sub-directory is also not indexed, meaning 2 research plans are invisible to session startup.

---

## F. Top 5 Highest-Risk Duplications (recency × impact)

| Rank | Pair | Risk | Why |
|---|---|---|---|
| 1 | `governed-self-improvement-roadmap.md` (2026-04-29) ↔ no ADR | **HIGH** | Most recent, touches core OS behavior, zero ADR backlink — next agent to work on self-improvement will re-derive decisions in an ADR without finding the roadmap |
| 2 | `docs/04-Concepts/architecture/plans/adr-064-implementation-plan.md` ↔ ADR-081 | **HIGH** | Triggered this audit; plan is NOT in the indexed directory; ADR-081 reconciled it manually but only by chance |
| 3 | `SO-RELIABILITY-MEGA-PLAN.md` (in `docs/plans/`) ↔ ADR-028 | **MEDIUM-HIGH** | Historic recurrence — same pattern already caused ADR-028a addendum; mega-plan is unarchived and could confuse future agents |
| 4 | `sessionstart-deep-audit.md` ↔ ADR-080 | **MEDIUM** | Plan (research) is not indexed; ADR-080 is Proposed; implementation work could start without finding the audit findings |
| 5 | `headless-clustered-runtime-plan.md` + `runtime-comparison-benchmark-plan.md` ↔ no dedicated ADR | **MEDIUM** | Two plans with no owning ADR, both referencing ADR-027 incidentally; if cluster/benchmark work restarts, decisions are uncaptured |

---

*Report generated 2026-04-30. Scope: read-only. No files modified.*
