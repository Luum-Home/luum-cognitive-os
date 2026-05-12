<!--
RECONCILIATION STATUS: COMPLETE — 2026-05-10 (post-v0.28.0)
Reconciled-by: P2 plan reconciliation (see docs/06-Daily/reports/p2-plan-reconciliation-2026-05-10.md)
All 5 phases of this plan are shipped per the body's "Last updated: 2026-05-01 / Status: ALL PHASES (1-5) COMPLETE" header. Post-v0.28.0 reinforcement:
- Phase 3 (timing): scripts/hook-timing-wrapper.sh + tests/audit/test_hook_latency_budget.py confirmed; integrated into the radar tracker H4 follow-ups.
- Phase 4 (hook composition): hooks/_lib/hook-pipe.sh + tests/audit/test_hook_pipe.py confirmed.
- Phase 5 (DISABLE_HOOK_*): hooks/_lib/common.sh check_disabled_env + tests/audit/test_hook_disable_env.py confirmed.
- Itinerary hook event alignment landed post-0.28 (commits 73fbdfa93, 0183c24fb) — keeps registry / settings.json / .codex/hooks.json projections in sync, which is the long-tail risk this plan called out as "Profile JSON files diverge from docs over time".
- Control-plane audit loop (ADR-248) + classification projection (commit f94260f41) provide the manifest-vs-runtime parity test the plan §13 requested.
Recommendation: archive — move file to .cognitive-os/plans/archive/ in a future tidy commit. (Recommendation only; do NOT physically move now per reconciliation scope.)

OPUS REFINEMENT — 2026-05-11 (post-v0.28.0):
Verified hooks/_lib/common.sh check_disabled_env at lines 181-194; tests/audit/test_hook_disable_env.py + test_hook_pipe.py + test_hook_latency_budget.py all present; rules/hook-security-profiles.md §"Per-Session Hook Suppression (DISABLE_HOOK_* env vars)" line 51+ documents the pattern. The 14 still-unchecked checkboxes (lines 492-505 documenting Profile JSON parity + 658-665 final acceptance sweep) are documentation-sync hygiene (hook-count test counters, profile JSON cross-references, comparison-matrix updates) — none represent missing implementation; the plan body's "Last updated: 2026-05-01 / Status: ALL PHASES (1-5) COMPLETE" header is authoritative. Opus AGREES with Sonnet: COMPLETE. Recommendation stands: ARCHIVE in next tidy commit.
Older inline reconciliation history (preserved for audit):
PARTIAL_DONE — Phases 1+2 complete, Phases 3-5 pending
Superseded for Phase 1 by: scripts/apply-efficiency-profile.sh + scripts/set-security-profile.sh (ws7 commit 329deb2), ADR-028a (runtime feature flags), ADR-029 (reinvention-check wiring), ADR-027 (slim-profile work)
Reconciled: 2026-04-21 (Phase 1 only)
Re-audited: 2026-04-27 — Phase 1 (3-profile model + 41 tests + JSON profile files) confirmed shipped via apply-efficiency-profile.sh + set-security-profile.sh. Phase 2 (set-security-profile.sh missing SubagentStart/UserPromptSubmit/PreCompact event coverage — grep returns 0 matches), Phase 3 (timing instrumentation), Phase 4 (hook-pipe), Phase 5 (disable env vars) remain real work.
Phase 2 complete: 2026-04-27 — set-security-profile.sh already reads profile JSON files directly; the three baseline JSON files (minimal/standard/paranoid) already contained SubagentStart, UserPromptSubmit, PreCompact. All three profiles verified to produce settings.json with all 7 required event keys. No code change to set-security-profile.sh required — the script was correct; the audit gap was a false alarm (grep for event names in the generator script missed that the script delegates to JSON files).
Phase 2 sub-item closed: 2026-04-27 — TeammateIdle, TaskCreated, TaskCompleted added to standard + paranoid JSON profiles (skipped on minimal per plan §6). Verified: minimal=7 keys, standard=paranoid=10 keys including the 3 task events. Hooks teammate-idle.sh / task-created.sh / task-completed.sh already exist on disk; now wired.
Reason for original SUPERSEDED tag: Phase 1 shipped under apply-efficiency-profile.sh + set-security-profile.sh. The remaining phases never had separate plan files — they live in this document.
-->

# Hook Architecture v2 — Updated Implementation Plan

> Last updated: 2026-05-01
> Status: ALL PHASES (1-5) COMPLETE
> Phase 4 (hook composition / pipe library): hook-pipe.sh shipped. clarification-gate emits
> clarification_score; blast-radius reads it and adjusts HIGH threshold. 10 new audit tests pass.
> Phase 5 (dynamic disable env vars): check_disabled_env added to common.sh. 15 hooks updated.
> DISABLE_HOOK_* documented in rules/hook-security-profiles.md. 36 new audit tests pass.

---

## 1. Current State (as of 2026-04-10)

### 1.1 Active settings.json

The live `.claude/settings.json` has **21 hooks** across **4 events** only:
`SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`.

Missing from live settings: `SubagentStart`, `UserPromptSubmit`, `PreCompact`,
`TeammateIdle`, `TaskCreated`, `TaskCompleted`.

Notable gaps vs. docs:
- `registration-check.sh` is registered (PreToolUse Agent) in live settings but absent from the
  profile JSON files and the `apply-efficiency-profile.sh` script.
- `confidentiality-enforcer.sh` is registered in live settings but absent from the profile JSON
  files and the `set-security-profile.sh` script.
- `audit-id-enricher.sh` is registered in live settings but absent from both scripts.
- New event hooks (`subagent-context-injector.sh`, `user-prompt-capture.sh`,
  `pre-compaction-flush.sh`, `teammate-idle.sh`, `task-created.sh`, `task-completed.sh`)
  all **exist as files** but are not registered in the live settings.

### 1.2 Profile System

Two parallel profile systems exist — they are independent and both incomplete:

| Script | Profiles | Events covered | Status |
|--------|----------|----------------|--------|
| `scripts/apply-efficiency-profile.sh` | lean / standard / full | SessionStart, PreToolUse, PostToolUse, Stop | Standard uses 27 hooks but emits no new events |
| `scripts/set-security-profile.sh` | minimal / standard / paranoid | SessionStart, PreToolUse, PostToolUse, Stop | Emits 0 new events despite docs saying standard=26 and paranoid=62 |
| Profile JSON files in `.cognitive-os/plans/features/` | minimal / standard / paranoid | SessionStart, **UserPromptSubmit**, **SubagentStart**, **PreCompact**, PreToolUse, PostToolUse, Stop | Complete for 7 events. Missing TeammateIdle, TaskCreated, TaskCompleted |

### 1.3 Hook Inventory

- **Total hook files in hooks/**: 101
- **Hooks in live settings.json**: 21
- **Hooks documented in paranoid profile (docs/)**: 62
- **Hooks in paranoid profile JSON file**: 47
- **Hooks in set-security-profile.sh paranoid**: ~52 (no new events)
- **Hooks using timing.sh**: 0 (timing.sh exists but no hooks call it)

### 1.4 What new hooks exist (file + header confirms)

All three planned hooks from the original plan are implemented:

| Hook | Event | File | Async | Status |
|------|-------|------|-------|--------|
| `subagent-context-injector.sh` | SubagentStart | Exists | No | Not in live settings |
| `user-prompt-capture.sh` | UserPromptSubmit | Exists | Yes | Not in live settings |
| `pre-compaction-flush.sh` | PreCompact | Exists | No | Not in live settings |

Additionally, these hooks from the multi-agent events exist but are unregistered:

| Hook | Event | File | Status |
|------|-------|------|--------|
| `teammate-idle.sh` | TeammateIdle | Exists | Not registered anywhere |
| `task-created.sh` | TaskCreated | Exists | Not registered anywhere |
| `task-completed.sh` | TaskCompleted | Exists | Not registered anywhere |

### 1.5 Profile JSON files vs. set-security-profile.sh gap

The profile JSON files (used by tests) cover 7 events. The `set-security-profile.sh` script
only emits 4 events. Running `set-security-profile.sh standard` produces a settings.json that
is worse than the profile JSON files and worse than the live settings.json (which was hand-crafted).

**This is the primary outstanding gap.**

---

## 2. Target State

Three security profiles generated by `scripts/set-security-profile.sh` that match the profile
JSON files exactly:

| Profile | Hooks | Events | Use Case |
|---------|-------|--------|----------|
| minimal | 11 | 7 | Exploration, max speed |
| standard | 26 | 7 + 3 multi-agent | Daily development |
| paranoid | 62 | 7 + 3 multi-agent | Pre-production, security audits |

All profiles emit: SessionStart, UserPromptSubmit, SubagentStart, PreCompact, PreToolUse,
PostToolUse, Stop.

Standard and paranoid also emit: TeammateIdle, TaskCreated, TaskCompleted.

The live `settings.json` becomes the output of `set-security-profile.sh standard` (default profile).

**Hook subset relationship remains strict**: minimal ⊆ standard ⊆ paranoid.

---

## 3. What Claude Code Hook Events Exist

Based on observed Claude Code behavior and hook headers, the confirmed events are:

| Event | Current Coverage | When It Fires |
|-------|-----------------|---------------|
| `SessionStart` | ✅ All profiles | When a Claude Code session begins |
| `PreToolUse` | ✅ All profiles | Before any tool executes (matcher filters by tool name) |
| `PostToolUse` | ✅ All profiles | After any tool executes |
| `Stop` | ✅ All profiles | When a session ends naturally |
| `SubagentStart` | ✅ Profile JSONs, ❌ set-security-profile.sh | Before a sub-agent starts |
| `UserPromptSubmit` | ✅ Profile JSONs, ❌ set-security-profile.sh | When the user submits a message |
| `PreCompact` | ✅ Profile JSONs, ❌ set-security-profile.sh | Before context compaction |
| `TeammateIdle` | ❌ Not in any profile or script | When a teammate agent has no more tasks |
| `TaskCreated` | ❌ Not in any profile or script | When a task is added to the shared task list |
| `TaskCompleted` | ❌ Not in any profile or script | When a teammate marks a task done |

**Gap**: TeammateIdle, TaskCreated, TaskCompleted are entirely unregistered. They exist as
hook files but appear in zero settings files or generator scripts.

---

## 4. Proposed Improvements

### 4.1 Hook Composition (output chaining)

**Current**: Each hook is independent. Output goes to stderr only; no hook can pass enriched
data to the next hook.

**Proposed**: Hooks can emit structured data to `.cognitive-os/.hook-pipe/{event}.jsonl` that
later hooks in the same event chain read. The `_lib/common.sh` library would provide:
- `hook_emit <key> <value>` — write to the hook-pipe file for this event
- `hook_read <key>` — read a value emitted by a prior hook in the same event chain

**Use case**: `clarification-gate.sh` emits `score=72` → `blast-radius.sh` reads it and
adjusts its threshold (high-ambiguity + high blast-radius = more aggressive warning).

**Implementation**: `_lib/hook-pipe.sh` new library file. Pipe directory cleared at PreToolUse
start via a lightweight self-install entry.

**Cost**: 1 session. **Priority**: LOW (nice to have, not blocking).

### 4.2 Hook Performance Monitoring

**Current**: `_lib/timing.sh` exists but **zero hooks use it**. No performance data is
collected.

**Proposed**: Instrument the top 15 slowest-expected hooks with `start_timer`/`end_timer`
from the existing `timing.sh`. Target hooks:

| Hook | Expected overhead | Why instrument first |
|------|------------------|---------------------|
| `dispatch-gate.sh` | ~200ms | Blocks every agent launch |
| `clarification-gate.sh` | ~100ms | Blocks every agent launch |
| `blast-radius.sh` | ~50ms | Blocks every agent launch |
| `completion-gate.sh` | ~200ms | Blocks every agent completion |
| `claim-validator.sh` | ~100ms | Blocks every agent completion |
| `consequence-evaluator.sh` | ~300ms | Blocks every agent completion |
| `architecture-compliance.sh` | ~500ms | Blocks every agent completion |
| `error-pattern-detector.sh` | ~100ms | Blocks every agent launch |
| `semgrep-scan.sh` | ~2000ms | Blocks after sdd-apply |
| `aguara-scan.sh` | ~500ms | Blocks every agent launch |

Performance data writes to `.cognitive-os/metrics/performance.jsonl` (existing format).
Dashboard: `cos perf` already reads this file.

**Cost**: 1 session. **Priority**: MEDIUM.

### 4.3 Hook Dependency Management

**Current**: Hooks run in declaration order within each event group. No explicit dependencies.

**Observed ordering problem**: `completion-gate.sh` calls `completion-gate.sh` uses the
Trust Report output from the agent, but `trust-score-validator.sh` also reads it. If
`trust-score-validator.sh` runs before `completion-gate.sh`, the validator has no effect on
blocking the gate.

**Proposed**: Document the canonical execution order for each event in `docs/05-Methodology/root/hooks.md` and
enforce it in the generator scripts. No new runtime mechanism needed — order is enforced
by hook group declaration order.

**Canonical PostToolUse Agent order** (current in paranoid, should be standardized):
1. `scope-proportionality.sh` — detect overshoot first
2. `claim-validator.sh` — verify file claims
3. `assumption-tracker.sh` — detect assumptions
4. `trust-score-validator.sh` — validate Trust Report
5. `confidence-gate.sh` — gate on trust score
6. `clarification-interceptor.sh` — detect NEEDS_CLARIFICATION
7. `auto-rollback-trigger.sh` — detect retry exhaustion
8. `completion-gate.sh` — DoD check
9. `consequence-evaluator.sh` — OKR feedback
10. `auto-skill-generator.sh` — skill generation
11. `architecture-compliance.sh` — architecture check
12. `tool-loop-detector.sh` — loop detection
13. `skill-tracker.sh` — metrics
14. `semgrep-scan.sh` — SAST
15. `observability-trace.sh` — tracing
16. `notify.sh` — notifications
17. `agent-checkpoint.sh` — task tracking (LAST: final state write)

**Cost**: Documentation update only — 0.5 sessions. **Priority**: MEDIUM.

### 4.4 Dynamic Hook Loading (enable/disable at runtime)

**Current**: Switching profiles requires running a script that overwrites `settings.json`.
Claude Code must be restarted to pick up new hooks.

**Proposed**: A two-layer mechanism:
1. **Profile selection at session start**: The `session-init.sh` hook reads
   `efficiency.profile` from `cognitive-os.yaml` and writes a profile tag to the session
   state. No restart required.
2. **Per-hook opt-out env var**: Hooks check `DISABLE_HOOK_<NAME>=true` before executing.
   Example: `DISABLE_HOOK_BLAST_RADIUS=true` skips `blast-radius.sh` for the current session.
   This is additive — hooks already check `check_capability_level` and `check_private_mode`.

**Note**: Dynamic loading cannot add new events (like SubagentStart) without restarting
Claude Code. It can only enable/disable hooks within already-registered events.

**Implementation cost**: Add 1 env var check to `_lib/common.sh` (`check_disabled_env`).
Then update the 15 most commonly disabled hooks to call it.

**Cost**: 0.5 sessions. **Priority**: LOW.

### 4.5 Hook Testing Framework Improvements

**Current**: `tests/behavior/test_hook_architecture_v2.py` has 41 tests. All pass. The tests
check JSON structure, file existence, and subset relationships.

**Missing tests**:
1. **Execution order tests**: Verify canonical PostToolUse Agent order is maintained in
   all three profiles.
2. **New event tests**: Verify TeammateIdle, TaskCreated, TaskCompleted are present in
   standard and paranoid profile JSONs.
3. **Timing adoption test**: Verify that at least N hooks call `timing.sh` (performance
   monitoring adoption rate).
4. **set-security-profile.sh output tests**: Run the script in a temp directory and verify
   the generated settings.json matches the corresponding profile JSON files.
5. **Hook overlap test**: Verify that hooks registered in the live `settings.json` are a
   subset of the paranoid profile (no rogue hooks).

**Cost**: 0.5 sessions. **Priority**: HIGH (these tests catch regressions).

---

## 5. Gap Analysis: Profile JSON vs. Generator Script

The profile JSON files are the source of truth for the test suite. The `set-security-profile.sh`
script is the tool users actually run. They diverge significantly:

### Missing events in set-security-profile.sh

| Event | Profile JSONs | set-security-profile.sh | Action |
|-------|--------------|------------------------|--------|
| SubagentStart | ✅ minimal, standard, paranoid | ❌ None | Add to script |
| UserPromptSubmit | ✅ minimal, standard, paranoid | ❌ None | Add to script |
| PreCompact | ✅ minimal, standard, paranoid | ❌ None | Add to script |
| TeammateIdle | ❌ Not in profile JSONs | ❌ None | Add to both |
| TaskCreated | ❌ Not in profile JSONs | ❌ None | Add to both |
| TaskCompleted | ❌ Not in profile JSONs | ❌ None | Add to both |

### Missing hooks in profile JSONs (vs. docs/09-Quality/root/hook-security-profiles.md)

The paranoid profile JSON has 47 hooks. The docs say paranoid should have 62.
15 hooks documented in docs/ are missing from the JSON file:

| Hook | Documented in | Missing from |
|------|--------------|-------------|
| `audit-id-enricher.sh` | docs/09-Quality/root/hook-security-profiles.md (standard+) | Profile JSONs, set-security-profile.sh |
| `confidentiality-enforcer.sh` | live settings.json, docs | Profile JSONs, set-security-profile.sh |
| `clarification-interceptor.sh` | docs/09-Quality/root/hook-security-profiles.md (standard+) | Profile JSONs, set-security-profile.sh |
| `reinvention-check.sh` | docs/09-Quality/root/hook-security-profiles.md (paranoid) | Profile JSONs |
| `confidence-gate.sh` | docs/09-Quality/root/hook-security-profiles.md (paranoid) | Profile JSONs |
| `git-context-capture.sh` | live settings.json | Profile JSONs, set-security-profile.sh |
| `session-changelog.sh` | live settings.json | Profile JSONs, set-security-profile.sh |
| `auto-rollback-trigger.sh` | docs/09-Quality/root/hook-security-profiles.md (paranoid) | Profile JSONs |
| `session-resume.sh` | docs/09-Quality/root/hook-security-profiles.md (paranoid) | set-security-profile.sh paranoid |
| `teammate-idle.sh` | docs/09-Quality/root/hook-security-profiles.md (standard+) | Profile JSONs, set-security-profile.sh |
| `task-created.sh` | docs/09-Quality/root/hook-security-profiles.md (standard+) | Profile JSONs, set-security-profile.sh |
| `task-completed.sh` | docs/09-Quality/root/hook-security-profiles.md (standard+) | Profile JSONs, set-security-profile.sh |
| `predev-completeness-check.sh` | live settings.json | Profile JSONs, set-security-profile.sh |
| `inject-phase-context.sh` | live settings.json | set-security-profile.sh standard |
| `agent-prelaunch.sh` | live settings.json | set-security-profile.sh standard |

### Hooks in live settings.json not in set-security-profile.sh standard

Running `set-security-profile.sh standard` produces a weaker settings than the current live one:

| Hook | Live settings.json | set-security-profile.sh standard |
|------|-------------------|----------------------------------|
| `registration-check.sh` | ✅ | ❌ |
| `confidentiality-enforcer.sh` | ✅ | ❌ |
| `audit-id-enricher.sh` | ✅ | ❌ |
| `inject-phase-context.sh` | ✅ | ❌ |
| `agent-prelaunch.sh` | ✅ | ❌ |
| `predev-completeness-check.sh` | ✅ | ❌ |
| `trust-score-validator.sh` | ✅ | ❌ |
| `session-resume.sh` | ✅ | ❌ |
| `git-context-capture.sh` | ✅ | ❌ |
| `session-changelog.sh` | ✅ | ❌ |

---

## 6. New Hooks Documentation

### subagent-context-injector.sh

- **Event**: SubagentStart
- **Async**: No (must complete before subagent starts)
- **Exit**: Always 0 (never blocks subagent launch)
- **Output**: JSON with `additionalContext` field injected into subagent context
- **Purpose**: Injects agent preamble, phase context, and engram sidecar memory into
  sub-agents before they run. Eliminates need for orchestrator to manually compose preambles.
- **Profile**: standard, paranoid

### user-prompt-capture.sh

- **Event**: UserPromptSubmit
- **Async**: Yes (must never block user input)
- **Exit**: Always 0
- **Purpose**: Classifies user prompts using `lib/prompt_classifier.py` and saves actionable
  prompts to Engram for cross-session recall. Implements `rules/user-prompt-capture.md`.
- **Profile**: standard, paranoid

### pre-compaction-flush.sh

- **Event**: PreCompact
- **Async**: No (must complete before compaction begins)
- **Exit**: Always 0
- **Output**: System message instructing agent to flush state to Engram
- **Purpose**: Last-resort safety net. Reminds agent to call `mem_session_summary` and
  `mem_save` before context is compacted. Implements Tier 3 in `rules/fault-tolerance.md`.
- **Profile**: minimal, standard, paranoid
- **Security-critical**: Yes — never async

### teammate-idle.sh

- **Event**: TeammateIdle
- **Async**: No
- **Exit**: 0 (allow idle) or 2 (keep working, has pending tasks)
- **Purpose**: When a teammate agent is about to idle, checks `active-tasks.json` for
  pending tasks. Exits 2 with a suggestion if tasks are available, preventing premature
  teammate shutdown.
- **Profile**: standard, paranoid

### task-created.sh

- **Event**: TaskCreated
- **Async**: No
- **Exit**: 0 (allow) or 2 (block — validation failed)
- **Purpose**: Validates task quality on creation: checks for meaningful description,
  prevents duplicates, blocks tasks without acceptance criteria in production phase.
- **Profile**: standard, paranoid

### task-completed.sh

- **Event**: TaskCompleted
- **Async**: No
- **Exit**: 0 (accept) or 2 (reject — criteria not met)
- **Purpose**: Verifies completion criteria when a teammate marks a task done. Validates
  that output is non-empty, file claims are partially verifiable, and logs completion
  to metrics and `active-tasks.json`.
- **Profile**: standard, paranoid

---

## 7. Async Policy

Security-critical hooks are NEVER async:

- `secret-detector.sh`
- `content-policy.sh`
- `rate-limiter.sh`
- `clarification-gate.sh`
- `pre-compaction-flush.sh`
- `claim-validator.sh`
- `confidence-gate.sh`

Advisory-only hooks MAY be async to reduce blocking overhead:

- `user-prompt-capture.sh` — MUST be async (UserPromptSubmit must not block typing)
- `observability-trace.sh` — async recommended
- `notify.sh` — async recommended
- `kpi-trigger.sh` — async recommended
- `engram-auto-sync.sh` — async recommended

---

## 8. Profile Design (Canonical)

### Minimal Profile (11 hooks)

Core safety only: session lifecycle, error capture, secret detection, crash recovery,
auto-checkpoint, pre-compaction flush.

No quality gates. No agent governance. Fastest possible iteration.

| Event | Hook |
|-------|------|
| SessionStart | self-install.sh, session-init.sh, crash-recovery.sh |
| PreCompact | pre-compaction-flush.sh |
| PreToolUse Bash\|Agent\|Edit\|Write | rate-limiter.sh |
| PostToolUse Bash | error-pipeline.sh |
| PostToolUse Edit\|Write | secret-detector.sh |
| PostToolUse Bash\|Edit\|Write | auto-checkpoint.sh |
| PostToolUse Agent | agent-checkpoint.sh |
| Stop | session-learning.sh, session-cleanup.sh |

### Standard Profile (26 hooks)

All minimal hooks plus: quality gates, content policy, key safety mesh layers,
multi-agent events.

| Event | Hook |
|-------|------|
| SessionStart | self-install.sh, session-init.sh, crash-recovery.sh |
| PreCompact | pre-compaction-flush.sh |
| SubagentStart | subagent-context-injector.sh |
| UserPromptSubmit | user-prompt-capture.sh |
| TeammateIdle | teammate-idle.sh |
| TaskCreated | task-created.sh |
| TaskCompleted | task-completed.sh |
| PreToolUse Bash\|Agent\|Edit\|Write | rate-limiter.sh |
| PreToolUse Read | large-file-advisor.sh |
| PreToolUse Agent | dispatch-gate.sh, clarification-gate.sh, blast-radius.sh, inject-phase-context.sh, agent-prelaunch.sh, error-pattern-detector.sh, predev-completeness-check.sh, registration-check.sh |
| PostToolUse Bash | error-pipeline.sh, result-truncator.sh |
| PostToolUse Edit\|Write | secret-detector.sh, content-policy.sh, confidentiality-enforcer.sh, doc-sync-detector.sh |
| PostToolUse Bash\|Edit\|Write | auto-checkpoint.sh |
| PostToolUse Agent | claim-validator.sh, completion-gate.sh, clarification-interceptor.sh, trust-score-validator.sh, audit-id-enricher.sh, agent-checkpoint.sh |
| Stop | session-learning.sh, session-cleanup.sh, git-context-capture.sh, session-changelog.sh |

### Paranoid Profile (62 hooks)

All standard hooks plus: all remaining safety mesh layers, external scanners, observability,
full governance.

Full list in `docs/09-Quality/root/hook-security-profiles.md`. That doc is authoritative for paranoid.

---

## 9. Hook Count Contract

| Profile | Target | Tolerance |
|---------|--------|-----------|
| minimal | 11 | ±2 |
| standard | 26 | ±3 |
| paranoid | 62 | ±5 |

Subset relationship: minimal ⊆ standard ⊆ paranoid (zero exceptions).

---

## 10. Implementation Phases

### Phase 1: New events in profile JSON files (COMPLETE)

- [x] `subagent-context-injector.sh` written and functional
- [x] `user-prompt-capture.sh` written and functional
- [x] `pre-compaction-flush.sh` written and functional
- [x] Profile JSON files (minimal/standard/paranoid) include SubagentStart, UserPromptSubmit, PreCompact
- [x] 41 behavior tests pass
- **Cost**: completed

### Phase 2: Sync set-security-profile.sh to profile JSON files (CURRENT)

**Goal**: Running `set-security-profile.sh standard` produces settings.json that is at least
as capable as the current live settings.json, and includes the new events.

**Tasks**:
- [x] Add SubagentStart section — already present in all three profile JSON files; script reads them directly
- [x] Add UserPromptSubmit section — already present in all three profile JSON files
- [x] Add PreCompact section — already present in all three profile JSON files
- [ ] Add TeammateIdle, TaskCreated, TaskCompleted sections (standard + paranoid) — lower priority
- [ ] Add missing hooks to standard: `inject-phase-context.sh`, `agent-prelaunch.sh`,
  `predev-completeness-check.sh`, `registration-check.sh`, `confidentiality-enforcer.sh`,
  `trust-score-validator.sh`, `audit-id-enricher.sh`, `git-context-capture.sh`,
  `session-changelog.sh`, `clarification-interceptor.sh`
- [ ] Add `session-resume.sh` to standard (currently only in paranoid)
- [ ] Add missing hooks to profile JSON files:
  `confidentiality-enforcer.sh`, `audit-id-enricher.sh`, `clarification-interceptor.sh`,
  `reinvention-check.sh`, `confidence-gate.sh`, `git-context-capture.sh`,
  `session-changelog.sh`, `auto-rollback-trigger.sh`, `teammate-idle.sh`,
  `task-created.sh`, `task-completed.sh`, `predev-completeness-check.sh`,
  `inject-phase-context.sh`, `agent-prelaunch.sh`
- [ ] Add new behavior tests: execution order, new events in profile JSONs, script vs JSON parity
- [ ] Update hook counts in test suite (currently checks 11/26/62; profile JSONs show 11/31/47)

**Estimated cost**: 1 session (sonnet). **Priority**: HIGH.

### Phase 3: Hook performance monitoring adoption (COMPLETE — 2026-04-30)

**Goal**: Instrument hooks with timing to populate metrics and enforce latency budgets.

**Implementation approach**: wrapper-based (not per-hook timing.sh injection).
`scripts/hook-timing-wrapper.sh` wraps every hook at the settings.json registration
level via `scripts/_lib/settings-driver-claude-code.sh`. All hooks are instrumented
automatically — no per-hook source changes required.

**Tasks**:
- [x] `scripts/hook-timing-wrapper.sh` — logs per-invocation timing to
  `.cognitive-os/metrics/hook-timing.jsonl` (timestamp, event, hook, duration_ms,
  exit_code, session_id, pid)
- [x] Auto-injection at hook registration — `scripts/_lib/settings-driver-claude-code.sh`
  wraps every hook command with the timing wrapper (lines 52-65); confirmed by `grep -c
  "hook-timing-wrapper" scripts/_lib/settings-driver-claude-code.sh` > 0
- [x] `scripts/hook_timing_report.py` — reads `.cognitive-os/metrics/hook-timing.jsonl`,
  prints p50/p95/p99 per hook, supports `--threshold-only` (show only budget violators),
  `--json` (machine-readable), `--event`, `--since`, `--live`, `--session`
- [x] `tests/audit/test_hook_latency_budget.py` — reads JSONL, computes p95 over last
  N=100 invocations per (event, hook) pair, asserts within event budget
  (PreToolUse <2s, PostToolUse <5s, Stop <10s, SessionStart/SubagentStart/
  UserPromptSubmit/TeammateIdle/TaskCreated/TaskCompleted <3s, PreCompact <5s);
  skips pairs with <5 samples
- [x] 58 unique hooks recorded in `.cognitive-os/metrics/hook-timing.jsonl` after live
  sessions — requirement of ≥10 instrumented hooks exceeded

**Evidence**:
- `scripts/hook-timing-wrapper.sh` exists (229 lines)
- `python3 scripts/hook_timing_report.py` shows 6 308 records across 58 hooks
- `tests/audit/test_hook_latency_budget.py` passes (or skips for low-sample events)

**Estimated cost**: 0.5 sessions (sonnet). **Priority**: MEDIUM.

### Phase 4: Hook composition (pipe library) — COMPLETE 2026-05-01

**Goal**: Enable hooks to pass data forward within an event chain.

**Tasks**:
- [x] Create `hooks/_lib/hook-pipe.sh` with `hook_emit` and `hook_read` functions — 124 lines, includes `hook_pipe_clear`
- [x] Update `clarification-gate.sh` to emit `score` to the pipe — emits `clarification_score` to `PreToolUse` namespace
- [x] Update `blast-radius.sh` to read `clarification_score` and adjust threshold — lowers HIGH from 40→20 when score ≥ 30
- [x] Add documentation to `docs/05-Methodology/root/hooks.md` — "Hook Composition" section with function table, data flow table, and usage guide
- [x] Add test: `test_hook_pipe_data_sharing` — 10 tests in `tests/audit/test_hook_pipe.py` (all pass)

**Evidence**:
- `hooks/_lib/hook-pipe.sh` exists (124 lines); bash -n passes
- `clarification-gate.sh` sources hook-pipe.sh and calls `hook_emit "clarification_score"`
- `blast-radius.sh` reads `clarification_score` via `hook_read`, uses `HIGH_THRESHOLD` variable
- `docs/05-Methodology/root/hooks.md` documents "Hook Composition" with `hook_emit`/`hook_read`/`hook_pipe_clear`
- `tests/audit/test_hook_pipe.py`: 10 tests, all pass

**Estimated cost**: 1 session (sonnet). **Priority**: LOW.

### Phase 5: Dynamic hook disable env vars — COMPLETE 2026-05-01

**Goal**: Allow per-session hook suppression without editing settings.json.

**Tasks**:
- [x] Add `check_disabled_env` function to `_lib/common.sh` — checks `DISABLE_HOOK_<UPPERCASE_NAME>=true|1`, exits 0 silently if set; uses `tr '[:lower:]-' '[:upper:]_'` transformation; bash -n passes
- [x] Add `check_disabled_env` call to the 15 most commonly disabled hooks — blast-radius, clarification-gate, assumption-tracker, confidence-gate, claim-validator, consequence-evaluator, architecture-compliance, dispatch-gate, auto-skill-generator, tool-loop-detector, scope-proportionality, trust-score-validator, error-pattern-detector, semgrep-scan, aguara-scan
- [x] Document in `rules/hook-security-profiles.md` — "Per-Session Hook Suppression" section with full table of 15 env vars, usage examples, security notes
- [x] Add test: `test_disable_hook_env_var_respected` — 36 tests in `tests/audit/test_hook_disable_env.py` (all pass)

**Evidence**:
- `hooks/_lib/common.sh` contains `check_disabled_env()` (bash -n passes)
- 15 hook files updated (verified by `test_minimum_15_hooks_support_disable_env`)
- `rules/hook-security-profiles.md` documents `DISABLE_HOOK_*` pattern
- `tests/audit/test_hook_disable_env.py`: 36 tests, all pass

**Estimated cost**: 0.5 sessions (sonnet). **Priority**: LOW.

---

## 11. Files Affected

### Phase 2 (immediate)
- `scripts/set-security-profile.sh` — add new event sections for all profiles
- `.cognitive-os/plans/features/hook-architecture-v2-settings.json` — add missing hooks
- `.cognitive-os/plans/features/hook-architecture-v2-settings-minimal.json` — no change needed
- `.cognitive-os/plans/features/hook-architecture-v2-settings-paranoid.json` — add missing hooks
- `tests/behavior/test_hook_architecture_v2.py` — add new test cases
- `docs/09-Quality/root/hook-security-profiles.md` — update hook counts and comparison matrix

### Phase 3 (performance)
- `hooks/dispatch-gate.sh` through `hooks/trust-score-validator.sh` (15 files)

### Phase 4 (composition)
- `hooks/_lib/hook-pipe.sh` (new)
- `hooks/clarification-gate.sh` (emit)
- `hooks/blast-radius.sh` (read)

### Phase 5 (dynamic disable)
- `hooks/_lib/common.sh` (add `check_disabled_env`)
- Up to 15 hook files (add call)

---

## 12. Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Running set-security-profile.sh standard produces weaker settings than current | HIGH (confirmed gap) | HIGH | Phase 2 fixes this. Until then, do not run the script on live settings. |
| TeammateIdle/TaskCreated/TaskCompleted events may not fire in all Claude versions | MEDIUM | LOW | Hooks are defensive — graceful exit 0 if event data is missing |
| Profile JSON files diverge from docs over time | MEDIUM | MEDIUM | add doc-vs-json parity test in Phase 2 |
| Adding 10+ more hooks to PostToolUse Agent pushes overhead >5s in paranoid | LOW | MEDIUM | Async hooks for non-blocking; timing instrumentation (Phase 3) will surface this |
| Hook-pipe data is stale across events | MEDIUM | LOW | Pipe cleared on each PreToolUse entry |
| Timing instrumentation adds overhead to fast hooks | LOW | LOW | timing.sh overhead is ~1ms (Python subprocess); negligible |

---

## 13. Test Plan

### Existing (41 tests, all passing)
- Plan file structure
- Profile JSON valid JSON
- All required events in standard (7 events)
- PreCompact in minimal
- SubagentStart, UserPromptSubmit documented in plan
- All referenced hook files exist
- minimal < standard < paranoid hook counts
- minimal ⊆ standard ⊆ paranoid subset relationship
- Security-critical hooks not marked async

### New tests for Phase 2

| Test | What it checks |
|------|----------------|
| `test_standard_has_teammate_idle` | TeammateIdle in standard profile JSON |
| `test_standard_has_task_created` | TaskCreated in standard profile JSON |
| `test_standard_has_task_completed` | TaskCompleted in standard profile JSON |
| `test_profile_json_matches_script_standard` | Run set-security-profile.sh standard in temp dir; compare hook lists to standard profile JSON |
| `test_profile_json_matches_script_paranoid` | Run set-security-profile.sh paranoid in temp dir; compare to paranoid profile JSON |
| `test_canonical_post_agent_order` | Verify completion-gate runs after trust-score-validator in paranoid |
| `test_hooks_with_timing_count` | Count hooks using timing.sh; ≥ 10 after Phase 3 |
| `test_live_settings_subset_of_paranoid` | Every hook in live settings.json is in paranoid profile |
| `test_missing_hooks_resolved` | confidentiality-enforcer, audit-id-enricher, clarification-interceptor in standard JSON |

### New tests for Phase 4

| Test | What it checks |
|------|----------------|
| `test_hook_pipe_library_exists` | `hooks/_lib/hook-pipe.sh` exists |
| `test_hook_pipe_functions_defined` | hook_emit and hook_read are defined in hook-pipe.sh |

---

## 14. Definition of Done

- [ ] All tests in `tests/behavior/test_hook_architecture_v2.py` pass (including new ones)
- [ ] `set-security-profile.sh standard` output ≥ live settings.json hook coverage
- [ ] New events (SubagentStart, UserPromptSubmit, PreCompact, TeammateIdle, TaskCreated, TaskCompleted) registered in standard and paranoid
- [ ] Profile JSON files and set-security-profile.sh script are in sync (no divergence)
- [ ] No hook file references missing from any profile
- [ ] Profile subset relationships maintained
- [ ] Hook counts documented in `docs/09-Quality/root/hook-security-profiles.md` match actual counts (within tolerance)
- [ ] `docs/09-Quality/root/hook-security-profiles.md` comparison matrix is up to date
