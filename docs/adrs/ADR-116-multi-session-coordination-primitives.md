---
adr: 116
title: Multi-Session Coordination Primitives
status: accepted
date: 2026-05-02
supersedes: []
superseded_by: null
implementation_files:
  - lib/task_claim_ledger.py
  - hooks/agent-prelaunch.sh
  - lib/session_lifecycle.py
  - lib/merge_queue.py
  - scripts/cos_coordination_status.py
  - scripts/so-reaper.sh
  - scripts/cos_work_inventory.py
tier: strict
tags: [coordination, multi-session, concurrency, primitives]
---

# ADR-116 — Multi-Session Coordination Primitives

<!-- SCOPE: OS -->

**Status**: Accepted — transactional rollout in progress
**Date**: 2026-05-02
**Author**: Maintainer (operator) + Software Architect (analysis)
**Related**: ADR-088 (provenance markers), ADR-089 (multi-session git coordination), ADR-098 (multi-agent file edit-locks), ADR-099 (pre-agent snapshot copy-on-untracked), ADR-102 (task-tracker lifecycle), ADR-105 (bilateral claim verification contract), ADR-106 (multi-session safety primitives), ADR-108 (concurrent-agent safety layer), ADR-109 (validation capsule worktree isolation), ADR-110 (preserve-branch governance), ADR-113 (validation capsule liveness), `docs/incidents/2026-05-02-false-done-compounding.md`, `docs/architecture/multi-session-orchestration-audit-2026-05-02.md`

## Status

Accepted (2026-05-02). Formalizes the full set of primitives required to make concurrent Claude Code / Codex / operator sessions safe on `main`. Composes on top of ADR-098/099/105/106/108/109/110/113. Each primitive is independently deployable behind a feature flag.

## Context

Today (2026-05-02) two of my own commits became orphaned because a parallel session rebased them away. Verified:

- Commits `173bcae1` and `3f5932d6` exist as objects (`git cat-file -e` succeeds) but are not reachable from any branch (`git branch --contains` returns empty). Equivalent content was re-applied by a parallel session as `52380c52` and `781e2c79` — recovery happened by accident, not by design.
- A sub-agent's claim-gate fix to `packages/verification-audit/lib/orchestrator_verify.py` was wiped from the working tree by a parallel `git pull --rebase origin main` before it could land. It was re-applied later as `f4e4ddd1` only because the operator noticed the diff disappeared.
- `.git/index.lock` was held for ~2 hours by a dead process earlier in the day, blocking commits across the whole repo until manual `rm`.
- 17 pending tasks accumulated in `dispatch-queue.json` with no claim coordination — multiple sessions picked the same items, visible as duplicate task IDs in `active-tasks.json`.
- Task `b1de3c40` (task-tracker-lifecycle from ADR-102) reaped 56 zombie task records but did not prevent duplicate claims at submission time.

ADR-098 covers within-session file edit-locks. ADR-099 covers untracked-file snapshots. ADR-105 covers bilateral claim verification at the orchestrator/sub-agent boundary. ADR-106 covers stash-leak alarms, plan-file advisory locks, commit provenance trailers, and bilateral-gate orchestrator behavior. ADR-108/109/110/113 cover the validation capsule and preserve-branch governance. None of these compose into a complete multi-session coordination contract: there is no task-claim ledger, no work-identity fingerprinting, no inter-session pub/sub, no stale-task watermark, no per-session branches by default, no merge queue, no orphan-commit notifier, no `git reset --hard` protection layer, no coordination-status CLI, no pre-commit content-hash dedupe, no push-time collision detection, no engram-as-claims source-of-truth, no cross-session advisory lock via engram. This ADR formalizes those 12 primitives.

## Decision

Twelve primitives organized into six layers (L1 Detection / L2 Coordination / L3 Isolation / L4 Telemetry / L5 Idempotency / L6 Shared evidence). L1 is already in place via ADR-088/098/099/105 + `commit_provenance.py`; this ADR is the gap-closure for L2–L6.

---

### P1.1 — Task-claim ledger

- **Layer**: L2 Coordination
- **Problem (concrete failure mode)**: 17 dispatch-queue tasks were picked by multiple sessions today; duplicate task IDs surfaced in `active-tasks.json`. The reaper from ADR-102 cleaned up after the fact but never blocked the second claim at submission time.
- **Decision**: introduce `.cognitive-os/tasks/active-claims.json` with the schema `{task_id, session_id, claimed_at, expected_files, fingerprint, ttl}`. Writes are guarded by an `flock`-protected helper `scripts/claim_task.py`. A claim is rejected if `task_id` already has an unexpired claim from a different `session_id`. Claims are released on completion or TTL expiry.
- **Artifacts to create**: `scripts/claim_task.py`, `.cognitive-os/tasks/active-claims.json` (runtime), `lib/task_claim_ledger.py`, hook `hooks/pre-dispatch-claim.sh`.
- **Effort**: M (~1 day).
- **Acceptance criteria**: `tests/contracts/test_task_claim_ledger.py::test_duplicate_claim_rejected` — when session A claims task T and session B attempts to claim T within TTL, B receives exit code 2 with holder metadata.
- **Supersedes/related**: extends ADR-102 (lifecycle reaper), composes with ADR-098 (file edit-locks).

---

### P1.2 — Work-identity fingerprinting

- **Layer**: L5 Idempotency (entry surface lives in L2)
- **Problem (concrete failure mode)**: parallel session re-applied the same content as `52380c52` and `781e2c79` after my orphaned commits — neither session knew the other had already produced equivalent output.
- **Decision**: before commit, compute `fingerprint = sha256(task_id || normalized_diff_of_expected_outputs)`. If a commit on `origin/main` (last 200 commits) carries the same fingerprint trailer, abort. Trailer format: `X-COS-Work-Fingerprint: <sha256>`.
- **Artifacts to create**: `lib/work_fingerprint.py`, hook `hooks/pre-commit-fingerprint.sh`, trailer documented in ADR-088 successor table.
- **Effort**: M (~1 day).
- **Acceptance criteria**: `tests/contracts/test_work_fingerprint.py::test_duplicate_fingerprint_aborts` — second commit with identical fingerprint returns exit code 3 with the matching commit SHA.
- **Supersedes/related**: composes with P1.1 (claim → fingerprint), P4.1 (patch-id dedupe is a complementary but different signal).

---

### P1.3 — Inter-session pub/sub bus

- **Layer**: L2 Coordination
- **Problem (concrete failure mode)**: today's two orchestrator sessions (X-COS-Session 1777732313 / 1777731331) had no signaling channel. Each was blind to the other's claims, commits, and rebases until git history surfaced the divergence post-hoc.
- **Decision**: append-only `.cognitive-os/sessions/events.jsonl` written by every session on `claim`, `commit`, `rebase`, `force-push-attempt`, `release-claim`. Tail-watcher `scripts/session_event_watcher.py` (one per session, started by SessionStart hook) fans events to in-session listeners. Schema: `{ts, session_id, event_type, payload}`. File rotated daily; >7-day archives moved to `.cognitive-os/sessions/archive/`.
- **Artifacts to create**: `scripts/session_event_watcher.py`, `lib/session_bus.py`, hook `hooks/session-start-bus.sh`.
- **Effort**: M (~1 day).
- **Acceptance criteria**: `tests/integration/test_session_bus.py::test_event_visible_to_second_session` — event written by session A is observed by session B's watcher within 2s.
- **Supersedes/related**: prerequisite for P1.4 (stale-task watermark needs the bus to react in real time).

---

### P1.4 — Stale-task watermark

- **Layer**: L4 Telemetry (with L2 side effects)
- **Problem (concrete failure mode)**: when a parallel session completes the same work, the originating session's task record stays `pending` until the reaper runs. This is exactly the failure that produced the duplicate claims today.
- **Decision**: extend `so-reaper.sh` to subscribe to P1.3 events. On every `commit` event with `expected_outputs` matching a `pending` task in any session's `tasks.json`, mark that task `done-by-other-session` with cross-reference `done_by_commit` and `done_by_session_id`.
- **Artifacts to create**: extension to `scripts/so-reaper.sh`, new field in `tasks.json` schema (`done_by_session_id`, `done_by_commit`).
- **Effort**: S (~4h).
- **Acceptance criteria**: `tests/integration/test_stale_watermark.py::test_other_session_completion_marks_done` — when session B commits content matching session A's expected outputs, A's task record transitions within 1 reaper cycle.
- **Supersedes/related**: extends ADR-102 reaper, requires P1.3.

---

### P2.1 — Per-session branches by default

- **Layer**: L3 Isolation
- **Problem (concrete failure mode)**: today's orphaned commits (`173bcae1`, `3f5932d6`) happened because two sessions wrote directly to `main`. A rebase from one session detached the other's commits.
- **Decision**: `SessionStart` creates or recommends a session branch for multi-session work. Local enforcement is actor-aware: autonomous agents/sub-agents are blocked from committing directly on `main`/`master`, while operator commits on `main` warn by default and can be escalated to block with `COS_OPERATOR_MAIN_POLICY=block`. `COS_ALLOW_DIRECT_MAIN=1` remains a one-off emergency bypass.
- **Remote invariant**: local warnings are UX, not the safety boundary. The authoritative guarantee is the vendor-neutral protected landing contract in `docs/architecture/protected-landing-contract.md`: `main`/`master` must be advanced by provider-native protection, server-side Git hooks, or COS merge-queue/pre-push fallback according to remote capabilities.
- **Artifacts to create/update**: `hooks/direct-main-guard.sh`, hook projections, `scripts/cos-session-branch.sh`, `lib/session_branch.py`, `docs/architecture/direct-main-policy.md`, and `docs/architecture/per-session-branches.md`.
- **Effort**: L (~2 days, includes settings-driver integration).
- **Acceptance criteria**: `tests/unit/test_direct_main_guard.py` covers agent block, operator warn, strict operator block, bypass, non-main branches, `master`, auto-detected agent env, and ignored non-commit/non-Bash calls. `tests/integration/test_per_session_branch.py::test_subagent_cannot_commit_to_main` covers the SessionStart branch workflow once P2.1 branch switching is default-on.
- **Supersedes/related**: composes with ADR-110 (preserve-branch governance), ADR-109 (worktree isolation — see open question below on overlap).

---

### P2.2 — Merge queue / landing pipeline

- **Layer**: L3 Isolation
- **Problem (concrete failure mode)**: there is no single-writer to `main` today. Concurrent rebase + commit sequences are what produced the orphaned commits.
- **Decision**: `scripts/merge-to-main.sh` is the only sanctioned path to update `main`. It acquires `.cognitive-os/runtime/main-merge.lock` via `flock`, runs all gates (P1.2 fingerprint, P4.1 patch-id, full test lane), and applies atomically with `git push --force-with-lease`. A queue file `.cognitive-os/runtime/main-merge-queue.json` orders pending merges across sessions.
- **Artifacts to create**: `scripts/merge-to-main.sh`, `lib/merge_queue.py`, hook `hooks/pre-merge-gate.sh`.
- **Effort**: L (~2 days).
- **Acceptance criteria**: `tests/integration/test_merge_queue.py::test_serialized_main_writes` — two concurrent invocations of `merge-to-main.sh` are serialized; the second waits and re-validates against the new `main` HEAD before applying.
- **Supersedes/related**: prerequisite for P2.1 to provide value (per-session branches without a merge queue just defers the race).

#### P2.2a — Remote protection boundary

- **Layer**: L3 Isolation
- **Problem**: local hooks can be bypassed intentionally or accidentally, especially by operator terminal workflows.
- **Decision**: `main`/`master` must use the vendor-neutral protected landing contract. Provider-native branch protection/merge queues are preferred when available, server-side Git hooks are the strongest portable self-hosted mechanism, and COS local merge queue + pre-push gates are the fallback for unknown/unsupported remotes. GitHub is one adapter, not a requirement.
- **Acceptance criteria**: a direct `git push origin main` from a non-queue actor is rejected by the strongest available protection layer, while queue/bot landing succeeds after required gates. If remote enforcement is unavailable, status/documentation must report local-only fallback rather than claiming remote protection.

---

### P2.3 — Validation capsule full mode (default-on)

- **Layer**: L3 Isolation
- **Problem (concrete failure mode)**: ADR-109 worktree isolation exists but is not default-on. The sub-agent claim-gate fix that was wiped today happened in the operator's main worktree precisely because no capsule isolated it.
- **Decision**: flip `multi_session.validation_capsule.full_mode` default to `true` in `cognitive-os.yaml`. Every sub-agent dispatch runs in a worktree-isolated capsule (ADR-109) with liveness checks (ADR-113). Operator-direct edits remain in the main worktree.
- **Artifacts to create**: config flip in `cognitive-os.yaml`, migration note in `docs/architecture/validation-capsule-rollout.md`.
- **Effort**: S (~4h, mostly defaults + doc; primitives already exist).
- **Acceptance criteria**: `tests/integration/test_capsule_default_on.py::test_subagent_runs_in_capsule` — fresh install dispatches sub-agent in a worktree distinct from `pwd`.
- **Supersedes/related**: ADR-109, ADR-113 (this ADR is the rollout decision, not new mechanism).

---

### P3.1 — Orphan-commit notifier

- **Layer**: L4 Telemetry
- **Problem (concrete failure mode)**: today's `173bcae1` and `3f5932d6` were detected only by chance via manual `git cat-file -e` + `git branch --contains`. There was no automatic alarm.
- **Decision**: `hooks/post-rebase-orphan-scan.sh` runs after every rebase / pull --rebase. It diffs reflog before/after, identifies commits no longer reachable from any branch, and writes to `.cognitive-os/runtime/orphan-commits.jsonl` + emits to P1.3 bus + saves to engram under topic `orphan-commit/<sha>`.
- **Artifacts to create**: `hooks/post-rebase-orphan-scan.sh`, `lib/orphan_detector.py`.
- **Effort**: S (~4h).
- **Acceptance criteria**: `tests/integration/test_orphan_notifier.py::test_rebase_orphan_detected` — rebase that drops a commit produces an entry in `orphan-commits.jsonl` and an engram observation.
- **Supersedes/related**: composes with P1.3.

---

### P3.2 — `git reset --hard` protection layer

- **Layer**: L4 Telemetry
- **Problem (concrete failure mode)**: the sub-agent's `orchestrator_verify.py` claim-gate fix was wiped by a parallel `git pull --rebase` that effectively reset the working tree state. There was no auto-stash or reflog snapshot.
- **Decision**: `hooks/pre-destructive-git.sh` intercepts `git reset --hard`, `git checkout -- .`, `git restore .`, and `git pull --rebase` when the working tree is dirty. It auto-stashes (with the ADR-099 mechanism), records a reflog snapshot, runs a WIP-presence check, and requires explicit operator approval (`COS_ALLOW_DESTRUCTIVE=1`) for sub-agent invocations.
- **Artifacts to create**: `hooks/pre-destructive-git.sh`, `lib/destructive_git_guard.py`.
- **Effort**: M (~1 day).
- **Acceptance criteria**: `tests/contracts/test_destructive_git_guard.py::test_dirty_tree_blocked` — sub-agent invoking `git reset --hard` with dirty tree is blocked; auto-stash created; reflog snapshot saved.
- **Supersedes/related**: composes with ADR-099 (snapshot infra reused).

---

### P3.3 — Coordination-status CLI

- **Layer**: L4 Telemetry
- **Problem (concrete failure mode)**: today, diagnosing the multi-session state required ~10 separate commands (`git stash list`, `git reflog`, `cat active-tasks.json`, `cat sessions/*.json`, `git worktree list`, etc.). No single view exists.
- **Decision**: `scripts/cos-coordination-status.sh` produces a single report: active sessions, active claims, unapplied stashes, orphan commits, worktrees, dispatch-queue depth, race-risk score. Output JSON + human-readable. This is Phase 0 — it ships first because it is the visibility primitive the other phases need to validate.
- **Artifacts to create**: `scripts/cos-coordination-status.sh`, `lib/coordination_status.py`.
- **Effort**: S (~4-6h).
- **Acceptance criteria**: `tests/integration/test_coordination_status.py::test_full_report` — script returns exit 0 with all 7 sections populated; race-risk score ∈ [0,1].
- **Supersedes/related**: this is the read-side companion to every other primitive.

---

### P4.1 — Pre-commit content-hash dedupe

- **Layer**: L5 Idempotency
- **Problem (concrete failure mode)**: today's `52380c52` and `781e2c79` re-applied the same diff already produced by `173bcae1`/`3f5932d6`. `git patch-id` would have detected this had it been consulted.
- **Decision**: `hooks/pre-commit-patch-id.sh` runs `git patch-id` on the staged diff and compares against `git log --format=%H origin/main -200 | git patch-id --stable`. On match, abort with the matching SHA + suggest `git cherry-pick` instead.
- **Artifacts to create**: `hooks/pre-commit-patch-id.sh`, `lib/patch_id_dedupe.py`.
- **Effort**: S (~4h).
- **Acceptance criteria**: `tests/contracts/test_patch_id_dedupe.py::test_duplicate_patch_aborts` — committing a diff equivalent to an existing commit aborts with exit 4.
- **Supersedes/related**: complementary to P1.2 (fingerprint = task+outputs; patch-id = raw diff). Both fire to catch different equivalence classes.

---

### P4.2 — Push-time collision detection

- **Layer**: L5 Idempotency
- **Problem (concrete failure mode)**: when a session's commits are about to push but `origin/main` has gained equivalent content from another session, today nothing flags it. Result: orphaned commits or duplicate landing.
- **Decision**: `hooks/pre-push-collision.sh` scans unpushed commits for subject-line collision with last 200 commits on `origin/main` (post-fetch). On subject match, diff content; on content match, abort with rebase suggestion. On subject-only match, warn.
- **Artifacts to create**: `hooks/pre-push-collision.sh`, `lib/push_collision_detector.py`.
- **Effort**: S (~4h).
- **Acceptance criteria**: `tests/contracts/test_push_collision.py::test_subject_match_warns` and `test_content_match_aborts`.
- **Supersedes/related**: existing pending task `task-1777744271-22763` ("Force-push blocking + commit-msg false-pos fix") covers part of this surface.

---

### P4.3 — Stash provenance auto-reapply

- **Layer**: L5 Idempotency
- **Problem (concrete failure mode)**: ADR-099 records stash provenance, but on subsequent SessionStart of the same `session_id`, there is no auto-reapply policy. Today's claim-gate fix that was wiped is the prototype: it lived in a stash and never came back without manual `git stash pop`.
- **Decision**: extend `pre-agent-snapshot.sh` provenance file (`auto-pre-agent-<hash>`) with `session_id`, `agent_id`, `original_files[]`, `created_at`. SessionStart hook checks for stashes with matching `session_id` and offers reapply (interactive) or auto-reapplies if `COS_AUTO_REAPPLY_STASH=1` and no working-tree conflict.
- **Artifacts to create**: extension to `hooks/pre-agent-snapshot.sh`, new `hooks/session-start-stash-reapply.sh`, `lib/stash_provenance.py`.
- **Effort**: M (~1 day).
- **Acceptance criteria**: `tests/integration/test_stash_reapply.py::test_same_session_id_reapplies` — SessionStart with matching session_id and clean tree auto-reapplies the matching stash.
- **Supersedes/related**: extends ADR-099, complements ADR-106 P1 (stash-leak alarm — that one warns, this one heals).

---

### P4.4 — Atomic plan-checkbox transitions

- **Layer**: L5 Idempotency
- **Problem (concrete failure mode)**: ADR-105 introduced `plan-claim-validator` in advisory mode. Today's incident showed the parser is now hardened enough to flip to block mode without false positives.
- **Decision**: flip `plan-claim-validator` hook to `block` mode in `manifests/hook-quality.yaml`. Any `[ ] → [x]` transition without an inline `(verified: <cmd>)` clause is rejected at commit time. Composes with ADR-106 P2 (plan advisory lock).
- **Artifacts to create**: config flip in `manifests/hook-quality.yaml`; smoke-test updates.
- **Effort**: S (~2h, mostly already done per spec).
- **Acceptance criteria**: `tests/contracts/test_plan_claim_validator_block.py::test_unverified_checkbox_blocks` — commit with unverified `[x]` is rejected.
- **Supersedes/related**: ADR-105 (this is the mode-flip), ADR-106 P2 (plan advisory lock).

---

### P5.1 — Engram as claims source-of-truth

- **Layer**: L6 Shared evidence
- **Problem (concrete failure mode)**: `active-claims.json` (P1.1) is a per-repo JSON file; cross-machine or cross-worktree sessions don't share it. Engram is already cross-session and persistent.
- **Decision**: on claim, write `mem_save topic=claims/<task-id>` with claim metadata. On completion, update with completion metadata. Before claiming, `mem_search topic=claims/<task-id>` — if a live claim from another session exists, defer or abort. Engram is the SoT; the JSON file is the local cache.
- **Artifacts to create**: `lib/engram_claim_store.py`, integration in `scripts/claim_task.py`, doc in `docs/architecture/engram-as-claims-sot.md`.
- **Effort**: M (~1 day).
- **Acceptance criteria**: `tests/integration/test_engram_claims.py::test_cross_worktree_claim_visible` — claim made in worktree A is visible to worktree B via engram.
- **Supersedes/related**: extends P1.1; depends on engram daemon throughput (see open questions).

---

### P5.2 — Cross-session advisory locks via engram

- **Layer**: L6 Shared evidence
- **Problem (concrete failure mode)**: file edit-locks (ADR-098) are filesystem-local. When two sessions run in different worktrees but touch logically the same resource (e.g. an engram observation, a shared service config), filesystem locks don't coordinate.
- **Decision**: `mem_save topic=lock/<resource-uri>` with TTL claims a logical lock. Acquire = save with conditional check that no live lock exists for the same resource by another session. Release = save with `released_at`. TTL auto-expiry built into engram daemon.
- **Artifacts to create**: `lib/engram_advisory_lock.py`, helper `scripts/cos-lock.sh acquire|release|status <resource>`.
- **Effort**: M (~1 day).
- **Acceptance criteria**: `tests/integration/test_engram_advisory_lock.py::test_concurrent_acquire_serialized` — second `acquire` call for the same resource by a different session blocks until release or TTL.
- **Supersedes/related**: complements ADR-098 (filesystem edit-locks); extends P5.1's storage pattern.

---

## Transactional gate rollout

The design is now treated as a set of SO transactions, not agent reminders. The first implementation slice makes these invariants default-on where they are cheap and structural:

1. **Derived-artifact gate**: `scripts/derived_artifact_gate.py` checks `cognitive-os.yaml` registry drift against `manifests/hook-quality.yaml`, `.claude/settings.json`, `.codex/hooks.json`, and Codex/Claude parity. `hooks/pre-commit-gate.sh` invokes it in staged mode so a registry change cannot be committed without regenerated artifacts.
2. **Projection parity**: supported target events are blocking; limited/unsupported harness gaps remain explicit report rows. This keeps ADR-081 honest for non-Bash Codex events instead of blindly copying Claude hooks.
3. **Task-claim ledger**: `lib/task_claim_ledger.py` and `scripts/claim_task.py` provide an atomic local cache for P1.1; Engram remains the future cross-worktree source of truth in P5.1.
4. **Session/event bus**: `lib/session_bus.py` and `scripts/session_event_bus.py` provide the append-only bus required by P1.3 and later stale-task watermarking.
5. **Single-writer landing**: `scripts/merge-to-main.sh` serializes branch landing via `.cognitive-os/runtime/main-merge.lock`, rebases against fresh `origin/main`, runs validation, fast-forwards `main`, and pushes.
6. **Orphan/overwrite detection**: `scripts/orphan_overwrite_detector.py` records unreachable commits or changed paths as corruption evidence and emits to the session bus.

This slice does not claim to finish P1.2/P4.1/P4.2/P5.1/P5.2. It closes the immediate drift class by moving registry/projection correctness from late contract tests into pre-commit/merge gates, and it creates the runtime files that the remaining primitives can compose with.

## Phase plan

| Phase | Primitives | Effort | Blocker for next phase |
|---|---|---|---|
| Phase 0 — Visibility    | P3.3                                | 4-6h    | none — start here    |
| Phase 1 — Coordination  | P1.1, P1.3, P5.1, P5.2              | ~2 days | P3.3 in place        |
| Phase 2 — Idempotency   | P1.2, P4.1, P4.2, P4.4              | ~2 days | P1.1 + P1.3          |
| Phase 3 — Isolation     | P2.1, P2.2, P2.3                    | ~3 days | Phase 2 in place     |
| Phase 4 — Telemetry     | P1.4, P3.1, P3.2, P4.3              | ~2 days | parallel with Phase 3 |

Total wall-clock estimate: ~10 working days for one operator + sub-agents. Phase 0 ships standalone (it provides value even with nothing else changed because it surfaces the current state).

## Out of scope

- Refactoring the orchestrator's task-dispatch internals beyond claim wiring.
- Replacing engram with an alternative store.
- Changing the harness layer (Claude Code / Codex) — all primitives compose on top of harness-provided hooks.
- Cross-machine coordination (assumes single-host today; engram-as-SoT is a stepping stone but multi-host is a separate ADR).
- Any change to ADR-110 preserve-branch governance semantics.

## Migration / rollback

Each primitive lives behind a feature flag in `cognitive-os.yaml` under the `multi_session.*` namespace:

```yaml
multi_session:
  task_claim_ledger: false           # P1.1
  work_fingerprint: false            # P1.2
  session_event_bus: false           # P1.3
  stale_task_watermark: false        # P1.4
  per_session_branches: false        # P2.1
  merge_queue: false                 # P2.2
  validation_capsule_full_mode: false # P2.3
  orphan_commit_notifier: false      # P3.1
  destructive_git_guard: false       # P3.2
  coordination_status_cli: true      # P3.3 — read-only, safe default-on
  patch_id_dedupe: false             # P4.1
  push_collision_detection: false    # P4.2
  plan_validator_block_mode: false   # P4.4 — flip to true after burn-in
  stash_auto_reapply: false          # P4.3
  engram_claims_sot: false           # P5.1
  engram_advisory_locks: false       # P5.2
```

Defaults are `false` until validated against the existing test corpus + one week of operator dogfooding. P3.3 ships default-on because it is read-only.

Reaper (ADR-102) and edit-lock infra (ADR-098) already exist; this ADR composes on top — no rollback required for those layers. Rollback for any primitive = flip flag to `false` and remove hook registration.

## Pending tasks that partially cover this ADR

From `.cognitive-os/tasks/active-tasks.json`:

| Task ID | Description | Primitives partially covered |
|---|---|---|
| `task-1777743348-13779` | Audit multi-session orchestration (cancelled-stale) | P1.3, P2.1 (audit produced gap inventory feeding this ADR) |
| `task-1777744271-22763` | Force-push blocking + commit-msg false-pos fix (cancelled-stale) | P4.2 (partial — covers force-push subset) |
| `task-1777745639-25988` | B: fix claim-gate false positives (pending) | P4.4 (parser hardening that enables block-mode flip) |
| `task-1777747354-32631` | ADR-116 multi-session coordination primitives (pending) | this ADR itself |
| `task-1777575675-30572` | Draft ADR-088 multi-session git coord (completed) | L1 detection foundation |
| `task-1777576238-15849` | Implement ADR-089 multi-session coord (completed) | L1 detection foundation |
| Earlier "work inventory doctor" work (shipped, no live task ID) | precursor of P3.3 — this ADR formalizes and extends it |

## Open questions

1. **Engram daemon throughput for P1.3 + P5.1 + P5.2**: P1.3 emits events on every claim/commit/rebase. P5.1 writes claim observations on every dispatch. P5.2 acquires logical locks for shared resources. Combined throughput at peak (10 sub-agents × 5 events/agent/min) is ~50 writes/min. Not measured. Need a benchmark before flipping these flags default-on.

2. **P2.1 vs ADR-109 worktree isolation overlap**: ADR-109 already isolates sub-agents in worktrees. P2.1 puts sub-agent commits on a session branch. If ADR-109 is default-on (P2.3), is P2.1 redundant? Or do they layer (worktree provides FS isolation, branch provides git-history isolation)? Tentative answer: they layer — worktrees can still write to `main` if not branched. But the cost-benefit of running both default-on needs validation in Phase 3.

3. **P1.2 fingerprint vs P4.1 patch-id**: both detect duplicate work but at different levels (task-bound vs raw-diff). Running both means two abort paths with different error messages. Acceptable, or should one supersede the other? Tentative answer: keep both — fingerprint catches semantic equivalence (same task → same outputs), patch-id catches syntactic equivalence (same diff regardless of task).

4. **P3.2 destructive-git guard scope creep**: should `git push --force` be in the destructive set? It is destructive to `origin/main` reflog but not to local working tree. Likely yes, but interaction with merge-queue (P2.2) needs design.

6. **Effort estimates not historically anchored**: T-shirt sizes above are reasoned estimates, not derived from `lib/cost_predictor.py` historical data. Calibration after Phase 0 ships.


## Alternatives rejected

1. **Keep direct-main multi-session work and rely on manual vigilance.** Rejected because the 2026-05-02 incident showed manual checks happen after orphaned commits, duplicate claims, and wiped fixes have already occurred.
2. **Only add more validation-capsule isolation.** Rejected because worktree isolation reduces filesystem collisions but does not provide task-claim ownership, duplicate-work fingerprints, merge serialization, or cross-session evidence sharing.
3. **Use a heavyweight external queue as the first primitive.** Rejected for reconstruction-phase rollout: the immediate failure class needs repo-local, inspectable primitives first, with Engram-backed coordination added after throughput is measured.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
python3 -m pytest tests/contracts/test_hook_quality_system.py -q
make test-laptop
```

## Consequences

### Positive

- Closes the orphaned-commit class entirely (P1.2 + P4.1 + P4.2 + P3.1).
- Closes the duplicate-claim class entirely (P1.1 + P5.1).
- Wiped-fix class addressed (P3.2 + P4.3).
- Single diagnostic surface for any future incident (P3.3).
- Plan-checkbox false-done class becomes commit-blocked (P4.4 + ADR-105 + ADR-106 P2).

### Negative

- ~12 new flags in `cognitive-os.yaml`. Configuration surface grows.
- Engram becomes a hot-path dependency for P5.1/P5.2. Daemon outage degrades coordination quality (graceful degradation: fall back to filesystem JSON).
- Per-session branches (P2.1) change muscle memory for the operator.

### Neutral

- All primitives are additive and flagged. Phased rollout is the migration plan.

## References

- Incident: `docs/incidents/2026-05-02-false-done-compounding.md`
- Audit: `docs/architecture/multi-session-orchestration-audit-2026-05-02.md`
- ADR-088, ADR-089, ADR-098, ADR-099, ADR-102, ADR-105, ADR-106, ADR-108, ADR-109, ADR-110, ADR-113
- Today's evidence commits: `173bcae1`, `3f5932d6` (orphaned); `52380c52`, `781e2c79` (duplicate re-apply); `f4e4ddd1` (re-applied claim-gate fix); `b1de3c40` (reaper run that cleaned 56 zombies)
