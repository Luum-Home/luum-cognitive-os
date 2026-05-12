---
adr: 224
title: Tombstone (consolidated into ADR-227)
status: tombstone
implementation_status: not-applicable
date: '2026-05-08'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit prose status migration for previously prose-only ADR
---

# ADR-224 — Tombstone (consolidated into ADR-227)

status: tombstone

## Status
Tombstone


<!-- SCOPE: OS -->

**Status**: Tombstone — consolidated into ADR-227 (2026-05-08)
**Date**: 2026-05-07 (original); tombstoned 2026-05-08
**Related**: ADR-227 (shadow-git checkpoint substrate — canonical authority)

---

## Reason

ADR-224 was originally proposed as the operator-facing "safety net boundary"
around ADR-227's shadow-git substrate. The M3 ADR sweep (2026-05-08) found
that every decision ADR-224 carried was already a hard rule in ADR-227:

| ADR-224 hard rule | Where it lives in ADR-227 |
|---|---|
| Snapshot storage never inside the project worktree | "Bare repo never enters user's project tree" hard rule |
| Snapshot does not touch `.git/index` or `git stash` | "`GIT_INDEX_FILE` isolation is mandatory" hard rule |
| Restore requires preview + explicit confirmation | "Restore is opt-in and gated" hard rule + diff-preview contract |
| Conversation truncation uses ADR-227 modes | Atomic restore semantics §`restore_atomic` |

Splitting these into two ADRs forced a "thin wrapper" shape (311 words, the
shortest non-tombstone in the 218–238 batch) that mostly deferred to ADR-227.
The decision to consolidate mirrors the precedent set by ADR-229 (cost-budget
ADR consolidated into ADR-228).

## Canonical authority

See **[ADR-227 — Shadow-Git Checkpoint Substrate](ADR-227-shadow-git-checkpoint-substrate.md)**. The "safety-net boundary" semantics are
documented under ADR-227's "Hard rules" and "Atomic restore semantics"
sections.

## Slot policy

- ADR-224 is reserved as a tombstone. Do not reuse the number for unrelated
  work.
- Future work on shadow-state safety boundaries extends ADR-227 in place or
  supersedes it; it does not re-occupy ADR-224.
- This mirrors the precedent set by ADR-229 (cost-budget consolidation into
  ADR-228) and ADR-214 (vacated for parallel-session collision).

## Implementation pointer

- `lib/shadow_git.py` — substrate (owned by ADR-227)
- `scripts/cos-rollback` — preview/restore CLI (owned by ADR-227)
- `manifests/shadow-git.yaml` — retention declaration (owned by ADR-227)
- `docs/runbooks/shadow-git-rollback.md` — operator runbook (owned by ADR-227)

No code or manifest moved as part of this consolidation; only the ADR record
was tombstoned. Cross-references in other ADRs (223, 227) that name ADR-224
remain valid as historical pointers.

## Context
This ADR was backfilled into the ADR-067 section contract after the
consolidation decision had been recorded. The original context remains in git
history (see commit prior to tombstone); this section exists so the ADR can be
audited uniformly under the contract audit.

## Decision
Tombstone ADR-224. ADR-227 is the canonical authority for shadow-state
snapshot semantics, including the operator-facing safety boundary that
ADR-224 originally tried to scope.

## Consequences
- The ADR can be checked by the common ADR contract audit.
- Future amendments must preserve this decision record instead of relying on
  conversation history.
- No implementation impact: ADR-224's slices A–C were always implemented as
  part of ADR-227's slice plan.

## Alternatives rejected
- Reusing this ADR number for a different decision — rejected because
  tombstones preserve numbering provenance and prevent contradictory
  references.
- Expanding ADR-224 with additional decision content — rejected because no
  unique decision exists; every hard rule is already in ADR-227.

## Verification
```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```
