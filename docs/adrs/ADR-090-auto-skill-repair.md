---
adr: 90
title: Auto-skill repair via failure-threshold signals
status: accepted
implementation_status: partial
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit pending/deferred/planned scope
---

# ADR-090: Auto-skill repair via failure-threshold signals

**Status**: Accepted
**Date**: 2026-04-30
**Author**: Maintainer (COS sub-agent)
**Engram topic keys**: `cos/learning-loop-final-30pct`, `cos-learning-loop-wiring-audit`, `cos/tier-0-learning-loop-closure`

---

## Status

Accepted.

## Context

The COS learning loop was ~70% complete after the Tier-0 closure sprint
(2026-04-30). Three gaps remained. This ADR addresses **gap #1**: no
automated response when a skill degrades.

`hooks/skill-feedback-tracker.sh` (registered in the same sprint) writes one
JSONL line per skill invocation to
`.cognitive-os/metrics/skill-feedback.jsonl`:

```jsonl
{"timestamp":"2026-04-30T16:10:06Z","skill":"my-skill","success":false}
```

Without a consumer, this data accumulated silently. A human had to notice the
`SKILL DEGRADED` warning printed to stderr by the tracker hook and then
manually decide what to do. That broke the autonomous-learning promise.

### Relationship to existing repair infrastructure

`hooks/_lib/auto-repair-dispatcher.sh` handles *agent-level* auto-repair
(crashes, failed tool calls). It is distinct from skill-level repair: a skill
failure is a degradation of the OS's skill catalog, not a transient tool
error. The two systems coexist without overlap.

`skills/optimize-skill/SKILL.md` improves a skill's *prompt quality*. It is a
manual skill. This ADR's repair queue may delegate to it for `investigate`
cases but does not replace it.

---

## Decision

Implement a **detect → signal → gated action** pipeline:

1. **Detect** (new): `lib/skill_failure_repair.py` reads
   `skill-feedback.jsonl` and identifies skills with ≥ 5 failures in the
   last 24 hours. Returns a structured list with failure counts and error
   samples.

2. **Signal** (new): `hooks/skill-failure-monitor.sh` fires at the `Stop`
   event (session end), calls the Python module, and appends repair signals
   to `.cognitive-os/metrics/skill-repair-queue.jsonl`:

   ```jsonl
   {"timestamp":"…","skill":"x","failure_count":5,"sample_errors":[],"suggested_action":"investigate","status":"pending"}
   ```

   A 5-minute cooldown (stored in `.cognitive-os/runtime/skill-failure-monitor-last`)
   prevents redundant analysis across multiple rapid stops.

3. **Gated action** (new): `skills/repair-skill/SKILL.md` is invoked
   explicitly by the user (or by `/queue-drain`) and reads the next pending
   queue entry. It then delegates to `/add-skill`, `/skill-creator`, or
   `/optimize-skill` based on `suggested_action`.

**Auto-regeneration is deliberately NOT wired.** The act-on-signal step
requires a human or explicit invocation.

### `suggested_action` heuristic

| Condition | Action |
|-----------|--------|
| All failures share the same error string | `regenerate` |
| Failures have varied error strings | `investigate` |
| No successful run in the last 7 days | `deprecate` |
| No error metadata available | `investigate` (conservative default) |

---

## Rationale

### Why signal-first, not direct auto-regeneration?

**Cost gate**: regeneration is an LLM call (Sonnet, ~$0.04/10K tokens for
context + skill output). Firing it automatically for every threshold crossing
could produce several unexpected charges per session.

**Runaway-loop prevention**: if the regenerated skill is still broken, it
produces more failures, which would trigger another regeneration. The
signal-queue pattern breaks the loop: a human or gated consumer can inspect
the queue before acting.

**Visibility**: the queue file is a plain JSONL that can be grepped, audited,
and archived. Invisible auto-actions are harder to reason about.

### Why threshold = 5, window = 24h?

- Threshold = 3 produces false positives in flaky environments (one bad
  session with retries can exceed it). Five is empirically more stable.
- 24-hour window aligns with the `skill-feedback-tracker.sh` existing
  warning (which also uses 24h) and matches the daily review cadence.

### Why Stop event (not PostToolUse/Agent)?

The `Stop` event fires once per session, keeping per-turn overhead near zero.
PostToolUse/Agent fires on every tool call — running JSONL analysis there
would add latency to every response.

---

## Consequences

### Positive

- Skill degradation is detected automatically without human polling.
- The repair queue is visible, auditable, and replayable.
- No runaway LLM loops.
- Fits within the existing hook infrastructure; no new event types needed.

### Negative

- The queue accumulates if no one drains it. Users who do not run
  `/repair-skill` or `/queue-drain` will see stale entries. A future
  improvement could add a session-start check that warns about queue depth
  (similar to how `repair-status` warns about pending repairs).
- The 5-minute cooldown means that if a skill fails massively within one
  session the signal is only emitted once per stop event, not once per
  failure. This is intentional (deduplication) but means the queue entry's
  `failure_count` reflects what was captured at analysis time, not real-time.

### Follow-up

- ADR-095 (Proposed): skill synthesis from success patterns — the inverse
  signal path.
- ADR-096 (Proposed): review-agent pattern — active auditing by a second
  agent.
- Future: add session-start hook that prints "N skill repairs pending — run
  /repair-skill to process" when queue depth > 0.

---

## Alternatives rejected

| Alternative | Reason rejected |
|-------------|-----------------|
| Direct auto-regeneration on threshold cross | Runaway loop risk + unexpected cost |
| Threshold N = 3 | Too many false positives in flaky environments (e.g. network-dependent skills) |
| Periodic cron job | Adds cron dependency; Stop event already provides a natural boundary |
| Extend `auto-repair-dispatcher.sh` | That hook handles agent-level errors; conflating it with skill degradation mixes two distinct concerns |

---

## Files introduced

| File | Purpose |
|------|---------|
| `lib/skill_failure_repair.py` | Detection and signal-emission logic |
| `hooks/skill-failure-monitor.sh` | Stop-event hook that calls the Python module |
| `skills/repair-skill/SKILL.md` | Gated consumer skill for queue entries |
| `tests/unit/test_skill_failure_repair.py` | 19 unit tests covering all three public functions |

## Verification

Run the focused contract for this decision:

```bash
python3 -m pytest tests/behavior/test_self_improvement.py -q
```
