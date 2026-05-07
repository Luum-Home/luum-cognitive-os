# Runbook — Shadow-Git Rollback

<!-- SCOPE: OS -->

Use this when a COS session needs to inspect or restore an off-repo checkpoint without touching `git stash`.

## Safety invariants

- Snapshot storage lives under `$COS_SHADOW_GIT_BASE` or `~/.cognitive-os/snapshots`, never inside the project worktree.
- Restore is preview-gated: run `--preview` first, then pass the returned `--preview-path` plus `--yes`.
- Use `files_and_conversation` when rewinding agent state; files-only rollback is for manual operator repair.

## Recipes

### 1. Capture a checkpoint

```bash
scripts/cos-rollback --project-dir "$PWD" --session-id "$COGNITIVE_OS_SESSION_ID" --snapshot --json
```

Save the returned `tree_sha` with the event or report that motivated the checkpoint.

### 2. Preview and restore files only

```bash
scripts/cos-rollback --project-dir "$PWD" --session-id SESSION --tree-sha TREE --preview --json
scripts/cos-rollback --project-dir "$PWD" --session-id SESSION --tree-sha TREE \
  --restore --mode files_only --preview-path PREVIEW --yes --json
```

### 3. Restore files and conversation atomically

```bash
scripts/cos-rollback --project-dir "$PWD" --session-id SESSION --tree-sha TREE --preview --json
scripts/cos-rollback --project-dir "$PWD" --session-id SESSION --tree-sha TREE \
  --restore --mode files_and_conversation --target-seq N \
  --preview-path PREVIEW --yes --json
```

Use this when the agent should resume as if events after `N` never happened.

### 4. Prune old snapshots

Dry-run first:

```bash
scripts/cos-rollback --project-dir "$PWD" --prune --max-age-seconds 604800 --json
```

Execute only after reviewing candidates:

```bash
scripts/cos-rollback --project-dir "$PWD" --prune --max-age-seconds 604800 --yes --json
```

## Troubleshooting

- If files changed but the agent still references future events, redo with `--mode files_and_conversation` or `--mode conversation_only` and the correct `--target-seq`.
- If preview is empty, the target tree already matches the workspace.
- If restore fails, ADR-227 writes a safety snapshot before combined restore and rolls back the event stream bytes on failure.
