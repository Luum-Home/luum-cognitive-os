---
adr: 35
title: 'Worktree CWD Enforcement: 3-Layer Defense'
status: accepted
implementation_status: partial
date: '2026-04-20'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
---

# ADR-035 — Worktree CWD Enforcement: 3-Layer Defense

**Status**: Accepted  
**Date**: 2026-04-20  
**Deciders**: Maintainer  

---

## Context

Claude Code sub-agents inherit the current working directory (cwd) from the
orchestrator process. When a user launches Claude Code from inside a git
worktree (a secondary checkout created by `git worktree add`), every sub-agent
that runs `git commit`, `git add`, or any path-relative file operation operates
on the worktree branch, not on `main`.

This is silent and surprising. There is no error — commits simply accumulate on
a branch the user did not intend to target. The problem compounds when:

- The worktree branch is a short-lived Claude-managed branch
  (e.g. `claude/gracious-burnell-5a757d`)
- The user expects work to land on `main` or a feature branch they created
- The `agent-working-dir-inject.sh` hook resolves the correct path but the
  sub-agent ignores the injected context (happens when prompts are long and
  the directive is buried)

Three separate mitigation layers exist or are planned. This ADR documents all
three so they can be built, maintained, and reasoned about as a coherent
defense-in-depth strategy.

---

## Decision

Implement a 3-layer defense against unintended worktree commits:

### Layer 1 — SessionStart nudge (this ADR, implemented)

**Hook**: `hooks/session-start-worktree-nudge.sh`  
**Event**: `SessionStart`  
**Mechanism**: Fires before any user prompt is processed. Detects whether
Claude Code was launched from a non-main worktree by checking if `.git` in the
project root is a file (worktree link) rather than a directory (main worktree).
If a worktree is detected, emits a prominent `WARNING: WORKTREE DETECTED`
message as `additionalContext`, visible to both the user and the model before
any work begins.

The nudge includes:
- The current worktree path and branch
- The resolved main worktree path
- Three actionable suggestions (launch from main, rely on enforcer, or opt in)
- The current `orchestration.sub_agent_cwd` policy from `cognitive-os.yaml`

This is the **earliest possible interception point**. Even if the user ignores
it, the warning is in the session transcript.

Logs every firing to `.cognitive-os/metrics/worktree-nudges.jsonl` for
observability.

### Layer 2 — Working-dir advisory injection + Bash command warning (existing, already merged)

Two hooks implement this layer:

**`hooks/agent-working-dir-inject.sh`** (PreToolUse:Agent)  
Resolves the correct working directory based on the
`orchestration.sub_agent_cwd` policy in `cognitive-os.yaml` and injects a
`WORKING DIR:` directive into every sub-agent's `additionalContext`. Policy
options: `current` (no injection), `main_worktree` (resolve and inject main
branch path), `branch` (inject the path for the currently checked-out branch).
Includes a warm-path cache (p95 <5ms, <50ms cold) to avoid repeated
`git worktree list` calls.

**`hooks/agent-bash-cwd-enforcer.sh`** (PreToolUse:Bash, warn mode)  
Intercepts `git` commands issued by sub-agents and warns when the command will
operate on a worktree branch. Operates in warn mode — emits a warning but does
not block the command. This preserves the ability to intentionally commit to
worktree branches while still producing an observable signal.

Limitation: advisory injection can be ignored by sub-agents if the directive
is buried in a long prompt. Warn mode does not prevent the commit.

### Layer 3 — Enforcer upgrade: warn → command rewrite (pending, separate task)

**Hook**: `hooks/agent-bash-cwd-enforcer.sh` (upgrade)  
**Status**: Not yet implemented — planned as a follow-up task  
**Mechanism**: Upgrades the enforcer from warn mode to command-rewrite mode.
When a sub-agent issues a `git` command from a worktree cwd, the hook
transparently prepends `cd <main-path> &&` (or uses `git -C <main-path>`)
before the command reaches the shell. The sub-agent sees a successful commit
to the correct branch without needing to understand the worktree context.

This is the only layer that provides **guaranteed** enforcement — the other two
rely on the model or user reading and acting on warnings. Layer 3 makes
correct behavior automatic.

Implementation notes for Layer 3:
- Must not rewrite commands when the user has set `sub_agent_cwd: current`
  (explicit opt-in to worktree commits)
- Must handle `git -C <path>` invocations that already specify a correct path
- Must preserve command arguments verbatim (no unintended quoting changes)
- Needs a HALT-and-WAIT gate for the first session after enabling, to confirm
  the rewrite behaves correctly in the user's repo topology

---

## 3-Layer Defense Summary

| Layer | Hook | Event | Mode | Scope |
|-------|------|--------|------|-------|
| 1 | `session-start-worktree-nudge.sh` | SessionStart | Warn (user-visible) | This ADR |
| 2a | `agent-working-dir-inject.sh` | PreToolUse:Agent | Advisory (model-visible) | Existing |
| 2b | `agent-bash-cwd-enforcer.sh` | PreToolUse:Bash | Warn (model-visible) | Existing |
| 3 | `agent-bash-cwd-enforcer.sh` (upgraded) | PreToolUse:Bash | Enforce (rewrite) | Pending |

---

## Consequences

### Positive

- Layer 1 eliminates silent surprise: the user knows before any work starts
- The three-layer design means no single point of failure
- Layer 1 and 2 are advisory-only: zero risk of blocking legitimate worktree work
- The nudge log enables analytics: how often do users work from worktrees?
- `orchestration.sub_agent_cwd: current` provides a clean opt-out

### Negative / Trade-offs

**False positives on intentional worktree use**:  
Users who deliberately launch Claude Code from a worktree (e.g. to work on
a feature branch in isolation) will see the Layer 1 nudge every session.
Mitigated by the explicit `sub_agent_cwd: current` opt-out and the clear
wording of suggestion #3.

**Operational burden**:  
Layer 1 adds ~10–20ms to session start (one `git worktree list --porcelain`
call). Within the SLO 1 p95 <2s budget. Layer 2 hooks were already present;
no new burden.

**Layer 3 complexity**:  
Command rewriting is non-trivial and carries risk of breaking legitimate git
invocations. Deferred to a separate task with its own review and HALT gate.

---

## Alternatives Considered

### git-level pre-commit hook

A `.git/hooks/pre-commit` that rejects commits from worktrees unless an env
var is set. Rejected because:
1. Pre-commit hooks require the environment to be set up in the worktree, not
   the main repo — fragile when worktrees are created by Claude.
2. Provides no early warning; the user only learns at commit time.
3. Cannot inject the correct path — only blocks.

### Orchestrator chdir at startup

Having the orchestrator `chdir` to the main worktree before launching
sub-agents. Rejected because:
1. Not possible — Claude Code does not expose a pre-agent-launch chdir hook.
2. Would change the user's cwd unexpectedly, breaking relative-path workflows.
3. Layer 3 (command rewrite) achieves the same outcome more surgically.

### Disable worktree support entirely

Reject `git worktree add` patterns in the codebase. Rejected because:
1. Claude Code uses worktrees intentionally for branch isolation.
2. Would prevent a core feature of the development workflow.

---

## Rollout

1. Layer 1 (`session-start-worktree-nudge.sh`) — deployed in this commit.
   Registered in `default` and `full` profiles via `apply-efficiency-profile.sh`.
2. Layer 2 hooks — already deployed (no change required).
3. Layer 3 (enforcer upgrade) — tracked as a follow-up task. Requires:
   - Design review of the rewrite logic
   - HALT gate on first activation
   - Test coverage for rewrite edge cases

---

## Verification

```bash
# Layer 1: hook is executable
test -x hooks/session-start-worktree-nudge.sh

# Layer 1: registered in settings.json after profile apply
grep session-start-worktree-nudge .claude/settings.json

# Layer 1: fires from a worktree (returns non-empty output)
CLAUDE_PROJECT_DIR=$(pwd) bash hooks/session-start-worktree-nudge.sh | grep -c "WORKTREE DETECTED"

# Layer 1: silent from main worktree (run from the main worktree root)
CLAUDE_PROJECT_DIR=<main-worktree-path> bash hooks/session-start-worktree-nudge.sh | wc -c

# Tests
pytest tests/integration/test_session_start_worktree_nudge.py -v
```
