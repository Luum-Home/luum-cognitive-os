# ADR-223 — Agent Lifecycle Reconstruction: Worktree-Per-Write-Agent

<!-- SCOPE: OS -->

**Status**: Accepted — Slice A implemented (2026-05-07)
**Date**: 2026-05-07
**Related**: ADR-213 (preflight before snapshot), ADR-219 (work ownership), ADR-220 (worktree divergence audit), ADR-221 (stash refs by SHA), ADR-222 (two-phase capture tactical mitigation), ADR-226 (event-sourced session bus), ADR-227 (shadow-git checkpoint substrate), ADR-224 (shadow-state snapshots)
**Source**: `docs/research/multi-agent-orchestration-prior-art-2026-05-06.md`, `docs/research/orchestration-gaps/background-agent-patterns.md`, and the operator incident where auto-pre-agent stashes hid WIP after blocked launches.
**Evaluation contract**: `manifests/orchestration-research-evaluation.yaml` — C1/C2/C3/C4.

---

## Context

COS historically protected the operator worktree by running `pre-agent-snapshot.sh` before write-capable agent launches. That hook captures tracked modifications with `git stash push --keep-index` and restores after `PostToolUse`. This was well-intentioned but structurally fragile:

- If a later preflight blocked, `PostToolUse` did not run and the stash became orphaned.
- `git stash` is a mutable global stack; even with ADR-221 SHA identity, it is still a shared mutable coordination surface.
- Agents and operators can observe different states when linked worktrees are stale or hidden WIP lives in stashes.
- Prior-art research shows mature systems isolate write agents in their own worktree/VM/sandbox instead of mutating the operator worktree for setup.

ADR-222 remains a tactical mitigation while stash-based snapshots exist. ADR-223 is the structural replacement.

## Decision

Introduce a write-agent lifecycle lane that creates a dedicated git worktree for write-capable agents before launch and instructs the agent to operate there. In that lane, `pre-agent-snapshot.sh` is suppressed because the safety boundary is the isolated worktree, not a stash of the operator worktree.

Slice A is **opt-in** via `COS_AGENT_LIFECYCLE_MODE=worktree`. This avoids changing all harness behavior before the lifecycle lane has production telemetry.

## Slice A behavior

1. `scripts/cos-agent-worktree-prepare` creates a dedicated worktree from current `HEAD` under a sibling `.cos-agent-worktrees/<repo>/<task-slug>/` directory.
2. Worktree creation is serialized by `.cognitive-os/runtime/agent-worktree-add.lock` to avoid concurrent `git worktree add` races.
3. `hooks/agent-prelaunch.sh`, when `COS_AGENT_LIFECYCLE_MODE=worktree` and the subagent is write-capable, calls the prepare script and emits `hookSpecificOutput.additionalContext` with the target working directory.
4. The same hook writes `COS_SUPPRESS_AGENT_SNAPSHOT=1` intent via a runtime marker for that task.
5. `hooks/pre-agent-snapshot.sh` exits early for matching runtime markers, so write-agent launch no longer creates auto-pre-agent stashes in this lane.

## Hard rules

- Read-only agents do not get write-agent worktrees.
- Worktree branch names and paths are sanitized from task IDs; no prompt text becomes a path without slugging.
- The parent/operator worktree is never stashed by the worktree lifecycle lane.
- `git worktree add` is serialized under a COS runtime lock.
- The lane remains opt-in until smoke tests cover the real launch paths for supported harnesses.

## Test matrix

- T1 unit: lifecycle path/branch slugging and manifest generation.
- T3 behavior: `cos-agent-worktree-prepare --json` creates a real worktree and manifest.
- T4 smoke: PreToolUse Agent hook in worktree mode emits WORKING DIR context and `pre-agent-snapshot.sh` does not create stashes.
- T7 chaos: future slice — interrupted worktree add leaves a recoverable manifest/lock state.
- T10 audit invariants: operator worktree stash count does not increase in worktree lifecycle mode.

## Implementation status

- **2026-05-07 — Slice A implemented**: opt-in worktree-per-write-agent preparation and snapshot suppression markers.
- **Deferred**: default-on lifecycle mode, automatic cleanup/reaper, branch-per-task policy (ADR-225), shadow-state snapshots (ADR-224/227), cross-harness launch projection.
