<!-- TIER: 1 -->
<!-- SCOPE: both -->
# SO SLO Catalogue — Source of Truth (ADR-028 D5)

> Adopted: 2026-04-20. Owner: ADR-028 coordinator.
> Measurement infra: `hooks/_lib/hook-runtime-probe.sh` (per-hook latency),
> `scripts/so-vitals.sh` (system-level), `scripts/so-slo-report.sh` (daily p95 roll-up, stub).

---

## SLO Table

| # | Dimension | SLO target | Error budget | Measured by | Logged to | Owner hook | Chaos test |
|---|-----------|-----------|-------------|-------------|-----------|------------|------------|
| 1 | `SessionStart` p95 duration | < 2 s | 4 h / month degraded | `hook-runtime-probe.sh` wraps hook | `hook-health.jsonl` | `session-init.sh` | `test_hook_timeout.py` |
| 2 | `PreToolUse` p95 latency | < 200 ms | 1 % of calls over SLO | `hook-runtime-probe.sh` | `hook-health.jsonl` | dispatch / rate-limiter hooks | `test_hook_timeout.py` |
| 3 | `PostToolUse` p95 latency | < 500 ms | 1 % of calls over SLO | `hook-runtime-probe.sh` | `hook-health.jsonl` | completion-gate / auto-verify | `test_hook_timeout.py` |
| 4 | Process leak rate | 0 orphans / session | 0 tolerance | reaper diff: registered PIDs vs `ps` | `processes.jsonl` | `session-end-reap.sh` | `test_fd_exhaustion.py` |
| 5 | RAM steady state (MCPs + hooks) | < 300 MiB | 1 h / month over | `scripts/so-vitals.sh --json` | `so-vitals.jsonl` | `session-init.sh` | `test_kill_mcp_mid_session.py` |
| 6 | Full-suite test runs / session | = 1 | 0 tolerance | count `pytest tests/unit` invocations per session log | `global-verify.jsonl` | `global-verify.sh` | — |
| 7 | JSONL total growth / session | < 1 MiB | — | `du` diff before/after | `so-vitals.jsonl` | `metrics-rotation.sh` | `test_disk_full_metrics.py` |
| 8 | Destructive git ops from hooks | 0 | 0 tolerance | `test_hook_no_destructive_git` + reflog diff | contract-test CI | `git-context-capture.sh` | `test_reset_cascade_detector.py` |
| 9 | Agent heartbeat staleness | p99 < 5 min | 1 agent / month stale | watchdog scan of `agent-heartbeat.jsonl` | `agent-heartbeat.jsonl` | `state-heartbeat.sh` (session) / agent watchdog | `test_kill_mcp_mid_session.py` |
| 10 | Initial context payload size | < 50,000 tokens (core) | 10% of sessions over SLO | `scripts/startup-benchmark.sh` → `payload.core_payload_tokens` | `startup-benchmark.jsonl` | `session-init.sh` (catalog loading) | `test_startup_budget.py` |
| 11 | TTFT (Time to First Token) | p95 < 5 s | 4 h / month over | Manual: wall-clock from session start to first output token; automated via PostToolUse delta (see `docs/architecture/functional-audit/startup-baseline-2026-04-20.md` §6) | `ttft-events.jsonl` (future) | `session-init.sh` + first PostToolUse hook | — (manual until instrumented) |

### Note on SLO 9 — heartbeat subsystem split

Two distinct mechanisms share the "heartbeat" label; they must not be confused:

- **`state_heartbeat`** (`hooks/state-heartbeat.sh`) — writes a crash-recovery
  checkpoint after each `PostToolUse Agent` event. Its purpose is session
  crash-recovery (ADR-027 D1), not liveness monitoring.
- **`agent_bus_metrics`** — the sub-agent heartbeat emitted by
  `lib/agent_heartbeat.py` and consumed by the watchdog. **SLO 9 targets this
  second mechanism exclusively.** Staleness is measured against
  `agent-heartbeat.jsonl`, not `state-heartbeat.jsonl`.

---

## Error Budget Policy

### Budget cycle

- Budgets reset at **UTC month boundary** (midnight 1st of each calendar month).
- A budget is considered **exhausted** when either condition is true:
  1. A single SLO has been in breach for > 24 consecutive hours.
  2. Cumulative breach minutes for that SLO exceed the monthly budget
     (e.g. SLO 1: 240 min, SLO 5: 60 min).

### When budget is exhausted

1. **Development paused**: no new feature agents are launched until budget recovers.
2. **Minimal profile enforced**: the session defaults to
   `efficiency.profile: minimal` (only the critical whitelist fires —
   `credential-guard.sh`, `license-guard.sh`, `pre-compaction-flush.sh`).
3. **Operator notified**: `scripts/so-vitals.sh` emits a `budget_exhausted`
   field in its JSON output; the orchestrator surfaces this to the user.
4. **Budget recovery**: once the breaching SLO returns within target for
   ≥ 1 h the development pause is lifted and the normal profile is restored.

### Zero-tolerance SLOs (no budget)

SLOs 4, 6, and 8 have **0 tolerance**. A single breach triggers immediate
incident response regardless of accumulated budget.

---

## Measurement Cadence

| Event | Action |
|-------|--------|
| Every `SessionEnd` | `scripts/so-vitals.sh --json` appends one record to `so-vitals.jsonl` |
| Daily (cron / on-demand) | `scripts/so-slo-report.sh` reads `hook-health.jsonl` and emits p95 roll-up (stub — not yet built; reference only) |
| Per-hook invocation | `hooks/_lib/hook-runtime-probe.sh` wraps duration; appends to `hook-health.jsonl` |
| Agent completion | `lib/agent_heartbeat.py` stamps `agent-heartbeat.jsonl`; watchdog checks staleness |

---

## Reconciliation with ADR-028a Feature Flags

| Flag | SLO impact |
|------|------------|
| `runtime.killswitch_respected: false` | Killswitch flag ignored; hooks run at full profile regardless of budget state |
| `runtime.heartbeat.enabled: false` | SLO 9 unmeasurable — treat as unknown, not breached |
| `runtime.reaper.enabled: false` | SLO 4 unmeasurable — reaper no-op means orphan detection disabled |
