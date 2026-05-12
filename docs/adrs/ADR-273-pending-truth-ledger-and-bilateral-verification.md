---

adr: 273
title: Pending Truth Ledger and Bilateral Verification Loop
status: accepted
implementation_status: partial
date: 2026-05-12
supersedes: []
superseded_by: null
extends: [ADR-082, ADR-127, ADR-247, ADR-248, ADR-252, ADR-254, ADR-255]
implementation_files:
  - manifests/pending-truth.yaml
  - scripts/cos-pending-truth-aggregator
  - scripts/cos-pending-truth-verify
  - docs/reports/pending-truth-latest.json
  - docs/reports/pending-truth-latest.md
  - tests/red_team/portability/test_cos-pending-truth-aggregator.py
tier: maintainer
tags: [control-plane, backlog, plans, verification, drift-prevention, source-of-truth, postmortem-2026-05-12]
---
# ADR-273: Pending Truth Ledger and Bilateral Verification Loop

## Status
Accepted — Slice A implemented (schema + aggregator); Slices B (verifier) and C (hooks) tracked.

<!-- SCOPE: OS -->

**Date**: 2026-05-12

## Context

The 2026-05-12 bilateral verification pass surfaced a systemic drift problem
in COS pending-work tracking. Today's data point:

- **9 different surfaces** independently claim to track "what is pending":
  plan checkboxes, ADR status frontmatter, `master-pending-*.md` snapshots,
  `radar-2026-05-08-implementation-tracker.md`, `cos_session_backlog.py`
  output, `aspirational-audit.py`, `acc_pipeline.py`, `cos-control-plane-audit`,
  `feature-reality-matrix`.
- **None is a verified source of truth**. Three Opus agents working in
  parallel found that **25% of the project's 283 OPEN plan checkboxes are
  actually shipped** but the plan was never updated. Additionally **7% are
  obsolete** (context no longer applies) and **16% are ambiguous**. Only
  **~52% are truly pending**.
- The same drift pattern was discovered 2026-05-11 on a single plan
  (`component-scope-classification.md` Phase 4 reported PENDING but actually
  shipped). Today's pass proves the pattern is project-wide, not local.

**Root cause**: plan checkboxes and ADR statuses are **manually maintained
by the author at write time**. When code lands that closes a plan item,
nothing forces the plan to update. Every "is X done?" query requires fresh
bilateral verification, and the existing primitives don't aggregate or
auto-verify.

**Existing primitives that should solve this but don't**:
- `plan-claim-validator.sh` — enforces `(verified: ...)` proofs **on edit**;
  does nothing when code lands without touching the plan.
- `cos_session_backlog.py` — aggregates surfaces but does not verify;
  currently broken under Python 3.14.
- `cos-control-plane-audit` (ADR-248) — runs manifest-declared regression
  audits, but no manifest yet covers plan items.
- `aspirational-audit.py`, `acc_pipeline.py`, `feature-reality-matrix` —
  each covers a slice (primitives, capabilities, feature claims) but not
  plan items or follow-ups.

## Decision

Introduce a single canonical pending-truth ledger with bilateral verification:

### 1. Canonical schema (`manifests/pending-truth.yaml`)

Every actionable pending item carries:

```yaml
schema_version: pending-truth/v1
items:
  - id: plan:adr-064:slice-1-1            # stable composite id
    type: plan-checkbox                    # plan-checkbox|adr-slice|follow-up|user-request|audit-finding
    source: .cognitive-os/plans/architecture/adr-064-implementation-plan.md:L42
    status: verified-pending               # verified-pending|verified-done|ambiguous|obsolete|unverified
    last_verified: 2026-05-12T14:30Z
    evidence:
      - {kind: file_exists, path: lib/codex_adapter.py, result: missing}
      - {kind: test_passes, cmd: "pytest tests/unit/test_codex_adapter.py", result: not_found}
    next_action: implement codex adapter
    owner_adr: ADR-064
    effort_estimate: 1 session
```

### 2. Aggregator (`scripts/cos-pending-truth-aggregator`)

Read-only walk of all surfaces, emit normalized items to
`manifests/pending-truth.yaml` + `docs/reports/pending-truth-latest.{json,md}`.

Sources scanned in v1:
- `.cognitive-os/plans/{features,architecture,roadmaps}/*.md` — every `- [ ]`
  checkbox becomes a `plan-checkbox` item
- `docs/adrs/ADR-*.md` — every ADR with `status: proposed|draft|in-progress`
  becomes an `adr-slice` item
- `docs/reports/radar-2026-05-08-implementation-tracker.md` — every 🔲 or 🟡
  row becomes a `follow-up` item
- `.cognitive-os/sessions/*/user-requests.jsonl` — every `status: pending`
  becomes a `user-request` item
- `.cognitive-os/tasks/active-tasks.json` — every non-cancelled becomes
  `audit-finding`

### 3. Verifier (`scripts/cos-pending-truth-verify`) — Slice B (not implemented in this ADR)

For each item, runs the declared `evidence` checks (grep / file existence /
test execution / ADR cross-reference), updates `status` + `last_verified`,
and emits drift diff. This is the automation of what the 3 Opus agents did
manually on 2026-05-12.

### 4. Hooks (Slice C, not implemented in this ADR)

- **PostToolUse Edit**: when commit touches `lib/X.py` and ≥1 ledger item
  declares evidence on `lib/X.py`, suggest "should you mark item closed?"
- **Stop hook (weekly)**: re-run verifier on items with `last_verified > 7 days`.
- **PreCommit gate**: block merge-to-main if `pending-truth-latest.json` is
  stale > 30 days.

### 5. ADR-273 contract

- The 9 dispersed surfaces remain as **inputs** to the aggregator, NOT as
  competing sources of truth. The ledger replaces them as the canonical
  query target for "what is pending".
- Every new actionable item proposed by a plan, ADR, or report MUST appear
  in `manifests/pending-truth.yaml` within one aggregation cycle.
- The aggregator output (`docs/reports/pending-truth-latest.md`) is the
  ONE doc to read for pending-work questions in future sessions.

## Slice A scope (this ADR's commit)

Implements only:
- The schema definition (this ADR §1).
- `manifests/pending-truth.yaml` skeleton with 5 sample items demonstrating
  each `type` value.
- `scripts/cos-pending-truth-aggregator` — read-only walk of the 5 sources
  above, emits `docs/reports/pending-truth-latest.{json,md}`.
- Portability test at `tests/red_team/portability/test_cos-pending-truth-aggregator.py`.

Slices B (verifier) and C (hooks) are tracked as follow-ups; this ADR
declares the schema is stable so they can build on it.

## Consequences

- **One file to consult**: `docs/reports/pending-truth-latest.md` answers
  "what is pending" without re-running 3 Opus agents.
- **Drift becomes visible**: after Slice B lands, items whose evidence
  fails verification get re-classified; plans/ADRs that disagree become
  audit findings instead of silent staleness.
- **Anti-accumulation enforced**: after Slice C, new items without
  evidence-check declarations cannot be added.
- **Migration**: existing 9 surfaces stay; their format does not change.
  Only their role does — from "potential source of truth" to "input to
  aggregator".

## Alternatives rejected

- **Per-plan tracker tabs**: would not solve cross-surface drift; only
  pushes the problem from plans into plan-trackers.
- **Engram as ledger**: Engram works for episodic memory + semantic recall;
  it does not produce a deterministic verifier-friendly export.
- **External issue tracker (GitHub Issues)**: would require new
  permissions/auth surface; off-roadmap and violates local-first posture.
- **Eliminate 8 surfaces, keep only this ledger**: too aggressive — plans
  still serve operator narrative; ADRs serve architectural memory. The
  ledger is **derived**, not replacement.

## Verification

```bash
# Slice A acceptance (this commit)
python3 scripts/cos-pending-truth-aggregator --json > /tmp/pt.json
python3 -c "import json; d=json.load(open('/tmp/pt.json')); assert d['schema_version']=='pending-truth/v1'; assert len(d['items'])>0; print('items:', len(d['items']))"

# Portability proof
python3 -m pytest tests/red_team/portability/test_cos-pending-truth-aggregator.py -q

# Manifest schema valid
python3 -c "import yaml; d=yaml.safe_load(open('manifests/pending-truth.yaml')); assert d['schema_version']=='pending-truth/v1'"
```

## Follow-ups

- **Slice B** — `scripts/cos-pending-truth-verify` (bilateral evidence
  runner). Effort: 1 session. Tracked separately.
- **Slice C** — hook wiring (PostToolUse Edit + Stop weekly + PreCommit
  staleness gate). Effort: 1 session. Tracked separately.
- **Migration audits**: deprecate `master-pending-YYYY-MM-DD.md` cadence
  in favor of `pending-truth-latest.md` once Slice B lands.

## Related

- ADR-082 — Plan location convention (input to aggregator)
- ADR-127 — Active primitive index (analogous "derived truth" pattern)
- ADR-247 — Manifest-driven postmortem regression audits (same manifest
  pattern for audits)
- ADR-248 — Control-plane audit loop (Slice C will integrate with this)
- ADR-252 — Capability coverage matrix and feature reality ledger (sibling
  pattern, different domain)
- ADR-254 — External tool intelligence plane (sibling: derived from
  multiple sources)
- ADR-255 — Feature-to-external-tool due diligence (anti-reinvention
  guardrail)
- Postmortem 2026-05-12 bilateral verification: 165 OPEN checkboxes →
  42 mismarked-done (25%), 11 obsolete (7%) — documented in
  `docs/reports/historical-pending-analysis-2026-05-12.md` §5.
