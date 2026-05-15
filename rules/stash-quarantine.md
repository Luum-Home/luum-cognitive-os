<!-- SCOPE: both -->
<!-- TIER: 1 -->
---
enforcement: agent-instruction
trigger_priority: high
routing_patterns:
- pattern: \bstash@\{\d+\}
  confidence: 0.95
- pattern: \bgit stash (apply|pop|drop)\b
  confidence: 0.9
- pattern: \bwork[- ]front isolation\b
  confidence: 0.85
- pattern: \bcheckpoint\b.*\bstash\b
  confidence: 0.8
summary_line: Treat Git stash as temporary quarantine; use copy checkpoints, commits, branches, or worktrees as durable work-front identity.
routing_intents:
- intent: stash_quarantine_safety
  description: User or agent is using stash references, isolating work fronts, restoring WIP, or resolving stash conflicts.
  confidence: 0.9
---
# Stash Quarantine and Work-Front Isolation

## Purpose

Prevent agents from treating positional Git stash refs as durable identity. `stash@{N}` is a moving pointer. Work-front isolation is a Cognitive OS concern, but the durable units are commits, branches, worktrees, named quarantine entries, copied checkpoints, and inspected refs.

## Rule

Do not instruct or execute bare `git stash pop`, bare `git stash apply`, or bare `git stash drop`. Do not call `stash@{0}` the identity of a work front.

Use this sequence instead:

1. Prefer a branch, worktree, or commit for any durable work front.
2. If temporary stash quarantine is unavoidable, create it with a unique descriptive message.
3. Inspect the quarantine entry by file list and message before applying or dropping.
4. Apply only the reviewed current ref or SHA.
5. Drop only after verifying the restore or deciding the entry is obsolete.

## Cognitive OS Default

Auto-checkpoints must be copy-only by default. Stash mutation is a compatibility escape hatch requiring explicit opt-in.

Run the audit when editing stash guidance:

```bash
python3 scripts/stash_quarantine_audit.py --project-dir . --fail <paths>
```

## Contextual Trigger

- Pattern: `stash@{N}` or `stash@{0}`
- Pattern: `git stash pop`, `git stash apply`, or `git stash drop`
- The agent is isolating work fronts, recovering WIP, applying a stash, or explaining checkpoint/recovery behavior.
