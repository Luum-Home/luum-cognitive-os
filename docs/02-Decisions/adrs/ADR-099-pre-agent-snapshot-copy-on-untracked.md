---
adr: 99
title: 'Pre-agent snapshot: copy-on-untracked instead of stash-sweep'
status: accepted
implementation_status: implemented
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: 'pre-agent snapshot, crash recovery, cleanup, snapshot manager, and integration tests implement copy-on-untracked behavior'
---

# ADR-099 — Pre-agent snapshot: copy-on-untracked instead of stash-sweep

<!-- SCOPE: OS -->

**Status**: Accepted
**Date**: 2026-04-30
**Supersedes**: (part of ADR-003 Mechanism A)

---

## Status

Accepted.

## Context

`hooks/pre-agent-snapshot.sh` ran `git stash push --include-untracked --keep-index` before every Agent tool launch. This was intended to create a rollback point so `post-agent-verify.sh` could restore out-of-scope writes.

**The bug**: `--include-untracked` moves untracked files from the working tree into the stash object. The files disappear from the WT. The hook's pathspec exclusion (`:(exclude).cognitive-os`) only protected bookkeeping files; all other untracked files were swept.

**Evidence**:
- Today (2026-04-30) a session left `ADR-097-task-tracker-lifecycle.md` and associated test files untracked. Another session launched an agent; `pre-agent-snapshot.sh` ran and swept those files into stash `stash@{1}: cos-20260430-165827`. The orchestrator panicked thinking the files had been deleted; manual recovery from that stash was required.
- `git stash list | grep cos-` revealed **9 accumulated stashes** of the form `cos-YYYYMMDD-HHMMSS` — every session that had untracked files lost them transiently and had to manually recover.
- The invariant "the working tree is stable until I explicitly touch it" was violated on every agent launch when untracked files existed.

This is an architectural bug, not an operator error.

---

## Decision

Replace `--include-untracked` with a **copy-to-backup-dir** approach for untracked files:

1. **Compute snapshot ID**: `auto-pre-agent-<AGENT_ID>-<timestamp>-<pid>`.  
   The `pid` suffix prevents concurrent invocations from colliding.

2. **Tracked-modified files**: continue using `git stash push --keep-index` **without** `--include-untracked`. This stashes staged/unstaged tracked changes while preserving the index for the agent's workflow.

3. **Untracked files**: copy them to `.cognitive-os/snapshots/<snapshot-id>/` (preserving directory structure). **Do NOT remove them from the WT.** The backup is purely additive.

4. **Manifest**: write `.cognitive-os/snapshots/<snapshot-id>/manifest.json`:
   ```json
   {
     "snapshot_id": "auto-pre-agent-<ID>-<ts>-<pid>",
     "agent_id": "<AGENT_ID>",
     "timestamp": 1746028800.0,
     "timestamp_iso": "2026-04-30T16:00:00Z",
     "untracked_files": ["path/to/file.py", ...],
     "tracked_stash_ref": "stash@{0}",
     "snapshot_dir": ".cognitive-os/snapshots/<snapshot-id>",
     "mode": "copy",
     "status": "ok"
   }
   ```

5. **Recovery**: `crash-recovery.sh` reads the manifest and surfaces both halves (untracked backup + tracked stash) for operator restoration. `lib/snapshot_manager.restore_snapshot()` handles the actual restoration.

6. **TTL / cleanup**: `scripts/cleanup-snapshots.sh` calls `lib/snapshot_manager.prune_expired(ttl_days=30)`. TTL configurable in `cognitive-os.yaml` under `snapshots.ttl_days`.

7. **Size guard / retention cap**: untracked backup copies are bounded by `snapshots.max_file_mb` per file and `snapshots.max_total_mb` across snapshot storage. Oversized files stay in the WT, are not copied, and are recorded in `skipped_untracked_files`; aggregate cleanup prunes oldest snapshots first.

**Implementation artefacts**:
- `lib/snapshot_manager.py` — pure-Python helper (`create_snapshot`, `list_snapshots`, `restore_snapshot`, `prune_expired`)
- `hooks/pre-agent-snapshot.sh` — updated; delegates to `snapshot_manager.py` via inline Python heredoc
- `hooks/crash-recovery.sh` — extended to surface snapshot manifests (backward-compat: still shows legacy stashes)
- `cognitive-os.yaml` — new `snapshots:` section (ttl_days, max_file_mb, max_total_mb, mode)
- `scripts/cleanup-snapshots.sh` — operator script
- `tests/unit/test_snapshot_manager.py` — 12 unit tests
- `tests/integration/test_pre_agent_snapshot_border_cases.py` — 9 integration tests against real hooks
- `scripts/chaos/` — 3 operator runbook scripts

---

## Migration: existing 9 legacy stashes

The 9 `cos-YYYYMMDD-HHMMSS` stashes were created by the old path. They are **not auto-recovered** (risky without knowing original context). To inspect and selectively recover:

```bash
# List all legacy snapshot stashes
git stash list | grep -E '(cos-|auto-pre-agent-)'

# Show files in a specific stash
git stash show -p "stash@{1}"

# Restore a single file from a stash
git checkout "stash@{1}" -- path/to/file.py

# Apply entire stash (careful: may conflict with current state)
git stash apply "stash@{1}"

# Drop a stash once confirmed safe
git stash drop "stash@{1}"
```

The known recovery stash from today's incident: `stash@{1}: cos-20260430-165827`.

New-path snapshots live in `.cognitive-os/snapshots/` and coexist with old stashes. Old stashes are stale and can be dropped after manual review.

---

## Consequences

### Positive
- **WT stability**: untracked files are never ghosted by an agent launch. The invariant "WT is stable until I explicitly touch it" is restored.
- **Concurrent sessions**: snapshot IDs include PID; parallel launches write to distinct directories without races.
- **Full rollback preserved**: both halves (untracked backup + tracked stash) allow complete restoration.
- **Backward compat**: `COS_LEGACY_SNAPSHOT=1` restores old behaviour for operators who depend on it.
- **Observability**: manifest JSON makes every snapshot self-describing; `list_snapshots()` enumerates them.

### Negative
- **Disk usage**: snapshot copies accumulate until pruned. On a busy system with large untracked files and frequent agent launches, this could grow. Bounded by:
  - TTL prune (30 days default)
  - `scripts/cleanup-snapshots.sh` can be run manually or scheduled
  - Size caps skip large per-file copies and prune oldest snapshots under aggregate repo pressure

### Follow-up
- `cleanup-snapshots.sh` could be registered as a periodic hook (SessionEnd or daily cron).
- The manifest schema may evolve as crash-recovery.sh gains richer restoration UX; versioning in manifest recommended.

---

## Alternatives rejected

- Keep the previous behavior unchanged — rejected because the audit or runtime failure would remain deterministic and would continue masking real regressions.

## Verification

Run the focused contract for this decision:

```bash
python3 -m pytest tests/behavior/test_pre_agent_snapshot.py tests/unit/test_snapshot_manager.py -q
```
