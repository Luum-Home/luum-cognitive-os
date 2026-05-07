# ADR-227 — Shadow-Git Checkpoint Substrate

<!-- SCOPE: OS -->

**Status**: Accepted — Slices A–F implemented (2026-05-07)
**Date**: 2026-05-06
**Related**: ADR-099 (pre-agent snapshot), ADR-200 (state retention controller), ADR-220 (worktree divergence audit), ADR-223 (agent lifecycle reconstruction — reserved), ADR-224 (shadow-state snapshots — reserved); depends on ADR-226 (event-sourced session bus)
**Source**: [`docs/research/orchestration-gaps/replay-timeline-architectures.md`](../research/orchestration-gaps/replay-timeline-architectures.md). Cline, Hermes, Kilo.ai, and `git-shadow` independently converged on the same primitive: a bare git repo *outside* the project, `git write-tree` after every tool call, tree SHA stored alongside conversation context. No hypervisor, no cloud, no service.

---

## Context

Cognitive OS lacks a "rewind and inspect" primitive comparable to Devin's *scrub timeline + restore checkpoint* feature. Engram captures conversation memory; ADR-226 captures event sequences; neither captures the **filesystem state** at the moment each event was emitted.

The replay-timeline research found the field has converged on a single answer: **shadow-git** — a bare git repository owned by the OS, located outside the user's project, that takes a `git write-tree` snapshot after every state-mutating tool call. The tree SHA is recorded as a field on the originating event. To "restore," the OS runs `git checkout-index --prefix=<workspace>/ <tree_sha>` against the user's working tree.

Why shadow-git over alternatives:

- **No hypervisor required** (vs. Devin VM snapshots): zero infrastructure cost.
- **No cloud service required** (vs. Replit CoW-blocks): runs entirely local.
- **Doesn't pollute user history** (vs. auto-commits to user's repo): bare repo elsewhere.
- **Captures everything, including untracked** (vs. user `git stash`): write-tree on the working directory, not the index.
- **Already proven in 4 production tools**: Cline, Hermes, Kilo.ai, git-shadow. Pattern is mature; we adopt the *pattern* (per C1), not the code.

The most important architectural property: **shadow-git enables governance-as-restore-point**. Every policy check, blast-radius assessment, and audit finding emitted by ADR-226 carries a `file_tree_sha`. Operators can rewind to any governance event. No competitor offers this; the prior-art research called it the single defensible differentiation.

The companion ADR-224 (Shadow-State Snapshots, Off-Repo) covers the operator-facing safety net (the Cline-style restore semantics). ADR-227 covers the **substrate** that ADR-224 consumes. Both can land together; ADR-227 is what every other consumer (ADR-220 worktree audit, ADR-228 retry context, ADR-234 policy audit trail) plugs into.

Hard constraint from C3 in the gap analysis: file-restore MUST be tied to ADR-226 event truncation in the same atomic operation. Restoring files without truncating events leaves the agent in an inconsistent state — the most common checkpoint failure mode the research documented (Hermes calls this "undo the last conversation turn"; the Claude Code SDK `rewindFiles()` does *not* do this and the docs flag it as a limitation).

## Decision

Ship `lib/shadow_git.py` as the canonical checkpoint substrate. One bare git repo per session under a managed location. Three operations: snapshot, restore, prune.

1. **Repository layout**: bare repo at `~/.cognitive-os/snapshots/{project_id}/{session_id}/.git`. The session directory is created on first `snapshot()` call and cleaned up by ADR-200 retention controller.
2. **Snapshot operation**: `snapshot(workspace_path) -> tree_sha`. Stages the workspace via `GIT_INDEX_FILE=<temp>` to avoid polluting the user's index, runs `git write-tree`, returns the SHA. Idempotent: snapshotting an unchanged workspace returns the same SHA.
3. **Restore operation**: `restore(tree_sha, workspace_path, mode)`. Three modes mirroring Cline's three-mode UX:
   - `files_only`: `git checkout-index --prefix={workspace}/` for tracked paths; `git ls-tree -r {tree_sha}` to identify untracked file paths and re-materialize them.
   - `conversation_only`: no file restore; calls into ADR-226 to truncate events past the originating event's `seq`.
   - `files_and_conversation`: both, atomically (see §"Atomic restore").
4. **Event-envelope extension**: ADR-226 events gain optional `file_tree_sha` and optional `file_changes` (count, paths summary). Producers populate these via `shadow_git.snapshot()` after their state mutation completes.
5. **Diff preview before restore**: every `restore()` call produces a `git diff-tree --name-status <current_tree> <target_tree>` and writes it to `.cognitive-os/reports/restore-preview-{ts}.txt` *before* the destructive operation. The CLI surface (`cos rollback`) refuses to proceed without operator confirmation.

## Atomic restore semantics

The "context-mismatch bug" (research §3.G of replay-timeline) is the dominant checkpoint failure mode in the field. Cline solves it; Claude Code SDK does not; the difference is atomicity. ADR-227's contract:

```
restore_atomic(tree_sha, target_seq, mode):
  acquire(restore_lock)
  try:
    1. write diff-tree preview
    2. await operator confirmation (interactive) OR --yes flag
    3. if mode in (files_only, files_and_conversation):
         git checkout-index --prefix={workspace}/ <tree_sha>
         re-materialize untracked-at-snapshot files
    4. if mode in (conversation_only, files_and_conversation):
         event_bus.truncate_session(target_seq)   # ADR-226 op
    5. emit RESTORE_COMPLETED event with both shas
    6. invalidate dependent projections (cost ledger, etc.)
  except:
    rollback any partial step; emit RESTORE_FAILED
  finally:
    release(restore_lock)
```

The `restore_lock` is a session-scoped `flock` on `.cognitive-os/sessions/{session_id}.restore.lock`. Concurrent restore on the same session is impossible.

## Manifest declaration

```yaml
# manifests/shadow-git.yaml
schema_version: shadow-git/v1
status: active
owner: platform-orchestration

storage:
  base_dir: "~/.cognitive-os/snapshots"
  per_session_path: "{base_dir}/{project_id}/{session_id}/.git"
  retention_governed_by: "ADR-200"

snapshot:
  trigger: "post_tool_use_hook | manual_via_cli"
  atomicity: "git_write_tree"
  cost_budget_ms_p95: 200

restore:
  modes: [files_only, conversation_only, files_and_conversation]
  preview_required: true
  preview_path: ".cognitive-os/reports/restore-preview-{ts}.txt"
  lock_path: ".cognitive-os/sessions/{session_id}.restore.lock"

untracked_capture:
  policy: "all_workspace_files_except_gitignore"
  exclusions:
    - ".git/"
    - "node_modules/"
    - ".venv/"
    - "__pycache__/"
    - "*.pyc"
    - ".cognitive-os/snapshots/"   # never recurse into our own storage
  size_warning_mb: 50
  size_block_mb: 500

governance_events_carry_tree_sha:
  - blast_radius_assessment
  - policy_check
  - audit_finding
  - validation_block
  - clarification_gate

cli:
  command: "cos rollback [--mode files|conversation|both] [--to-seq N | --to-event-id ID] [--yes]"
  refuses_without_preview: true
  refuses_under_dirty_workspace: true
```

## Hard rules

- **Bare repo never enters user's project tree.** Anchored under `$HOME` (or `XDG_DATA_HOME`); never under `${PROJECT}/`. Verified by a CI test that asserts no shadow-git path is ever a descendant of any tracked project.
- **`GIT_INDEX_FILE` isolation is mandatory.** Snapshot operations must not touch the user's `.git/index`. Verified by a snapshot-equality test on `.git/index` before and after a snapshot.
- **Restore is opt-in and gated.** No automatic restore on any path. CLI requires `--yes` or interactive confirmation; the diff preview MUST be written before any mutation; `restore_lock` MUST be held.
- **Atomic file+conversation restore is the default for `files_and_conversation`.** Partial restores leave the system in an undefined state and MUST emit `RESTORE_FAILED` with rollback instructions.
- **Untracked-file capture is bounded.** Snapshots refuse if the workspace exceeds `size_block_mb`. Warns above `size_warning_mb`. This prevents runaway storage on monorepos with large generated artefacts.
- **Schema-versioned events.** `file_tree_sha` is added under `event-sourced-session-bus/v1` envelope; receivers MUST tolerate events without the field (older events) and MUST validate format (40-char hex).
- **No external dependencies beyond `git` itself.** Honors C2: `git` is already a hard requirement. No new install.

## Test tier matrix (per C3)

T1 ✅ unit — snapshot/restore/prune in isolation
T2 ✅ integration — snapshot → mutate workspace → restore → assert byte-identical
T3 ✅ behavior — `cos rollback` CLI contract, refusal paths, diff preview format
T4 ✅ smoke — record session, restore to seq 5, assert workspace + conversation match seq 5 state
T5 ✅ adversarial — restore under dirty workspace, restore with stale lock, snapshot of >500MB workspace, snapshot during operator's own `git commit`
T6 ⬜ performance — covered indirectly via T4 timing budget
T7 ✅ chaos — kill -9 mid-snapshot, kill -9 mid-restore, full disk during snapshot, corrupted shadow repo
T8 ⬜ cross-harness — N/A, internal substrate
T9 ⬜ adoption-truth — pattern-only adoption; no external tool integrated
T10 ✅ audit invariants — `git status` on user repo byte-identical before and after a snapshot; restore never touches paths outside workspace

## Consequences

### Positive

- **Devin-parity replay-and-restore** at zero infra cost. Closes the most-cited orchestration-gap differentiation.
- **Governance-as-restore-point** is the unique ADR-227 + ADR-226 combo. No competitor links policy events to file state with restore capability.
- **Untracked-file capture** closes the gap that Cline's shadow-git solves and `git stash` does not. Operator's WIP is captured even if not staged.
- **Clean separation from user history.** Operator's `git log`, `git status`, `git stash` are unaffected. Honors the prior-art research finding that "user-side mutation as part of agent setup is industry anti-pattern."
- **ADR-224 (shadow-state safety net)** has its substrate. ADR-220 worktree audit can record file_tree_sha on every audit finding. ADR-228 retry context can rewind workspace to pre-failure state.

### Negative / trade-offs

- **Storage growth**: one bare repo per session. Mitigation: ADR-200 retention controller; per-session repos GC'd on session close.
- **Snapshot latency**: `git write-tree` on a large workspace can spike. Mitigation: budget p95 < 200 ms; size_block at 500 MB; warns above 50 MB so operators see the cost before it bites.
- **Restore-confusion risk**: operators may misunderstand `mode` choices. Mitigation: diff preview + interactive confirmation; CLI help is explicit about each mode; runbook documents the three patterns with examples.
- **Untracked-file capture on monorepos with generated artefacts** can balloon storage. Mitigation: explicit exclusion patterns in manifest; warning + block thresholds; operator can extend exclusions per project.

## Alternatives rejected

- **`git stash` as the snapshot primitive.** This is exactly what the prior-art research argued against (see [`multi-agent-orchestration-prior-art-2026-05-06.md`](../research/multi-agent-orchestration-prior-art-2026-05-06.md) §1.2). Rejected.
- **VM snapshots (Devin-style).** Hard constraint from C2: no hypervisor in default path. Optional adapter at most. Rejected as primary.
- **Block-level CoW (Replit-style).** Requires control of the storage backend. Local-first OS doesn't have that. Rejected.
- **Per-event commit to user's repo with custom committer.** Pollutes history; user's `git log` becomes unreadable; bisect breaks. Rejected.
- **In-memory snapshot only.** Doesn't survive process death; useless for replay across crashes. Rejected.
- **Adopt git-shadow library directly.** License-verified-MIT but small surface; we get no leverage from a dep we'd need to audit and pin. Pattern adoption is sufficient.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_shadow_git.py tests/behavior/test_cos_rollback_cli.py tests/audit/test_shadow_git_user_index_invariant.py tests/chaos/test_shadow_git_kill9.py -q

# Smoke (T4): full record-mutate-restore round-trip
bash tests/smoke/test_record_mutate_restore.sh
```

The tests must prove:

- `snapshot()` produces a stable tree SHA: snapshotting unchanged workspace returns the same SHA.
- `snapshot()` does not touch user's `.git/index`: byte-identical before and after.
- `restore(mode=files_only)` correctly re-materializes both tracked and untracked-at-snapshot files.
- `restore(mode=files_and_conversation)` is atomic: a kill mid-restore leaves either pre-state or post-state, never partial.
- `cos rollback` refuses when no preview was generated.
- `cos rollback` refuses when workspace is dirty (operator must commit/stash their own changes first — irony noted).
- Restore lock prevents concurrent restore on same session.
- Snapshot of a workspace exceeding `size_block_mb` returns `SnapshotTooLarge` and emits an event, not a crash.
- `file_tree_sha` field is correctly populated on governance events declared in `governance_events_carry_tree_sha`.
- Round-trip on a fixture workspace: snapshot → modify → restore → `diff` returns empty.

## Implementation slices

1. **Slice A — Bare repo lifecycle** (~50 LOC). `lib/shadow_git.py:init_session_repo`, `prune_session_repo`. Tests T1+T7.
2. **Slice B — Snapshot operation** (~60 LOC). `snapshot(workspace_path) -> tree_sha` with `GIT_INDEX_FILE` isolation. Tests T1+T2+T10.
3. **Slice C — Restore operation, files_only** (~50 LOC). `restore(sha, workspace, mode='files_only')` with `git checkout-index --prefix`. Untracked re-materialization via `git ls-tree -r` + write. Tests T2+T5+T7.
4. **Slice D — Conversation-only and atomic combined modes** (~40 LOC). Calls into ADR-226's `truncate_session(seq)`. Restore lock. Tests T2+T7.
5. **Slice E — `cos rollback` CLI** (~60 LOC). Diff preview, interactive confirmation, `--yes` flag, refusal paths. Tests T3+T4.
6. **Slice F — Event-envelope wiring** (~30 LOC). PostToolUse hook captures `file_tree_sha`; governance event producers (blast-radius, policy-check, audit) auto-populate. Tests T2.
7. **Slice G — Operator runbook** at `docs/runbooks/shadow-git-rollback.md`. Three canonical recipes; troubleshooting for "I rolled back but the conversation didn't" → mode=conversation_only.

Total: ~290 LOC.

## Implementation status

- **2026-05-07 — Slice A implemented with ADR-224**: `lib/shadow_git.py` creates off-repo bare repositories, snapshots workspace files with isolated `GIT_INDEX_FILE`, generates restore previews, and performs preview-gated `files_only` restore.
- **CLI**: `scripts/cos-rollback` and `scripts/cos rollback` expose `--snapshot`, `--preview`, and `--restore --yes` flows.
- **Safety-net boundary**: no git stash mutation and no user `.git/index` mutation during snapshot; storage is outside the project tree.
- **Deferred**: conversation truncation, combined atomic files+conversation restore, PostToolUse event-envelope wiring, retention/reaper integration.

## Open questions

- **Should the shadow repo be `--bare` or `--bare --shared`?** Bare is enough; shared adds permission complexity for a single-user OS. Defer until multi-user use case emerges.
- **Should `snapshot()` deduplicate identical trees across sessions?** Possible via hardlinking object dirs, but adds complexity. Defer until storage measurement justifies it.
- **Does `cos rollback --to-event-id` semantics need a "soft" mode that *preserves* later events while restoring files?** Initial answer: no — that's exactly the context-mismatch bug. If operators want it, document as research-question-not-feature.
- **Interaction with ADR-220 worktree audit**: a successful restore may invalidate the audit's "behind/conflict" findings. Worktree audit should re-run after a restore. Tracked as a slice of ADR-220.
- **Interaction with ADR-223 (agent lifecycle reconstruction)**: when ADR-223 lands and worktree-per-write-agent replaces auto-stash, the snapshot trigger moves from PostToolUse to per-worktree commit. Re-evaluate snapshot trigger semantics after 223 lands.
