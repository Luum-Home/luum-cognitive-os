---
adr: 274
title: Operational Guide Required for Maintainer-Tier Capability ADRs
status: accepted
implementation_status: partial
classification_basis: 'Slice A audit and Phase 1 enforcement exist; P1/P2 backfill and trust-score integration remain future scope'
date: 2026-05-12
supersedes: []
superseded_by: null
extends: [ADR-067, ADR-097, ADR-105, ADR-144, ADR-244, ADR-273]
implementation_files:
  - scripts/cos-operational-guide-audit.py
  - hooks/adr-section-validator.sh
  - docs/reports/operational-guide-audit-latest.json
  - docs/reports/operational-guide-audit-latest.md
  - tests/red_team/portability/test_cos-operational-guide-audit.py
tier: maintainer
tags: [adr-contract, documentation, operational-guide, drift-prevention, anti-overclaim, postmortem-2026-05-12]
partial_remaining: Slice A audit and Phase 1 enforcement exist; P1/P2 backfill and trust-score integration remain future scope
partial_remaining_basis: specific classification_basis
---
# ADR-274: Operational Guide Required for Maintainer-Tier Capability ADRs

## Status
Accepted — Slice A implemented (audit + Phase 1 enforcement).

<!-- SCOPE: OS -->

**Date**: 2026-05-12

## Context

The 2026-05-12 adversarial-review finding on ADR-273 surfaced a recurring
anti-pattern in the project:

> Architectural decisions are documented (Decision, Consequences,
> Alternatives), but the **operational mental model** (how to actually
> USE the capability, what changes for the operator, where to read it
> cold without conversation context) lives only in chat and gets lost
> between sessions.

The remedy applied to ADR-273 (adding an §Operational Guide section +
rendering an auto-preamble in the aggregator output) was a single-instance
fix. **It did not generalize**:

- No convention requiring §Operational Guide for new maintainer-tier
  capability ADRs.
- No gate validating its presence (existing `hooks/adr-section-validator.sh`
  per ADR-067 enforces §Status, §Context, §Decision, §Consequences,
  §Alternatives rejected, §Verification — but NOT §Operational Guide).
- No audit detecting existing ADRs without operational guides.
- No backfill priority list.

**Empirical magnitude (from 2026-05-12 audit)**: of 280 ADRs, approximately
N (TBD post-audit) maintainer-tier capability ADRs lack an
§Operational Guide. Each is a future "esto está documentado?" moment.

**Root cause shared with ADR-273**: COS produces capabilities faster than
documentation discipline keeps up. Without explicit gates, operational
context perpetually trails artifacts.

## Decision

Establish a contract for §Operational Guide in maintainer-tier ADRs that
introduce new capabilities.

### 1. Required sections (the contract)

An ADR REQUIRES §Operational Guide when ALL of these are true:

- `tier: maintainer` (or absence of tier with capability declared in body)
- `status: accepted`
- Introduces a NEW capability (one or more of: new script, new manifest,
  new hook, new schema, new public-facing surface)
- Is NOT a tombstone, superseded, or alias

Excluded by design:
- Tombstone ADRs (`*-tombstone.md`) — no operational guide needed.
- Pure-architectural ADRs that DECIDE but don't introduce a new operator-facing
  surface (e.g., "use Apache 2.0 license", "rename ADR-X to ADR-Y").

### 2. Minimum structure

An §Operational Guide MUST include at least 3 of these 5 sub-sections:

1. **What changes for the operator** — what is the new surface, what
   roles existing artifacts now play
2. **What this answers (and what it doesn't)** — a `before/after` table
   anchored on concrete questions
3. **Daily operational pattern** — a numbered workflow with concrete
   commands
4. **When sources disagree** — the conflict-resolution rule (per ADR-105
   trust-score precedent, code usually wins)
5. **Reading guide for cold readers** — for a future operator/agent who
   encounters this ADR without conversation context

### 3. Audit (Phase 1, this ADR)

`scripts/cos-operational-guide-audit.py` scans `docs/adrs/ADR-*.md`,
identifies ADRs subject to the contract, and reports presence/absence of
§Operational Guide with sub-section coverage. Emits:

- `docs/reports/operational-guide-audit-latest.json` (machine-readable)
- `docs/reports/operational-guide-audit-latest.md` (human-readable + backfill list)

### 4. Gate (Phase 1, this ADR)

`hooks/adr-section-validator.sh` is extended with a new check
(`require_operational_guide`) that fires when:

- The edited ADR has `tier: maintainer` in frontmatter
- AND `status: accepted` (or transitioning to accepted)
- AND `implementation_files` lists at least one non-tombstone file

Default behavior: WARN (exit 0). Strict mode (`COS_STRICT_ADR_VALIDATION=1`)
exits 2 to block the edit until the section is added.

This **does NOT enforce on existing ADRs at first run** — those are handled
via the backfill list (§5). Enforcement applies only to ADRs edited after
this ADR lands.

### 5. Backfill (Phase 1, this ADR)

The first audit run produces a prioritized backfill list. Priorities:

- **P0** — ADRs accepted ≤ 30 days (recent capabilities most likely to need
  operational context fresh in mind)
- **P1** — Maintainer-tier accepted ADRs with implementation_files
- **P2** — Older maintainer-tier ADRs missing the guide
- **Exclude** — tombstones, superseded, project-tier internal-only ADRs

### 6. Future scope (Phase 2+, tracked follow-ups)

- **Plans** with `status: ACTIVE` → §Operational Guide required after
  shipping (when the plan is complete enough to be "used")
- **Manifests** for control-plane primitives → operational guide in the
  manifest's `purpose:` field plus the manifest's owning script's docstring
- **Skills** → `description: "Use when…"` is the operational-guide-equivalent;
  H6 migration already enforces this convention

### 7. Trust-score integration

§Operational Guide presence becomes part of the Trust Report scoring for
ADRs: if a maintainer-tier capability ADR ships without one, that's a
**LOW** trust signal even if all other sections are present.

## Operational Guide

### What changes for the operator

Before this ADR: §Operational Guide was a discretionary section. Some ADRs
had it (ADR-273 after its 2026-05-12 retrofit); most didn't.

After this ADR: maintainer-tier capability ADRs MUST include it. New ADRs
written after 2026-05-12 are validated at write-time (advisory by default,
blocking under strict mode). Existing ADRs identified in the backfill list
are tracked as work items, not silently tolerated.

### What this answers (and what it doesn't)

| Question | Before | After |
|---|---|---|
| "Will this ADR be readable cold by a future operator?" | unknown | YES if it has §Operational Guide; NO otherwise (audit flags it) |
| "How many ADRs are missing operational context?" | unknown | reported by audit, prioritized for backfill |
| "Does a new capability ADR need an operational guide?" | author's choice | required by hook (advisory default) |

### Daily operational pattern

1. Author drafts an ADR with §Status, §Context, §Decision, §Consequences,
   §Alternatives rejected, §Verification (existing ADR-067 contract).
2. If the ADR introduces a new capability: also add §Operational Guide with
   ≥3 of the 5 sub-sections (§2 above).
3. `adr-section-validator.sh` fires on Write/Edit, warns if missing.
4. If pushing to main: `cos-operational-guide-audit` runs and reports.
5. Periodically (weekly), operator reads
   `docs/reports/operational-guide-audit-latest.md` and picks P0 backfill items.

### When sources disagree

If the audit reports an ADR as missing §Operational Guide but the operator
believes the ADR doesn't need one (e.g., pure architectural decision):

- Add `<!-- adr-274-exempt: <reason> -->` comment in the ADR body
- The audit honors the exemption; record appears with status `exempt` not
  `missing`
- This is the safety valve; abuse defeats the contract

### Reading guide for cold readers

If you encounter ADR-274 cold:

1. Read `docs/reports/operational-guide-audit-latest.md` for the current
   audit state (which ADRs comply, which need backfill).
2. Read this ADR §Decision for the contract.
3. Check `hooks/adr-section-validator.sh` for the gate implementation.
4. The audit is integrated into ADR-248 control-plane audit loop; expect
   it to fire automatically on session-start and on ADR edits.

## Consequences

- **Drift loop closes**: future maintainer-tier capability ADRs cannot ship
  without operational context (advisory at first, strict-on-demand).
- **Backfill is explicit**: the audit produces the prioritized list; what's
  missing is no longer invisible.
- **Trust-score signal**: ADRs without operational guide carry a defined
  cost in trust-score; this matches the ADR-105 bilateral-claim-verification
  principle (claims need evidence; operational guides ARE the operator-facing
  evidence).
- **Migration cost**: backfilling existing P1/P2 ADRs is real work (~15min
  per ADR). The audit makes the scope visible; sweeping is the operator's
  decision per sprint.

## Alternatives rejected

- **Mandate from day 1 without audit**: would block every existing ADR edit
  on a "missing operational guide" warning. Too noisy. Audit + backfill is
  the migration path.
- **Make it a Rule in rules/agent-quality.md only**: rules without enforcement
  are honored ~50% of the time per project history (today's audit on 165
  checkboxes proved this). Code-enforced gate is necessary.
- **Auto-generate operational guides from ADR body via LLM**: violates the
  doctrine principle that operational context must be human-curated; LLM
  output would be plausible-but-untested and pollute the trust signal.
- **Inherit the section from a parent ADR**: too coupled; each ADR should
  stand on its own when read cold.

## Verification

```bash
# Audit (Phase 1)
python3 scripts/cos-operational-guide-audit.py --write

# View backfill list
cat docs/reports/operational-guide-audit-latest.md | head -50

# Validator (Phase 1) — triggers on PostToolUse Edit on docs/adrs/ADR-*.md
# Default advisory; strict mode:
COS_STRICT_ADR_VALIDATION=1 bash hooks/adr-section-validator.sh < /dev/null

# Portability proof
python3 -m pytest tests/red_team/portability/test_cos-operational-guide-audit.py -q
```

## Follow-ups

- **Phase 2** — extend contract to plans (`*-plan.md` with status: ACTIVE),
  manifests (purpose field), and scripts (docstring requires operational
  guide section if SCOPE: both). Tracked as `adr-274-phase-2-plans-manifests`.
- **Phase 3** — wire operational-guide-audit into `cos-control-plane-audit`
  lane (ADR-248) so it runs automatically alongside primitive-coherence
  and capability-coverage audits.
- **Phase 4** — operational-guide rendering: build a doc-site or skill
  that surfaces all guides as a navigable index for cold readers.

## Related

- **ADR-275** — Closure & projection primitives. ADR-275's
  `cos-session-start-projector` surfaces this audit's P0/P1 backfill
  list at session start across 3 harnesses, and
  `cos-closure-trust-signal` quantifies operator trust based on whether
  closures used the close primitive. Together they make the §OG contract
  self-correcting (audit → projector surfaces → operator closes via
  primitive → trust signal updates).
- **`docs/adrs/STATUS-TAXONOMY.md`** — canonical decision/implementation
  status vocabulary that the audit consumes when deciding whether an
  ADR is `subject_to_contract` (must be `accepted | implemented`,
  not `tombstone | superseded`).
- **`docs/architecture/pending-truth-architecture.md`** — 4-layer map
  of the read/project/close/drift system this ADR is part of.
- ADR-067 — ADR section contract (existing baseline; this ADR extends)
- ADR-097 — Documentation execution audit (audit pattern this ADR follows)
- ADR-105 — Bilateral claim verification (operational guides ARE the
  bilateral evidence for capability claims)
- ADR-144 — Hook-enforced rule projection (extension of adr-section-validator
  follows this pattern)
- ADR-244 — Trust-report enforcement (operational-guide presence feeds the
  trust score)
- ADR-273 — Pending truth ledger (the audit emits items into the ledger
  schema as `audit-finding` type)
- 2026-05-12 adversarial-review finding on ADR-273 documenting the
  anti-pattern that motivated this ADR.
