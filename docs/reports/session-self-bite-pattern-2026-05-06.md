# Session Diagnosis — State Retention Self-Bite Pattern — 2026-05-06

## Purpose

This session captured a structural failure mode: Cognitive OS creates safety
state generously and cleans it timidly. The immediate symptom was an ADR-116
preflight block on stale stashes before launching parallel agents, but the same
shape appears across claims, bus folders, metrics, locks, and preserved
worktrees.

This is not a landing-page anecdote. It is a pre-launch reliability risk: the
system correctly preserves work, then later blocks users on its own residue.

## Incident Summary

ADR-116 did the right conceptual thing: it blocked agent launch after finding
stale stashes not tied to an active session. A preflight that ignores hidden WIP
would violate the product's data-preservation promise.

Execution quality was poor:

- the same block surfaced repeatedly across parallel launch attempts;
- the output exposed a large JSON payload instead of one compact operator action;
- the recovery path asked for manual `git stash show` inspection instead of
  presenting a summary and a safe cleanup command;
- the system had evidence that the stashes were stale but no paired reaper.

Local verification during this session found two `auto-pre-agent-*` stashes and
one manual/session WIP stash named `wip-matrix-merge`. That correction matters:
only the auto-generated stashes are safe candidates for an automated cleanup
path. Manual/session stashes must be preserved or reviewed explicitly.

## Surface Map

| Risk | Surface | Evidence level | Pattern |
|---|---|---:|---|
| High | `auto-pre-agent-*` stashes | ✓ observed locally | Agent safety snapshots can outlive the agent/session and later block dispatch. |
| High | Task claims ledger | ✓ observed in flow; implemented as status-marking JSON | Released claims remain as ledger rows unless compacted. |
| High | Preserve worktrees | ⚠ requires focused audit | Preflight knows preserve branch patterns; cleanup must be archive-first. |
| High | Runtime locks | ⚠ partly mitigated by stash-lock tests | Any lock without owner liveness can turn safety into a hard stop. |
| Medium | `.cognitive-os/metrics/*.jsonl` | ⚠ append-only by design | Evidence logs need rotation/archival. |
| Medium | Agent bus folders and heartbeat JSONL | ✓ many local folders exist | Per-agent outputs accumulate beyond recent debugging value. |
| Medium | Error-learning/session JSONL outputs | ⚠ pattern match | Deduplication does not imply retention. |
| Low | Single-file state caches | ✓ bounded by overwrite | `rate-limit-state.json` style surfaces are less likely to self-bite. |

Legend: ✓ means observed in local repository state or code; ⚠ means a candidate
surface that follows the architecture pattern and needs a dedicated audit.

## Root Cause

The default mental model has been "saving is safe." That is true at the moment
of potential data loss. Over multiple sessions, unbounded saving becomes unsafe:
it slows diagnostics, pollutes preflight, and eventually blocks normal work.

The missing primitive is a retention contract. Every mutable state surface needs
a declared kind, age/count budget, reaper, tombstone behavior, and owner-liveness
policy before it can be added to the runtime.

## Decision Created

ADR-199 introduces a universal State Retention Policy and Reaper Protocol. It is
backed by:

- `manifests/state-retention.yaml` — machine-readable retention declarations;
- `scripts/state_retention_audit.py` — retention drift audit and safe reaper;
- `hooks/state-retention-audit.sh` — session-end/read-only retention summary;
- `cos state retention` — operator audit entrypoint;
- `cos stash cleanup` — archive-first cleanup for stale auto-pre-agent stashes.

## Operator Rule From This Session

Do not drop all stashes just because preflight calls them stale. First classify
provenance:

- `auto-pre-agent-*`: cleanup candidate after archive-ref-and-patch tombstone;
- manual/session stash names: review or preserve explicitly;
- unknown stash names: treat as user WIP.

## Acceptance Criteria

```text
ACCEPTANCE CRITERIA:
1. A manifest declares retention policy for stashes, claims, tasks, agent bus folders, metrics, locks, and preserve worktrees.
2. A read-only audit reports retention drift without blocking normal session close.
3. `cos stash cleanup` previews stale auto-pre-agent cleanup by default.
4. `cos stash cleanup --execute` archives patch/name-status/ref before dropping stale auto-pre-agent stashes.
5. Manual/session stashes are not selected by the auto-pre-agent cleanup path.
```
