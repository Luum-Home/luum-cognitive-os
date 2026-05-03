---
adr: 119
title: Session Filesystem Reaper
status: implemented
date: 2026-05-02
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos_work_inventory.py
  - lib/session_lifecycle.py
  - hooks/_lib/session-fs-reap.sh
  - scripts/so-reaper.sh
tier: standard
tags: [session, filesystem, reaper, cleanup]
---

# ADR-119: Session Filesystem Reaper

## Status

Accepted — 2026-05-02. Related: ADR-102, ADR-106, ADR-111, ADR-116, ADR-117.

## Context

Cognitive OS already has a process/session reaper path. `scripts/so-reaper.sh`
cleans expired process-registry entries and stale active task records. That
solves registry zombies: entries in `active-sessions.json`, process ledgers, or
active task records that no longer represent live work.

It does not solve filesystem accumulation. Session directories, request markers,
metrics, and handoff artifacts under `.cognitive-os/sessions/` can accumulate
long after a registry entry is gone. The inventory doctor can reveal this volume,
but a doctor is read-only: it reports the problem and leaves manual cleanup to an
operator.

The missing primitive is an archive-first filesystem action layer that can run
from the normal reaper cadence without deleting useful work.

## Decision

Add a Session Filesystem Reaper primitive.

The primitive is split into three layers:

1. `scripts/cos_work_inventory.py` remains the read-only detector and gains a
   volume alarm for aggregate session filesystem artifacts.
2. `lib/session_lifecycle.py` owns the action decision model and filesystem
   operations.
3. `hooks/_lib/session-fs-reap.sh` invokes the library from `scripts/so-reaper.sh`.

The reaper is conservative:

- Live PID/session evidence means keep.
- Pending content means keep.
- Recent dead sessions remain in grace.
- Old clean dead sessions are archived, not deleted.
- Archived sessions are removed only after the retention window.

## Decision states

| State | Meaning | Action |
|---|---|---|
| `KEEP_ACTIVE` | Session PID appears alive. | Leave untouched. |
| `KEEP_PENDING_CONTENT` | Pending request, unresolved task, parked edit, or pending marker exists. | Leave untouched. |
| `KEEP_RECENT_GRACE` | Dead/clean but younger than grace, or archive younger than retention. | Leave untouched. |
| `ARCHIVE` | Dead, content-clean, older than grace. | Move to `.cognitive-os/archive/sessions/`. |
| `RM_ARCHIVED` | Archived session older than retention. | Delete archive copy. |
| `ERROR_UNREADABLE` | Reaper cannot inspect safely. | Leave untouched and report. |

## Pending content inspection

Before acting, the reaper inspects:

- `user-requests.jsonl` for pending/open/queued/in-progress records;
- `tasks.json` for non-terminal task statuses;
- `handoff.md`, `backlog.md`, and `summary.md` for pending markers;
- `parked-edits/` for parked edits.

This content inspection is intentionally stricter than registry cleanup because
filesystem artifacts may be the only remaining evidence of interrupted work.

## Volume alarm

`cos_work_inventory.py` adds `--volume-alarm-threshold N` with default `1000` and
emits `session-volume-exceeded` when session directories plus marker files exceed
the threshold. This alarm is detection-only; cleanup still goes through the
archive-first reaper.

## Consequences

- The system no longer relies on humans to manually delete hundreds of stale
  session directories.
- Session cleanup is reversible during the archive window.
- The reaper can run every few minutes without deleting live or pending work.
- Operators get a count-level alarm when accumulation becomes unhealthy.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Delete filesystem sessions directly from `so-reaper.sh` | Too risky; shell code would duplicate inspection logic and make recovery harder. |
| Keep the doctor read-only and require manual cleanup forever | Does not scale with multi-agent/multi-IDE session volume. |
| Treat absence from `active-sessions.json` as safe to delete | Registry state and filesystem evidence have different lifecycles. |
| Archive forever without retention | Prevents data loss but still leaks disk/state indefinitely. |

## Verification

```bash
python3 -m pytest tests/behavior/test_session_fs_reap.py -q
python3 -m pytest tests/unit/test_cos_work_inventory.py -q
bash -n hooks/_lib/session-fs-reap.sh scripts/so-reaper.sh
python3 -m py_compile lib/session_lifecycle.py scripts/cos_work_inventory.py
```
