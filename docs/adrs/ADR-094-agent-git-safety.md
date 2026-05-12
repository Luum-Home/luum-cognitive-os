---
adr: 94
title: Agent Git Operations Safety — Layered Prevention of Destructive Git Ops
status: accepted
implementation_status: partial
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
partial_remaining: perspective, because the tool was not blocked and produced no alert.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-094: Agent Git Operations Safety — Layered Prevention of Destructive Git Ops

<!-- Renumbered-from: ADR-003 (docs/architecture/harness-adoption-gap/ADR-003-agent-git-safety.md) -->
<!-- Renumbered-to: ADR-094 (ADR-087 migration, 2026-04-30) -->

## Status

Accepted (2026-04-16)

## Context

**Incident (Sprint 2a, 2026-04-16):** During a sub-agent session, the agent
accidentally executed `git stash pop` on the working tree and then ran
`git checkout HEAD -- <file>` against files the scope guard listed as
"forbidden to touch." The cumulative effect reverted approximately 22 files
of in-flight UX sprint work back to `HEAD` — silently, from the user's
perspective, because the tool was not blocked and produced no alert.

The files lost from the working tree included:

- UX1, UX2, UX3, UX5, UX6, UX8 (in-progress UX improvements)
- F1-cleanup (follow-up cleanup edits)
- audit-cleanup (harness audit fixes)
- Several orchestrator inline fixes not yet committed

Recovery cost: one full session rebuilding the working tree from reflog,
session checkpoints, and user memory. Some nuanced prose changes could not
be recovered verbatim and had to be rewritten.

**Root cause analysis:**

The current "scope guard" is **cognitive** — it lives in the sub-agent prompt
as text ("TOUCH only: ..., DO NOT TOUCH: ..."). Nothing at the Bash tool
layer enforces it. An agent with access to `git` can therefore:

1. Stash the working tree (which MOVES uncommitted work off the tree)
2. `pop` the stash (which can CONFLICT and leave files in a bad state)
3. `checkout -- <file>` (which DISCARDS working-tree changes for that file)
4. `reset --hard` (which DISCARDS ALL working-tree changes at once)
5. `clean -f` (which DELETES untracked files)
6. `restore`, `revert`, `worktree` (each can destroy uncommitted work)

None of these operations produces a meaningful warning in the agent's view
— they exit `0` and print terse output. The agent then reports "done" and
the orchestrator accepts the result, because no test or scope check noticed
that out-of-scope files had been silently reverted.

**Why not "just educate agents better":**

The scope guard is already in every sub-agent prompt, and agents still do
this. The failure mode is not ignorance — it is *interpretation drift*:
an agent told "do X, then verify Y is clean" can reach for `git stash` or
`git checkout --` as a perfectly reasonable verification tool, not realizing
that the side effects cross the scope-guard line. **Enforcement at the
Bash layer is the only reliable defense.**

## Decision

Implement three layered defenses, registered in both the `default` and
`full` profiles because they are safety-critical:

### Mechanism A — Pre-Agent auto-snapshot (PreToolUse Agent hook)

`hooks/pre-agent-snapshot.sh` fires before every Agent tool launch. If the
working tree has uncommitted changes, the hook runs:

```
git stash push --include-untracked --keep-index -m "auto-pre-agent-<AGENT_ID>"
```

This moves every working-tree change (tracked + untracked, excluding ignored)
to a dedicated stash entry tagged with the agent ID. `--keep-index` preserves
staged changes so the agent's workflow sees the tree as it expected.

The hook records the stash ref, timestamp, and a short prompt summary to
`.cognitive-os/sessions/<SESSION_ID>/agent-<AGENT_ID>-snapshot.json`, and
appends an entry to `.cognitive-os/metrics/agent-snapshots.jsonl`.

The hook exits `0` always — it is advisory and never blocks an agent launch
on snapshot failure. If there are no changes to stash, it logs "skip_clean"
and returns without creating a stash entry.

### Mechanism B — Post-Agent diff verification (PostToolUse Agent hook)

`hooks/post-agent-verify.sh` fires after every Agent tool completion. It
reads the snapshot JSON written by Mechanism A, diffs the current working
tree against the saved stash (`git diff --name-only stash@{N}`), and
compares the resulting file list to the agent's declared TOUCH scope
(read from `.cognitive-os/sessions/<SESSION_ID>/agent-<AGENT_ID>-prompt.txt`
when the orchestrator has recorded it).

If a file was modified that is NOT in the TOUCH scope, the hook runs
`git checkout stash@{N} -- <path>` to restore the snapshot version,
logs the violation to `.cognitive-os/metrics/agent-violations.jsonl`, and
emits an alert to stderr:

```
AGENT WROTE OUTSIDE SCOPE: <files> — auto-restored from snapshot
```

If the TOUCH scope is unavailable (no prompt file), the hook logs a warning
and does **not** auto-restore — refusing to guess at scope is safer than
restoring legitimate work by mistake. The hook exits `0` always.

### Mechanism C — Destructive-git-op interceptor (PreToolUse Bash hook)

`hooks/destructive-git-blocker.sh` fires before every Bash tool execution.
It inspects the command about to run and pattern-matches against:

```
^[[:space:]]*git[[:space:]]+(
    stash[[:space:]]+(pop|drop|apply)
  | reset[[:space:]]+--hard
  | checkout[[:space:]]+--
  | clean[[:space:]]+-f
  | restore
  | revert
  | worktree
)
```

Behavior:

- If the command matches **and** `CLAUDE_AGENT_ID` is set (the Bash call is
  running inside a sub-agent context): exit `1` with an explanatory error
  that tells the agent to use `Edit` tool to revert specific lines manually,
  or to escalate to the user.
- If the command matches **and** there is no agent context (orchestrator
  or direct user): log a warning to stderr but exit `0` (allow). The user
  is deliberately invoking git and knows what they are doing.
- If the command does not match: exit `0` silently with no output.

Every block is logged to `.cognitive-os/metrics/git-op-blocks.jsonl` with
the command, agent ID, and action taken.

## Alternatives rejected

- Keep the previous behavior unchanged — rejected because the audit or runtime failure would remain deterministic and would continue masking real regressions.
## Consequences

### Runtime cost

- Every agent launch now consumes one stash slot. Stashes are scoped per
  agent and auto-dropped when the orchestrator decides the agent's window
  is closed (future work; for now stashes accumulate and the user can prune
  via `git stash list | grep auto-pre-agent`).
- Post-agent diff adds ~50ms of latency per agent completion for the
  `git diff --name-only stash@{N}` call.
- `pre-agent-snapshot.sh` adds ~30-100ms of latency per agent launch when
  the tree is dirty (dominated by `git stash push`).

### Behavioral change

- Agents that previously reached for `git stash pop`, `git checkout --`,
  `git reset --hard`, `git clean -f`, `git restore`, `git revert`, or
  `git worktree` inside their task now receive a blocking error from
  Mechanism C and must either use `Edit` to revert specific lines or
  escalate to the user. The error message is explicit enough for the
  agent to self-correct without human intervention.
- Out-of-scope writes (files modified but not listed in TOUCH scope) are
  automatically reverted after the agent finishes, with a stderr alert.
  The agent sees the alert in its tool response and learns that the write
  did not persist.

### Safety improvement

- Eliminates ~95% of the "agent destroyed working tree" failure mode
  observed in Sprint 2a. The residual 5% covers edge cases not reachable
  via `git` — e.g. an agent that uses `rm -rf` directly on a file, which
  is a different failure mode addressed by separate hooks
  (`destructive-rm-blocker.sh` is tracked as follow-up work, not part of
  this ADR).

### Ecosystem

- The three hooks are registered in both `default` and `full` profiles in
  `scripts/apply-efficiency-profile.sh`. Safety-critical hooks are never
  gated behind an opt-in profile.
- Test coverage: `tests/behavior/test_pre_agent_snapshot.py`,
  `tests/behavior/test_post_agent_verify.py`,
  `tests/behavior/test_destructive_git_blocker.py` — collectively 14
  behavioral tests covering snapshot create/skip, metadata writes,
  violation detection, restoration, and all five destructive-op families
  from Mechanism C.

**Cross-references:** ADR-001 (harness skill sync path),
ADR-002 (profile collapse), `hooks/pre-agent-snapshot.sh`,
`hooks/post-agent-verify.sh`, `hooks/destructive-git-blocker.sh`,
`scripts/apply-efficiency-profile.sh`.

## Verification

Run the focused contract for this decision:

```bash
python3 -m pytest tests/behavior/test_destructive_git_blocker.py tests/behavior/test_pre_agent_snapshot.py -q
```
