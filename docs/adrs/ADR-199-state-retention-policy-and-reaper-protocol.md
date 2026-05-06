# ADR-199: State Retention Policy and Reaper Protocol

## Status

Accepted — 2026-05-06

## Context

Cognitive OS relies on mutable safety state: stashes, task claims, active tasks,
agent bus folders, JSONL metrics, runtime locks, and preserve worktrees. These
surfaces protect user work and make agent behavior auditable.

The failure mode is accumulation. A safety surface that is never reaped becomes
a self-bite: it slows diagnostics, pollutes preflight, or blocks agent dispatch.
The 2026-05-06 stash preflight incident showed the pattern clearly. ADR-116 was
right to detect stale hidden WIP, but the runtime lacked the paired retention
policy and cleanup path.

## Decision

Every mutable Cognitive OS state surface must declare a retention policy in
`manifests/state-retention.yaml` before it is treated as a durable runtime
surface.

Each declaration includes:

- `kind`: `ledger`, `artifact-pool`, `lock`, or `cache`;
- `path`: filesystem, Git stash, or Git worktree surface;
- `max_age`: bounded duration or `persistent`;
- `max_count`: item budget or rotation/archive marker;
- `reaper`: `session-start`, `session-end`, `manual`, `auto-on-create-plus-one`,
  or `rotation`;
- `tombstone`: whether cleanup drops, archives, compacts, or preserves a ref;
- `owner_pid`: whether liveness should extend retention;
- `owner_files` and `documentation`.

Add `scripts/state_retention_audit.py` as the enforcement/audit entrypoint. It
validates the manifest, inventories declared surfaces, reports drift, and offers
archive-first cleanup for supported surfaces. Mutation requires `--execute`; the
default is dry-run.

Add operator aliases:

- `cos state retention` for the general audit;
- `cos stash cleanup` for stale `auto-pre-agent-*` cleanup.

Add `hooks/state-retention-audit.sh` and call the audit from `scripts/so-reaper.sh`
so session-end reports retention drift without turning cleanup bugs into session
failures.

## Safety Rules

- Cleanup of Git stashes must archive before drop by writing a preserved ref and
  patch/name-status files.
- Auto cleanup must only target known auto-generated stash subjects.
- Manual/session stashes remain outside the auto-pre-agent cleanup selector.
- Reaper failures are advisory in session-end hooks.
- Strict blocking belongs in explicit audit/CI lanes, not the default Stop hook.

## Consequences

- New mutable state cannot be added responsibly without a retention declaration.
- Operators get one command to inspect retention drift instead of ad hoc greps.
- The stash self-bite class has an archive-first escape valve.
- The first implementation does not solve every surface completely; it creates
  the manifest and the highest-risk cleanup path, then lets future reapers fill
  in declared policies without new ADRs.

## Alternatives Rejected

- Fix only `auto-pre-agent-*` stashes. Rejected because claims, bus folders,
  JSONL logs, locks, and preserve worktrees share the same accumulation pattern.
- Auto-drop stale stashes without tombstones. Rejected because stash names and
  indices are not a reliable proof that the contents are worthless.
- Keep all cleanup manual. Rejected because the product promise is operational
  safety for non-expert users, not permanent operator archaeology.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. `manifests/state-retention.yaml` declares kind, age/count, reaper, tombstone, owner liveness, owner files, and docs for every initial state surface.
2. `python3 scripts/state_retention_audit.py --json` validates the manifest and inventories declared surfaces.
3. `python3 scripts/state_retention_audit.py --surface auto-pre-agent-stashes --reap --json` previews stale auto-pre-agent stash cleanup without mutation.
4. `python3 scripts/state_retention_audit.py --surface auto-pre-agent-stashes --reap --execute` archives refs and patches before dropping matching stale auto stashes.
5. Tests prove manual stashes are excluded from auto-pre-agent cleanup.
```

## Verification

```bash
bash -n hooks/state-retention-audit.sh scripts/so-reaper.sh scripts/cos
python3 -m pytest tests/unit/test_state_retention_audit.py -q
python3 scripts/state_retention_audit.py --project-dir . --json --no-metrics
```
