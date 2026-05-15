# Primitive SCOPE classifier — Iteration 032 skills contradiction closure

Date: 2026-05-15

## Goal

Close the 3 skill contradictions after hooks were resolved.

## Manual classification decision

Kept these skills as `SCOPE: both` and corrected stale consumer availability from maintainer-only to shared-surface:

- `skills/proof-drill/SKILL.md`
- `skills/session-pending-brief/SKILL.md`
- `skills/session-pending-close/SKILL.md`

## Evidence

- `proof-drill` explicitly distinguishes `os-self`, `consumer-project`, and `both` proof modes.
- `session-pending-brief` orients COS and adopter-project sessions over pending work through projected session-start/pending ledgers.
- `session-pending-close` closes pending task/ADR/ledger items with bilateral proof and audit trail, which is a session workflow for COS and adopter projects using COS ledgers.

## Classifier robustness update

Added exact shared skill semantic patterns for:

- `proof-drill`;
- `session-pending-brief`;
- `session-pending-close`.

## Before / after

Before:

```json
{"skill_contradictions": 3, "classifier_contradictions": 30}
```

After:

```json
{"skill_contradictions": 0, "classifier_contradictions": 27, "remaining_contradictions_by_prefix": {"scripts": 27}}
```

Scripts remain intentionally deferred to a separate front.
