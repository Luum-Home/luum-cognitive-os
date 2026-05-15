---
name: stash-quarantine
command: /stash-quarantine
description: Use when safely isolating, inspecting, restoring, or discarding temporary Git stash quarantine entries without relying on positional refs.
trigger: User or agent needs to isolate work fronts, inspect stashes, restore WIP, or explain stash/checkpoint safety.
version: 1.0.0
audience: both
platforms:
- claude-code
- codex
summary_line: Safely isolate, inspect, restore, or discard temporary Git stash quarantine entries without positional stash refs.
routing_intents:
- intent: stash_quarantine_request
  description: User needs to inspect, isolate, restore, apply, pop, or drop Git stash entries safely without relying on positional refs.
  confidence: 0.9
routing_patterns:
- pattern: \bstash@\{\d+\}
  confidence: 0.96
- pattern: \bgit stash (apply|pop|drop)\b
  confidence: 0.92
- pattern: \brestore.*stash\b
  confidence: 0.88
- pattern: \bwork[- ]front isolation\b
  confidence: 0.86
triggers:
- stash quarantine
- stash restore
- work-front isolation
---
<!-- SCOPE: both -->
# Stash Quarantine

## Purpose

Preserve WIP and separate semantic work fronts without treating `stash@{N}` as a stable identity.

## Procedure

1. Prefer a branch, worktree, or commit if the work front should survive beyond this immediate operation.
2. If stash quarantine is unavoidable, create a named entry:

   ```bash
   git stash push -u -m "quarantine-<front>-<date>"
   ```

3. Before applying or dropping, inspect the current entry:

   ```bash
   git stash list --format='%gd %H %gs'
   git stash show --name-status <reviewed-stash-ref>
   ```

4. Restore only the inspected entry:

   ```bash
   git stash apply <reviewed-stash-ref-or-sha>
   ```

5. Verify the working tree and tests. Drop only after confirming ownership and restore:

   ```bash
   git stash drop <reviewed-stash-ref>
   ```

6. When editing docs/scripts that mention stash recovery, run:

   ```bash
   python3 scripts/stash_quarantine_audit.py --project-dir . --fail <paths>
   ```

## Output Contract

```text
STASH_QUARANTINE_REPORT
Front: <semantic work front>
Durable home: <branch/worktree/commit or quarantine reason>
Reviewed entry: <ref/sha/message or none>
Action: applied | dropped | preserved | no-op
Verification: <commands or manual checks>
Residual risk: <risk or none>
```
