---
type: methodology-synthesis
source: docs/05-Methodology/runbooks/shadow-git-rollback.md
provenance: "Short recipe runbook for inspecting or restoring off-repo checkpoints via `scripts/cos-rollback`, giving COS sessions a way to rewind files and/or conversation state without touching `git stash`."
---

## What it is

A compact recipe-style runbook for `scripts/cos-rollback`, the shadow-git checkpoint/restore tool used to inspect or roll back a COS session's working tree and/or conversation state.

## Key mechanics

- Safety invariants: snapshots live under `$COS_SHADOW_GIT_BASE` (or `~/.cognitive-os/snapshots`), never inside the project worktree; restore is preview-gated — `--preview` must run before `--restore ... --yes`; `files_and_conversation` mode is for rewinding agent state, while files-only rollback is for manual operator repair.
- Recipe 1 — capture: `scripts/cos-rollback --project-dir "$PWD" --session-id "$COGNITIVE_OS_SESSION_ID" --snapshot --json`, saving the returned `tree_sha` alongside the event/report that motivated the checkpoint.
- Recipe 2 — preview + files-only restore: `--preview --json` first, then `--restore --mode files_only --preview-path PREVIEW --yes --json`.
- Recipe 3 — atomic files + conversation restore: same preview step, then `--restore --mode files_and_conversation --target-seq N --preview-path PREVIEW --yes --json`, used when the agent should resume as if events after sequence `N` never happened.
- Recipe 4 — pruning: dry-run `--prune --max-age-seconds 604800 --json` first, then re-run with `--yes` only after reviewing candidates.
- Troubleshooting: if files changed but the agent still references future events, redo with `--mode files_and_conversation` or `--mode conversation_only` and the correct `--target-seq`; an empty preview means the target tree already matches the workspace; ADR-227 guarantees a safety snapshot is written before a combined restore and rolls back event-stream bytes on failure.

## Relations & where used

Directly implements ADR-227's combined-restore safety guarantee; complements (but is explicitly distinct from) `git stash` as the mechanism for off-repo checkpointing.

## Status / caveats

None found — a short, self-consistent operational recipe doc with no dated claims or point-in-time metrics.
