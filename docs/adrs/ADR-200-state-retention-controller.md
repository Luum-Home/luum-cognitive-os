---
adr: 200
title: State Retention Controller
status: accepted
implementation_status: not-applicable
date: '2026-05-06'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted decision/policy record with no explicit implementation
  surface
---

# ADR-200: State Retention Controller

## Status

Accepted — 2026-05-06

## Context

ADR-199 created the retention manifest and archive-first cleanup primitives. The
remaining risk is integration: a manual cleanup command does not prevent the
next self-bite, while a broad automatic reaper could delete or hide real WIP.

The architecture needs a controlled middle ground: automatic cleanup only for
surfaces whose safety invariants are proven, with repair occurring near the
operator pain point.

## Decision

Add `retention_mode` to each `manifests/state-retention.yaml` surface. The legacy `reaper` field remains as the intended trigger/location metadata; `retention_mode` is the enforcement selector used by automatic execute paths.


- `observe`: audit only; no automatic mutation.
- `repair-safe`: automatic archive-first cleanup is allowed from session-end.
- `repair-before-block`: preflight may repair once before blocking, but only
  when the inventory failure is exclusively caused by that surface.

`state_retention_audit.py` becomes the retention controller entrypoint:

- `--auto-safe --reap --execute` selects only `repair-safe` surfaces.
- `--repair-before-block --reap --execute` selects only preflight-repair
  surfaces.
- non-manual execute paths use a controller lock and cooldown.

`hooks/agent-prelaunch.sh` implements repair-first behavior for stale
auto-pre-agent stashes:

1. run ADR-116 inventory strict;
2. if it fails only because of auto-pre-agent stash residue, run the
   repair-before-block controller once;
3. retry inventory;
4. if it still fails, print compact findings and block.

`so-reaper.sh` runs `--auto-safe --reap --execute` at session end. Failures stay
advisory so cleanup bugs do not break session shutdown.

## Safety Boundary

Automatic repair is initially allowed only for:

- terminal task-claims compaction;
- stale/overflow agent-bus directory archival;
- auto-pre-agent stash archival during preflight repair.

Automatic repair is not allowed for manual stashes, preserve worktrees, runtime
locks, or metrics rotation until each has its own implementation and tests.

## Consequences

- The known auto-pre-agent self-bite is repaired at the point of failure.
- Mature append-only state stops accumulating indefinitely across sessions.
- Manual WIP remains protected and still blocks until explicitly reviewed.
- The controller adds complexity, but lock/cooldown/idempotency keep it from
  becoming a new source of repeated failures.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. `--auto-safe --reap --execute` cleans only `repair-safe` surfaces.
2. `--repair-before-block --reap --execute` cleans only auto-pre-agent stashes.
3. A full preflight smoke with a stale auto-pre-agent stash repairs and passes.
4. A full preflight smoke with a manual stale stash blocks and does not drop it.
5. Preflight block output is compact and does not print the full JSON payload.
```

## Verification

```bash
bash -n hooks/agent-prelaunch.sh scripts/so-reaper.sh scripts/state_retention_audit.py
python3 -m pytest tests/unit/test_state_retention_audit.py tests/behavior/test_state_retention_controller_flow.py -q
```

## Alternatives rejected
- Leave the decision as conversation-only or strategy-only documentation — rejected because ADR-067 requires executable decision records with auditable verification.
