---

adr: 243
title: Post-Rewrite Push-Collision Check Exception
status: accepted
implementation_status: implemented
classification_basis: 'history rewrite receipt and push-collision exception are implemented; future expires_at is an enhancement not core closure'
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-094, ADR-242]
implementation_files:
  - hooks/_lib/push-collision-check.sh
  - scripts/push_collision_detect.py
  - lib/history_sanitization.py
  - tests/behavior/test_push_collision_post_rewrite.py
tier: maintainer
tags: [history-rewrite, push-gates, dx, postmortem-2026-05-08]
---
# ADR-243: Post-Rewrite Push-Collision Check Exception

## Status

Accepted — Slice A implemented. History sanitization writes `.cognitive-os/runtime/last-rewrite.json`; push-collision detection consumes it to allow matching post-rewrite subject collisions without disabling other push gates.

## Context

After a history rewrite (mailmap, sanitize, or text replacement), every
commit on the rewritten branch has the same subject line as before but a
new SHA. The push-collision-check primitive
(`hooks/_lib/push-collision-check.sh` plus
`scripts/push_collision_detect.py`) treats subject-identical commits with
divergent SHAs as a strong signal of accidental duplicate commits and
blocks the push.

This is correct in normal operation. After a deliberate rewrite, it is a
false positive, and a high-cost one: there can be hundreds of subject
collisions on a single rewrite, and there is no way to acknowledge them
in a single gesture.

Observed symptoms on 2026-05-08:

- Force-push after `cos-history-sanitization --execute` was blocked by
  push-collision-check on every rewritten commit.
- The documented bypass envs only worked when pre-set in the harness env;
  inline `DISABLE_HOOK_PUSH_COLLISION_CHECK=1 git push` did not reach the
  PreToolUse hook (the same root issue ADR-241 addresses).
- The operator fell back to `git push --no-verify --force-with-lease`,
  which discarded *every* push-time protection (commit signing checks,
  branch ownership lock, merge-queue gates), not only the collision check.
- No audit trail recorded that a rewrite had occurred, so a separate
  reviewer could not distinguish a benign post-rewrite force-push from
  a destructive one.

## Decision

Introduce a "post-rewrite mode" that the rewrite path writes and the
push-collision check reads.

1. **Write side.** `lib/history_sanitization.py` (and the wrapper from
   ADR-242) writes `.cognitive-os/runtime/last-rewrite.json` containing:
   - `pre_head` — the SHA of `HEAD` before the rewrite,
   - `post_head` — the SHA of `HEAD` after the rewrite,
   - `rewritten_at` — ISO-8601 timestamp,
   - `ttl_seconds` — default 86400 (24 hours),
   - `rules_hash` — the same hash ADR-242 records.
2. **Read side.** `hooks/_lib/push-collision-check.sh` and
   `scripts/push_collision_detect.py` consult this file before raising
   collisions. The post-rewrite exception applies if and only if all of:
   - the file exists and is within `ttl_seconds`,
   - the local `HEAD` SHA equals `post_head`,
   - the upstream `HEAD` SHA equals `pre_head` (i.e. the push is the
     expected first push of the rewrite),
   - the colliding commits are within the rewrite's commit range.
3. **Audit, do not silence.** When the exception applies, the check still
   logs every collision to `agent-heartbeat.jsonl` with the rewrite hash
   as correlation, so the audit trail is preserved. The hook returns
   success rather than failure.
4. **Marker lifecycle.** The marker is cleared on first successful push or
   when its TTL expires, whichever is sooner. A subsequent rewrite
   overwrites it.

## Operational Guide

### What changes for the operator

Before this ADR: after any history rewrite, `git push --force-with-lease` was blocked by push-collision-check on every rewritten commit (same subject, new SHA). The only workaround was `--no-verify`, which disabled all push-time protections simultaneously.

After this ADR: the rewrite toolchain writes `.cognitive-os/runtime/last-rewrite.json`. The push-collision check reads it and admits subject collisions that are within the rewrite's commit range and match the expected pre/post HEAD pair — without disabling any other push gate.

| Scenario | Before | After |
|---|---|---|
| Force-push after `cos-history-sanitization --execute` | blocked by push-collision-check on every commit | allowed when marker matches; other gates remain active |
| Audit trail | no record that collisions were post-rewrite | collisions logged to `agent-heartbeat.jsonl` with `rules_hash` correlation |
| Bypass method needed | `--no-verify` (kills all gates) | no bypass needed; marker file handles it automatically |
| Marker lifetime | n/a | 24 hours or first successful push, whichever is sooner |

### Daily operational pattern

**Normal flow — no operator action required:**

1. Run the history rewrite via `cos-history-sanitization --execute` or `cos-filter-repo-wrap.sh` (see ADR-242).
2. Both tools write `.cognitive-os/runtime/last-rewrite.json` automatically.
3. Run `git push --force-with-lease` as normal — collision-check reads the marker and admits the post-rewrite collisions.
4. After a successful push, the marker is cleared automatically.

**To verify the marker is present before pushing:**
```bash
python3 -c "import json; d=json.load(open('.cognitive-os/runtime/last-rewrite.json')); print(d)"
# Expected fields: pre_head, post_head, rewritten_at, ttl_seconds, rules_hash
```

**If the marker has expired (> 24 hours since rewrite) and push is still blocked:**
```bash
# The TTL has passed; use COS_BYPASS=push_collision (per ADR-241) to admit
# the push, then investigate why the push was delayed
COS_BYPASS=push_collision git push --force-with-lease
```

**To run the acceptance tests:**
```bash
python3 -m pytest tests/behavior/test_push_collision_post_rewrite.py -q
```

### When sources disagree

If the push-collision check blocks despite a valid marker file:

- Verify that the local `HEAD` SHA equals `post_head` in the marker. If they differ, another commit landed after the rewrite and the marker no longer describes the current state.
- Verify that the upstream `HEAD` equals `pre_head`. If upstream has been updated by another push since the rewrite, the expected pre/post correlation is broken.
- In either case the correct action is to re-run the rewrite against the updated base, not to bypass the collision check.

If the push succeeds but you expected it to be blocked (i.e., the marker was stale or mismatched):

- Check `agent-heartbeat.jsonl` for the most recent push-collision entry and its `rewrite_hash` field. An admission without a matching hash indicates a logic gap; file a follow-up issue.

## Alternatives rejected

- **Always allow force-push after a rewrite without an audit entry** —
  rejected because it removes the operator's ability to retrospectively
  see that subject-identical commits were intentional, not accidental.
- **Require the operator to pass `--allow-rewrite` on the push command** —
  rejected because most operators reach for `--no-verify` first; the goal
  is to remove the incentive to bypass *all* gates to avoid one.
- **Cache acknowledged collisions in Engram and ask interactively per
  commit** — rejected because rewrites can produce hundreds of collisions
  and an interactive loop is a worse UX than a documented marker file.
- **Disable push-collision-check entirely after any rewrite for the life
  of the branch** — rejected because the protection should re-engage as
  soon as the rewrite is upstream, which is what the marker TTL achieves.

## Consequences

### Positive

- Force-push after a deliberate rewrite no longer requires `--no-verify`,
  so the other push-time protections stay engaged.
- The audit trail still records the colliding commit set, with a
  correlation hash that links it to the rewrite that produced it.
- Reviewers can distinguish a post-rewrite push from a regression because
  the marker file is part of the recovery artifact set from ADR-242.

### Negative

- A 24-hour TTL is a window in which a non-rewrite force-push could match
  the marker conditions and be admitted; the conjunction
  (`pre_head` upstream + `post_head` local + commit range) makes this
  narrow but not impossible.
- One more file under `.cognitive-os/runtime/` to manage at session end.
- Two hooks (the bash and python paths) must stay in sync on the
  exception logic.

## Acceptance criteria

1. After `cos-history-sanitization --execute`,
   `.cognitive-os/runtime/last-rewrite.json` exists with all required
   fields and a future `expires_at`.
2. With the marker present and matching, `git push --force-with-lease`
   succeeds without `--no-verify` even when subject collisions exist.
3. Without the marker, push-collision-check still blocks on the same
   collisions.
4. After a successful push, the marker is cleared.
5. `tests/behavior/test_push_collision_post_rewrite.py` covers:
   marker-match success, marker-expired fallback, marker-mismatch
   fallback, audit-entry presence on success.

## Verification

```bash
python3 -m pytest tests/behavior/test_push_collision_post_rewrite.py -q
test -f .cognitive-os/runtime/last-rewrite.json && \
  python3 -c "import json,sys; json.load(open('.cognitive-os/runtime/last-rewrite.json'))"
```
