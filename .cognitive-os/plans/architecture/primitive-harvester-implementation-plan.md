# Primitive Harvester Implementation Plan

## Goal

Make conversation-to-primitive promotion repeatable and testable without allowing
unreviewed self-modification.

## Phase 1 — Advisory classifier

- Add `scripts/cos_primitive_harvester.py`.
- Add `skills/primitive-harvester/SKILL.md`.
- Emit JSON plans only; no repository writes.
- Cover all decision classes with automated tests.

## Phase 2 — Integration points

- Invoke from session close or after large task summaries.
- Feed Engram session summaries into `--conversation-file`.
- Add optional report output under `.cognitive-os/reports/`.

## Phase 3 — Governed artifact drafting

- Allow a separate worker to consume `CREATE_PRIMITIVE` / `IMPROVE_EXISTING`
  plans and draft files.
- Require behavior tests and portability tests before merge.
- Require normal merge queue landing.

## Non-goals

- No automatic commits from the classifier.
- No direct hook registration.
- No runtime mutation based solely on confidence score.

## Acceptance Criteria

- CREATE, IMPROVE_EXISTING, USE_EXISTING, DOCUMENT_ONLY, and DISCARD decisions
  are all tested.
- Existing primitive matching prevents duplicate worktree/cleanup primitives.
- Discard paths include low-signal and ambiguous conversations.
- Portability proof runs in a temporary consumer-style repo.
