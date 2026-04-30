# ADR-082 — Plan Location Convention

<!-- SCOPE: OS -->

**Status**: Accepted (executed 2026-04-30)
**Date**: 2026-04-30
**Author**: Maintainer
**Related**: ADR-028, ADR-028a, ADR-064, ADR-081,
duplication audit (engram #15886, `/tmp/cos-duplication-audit-2026-04-30.md`)

---

## Status

Accepted (executed 2026-04-30).

### Migration log (2026-04-30)

Files moved via `git mv` and all citations updated in the same changeset:

| Old path | New path |
|---|---|
| `docs/architecture/plans/adr-064-implementation-plan.md` | `.cognitive-os/plans/architecture/adr-064-implementation-plan.md` |
| `docs/architecture/plans/governed-self-improvement-roadmap.md` | `.cognitive-os/plans/architecture/governed-self-improvement-roadmap.md` |
| `docs/architecture/plans/headless-clustered-runtime-plan.md` | `.cognitive-os/plans/architecture/headless-clustered-runtime-plan.md` |
| `docs/architecture/plans/runtime-comparison-benchmark-plan.md` | `.cognitive-os/plans/architecture/runtime-comparison-benchmark-plan.md` |
| `docs/architecture/core-vs-extensions-migration-plan.md` | `.cognitive-os/plans/architecture/core-vs-extensions-migration-plan.md` |
| `docs/architecture/skills-rules-canonicalization-workplan.md` | `.cognitive-os/plans/architecture/skills-rules-canonicalization-workplan.md` |
| `docs/plans/SO-RELIABILITY-MEGA-PLAN.md` | `.cognitive-os/plans/roadmaps/so-reliability-mega-plan.md` |
| `docs/roadmaps/adr-049-050-051-mega-plan.md` | `.cognitive-os/plans/roadmaps/adr-049-050-051-mega-plan.md` |
| `docs/architecture/stabilization-roadmap.md` | `.cognitive-os/plans/roadmaps/stabilization-roadmap.md` |
| `docs/archive/plans/token-optimization-masterplan.md` | `.cognitive-os/plans/archive/token-optimization-masterplan.md` |

**Anomaly resolved (2026-04-30 follow-up)**: `docs/architecture/plans/test-resource-governance-sprint.md`
was not in this ADR's migration table but was discovered during execution. It is a sprint plan
tied to ADR-072/073 (test lane taxonomy) and was moved to
`.cognitive-os/plans/architecture/test-resource-governance-sprint.md`. The directory
`docs/architecture/plans/` was then removed.

Hook updated: `hooks/session-startup-protocol.sh` now indexes
`.cognitive-os/plans/architecture/` and `.cognitive-os/plans/roadmaps/` instead of
`docs/architecture/plans/`, `docs/plans/`, and `docs/roadmaps/`.

Enforcement test created: `tests/audit/test_plan_locations.py`.

---

## Context

### The problem: plans are invisible to each other

As of 2026-04-30 there is no documented convention for where plan files live.
The duplication audit (engram #15886) found 26+ plan files spread across at
least seven directories with no governing rule:

| Directory | File count | Notes |
|---|---|---|
| `.cognitive-os/plans/features/` | 16 | SDD artifacts, short-lived feature work |
| `.cognitive-os/plans/research/` | 2 | Pre-decision research |
| `docs/architecture/plans/` | 5 | Cross-cutting and ADR-linked |
| `docs/plans/` | 1 | Orphan (`SO-RELIABILITY-MEGA-PLAN.md`) |
| `docs/roadmaps/` | 1 | Multi-ADR mega-plan |
| `docs/archive/plans/` | 1 | Superseded token-optimization work |
| `docs/architecture/` (root, no subdir) | 2 | Plans landed outside any plans subdir |

None of these directories is indexed by `hooks/session-startup-protocol.sh`.
As of today, 10+ plan files are invisible to startup-protocol discovery.

### Confirmed duplication incidents

**Incident 1 — 2026-04-17**: The orchestrator drafted ADR-028a
(`SO-RELIABILITY-MEGA-PLAN`) as a new document. An equivalent plan already
existed in `docs/plans/SO-RELIABILITY-MEGA-PLAN.md` and was referenced by
ADR-028. Because `docs/plans/` was not indexed at SessionStart, the prior plan
was invisible and the duplication was not caught until manual review.

**Incident 2 — 2026-04-30**: An agent authored
`docs/architecture/plans/adr-064-implementation-plan.md` to record the
implementation plan for cross-harness authoring. ADR-064 and ADR-081 already
captured the same sequencing decisions. The file was invisible to the agent
that wrote ADR-081, which re-derived the dependency order independently.

Both incidents share the same failure mode: the orchestrator cannot discover a
prior plan because the directory it lives in is not in the startup index. Once
duplication occurs it compounds — later agents cite the duplicate rather than
the canonical source, creating a second divergence.

### Design tension: operational vs. architectural plans

Some directories exist by intent (`.cognitive-os/plans/features/` was created
explicitly for SDD artifacts), others by accident (plans landing in
`docs/architecture/` root, plans landing in `docs/roadmaps/` because there was
no canonical roadmap location). The core tension is:

- **Operational plans** (SDD feature work, short-lived, tied to a sprint or
  change) should live close to the tooling that creates and reads them.
- **Architectural plans** (cross-cutting decisions, ADR implementation
  sequencing, multi-quarter roadmaps) should live close to the ADRs they
  reference.

Merging them into one flat directory solves discoverability but erases that
distinction and creates noise when browsing either type. Keeping them separate
is defensible only if the boundary is explicit, enforceable, and indexed.

---

## Decision

### Option A — Single root under `.cognitive-os/plans/` with typed subdirs

```
.cognitive-os/plans/
  features/       — SDD feature plans, short-lived, sprint-scoped
  research/       — exploratory / pre-decision research
  architecture/   — cross-cutting, ADR-linked, long-lived plans
  roadmaps/       — strategic, multi-quarter, time-horizon-based plans
  archive/        — completed or superseded plans (excluded from active indexing)
```

### Option B — Split by audience: operational vs. architectural

```
.cognitive-os/plans/         — operational: feature-scoped, short-lived
docs/architecture/plans/     — architectural: cross-cutting, ADR-linked
docs/roadmaps/               — strategic: time-horizon-based
```

**Recommendation: Option A.**

Justification by trade-off:

| Concern | Option A | Option B |
|---|---|---|
| Discoverability | Single root → one glob pattern indexes everything | Three roots → three glob patterns, sync risk |
| ADR coupling | `architecture/` subdir named for the relationship | `docs/architecture/plans/` implies the ADR hierarchy is the organizing principle, which is sometimes wrong (roadmaps are not architecture-driven) |
| Agent compliance | Agents that do not know the convention land in `.cognitive-os/plans/` by default (they already do) — the convention formalizes the current gravity | Agents must choose between two roots; without a convention document they always pick wrong |
| Archival semantics | `archive/` subdir is explicit, excluded from indexing by path prefix | Archival must be handled per-root; no shared mechanism |
| Migration cost | Move 6 files from `docs/` trees into `.cognitive-os/plans/architecture/` and `roadmaps/` | Move 16 files in the opposite direction |

Option B's main argument — that architectural plans belong near ADRs — is
undercut by the fact that `.cognitive-os/plans/architecture/` is
a named type boundary, not a physical distance. The startup indexing is
path-based; physical proximity to ADRs does not help discoverability.
The discoverability gain from a single root is unambiguous and resolves the
confirmed failure mode directly.

### Canonical structure (adopted)

```
.cognitive-os/plans/
  features/       — SDD change plans, feature design, sprint artifacts
  research/       — pre-decision research, audits, landscape surveys
  architecture/   — cross-cutting and ADR-linked plans (long-lived)
  roadmaps/       — multi-quarter, product-level, time-horizon plans
  archive/        — completed or superseded (excluded from active indexing)
```

All plan directories under `.cognitive-os/plans/` (except `archive/`) MUST be
indexed by `hooks/session-startup-protocol.sh`. The `archive/` subdir is
excluded from the active count but remains discoverable on-demand.

Directories that currently hold plan files and are not in the canonical
structure above are deprecated as plan locations. Any plan appearing outside
`.cognitive-os/plans/` after this ADR is accepted is a violation.

---

## Naming convention

- **File names**: kebab-case, descriptive, no spaces.
- **ADR-linked plans**: `adr-NNN-implementation-plan.md` or
  `adr-NNN-<topic>-plan.md`. The `NNN` prefix makes the relationship
  machine-readable for auditing.
- **Date-prefixed roadmaps**: `YYYY-MM-<topic>-roadmap.md`. Date prefix is
  required for time-sensitive roadmaps so archive ordering is deterministic.
- **Research files**: descriptive name, no date required unless the research is
  a point-in-time snapshot (audits, landscapes).

### Required front matter

Every plan file MUST include one of the following fields in its front-matter or
opening metadata block:

```yaml
related-adr: ADR-NNN        # if the plan is coupled to an ADR
# OR
no-adr-required: true
reason: <one sentence>      # why no ADR governs this plan
```

The `related-adr` field is the machine-readable link that prevents the
duplication failure mode: startup indexing and audit tooling can cross-reference
plans against ADRs and surface orphans.

---

## Migration plan

The following files must move to comply with the canonical structure. No file
moves in this ADR — this is design only. Migration is a follow-up task.

### Files to move into `.cognitive-os/plans/architecture/`

| Current path | Target path | Rationale |
|---|---|---|
| `docs/architecture/plans/adr-064-implementation-plan.md` | `.cognitive-os/plans/architecture/adr-064-implementation-plan.md` | ADR-linked, cross-cutting |
| `docs/architecture/plans/governed-self-improvement-roadmap.md` | `.cognitive-os/plans/architecture/governed-self-improvement-roadmap.md` | Architectural scope, not time-horizon strategic |
| `docs/architecture/plans/headless-clustered-runtime-plan.md` | `.cognitive-os/plans/architecture/headless-clustered-runtime-plan.md` | Architectural, cross-cutting |
| `docs/architecture/plans/runtime-comparison-benchmark-plan.md` | `.cognitive-os/plans/architecture/runtime-comparison-benchmark-plan.md` | Architectural scope |
| `docs/architecture/core-vs-extensions-migration-plan.md` | `.cognitive-os/plans/architecture/core-vs-extensions-migration-plan.md` | Plan at wrong depth in docs/architecture/ |
| `docs/architecture/skills-rules-canonicalization-workplan.md` | `.cognitive-os/plans/architecture/skills-rules-canonicalization-workplan.md` | Plan at wrong depth in docs/architecture/ |

### Files to move into `.cognitive-os/plans/roadmaps/`

| Current path | Target path | Rationale |
|---|---|---|
| `docs/plans/SO-RELIABILITY-MEGA-PLAN.md` | `.cognitive-os/plans/roadmaps/so-reliability-mega-plan.md` | Multi-ADR, cross-cutting roadmap; was root of Incident 1 |
| `docs/roadmaps/adr-049-050-051-mega-plan.md` | `.cognitive-os/plans/roadmaps/adr-049-050-051-mega-plan.md` | Multi-ADR roadmap in a now-deprecated location |
| `docs/architecture/stabilization-roadmap.md` | `.cognitive-os/plans/roadmaps/stabilization-roadmap.md` | Time-horizon roadmap, not ADR-linked |
| `docs/architecture/plans/runtime-comparison-benchmark-plan.md` | (covered above under architecture — verify intent before moving) | May belong in research if it is pre-decision |

### Files to move into `.cognitive-os/plans/archive/`

| Current path | Target path | Rationale |
|---|---|---|
| `docs/archive/plans/token-optimization-masterplan.md` | `.cognitive-os/plans/archive/token-optimization-masterplan.md` | Already considered archived; consolidate |

### Files that stay in place (no move required)

| Path | Reason |
|---|---|
| `docs/plan-system.md` | Documentation about the plan system itself, not a plan |
| `docs/rules-consolidation-plan.md` | Evaluate: may belong in architecture after migration |
| `docs/roadmap.md` | Top-level product roadmap; may serve as entry point pointing into `.cognitive-os/plans/roadmaps/` |
| `docs/architecture/plans-reconciliation-2026-04-21.md` | Audit artifact; belongs in `docs/reports/`, not plans — no move under this ADR |
| `docs/business/` files | Business-scoped; outside plan convention scope; evaluate separately |
| `docs/release/roadmap-v1.0-full-e2e.md` | Release artifact; outside plan convention scope |
| `docs/reports/merge-readiness-master-plan-2026-04-23.md` | Report artifact; keep in reports |
| `docs/reports/next-session-plan-dormant-to-real.md` | Session artifact; keep in reports |

### Timing

Migration should be executed as a single follow-up task immediately after this
ADR is accepted. It is not gated on any other ADR. The task should update the
`related-adr` front matter field in each file as part of the move.

---

## Indexing rules

1. `hooks/session-startup-protocol.sh` MUST glob all of the following and
   include the count in the startup summary:
   - `.cognitive-os/plans/features/**/*.md`
   - `.cognitive-os/plans/research/**/*.md`
   - `.cognitive-os/plans/architecture/**/*.md`
   - `.cognitive-os/plans/roadmaps/**/*.md`
2. `.cognitive-os/plans/archive/` is explicitly excluded from the active
   count. Files there are still discoverable via `mem_search` and direct path
   access; they are excluded only from the "active plan" inventory shown at
   startup.
3. A follow-up task must extend `session-startup-protocol.sh` to add these
   globs. Until that task ships, the protocol remains blind — this ADR
   documents the target state.

---

## Enforcement

### Audit test

A new test `tests/audit/test_plan_locations.py` must be created. It fails if
any `.md` file matching the pattern `*plan*.md` or `*roadmap*.md` (case
insensitive) is found outside `.cognitive-os/plans/` or the explicitly
exempted paths listed in `Stay in place` above. Exemptions are maintained in
the test itself as a documented allowlist.

### Pre-commit gate

Optional — not mandated by this ADR. The audit test runs in the `broad` test
lane and is sufficient as a CI gate. A pre-commit hook would reduce the
feedback loop but the audit test covers the invariant at the merge boundary.
Left as an open question for the team.

---

## Consequences

### Positive

- **Single root, one glob** — startup indexing requires one path pattern instead
  of seven. New agents that drop plans in `.cognitive-os/plans/` comply by
  default even without reading this ADR.
- **Duplication backstop** — the `related-adr` front matter field, combined
  with audit tooling, surfaces plans that duplicate ADR-level decisions before
  they diverge.
- **Archive semantics are explicit** — `archive/` is a named subdir with a
  documented exclusion from active counts. Previously, "archived" meant "moved
  somewhere in `docs/`" with no consistent convention.
- **ADR-linked plans are machine-readable** — the `adr-NNN-` filename prefix
  enables cross-referencing without parsing file content.

### Negative / Trade-offs

- **One-time migration cost** — 6–10 files must move. Each move requires
  updating any cross-references (ADR bodies, engram entries, hook scripts that
  reference old paths).
- **`docs/architecture/plans/` becomes a deprecated location** — existing
  tooling or agent prompts that hard-code this path will produce files in the
  wrong place until they are updated. The audit test catches violations at the
  next CI run.
- **Agents that skip reading conventions still land in the wrong place** — the
  audit test is a CI backstop, not a prevention mechanism. An auto-relocate
  hook (see open questions) would close this gap.

---

## Open questions

**1. Should `docs/roadmaps/` survive as a separate location?**

The `docs/roadmaps/` directory currently holds one file
(`adr-049-050-051-mega-plan.md`) which belongs in `.cognitive-os/plans/roadmaps/`
under this ADR. Once migration is complete, `docs/roadmaps/` would be empty
and should be removed. However, `docs/roadmap.md` (note: file, not directory)
is a top-level entry point that may be meaningful to human readers browsing the
repo. Recommended resolution: keep `docs/roadmap.md` as a human-readable
index that links into `.cognitive-os/plans/roadmaps/`; remove the empty
`docs/roadmaps/` directory after migration.

**2. Auto-relocate hook for agent-authored plans?**

Agents that do not read this ADR will continue to land plans in arbitrary
locations. A post-write hook that detects `*plan*.md` patterns outside the
canonical root and moves them (with a warning) would close the prevention gap.
This is a follow-up item and is not mandated here. The risk of false positives
(moving documentation that happens to contain "plan" in its name) must be
evaluated before implementing such a hook.

---

## Alternatives rejected

- **Option B (two-root split: operational vs. architectural)**: Rejected because
  it requires agents to correctly classify their output before writing, which
  has already proven unreliable. It also requires two startup index patterns
  instead of one and provides no archive consolidation mechanism.
- **Single flat directory (no subdirs)**: Rejected because feature plans (16
  files, high churn) and roadmaps (low churn, strategic) would become
  undifferentiated. Browsing and filtering by type would require content
  inspection rather than path inference.
- **No convention, enforce via lint only**: Rejected because lint-only
  enforcement does not help discovery at SessionStart. The startup index is
  path-based; without a canonical root, lint can tell you a file is in the
  wrong place only after the damage (invisible plan, potential duplication) has
  already occurred in the session that wrote it.

---

## Verification

```bash
# After migration is complete
python3 -m pytest tests/audit/test_plan_locations.py -q --tb=short

# Confirm startup protocol indexes all four active subdirs
grep -n "cognitive-os/plans" hooks/session-startup-protocol.sh
```

---

## Cross-references

- ADR-028: SO SLO catalogue (source of Incident 1 duplication)
- ADR-028a: SO-RELIABILITY-MEGA-PLAN addendum (the duplicate)
- ADR-064: Cross-harness authoring guide (source of Incident 2)
- ADR-081: Codex harness adapter (duplicate sequencing in `adr-064-implementation-plan.md`)
- Duplication audit: engram #15886, `/tmp/cos-duplication-audit-2026-04-30.md`
- `hooks/session-startup-protocol.sh` (indexing follow-up target)
- `tests/audit/test_plan_locations.py` (to be created)
