# Cognitive OS: Adoption Tiers

> Who should enable what, and in what order.

This document maps three concrete adoption tiers — **lean**, **standard**, and
**strict** — to the specific hooks, library primitives, and skills that make
sense at each level. Each tier is grounded in verified file paths and the ADRs
that motivated each piece.

Audience: a developer who has never used the OS and is deciding whether to
adopt it and how much of it to turn on.

---

## Decision tree — start here

Answer these questions in order. Stop when you reach a tier.

```
1. Do you run more than one agent session at a time?
   NO  → go to question 2
   YES → go to question 3

2. Are you prototyping and iteration speed matters more than safety?
   YES → consider NOT using the OS (see Anti-patterns below)
   NO  → LEAN

3. Are you one person running multiple IDEs/harnesses (for example
   Claude Code + Codex), multiple simultaneous sessions, or multiple agents
   across more than one project?
   YES → STRICT, even if the "team size" is one
   NO  → go to question 4

4. Is your team larger than 5 people, or do you run 5+ agents concurrently?
   NO  → STANDARD
   YES → STRICT

5. (STRICT check) Does your organization prohibit pre-commit hooks
   or pre-tool-use hooks?
   YES → the OS is not a fit (see Anti-patterns below)
   NO  → STRICT
```

---

## Tier overview

| | Lean | Standard | Strict |
|---|---|---|---|
| Target team size | 1 developer | 2-5 developers | 5+ or enterprise, including a solo maintainer operating a multi-IDE swarm |
| Concurrent sessions | 1 | occasional parallel | 5+ simultaneous, or multiple harnesses/projects controlled by one operator |
| Hooks wired | ~72 (minimal profile) | ~107 (standard profile) | ~123 (paranoid profile) |
| Setup time | 15-30 min | 45-90 min | 2-4 hours |
| Primary ADRs | ADR-105, ADR-121 §4 | + ADR-116, ADR-119, ADR-122 | + ADR-116 full, ADR-121 all |
| Kill problems | Silent WIP loss, agent commits to main | + duplicate claims, stale sessions, orphaned commits | + multi-agent races, merge collisions, chaos-level failures |
| Primary cost | ~72 hook fires/turn | ~107 hook fires/turn | ~123 hook fires/turn + engram I/O |

---

## Lean — Solo developer, 1 session at a time

### Target user

One developer, one IDE, one active agent session. Your priority is iteration
speed. You want to prevent the worst agent failures (WIP loss, bad commits to
main, leaked credentials) without adding ceremony for low-risk work.

Important carve-out: **solo developer does not automatically mean Lean**. If one
operator runs Claude Code and Codex at the same time, opens multiple concurrent
sessions, or delegates to multiple agents across multiple projects, that operator
is no longer in the Lean risk model. That is a solo swarm and should use Strict
or a Strict-derived maintainer profile.

### What it prevents

- Agent silently commits directly to `main` (ADR-116 P2.1, `direct-main-guard.sh`)
- Agent overwrites working-tree changes via destructive git operations (`destructive-git-blocker.sh`)
- Concurrent writes to the same file in the same session (`concurrent-write-guard.sh`)
- Secrets written to disk during Edit/Write calls (`secret-detector.sh`)
- Runaway agent creates lethal tool sequences (`lethal-trifecta-gate.sh`)
- Claim without verification — orchestrator produces false "done" (`orchestrator-claim-gate.sh`, ADR-105)
- WIP lost across session restarts — stash auto-reapplied on session resume (`session-start-stash-reapply.sh`, ADR-099/P4.3)
- Crash leaves the session in unknown state (`crash-recovery.sh`)
- Validation locks left dangling from a previous session (`validation-lock-cleanup.sh`)

### What it does NOT prevent

- Two sessions writing to the same branch simultaneously (no task-claim ledger, no per-session branches)
- Duplicate task claims across sessions (need Standard for P1.1)
- Orphaned commits after rebase (need Standard for full orphan detection)
- Accumulated stale session filesystem artifacts (need Standard for the FS reaper)

### Hook list (lean / minimal security profile)

These are the hooks present in `templates/security-profiles/minimal.json`
(`_hook_count: 72`). Enable by copying that profile into `.claude/settings.json`
or running the installer.

**SessionStart** (fires once per session open):

| Hook | Purpose |
|---|---|
| `hooks/self-install.sh` | Verifies hook projection is current on each start |
| `hooks/session-init.sh` | Writes session marker, initializes runtime state |
| `hooks/host-tool-doctor.sh` | Checks `jq`, `flock`, `git` presence (async) |
| `hooks/crash-recovery.sh` | Detects and logs prior crash state before continuing |
| `hooks/session-resume.sh` | Reattaches to prior session context if present |
| `hooks/session-sanity.sh` | Validates config invariants before work begins |
| `hooks/validation-lock-cleanup.sh` | Removes dangling validation locks from dead sessions |
| `hooks/session-start-stash-reapply.sh` | Auto-reapplies stashes with matching session provenance |

**UserPromptSubmit** (fires on every user message):

| Hook | Purpose |
|---|---|
| `hooks/user-prompt-capture.sh` | Archives prompts for audit and memory recall (async) |
| `hooks/session-wrapup-trigger.sh` | Triggers wrapup summary on session close signals (async) |
| `hooks/memory-prefetch.sh` | Pre-fetches Engram context for the incoming prompt (async) |
| `hooks/stash-budget-warn.sh` | Warns if stash count exceeds safe threshold (async) |
| `hooks/concurrent-write-guard-codex-proxy.sh` | Codex-harness concurrent-write interlock |

**SubagentStart** (fires when a sub-agent is dispatched):

| Hook | Purpose |
|---|---|
| `hooks/subagent-context-injector.sh` | Injects session context into sub-agent prompt (async) |

**PreCompact** (fires before context compaction):

| Hook | Purpose |
|---|---|
| `hooks/pre-compaction-flush.sh` | Flushes pending observations to Engram before compaction |

**PreToolUse** (fires before every tool call):

| Hook | Matcher | Purpose |
|---|---|---|
| `hooks/lethal-trifecta-gate.sh` | `*` | Blocks the dangerous combination of sensitive data + external communication (see `docs/security/lethal-trifecta-gate.md`) |
| `hooks/rate-limiter.sh` | `Bash\|Agent\|Edit\|Write` | Token-bucket rate control |
| `hooks/destructive-git-blocker.sh` | `Bash` | Blocks dangerous git operations (force-reset, force-push to main) |
| `hooks/symlink-mutation-guard.sh` | `Bash` | Guards against accidental symlink mutations |
| `hooks/scope-marker-portability-gate.sh` | `Bash` | Enforces OS vs project scope markers |
| `hooks/git-commit-scope-guard.sh` | `Bash` | Validates commit scope before it lands |
| `hooks/direct-main-guard.sh` | `Bash` | Blocks agent commits directly to main/master |
| `hooks/orchestrator-claim-gate.sh` | `Bash` | Bilateral claim verification (ADR-105) |
| `hooks/pre-commit-content-hash-dedupe.sh` | `Bash` | Rejects duplicate-content commits |
| `hooks/large-file-advisor.sh` | `Read` | Warns before reading very large files |
| `hooks/secret-detector.sh` | `Edit\|Write` | Detects credentials before write |

**PostToolUse** (fires after tool calls):

| Hook | Matcher | Purpose |
|---|---|---|
| `hooks/error-pipeline.sh` | `Bash` | Routes errors to structured error log |
| `hooks/result-truncator.sh` | `Bash` | Truncates oversized tool results |
| `hooks/error-learning.sh` | `Bash` | Persists error patterns for deduplication |
| `hooks/post-git-orphan-notifier.sh` | `Bash` | Detects orphaned commits post-rebase |
| `hooks/post-agent-snapshot-restore.sh` | `Agent` | Restores pre-agent snapshots after completion |
| `hooks/auto-rollback-trigger.sh` | `Agent` | Triggers rollback if agent exit state is bad |

**Stop** (fires when session ends):

| Hook | Purpose |
|---|---|
| `hooks/session-wrapup-trigger.sh` | Final wrapup flush |

### Active primitives (lean)

| Primitive | Role |
|---|---|
| `lib/session_lifecycle.py` | Session state machine and archive decisions (ADR-119) |
| `lib/stash_provenance.py` | Stash metadata for auto-reapply (ADR-099/P4.3) |
| `lib/concurrent_agent_safety_status.py` | Single-session concurrent-write status |
| `scripts/cos_work_inventory.py` | Read-only session/WIP inventory (ADR-119) |

### Skills useful at lean tier

| Skill | When to use |
|---|---|
| `skills/auto-rollback/` | After a bad agent run — deterministic undo |
| `skills/run-tests/` | Verify state after agent edits |
| `skills/session-wrapup/` | Explicit session summary and Engram flush |
| `skills/smoke-test/` | Quick confidence check before a commit |

### Setup

```bash
# 1. Install the OS
bash install.sh

# 2. Apply the minimal security profile
cp templates/security-profiles/minimal.json .claude/settings.json

# 3. Verify hook projection
bash hooks/self-install.sh

# 4. Verify session inventory is reachable
python3 scripts/cos_work_inventory.py --json | \
  python3 -c "import sys,json; d=json.load(sys.stdin); \
  print('Sessions:', d['session_fs_stats']['session_dir_count'])"
```

### Overhead at lean tier

- ~72 hook fires per agent turn
- `session-init.sh` + `crash-recovery.sh` add ~200ms to session open
- `destructive-git-blocker.sh` adds ~50ms per Bash call (checks command string)
- `secret-detector.sh` adds ~100ms per Edit/Write call (regex scan)
- No background daemons required at lean tier (Engram optional)
- Disk overhead: `.cognitive-os/sessions/` grows ~5 KB/session; the FS reaper
  (available at Standard) manages volume accumulation

---

## Standard — Small team, occasional parallel sessions

### Target user

Two to five developers sharing a repo, or a solo developer who runs parallel
agent sessions (e.g., one Claude Code window + one Codex session, or multiple
terminal sessions). You need coordination across sessions without manually
choreographing who owns what.

### What it adds over lean

- Preflight gate before every sub-agent launch — dirty linked worktrees on the
  same branch block dispatch (ADR-116, ADR-122, `agent-prelaunch.sh`)
- Task-claim ledger — atomic flock-guarded claims; duplicate task IDs rejected at
  submission time (ADR-116 P1.1, `lib/task_claim_ledger.py`)
- Session event bus — append-only event log so sessions can observe each other's
  claims and commits (ADR-116 P1.3, `lib/session_bus.py`)
- Per-session branch guard — sub-agents blocked from committing directly to main;
  operators warned (ADR-116 P2.1, `hooks/direct-main-guard.sh` block mode for agents)
- FS reaper — archive-first cleanup of stale session directories, no accidental
  deletion of pending work (ADR-119, `lib/session_lifecycle.py`)
- Stash auto-reapply with provenance — wiped WIP is restored on next session open
  (ADR-116 P4.3, `hooks/session-start-stash-reapply.sh`)
- Engram memory — cross-session persistent context, claim source-of-truth for P5.1
  (`hooks/engram-daemon-launcher.sh`)
- Blast radius gate before agent dispatch (`hooks/blast-radius.sh`)
- Clarification gate before ambiguous agent dispatch (`hooks/clarification-gate.sh`)
- Agent preflight check with read-only sub-agent recognition (ADR-122)
- Infra health check on session open (`hooks/infra-health.sh`)
- Coordination status CLI — single-command multi-session state view (ADR-116 P3.3,
  `scripts/cos-coordination-status.sh`)

### What it does NOT prevent

- Concurrent landings to main without a merge queue (need Strict for P2.2)
- Cross-machine coordination (Engram is single-host at this tier)
- Chaos-level swarm races (need Strict chaos validation)

### Hook list (standard security profile)

`templates/security-profiles/standard.json` (`_hook_count: 107`).

Inherits all lean hooks plus the following additions.

**SessionStart additions:**

| Hook | Purpose |
|---|---|
| `hooks/profile-drift-autoapply.sh` | Detects and repairs hook projection drift automatically |
| `hooks/engram-daemon-launcher.sh` | Starts the Engram memory daemon (async) |
| `hooks/infra-health.sh` | Dependency health check on session open (async) |

**PreToolUse[Agent] additions:**

| Hook | Purpose |
|---|---|
| `hooks/dispatch-gate.sh` | Rate/quota check before agent dispatch |
| `hooks/clarification-gate.sh` | Requires clarification for ambiguous tasks |
| `hooks/blast-radius.sh` | Estimates file-count impact before dispatch |
| `hooks/inject-phase-context.sh` | Injects SDD phase context into sub-agent prompt |
| `hooks/agent-working-dir-inject.sh` | Locks working directory for sub-agent |
| `hooks/query-tailored-context-inject.sh` | Pulls relevant Engram context for the query |
| `hooks/pre-agent-snapshot.sh` | Snapshots WIP before agent modifies working tree (ADR-099) |
| `hooks/agent-prelaunch.sh` | Full preflight gate — race detection, read-only recognition (ADR-116/ADR-122) |
| `hooks/error-pattern-detector.sh` | Checks for known error patterns before dispatch |
| `hooks/reinvention-check.sh` | Warns if task likely duplicates an existing skill |

**PostToolUse[Agent] additions:**

| Hook | Purpose |
|---|---|
| `hooks/post-agent-verify.sh` | Runs acceptance-criteria verification after agent completes |
| `hooks/agent-checkpoint.sh` | Checkpoints agent output before next step |

**Stop additions:**

| Hook | Purpose |
|---|---|
| `hooks/auto-checkpoint.sh` | Creates checkpoint artifact on session end |
| `hooks/code-review-on-commit.sh` | Triggers automated code review after commits |
| `hooks/aguara-scan.sh` | Security scan of changed files (189-rule set) |

### Active primitives (standard)

Inherits lean primitives plus:

| Primitive | Role |
|---|---|
| `lib/task_claim_ledger.py` | Atomic local task-claim store; flock-guarded (ADR-116 P1.1) |
| `lib/session_bus.py` | Append-only cross-session event bus (ADR-116 P1.3) |
| `lib/merge_queue.py` | Merge queue machinery (available, not default-on until Strict) |
| `lib/engram_claims.py` | Engram-backed claim SoT for cross-worktree visibility (ADR-116 P5.1) |
| `scripts/claim_task.py` | CLI entry point for atomic task claiming |
| `scripts/cos-coordination-status.sh` | Multi-session status: sessions, claims, stashes, orphan commits, race score |

### Skills useful at standard tier

Inherits lean skills plus:

| Skill | When to use |
|---|---|
| `skills/branch-worktree-closure/` | Clean up agent worktrees and branches after work lands |
| `skills/session-manager/` | Cross-session state inspection and handoff |
| `skills/session-backlog/` | Recover pending work from previous sessions |
| `skills/session-report-executive/` | Cross-session summary for handoffs |
| `skills/coordination-status/` | Inspect live race-risk score and active claims |
| `skills/component-reality-check/` | Audit which hooks and primitives are actually wired |
| `skills/invariant-check/` | Run ADR-121 invariant assertions |

### Setup

```bash
# 1. Install the OS
bash install.sh

# 2. Apply the standard security profile
cp templates/security-profiles/standard.json .claude/settings.json

# 3. Enable coordination features in cognitive-os.yaml
#    Set these flags under the multi_session: key:
#      task_claim_ledger: true      # P1.1
#      session_event_bus: true      # P1.3
#      coordination_status_cli: true  # P3.3 (already default-on)

# 4. Start Engram daemon (required for P5.1 claims)
bash hooks/engram-daemon-launcher.sh

# 5. Verify multi-session state surface
bash scripts/cos-coordination-status.sh

# 6. Run preflight smoke test
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

### Overhead at standard tier

- ~107 hook fires per turn
- `agent-prelaunch.sh` adds ~400ms per sub-agent dispatch (preflight inventory)
- `pre-agent-snapshot.sh` adds ~200ms + disk per agent call
- `engram-daemon-launcher.sh` starts one background process per session
- Engram writes: ~5-10 per session at normal workload
- Disk: `.cognitive-os/tasks/active-claims.json` + session event bus JSONL;
  reaper runs at session close to archive stale session directories

---

## Strict — Enterprise agentic / multi-IDE swarm

### Target user

Five or more parallel agent sessions, multiple IDEs, or a team with more than
five developers. This tier also covers the solo maintainer swarm: one operator
running Claude Code and Codex, multiple simultaneous sessions, multiple
sub-agents, and multiple consumer projects while building the OS itself. You are
running the OS as production-grade infrastructure where a merge collision,
duplicate claim, orphaned commit, silent stash, or false-done report has
measurable cost. You need the full ADR-116 primitive set, chaos validation, and a
serialized landing path to main.

### What it adds over standard

- Full merge queue — only `scripts/merge-to-main.sh` may advance main; concurrent
  attempts serialized via `.cognitive-os/runtime/main-merge.lock` (ADR-116 P2.2,
  `lib/merge_queue.py`)
- Work-identity fingerprinting — commit aborted if `sha256(task_id || diff)`
  matches last 200 commits on origin/main (ADR-116 P1.2)
- Push-time collision detection — pre-push check for subject+content collision
  against remote (ADR-116 P4.2)
- Content-hash dedupe at pre-commit — `git patch-id` comparison against recent
  origin/main (ADR-116 P4.1)
- Orphan-commit notifier — automatic alarm after every rebase for unreachable
  commits (ADR-116 P3.1, `hooks/post-git-orphan-notifier.sh`)
- Plan-claim validator in block mode — checkbox transitions without verified
  evidence are rejected at commit time (ADR-116 P4.4, `hooks/plan-claim-validator.sh`)
- Stale-task watermark — reaper marks tasks done-by-other-session when a matching
  commit arrives (ADR-116 P1.4)
- Engram advisory locks — logical cross-session resource locks backed by Engram
  (ADR-116 P5.2, `lib/engram_claims.py`)
- Validation capsule full mode default-on — every sub-agent dispatch runs in a
  worktree-isolated capsule (ADR-116 P2.3, ADR-109)
- Chaos validation lane — swarm tests exercise concurrent agents, validation,
  cleanup, merge, and reaper races (ADR-121 §6)
- Guard maturity enforcement — no hook may default to block without tests for
  false positives (ADR-121 §4, ADR-123 §1)
- Aguara full scan (189-rule set) on every Stop event
- Full ADR-121 invariants: validation capsules as protected transactions,
  single-writer main, WIP ownership, guard maturity, lane taxonomy, chaos coverage

### What it does NOT prevent

- Cross-machine coordination (multi-host Engram is a separate ADR)
- Remote provider failure — strict requires vendor-native branch protection or
  server-side hooks per ADR-116 §P2.2a; local merge queue is the fallback,
  not the primary guarantee

### Hook list (strict / paranoid security profile)

`templates/security-profiles/paranoid.json` (`_hook_count: 123`).

Inherits all standard hooks plus the following additions.

**Commit-time gates:**

| Hook | Purpose |
|---|---|
| `hooks/plan-claim-validator.sh` | Block mode — rejects unverified checkbox transitions (ADR-116 P4.4) |

Note: `hooks/post-git-orphan-notifier.sh` is already wired at lean, but at
strict tier it also writes to the session bus and to Engram (ADR-116 P3.1 full
contract requires P1.3 bus to be active).

**Agent dispatch (PreToolUse[Agent]) behavior change:**

At strict tier, `agent-prelaunch.sh` runs with `COS_PREFLIGHT_STRICT=1`, which
disables ephemeral path filtering and read-only sub-agent exemptions (ADR-122
kill-switch). Every worktree race risk is treated as BLOCK regardless of the
agent role.

**PostToolUse additions:**

| Hook | Purpose |
|---|---|
| `hooks/auto-verify.sh` | Runs acceptance criteria on every agent completion |

**Stop additions:**

| Hook | Purpose |
|---|---|
| `hooks/aguara-scan.sh` | Full 189-rule security scan on session end (also active at Standard) |

### Active primitives (strict)

Inherits standard primitives plus:

| Primitive | Role |
|---|---|
| `lib/merge_queue.py` | Serialized main-landing with flock lock (ADR-116 P2.2) |
| `lib/engram_claims.py` | Cross-worktree claim SoT + advisory locks (ADR-116 P5.1/P5.2) |
| `lib/capability_levels.py` | Runtime capability level enforcement (L3/L4 modes) |
| `lib/agent_health_monitor.py` | Continuous health tracking across concurrent agent sessions |
| `scripts/merge-to-main.sh` | The only sanctioned path to advance main |
| `scripts/cos_work_inventory.py --strict` | Full preflight inventory with no exemptions |

### Configuration flags (cognitive-os.yaml at strict tier)

```yaml
multi_session:
  task_claim_ledger: true           # P1.1
  work_fingerprint: true            # P1.2
  session_event_bus: true           # P1.3
  stale_task_watermark: true        # P1.4
  per_session_branches: true        # P2.1
  merge_queue: true                 # P2.2
  validation_capsule_full_mode: true  # P2.3
  orphan_commit_notifier: true      # P3.1
  destructive_git_guard: true       # P3.2
  coordination_status_cli: true     # P3.3
  patch_id_dedupe: true             # P4.1
  push_collision_detection: true    # P4.2
  plan_validator_block_mode: true   # P4.4
  stash_auto_reapply: true          # P4.3
  engram_claims_sot: true           # P5.1
  engram_advisory_locks: true       # P5.2
```

### Skills useful at strict tier

Inherits standard skills plus:

| Skill | When to use |
|---|---|
| `skills/cognitive-os-status/` | Full OS health report across all active sessions |
| `skills/docs-execution-audit/` | Audit that every documented primitive is actually wired |
| `skills/invariant-check/` | Assert all ADR-121 invariants are satisfied |
| `skills/cognitive-os-test/` | Run the full chaos validation suite |

### Setup

```bash
# 1. Install the OS
bash install.sh

# 2. Apply the paranoid security profile
cp templates/security-profiles/paranoid.json .claude/settings.json

# 3. Enable all ADR-116 primitives (edit cognitive-os.yaml as shown above)

# 4. Enable strict preflight mode (add to shell env or cognitive-os.yaml)
export COS_PREFLIGHT_STRICT=1

# 5. Verify the merge queue is operational
bash scripts/merge-to-main.sh --dry-run

# 6. Run full validation suite
python3 -m pytest tests/audit/test_adr_contracts.py -q
python3 -m pytest tests/contracts/test_task_claim_ledger.py -q
python3 -m pytest tests/contracts/test_orchestrator_verify.py -q
make test-laptop

# 7. Run chaos validation
python3 -m pytest tests/chaos/ -q
```

### Overhead at strict tier

- ~123 hook fires per turn
- `agent-prelaunch.sh --strict` adds ~600ms per sub-agent dispatch
- `merge-to-main.sh` acquires a flock before every main landing; adds 1-5s
  per landing
- Engram becomes a hot-path dependency: claim writes + advisory lock acquires
  on every task dispatch
- At peak (10 sub-agents x 5 events/min) Engram sees ~50 writes/min — measure
  throughput before enabling P5.1/P5.2 at scale (ADR-116 open question §1)
- Chaos suite runtime: ~20-40 min (lane taxonomy from ADR-121 §5 separates it
  from the fast lane)

---

### Solo maintainer swarm is Strict, not Lean

The common adoption mistake is to classify by headcount only. Cognitive OS should
classify by **concurrency and blast radius**. A single developer can still have a
Strict problem when they operate:

- two or more IDEs/harnesses, such as Claude Code and Codex;
- multiple simultaneous sessions against the same repository;
- multiple sub-agents inside those sessions;
- the OS itself plus several consumer projects;
- long-running WIP where a silent stash, rebase, or false-done can erase days of
  reasoning.

For that persona, vanilla harness primitives are not enough. The required value
is not bureaucracy; it is determinism pressure: task ownership, protected
landing, derived-artifact gates, symmetric WIP recovery, work inventory, event
signals, and repair-first diagnostics. The goal is to make agent concurrency
boring enough that one operator can safely run what otherwise behaves like a
small engineering organization.

## Migration path — graduating between tiers

The OS is additive. Each tier adds hooks and flips feature flags; nothing in
the previous tier is removed.

### Lean to Standard

1. Swap the security profile:
   ```bash
   cp templates/security-profiles/standard.json .claude/settings.json
   ```
2. In `cognitive-os.yaml`, enable:
   ```yaml
   multi_session:
     task_claim_ledger: true
     session_event_bus: true
   ```
3. Start the Engram daemon: `bash hooks/engram-daemon-launcher.sh`
4. Verify with: `bash scripts/cos-coordination-status.sh`

No re-install required. The `profile-drift-autoapply.sh` hook detects and
repairs projection drift automatically on next session open.

### Standard to Strict

1. Swap the security profile:
   ```bash
   cp templates/security-profiles/paranoid.json .claude/settings.json
   ```
2. Enable the remaining ADR-116 flags in `cognitive-os.yaml` (P1.2, P2.1,
   P2.2, P2.3, P3.1, P3.2, P4.1, P4.2, P4.4, P5.1, P5.2 — see Strict
   configuration block above).
3. Set `COS_PREFLIGHT_STRICT=1` in your environment.
4. Run the merge queue smoke test: `bash scripts/merge-to-main.sh --dry-run`
5. Run the ADR contract suite:
   `python3 -m pytest tests/audit/test_adr_contracts.py -q`

Flags default to `false` until explicitly enabled. Rollback at any point = flip
the flag back to `false` and remove the hook registration. No database
migrations, no schema changes.

---

## Anti-patterns — when NOT to use the OS

### 1. Single developer, single agent, prototyping speed matters more than safety

The OS fires hooks on every tool call. At lean tier that is ~72 fires; even
async hooks add latency. If you are in a tight creative loop — generating
scaffolds, discarding them, regenerating — the per-call overhead trains you to
work around the guards rather than with them.

Use the OS when you need the session to survive a mistake, not when you are
deliberately making mistakes to explore an idea. Raw Claude Code or Codex
without COS is the right tool for pure exploration.

Signal that you are in this category: you find yourself setting
`COS_ALLOW_DESTRUCTIVE=1` on every other command.

### 2. CI-only environment with no human in the loop

The OS is designed for interactive sessions where an operator can respond to a
block, approve a repair, or examine a coordination-status report. CI pipelines
run as unattended jobs with no operator. The claim-gate, clarification-gate,
and blast-radius hooks emit blocking output that a CI runner cannot respond to.
The session reaper's grace period and archive logic assume a human will
eventually look at the output.

Using the OS in a fully headless CI context means either bypassing every
interactive gate (defeating the purpose) or hanging the pipeline on prompts
that never get answered.

Signal: you need to set 10+ `COS_*=bypass` environment variables to make CI
pass.

### 3. Organization with a hard policy prohibiting pre-commit or pre-tool-use hooks

The OS's safety guarantees rest on `PreToolUse` hooks (`destructive-git-blocker`,
`secret-detector`, `lethal-trifecta-gate`, `direct-main-guard`) and on
`SessionStart` hooks (`crash-recovery`, `session-init`). If your organization's
security policy or corporate harness configuration disables or sandboxes
pre-tool-use hooks, these guards cannot fire.

The OS will appear to install and run but the claimed safety properties will
not hold. Verify hook execution with `bash hooks/self-install.sh` and confirm
the hooks surface appears in the harness event log before trusting any tier's
guarantees.

Signal: `bash hooks/self-install.sh` reports hooks registered but
`hooks/session-sanity.sh` exits non-zero on every session open.

---

## Comparison table

| Dimension | Lean | Standard | Strict |
|---|---|---|---|
| Security profile file | `minimal.json` | `standard.json` | `paranoid.json` |
| Hook count | 72 | 107 | 123 |
| ADR-116 primitives active | None (P2.1 warn-only for agents) | P1.1, P1.3, P3.3, P4.3, P5.1 | All 12 (P1.1-P5.2) |
| ADR-121 invariants covered | §4 guard maturity (observe/warn only) | + §3 WIP ownership | All 6 invariants |
| ADR-122 preflight refinements | Not applicable (no sub-agent preflight) | Active with ephemeral filter and read-only exemption | Active with `COS_PREFLIGHT_STRICT=1` |
| ADR-119 FS reaper | Read-only inventory only | Archive-first reaper active | Archive-first reaper + volume alarm |
| ADR-105 claim gate | Active (`orchestrator-claim-gate.sh`) | Active | Active + plan-claim-validator block mode |
| Engram required | No (optional) | Yes (daemon for P5.1) | Yes (hot-path for P5.1/P5.2) |
| Merge queue | No | No | Yes (`scripts/merge-to-main.sh`) |
| Chaos validation | No | No | Yes (`tests/chaos/`) |
| Setup time | 15-30 min | 45-90 min | 2-4 hours |
| Kill problems prevented | WIP loss, bad commits, secrets | + duplicate claims, orphaned commits, stale sessions | + merge collisions, fingerprint dupes, swarm races |
| Hook fires per turn | ~72, 0 daemons | ~107, 1 daemon (Engram) | ~123, Engram hot-path |
| Rollback cost | Swap `settings.json` | Swap `settings.json` + flip 5 flags | Swap `settings.json` + flip 16 flags |

---

## Related documents

- `docs/adrs/ADR-105-claim-verification-contract.md` — bilateral claim gate
- `docs/adrs/ADR-116-multi-session-coordination-primitives.md` — all 12 coordination primitives
- `docs/adrs/ADR-119-session-filesystem-reaper.md` — archive-first session cleanup
- `docs/adrs/ADR-121-foundation-hardening-program.md` — 6 invariants
- `docs/adrs/ADR-122-preflight-gate-refinements.md` — false-positive reduction + kill-switch
- `docs/adrs/ADR-123-operational-stability-friction-reduction.md` — guard maturity, adaptive profiles
- `docs/hook-security-profiles.md` — profile design rationale
- `docs/getting-started.md` — first-time install guide
- `docs/architecture/cross-harness-authoring.md` — multi-harness model

---

<!-- Generated from 2f1436d7 on 2026-05-06T04:48:56Z. Do not edit directly. Run `python3 scripts/render_adoption_tiers.py` to regenerate. -->
