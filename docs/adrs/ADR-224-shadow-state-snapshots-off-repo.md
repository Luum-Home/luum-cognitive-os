# ADR-224 — Shadow-State Snapshots, Off-Repo

<!-- SCOPE: OS -->

**Status**: Accepted — Slices A–C implemented with ADR-227 (2026-05-07)
**Date**: 2026-05-07
**Related**: ADR-223 (worktree-per-write-agent), ADR-226 (event-sourced session bus), ADR-227 (shadow-git checkpoint substrate)
**Source**: Cline/Hermes/Kilo/git-shadow pattern research; implemented clean-room under FSL-1.1-MIT.

---

## Context

ADR-227 provides the storage substrate: a bare shadow git repository outside the project that can snapshot and restore filesystem state. ADR-224 defines the safety-net boundary around that substrate.

The safety net must not recreate the bug class that prompted ADR-223: mutating the operator worktree through `git stash` as part of agent setup. Shadow-state snapshots are off-repo and opt-in; they do not hide WIP and do not mutate `git stash`.

## Decision

Use ADR-227 shadow-git as the only default safety-net substrate for future rollback/replay work. Store snapshot object databases outside the project tree, keyed by project/session, and expose restore only through preview-gated APIs/CLI.

## Hard rules

- Snapshot storage is never inside the project worktree.
- Snapshot creation does not touch `.git/index` or `git stash`.
- Restore requires preview first and explicit operator confirmation/`--yes`.
- Conversation truncation and combined restore use ADR-227 modes; filesystem-only remains available only for operator repair.

## Implementation status

- **2026-05-07 — Slice A implemented**: `lib/shadow_git.py` stores bare repos off-repo and supports snapshot, preview, files-only restore, and prune. `scripts/cos-rollback` exposes preview/restore. Tests cover no-stash/no-index mutation and round-trip restore.
- **2026-05-07 — Slices B–C implemented**: `docs/runbooks/shadow-git-rollback.md` documents capture/preview/restore/prune flows; `manifests/shadow-git.yaml` declares retention; `scripts/cos-rollback --prune` dry-runs or executes TTL cleanup for off-repo session stores.
