# ADR-003 — Pending Hook Registration

**Status:** deferred. `scripts/apply-efficiency-profile.sh` was being modified by
another agent during the Sprint 2a safety work (status: ` M`). The ADR-003
agent did not touch the file, to avoid a merge conflict that could itself
cause the kind of working-tree loss this ADR was written to prevent.

The orchestrator (or a follow-up session) MUST apply the three hook
registrations below once the concurrent edit has settled.

## Files to register

| Hook | File | Surface | Profile |
|---|---|---|---|
| Mechanism A | `hooks/pre-agent-snapshot.sh` | `PreToolUse` / `Agent` | default (`standard`) and `full` |
| Mechanism B | `hooks/post-agent-verify.sh` | `PostToolUse` / `Agent` | default (`standard`) and `full` |
| Mechanism C | `hooks/destructive-git-blocker.sh` | `PreToolUse` / `Bash` | default (`standard`) and `full` |

These three hooks are safety-critical — they must never be gated behind an
opt-in profile.

## Patch 1 — add `destructive-git-blocker.sh` to PreToolUse Bash (standard)

In the `standard` branch of the `pre_bash` assignment, append the new hook:

```diff
     standard)
       # ADR-023: secret-detector also runs as PreToolUse on Bash|Edit|Write|MultiEdit
       # so it can REDACT literal credentials via hookSpecificOutput.updatedInput
       # before the command/edit reaches the shell or the disk.
+      # ADR-003: destructive-git-blocker intercepts `git stash pop|drop|apply`,
+      # `git reset --hard`, `git checkout --`, `git clean -f`, `git restore`,
+      # `git revert`, `git worktree` when CLAUDE_AGENT_ID is set (agent context).
       pre_bash=$(hook_group "Bash" \
         "rate-limiter.sh" \
-        "secret-detector.sh")
+        "secret-detector.sh" \
+        "destructive-git-blocker.sh")
```

## Patch 2 — add `pre-agent-snapshot.sh` to PreToolUse Agent (standard)

Append `pre-agent-snapshot.sh` at the end of the existing `pre_agent`
hook_group for the `standard` branch (after `agent-work-tracker.sh`):

```diff
       pre_agent=$(hook_group "Agent" \
         "dispatch-gate.sh" \
         "clarification-gate.sh" \
         "blast-radius.sh" \
         "inject-phase-context.sh" \
         "agent-prelaunch.sh" \
         "error-pattern-detector.sh" \
         "predev-completeness-check.sh" \
         "completeness-check-llm.sh" \
         "prompt-quality-llm.sh" \
         "registration-check.sh" \
-        "agent-work-tracker.sh")
+        "agent-work-tracker.sh" \
+        "pre-agent-snapshot.sh")
```

## Patch 3 — add `post-agent-verify.sh` to PostToolUse Agent (standard)

Append `post-agent-verify.sh` at the end of the `post_agent` hook_group for
the `standard` branch (after `task-bridge-notify.sh`):

```diff
       post_agent=$(hook_group "Agent" \
         "claim-validator.sh" \
         "completion-gate.sh" \
         "agent-checkpoint.sh" \
         "trust-score-validator.sh" \
         "confidence-gate-llm.sh" \
         "audit-id-enricher.sh" \
         "state-heartbeat.sh" \
         "agent-work-tracker.sh" \
         "task-panel-sync.sh" \
-        "task-bridge-notify.sh")
+        "task-bridge-notify.sh" \
+        "post-agent-verify.sh")
```

## Full profile

The `full` branch in `apply-efficiency-profile.sh` short-circuits and leaves
`settings.json` unchanged. To wire the three new hooks into `full`, edit
`.claude/settings.json` directly (or regenerate from `full`'s upstream
source) and add identical entries in the same matchers used above.

## Summary block updates

After applying the three hooks, also update the `# ── Summary ──` block at
the bottom of `apply-efficiency-profile.sh` so the printed totals reflect
the added hooks:

- `standard` total: `31 hooks` → `34 hooks`
- Mention the three new hooks in the per-matcher summary lines:
  - `PreToolUse Bash: ..., destructive-git-blocker.sh (ADR-003)`
  - `PreToolUse Agent: ..., pre-agent-snapshot.sh (ADR-003)`
  - `PostToolUse Agent: ..., post-agent-verify.sh (ADR-003)`

## Verification

After the three patches are in:

```bash
cd <operator-repo-path>
bash -n scripts/apply-efficiency-profile.sh
bash scripts/apply-efficiency-profile.sh standard
grep -c 'destructive-git-blocker.sh\|pre-agent-snapshot.sh\|post-agent-verify.sh' .claude/settings.json   # expect 3
```

Plus the standard ADR-003 tests must still pass:

```bash
python3 -m pytest tests/behavior/test_pre_agent_snapshot.py \
  tests/behavior/test_post_agent_verify.py \
  tests/behavior/test_destructive_git_blocker.py -v
```
