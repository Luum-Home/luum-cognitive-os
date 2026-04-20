# Artifact Verification Report — 2026-04-20

**Scope**: ADR-027, ADR-028, commits d176c07..92cf485 (2026-04-16 → 2026-04-20)
**Auditor**: Explore agent (read-only)
**Total artifacts verified**: 23
**Delivered in**: sonnet parallel audit (commit this report sidecar)

## Verification Table

| artifact | claim source | exists? | imports/syntax? | wired? | tested? | status |
|---|---|---|---|---|---|---|
| `lib/agent_bus_metrics.py` | ADR-028b D1.C; commit d176c07 | YES (14,970 B) | `from agent_bus_metrics import AgentBusMetrics` → ok | YES — `scripts/so-vitals.sh:51` imports `AgentBusMetrics`; `scripts/orchestrator.py` imports it | YES — `tests/contracts/test_agent_bus_metrics.py` 12 tests | **SHIPPED** |
| `lib/metric_event.py` | ADR-028 D1.A.1; commit 3d03419 | YES (5,984 B) | `from metric_event import MetricEvent, append_event` → ok | YES — 8 lib/ callers + 4 hook callers | YES — `tests/unit/test_metric_event.py` 28 tests | **SHIPPED** |
| `lib/process_registry.py` | ADR-028 D1.B; commit 3d03419 | YES (8,380 B) | `from process_registry import register, cleanup_expired, detect_orphans` → ok; class `ProcessRegistry` does NOT exist | YES — `scripts/so-reaper.sh:51` + `so-vitals.sh:51` use correct free-function API | YES — `tests/contracts/test_process_registry.py` 13 tests | **BROKEN** (class-name claim in commit body false; code works — only docs lie) |
| `lib/targeted_test_resolver.py` | ADR-027 Phase 1; commit e4a3c86 | YES (4,757 B) | `resolve_tests_for_changes` exported; class `TargetedTestResolver` does NOT exist | YES — `hooks/global-verify.sh:58` imports the correct function | YES — `tests/unit/test_targeted_test_resolver.py` 10 tests | **BROKEN** (same as above — class-name claim false) |
| `scripts/orchestrator.py` | ADR-028b; commit d176c07 | YES (8,114 B, executable) | syntax OK, smoke-tested | NO — 0 hooks/cron invoke it; manual/dogfood only | PARTIAL — smoke-test doc only, no pytest | **ASPIRATIONAL** (no production call path) |
| `scripts/so-vitals.sh` | ADR-028 D1.D; commit 3d03419 | YES (7,238 B) | `bash -n` OK | YES — called from chaos + contract tests, referenced in `rules/so-slo.md` | YES — `test_ram_ceiling.py` + `test_fd_exhaustion.py` | **SHIPPED** |
| `scripts/so-reaper.sh` | ADR-028 D1.B; commit 3d03419 | YES (2,327 B) | `bash -n` OK | YES — `hooks/session-end-reap.sh:13` calls it every Stop; `so-emergency-stop.sh` calls it | YES — exercised by `test_killswitch.py` + chaos tests | **SHIPPED** |
| `scripts/so-emergency-stop.sh` | ADR-028 Phase C+E; commit bc7f70b | YES (4,340 B) | `bash -n` OK | PARTIAL — intentionally manual (referenced by runbook) | YES — `test_killswitch.py` 5 tests | **PARTIAL** (by design) |
| `hooks/global-verify.sh` | ADR-027 Phase 1; commit dacd7dc | YES (8,958 B) | `bash -n` OK | YES — registered in `settings.json` PreToolUse + PostToolUse | YES — `test_global_verify.py` 7 tests | **SHIPPED** |
| `hooks/session-end-reap.sh` | ADR-028 D1.B | YES (526 B) | `bash -n` OK | YES — registered in `settings.json` Stop | YES — via `test_process_registry.py` + `test_killswitch.py` | **SHIPPED** |
| `hooks/valkey-ensure.sh` | commit 91cc078 | YES (4,174 B) | `bash -n` OK | YES — registered in `settings.json` SessionStart | YES — covered by `test_ram_ceiling.py` + `test_fd_invariant.py` | **SHIPPED** |
| `hooks/reinvention-check.sh` | commit 91cc078 | YES (1,906 B) | `bash -n` OK | YES — registered in `settings.json` PreToolUse | YES — `test_fd_invariant.py` runs it 3× | **SHIPPED** |
| `hooks/token-budget-monitor.sh` | commit 92cf485 (renamed from rate-limit-protection) | YES (3,320 B) | `bash -n` OK | YES — registered in `settings.json` PreToolUse Bash | YES — `test_rate_limit_protection.py` via `lib/token_budget_monitor.py` | **SHIPPED** |
| `hooks/_lib/killswitch_check.sh` | ADR-028 Phase E; commit bc7f70b | YES (3,171 B) | `bash -n` OK | **NO** — grep of `hooks/*.sh` for `source.*_lib/killswitch_check` returns 0 real hook files sourcing it | YES — `test_killswitch.py` 5 tests exercise flag logic directly | **ASPIRATIONAL** (guard library never sourced in production hooks) |
| `hooks/_lib/register-bg.sh` | commit 0f72398 | YES (1,904 B) | `bash -n` OK | PARTIAL — `paperclip-notify.sh` uses own `_paperclip_register_bg` wrapper; `skill-usage-tracker.sh` claim to use `_register_bg` not confirmed by grep | NO — no pytest test for this helper | **PARTIAL** |
| `rules/so-slo.md` | ADR-028 Phase E; commit bc7f70b | YES (4,791 B, 61 lines) | n/a | **NO** — not in `settings.json` includedFiles, not in `rules/RULES-COMPACT.md`, not auto-loaded | NO | **ASPIRATIONAL** (reference doc, no runtime wiring) |
| `docs/runbooks/so-incident-runbook.md` | ADR-028 Phase E; commit bc7f70b | YES (7,228 B, 157 lines) | n/a | PARTIAL — human-operated runbook by design | NO | **PARTIAL** (by design) |
| `tests/contracts/test_agent_bus_metrics.py` | commit d176c07 | YES | pytest collects | YES | 12 tests | **SHIPPED** |
| `tests/contracts/test_fd_invariant.py` | commit e6a080a | YES | pytest collects | YES | 4 tests | **SHIPPED** |
| `tests/contracts/test_ram_ceiling.py` | commit e6a080a | YES | pytest collects | YES | 4 tests | **SHIPPED** |
| `tests/contracts/test_p95_hook_latency.py` | commit e6a080a | YES | pytest collects | YES | 4 tests | **SHIPPED** |
| `tests/contracts/test_killswitch.py` | commit bc7f70b | YES | pytest collects | YES | 5 tests | **SHIPPED** |
| `tests/chaos/test_*` (5 files) | commit bc7f70b + 92cf485 | YES all | pytest collects | YES | 9 tests | **SHIPPED** |

## Status Summary

| status | count | items |
|---|---|---|
| SHIPPED | 9 | agent_bus_metrics, metric_event, so-vitals, so-reaper, global-verify, session-end-reap, valkey-ensure, reinvention-check, token-budget-monitor |
| PARTIAL | 5 | so-emergency-stop, register-bg, so-incident-runbook, all contract + chaos test files (expected — they ARE the verification layer) |
| BROKEN | 2 | `lib/process_registry.py`, `lib/targeted_test_resolver.py` — class-name claims false but actual function API works |
| ASPIRATIONAL | 3 | `hooks/_lib/killswitch_check.sh` (never sourced), `scripts/orchestrator.py` (no production call path), `rules/so-slo.md` (not in auto-load chain) |

## BROKEN — Detail

### `lib/process_registry.py` — class name mismatch
- Commits 3d03419 and d176c07 refer to `ProcessRegistry` class.
- Actual exports: dataclass `ProcessRecord` + free functions (`register`, `deregister`, `cleanup_expired`, `detect_orphans`, `list_live`).
- `python3 -c "from process_registry import ProcessRegistry"` → `ImportError`.
- `so-reaper.sh` + `so-vitals.sh` use correct free-function API — no caller actually broken. Only commit-body claim is false.

### `lib/targeted_test_resolver.py` — class name mismatch
- Commit e4a3c86 and ADR-027 refer to `TargetedTestResolver` class.
- Actual export: `resolve_tests_for_changes` function; `__all__ = ["resolve_tests_for_changes"]`.
- `hooks/global-verify.sh` correctly imports the function — hook is functional. Class-name claim is false.

## ASPIRATIONAL — Detail

### `hooks/_lib/killswitch_check.sh`
- File exists, tests exist, but grep of `hooks/` for `source.*_lib/killswitch_check` returns **zero results** in any non-`_lib` hook.
- Only references outside the file: example block in ADR-028.md:561, runbook prose.
- ADR-028 checklist `[ ] Killswitch sourced as first real line` still open for every hook.
- Impact: if flag is set, no hook will self-suppress. `so-emergency-stop.sh` is NOT a no-op under the flag.

### `scripts/orchestrator.py`
- Exists, works by hand, smoke-tested.
- No `settings.json` hook, no cron, no `.sh` wrapper calls it.
- No `tests/contracts/test_orchestrator.py`.
- Developer tool only. ADR-028 "self-hosting loop" claim requires it to be invoked from SO infrastructure itself — not done.

### `rules/so-slo.md`
- Well-written 82 lines.
- Not in `rules/RULES-COMPACT.md`, not in `settings.json` `includedFiles`.
- Never loaded into any Claude context.
- ADR-028 action item `[ ] Add ref-key so-slo → rules/so-slo.md in RULES-COMPACT.md` still open.

## Duplicate Reuse Check

No unintentional duplicates this round.
- `lib/agent_bus_metrics.py` is an adapter over `agent_bus.py`, not a copy ✓
- `rate-limit-protection` → `token-budget-monitor` rename cleanly shimmed ✓
- hermes-agent `process_registry` is in plugin namespace, separate codebase ✓
- `hooks/_lib/register-bg.sh` vs `paperclip-notify.sh:_paperclip_register_bg` — minor duplication smell, not blocking

## ADR Open Checklist Items Affecting Wiring

- `ADR-028.md:584` `[ ] Killswitch sourced as first real line` → blocks `killswitch_check.sh` from SHIPPED
- `ADR-028.md:585` `[ ] All & / nohup / disown register a PID` → partial (register-bg.sh exists but not universally sourced)
- `ADR-028.md:587` `[ ] All JSONL writes use lib.metric_event` → partial
- `ADR-028a.md:320` `[ ] Add Complements ADR-028 D1.C comment to agent_bus_metrics.py` → cosmetic
- ADR-028 action item to add `so-slo` ref-key to `RULES-COMPACT.md` → open
