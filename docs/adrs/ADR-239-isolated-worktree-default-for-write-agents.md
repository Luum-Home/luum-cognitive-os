---
adr: 239
title: Isolated Worktree Default for Write Agents
status: accepted
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-035, ADR-094, ADR-182, ADR-223, ADR-225]
implementation_files:
  - cognitive-os.yaml
  - hooks/agent-working-dir-inject.sh
  - hooks/agent-bash-cwd-enforcer.sh
  - hooks/agent-prelaunch.sh
  - hooks/destructive-git-blocker.sh
  - scripts/cos-agent-worktree-prepare
  - tests/integration/test_agent_working_dir_inject.py
  - tests/integration/test_cwd_enforcer_rewrite.py
  - tests/unit/test_destructive_git_block.py
tier: maintainer
tags: [git-safety, worktree, agent-lifecycle, concurrency, postmortem-2026-05-08]
---
# ADR-239: Isolated Worktree Default for Write Agents

## Status

Accepted. This ADR records the corrective decision after the 2026-05-08
branch-shift incident pattern documented in
`docs/reports/silent-agent-branch-switch-postmortem-2026-05-08.md`.

## Context

`cognitive-os.yaml` previously configured:

```yaml
orchestration:
  sub_agent_cwd: main_worktree
```

That policy solved one problem and created another.

**Good property:** path consistency. A sub-agent sees the canonical repository
path, so `lib/foo.py` points at the expected checkout instead of an arbitrary
temporary directory.

**Bad property:** branch ownership collapse. Multiple write agents share the
operator worktree's `.git/index` and HEAD. If any agent creates or switches a
branch, every other agent using the main worktree inherits that shifted branch
context. Commits can land on a branch the operator or another agent did not
intend.

Observed symptoms on 2026-05-08:

- Agents created branches without an operator-visible handoff, including
  `fix/c4-portability-test-failures`, `feat/cos-cleanup-tiered`, and
  `session/m3-medium-resolutions-v2`.
- Commits landed on a branch different from the branch observed at the prior
  `git status`.
- Work had to be rescued repeatedly because an agent committed to a branch that
  the operator believed was `main`.
- Parallel commits contended on `.git/index.lock`.
- Force-push target was ambiguous because `HEAD` could mean the actual current
  branch, not the branch the operator thought was current.
- A medium-resolution agent reported its branch shifted multiple times during a
  single task.

The existing primitives were individually reasonable but composed into an
unstable mode:

- ADR-035 `agent-working-dir-inject.sh` could inject `main_worktree`.
- `agent-bash-cwd-enforcer.sh` rewrote git commands back to the main worktree.
- ADR-223 `agent-prelaunch.sh` can prepare dedicated write-agent worktrees.
- ADR-182 branch locks protect writes on the current branch, but do not make a
  shared worktree safe for concurrent branch creation.
- ADR-094 destructive git blocking did not originally classify branch context
  changes as governed mutations; that gap was closed by the same incident
  response.

The anti-pattern is **mixing path consistency with branch ownership**.

## Causal primitive review

This decision follows a direct review of the primitives and scripts that made
branch-shift possible or attractive to agents. The root issue was not one bad
script; it was a composition bug across otherwise reasonable safety layers.

### Why agents believed branch creation was allowed

Agents had multiple signals that made branch creation look like the responsible
choice:

- protected-branch guards discourage committing directly to `main`;
- ADR-116 and ADR-225 describe per-session / branch-per-task isolation;
- `scripts/cos-session-branch.sh` can create and switch to a session branch;
- merge-queue and preserve-branch docs normalize temporary branches as a
  recoverability tool;
- `main_worktree` made the cwd look canonical, so the agent did not see a
  boundary between path correctness and branch ownership.

Given those signals, an agent trying not to overwrite the orchestrator or peer
agents could rationally create a branch. The system bug was allowing that
branch to be created **inside the shared operator worktree**.

### Script and primitive roles

| Primitive/script | Role in the old model | Correct interpretation after this ADR |
|---|---|---|
| `cognitive-os.yaml` `sub_agent_cwd` | selected the cwd injected into agents | `isolated_worktree` is the only safe default for concurrent write agents |
| `hooks/agent-working-dir-inject.sh` | injected `main_worktree` as a stable path | must not inject a shared cwd in isolated mode; ADR-223 prelaunch owns the path |
| `hooks/agent-bash-cwd-enforcer.sh` | rewrote git commands back to main | legacy single-agent compatibility only; must stand down for isolated worktrees |
| `hooks/agent-prelaunch.sh` | task claims and optional worktree lifecycle | canonical place to prepare write-agent worktrees |
| `scripts/cos-agent-worktree-prepare` | creates dedicated worktree/branch | correct primitive for branch-per-agent isolation |
| `scripts/cos-session-branch.sh` | creates/switches a session branch | acceptable only with explicit operator intent or non-shared worktree context |
| `scripts/cos-branch-task-check` | checks branch/task naming | naming check, not isolation by itself |
| `hooks/branch-ownership-lock.sh` | locks writes on current branch | cannot authorize prior branch switches; complementary, not sufficient |
| `hooks/destructive-git-blocker.sh` | blocks destructive git operations | must also block branch context changes as governed mutations |

### Doctrine clarified

- Path consistency means agents use the expected repository tree.
- Branch ownership means each writer has an isolated `HEAD` and index.
- `main_worktree` gave path consistency by sacrificing branch ownership.
- Branch-per-task without worktree-per-agent still mutates the shared `HEAD`.
- Therefore concurrent write agents need `worktree per write agent`, with branch
  naming layered on top.

## Decision

Default sub-agent cwd policy is now:

```yaml
orchestration:
  sub_agent_cwd: isolated_worktree
```

Semantics:

1. Write-capable agents get a dedicated ADR-223 worktree from
   `hooks/agent-prelaunch.sh` / `scripts/cos-agent-worktree-prepare`.
2. `hooks/agent-working-dir-inject.sh` does not inject a shared cwd for
   `isolated_worktree`; it defers to `agent-prelaunch.sh`, which emits the
   dedicated worktree path.
3. `hooks/agent-bash-cwd-enforcer.sh` only rewrites git commands back to main
   when the explicit legacy policy is `main_worktree`.
4. Raw branch context changes (`git switch`, `git checkout <branch>`) remain
   blocked by `hooks/destructive-git-blocker.sh` unless explicitly audited with
   `--allow-branch-switch` or `COS_ALLOW_BRANCH_SWITCH=1`.

## Policy modes

| Mode | Status | Meaning | Concurrency safety |
|---|---|---|---|
| `isolated_worktree` | default | write agents get dedicated worktrees; parent HEAD does not shift | safest for 2+ agents |
| `current` | opt-in | agent inherits caller cwd | safe only if caller intentionally controls branch |
| `main_worktree` | legacy opt-in | inject/rewrite to the default-branch worktree | single-agent only; unsafe for parallel write agents |
| `branch` | opt-in | inject current branch's worktree path | safer than shared main only when branch has one owner |

## Alternatives rejected

- **Keep `main_worktree` and rely on branch locks** — rejected because branch locks protect the branch that is current at write time. They do not prevent a previous shell command from moving the shared worktree to another branch, nor do they remove `.git/index.lock` contention among parallel agents.
- **Commit directly to `main` with a global lock** — rejected as a default. It can work for a single orchestrated queue, but it makes all write agents serialize on one branch and does not preserve per-task review boundaries. It remains viable for explicitly single-agent/operator-controlled sessions.
- **Branch per agent without worktree isolation** — rejected because a branch per agent inside the same worktree still shifts the shared HEAD and shared index. It is the failure mode this ADR is correcting.
- **Worktree per write agent** — accepted because it separates path consistency from branch ownership: agents still get absolute repository paths, but those paths live in isolated worktrees with their own branch and index.

## Consequences

### Positive

- Parallel write agents no longer mutate the operator worktree HEAD.
- `.git/index.lock` contention between write agents is reduced because each
  agent has its own worktree/index surface.
- Commits have an auditable per-agent branch/worktree boundary before explicit
  merge back to `main`.
- The C4 portability lane is safer because readiness agents cannot silently
  shift the branch context for each other.

### Negative

- Dedicated worktrees consume disk. Current observed cost is roughly tens of MB
  per agent for this repository shape.
- Agent cleanup/reaper paths remain important; abandoned worktrees must be
  manifest-scoped and safely removable.
- Legacy tests and docs that intentionally exercise `main_worktree` remain, but
  must describe it as a legacy single-agent mode.

## Acceptance criteria

1. `cognitive-os.yaml` sets `orchestration.sub_agent_cwd: isolated_worktree`.
2. `agent-working-dir-inject.sh` emits no shared-main `WORKING DIR` context for
   `isolated_worktree`.
3. `agent-bash-cwd-enforcer.sh` does not rewrite git commands back to main when
   policy is `isolated_worktree`.
4. Existing `main_worktree` rewrite behavior remains available for explicit
   legacy tests.
5. Branch context changes are blocked by the destructive-git blocker unless
   explicitly audited.

## Verification

Focused verification:

```bash
python3 -m pytest tests/integration/test_agent_working_dir_inject.py tests/integration/test_cwd_enforcer_rewrite.py tests/unit/test_destructive_git_block.py -q
```
