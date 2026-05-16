---
name: devbox-checkpoint
description: Save and restore environment state snapshots using devbox
invoke: /checkpoint
version: 1.0.0
model: sonnet
audience: project
platforms:
- claude-code
prerequisites: []
triggers:
- devbox-checkpoint
- /devbox-checkpoint
- Devbox Checkpoint — State Snapshots
- Save and restore environment state snapshots using devbox
routing_intents:
  - "save a devbox environment checkpoint before risky changes"
  - "restore a devbox workspace snapshot after failed changes"
  - "compare devbox state before and after dependency changes"
  - "checkpoint dependencies before risky infrastructure work"
---
<!-- SCOPE: both -->
# Devbox Checkpoint — State Snapshots

## Purpose

Save and restore reproducible snapshots of the development environment state, including devbox config, dependency lock files, git status, and running containers.

## Commands

### `/checkpoint save [label]`

Save a checkpoint with optional label.

### `/checkpoint restore [timestamp|label]`

Restore and verify environment matches a previous checkpoint.

### `/checkpoint list`

List all saved checkpoints.

### `/checkpoint diff [timestamp|label]`

Compare current state against a checkpoint.

## Save Procedure

1. Read `devbox.json` and `devbox.lock` (if exists)
2. Capture hashes:
   - `go.sum` files: `find . -name go.sum -exec md5 {} \;`
   - `package-lock.json` / `yarn.lock` files: `find . -name package-lock.json -o -name yarn.lock -exec md5 {} \;`
   - `gradle.lockfile` if present
3. Capture `git status --porcelain` and `git log --oneline -5`
4. Capture `docker ps --format '{{.Names}} {{.Image}} {{.Status}}'`
5. Store checkpoint as JSON in `.cognitive-os/checkpoints/{timestamp}.json`:

```json
{
  "timestamp": "2026-03-22T10:00:00Z",
  "label": "pre-refactor",
  "devbox": { "packages": [...], "hash": "..." },
  "dependencies": {
    "go_sums": [{"path": "...", "hash": "..."}],
    "node_locks": [{"path": "...", "hash": "..."}],
    "gradle_locks": [{"path": "...", "hash": "..."}]
  },
  "git": {
    "branch": "main",
    "head": "abc1234",
    "dirty_files": ["..."],
    "recent_commits": ["..."]
  },
  "docker": {
    "containers": [{"name": "...", "image": "...", "status": "..."}]
  }
}
```

## Restore Procedure

1. Read checkpoint JSON
2. Compare each section against current state
3. Report diffs:
   - Package mismatches (devbox.json changed)
   - Dependency drift (lock file hashes differ)
   - Git state changes (new commits, dirty files)
   - Container state changes (missing/extra containers)
4. Suggest remediation for each diff:
   - `devbox install` for package mismatches
   - `go mod tidy` / `yarn install` for dependency drift
   - `git stash` / `git checkout` for git state
   - `docker-compose up -d` for container state

## Notes

- Checkpoints are lightweight (JSON metadata only, no binary snapshots)
- Maximum 50 checkpoints retained; oldest pruned automatically
- Use labels for meaningful checkpoints (e.g., "pre-migration", "stable-v2")
