# Next-Session Plan — DORMANT + ASPIRATIONAL → REAL

**Date**: 2026-04-20 (handoff to session N+1)
**Anchor**: `docs/reports/aspirational-audit-2026-04-20.md` (68.5% dormant+aspirational ratio)
**Target**: reduce ratio to < 40% by converting the following 13 items.

Every item below has a concrete **first step** (≤ 15 min to verify), **effort estimate**, and **verification command** that proves it flipped to REAL.

## ASPIRATIONAL → REAL (4 items)

### A1. `ref_key_loader` — wire into `inject-phase-context.sh`

**Problem**: `lib/ref_key_loader.py` exists, 13 tests pass, zero callers in hooks.

**Fix**: in `hooks/inject-phase-context.sh`, after assembling `CONTEXT_BUF`, pipe it through `lib.ref_key_loader.expand(text)`. Every `[\`ref-key\`]` in the preamble gets replaced with the full rule body inline.

**First step**:
```python
# Add to the HEREDOC python block in inject-phase-context.sh:
from lib.ref_key_loader import expand
CONTEXT_BUF = expand(CONTEXT_BUF, max_depth=1)
```

**Effort**: 30 min (including test).

**Verification**: invoke a sub-agent, capture preamble additionalContext, assert at least one `[\`X\`]` from RULES-COMPACT was expanded inline.

### A2. `install.sh` scope-filter

**Problem**: 506 SCOPE tags on disk, but `install.sh` copies everything regardless.

**Fix**: add `--scope=project|both|all` flag (default `both` for user projects, `all` for COS self-hosting). During copy, grep each file for `# SCOPE:` / `<!-- SCOPE: -->` header and skip if filter excludes it.

**First step**:
```bash
# install.sh: before each cp, add:
case "$INSTALL_SCOPE" in
  project) grep -qE '^(# SCOPE: (project|both)|<!-- SCOPE: (project|both) -->)' "$f" || continue ;;
  both)    grep -qE '^(# SCOPE: (project|both)|<!-- SCOPE: (project|both) -->)' "$f" || continue ;;
  all)     ;;  # install everything
esac
```

**Effort**: 1 h (including tests over a dummy project tree).

**Verification**: install with `--scope=project` into `tmp_path`, count installed files; expect ≤ 300 (exclude os-only components).

### A3. ADR-028c migration contract

**Problem**: aspirational until a real breaking change happens.

**Fix**: not fixable proactively. Leave as-is. ADR-031 aspirational-audit will re-classify if ever triggered.

**Effort**: 0.

**Status**: expected-aspirational. Document as "intentionally inactive until needed".

### A4. ADR-030 Q1 obedience

**Problem**: compliance-test requires data (JSONL rows). Hooks log starting from commit `2cb7655` — no data yet.

**Fix**: wait for organic accumulation. After 1 week with real use, re-run
`pytest tests/integration/test_auto_trigger_honoured.py` — skip turns into pass/fail.

**Effort**: 0 (time-based).

**Verification**: 1 week from 2026-04-20, `pytest -v tests/integration/test_auto_trigger_honoured.py` shows no skips on the data-dependent tests.

## DORMANT → REAL (9 items)

### D1. `process_registry` reaper — cron schedule

**Problem**: `cleanup_expired` runs only at `SessionEnd` (session-end-reap.sh). Dead processes with expired TTL linger the whole session.

**Fix**: add cron entry (via `mcp__scheduled-tasks` OR a lightweight shell wrapper invoked by a periodic SessionStart check) that runs `bash scripts/so-reaper.sh` every 5 min. Matches ADR-028 D1.B spec.

**First step**: create `hooks/reaper-heartbeat.sh` at SessionStart that schedules the reaper via `mcp__scheduled-tasks create_scheduled_task` with `--interval=300s`. Or: simple bash-level `while sleep 300; do bash scripts/so-reaper.sh; done &` guarded by single-instance lock.

**Effort**: 30 min.

**Verification**: `.cognitive-os/metrics/processes.jsonl` shows `process.reaped` events from multiple timestamps during a single session.

### D2. `agent_bus_metrics` — native Agent bridge

**Problem**: adapter only fires when `ORCHESTRATOR_MODE=executor`. Native Agent (Claude Code default) bypasses it.

**Fix**: new hook `hooks/native-agent-heartbeat.sh` at `PostToolUse:Agent` + `PreToolUse:Agent` — synthesizes heartbeat events and writes them directly to `lib.agent_bus.FallbackBus` files. `AgentBusMetrics.on_heartbeat_event` then picks them up via its standard subscribe path.

**First step**:
```bash
# hooks/native-agent-heartbeat.sh (PreToolUse:Agent)
# Emits {"type":"heartbeat","agent_id":"<tool_use_id>","alive":true} to FallbackBus
```

**Effort**: 1 h.

**Verification**: after one agent launch, `.cognitive-os/metrics/agent-heartbeat.jsonl` has `agent_launched` AND `agent_completed` events.

### D3. D5 killswitch — scheduled exercise

**Problem**: 124 hooks source killswitch_check.sh but the flag is never flipped in production; mechanism untested at scale.

**Fix**: weekly chaos scenario (new test under `tests/chaos/test_killswitch_exercise.py`): flip flag → invoke a list of non-critical hooks → assert all exit 0 silently → restore. Run via `mcp__scheduled-tasks` weekly.

**First step**: add `test_killswitch_exercise` class with 3 scenarios (representative hooks from each category).

**Effort**: 30 min.

**Verification**: scheduled task logs to `.cognitive-os/metrics/chaos-runs.jsonl` with `event_type=killswitch.exercised`.

### D4. Chaos suite — weekly schedule

**Problem**: 5 chaos tests pass on demand; no recurring schedule = never measured across real time.

**Fix**: `mcp__scheduled-tasks create_scheduled_task` with `cron="0 3 * * 1"` (Mondays 3 AM) that runs `pytest tests/chaos/ -q` and writes result JSONL to `.cognitive-os/metrics/chaos-weekly.jsonl`.

**First step**: single CronCreate call with the cmd + log redirect.

**Effort**: 20 min.

**Verification**: after 1 week, check `.cognitive-os/metrics/chaos-weekly.jsonl` has at least 1 row.

### D5. ADR-027 Phase 1 `global-verify` — exercise scenario

**Problem**: hook registered but never observed blocking a real agent.

**Fix**: chaos test that synthetically invokes `bash hooks/global-verify.sh before` + modifies a tracked test to fail + runs `after` + asserts exit 1 + BLOCKED message. Add to chaos suite so it runs weekly (see D4).

**First step**: `tests/chaos/test_global_verify_regression_catches.py` with the end-to-end scenario.

**Effort**: 45 min.

**Verification**: `pytest tests/chaos/test_global_verify_regression_catches.py` passes AND produces a `verify.after.compared` MetricEvent with `delta_failed > 0`.

### D6. ADR-029 `reinvention-check` — synthetic trigger

**Problem**: hook registered, greps, writes JSONL, but no observed warning in orchestrator context.

**Fix**: add test that sends a stub Agent prompt claiming "create `lib/rate_limiter.py`" (which exists) → verify the hook emits additionalContext pointing to the existing module. Register in chaos suite.

**First step**: `tests/chaos/test_reinvention_check_fires.py` with synthetic tool_use JSON.

**Effort**: 30 min.

**Verification**: `tests/contracts/test_reinvention_check.py` asserts additionalContext contains existing module path.

### D7. `destructive-rm-blocker` + R3/R4/Q#5 — combined synthetic exercise

**Problem**: mechanisms correct, zero observed fires in production (nothing bad happened → nothing triggered).

**Fix**: single chaos scenario that attempts each dangerous pattern in agent context (with a flag indicating it's a safety drill, so logs are not alarm events but drill events). Covers R2, R3, R4, Q#5 in one test file.

**First step**: `tests/chaos/test_safety_drill.py` with 6 scenarios (rm -rf, stash pop, checkout HEAD -- from various contexts).

**Effort**: 1 h.

**Verification**: single pytest run green + drill events visible in `safety-drill.jsonl`.

### D8. D6 chaos — already covered by D4

Consolidated above.

### D9. ADR-030 compliance test data

**Problem**: logs wired at `2cb7655`, no accumulated data yet.

**Fix**: time-based. Re-run test after 1 week of organic use.

**Effort**: 0 (time).

**Verification**: `pytest tests/integration/test_auto_trigger_honoured.py -v` shows ≥1 non-skipped test about production data.

## Execution strategy

Total estimated work: **~5-6 hours** for a full sweep, depending on parallelism.

Recommended parallelism (3 sonnet agents, ~2 h wall):

**Agent 1**: A1 (ref_key_loader wire) + D5 (global-verify exercise test) + D6 (reinvention-check test)
**Agent 2**: D1 (reaper cron) + D2 (native-agent bridge) + D4 (chaos schedule via mcp__scheduled-tasks)
**Agent 3**: A2 (install.sh scope filter) + D7 (safety drill) + D3 (killswitch exercise)

A3, A4, D8, D9 are either intentionally untouched or purely time-based.

Expected post-sweep metrics:
- ASPIRATIONAL: 4 → 2 (A3, A4 remain by design; A1, A2 flip to REAL)
- DORMANT: 9 → 1-2 (D9 time-based; rest flip to REAL via exercise scenarios)
- Overall ratio: 68.5% → target < 40%

## First command to run in next session

```bash
# 1. Load the plan + engram state
cat docs/reports/next-session-plan-dormant-to-real.md | head -60

# 2. Re-run the audit to get current baseline
python3 scripts/aspirational-audit.py --dry-run

# 3. Pick an agent-1 / agent-2 / agent-3 track and go
```
