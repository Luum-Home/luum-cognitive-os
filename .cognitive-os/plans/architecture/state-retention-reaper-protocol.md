# State Retention Reaper Protocol Implementation Plan

## Goal

Stop Cognitive OS from self-biting on its own safety residue by making mutable
state retention declared, audited, and reaped with archive-first safety.

## Phase 1 — Land the contract

- Add `manifests/state-retention.yaml` with initial high/medium-risk surfaces.
- Add ADR-199 and the 2026-05-06 session diagnosis.
- Link the artifacts from the docs index and master plan checklist.

## Phase 2 — Build the operator path

- Add `scripts/state_retention_audit.py`.
- Add `cos state retention` for general audit.
- Add `cos stash cleanup` as an archive-first stale auto-pre-agent cleanup path.
- Add `hooks/state-retention-audit.sh` and session-end dry-run wiring.

## Phase 3 — Expand reapers

- Compact terminal claims and active-task records after their declared age/count.
- Archive stale `.cognitive-os/agent-bus/*` directories.
- Add rotation for metrics JSONL files.
- Add preserve-worktree intake cleanup only after dirty/stash/commit closure checks.

## Phase 4 — Enforce new-surface discipline

- Add a contract test that detects new mutable `.cognitive-os` paths without a
  manifest row.
- Add CI/audit lane strict mode for manifest validity.
- Require new runtime PRs to update retention policy when adding a ledger,
  artifact pool, lock, or cache.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. State retention audit can run in read-only mode from the repo root.
2. Session-end reaper prints a compact retention summary and never fails the hook chain.
3. Stale auto-pre-agent stashes can be cleaned with archive-ref-and-patch tombstones.
4. Manual/session stashes are excluded from automatic stash cleanup.
5. Follow-up reapers are implemented behind the same manifest instead of new one-off policies.
```
