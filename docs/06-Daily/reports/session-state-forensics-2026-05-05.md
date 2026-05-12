---
title: Session State Forensics — Branch, Worktree, and ADR Collision
date: 2026-05-05
status: draft
scope: maintainer
tags: [forensics, worktree, adr, routing, paperclip, session-safety]
---

# Session State Forensics — 2026-05-05

## Purpose

Record the observed state of the active session branch after multiple agents worked
on related but separate topics: skill routing, rejected Paperclip surfaces,
ADR tombstones, and primitive routing contracts.

This report is intentionally forensic rather than normative. It preserves what
was found, why it is risky, and which remediation path should be applied before
continuing feature work.

## Operator Intent

The operator asked to review the active local work, including local branches and
worktrees, while several agents were attacking separate themes. The intent was
to cover gaps in the chosen session branch, not to silently import another
worktree's cleanup strategy into that branch.

The topics in scope were separate:

- primitive routing coverage and router metadata gaps;
- post-mortem for the routing investigation;
- exhaustive tests preventing future routing regressions;
- Paperclip rejection/purge decisions;
- ADR tombstone primitive proposal;
- ADR numbering integrity;
- local uncommitted work across branches/worktrees.

## Observed Git State

Observed from `<repo-root>`.

```text
Active branch:
  session/41961ce2-paperclip-rejection-multi-surface

HEAD:
  aeb391b0 chore: finish rejected surface tombstones

Recent stack:
  aeb391b0 chore: finish rejected surface tombstones
  a4bd126d refactor: tombstone rejected integration surface
  937d0ece feat(skills): activate routing store and lifecycle proposals
  9d7598dd release: v0.26.0 — Operator-CLI Primary, Phoenix Optional, Honest API Findings
```

Two worktrees were present:

```text
<repo-root>
  branch: session/41961ce2-paperclip-rejection-multi-surface
  head:   aeb391b0

<session50-worktree>
  branch: session/50c35ce9-remove-paperclip-multi-surface
  head:   2aba0fe9
```

## Commit Classification

### Commit 1 — Keep

`937d0ece feat(skills): activate routing store and lifecycle proposals`

Observed content aligns with the session's routing work:

- ADR-174 routing follow-up;
- ADR-176 SkillStore;
- ADR-177 lifecycle proposal work;
- new routing/lifecycle hooks;
- `lib/skill_store.py`;
- `lib/skill_lifecycle_promoter.py`;
- initial SKILL.md routing metadata migrations;
- routing coverage manifest and tests.

Forensic verdict: keep this commit as the baseline for the routing work.

### Commit 2 — Conflict Candidate

`a4bd126d refactor: tombstone rejected integration surface`

Observed as a broad rejected-surface cleanup commit. It touched many unrelated
areas and applied a hard-delete/tombstone strategy to Paperclip-related material.

Risk factors:

- removed or rewrote broader settings and configuration surfaces;
- deleted `docs/02-Decisions/adrs/ADR-043-paperclip-local-daemon.md`;
- modified many existing ADRs and reports;
- mixed Paperclip disposition policy with unrelated repository-wide cleanup.

Forensic verdict: conflict candidate. It should not be treated as accepted work
on the active session branch without an explicit disposition decision.

### Commit 3 — Conflict Candidate

`aeb391b0 chore: finish rejected surface tombstones`

Observed as a continuation of the hard-delete/tombstone strategy.

It added:

- ADR tombstones for `003`, `004`, `005`, `043`, `046`, `085`, `171`, `173`,
  and `179`;
- `scripts/adr_tombstone.py`;
- `scripts/cos-adr-tombstone`;
- `skills/adr-tombstone/SKILL.md`;
- tombstone-related tests.

It also deleted Paperclip hooks, client code, package files, and tests.

Forensic verdict: conflict candidate. The `adr-tombstone` primitive may be
salvageable, but the tombstones for `171`, `173`, and `179` collide with active
session numbering expectations.

## Confirmed ADR Number Collisions

The active branch currently contains these tombstones:

```text
docs/02-Decisions/adrs/ADR-171-tombstone.md
docs/02-Decisions/adrs/ADR-173-tombstone.md
docs/02-Decisions/adrs/ADR-179-tombstone.md
```

Their frontmatter declares the numbers as tombstones:

```yaml
adr: 171
status: tombstone
```

```yaml
adr: 173
status: tombstone
```

```yaml
adr: 179
status: tombstone
```

This conflicts with the session's expected use of those numbers:

| ADR number | Session expectation | Current active-branch state | Risk |
|---|---|---|---|
| ADR-171 | Paperclip rejection/disposition decision | Tombstone | Number ownership collision |
| ADR-173 | Skill router observability/reservation context | Tombstone | Number ownership collision |
| ADR-179 | Rules auto-derive decision | Tombstone | Number ownership collision |

## Root Cause

The immediate root cause was a worktree/branch hygiene failure:

1. A second worktree was created or used for the Paperclip purge surface.
2. Its hard-delete/tombstone strategy was allowed to influence the active
   session branch.
3. The active branch then carried commits from two different policy choices:
   mark/deprecate/archive versus delete/tombstone.
4. ADR numbers were not reserved or checked globally before tombstones were
   created.

The deeper systemic gap is that ADR mutation, skill creation, and router
metadata all need fail-new contracts. The repository now has tests for some
skill-routing gaps, but the session exposed that ADR numbering and worktree
ownership need the same level of enforcement.

## Blast Radius

The suspicious range is:

```text
937d0ece..aeb391b0
```

Files touched by the conflict-candidate commits include:

- local harness/settings files such as `.claude/settings.json` and
  `.codex/hooks.json`;
- `cognitive-os.yaml`;
- `CHANGELOG.md`;
- many ADRs, reports, plans, and manifests;
- Paperclip docs, hooks, package files, and tests;
- the new `adr-tombstone` primitive and tests.

The broad blast radius means this should not be repaired with ad hoc file edits.
It needs a deliberate branch-state correction.

## Recommended Remediation

Recommended order:

1. Preserve the current dirty worktree as a patch before destructive operations.
2. Keep `937d0ece`.
3. Revert `aeb391b0` and `a4bd126d` from the active branch.
4. Re-apply only explicitly accepted changes:
   - routing contracts and manifest changes;
   - Paperclip test deletion if still desired;
   - Paperclip runtime deletion only under the accepted disposition policy;
   - `adr-tombstone` primitive only after removing number collisions and adding
     numbering integrity tests.
5. Restore or create the intended ADR files for `171`, `173`, and `179`, or
   explicitly renumber them with a documented reconciliation.
6. Add or keep contracts that fail if:
   - a new skill lacks routing metadata;
   - projected skills are not routeable by profile;
   - unprojected skills are included in router indices;
   - router cache ignores SKILL.md checksum changes;
   - lazy catalogs load full skill bodies unnecessarily;
   - an ADR number is reused by multiple semantic decisions;
   - a tombstone is created for an ADR number already owned by an active
     decision.

## Policy Decision Still Needed

Paperclip disposition must be made explicit before further cleanup:

| Policy | Meaning | Consequence |
|---|---|---|
| Deprecated/archived | Keep historical ADR and code references with clear non-active status | Safer audit trail, less purge completeness |
| Delete/tombstone | Remove rejected integration material and reserve numbers with neutral tombstones | Cleaner surface, higher collision and history-loss risk |

The branch currently contains evidence of both policies. Continuing without a
single policy will create more contradictory documentation and tests.

## Acceptance Criteria for Repair

The repair is not done until all of the following are true:

1. `git log --oneline` shows the active branch keeping the routing commit while
   removing or neutralizing the two conflict-candidate commits.
2. `docs/02-Decisions/adrs/ADR-171*`, `docs/02-Decisions/adrs/ADR-173*`, and `docs/02-Decisions/adrs/ADR-179*` no
   longer collide with active session decisions.
3. The Paperclip disposition policy is represented consistently in ADRs, docs,
   hooks, packages, and tests.
4. New skill routing contracts continue to pass.
5. ADR numbering integrity tests prevent future tombstone/decision collisions.
6. `docs/00-MOCs/entrypoints/README.md` links to this forensic report.

## Current Forensic Conclusion

The active branch is not merely behind or dirty. It contains valid routing work
plus imported cleanup commits whose ADR tombstone policy conflicts with the
session's ADR numbering and Paperclip disposition expectations.

The safest path is to keep the routing commit, back up uncommitted changes, undo
the two conflicting commits, and then reintroduce only accepted cleanup through a
single policy.
