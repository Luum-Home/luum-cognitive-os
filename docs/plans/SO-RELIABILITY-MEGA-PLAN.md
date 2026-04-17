# SO Reliability & Observability Mega-Plan

> Pick-up-from-any-session doc. Formalises the "SRE for agents" framework that
> surrounds and enables ADR-027 (SO Slimming). Final form lives in ADR-028.

## Context (why this exists)

On 2026-04-17, during Lote 4 work, we discovered:

- `hooks/session-init.sh` spawned `python3 -m pytest` (full suite) on every
  SessionStart via a `(…) &` subshell. The parent stayed blocked in `S` state
  because the backgrounded children inherited its FDs.
- **190 orphaned `session-init.sh` processes** + **187 orphaned pytest
  processes** + **49 orphaned `pre-commit-gate.sh`/`coverage-report.sh`** were
  holding ~300 MiB RAM and many FDs across accumulated sessions.
- Author of the leak: the project owner, commit `1b755cf` on 2026-04-10
  (`feat(ws11): test baseline diff hook for anti-confirmation-bias`). Good
  intent (baseline for regression detection), broken implementation.
- **No existing test caught this.** Hook tests verify exit code + file output;
  none count orphaned processes or measure RAM/FD deltas.

This is a structural failure, not a one-off. Three root causes:

1. **No runtime observability of the SO itself.** Metrics track business
   concerns (cost, tokens, trust-score) but not runtime state (process count,
   FDs, RAM per hook, orphan detection).
2. **No contract tests for hooks.** "Does what it says" is verified; "leaves
   the system clean" is not.
3. **Well-intentioned features added in isolation**, no owner or cross-hook
   coordination. `Test baseline capture`, `coverage-report`, `pre-commit-gate`,
   MCP-always-on, self-install, etc.

## The 6 Pillars

### Pillar 1 — Runtime Observability of the SO

**Goal**: know at all times what processes/resources the SO consumes; know
which metrics are actually consumed; detect and safely terminate hung
agents and bash processes.

Sub-pillar 1.A — Metrics census (audit existing):

- Inventory every `.cognitive-os/metrics/*.jsonl` file: who writes it, who
  reads it, retention policy.
- Current known files: cost-events, error-learning, trust-scores,
  hook-health, context-watchdog, truncation-events, resource-checks,
  auto-verify, completeness-check, prompt-captures, skill-archive,
  consequence-history, large-file-reads, infra-usage.
- For each: CONSUMED (keep + rotate), ORPHAN (deprecate), or MISCONFIGURED
  (fix the consumer).
- Rotation policy: size-based (1 MiB cap) + age-based (7 days) per file.
- Schema unification: one `MetricEvent` base schema all writers extend.
- Deliverable: `docs/reports/metrics-census.md` with triage table.

Sub-pillar 1.B — Process registry + reaper (hooks and subprocesses):

- `lib/process_registry.py` — every hook that uses `&`, `nohup`, or spawns
  a long-lived subprocess MUST register PID + TTL + owner-hook.
- Reaper runs at SessionEnd AND as a lightweight cron (every 5 min):
  SIGTERM with 10s grace, then SIGKILL. Safe-kill policy enforced.
- Whitelist of `detached-daemon` entries (MCP servers, Docker) skipped by
  reaper but still monitored for RAM/CPU thresholds.

Sub-pillar 1.C — Agent liveness (Claude-Code sub-agents):

- Every sub-agent writes a heartbeat to
  `.cognitive-os/tasks/{agent_id}.heartbeat` every 60s (adapt the preamble
  template).
- Watchdog: any heartbeat >5 min stale → marked `stale`, orchestrator
  notified, optionally SIGTERM'd.
- State machine: `launched → running → stale → reaped | completed`.
- `scripts/so-agent-status.sh` prints current agent fleet: id, model,
  elapsed, heartbeat age, status.

Sub-pillar 1.D — Unified dashboard:

- `scripts/so-vitals.sh` — one-shot CLI printing:
  - Agents in flight (from 1.C)
  - Registered bash processes + TTL (from 1.B)
  - Orphan detection (processes not in registry but spawned by our hooks)
  - MCP RSS summary
  - JSONL sizes + rotation status (from 1.A)
  - Hook runtime p50/p95 (last 100 invocations)
- Runnable manually, at SessionStart (silent unless thresholds breached),
  or by `/so-status` skill.
- Exit code non-zero if any SLO breached — usable in CI.

### Pillar 2 — Contract Tests for Hooks

New rule `rules/hook-contracts.md`:

> Every hook MUST have a test that executes the hook in a sandbox and verifies:
> 1. Exit 0 on happy path.
> 2. **Zero child processes alive 100ms after the hook returns** (exceptions
>    require explicit `detached-daemon` annotation with a tracked PID).
> 3. **Zero FDs opened by the hook and left open** (excluding stdout/stderr).
> 4. RAM delta below threshold (e.g. 10 MiB for short hooks, 50 MiB for
>    SessionStart).
> 5. p95 duration under SLO (SessionStart <2s, PreToolUse <200ms, PostToolUse
>    <500ms).

Implementation:

- `tests/contracts/test_hook_no_orphans.py` — parametrised over all hooks.
- `tests/contracts/test_hook_runtime_slo.py` — SLO enforcement.
- `tests/contracts/test_hook_fd_clean.py` — FD leak check via `lsof`.

This package is the regression net that would have caught the `session-init`
bug immediately.

### Pillar 3 — Systematic Audit of Existing Hooks

1 opus agent, read-only, produces a findings report:

- Walks all 110 hooks.
- Flags anti-patterns: `(…) &` without PID tracking, subprocess without
  timeout, `pytest`/`pip`/`docker` calls without reaping, infinite `sleep`,
  loops without break condition.
- Severity: BLOCKER / CONCERN / SUGGESTION.
- Output: `docs/reports/hook-audit-{date}.md`.

No fixes in this pillar; just the inventory.

### Pillar 4 — Systematic Fix + Refactor

For each finding from Pillar 3, a sonnet agent applies the canonical pattern:

- `&` → `nohup … & echo $! >> $SESSION_DIR/pids` + reaper.
- Subprocess without timeout → `timeout 30 …`.
- Tests called from hooks → move to `post-session-verify` (ADR-027 Phase 1).
- Unrotated metrics → rotator (ADR-027 Phase 3).

Multiple sonnet agents can run in parallel, each owning a disjoint set of
hooks.

### Pillar 5 — SLOs, Error Budget, Incident Runbook

New `rules/so-slo.md`:

| Dimension | SLO | Error Budget |
|---|---|---|
| SessionStart duration | p95 < 2s | 4h / month |
| Process leak rate | 0 orphans / session | 0 tolerance |
| Hook p95 latency | < 200ms | 1% of calls |
| RAM steady state | < 300 MiB MCPs + hooks | 1h / month over limit |
| Full-suite runs / session | = 1 | 0 tolerance |
| JSONL growth | < 1 MiB / session | — |

New `docs/runbooks/so-incident-runbook.md`:

- Symptoms: slow session, high CPU, high RAM.
- Diagnosis commands: `scripts/so-vitals.sh`.
- Kill-switch: `scripts/so-emergency-stop.sh` — disables hooks, kills orphans,
  leaves SO in minimal mode.
- Postmortem template.

### Pillar 6 — Chaos Engineering (lightweight)

Suite that breaks things on purpose to verify resilience:

- `chaos/kill_mcp_mid_session` — kill `engram` server; orchestrator must
  degrade gracefully.
- `chaos/hook_timeout` — inject `sleep 60` in a hook; verify timeout kills it.
- `chaos/disk_full_metrics` — fill JSONL; verify rotation or backpressure
  kicks in.
- `chaos/fd_exhaustion` — open 1000 FDs before SessionStart; hook must not
  crash.

Runs once per week (scheduled) or manually on release.

## Phase Order & Parallelism

```
A — Observability (Pillar 1)           ┐ prerequisite
B — Contract Tests framework (Pillar 2)┘ parallel with A (disjoint files)
      │
      ▼
C — Audit (Pillar 3, opus, read-only)
      │
      ▼
D — Systematic fix (Pillar 4) — N sonnet agents in parallel by domain
      │
      ▼
E — SLOs + Runbook + Chaos (Pillars 5 & 6)
      │
      ▼
F — ADR-027 original (Tests/Context/Resources), now running on top of
    an observable, testable SO.
```

| Phase | Can run parallel with | Reason |
|---|---|---|
| A | — | prerequisite |
| B | A | A owns `lib/process_registry.py` + hooks; B owns `tests/contracts/` |
| C | — | needs A + B to validate findings |
| D | multi-sonnet inside D | each agent owns disjoint hook set |
| E | — | needs D complete |
| F | partially with E | ADR-027 Phase 1 independent; Phase 3 needs D + E |

## Time Estimate

| Phase | Agent(s) | Duration |
|---|---|---|
| A | 1 opus (design) + 1 sonnet (impl) | 3–4h |
| B | 1 opus (framework) + 1 sonnet (integration) | 3–4h |
| C | 1 opus (audit) | 2h |
| D | 3–5 sonnet parallel | 4–6h |
| E | 1 opus | 2–3h |
| F | see ADR-027 | 9h |

Total: ~25–30h of agent work across 3–5 human sessions.

## Entry Points (how to resume)

- **Restart from scratch**: read this file + ADR-027 + ADR-028 (once written).
- **Check current phase**: look for latest `sdd/so-reliability/{phase}/state`
  entry in engram or latest commit touching `hooks/hook-runtime-probe.sh`
  / `lib/process_registry.py` / `tests/contracts/`.
- **Continue phase N**: read the phase's `Tasks` subsection in ADR-028,
  resume from the last unchecked task.

## Integration with ADR-027

ADR-027 defined the *slimming* targets (tests, context, resources). This plan
defines the *framework* on top of which the slimming actually works safely.

Without this framework, ADR-027's Phase 3 (resources) would be blind — we'd
reduce hook count without knowing which hooks were leaking in the first
place.

## What triggered this

- Symptom: 1h+ agent runs, 100% CPU, "slow session" complaints.
- Investigation: 350+ orphaned processes across `session-init.sh`, pytest,
  pre-commit-gate, coverage-report.
- Root cause: `session-init.sh:120-128` ran full pytest on every session;
  children never reaped; problem invisible because no contract test.
- Immediate fix: block commented out with pointer to ADR-027 Phase 3.
- This plan: make sure it can't happen again.

## Out of Scope

- Rewriting the agent orchestrator (separate concern, covered by existing
  SDD workflow).
- Rewriting MCP servers (their internal reliability is their own concern).
- Claude Code harness-level issues (RAM of Claude Helper processes, OrbStack
  Docker VM — not our code).
