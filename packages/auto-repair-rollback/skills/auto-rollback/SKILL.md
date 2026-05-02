<!-- SCOPE: both -->
---
name: auto-rollback
description: "Prepare a human-approved rollback plan when SDD verify-apply exceeds max retries"
triggers: ["/auto-rollback", "Verify-apply loop exceeded 3 retries", "rollback plan required"]
audience: project
summary_line: "Prepare a human-approved rollback evidence package; never silently reverts work."
version: "2.0.0"
platforms: ["claude-code"]
prerequisites: []
---

# /auto-rollback

Prepare a rollback evidence package. Do not run destructive git commands until the operator explicitly approves the plan.

## Safety Contract

This skill MUST NOT execute `git revert`, `git restore`, `git reset --hard`, `git clean`, `git checkout -- <path>`, stash mutation, branch deletion, or worktree mutation without explicit human approval. ADR-107 makes this true in every phase.

## Rollback Plan

```yaml
ROLLBACK_PLAN:
  approval_required: true
  destructive_commands_executed: false
  candidate_commits: []
  interleaved_commits: []
  dirty_worktree: clean|dirty
  affected_files: []
  proposed_commands: []
  verification_commands: []
  abort_conditions: []
```

Prefer explicit hashes over ranges. Avoid `HEAD~N..HEAD` unless the plan proves the range contains only owned commits. Ask for human approval before execution.
