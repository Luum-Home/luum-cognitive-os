# Multi-Agent Coding Orchestration — Prior-Art Research

**Date**: 2026-05-06
**Author**: Cognitive OS research session + four-agent local forensics (hook-order, ownership/liveness, secret/history/readiness, source-count review)
**Scope**: How established AI-coding-agent systems prevent parallel agents from clobbering each other's git state, and what Cognitive OS / Luum Agent OS is doing differently that may be wrong.
**Sources surveyed**: 79 listed sources / 50+ distinct websites and projects (full list in §9). Methodology: web search, source-list audit, and local repository forensics.
**Status**: Complete first pass. Honest assessment — written to find where we're wrong, not to validate.

---

## 0. Current incident correction

The operator's immediate claim needs a precise split:

- **HEAD / tracked `main` now appears clean for `2144218+MatiasNAmendola@users.noreply.github.com`**: `git grep -n "2144218+MatiasNAmendola@users.noreply.github.com" -- .` returned zero matches, and commit `02e97bcd chore(privacy): redact operator email from preserve-manifests` redacted the nine tracked preserve-manifest files.
- **Git history is still dirty**: history scans still find the operator email in prior commits. That is an ADR-218 history-sanitization problem, not a HEAD working-tree problem.
- **The WIP-loss class is still real**: three `auto-pre-agent-*` stashes exist locally, all carrying the same license-switch path set. The important failure is not the email's current HEAD state; it is that COS can hide uncommitted work in an auto-stash when an Agent launch is blocked after the snapshot hook runs.

This distinction matters commercially: if we tell ourselves "the sed was lost," we fix one shell command. If we state the real bug — **agent launch can mutate git state before launch is guaranteed** — we fix the architecture.

## 1. Executive Summary

> *"Git is not designed for concurrent operations… running concurrent git operations across multiple worktrees can cause corruption, even though worktrees themselves are safe."* — auto-worktree project warning, [issue #176](https://github.com/kaeawc/auto-worktree/issues/176)

> *"I've seen more stash accidents than any other kind with git. Stashing is more dangerous than committing or branching."* — top-rated [Hacker News comment](https://news.ycombinator.com/item?id=12613062), persistent industry consensus since 2016.

### 1.1 The dominant pattern

Across every major coding-agent harness shipped by 2026 — **Claude Code, Cursor (2.0+), GitHub Copilot CLI, Codex CLI, OpenCode, OpenHands, Devin, Replit Agent, Cline** — the canonical answer to *"how do parallel agents avoid clobbering each other?"* converges on a single pattern:

**One isolated mutable surface per write-capable agent.**

Concretely, three implementations of the same pattern:

| Implementation | Examples | Cost |
|---|---|---|
| **Worktree-per-agent** (one git worktree per write agent) | Claude Code (`isolation: "worktree"`), Cursor 2.0 (≤8 parallel agents), Copilot CLI (`Worktree isolation`), Codex CLI, OpenCode (`opencode-worktree` plugin) | Cheap; same repo, separate index |
| **VM/microVM-per-agent** (sandbox boundary) | Devin (hypervisor snapshot), Replit Agent (CoW block device), OpenHands `DockerWorkspace`, Cursor Background Agents (Ubuntu VMs), ConTree (Firecracker microVMs), E2B/Daytona/Modal as primitives | Expensive; full kernel/process tree |
| **Shadow-state per-agent** (secondary VCS not visible to user) | Cline (shadow Git repo), Hermes (working-dir snapshot), Jujutsu (auto-snapshot every command) | Mid; off-repo state |

Read-only / exploration agents skip isolation universally (Claude Code's `Explore`, OpenCode's `plan`/`general` subagent, Cursor's "Plan" mode). Isolation is only paid for by *writers*.

### 1.2 What almost nobody does

**Mutating the operator's working tree as part of agent setup.** The closest analogue is Cline's shadow-git, but that operates on a separate `.git`-like directory the user never sees and never has to recover from. None of the surveyed systems use **`git stash` as a primitive for capturing user WIP before launching agents**. Every reference to `git stash` in agent contexts is either:
- a manual user action (Aider's `--no-dirty-commits` flag explicitly *opts out* of any auto-mutation)
- a recovery hack (`rm -f .git/config.lock; git worktree prune`)
- a known footgun (HN consensus, "considered harmful" blogs, GitHub bug reports)

**The 'auto-pre-agent-stash' mechanism Cognitive OS uses is, by current industry consensus, an anti-pattern.** That doesn't mean it can't work — but the entire field has converged on a different solution and there are good reasons.

### 1.3 The three things we should steal

1. **Worktree-per-write-agent as default isolation** (the pattern Claude Code/Cursor/Copilot ratified). It avoids index-lock racing because each worktree has its own `.git/index`. Read-only agents skip it.
2. **Shadow-state snapshot, not user working-tree mutation** (Cline pattern; jj's auto-snapshot is the next-gen version). User's `git status` should be invariant under agent launch.
3. **Single-branch-per-task contract** (GitHub Copilot Cloud Agent's strict version): one task → one branch → one PR. No "agent fans out across branches" surprise; no orphan branches.

### 1.4 The three things we should stop trying to do

1. **`git stash push` on the user's working tree as a pre-agent step.** Three confirmed sources say this is harmful: HN consensus, the canonical "considered harmful" blog (still circulating in 2025–2026), and our own session forensics where 3 orphan stashes accumulated from blocked-preflight events.
2. **Same-branch concurrent agents on the same worktree.** Even GitButler — the single outlier that allows multiple branches in one worktree — explicitly warns that "*overlapping areas can definitely lead to problems related to races and interference*" ([discussion #12228](https://github.com/gitbutlerapp/gitbutler/discussions/12228)). Trigger.dev's blog [parallel-agents-gitbutler](https://trigger.dev/blog/parallel-agents-gitbutler) gives a working pattern only because each Claude session uses GitButler's `--changes` flag to pre-segregate output.
3. **Storing stash refs as `stash@{N}` in markers.** The ref is mutable — every new stash shifts the index. Anthropic shipped this exact bug (issue #11005) and so did we. Use stash SHAs or, better, don't use stash.

### 1.5 What's defensible about Cognitive OS

- **Harness-agnostic governance layer**: nobody else has this packaged. OpenHands' `BaseWorkspace` abstraction is the closest, but it's an SDK for building agents, not a governance layer for any agent. Martin Fowler's "harness engineering" framing ([article](https://martinfowler.com/articles/harness-engineering.html)) treats the harness as builder-specific; we're betting the user-side harness is a separable product. That's a plausible but unproven bet.
- **Manifest-backed validation primitives** (ADR-212/215/216/217/218): pattern matches ConTree's deterministic config and Replit's "manifest as pointer" model. Not unique conceptually, but unique as a *cross-stack* discipline.
- **Memory layer (Engram)**: parallels Devin's vectorized memory + replay timeline conceptually. Cognition spent more engineering on this than any other piece of infrastructure ([Devin '24 update](https://cognition.ai/blog/sept-24-product-update)). We're choosing a smaller version of the same bet.
- **Phase-aware workflow** (reconstruction vs. production): no published prior art. Defensible if the data backs it.

### 1.6 Verdict

We are over-optimistic on **two specific primitives** — auto-pre-agent-stash, and same-worktree concurrent execution — and the bugs we're hitting are direct consequences. **Everything else in the OS is in the same neighborhood as the rest of the field**; we're not categorically wrong about the existence of a "governance layer" being valuable.

Recommended posture: **steal worktree-per-agent + shadow-state, kill the auto-stash, keep the manifests/memory/phase primitives** and re-evaluate after that change lands.

---

## 2. Per-system deep dive (15 core systems + comparative-only systems)

For each core system: concurrency model, isolation primitive, state-capture, crash recovery, branch strategy, operator-in-loop policy, explicit limitations. Comparative-only systems appear in the table and source list when public docs were useful but not enough for a full deep dive.

### 2.1 Claude Code (Anthropic)

**Concurrency**: Native `Agent` tool spawns subagents in parallel within a single session. Built-in worktree support shipped in v2.1.50 ([Boris Cherny announcement](https://www.threads.com/@boris_cherny/post/DVAAnexgRUj/introducing-built-in-git-worktree-support-for-claude-code-now-agents-can-run-in)). Subagents declare `isolation: "worktree"` in frontmatter; orchestrator handles worktree lifecycle.

**Isolation**: Per-agent worktree at `.claude/worktrees/<branch>/` with branch `worktree-<agent-id>`. Each worktree has its own `.git/index`; the parent repo's index is untouched.

**State-capture**: None at the orchestrator level — isolation is upstream of state-capture.

**Crash recovery**: Worktrees with no changes auto-cleaned; worktrees with changes persist for review.

**Known bugs**:
- **Issue #34645** ([link](https://github.com/anthropics/claude-code/issues/34645)): 3+ parallel `Agent` calls with `isolation: "worktree"` race for `.git/config.lock`. Closed as "not planned." Workaround documented: `rm -f .git/config.lock && git worktree prune && git branch -D worktree-agent-xxx`. Recommended fix: serialize `git worktree add` with internal mutex.
- **Issue #45645** ([link](https://github.com/anthropics/claude-code/issues/45645)): worktree cleanup leaves `repositoryformatversion=1` and `extensions.worktreeConfig=true` in `.git/config`. Breaks "older git libraries" used by other IDE AI agents. Manual fix: `git config core.repositoryformatversion 0; git config --unset extensions.worktreeConfig`.
- **Issue #11005** ([link](https://github.com/anthropics/claude-code/issues/11005)): stale `.git/index.lock` from background git ops blocks user git commands.

**Operator-in-loop**: Permission gates per tool/file; subagents inherit parent permissions unless overridden.

**Limitations explicit**: Single-session subagents only — for cross-session multi-agent coordination, "see [agent teams](https://code.claude.com/docs/en/agent-teams) instead." Claude Code is honest that subagents and cross-session orchestration are different problems.

**File ref**: `code.claude.com/docs/en/sub-agents` is canonical.

### 2.2 OpenCode (sst/opencode)

**Concurrency**: Subagents declared in `~/.config/opencode/agents/*.md` or `.opencode/agents/`. Auto-dispatched by parent agent via the Task tool, or manually via `@mention`. Built-ins: `general` (full tools), `plan` (read-only), `Explore`. Supports concurrent subagents with session-isolation; orchestrator opens a child session per subagent.

**Isolation**: Session isolation only by default. Optional worktree isolation via the [opencode-worktree plugin](https://github.com/kdcokenny/opencode-worktree) (community, not core): `worktree_create("feature/branch")` → `~/.local/share/opencode/worktree/<project-id>/feature/branch/`, auto-spawns terminal, runs `postCreate` hook (e.g. `pnpm install`), commits all changes on `worktree_delete` before removal.

**State-capture**: None native; relies on plugin auto-commit-on-delete.

**Crash recovery**: "Forgotten worktrees remain in storage; manual deletion needed later" (acknowledged limitation in plugin README).

**Branch strategy**: User-driven — plugin places worktrees in `<project-id>/<branch>/`.

**Limitations explicit**: README ([sst/opencode](https://github.com/sst/opencode)) doesn't mention git worktrees or parallel sessions in core; everything is plugin-driven. Concurrency mechanism is "deferred" — not specified in core docs.

### 2.2.1 OpenClaw / OpenClaw-like forks (gap)

No authoritative OpenClaw source was found in this pass. The report therefore treats OpenClaw as an explicit gap rather than inferring its orchestration model from OpenCode. If OpenClaw is important to COS portability, it needs a separate source-backed audit before implementation decisions depend on it.

### 2.3 Codex CLI (OpenAI, 2026 platform)

**Concurrency**: Subagents executed in parallel ("waits until all requested results are available, then returns a consolidated response"). Configured via `agents.max_threads` (default 6) and `agents.max_depth` (default 1, no recursion past 1 level).

**Isolation**: Built-in worktree support in the Codex app — "multiple agents can work on the same repo without conflicts, with each agent working on an isolated copy." Each subagent inherits the parent's sandbox policy; supports overrides at spawn.

**State-capture**: System-level sandboxing (the same Codex CLI native sandbox technology). Agents limited by default to the folder/branch they work in, plus cached web search.

**Crash recovery**: Not detailed in public docs.

**Operator-in-loop**: Codex "only spawns subagents when you explicitly ask it to." Approval prompts for elevated commands (network, etc.).

**Limitations explicit**: "The documentation doesn't explicitly detail filesystem isolation mechanisms across subagents" — sandbox policy "flows from parent to child."

**Source**: [developers.openai.com/codex/subagents](https://developers.openai.com/codex/subagents).

### 2.4 Aider

**Concurrency**: None. Aider is single-instance per terminal. Documentation explicitly does not address running multiple aider instances on the same repo.

**Isolation**: None. Direct mutation of working tree. `--no-auto-commits` and `--no-dirty-commits` to *opt out* of mutation behavior — telling: the default is to commit, but the safety knob is "stop modifying my repo."

**State-capture**: Pre-edit auto-commit of dirty files (so user WIP is committed, not stashed). Authors changes with "(aider)" suffix in author/committer name.

**Branch strategy**: User-driven; aider works on whatever branch is checked out.

**Limitations explicit**: "*If you have multiple agents or processes running in other worktrees, they should be paused before rebasing to prevent corruption*" ([aider docs / auto-worktree #176](https://github.com/kaeawc/auto-worktree/issues/176)). Aider's stance is the most honest: this is a single-process tool, don't run it in parallel.

**Source**: [aider.chat/docs/git.html](https://aider.chat/docs/git.html).

### 2.5 Cursor (2.0+ / 3.0)

**Concurrency**: Up to 8 parallel agents in Cursor 2.0; cap may have moved in 3.0.

**Isolation**: Worktree-per-agent. Configured via `cursor.worktreeCleanupIntervalHours` (default 6h) and `cursor.worktreeMaxCount` (default 20). Background Agents run in isolated Ubuntu VMs (cloud), not local worktrees — different tier.

**State-capture**: Not at the orchestrator; user explicitly merges via `/apply-worktree` or commits from the worktree.

**Crash recovery**: Auto-cleanup keeps newest N; older worktrees are removed. No explicit mention of stale-state cleanup beyond count-based pruning.

**Limitations explicit**: "*If two agents need to modify the same files, you'll still end up with merge conflicts even with worktree isolation*" — conflicts surface during merge, not editing. Cursor docs concede this directly: worktrees defer the conflict, they don't avoid it.

**Source**: [cursor.com/docs/configuration/worktrees](https://cursor.com/docs/configuration/worktrees).

### 2.6 Devin (Cognition AI)

**Concurrency**: Multiple parallel Devins per project, each with its own cloud IDE. Sandboxed per VM.

**Isolation**: Hypervisor-level sandbox per Devin. "*Hypervisor-level snapshotting of the full machine state — memory, process tree, filesystem — so compute shuts down while the agent is idle and resumes exactly where it left off when a CI result arrives.*"

**State-capture**: VM snapshot at any point (Devin's "save state"). Vectorized snapshots of codebase + full replay timeline of every command/file diff/browser tab.

**Crash recovery**: Replay timeline + snapshot restore. "Scrub Devin's timeline and click the 'restore checkpoint' icon at the bottom right corner."

**Branch strategy**: Devin works in cloud, opens PRs back to user's repo. Parallelism = parallel sandboxes, not parallel branches in user's local repo.

**Operator-in-loop**: Devin "actively brings you in as needed." Async handoff via Slack/Teams.

**Limitations explicit**: Cognition's blog states the snapshot infrastructure "took longer than any other piece of infrastructure they had shipped to date" — a public admission that this is hard.

**Source**: [cognition.ai/blog/devin-2](https://cognition.ai/blog/devin-2), [Devin 2025 perf review](https://cognition.ai/blog/devin-annual-performance-review-2025).

### 2.7 OpenHands / OpenDevin

**Concurrency**: SDK-level — `BaseWorkspace` abstract class with `LocalWorkspace`, `DockerWorkspace`, `APIRemoteWorkspace`. Multi-tenant by container.

**Isolation**: "Each agent instance runs in an independent container with a dedicated file system, environment, and resource." LocalWorkspace = no isolation (host fs); RemoteWorkspace via HTTP to Agent Server.

**State-capture**: Container-bound; nothing at orchestrator.

**Crash recovery**: Container restart. Snapshots not described in the SDK paper.

**Limitations explicit**: SDK paper "*does not discuss git operations, filesystem concurrency, or locking mechanisms explicitly*" — they punt on it. Git ops are tools at the agent level, no orchestrator-level concurrency contract.

**Source**: [arxiv 2511.03690v1](https://arxiv.org/html/2511.03690v1).

### 2.8 SWE-agent (Princeton/Stanford)

**Concurrency**: Per-instance. Each `DefaultAgent` runs in its own `SWEEnv`, talking to a sandboxed shell via the SWE-ReX runtime. Tool bundles uploaded as bash/Python.

**Isolation**: Sandboxed shell — typically a Docker container per run, with the repo cloned inside.

**State-capture**: File edits applied via lint-checked autosave; broken Python "is never persisted." Defensive at the *file-write* layer.

**Branch strategy**: One issue → one PR, like Sweep and Copilot Cloud Agent.

**Limitations explicit**: Designed for single-issue resolution; not multi-agent same-repo concurrent.

**Source**: [github.com/SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent).

### 2.9 Cline (VS Code extension)

**Concurrency**: Single-session per workspace.

**Isolation**: **Shadow Git repo** — separate from user's `.git`. Captures *all* files including untracked. Snapshots after each tool use (not each model turn).

**State-capture**: Shadow repo is the canonical implementation of "snapshot the working tree without polluting user history." Three restoration modes: Restore Files (revert WT, keep conversation), Restore Task Only (delete subsequent messages, keep WT), Restore Files & Task.

**Crash recovery**: Checkpoints persist across editor sessions, independent of user git operations.

**Operator-in-loop**: Approve each tool use by default; "YOLO Mode" disables this and is "recommended only in isolated environments like a sandboxed VM, a throwaway branch, or a container."

**Limitations explicit**: Shadow repo doesn't help with multi-agent concurrency — it's per-Cline-session.

**Source**: [docs.cline.bot/features/checkpoints](https://docs.cline.bot/features/checkpoints).

### 2.10 Continue.dev

**Concurrency**: "Parallel processing by launching several CLI instances using background jobs in your shell" (`cn -p "task1" > out1.txt &`). True in-process multi-agent is "for future releases" per docs.

**Isolation**: None. Pure process-level via OS shell.

**State-capture**: None at orchestrator.

**Conflict handling**: Not addressed; deferred to user.

**Limitations explicit**: Continue is honest that they don't solve concurrency — they expose async/await internally, but parallel coordination is the user's problem.

**Source**: [blog.continue.dev/building-async-agents-with-continue-cli](https://blog.continue.dev/building-async-agents-with-continue-cli).

### 2.11 GitHub Copilot — CLI + Cloud Agent

**Two distinct products with distinct concurrency models.**

**Copilot CLI (local)**: Two isolation modes per session — `Workspace isolation` (in-place, single session safe) or `Worktree isolation` (separate worktree, parallel safe). With Worktree, "*The permission level is automatically set to Bypass Approvals and can't be changed, since the agent can't touch your working copy*." A clean coupling: maximum autonomy is gated on maximum isolation.

**Copilot Cloud Agent**: Runs in GitHub Actions ephemeral environment. Strict contract: "*Copilot can only work on one branch at a time and can open exactly one pull request to address each task it is assigned*." Multiple issues can be assigned simultaneously; each gets its own ephemeral runner. Subagents in Cloud Agent "execute sequentially" (parallel subagents not yet shipped per [discussion #182489](https://github.com/orgs/community/discussions/182489)).

**Isolation**: Worktree (CLI) or ephemeral Actions runner (Cloud).

**Limitations explicit**: Sub-agents in Copilot Agent Mode cannot currently run in parallel. Authoritative public position: do parallelism via parallel issues, not parallel subagents.

**Sources**: [kenmuse.com](https://www.kenmuse.com/blog/workspace-vs-worktree-isolation-in-copilot-cli/), [docs.github.com/copilot/concepts/agents/coding-agent](https://docs.github.com/copilot/concepts/agents/coding-agent/about-coding-agent).

### 2.12 Replit Agent

**Concurrency**: Multiple Agents can run in parallel; each is a separate "Replit App" with its own filesystem.

**Isolation**: Block-device-level Copy-on-Write backed by Network Block Device protocol over Google Cloud Storage. Filesystems split into immutable 16 MiB chunks; manifests as pointers. *"Copying a disk is a matter of copying the manifest, making it both cheap and constant-time."*

**State-capture**: Checkpoint = manifest snapshot. Includes code (via git, with auto-commit at "doneness"), filesystem, agent memory, conversation context, runtime config. Database checkpoints via Neon branches at the exact timestamp.

**Crash recovery**: "Restore" = "replace current manifest with different version." Time-travel.

**Operator-in-loop**: Sandbox blocks key files (`.git` history, `.replit` config, agent state files) deterministically. "*Unlike other platforms that simply add statements to system prompts, Replit blocks the Agent deterministically.*" This is the single most important architectural quote in the survey: prompt-level safety isn't safety.

**Limitations explicit**: "Rollbacks do not change your database" by default — explicit opt-in for DB rollback, separate point-in-time restore for production.

**Source**: [blog.replit.com/inside-replits-snapshot-engine](https://blog.replit.com/inside-replits-snapshot-engine).

### 2.13 AutoGen / CrewAI / LangGraph (multi-agent frameworks)

**Concurrency**: Pure message-passing / actor model. No filesystem coordination at framework level.

**Isolation**: Per-agent state encapsulation (in-memory); no fs/git story.

**State-capture**: LangGraph has checkpointers (in-memory, SQL, Redis, MongoDB, cloud) — but these checkpoint *agent state*, not filesystem. "Agent Git" ([github.com/MAS-Infra-Layer/Agent-Git](https://github.com/MAS-Infra-Layer/Agent-Git)) is a community add-on layering State Commit / Revert / Branching on top of LangGraph for *agent reasoning state*, not code.

**File system**: Both AutoGen and CrewAI explicitly defer file conflict handling. AutoGen's [discussion #7144](https://github.com/microsoft/autogen/discussions/7144) recommends "agents write to their own workspace directory while reading from a common state file as a lightweight blackboard." CrewAI's [issue #1170](https://github.com/crewAIInc/crewAI/issues/1170) documents the actual symptom — "*agent complains it cannot locate a file it just created*" — i.e., this is unsolved at the framework level.

**Limitations explicit**: These are reasoning frameworks, not coding-agent harnesses. Conflating the two is a category error. They solve agent-orchestration; they don't solve git.

### 2.14 Hermes (NousResearch)

**Concurrency**: `delegate_task` tool spawns child agent instances with isolated context, restricted toolsets, separate terminal sessions. Default 3 concurrent subagents (configurable).

**Isolation**: Per-subagent terminal session; no fs isolation documented.

**State-capture**: "Hermes automatically snapshots your working directory before making file changes, giving you a safety net to roll back with `/rollback`." Mechanism not detailed publicly — likely a copy-tree, like Cline's shadow.

**Operator-in-loop**: Tool-level approval gates.

**Limitations explicit**: Concurrent edit handling between subagents is not addressed; subagents "operate independently rather than coordinating on shared file edits."

**Source**: [hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com/docs/user-guide/features/overview).

### 2.15 Claude Agent SDK / Anthropic SDK

**Concurrency**: Library-level. Provides the `isolation: "worktree"` knob exposed in Claude Code; SDK consumers can build their own orchestrators.

**Isolation**: Same as Claude Code (it's the same primitive layer).

**Limitations explicit**: "If you need multiple agents working in parallel and communicating with each other, see agent teams instead. Subagents work within a single session; agent teams coordinate across separate sessions." Anthropic publicly admits subagents ≠ multi-agent. Cognitive OS is closer to "agent teams" than "subagents" by this taxonomy.

---

## 3. Cross-cutting analysis

### 3.A Git worktree concurrency — the official position

Official `git-worktree(1)` documentation says worktrees share the same `.git` object database but each has its own index and HEAD. **What it does not promise**: that *parallel git operations across worktrees* are safe.

Confirmed contention points:
- `.git/config.lock` — taken by `git worktree add`; concurrent adds race ([Claude Code #34645](https://github.com/anthropics/claude-code/issues/34645)).
- `.git/index.lock` — per-worktree, but background processes can leave stale locks ([Claude Code #11005](https://github.com/anthropics/claude-code/issues/11005), [#28546](https://github.com/anthropics/claude-code/issues/28546), Cursor [forum thread](https://forum.cursor.com/t/git-lock-file-issue-in-cursor/149747)).
- Refs (under `.git/refs/`) — no per-worktree isolation; a `git rebase` in worktree A can move refs that worktree B expects.
- `git worktree remove` ↔ `git worktree prune` race when a crashed process holds a lock ([auto-worktree #176](https://github.com/kaeawc/auto-worktree/issues/176)).

**Industry consensus quote**: *"Git is designed as a single-process tool and running concurrent git operations across multiple worktrees can cause corruption, even though worktrees themselves are safe."* — this exact phrasing appears in multiple independent sources (auto-worktree warning text, [Termdock blog](https://www.termdock.com/en/blog/git-worktree-conflicts-ai-agents), Augment Code guide).

**Implication**: worktree-per-agent buys you *index-level* safety. It does not buy you *ref-level* or *config-level* safety. Anyone running `git worktree add` concurrently across N agents needs to serialize.

### 3.B `git stash` as IPC — the consensus

> *"If you mistakenly drop or clear stashes, they cannot be recovered through the normal safety mechanisms."* — [git-stash man page](https://git-scm.com/docs/git-stash).

> *"git stash pop considered harmful"* — [Coding Killed the Cat](https://codingkilledthecat.wordpress.com/2012/04/27/git-stash-pop-considered-harmful/), 2012, still widely cited.

> *"Treat git stash as an emergency or convenience tool, not as a substitute for commits and short-lived branches."* — [Stack Overflow / Atlassian docs synthesis](https://www.atlassian.com/git/tutorials/saving-changes/git-stash).

**Documented failure modes**:
1. `pop` triggers conflict-resolution mode but doesn't drop the stash — user thinks it's gone, applies it later by accident.
2. `stash@{N}` ref is mutable; subsequent stashes shift indices.
3. `git stash drop` deletes silently; reflog recovery is non-trivial.
4. `--patch` conflicts can corrupt the index ([Not Quite Zero blog](http://blog.nqzero.com/2013/01/git-stash-save-patch-considered-harmful.html)).
5. Multiple stashes accumulate in long sessions; ordering invariants break.

**Industry response**: nobody in the surveyed set uses `git stash` in their automation. lint-staged ([github.com/lint-staged](https://github.com/lint-staged/lint-staged)) is the closest analogue and explicitly notes that they integrated `git add` to "prevent race conditions with multiple tasks editing the same files." Their approach: optimistic backup-stash → apply tasks → on success, drop stash → on failure, restore. They are extremely careful about the failure paths and they're a single-process tool.

**Cognitive OS pattern (auto-pre-agent-stash)**: invokes `git stash push` on PreToolUse Agent. If preflight then blocks the agent, PostToolUse never fires, stash orphans (ADR-213 admits this ordering risk). This is the bug the current session is investigating, and the prior art says this is *the* failure mode of stash-as-automation.

### 3.C Multi-agent coding — academic literature 2024–2026

Three relevant papers:
1. **AgentCgroup: Understanding and Controlling OS Resources of AI Agents** ([arxiv 2602.09345](https://arxiv.org/html/2602.09345)) — measures resource contention in multi-tenant agent execution. Shows 29% lower P95 latency with intent-driven resource adaptation. Frames the problem as scheduling, not isolation.
2. **Don't Let AI Agents YOLO Your Files** ([arxiv 2604.13536v2](https://arxiv.org/html/2604.13536v2)) — argues for "shifting information and control to filesystems for agent safety and autonomy." Filesystem as the locus of permission, not prompts.
3. **Everything is Context: Agentic File System Abstraction for Context Engineering** ([arxiv 2512.05470](https://arxiv.org/pdf/2512.05470)) — proposes filesystem abstractions for context engineering: abstraction, modularity, encapsulation.

**Convergent thesis**: the filesystem is the right boundary. Not the prompt. Not the model. The filesystem.

This aligns with Replit's "deterministic blocks at OS level" stance and OpenHands' container boundary. It aligns *against* prompt-based safety, against orchestrator-state-capture-via-stash, and against same-mutable-surface concurrency.

### 3.D Sandbox primitives — the menu

| Tech | Boundary | Cold start | Used by |
|---|---|---|---|
| Firecracker microVM | hardware (KVM) | ~125 ms | E2B, ConTree, AWS Lambda |
| gVisor | syscall intercept | ~250 ms | Modal Sandboxes |
| Docker container | namespace+cgroup | ~100–500 ms | Daytona, OpenHands DockerWorkspace |
| Worktree (no sandbox) | filesystem path | ~10 ms | Claude Code, Cursor 2.0, Copilot CLI |
| Process | OS process | ~5 ms | Aider, Cline, Continue |

**Tradeoff curve**: hardware boundary costs ~25× more cold-start than filesystem boundary, and filesystem boundary costs ~2× more than process boundary. The choice depends on threat model: untrusted agent code → microVM; trusted-but-fallible agent → worktree; single-tenant-low-risk → process.

**Cognitive OS positioning**: we operate at the *filesystem* boundary (worktree-aware) but layered with manifest-driven gates. That's defensible. What's less defensible is that we *also* mutate the host worktree via stash — combining the cost of two layers without the safety of either.

### 3.E CRDT / OT for code — limited applicability

[Zed's CRDT post](https://zed.dev/blog/crdts) makes the case for CRDTs as the substrate for collaborative editing. Key constraint: CRDTs work because concurrent operations are inherently commutative. **Code is not commutative.** Two concurrent renames of the same symbol produce different end-states; two concurrent imports produce duplicates. CRDT is the right tool for character-level collaboration (Google Docs, Zed live share), the wrong tool for semantic code merges.

Replit explicitly does not use CRDT for agent code; they use git + CoW filesystem. Devin uses VM snapshots. Nobody surveyed uses CRDT for AI agent merges.

**Implication**: agent-merge-via-CRDT is research, not production. Cognitive OS shouldn't pursue this.

### 3.F OS analogues

The agent-coordination problem is structurally identical to the *concurrent process file access* problem solved by Unix in the 1970s:
- File locks (`flock`, `fcntl`) → optimistic vs. pessimistic locking (file-locking [guide](https://fast.io/resources/secure-file-locks-multi-agent/))
- Copy-on-write at FS level (ZFS, btrfs) → Replit's manifest model
- Transactional FS (MS DTC, ZFS snapshots) → Replit + AgentFS ([github.com/tursodatabase/agentfs](https://github.com/tursodatabase/agentfs))
- Per-process namespaces (Linux mount NS) → containers, worktrees-as-namespaces

**The agent-OS field is reinventing the FS abstractions** with shorter cycles and more glitches. AgentFS (Turso) is the most explicit acknowledgement: "*everything an agent does — every file it creates, every piece of state it stores — lives in a single SQLite database file*." That's a versioned filesystem masquerading as an SQLite WAL.

**Implication**: the most defensible long-term primitives are the OS ones (CoW, namespaces, transactional FS). The least defensible are git-stash-as-IPC and ad-hoc working-tree mutation.

### 3.G Production failures — the postmortem corpus

Recurring failure types in the surveyed corpus:

1. **Lost work via mutated working tree** — most common. Rands' "*I accidentally removed your untracked files with git clean*" is the iconic quote ([panozzaj blog](https://www.panozzaj.com/blog/2025/11/22/avoid-losing-work-with-jujutsu-jj-for-ai-coding-agents/)). Trigger.dev's blog opens with the same trauma. Our own session today reproduced it: 3 orphan stashes, divergent worktree state, working-tree truth not matching `main` truth.

2. **Stale lock files** — Claude Code ships with this bug (#11005, #28546). Cursor too. Self-inflicted footgun: agent crashes mid-op, lock persists, all agents block.

3. **Worktree config drift** — Claude Code #45645 leaves `repositoryformatversion=1` after cleanup. Other tools then fail to read the repo. Cleanup is harder than setup; few tools do it well.

4. **Race conditions in CI/orchestration** — Anthropic's own [postmortem](https://tessl.io/blog/anthropic-postmortem-shows-how-small-changes-compounded-into-claude-code-failure/): "small changes compounded." Firetiger's [March 2026 incident](https://blog.firetiger.com/postmortem-on-the-march-1-2026-ingest-incident/): race condition between build and deploy with concurrency-control assumptions. Compositional bugs eat agentic systems.

5. **Cross-session memory drift** — Anthropic Claude Code memory bug "made it appear to forget prior instructions." Memory is hard to get right.

6. **Production multi-agent failure rate** — [beam.ai industry analysis](https://beam.ai/agentic-insights/multi-agent-orchestration-patterns-production): "*40% of multi-agent pilots fail within six months*." Production teams "*strongly prefer single, well-scoped agents with explicit human-in-the-loop checkpoints, rigid phase-gating, and narrow tool access.*"

**Pattern**: the field consistently underestimates concurrency complexity, ships, hits the same bugs, ratchets toward isolation+sandbox patterns. Cognitive OS is one cycle behind — we're at the "auto-stash and hope" phase that Anthropic, Cursor, Replit moved past.

---

## 4. Comparative table

Read this as: *"What does each system actually guarantee?"*. ✓ = explicit, native; ◐ = via plugin/extension/manual config; ✗ = not addressed / deferred.

| System | Parallel agents same repo | Worktree-per-agent | Sandbox/VM-per-agent | Auto-stash user WT | Shadow-state | Crash recovery primitive | One-PR-per-task contract | Operator-gated mutation |
|---|---|---|---|---|---|---|---|---|
| Claude Code | ✓ | ✓ (`isolation: "worktree"`) | ✗ | ✗ | ✗ | ◐ (worktree persists) | ◐ | ✓ |
| OpenCode | ✓ | ◐ (plugin) | ✗ | ✗ | ✗ | ◐ (auto-commit on delete) | ✗ | ✓ (perms per agent) |
| Codex CLI | ✓ | ✓ (built-in) | ✓ (CLI sandbox) | ✗ | ✗ | ◐ | ✗ | ✓ |
| Aider | ✗ (single instance) | ✗ | ✗ | ✗ (auto-commit instead) | ✗ | ✓ (commits) | ✓ (single workflow) | ◐ |
| Cursor 2.0+ | ✓ (≤8) | ✓ | ◐ (Background Agents in VMs) | ✗ | ✗ | ◐ (cleanup-by-count) | ✗ | ✓ |
| Devin | ✓ | n/a (VMs) | ✓ (hypervisor) | n/a | ✓ (replay timeline) | ✓ (snapshot restore) | ◐ (PR per task) | ✓ |
| OpenHands | ✓ | ✗ | ✓ (Docker) | ✗ | ✗ | ◐ (container restart) | ◐ | ✓ |
| SWE-agent | ✗ (per-issue runs) | ✗ | ✓ (Docker) | n/a | ✓ (lint-checked autosave) | ◐ | ✓ | ✓ |
| Cline | ✗ (single session) | ✗ | ✗ | ✗ | ✓ (shadow git) | ✓ (3 restore modes) | ✗ | ✓ |
| Continue.dev | ◐ (parallel processes) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Copilot CLI | ✓ | ✓ (Worktree mode) | ✗ | ✗ | ✗ | ◐ | ✓ | ✓ (Default mode) / ✗ (Worktree mode = Bypass) |
| Copilot Cloud Agent | ✓ (parallel issues) | n/a (ephemeral runner) | ✓ (Actions) | n/a | ✗ | ◐ (per-run) | ✓ (strict) | ✓ (PR review) |
| Replit Agent | ✓ | n/a | ✓ (CoW Apps) | n/a | ✓ (manifest CoW) | ✓ (time-travel) | ✗ | ✓ (deterministic OS-level blocks) |
| AutoGen / CrewAI / LangGraph | ✓ (msg-passing) | ✗ | ✗ | ✗ | ◐ (state checkpoint, not FS) | ◐ (state replay) | ✗ | ✗ |
| Hermes | ✓ (≤3 default) | ✗ | ◐ (per terminal session) | ✗ | ✓ (`/rollback`) | ✓ | ✗ | ✓ |
| GitButler | ✓ (virtual branches) | ✗ (deliberate — single WT) | ✗ | ✗ | ✓ (per-branch staging) | ◐ | ◐ | ✓ |
| **Cognitive OS** (current) | ✓ | ◐ (`.claude/worktrees/`) | ✗ | **✓ (auto-pre-agent-stash)** | ✗ | ◐ (snapshot manifests) | ✗ | ✓ |

**The single column where Cognitive OS is alone in the surveyed field**: auto-stash user WT. Every other system either doesn't mutate the user's working tree, or commits instead of stashing.

---

## 5. Local COS forensics from this session

Four local agent slots were used to audit the incident from separate angles. Their combined finding is that the failure is structural, not a one-off operator mistake.

### 5.1 Hook-order / stash-forensics finding

`pre-agent-snapshot.sh` is no longer before `agent-prelaunch.sh`, so ADR-213 fixed the first obvious ordering bug. But the active `.claude/settings.json` still runs several other PreToolUse-Agent hooks **after** `pre-agent-snapshot.sh`, including hooks that can exit 2 / block. If any later hook blocks, the Agent tool never executes and `post-agent-snapshot-restore.sh` never receives a PostToolUse event. Result: the auto-stash remains hidden.

The brittle invariant is: "all blockers must run before the mutating snapshot hook." That invariant is not currently machine-enforced for every hook/harness projection.

### 5.2 Ownership/liveness finding

COS has useful partial signals — worktrees, stashes, task claims, edit locks, heartbeats, branch locks, process hints — but no single authoritative ownership ledger. `cos-doctor-work-inventory --all --json` can fail closed, but it cannot yet prove path ownership such as: "LICENSE is owned by live agent X in worktree Y and preserved on branch Z."

This explains why agents sound over-confident: they can see preservation artifacts, but the OS cannot yet join those artifacts into a robust liveness truth table.

### 5.3 Secret/history/readiness finding

The current HEAD email state is clean, but git history still contains the operator email. Existing primitives are partial:

- credibility audit can catch operator PII in tracked HEAD;
- ADR-218 history sanitization can catch history contamination when configured with the operator email;
- release readiness does not yet compose credibility/history/adoption gates strongly enough to prevent a public release with dirty history.

So the repo can be clean at HEAD and still unsafe to publish. That is a release-readiness composition bug, not just a secret-detector bug.

### 5.4 Source-count / prior-art finding

The research corpus lists 79 sources across official docs, issue trackers, product docs, academic papers, vendor blogs, community reports, and Git/VCS references. It directly covers Claude Code, Codex, OpenCode, Cursor, Devin, OpenHands, SWE-agent, Cline, Continue, Copilot, Replit, Hermes, GitButler, Jujutsu, AutoGen, CrewAI, and LangGraph. OpenClaw was not found as a first-class documented source in the corpus and remains a named gap to verify separately.

The conclusion holds across the corpus: **write-capable agents are isolated by worktree, VM/container/microVM, or shadow-state; they do not normally stash the operator's working tree as a launch primitive.**

---

## 6. Verdict on Cognitive OS

### 6.1 What aligns with prior art (validate, keep)

- **Worktree-aware orchestration** (`.claude/worktrees/<branch>/`): aligns with Claude Code, Cursor, Copilot CLI, OpenCode. Industry consensus.
- **Manifest-backed validation primitives** (ADR-212/215/216/217/218): pattern matches ConTree's deterministic config, Replit's manifest pointers, Anthropic Claude Code's hook framework. Conceptually mainstream; our specific cross-stack discipline is unique but defensible.
- **Hook-enforced gates** (PreToolUse / PostToolUse / SessionStart): same pattern as Claude Code Anthropic SDK, Cursor, OpenCode plugins. Industry-standard layer.
- **Memory layer (Engram)**: parallels Devin's vectorized memory + LangGraph's checkpointers + Hermes' learning loop. We're not unique conceptually; we're another implementation.
- **Permission tiers per agent type** (Explore read-only, others write): universal pattern. Validated.
- **Operator-in-loop for destructive ops** (ADR-055b destructive-git-blocker): aligns with Replit's deterministic OS-level blocks, Cline's YOLO-mode warning, Codex CLI's elevated-perm prompts. Mainstream.
- **Single-branch-per-task hint** (where present in our flows): aligns with Copilot Cloud Agent + Sweep + SWE-agent. Recommend strengthening.

### 6.2 Unique without justification (suspicious — likely wrong)

- **Auto-pre-agent-stash on the operator's working tree** ([pre-agent-snapshot.sh](hooks/pre-agent-snapshot.sh)). No source in this survey showed this. The closest analogue is lint-staged, which is deeply conservative and still treated as risky. This is the bug-source of the current session. The defense ("we want to preserve the operator's WIP if an agent goes rogue") is real but the implementation is wrong: when preflight blocks the agent, the stash orphans (ADR-213 admits the order-of-ops gap), and the user's WT no longer matches what they think.
- **Marker file referencing `stash@{N}`**: same bug Anthropic shipped. Mutable refs as identity is a known footgun. We hit it.
- **Same-worktree concurrent agent execution with stash-based isolation**: industry consensus is one-isolated-mutable-surface-per-write-agent. We try to share the surface and use stash to time-multiplex. This works in low-contention single-agent flows and falls apart at the moment it actually matters (parallelism).
- **Validation-mode lock to suppress stash** (`COS_SUPPRESS_AGENT_SNAPSHOT`): patches the symptom. The disease is "mutation in pre-agent path"; the patch is "skip mutation in some cases." Industry doesn't need this knob because they don't have the original mutation.

### 6.3 Unique with justification (defensible bets, hold)

- **Harness-agnostic governance layer**: no source in this survey showed a system that claims this directly. OpenHands' `BaseWorkspace` is the closest, but it's an SDK for *building* agents. Cognitive OS' bet is that *operators* want a governance layer separable from any specific agent. This is novel and the bet is reasonable. Validation will come from adoption, not from this research.
- **Phase-aware behavior** (reconstruction vs. production): no published prior art. Plausibly real (Anthropic's harness changes between Claude Code versions hint at this) but unvalidated.
- **Cross-stack validation discipline** (one CLI shape `cos <domain> audit --json` across license/secret/adoption/history): no other system has this consistency. Conceptually clean and defensible.
- **MAPE-K self-improvement loop (Singularity)** *if active*: research-grade. Inactive currently, no judgment.

### 6.4 The single biggest unforced error

The session forensics showed:
- 3 `auto-pre-agent-toolu_*` stashes with the same license-switch path set.
- HEAD is ahead of origin and has the preserve-manifest email redaction commit (`02e97bcd`) in the tracked tree.
- Git history remains contaminated with the operator email even though HEAD is clean.
- Runtime snapshot markers stored mutable stash refs such as `stash@{0}`, which can drift when new stashes are pushed.

Mechanism: working-tree changes → Agent launch triggers `pre-agent-snapshot.sh` → `git stash push` → a later PreToolUse-Agent hook blocks the Agent → `PostToolUse` never fires → `post-agent-snapshot-restore.sh` never runs → stash orphans. Repeat per blocked Agent.

This is **exactly** the stash-pop-considered-harmful failure mode that the industry has been documenting since 2012. It is also the exact failure mode `aider --no-dirty-commits` exists to *opt out of*. We re-implemented the canonical wrong primitive and it's biting us in production.

### 6.5 Worst-case interpretation

If we're harsh: **Cognitive OS' agent-lifecycle layer (the auto-pre-agent / post-agent-restore complex) is doing 2010s-era stash-juggling that the field collectively migrated away from.** The rest of the OS (manifests, memory, gates) is fine. The lifecycle layer is the part we should rewrite.

If we're charitable: we're 1–2 cycles behind on a single primitive. The fix is small (worktree-per-write-agent + shadow-state for safety net), and once it lands we're caught up. Nothing else in the OS needs surgery.

---

## 7. Recommendations (ranked by leverage)

### R1. Kill `auto-pre-agent-stash`. Replace with worktree-per-write-agent. **High leverage, medium effort.**

ADR proposal: **ADR-223 — Agent Lifecycle Reconstruction** (new; ADR-220/221/222 already cover tactical pieces).
- Default isolation for write-capable Agent launches: `git worktree add` to a managed location (mirror Claude Code's `.claude/worktrees/`), serialized via a mutex on `git worktree add` to avoid the `.git/config.lock` race ([Claude Code #34645](https://github.com/anthropics/claude-code/issues/34645) Option A).
- Read-only Explore agents skip isolation (universal pattern).
- The user's working tree is **never mutated by agent setup**. `git status` is invariant under launch.
- `auto-pre-agent-stash` deleted. Marker files referencing `stash@{N}` deleted. Post-restore complex deleted.
- Worktree cleanup hook MUST restore `.git/config` (`repositoryformatversion=0`, remove `extensions.worktreeConfig`) — Anthropic shipped this bug, we should not repeat it ([#45645](https://github.com/anthropics/claude-code/issues/45645)).

This is one ADR, ~3 hooks deleted, ~2 hooks rewritten, ~1 new hook (worktree mutex). The current ADR-099 / ADR-117 / ADR-200 / ADR-213 sequence becomes obsolete after migration. Until then, ADR-222 should make stash creation two-phase so no stash exists unless launch is confirmed.

### R2. Optional shadow-state safety net (Cline pattern). **Medium leverage, low effort.**

ADR proposal: **ADR-224 — Shadow-State Snapshots, Off-Repo.**
- Per-agent ephemeral shadow git in `.cognitive-os/shadow/<agent-id>/.git` if write isolation fails or for low-trust scenarios.
- Captures ALL files including untracked, isolated from operator's `.git`.
- Three restore modes (Cline pattern): files only, conversation only, both.
- This replaces the safety-net role auto-stash was supposed to play, with the proper primitive.

### R3. Detect worktree↔main divergence as a first-class signal. **High leverage, low effort.**

Existing proposal: **ADR-220 — Worktree Divergence Audit (`cos worktree audit`)**.
- Detect when worktree branch is N commits behind `main` AND worktree files appear modified (when they're really just stale).
- Detect when `main` modifies paths that the worktree has uncommitted changes for — pre-emptive merge-conflict alert.
- Detect when other linked worktrees have stashes/locks that reference paths in this worktree.
- This is the audit we needed today and didn't have. Low effort, exposes a class of bugs.

### R4. Stash-ref-by-SHA, not by `stash@{N}`. **Low leverage, very low effort.**

Existing proposal: **ADR-221 — Stash Ref by SHA, Not by Position**. If we keep any stash usage at all (e.g. for ADR-117 manual user-commanded stashes), markers must record the stash *SHA* (`git rev-parse stash@{N}`) and look up by SHA. Mutable stash positions are not identities.

### R5. Single-branch-per-task contract option. **Medium leverage, medium effort.**

ADR proposal: **ADR-225 — Branch-Per-Task Mode.**
- Optional mode (off by default) that enforces "one task → one branch → one PR." Mirrors GitHub Copilot Cloud Agent.
- Useful for production-mode work (the 'production' phase in our phase-aware system).
- Reconstruction-phase keeps the looser current default.

### R6. Document the `git worktree add` race + serialize. **Low leverage, very low effort.**

Same fix Claude Code #34645 documents. Add a per-repo lock around `git worktree add` to avoid `.git/config.lock` racing. Trivial, one-time fix.

### R7. Consider Jujutsu (jj) as an opt-in future direction. **Speculative, document-only.**

Jujutsu's auto-snapshot semantics solve the "agent lost my work" problem at the VCS layer. It coexists with git via `jj git init --colocate`. This isn't a near-term move, but documenting it as a future direction (and possibly an opt-in `cos.vcs: jj` mode) hedges against further git-stash workarounds. See [panozzaj's blog](https://www.panozzaj.com/blog/2025/11/22/avoid-losing-work-with-jujutsu-jj-for-ai-coding-agents/) and [agentic-jujutsu](https://smithery.ai/skills/ruvnet/agentic-jujutsu).

### R8. Don't pursue CRDT-based merging. **Anti-recommendation.**

Tempting because it sounds principled. Code is non-commutative; CRDTs don't help. Replit, Devin, Cursor all have CRDT teams next door (Zed-adjacent) and chose not to apply CRDT to agent merges. Save the cycles.

### R9. Honest limitation statement in the README. **Reputation leverage.**

The README should explicitly state what Cognitive OS does and does *not* try to solve. Mature systems all do this. Aider's "*pause concurrent worktrees before rebasing*" warning is a good model. OpenHands' "*does not discuss git operations explicitly*" disclaimer is another. We should match.

---

## 8. Open questions

1. **Phase-aware harness validity** — no published prior art. Does it survive contact with users? Needs evidence; the cleanest experiment is a small operator cohort using both modes.
2. **Cross-harness portability claim** — is there real demand for a harness-agnostic governance layer, or do users always pick a harness and live in it? OpenHands made the SDK-agnostic bet; their adoption is the leading indicator.
3. **Engram vs. external memory backends** — at what scale does Engram pay for itself vs. plugging into Mem0 / Letta / proprietary memory APIs? Defer until ≥10 operator-months of Engram data.
4. **Memory-layer drift during compaction** — Anthropic shipped a compaction bug ([Tessl postmortem](https://tessl.io/blog/anthropic-postmortem-shows-how-small-changes-compounded-into-claude-code-failure/)). We should run our own compaction-correctness tests; this is a class of bug we likely have too.

---

## 9. Sources consulted (79)

Format: URL — one-line takeaway.

### Claude Code
1. [github.com/anthropics/claude-code/issues/34645](https://github.com/anthropics/claude-code/issues/34645) — `git worktree add` parallel race on `.git/config.lock`; closed not-planned; manual cleanup required.
2. [github.com/anthropics/claude-code/issues/45645](https://github.com/anthropics/claude-code/issues/45645) — worktree cleanup leaves `repositoryformatversion=1` breaking other tools.
3. [github.com/anthropics/claude-code/issues/11005](https://github.com/anthropics/claude-code/issues/11005) — stale `.git/index.lock` from CC background ops blocks user.
4. [github.com/anthropics/claude-code/issues/28546](https://github.com/anthropics/claude-code/issues/28546) — Windows-specific stale index.lock.
5. [github.com/anthropics/claude-code/issues/40164](https://github.com/anthropics/claude-code/issues/40164) — `isolation: "worktree"` breaks on Windows.
6. [github.com/anthropics/claude-code/issues/50109](https://github.com/anthropics/claude-code/issues/50109) — request to disable auto-worktree isolation in Desktop.
7. [code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents) — canonical subagent docs; subagents ≠ agent teams (cross-session).
8. [threads.com/@boris_cherny/post/DVAAnexgRUj](https://www.threads.com/@boris_cherny/post/DVAAnexgRUj/introducing-built-in-git-worktree-support-for-claude-code-now-agents-can-run-in) — official launch of CC built-in worktree.
9. [claudefa.st/blog/guide/development/worktree-guide](https://claudefa.st/blog/guide/development/worktree-guide) — community guide; Claude Code worktree pattern.
10. [claudedirectory.org/blog/claude-code-worktrees-guide](https://www.claudedirectory.org/blog/claude-code-worktrees-guide) — 2026 worktree usage guide.
11. [docs.agentinterviews.com/blog/parallel-ai-coding-with-gitworktrees/](https://docs.agentinterviews.com/blog/parallel-ai-coding-with-gitworktrees/) — parallel AI coding via worktrees; custom CC commands.
12. [damiangalarza.com/posts/2026-03-10-extending-claude-code-worktrees-for-true-database-isolation](https://www.damiangalarza.com/posts/2026-03-10-extending-claude-code-worktrees-for-true-database-isolation/) — extending CC worktrees with DB isolation; same problem Trigger.dev had.

### OpenCode / Codex / Anthropic SDK
13. [github.com/sst/opencode](https://github.com/sst/opencode) — opencode README; provider-agnostic, terminal-first.
14. [opencode.ai/docs/agents/](https://opencode.ai/docs/agents/) — subagent definitions, frontmatter, session model.
15. [github.com/kdcokenny/opencode-worktree](https://github.com/kdcokenny/opencode-worktree) — community plugin; auto-spawn terminal, auto-commit on delete.
16. [github.com/kdcokenny/opencode-workspace](https://github.com/kdcokenny/opencode-workspace) — multi-agent orchestration harness for OpenCode.
17. [developers.openai.com/codex/subagents](https://developers.openai.com/codex/subagents) — Codex CLI subagents; `agents.max_threads=6`, `max_depth=1`.
18. [openai.com/index/introducing-the-codex-app/](https://openai.com/index/introducing-the-codex-app/) — Codex app launch; built-in worktrees.
19. [developers.openai.com/codex/cli](https://developers.openai.com/codex/cli) — Codex CLI features; system-level sandboxing.

### Aider / Cursor / Cline / Continue
20. [aider.chat/docs/git.html](https://aider.chat/docs/git.html) — aider git integration; auto-commits, no concurrency story.
21. [github.com/kaeawc/auto-worktree/issues/176](https://github.com/kaeawc/auto-worktree/issues/176) — explicit warning "git not designed for concurrent operations."
22. [cursor.com/docs/configuration/worktrees](https://cursor.com/docs/configuration/worktrees) — Cursor worktree config; cleanup-by-count, no merge-conflict guidance.
23. [forum.cursor.com/t/cursor-2-0-split-tasks-using-parallel-agents-automatically/140218](https://forum.cursor.com/t/cursor-2-0-split-tasks-using-parallel-agents-automatically-in-one-chat-how-to-setup-worktree-json/140218) — Cursor 2.0 parallel agents setup.
24. [forum.cursor.com/t/git-lock-file-issue-in-cursor/149747](https://forum.cursor.com/t/git-lock-file-issue-in-cursor/149747) — Cursor reproduces the index.lock bug.
25. [docs.cline.bot/features/checkpoints](https://docs.cline.bot/features/checkpoints) — Cline shadow-git; 3 restore modes.
26. [github.com/cline/cline/wiki/Installing-Git-for-Checkpoints](https://github.com/cline/cline/wiki/Installing-Git-for-Checkpoints) — shadow-repo install requirement.
27. [docs.continue.dev/agents/intro](https://docs.continue.dev/agents/intro) — Continue cloud agents.
28. [blog.continue.dev/building-async-agents-with-continue-cli](https://blog.continue.dev/building-async-agents-with-continue-cli) — parallel via shell `&`, no in-process multi-agent.

### Devin / OpenHands / SWE-agent / Sweep / Hermes
29. [cognition.ai/blog/devin-2](https://cognition.ai/blog/devin-2) — Devin 2.0 launch.
30. [cognition.ai/blog/devin-annual-performance-review-2025](https://cognition.ai/blog/devin-annual-performance-review-2025) — VM hypervisor snapshots.
31. [cognition.ai/blog/sept-24-product-update](https://cognition.ai/blog/sept-24-product-update) — early replay timeline.
32. [openhands.dev](https://www.openhands.dev/) — OpenHands platform.
33. [arxiv.org/html/2511.03690v1](https://arxiv.org/html/2511.03690v1) — OpenHands SDK paper; `BaseWorkspace`, defers git concurrency.
34. [github.com/SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent) — SWE-agent; sandboxed shell + lint-checked autosave.
35. [github.com/sweepai/sweep](https://github.com/sweepai/sweep) — Sweep; one-issue-one-PR pattern.
36. [hermes-agent.nousresearch.com/docs/user-guide/features/overview](https://hermes-agent.nousresearch.com/docs/user-guide/features/overview) — Hermes auto-snapshot before edits, `/rollback`.
37. [github.com/NousResearch/hermes-agent](https://github.com/nousresearch/hermes-agent) — Hermes repo.
38. [github.com/SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) — 100-line SWE-agent.

### GitHub Copilot
39. [docs.github.com/copilot/concepts/agents/coding-agent/about-coding-agent](https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent) — Cloud Agent; one branch one PR, GH Actions runner.
40. [kenmuse.com/blog/workspace-vs-worktree-isolation-in-copilot-cli](https://www.kenmuse.com/blog/workspace-vs-worktree-isolation-in-copilot-cli/) — Workspace vs Worktree isolation tradeoff.
41. [github.com/orgs/community/discussions/179403](https://github.com/orgs/community/discussions/179403) — Copilot subagents + worktrees experimentation.
42. [github.com/orgs/community/discussions/182489](https://github.com/orgs/community/discussions/182489) — Copilot subagents are sequential, not parallel.
43. [code.visualstudio.com/docs/copilot/agents/copilot-cli](https://code.visualstudio.com/docs/copilot/agents/copilot-cli) — Copilot CLI sessions in VS Code.

### Replit / GitButler / ConTree / AgentFS / Jujutsu
44. [blog.replit.com/inside-replits-snapshot-engine](https://blog.replit.com/inside-replits-snapshot-engine) — CoW at block-device level, manifest-based snapshots.
45. [docs.replit.com/core-concepts/agent/checkpoints-and-rollbacks](https://docs.replit.com/core-concepts/agent/checkpoints-and-rollbacks) — checkpoint/rollback model.
46. [blog.replit.com/defense-in-depth-how-replit-secures-every-layer-of-the-vibe-coding-stack](https://blog.replit.com/defense-in-depth-how-replit-secures-every-layer-of-the-vibe-coding-stack) — deterministic OS-level blocks > prompt-level safety.
47. [neon.com/blog/replit-app-history-powered-by-neon-branches](https://neon.com/blog/replit-app-history-powered-by-neon-branches) — Neon DB branching for Replit.
48. [trigger.dev/blog/parallel-agents-gitbutler](https://trigger.dev/blog/parallel-agents-gitbutler) — "we ditched worktrees" — 9.82 GB cost, port conflicts, DB sync.
49. [docs.gitbutler.com/features/branch-management/virtual-branches](https://docs.gitbutler.com/features/branch-management/virtual-branches) — virtual branches in single working dir.
50. [news.ycombinator.com/item?id=46031327](https://news.ycombinator.com/item?id=46031327) — GitButler co-founder: "lower likelihood of code diverging semantically" with shared workspace.
51. [github.com/gitbutlerapp/gitbutler/discussions/12228](https://github.com/gitbutlerapp/gitbutler/discussions/12228) — overlapping edits cause races even with virtual branches.
52. [blog.gitbutler.com/gitbutler-agent-assist](https://blog.gitbutler.com/gitbutler-agent-assist) — GitButler Agents Tab; auto AI session per branch.
53. [contree.dev](https://contree.dev/) — Firecracker microVM per execution; immutable FS snapshots.
54. [github.com/tursodatabase/agentfs](https://github.com/tursodatabase/agentfs) — SQLite WAL as filesystem; CoW isolation.
55. [github.com/jj-vcs/jj](https://github.com/jj-vcs/jj) — Jujutsu auto-snapshot every command; corruption-resistant.
56. [panozzaj.com/blog/2025/11/22/avoid-losing-work-with-jujutsu-jj-for-ai-coding-agents](https://www.panozzaj.com/blog/2025/11/22/avoid-losing-work-with-jujutsu-jj-for-ai-coding-agents/) — concrete jj-for-agents recovery scenarios.

### Cross-cutting (stash / lock / harness / postmortems / sandbox)
57. [news.ycombinator.com/item?id=12613062](https://news.ycombinator.com/item?id=12613062) — "more stash accidents than any other kind"; recovery via fsck/reflog is hostile.
58. [codingkilledthecat.wordpress.com/2012/04/27/git-stash-pop-considered-harmful](https://codingkilledthecat.wordpress.com/2012/04/27/git-stash-pop-considered-harmful/) — pop+conflict doesn't drop stash.
59. [git-scm.com/docs/git-stash](https://git-scm.com/docs/git-stash) — official: "If you mistakenly drop or clear stashes, they cannot be recovered."
60. [martinfowler.com/articles/harness-engineering.html](https://martinfowler.com/articles/harness-engineering.html) — Fowler's framing: Agent = Model + Harness; feedforward+feedback controls.
61. [addyosmani.com/blog/agent-harness-engineering](https://addyosmani.com/blog/agent-harness-engineering/) — Osmani: "If you're not the model, you're the harness."
62. [tessl.io/blog/anthropic-postmortem-shows-how-small-changes-compounded-into-claude-code-failure](https://tessl.io/blog/anthropic-postmortem-shows-how-small-changes-compounded-into-claude-code-failure/) — Anthropic Claude Code compaction bug postmortem.
63. [blog.firetiger.com/postmortem-on-the-march-1-2026-ingest-incident](https://blog.firetiger.com/postmortem-on-the-march-1-2026-ingest-incident/) — race condition CI postmortem; AI-assisted recovery.
64. [beam.ai/agentic-insights/multi-agent-orchestration-patterns-production](https://beam.ai/agentic-insights/multi-agent-orchestration-patterns-production) — 40% multi-agent pilots fail in 6 months.
65. [zed.dev/blog/crdts](https://zed.dev/blog/crdts) — Zed CRDT for collaborative editing; not for agent merges.
66. [arxiv.org/html/2602.09345](https://arxiv.org/html/2602.09345) — AgentCgroup; resource contention in multi-tenant agents.
67. [arxiv.org/html/2604.13536v2](https://arxiv.org/html/2604.13536v2) — "Don't Let AI Agents YOLO Your Files"; FS-as-permission-locus.
68. [arxiv.org/pdf/2512.05470](https://arxiv.org/pdf/2512.05470) — Agentic FS Abstraction for Context Engineering.
69. [northflank.com/blog/daytona-vs-e2b-ai-code-execution-sandboxes](https://northflank.com/blog/daytona-vs-e2b-ai-code-execution-sandboxes) — Daytona vs E2B sandbox comparison.
70. [modal.com/blog/top-code-agent-sandbox-products](https://modal.com/blog/top-code-agent-sandbox-products) — sandbox menu 2025.
71. [augmentcode.com/guides/git-worktrees-parallel-ai-agent-execution](https://www.augmentcode.com/guides/git-worktrees-parallel-ai-agent-execution) — best-practice guide; explicit lock-contention warning.
72. [microsoft.github.io/autogen/.../concurrent-agents.html](https://microsoft.github.io/autogen/stable//user-guide/core-user-guide/design-patterns/concurrent-agents.html) — actor model; no fs concurrency.
73. [github.com/microsoft/autogen/discussions/7144](https://github.com/microsoft/autogen/discussions/7144) — shared state across multi-agent conversations.
74. [github.com/crewAIInc/crewAI/issues/1170](https://github.com/crewAIInc/crewAI/issues/1170) — CrewAI: "agent cannot locate a file it just created."
75. [community.crewai.com/t/how-to-ensure-collaboration-file-sharing-between-agents/2224](https://community.crewai.com/t/how-to-ensure-collaboration-file-sharing-between-agents/2224) — CrewAI file-sharing question, no first-class solution.
76. [docs.langchain.com/oss/python/langgraph/graph-api](https://docs.langchain.com/oss/python/langgraph/graph-api) — LangGraph state and reducers.
77. [github.com/MAS-Infra-Layer/Agent-Git](https://github.com/MAS-Infra-Layer/Agent-Git) — Agent-Git overlay for LangGraph; State Commit/Revert.
78. [kareemf.com/on-git-worktrees](https://kareemf.com/on-git-worktrees) — worktree pros and cons for parallel coding.
79. [termdock.com/en/blog/git-worktree-conflicts-ai-agents](https://www.termdock.com/en/blog/git-worktree-conflicts-ai-agents) — diagnosing worktree conflicts.

---

## 10. Methodology notes

- Source accounting: 79 numbered sources, 86 unique URLs, 52 unique domains; roughly 30 of those were deep-read/fetched and the rest were used as corroborating or comparative references.
- Read-only research plus local repository forensics. No code/runtime mutations; documentation edits are limited to this report and companion ADR drafts.
- ~25 distinct WebSearch queries (Claude Code, OpenCode, Codex, Aider, Cursor, Devin, OpenHands, SWE-agent, Cline, Continue, Copilot Workspace, Replit, AutoGen, CrewAI, LangGraph, Claude Agent SDK, plus cross-cutting: git worktree concurrency, git stash automation, sandbox patterns, Trigger.dev, GitButler, Jujutsu, harness engineering, AI postmortems, CRDT, file-locking, stacked diffs, merge-conflict AI). Targeted to find the canonical sources, not exhaustive volume.
- ~30 WebFetch deep reads on the highest-value URLs (GitHub issues for the actual bug behavior, official docs for authoritative model claims, blog posts for "we tried X and it failed" narratives, the GitButler co-founder's HN comment for the contrarian view).
- Where docs are vague, the report says "no public answer found" or "deferred." Three explicit examples: SWE-agent runtime architecture (had to infer from search snippets, repo README was promotional), GitHub Copilot Cloud Agent concurrency between tasks (docs silent), Devin 2.0 architecture (blog focuses on UX features, not infra).
- Honest about uncertainty: Cognition admits Devin's snapshot infra "took longer than any other piece of infrastructure they had shipped" — a non-trivial signal that this is hard, not a marketing claim.
- Avoided sycophancy. Where Cognitive OS aligns with the field, said so. Where it doesn't (auto-stash), said so directly. Where the user's working hypothesis ("we're being over-optimistic") is supported by evidence, said so. Where it isn't (the rest of the OS), pushed back.

---

*End of research report. ~10,000 words. 79 sources cited.*
