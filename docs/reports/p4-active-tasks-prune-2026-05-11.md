# P4 Active-Tasks & Claims Prune — 2026-05-11 (Opus re-run)

**Date:** 2026-05-11
**Model:** Opus 4.7 (re-prune after Sonnet pass on 2026-05-10)
**Scope:** `.cognitive-os/tasks/active-tasks.json` and `.cognitive-os/tasks/active-claims.json`

## Summary

| File | Before | After | Pruned |
|---|---|---|---|
| `.cognitive-os/tasks/active-tasks.json` | 4 | 4 | 0 |
| `.cognitive-os/tasks/active-claims.json` | 15 | 0 | 15 |

The prior Sonnet run on 2026-05-10 already reduced `active-tasks.json` from 113 → 4 and `active-claims.json` from 11 → 0. This Opus pass verified the surviving 4 task entries and pruned 15 newly-accumulated `released` claims that were written between 2026-05-10T23:58Z and 2026-05-11T15:36Z (after Sonnet's earlier prune).

## Tasks: kept (4 / 4)

All four surviving entries pass the prune criteria:

- **2× `cancelled`** with `completedAt = 2026-04-30T19:40:00Z` — 11 days old, inside the 30-day retention window (cutoff 2026-04-11). Kept per rule "cancelled with completedAt > 30 days ago → prune". These are zombie-cleanup ADR follow-ups.
- **2× `blocked_by_claim`** — real blockers (stash auto-reapply, ACC dashboard CLI). Kept per rule "blocked_by_claim → KEEP".

No additional task entries qualified for pruning this pass.

## Claims: pruned (15 / 15)

All 15 entries were `status: released` with `released_at` immediately following `claimed_at` (sub-second to ~7s ttl). These are completed claim-and-release transactions from the file-claim lock system — pure audit noise once released.

Breakdown by status:
- `released`: 15

### Sample of 3 pruned claims (sanitized)

```json
{
  "claimed_at": "2026-05-10T23:58:08Z",
  "released_at": "2026-05-10T23:58:09Z",
  "session_id": "default-session",
  "status": "released",
  "task_id": "task-desc-4ee0a899dc0f74aa",
  "fingerprint": "1c83b8ff65f9b759275db71f"
}
```

```json
{
  "claimed_at": "2026-05-11T00:12:43Z",
  "released_at": "2026-05-11T00:12:50Z",
  "session_id": "default-session",
  "status": "released",
  "task_id": "task-desc-6f4ba480f8cd1432",
  "fingerprint": "69655f666935ccab3bdf947f"
}
```

```json
{
  "claimed_at": "2026-05-11T15:36:39Z",
  "released_at": "2026-05-11T15:36:41Z",
  "session_id": "default-session",
  "status": "released",
  "task_id": "task-desc-95b9ea5b4ee495e6",
  "fingerprint": "8f0b3e29a82265a4e20a826a"
}
```

## Files

- Modified: `.cognitive-os/tasks/active-tasks.json` (no content change — 4 entries retained, only `lastUpdated` bumped)
- Modified: `.cognitive-os/tasks/active-claims.json` (15 → 0 entries; `updated_at` set to 2026-05-11)
- Created: `.cognitive-os/tasks/active-tasks-archive-2026-05-11.json` (empty `tasks[]` — preserved for audit symmetry)
- Created: `.cognitive-os/tasks/active-claims-archive-2026-05-11.json` (15 archived claims)
- Untouched: `.cognitive-os/tasks/active-tasks-archive-2026-05-10.json`, `.cognitive-os/tasks/active-claims-archive-2026-05-10.json` (prior audit history)

## Recommendation

1. **Auto-prune released claims at write-time.** Released claims have no operational value once `released_at` is set — the file-claim mutex is reset. The current flow keeps them indefinitely, which means a daily prune like this re-runs forever on the same shape of garbage. Suggest patching the claim-release helper to either (a) drop released entries immediately or (b) ship them straight to a rolling 7-day archive without touching `active-claims.json`.
2. **Re-examine the 2× `cancelled` zombie tasks.** They sit at 11 days old. Once they cross the 30-day boundary (~2026-05-30) they will auto-prune. If the ADR follow-up they reference has landed, consider closing them out now instead of letting them age.
3. **`blocked_by_claim` entries deserve a triage pass.** Both entries were requested on 2026-05-02 and still carry conflicts against `default-session`. If the holding session is gone, the conflict is stale and these should either be re-launched or formally cancelled.
4. **Confirm Sonnet 05-10 archive integrity before deleting any source.** This re-run did not re-validate yesterday's archive contents — recommended spot-check before any compaction job touches `.cognitive-os/tasks/`.

## Verification

- JSON parses cleanly on all four files (originals + new archives).
- No absolute filesystem paths anywhere in this report (confidentiality hook clean).
- Status counts reconcile: tasks 4 = 2 cancelled + 2 blocked_by_claim; claims 0 kept + 15 archived = 15 original.
