---
report_type: pyrefly-baseline-triage
date: 2026-05-15
tool: pyrefly
version: 1.0.0
source_receipt: .cognitive-os/reports/pyrefly/latest.txt
error_count: 268
---

# Pyrefly Baseline Manual Triage — 2026-05-15

## Executive Summary

I reviewed the full Pyrefly advisory baseline and grouped every reported error into fixable archetypes. This is not a suppression plan: most findings are real type/API-shape debt that should be reduced by narrowing untyped payloads, replacing `**dict` dataclass reconstruction, and guarding optional dependencies/callables.

| Metric | Value |
|---|---:|
| Total errors | 268 |
| Files touched by findings | 93 |
| Advisory runtime | 1–2 seconds after cache warm-up |
| Default missing-import mode | disabled |

## Error Archetypes

| Archetype | Count | Manual verdict | Fix pattern |
|---|---:|---|---|
| A14 local narrow fix / inspect individually | 99 | inspect individually | small local annotation or guard |
| A6 optional/missing attribute or optional dependency fallback | 29 | mixed | split optional dependency stubs from true API drift |
| A1 dataclass reconstruction from untyped dict | 28 | real debt | construct dataclasses explicitly or add typed from_dict helpers |
| A4 container shape not narrowed before indexing | 25 | real bug risk | isinstance guard dict/list before indexing |
| A3 numeric cast from object/None | 23 | real bug risk | use typed helpers for float/int extraction from dicts |
| A5 iterable not narrowed before loop/extend | 18 | real bug risk | coerce unknown config field to list[str] before iteration |
| A12 optional dependency type alias/fallback issue | 10 | mixed | move optional imports under TYPE_CHECKING/protocols or broaden aliases |
| A7 optional callable invoked without guard | 7 | real bug risk | guard callable is not None and raise/skip explicitly |
| A13 annotation too narrow for default/runtime value | 7 | low-risk typing debt | broaden annotation to Mapping/Collection/Optional |
| A8 TypedDict/schema mismatch | 7 | real schema debt | align TypedDict fields with actual payload |
| A9 return type from dict.get can be None | 6 | real API contract debt | validate fallback and cast only after guard |
| A10 risky protocol/dunder override typing | 4 | low-risk typing debt | avoid overriding str comparison on Enum or loosen signatures |
| A11 constructor/API signature drift | 3 | high priority | update caller or constructor compatibility shim |
| A2 JSON payload may be None/non-string | 2 | real bug risk | normalize Redis/webhook payload to str/bytes before json.loads |

## Prioritized File Review

| Priority | Errors | File | Dominant archetype | Manual review note |
|---|---:|---|---|---|
| P0 | 12 | `lib/webhook_trigger.py` | A6 optional/missing attribute or optional dependency fallback | API drift against `ClaudeExecutor`; also FastAPI optional fallback needs narrower route setup. Fix before any service-mode claim. |
| P1 | 27 | `lib/impact_analysis.py` | A14 local narrow fix / inspect individually | Mostly one local typing pattern: Pyrefly infers literal-only list. Low runtime risk; easy batch annotation. |
| P1 | 16 | `scripts/test_run_inventory.py` | A1 dataclass reconstruction from untyped dict | Two repeated `TestItem(**asdict(...))` patterns plus Counter from object. High leverage, safe explicit constructors. |
| P1 | 14 | `lib/agent_daemon.py` | A1 dataclass reconstruction from untyped dict | One repeated dataclass reconstruction. Fix with explicit `DetachedAgentTask(...)` or `replace()`. |
| P1 | 13 | `scripts/private_content_audit.py` | A4 container shape not narrowed before indexing | CLI output path reads unknown JSON/dict shapes; add isinstance guards before human rendering. |
| P1 | 12 | `scripts/cos_doc_path_audit.py` | A14 local narrow fix / inspect individually | CLI output path reads unknown JSON/dict shapes; add isinstance guards before human rendering. |
| P2 | 7 | `scripts/opencode_primitive_adapter_smoke.py` | A5 iterable not narrowed before loop/extend | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P2 | 6 | `lib/delete_intent.py` | A6 optional/missing attribute or optional dependency fallback | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P2 | 6 | `scripts/dogfood_score.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P2 | 6 | `scripts/primitive_gap_snapshot.py` | A3 numeric cast from object/None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P2 | 5 | `lib/prelaunch_audit.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P2 | 5 | `lib/sprint_orchestrator.py` | A12 optional dependency type alias/fallback issue | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P2 | 5 | `scripts/primitive_lifecycle.py` | A4 container shape not narrowed before indexing | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P2 | 5 | `scripts/radar_merge.py` | A4 container shape not narrowed before indexing | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P2 | 4 | `lib/process_user_message.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P2 | 4 | `scripts/adr_reserve.py` | A5 iterable not narrowed before loop/extend | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P2 | 4 | `scripts/cos_init.py` | A7 optional callable invoked without guard | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P2 | 4 | `scripts/cos_test_quality_audit.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P2 | 4 | `scripts/lab_first_promotion_gate.py` | A4 container shape not narrowed before indexing | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P2 | 4 | `scripts/primitive_harness_coverage.py` | A5 iterable not narrowed before loop/extend | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 3 | `lib/cost_predictor.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 3 | `lib/queue_advisor.py` | A4 container shape not narrowed before indexing | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 3 | `lib/routing_benchmark.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 3 | `lib/skill_description_enricher.py` | A4 container shape not narrowed before indexing | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 3 | `scripts/cos_falsification_benchmark.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/agent_bus.py` | A2 JSON payload may be None/non-string | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/agent_health_monitor.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/auto_repair.py` | A13 annotation too narrow for default/runtime value | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/changelog_generator.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/claude_executor.py` | A6 optional/missing attribute or optional dependency fallback | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/cognee_client.py` | A9 return type from dict.get can be None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/cost_dashboard.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/dispatch_gate.py` | A3 numeric cast from object/None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/gateway_selector.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/harness_adapter/codex.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/kpi_collector.py` | A3 numeric cast from object/None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/mlflow_bridge.py` | A13 annotation too narrow for default/runtime value | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/orchestrator_capabilities.py` | A6 optional/missing attribute or optional dependency fallback | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/outcome_metrics.py` | A3 numeric cast from object/None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/self_improvement.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `lib/smart_reader.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `scripts/acc_pipeline.py` | A8 TypedDict/schema mismatch | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `scripts/cos_watch.py` | A12 optional dependency type alias/fallback issue | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `scripts/cross_session_reconciler.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `scripts/orchestrator_claim_gate.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `scripts/queue_throughput_bench.py` | A6 optional/missing attribute or optional dependency fallback | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 2 | `scripts/so_vs_vanilla_benchmark.py` | A6 optional/missing attribute or optional dependency fallback | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/agent_bus_metrics.py` | A3 numeric cast from object/None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/agent_reflection.py` | A7 optional callable invoked without guard | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/agent_team_transport.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/context_injector.py` | A6 optional/missing attribute or optional dependency fallback | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/deferred_tool_loading.py` | A8 TypedDict/schema mismatch | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/dispatch_cost_predictor.py` | A3 numeric cast from object/None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/dispatch_model_advisor.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/engram_crystallizer.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/engram_graph_walker.py` | A3 numeric cast from object/None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/engram_lifecycle.py` | A3 numeric cast from object/None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/engram_locks.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/execution_profile.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/hook_types.py` | A3 numeric cast from object/None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/intent_arbiter.py` | A3 numeric cast from object/None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/language_dependence_audit.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/lethal_trifecta.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/maintainer_proposals.py` | A3 numeric cast from object/None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/memory_retrieval_benchmark.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/memory_retrieval_compare.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/orchestrator_verify.py` | A13 annotation too narrow for default/runtime value | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/performance_monitor.py` | A8 TypedDict/schema mismatch | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/reinvention_semantic.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/research_scoring.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/retry_classifier.py` | A12 optional dependency type alias/fallback issue | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/singularity.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/smart_access.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/smart_infra.py` | A9 return type from dict.get can be None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/work_queue.py` | A13 annotation too narrow for default/runtime value | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `lib/worktree_audit.py` | A12 optional dependency type alias/fallback issue | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/claim_enforcer.py` | A8 TypedDict/schema mismatch | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/cos_daemon.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/cos_demotion_loop_audit.py` | A6 optional/missing attribute or optional dependency fallback | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/cos_flow_register.py` | A6 optional/missing attribute or optional dependency fallback | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/cos_instance_init.py` | A6 optional/missing attribute or optional dependency fallback | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/cos_recovery_drill.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/cos_repair.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/cos_tier_claim_audit.py` | A5 iterable not narrowed before loop/extend | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/docs_duplicate_audit.py` | A3 numeric cast from object/None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/docs_execution_audit.py` | A6 optional/missing attribute or optional dependency fallback | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/hook_timing_report.py` | A5 iterable not narrowed before loop/extend | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/migrate_event_log_to_v2.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/parity_harness.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/portable_ai_overlay.py` | A14 local narrow fix / inspect individually | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/primitive_family_readiness_ledger.py` | A9 return type from dict.get can be None | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/security_red_team.py` | A8 TypedDict/schema mismatch | Review with archetype fix; likely narrow untyped dict/object values before use. |
| P3 | 1 | `scripts/update_readme_badges.py` | A3 numeric cast from object/None | Review with archetype fix; likely narrow untyped dict/object values before use. |

## Recommended Attack Order

1. **P0: API drift** — `lib/webhook_trigger.py` has actual constructor/method mismatch with `ClaudeExecutor`; decide whether this surface is live, archived, or needs a compatibility adapter.
2. **P1 repeated mechanical fixes** — `scripts/test_run_inventory.py`, `lib/agent_daemon.py`, `scripts/private_content_audit.py`, `scripts/cos_doc_path_audit.py`; these reduce many errors with low behavioral risk.
3. **Typed payload helpers** — add small local helpers for numeric/dict/list extraction in modules with repeated `dict.get` / `Any | None` failures.
4. **Optional dependency typing** — separate optional import runtime fallback from type-check surface using `TYPE_CHECKING`, Protocols, or local shims.
5. **Only then ratchet** — add a baseline/new-error ratchet; do not attempt zero-baseline gating immediately.

## Full Error Ledger

Every Pyrefly error from the 2026-05-15 advisory receipt is listed below with its manual archetype.

| # | File:line | Code | Archetype | Message |
|---:|---|---|---|---|
| 1 | `lib/agent_bus.py:502:47` | `bad-argument-type` | A2 JSON payload may be None/non-string | Argument `str \| Unknown \| None` is not assignable to parameter `s` with type `bytearray \| bytes \| str` in function `json.loads` |
| 2 | `lib/agent_bus.py:556:43` | `bad-argument-type` | A2 JSON payload may be None/non-string | Argument `str \| Unknown \| None` is not assignable to parameter `s` with type `bytearray \| bytes \| str` in function `json.loads` |
| 3 | `lib/agent_bus_metrics.py:187:39` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Any \| None` is not assignable to parameter `x` with type `Buffer \| SupportsFloat \| SupportsIndex \| str` in function `float.__new__` |
| 4 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `schema_version` with type `str` in function `DetachedAgentTask.__init__` |
| 5 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `task_id` with type `str` in function `DetachedAgentTask.__init__` |
| 6 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `session_id` with type `str` in function `DetachedAgentTask.__init__` |
| 7 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `command` with type `str` in function `DetachedAgentTask.__init__` |
| 8 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `project_dir` with type `str` in function `DetachedAgentTask.__init__` |
| 9 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `worktree_path` with type `str` in function `DetachedAgentTask.__init__` |
| 10 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `status` with type `str` in function `DetachedAgentTask.__init__` |
| 11 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `tmux_session` with type `str` in function `DetachedAgentTask.__init__` |
| 12 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `created_at` with type `float` in function `DetachedAgentTask.__init__` |
| 13 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `updated_at` with type `float` in function `DetachedAgentTask.__init__` |
| 14 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `team_name` with type `str \| None` in function `DetachedAgentTask.__init__` |
| 15 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `max_runtime_seconds` with type `int` in function `DetachedAgentTask.__init__` |
| 16 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `estimated_cost_usd` with type `float` in function `DetachedAgentTask.__init__` |
| 17 | `lib/agent_daemon.py:377:37` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `float \| str \| Any` is not assignable to parameter `budget_cap_usd` with type `float` in function `DetachedAgentTask.__init__` |
| 18 | `lib/agent_health_monitor.py:426:24` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `Any \| None` is not assignable to parameter `prompt` with type `str` in function `lib.queue_drainer.QueueDrainer.enqueue` |
| 19 | `lib/agent_health_monitor.py:427:29` | `unsupported-operation` | A4 container shape not narrowed before indexing | `None` is not subscriptable |
| 20 | `lib/agent_reflection.py:82:40` | `not-callable` | A7 optional callable invoked without guard | Expected a callable, got `None` |
| 21 | `lib/agent_team_transport.py:114:28` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `Awaitable[Any]` is not assignable to parameter `main` with type `Coroutine[Any, Any, @_]` in function `asyncio.runners.run` |
| 22 | `lib/auto_repair.py:101:29` | `bad-assignment` | A13 annotation too narrow for default/runtime value | `None` is not assignable to `Pattern[Unknown]` |
| 23 | `lib/auto_repair.py:627:35` | `bad-typed-dict-key` | A8 TypedDict/schema mismatch | `int` is not assignable to TypedDict key `exit_code` with type `bool \| str` |
| 24 | `lib/changelog_generator.py:154:26` | `no-matching-overload` | A14 local narrow fix / inspect individually | No matching overload found for function `sum` called with arguments: (Generator[Unknown \| None]) |
| 25 | `lib/changelog_generator.py:174:25` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `list[Unknown \| None] \| list[Unknown]` is not assignable to parameter `tasks_completed` with type `list[str]` in function `SessionChangelog.__init__` |
| 26 | `lib/claude_executor.py:842:26` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `Stream` has no attribute `content` |
| 27 | `lib/claude_executor.py:847:21` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `Stream` has no attribute `usage` |
| 28 | `lib/cognee_client.py:186:20` | `bad-return` | A9 return type from dict.get can be None | Returned type `Any \| None` is not assignable to declared return type `str` |
| 29 | `lib/cognee_client.py:221:20` | `bad-return` | A9 return type from dict.get can be None | Returned type `Any \| None` is not assignable to declared return type `list[dict[str, Any]]` |
| 30 | `lib/context_injector.py:189:9` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `EmbeddingsIndex` has no attribute `load_index` |
| 31 | `lib/cost_dashboard.py:146:19` | `unsupported-operation` | A14 local narrow fix / inspect individually | Cannot set item in `dict[str, float]` |
| 32 | `lib/cost_dashboard.py:146:42` | `no-matching-overload` | A14 local narrow fix / inspect individually | No matching overload found for function `dict.get` called with arguments: (Unknown \| None, float) |
| 33 | `lib/cost_predictor.py:387:33` | `unsupported-operation` | A14 local narrow fix / inspect individually | Cannot set item in `dict[str, dict[str, float]]` |
| 34 | `lib/cost_predictor.py:395:33` | `unsupported-operation` | A14 local narrow fix / inspect individually | Cannot set item in `dict[str, dict[str, float]]` |
| 35 | `lib/cost_predictor.py:404:33` | `unsupported-operation` | A14 local narrow fix / inspect individually | Cannot set item in `dict[str, dict[str, float]]` |
| 36 | `lib/deferred_tool_loading.py:48:38` | `bad-typed-dict-key` | A8 TypedDict/schema mismatch | `dict[str, Any]` is not assignable to TypedDict key `token_delta` with type `bool \| list[str] \| str` |
| 37 | `lib/delete_intent.py:178:74` | `bad-function-definition` | A13 annotation too narrow for default/runtime value | Default `frozenset[@_]` is not assignable to parameter `options_with_values` with type `set[str]` |
| 38 | `lib/delete_intent.py:259:11` | `bad-assignment` | A13 annotation too narrow for default/runtime value | `_Environ[str] \| dict[str, str]` is not assignable to variable `env` with type `dict[str, str] \| None` |
| 39 | `lib/delete_intent.py:260:20` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `get` |
| 40 | `lib/delete_intent.py:261:22` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `get` |
| 41 | `lib/delete_intent.py:262:14` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `get` |
| 42 | `lib/delete_intent.py:262:46` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `get` |
| 43 | `lib/dispatch_cost_predictor.py:75:70` | `bad-argument-type` | A3 numeric cast from object/None | Argument `object` is not assignable to parameter `x` with type `Buffer \| SupportsFloat \| SupportsIndex \| str` in function `float.__new__` |
| 44 | `lib/dispatch_gate.py:129:24` | `bad-argument-type` | A3 numeric cast from object/None | Argument `float \| object` is not assignable to parameter `x` with type `Buffer \| SupportsFloat \| SupportsIndex \| str` in function `float.__new__` |
| 45 | `lib/dispatch_gate.py:149:24` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Literal[0] \| object` is not assignable to parameter `x` with type `Buffer \| SupportsIndex \| SupportsInt \| SupportsTrunc \| str` in function `int.__new__` |
| 46 | `lib/dispatch_model_advisor.py:663:13` | `unsupported-operation` | A14 local narrow fix / inspect individually | `/` is not supported between `None` and `Literal['.cognitive-os']` |
| 47 | `lib/engram_crystallizer.py:376:63` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str \| None` is not assignable to parameter `project` with type `str` in function `lib.engram_http_client.get_recent` |
| 48 | `lib/engram_graph_walker.py:208:30` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Any \| None` is not assignable to parameter `x` with type `Buffer \| SupportsFloat \| SupportsIndex \| str` in function `float.__new__` |
| 49 | `lib/engram_lifecycle.py:563:17` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Any \| None` is not assignable to parameter `x` with type `Buffer \| SupportsFloat \| SupportsIndex \| str` in function `float.__new__` |
| 50 | `lib/engram_locks.py:144:27` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `Any \| None` is not assignable to parameter `ts` with type `str` in function `_seconds_since` |
| 51 | `lib/execution_profile.py:213:42` | `no-matching-overload` | A14 local narrow fix / inspect individually | No matching overload found for function `dict.get` called with arguments: (Unknown \| None, ExecutionProfile) |
| 52 | `lib/gateway_selector.py:110:22` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str \| None` is not assignable to parameter `base_url` with type `str` in function `GatewayConfig.__init__` |
| 53 | `lib/gateway_selector.py:123:18` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str \| None` is not assignable to parameter `base_url` with type `str` in function `GatewayConfig.__init__` |
| 54 | `lib/harness_adapter/codex.py:230:27` | `unsupported-operation` | A14 local narrow fix / inspect individually | `*` is not supported between `None` and `Literal[1000]` |
| 55 | `lib/harness_adapter/codex.py:230:69` | `unsupported-operation` | A14 local narrow fix / inspect individually | `//` is not supported between `None` and `Literal[1000000]` |
| 56 | `lib/hook_types.py:137:28` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Any \| None` is not assignable to parameter `x` with type `Buffer \| SupportsIndex \| SupportsInt \| SupportsTrunc \| str` in function `int.__new__` |
| 57 | `lib/impact_analysis.py:30:9` | `bad-override` | A10 risky protocol/dunder override typing | Class member `RiskLevel.__lt__` overrides parent class `str` in an inconsistent manner |
| 58 | `lib/impact_analysis.py:34:9` | `bad-override` | A10 risky protocol/dunder override typing | Class member `RiskLevel.__le__` overrides parent class `str` in an inconsistent manner |
| 59 | `lib/impact_analysis.py:37:9` | `bad-override` | A10 risky protocol/dunder override typing | Class member `RiskLevel.__gt__` overrides parent class `str` in an inconsistent manner |
| 60 | `lib/impact_analysis.py:40:9` | `bad-override` | A10 risky protocol/dunder override typing | Class member `RiskLevel.__ge__` overrides parent class `str` in an inconsistent manner |
| 61 | `lib/impact_analysis.py:527:18` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 62 | `lib/impact_analysis.py:530:22` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 63 | `lib/impact_analysis.py:534:18` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 64 | `lib/impact_analysis.py:536:22` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 65 | `lib/impact_analysis.py:542:22` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 66 | `lib/impact_analysis.py:545:26` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 67 | `lib/impact_analysis.py:547:30` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 68 | `lib/impact_analysis.py:553:22` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 69 | `lib/impact_analysis.py:556:26` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 70 | `lib/impact_analysis.py:558:30` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 71 | `lib/impact_analysis.py:564:22` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 72 | `lib/impact_analysis.py:567:26` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 73 | `lib/impact_analysis.py:569:30` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 74 | `lib/impact_analysis.py:577:22` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 75 | `lib/impact_analysis.py:580:26` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 76 | `lib/impact_analysis.py:586:22` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 77 | `lib/impact_analysis.py:589:26` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 78 | `lib/impact_analysis.py:591:30` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 79 | `lib/impact_analysis.py:597:18` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 80 | `lib/impact_analysis.py:598:18` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 81 | `lib/impact_analysis.py:599:18` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 82 | `lib/impact_analysis.py:600:18` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 83 | `lib/impact_analysis.py:601:18` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 84 | `lib/intent_arbiter.py:247:22` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Any \| None` is not assignable to parameter `x` with type `Buffer \| SupportsIndex \| SupportsInt \| SupportsTrunc \| str` in function `int.__new__` |
| 85 | `lib/kpi_collector.py:81:21` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Any \| None` is not assignable to parameter `x` with type `Buffer \| SupportsFloat \| SupportsIndex \| str` in function `float.__new__` |
| 86 | `lib/kpi_collector.py:87:16` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Any \| None` is not assignable to parameter `x` with type `Buffer \| SupportsIndex \| SupportsInt \| SupportsTrunc \| str` in function `int.__new__` |
| 87 | `lib/language_dependence_audit.py:217:50` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `SubPattern` is not assignable to parameter `parsed` with type `Iterable[tuple[Any, Any]]` in function `_iter_regex_literals` |
| 88 | `lib/lethal_trifecta.py:122:32` | `no-matching-overload` | A14 local narrow fix / inspect individually | No matching overload found for function `dict.__init__` called with arguments: (dict[str, Unknown] \| Any \| None) |
| 89 | `lib/maintainer_proposals.py:66:24` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Unknown \| None` is not assignable to parameter `x` with type `Buffer \| SupportsFloat \| SupportsIndex \| str` in function `float.__new__` |
| 90 | `lib/memory_retrieval_benchmark.py:366:25` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `bool \| float \| list[dict[str, Any]] \| list[Unknown] \| str \| Any` is not assignable to parameter `iterable` with type `Iterable[Unknown]` in function `list.extend` |
| 91 | `lib/memory_retrieval_compare.py:71:43` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `Any \| None` is not assignable to parameter `*args` with type `PathLike[str] \| str` in function `pathlib.Path.__new__` |
| 92 | `lib/mlflow_bridge.py:31:32` | `bad-assignment` | A13 annotation too narrow for default/runtime value | `None` is not assignable to attribute `_mlflow` with type `Module[mlflow]` |
| 93 | `lib/mlflow_bridge.py:33:28` | `bad-assignment` | A13 annotation too narrow for default/runtime value | `None` is not assignable to attribute `_mlflow` with type `Module[mlflow]` |
| 94 | `lib/orchestrator_capabilities.py:170:32` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `upper` |
| 95 | `lib/orchestrator_capabilities.py:178:24` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `upper` |
| 96 | `lib/orchestrator_verify.py:133:35` | `bad-assignment` | A13 annotation too narrow for default/runtime value | `list[ground_truth.Claim] \| list[lib.ground_truth.Claim]` is not assignable to `list[ground_truth.Claim \| lib.ground_truth.Claim]` |
| 97 | `lib/outcome_metrics.py:51:24` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Literal[0] \| object` is not assignable to parameter `x` with type `Buffer \| SupportsFloat \| SupportsIndex \| str` in function `float.__new__` |
| 98 | `lib/outcome_metrics.py:52:20` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Literal[0] \| object` is not assignable to parameter `x` with type `Buffer \| SupportsFloat \| SupportsIndex \| str` in function `float.__new__` |
| 99 | `lib/performance_monitor.py:587:38` | `bad-typed-dict-key` | A8 TypedDict/schema mismatch | `dict[str, Any]` is not assignable to TypedDict key `metadata` with type `bool \| float \| str` |
| 100 | `lib/prelaunch_audit.py:195:28` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `dict[str, bool \| str]` is not assignable to parameter `object` with type `dict[str, str]` in function `list.append` |
| 101 | `lib/prelaunch_audit.py:199:21` | `unsupported-operation` | A14 local narrow fix / inspect individually | Cannot set item in `list[dict[str, str]]` |
| 102 | `lib/prelaunch_audit.py:210:34` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `tuple[str, str]` is not assignable to parameter `object` with type `str` in function `list.append` |
| 103 | `lib/prelaunch_audit.py:212:34` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `tuple[str, str]` is not assignable to parameter `object` with type `str` in function `list.append` |
| 104 | `lib/prelaunch_audit.py:212:41` | `unbound-name` | A14 local narrow fix / inspect individually | `current_file` is uninitialized |
| 105 | `lib/process_user_message.py:20:42` | `unsupported-operation` | A14 local narrow fix / inspect individually | Cannot set item in `dict[str, str]` |
| 106 | `lib/process_user_message.py:28:37` | `unsupported-operation` | A14 local narrow fix / inspect individually | Cannot set item in `dict[str, str]` |
| 107 | `lib/process_user_message.py:35:37` | `unsupported-operation` | A14 local narrow fix / inspect individually | Cannot set item in `dict[str, str]` |
| 108 | `lib/process_user_message.py:38:37` | `unsupported-operation` | A14 local narrow fix / inspect individually | Cannot set item in `dict[str, str]` |
| 109 | `lib/queue_advisor.py:166:29` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `Any \| None` is not assignable to parameter `obj` with type `Sized` in function `len` |
| 110 | `lib/queue_advisor.py:708:22` | `unsupported-operation` | A4 container shape not narrowed before indexing | `None` is not subscriptable |
| 111 | `lib/queue_advisor.py:720:24` | `unsupported-operation` | A4 container shape not narrowed before indexing | `None` is not subscriptable |
| 112 | `lib/reinvention_semantic.py:455:31` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `Unknown \| None` is not assignable to parameter `arr` with type `_Buffer \| _NestedSequence[bytes \| complex \| str] \| _NestedSequence[_SupportsArray[dtype]] \| _SupportsArray[dtype] \| bytes \| complex \| str` in function `numpy.lib._npyio_impl.save` |
| 113 | `lib/research_scoring.py:102:32` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `Unknown \| None` is not assignable to parameter `text` with type `str` in function `_tokenize` |
| 114 | `lib/retry_classifier.py:16:20` | `invalid-inheritance` | A12 optional dependency type alias/fallback issue | Invalid base class: `lib.retry_classifier.StrEnum \| enum.StrEnum` |
| 115 | `lib/routing_benchmark.py:279:22` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `embed` |
| 116 | `lib/routing_benchmark.py:413:13` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str \| None` is not assignable to parameter `path_or_bytes` with type `PathLike[Unknown] \| bytes \| str` in function `onnxruntime.capi.onnxruntime_inference_collection.InferenceSession.__init__` |
| 117 | `lib/routing_benchmark.py:415:32` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str \| None` is not assignable to parameter `*args` with type `PathLike[str] \| str` in function `pathlib.Path.__new__` |
| 118 | `lib/self_improvement.py:70:21` | `unsupported-operation` | A14 local narrow fix / inspect individually | Cannot set item in `dict[str, int]` |
| 119 | `lib/self_improvement.py:70:45` | `no-matching-overload` | A14 local narrow fix / inspect individually | No matching overload found for function `dict.get` called with arguments: (Any \| None, Literal[0]) |
| 120 | `lib/singularity.py:396:32` | `no-matching-overload` | A14 local narrow fix / inspect individually | No matching overload found for function `typing.MutableMapping.setdefault` called with arguments: (Any \| None, list[@_]) |
| 121 | `lib/skill_description_enricher.py:566:22` | `unsupported-operation` | A4 container shape not narrowed before indexing | `Literal[True]` is not subscriptable |
| 122 | `lib/skill_description_enricher.py:571:52` | `unsupported-operation` | A4 container shape not narrowed before indexing | `Literal[True]` is not subscriptable |
| 123 | `lib/skill_description_enricher.py:574:33` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `Literal[True] \| str \| Any` is not assignable to parameter `text` with type `str` in function `parse_llm_response` |
| 124 | `lib/smart_access.py:124:25` | `unsupported-operation` | A14 local narrow fix / inspect individually | `+` is not supported between `None` and `Literal[2]` |
| 125 | `lib/smart_infra.py:217:16` | `bad-return` | A9 return type from dict.get can be None | Returned type `None` is not assignable to declared return type `dict[str, Any]` |
| 126 | `lib/smart_reader.py:285:20` | `unbound-name` | A14 local narrow fix / inspect individually | `compiled` may be uninitialized |
| 127 | `lib/smart_reader.py:395:45` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `dict[str, int \| str]` is not assignable to parameter `object` with type `dict[str, int]` in function `list.append` |
| 128 | `lib/sprint_orchestrator.py:141:21` | `invalid-inheritance` | A12 optional dependency type alias/fallback issue | Invalid base class: `harness_adapter.base.CanonicalEvent \| lib.harness_adapter.base.CanonicalEvent` |
| 129 | `lib/sprint_orchestrator.py:153:26` | `invalid-inheritance` | A12 optional dependency type alias/fallback issue | Invalid base class: `harness_adapter.base.CanonicalEvent \| lib.harness_adapter.base.CanonicalEvent` |
| 130 | `lib/sprint_orchestrator.py:165:27` | `invalid-inheritance` | A12 optional dependency type alias/fallback issue | Invalid base class: `harness_adapter.base.CanonicalEvent \| lib.harness_adapter.base.CanonicalEvent` |
| 131 | `lib/sprint_orchestrator.py:178:23` | `invalid-inheritance` | A12 optional dependency type alias/fallback issue | Invalid base class: `harness_adapter.base.CanonicalEvent \| lib.harness_adapter.base.CanonicalEvent` |
| 132 | `lib/sprint_orchestrator.py:188:23` | `invalid-inheritance` | A12 optional dependency type alias/fallback issue | Invalid base class: `harness_adapter.base.CanonicalEvent \| lib.harness_adapter.base.CanonicalEvent` |
| 133 | `lib/webhook_trigger.py:248:9` | `unexpected-keyword` | A11 constructor/API signature drift | Unexpected keyword argument `project_dir` in function `lib.claude_executor.ClaudeExecutor.__init__` |
| 134 | `lib/webhook_trigger.py:249:9` | `unexpected-keyword` | A11 constructor/API signature drift | Unexpected keyword argument `claude_bin` in function `lib.claude_executor.ClaudeExecutor.__init__` |
| 135 | `lib/webhook_trigger.py:250:9` | `unexpected-keyword` | A11 constructor/API signature drift | Unexpected keyword argument `timeout_seconds` in function `lib.claude_executor.ClaudeExecutor.__init__` |
| 136 | `lib/webhook_trigger.py:270:18` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `ClaudeExecutor` has no attribute `run_phase` |
| 137 | `lib/webhook_trigger.py:319:11` | `not-callable` | A7 optional callable invoked without guard | Expected a callable, got `None` |
| 138 | `lib/webhook_trigger.py:345:26` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `body` |
| 139 | `lib/webhook_trigger.py:346:22` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `headers` |
| 140 | `lib/webhook_trigger.py:349:19` | `not-callable` | A7 optional callable invoked without guard | Expected a callable, got `None` |
| 141 | `lib/webhook_trigger.py:352:22` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `headers` |
| 142 | `lib/webhook_trigger.py:356:19` | `not-callable` | A7 optional callable invoked without guard | Expected a callable, got `None` |
| 143 | `lib/webhook_trigger.py:439:5` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `run` |
| 144 | `lib/webhook_trigger.py:439:17` | `unbound-name` | A14 local narrow fix / inspect individually | `app` may be uninitialized |
| 145 | `lib/work_queue.py:68:42` | `bad-function-definition` | A13 annotation too narrow for default/runtime value | Default `None` is not assignable to parameter `depends_on` with type `list[str]` |
| 146 | `lib/worktree_audit.py:181:50` | `bad-specialization` | A12 optional dependency type alias/fallback issue | `object` is not assignable to upper bound `SupportsDunderGT[Any] \| SupportsDunderLT[Any]` of type variable `SupportsRichComparisonT` |
| 147 | `scripts/acc_pipeline.py:750:47` | `bad-typed-dict-key` | A8 TypedDict/schema mismatch | `str` is not assignable to TypedDict key `claim_map_status` with type `dict[str, int] \| int` |
| 148 | `scripts/acc_pipeline.py:752:50` | `bad-typed-dict-key` | A8 TypedDict/schema mismatch | `str` is not assignable to TypedDict key `claim_map_error` with type `dict[str, int] \| int` |
| 149 | `scripts/adr_reserve.py:77:17` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `object` is not iterable |
| 150 | `scripts/adr_reserve.py:115:30` | `bad-argument-type` | A3 numeric cast from object/None | Argument `object \| None` is not assignable to parameter `x` with type `Buffer \| SupportsIndex \| SupportsInt \| SupportsTrunc \| str` in function `int.__new__` |
| 151 | `scripts/adr_reserve.py:181:17` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `object` is not iterable |
| 152 | `scripts/adr_reserve.py:203:21` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `object` is not iterable |
| 153 | `scripts/claim_enforcer.py:42:34` | `bad-typed-dict-key` | A8 TypedDict/schema mismatch | `dict[Unknown, Unknown]` is not assignable to TypedDict key `details` with type `str` |
| 154 | `scripts/cos_daemon.py:185:13` | `bad-override-param-name` | A14 local narrow fix / inspect individually | Class member `CosdHandler.log_message` overrides parent class `BaseHTTPRequestHandler` in an inconsistent manner |
| 155 | `scripts/cos_demotion_loop_audit.py:134:35` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `isoformat` |
| 156 | `scripts/cos_doc_path_audit.py:398:29` | `bad-index` | A14 local narrow fix / inspect individually | Cannot index into `object` |
| 157 | `scripts/cos_doc_path_audit.py:399:34` | `bad-index` | A14 local narrow fix / inspect individually | Cannot index into `object` |
| 158 | `scripts/cos_doc_path_audit.py:400:36` | `bad-index` | A14 local narrow fix / inspect individually | Cannot index into `object` |
| 159 | `scripts/cos_doc_path_audit.py:401:24` | `bad-index` | A14 local narrow fix / inspect individually | Cannot index into `object` |
| 160 | `scripts/cos_doc_path_audit.py:406:23` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `object` has no attribute `items` |
| 161 | `scripts/cos_doc_path_audit.py:414:21` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `object` is not iterable |
| 162 | `scripts/cos_doc_path_audit.py:450:42` | `bad-index` | A14 local narrow fix / inspect individually | Cannot index into `object` |
| 163 | `scripts/cos_doc_path_audit.py:452:41` | `bad-index` | A14 local narrow fix / inspect individually | Cannot index into `object` |
| 164 | `scripts/cos_doc_path_audit.py:454:45` | `bad-index` | A14 local narrow fix / inspect individually | Cannot index into `object` |
| 165 | `scripts/cos_doc_path_audit.py:456:43` | `bad-index` | A14 local narrow fix / inspect individually | Cannot index into `object` |
| 166 | `scripts/cos_doc_path_audit.py:458:38` | `bad-index` | A14 local narrow fix / inspect individually | Cannot index into `object` |
| 167 | `scripts/cos_doc_path_audit.py:485:69` | `bad-index` | A14 local narrow fix / inspect individually | Cannot index into `object` |
| 168 | `scripts/cos_falsification_benchmark.py:71:42` | `bad-specialization` | A12 optional dependency type alias/fallback issue | `Unknown \| None` is not assignable to upper bound `SupportsDunderGT[Any] \| SupportsDunderLT[Any]` of type variable `SupportsRichComparisonT` |
| 169 | `scripts/cos_falsification_benchmark.py:73:68` | `unsupported-operation` | A14 local narrow fix / inspect individually | `*` is not supported between `None` and `float` |
| 170 | `scripts/cos_falsification_benchmark.py:73:105` | `unsupported-operation` | A14 local narrow fix / inspect individually | `*` is not supported between `None` and `Literal[4]` |
| 171 | `scripts/cos_flow_register.py:113:73` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `strip` |
| 172 | `scripts/cos_init.py:151:20` | `bad-return` | A9 return type from dict.get can be None | Returned type `Unknown \| None` is not assignable to declared return type `str` |
| 173 | `scripts/cos_init.py:444:18` | `not-callable` | A7 optional callable invoked without guard | Expected a callable, got `object` |
| 174 | `scripts/cos_init.py:488:14` | `not-callable` | A7 optional callable invoked without guard | Expected a callable, got `object` |
| 175 | `scripts/cos_init.py:488:49` | `not-callable` | A7 optional callable invoked without guard | Expected a callable, got `object` |
| 176 | `scripts/cos_instance_init.py:141:13` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `str` has no attribute `append` |
| 177 | `scripts/cos_recovery_drill.py:33:24` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `dict[str, object]` is not assignable to parameter `object` with type `dict[str, int \| str]` in function `list.append` |
| 178 | `scripts/cos_repair.py:30:29` | `unsupported-operation` | A14 local narrow fix / inspect individually | Cannot set item in `dict[str, str]` |
| 179 | `scripts/cos_test_quality_audit.py:158:35` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `Call` is not assignable to parameter `object` with type `Assert` in function `list.append` |
| 180 | `scripts/cos_test_quality_audit.py:161:35` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `Call` is not assignable to parameter `object` with type `Assert` in function `list.append` |
| 181 | `scripts/cos_test_quality_audit.py:162:12` | `bad-return` | A9 return type from dict.get can be None | Returned type `list[Assert]` is not assignable to declared return type `list[AST]` |
| 182 | `scripts/cos_test_quality_audit.py:482:17` | `bad-argument-type` | A3 numeric cast from object/None | Argument `object` is not assignable to parameter `x` with type `Buffer \| SupportsIndex \| SupportsInt \| SupportsTrunc \| str` in function `int.__new__` |
| 183 | `scripts/cos_tier_claim_audit.py:134:24` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `object` is not iterable |
| 184 | `scripts/cos_watch.py:121:33` | `not-a-type` | A12 optional dependency type alias/fallback issue | Expected a type form, got instance of `(obj: object, /) -> TypeIs[(...) -> object]` |
| 185 | `scripts/cos_watch.py:154:31` | `not-a-type` | A12 optional dependency type alias/fallback issue | Expected a type form, got instance of `(obj: object, /) -> TypeIs[(...) -> object]` |
| 186 | `scripts/cross_session_reconciler.py:30:28` | `unsupported-operation` | A14 local narrow fix / inspect individually | Cannot set item in `dict[str, str]` |
| 187 | `scripts/cross_session_reconciler.py:30:57` | `unsupported-operation` | A14 local narrow fix / inspect individually | Cannot set item in `dict[str, str]` |
| 188 | `scripts/docs_duplicate_audit.py:234:39` | `bad-argument-type` | A3 numeric cast from object/None | Argument `object` is not assignable to parameter `x` with type `Buffer \| SupportsIndex \| SupportsInt \| SupportsTrunc \| str` in function `int.__new__` |
| 189 | `scripts/docs_execution_audit.py:210:26` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `object` has no attribute `items` |
| 190 | `scripts/dogfood_score.py:53:18` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 191 | `scripts/dogfood_score.py:57:22` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 192 | `scripts/dogfood_score.py:58:18` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 193 | `scripts/dogfood_score.py:66:13` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 194 | `scripts/dogfood_score.py:72:26` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 195 | `scripts/dogfood_score.py:75:22` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 196 | `scripts/hook_timing_report.py:303:21` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `None` is not iterable |
| 197 | `scripts/lab_first_promotion_gate.py:167:24` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `int` is not iterable |
| 198 | `scripts/lab_first_promotion_gate.py:168:24` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 199 | `scripts/lab_first_promotion_gate.py:168:51` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 200 | `scripts/lab_first_promotion_gate.py:168:71` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 201 | `scripts/migrate_event_log_to_v2.py:77:103` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `object` is not assignable to parameter `obj` with type `Sized` in function `len` |
| 202 | `scripts/opencode_primitive_adapter_smoke.py:169:37` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `bool` is not iterable |
| 203 | `scripts/opencode_primitive_adapter_smoke.py:169:37` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `int` is not iterable |
| 204 | `scripts/opencode_primitive_adapter_smoke.py:169:37` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `None` is not iterable |
| 205 | `scripts/opencode_primitive_adapter_smoke.py:170:54` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `bool` is not iterable |
| 206 | `scripts/opencode_primitive_adapter_smoke.py:170:54` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `int` is not iterable |
| 207 | `scripts/opencode_primitive_adapter_smoke.py:170:54` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `None` is not iterable |
| 208 | `scripts/opencode_primitive_adapter_smoke.py:172:59` | `unknown` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `get` |
| 209 | `scripts/orchestrator_claim_gate.py:396:22` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 210 | `scripts/orchestrator_claim_gate.py:398:26` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `str` is not assignable to parameter `object` with type `LiteralString` in function `list.append` |
| 211 | `scripts/parity_harness.py:412:36` | `missing-argument` | A14 local narrow fix / inspect individually | Missing argument `claude_executor` in function `run_via_claude` |
| 212 | `scripts/portable_ai_overlay.py:226:56` | `unbound-name` | A14 local narrow fix / inspect individually | `primitive_id` may be uninitialized |
| 213 | `scripts/primitive_family_readiness_ledger.py:147:12` | `bad-return` | A9 return type from dict.get can be None | Returned type `Literal[''] \| bool` is not assignable to declared return type `bool` |
| 214 | `scripts/primitive_gap_snapshot.py:356:30` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Literal[0] \| object` is not assignable to parameter `x` with type `Buffer \| SupportsIndex \| SupportsInt \| SupportsTrunc \| str` in function `int.__new__` |
| 215 | `scripts/primitive_gap_snapshot.py:357:29` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Literal[0] \| object` is not assignable to parameter `x` with type `Buffer \| SupportsIndex \| SupportsInt \| SupportsTrunc \| str` in function `int.__new__` |
| 216 | `scripts/primitive_gap_snapshot.py:358:31` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Literal[0] \| object` is not assignable to parameter `x` with type `Buffer \| SupportsIndex \| SupportsInt \| SupportsTrunc \| str` in function `int.__new__` |
| 217 | `scripts/primitive_gap_snapshot.py:359:30` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Literal[0] \| object` is not assignable to parameter `x` with type `Buffer \| SupportsIndex \| SupportsInt \| SupportsTrunc \| str` in function `int.__new__` |
| 218 | `scripts/primitive_gap_snapshot.py:360:37` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Literal[0] \| object` is not assignable to parameter `x` with type `Buffer \| SupportsIndex \| SupportsInt \| SupportsTrunc \| str` in function `int.__new__` |
| 219 | `scripts/primitive_gap_snapshot.py:361:36` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Literal[0] \| object` is not assignable to parameter `x` with type `Buffer \| SupportsIndex \| SupportsInt \| SupportsTrunc \| str` in function `int.__new__` |
| 220 | `scripts/primitive_harness_coverage.py:398:50` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `bool` is not iterable |
| 221 | `scripts/primitive_harness_coverage.py:402:35` | `bad-argument-type` | A14 local narrow fix / inspect individually | Argument `Literal[True] \| list[str]` is not assignable to parameter `iterable` with type `Iterable[@_]` in function `set.__init__` |
| 222 | `scripts/primitive_harness_coverage.py:405:51` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `bool` is not iterable |
| 223 | `scripts/primitive_harness_coverage.py:406:51` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `bool` is not iterable |
| 224 | `scripts/primitive_lifecycle.py:354:24` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `bool` is not iterable |
| 225 | `scripts/primitive_lifecycle.py:354:24` | `not-iterable` | A5 iterable not narrowed before loop/extend | Type `int` is not iterable |
| 226 | `scripts/primitive_lifecycle.py:356:22` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 227 | `scripts/primitive_lifecycle.py:356:49` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 228 | `scripts/primitive_lifecycle.py:356:69` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 229 | `scripts/private_content_audit.py:375:70` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 230 | `scripts/private_content_audit.py:375:114` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 231 | `scripts/private_content_audit.py:380:22` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 232 | `scripts/private_content_audit.py:380:38` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 233 | `scripts/private_content_audit.py:380:55` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `str` has no attribute `get` |
| 234 | `scripts/private_content_audit.py:383:51` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `str` has no attribute `get` |
| 235 | `scripts/private_content_audit.py:383:82` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `str` has no attribute `get` |
| 236 | `scripts/private_content_audit.py:383:112` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `str` has no attribute `get` |
| 237 | `scripts/private_content_audit.py:384:56` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `dict[str, Any]` |
| 238 | `scripts/private_content_audit.py:385:26` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 239 | `scripts/private_content_audit.py:385:56` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 240 | `scripts/private_content_audit.py:385:74` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 241 | `scripts/private_content_audit.py:385:93` | `bad-index` | A4 container shape not narrowed before indexing | Cannot index into `str` |
| 242 | `scripts/queue_throughput_bench.py:300:22` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `BaseContext` has no attribute `Process` |
| 243 | `scripts/queue_throughput_bench.py:313:17` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `BaseContext` has no attribute `Process` |
| 244 | `scripts/radar_merge.py:402:25` | `unsupported-operation` | A4 container shape not narrowed before indexing | `None` is not subscriptable |
| 245 | `scripts/radar_merge.py:403:26` | `unsupported-operation` | A4 container shape not narrowed before indexing | `None` is not subscriptable |
| 246 | `scripts/radar_merge.py:404:28` | `unsupported-operation` | A4 container shape not narrowed before indexing | `None` is not subscriptable |
| 247 | `scripts/radar_merge.py:406:31` | `unsupported-operation` | A4 container shape not narrowed before indexing | `None` is not subscriptable |
| 248 | `scripts/radar_merge.py:406:68` | `unsupported-operation` | A4 container shape not narrowed before indexing | `None` is not subscriptable |
| 249 | `scripts/security_red_team.py:549:31` | `bad-typed-dict-key` | A8 TypedDict/schema mismatch | `int` is not assignable to TypedDict key `overall_score` with type `dict[str, Any] \| list[dict[str, str]] \| list[dict[str, Any]] \| str` |
| 250 | `scripts/so_vs_vanilla_benchmark.py:233:5` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `signal_matched` |
| 251 | `scripts/so_vs_vanilla_benchmark.py:234:5` | `missing-attribute` | A6 optional/missing attribute or optional dependency fallback | Object of class `NoneType` has no attribute `signal_matched` |
| 252 | `scripts/test_run_inventory.py:129:17` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `nodeid` with type `str` in function `TestItem.__init__` |
| 253 | `scripts/test_run_inventory.py:129:17` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `outcome` with type `str` in function `TestItem.__init__` |
| 254 | `scripts/test_run_inventory.py:129:17` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `file` with type `str` in function `TestItem.__init__` |
| 255 | `scripts/test_run_inventory.py:129:17` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `test` with type `str` in function `TestItem.__init__` |
| 256 | `scripts/test_run_inventory.py:129:17` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `duration_seconds` with type `float` in function `TestItem.__init__` |
| 257 | `scripts/test_run_inventory.py:129:17` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `message` with type `str` in function `TestItem.__init__` |
| 258 | `scripts/test_run_inventory.py:129:17` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `details` with type `str` in function `TestItem.__init__` |
| 259 | `scripts/test_run_inventory.py:176:22` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `nodeid` with type `str` in function `TestItem.__init__` |
| 260 | `scripts/test_run_inventory.py:176:22` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `outcome` with type `str` in function `TestItem.__init__` |
| 261 | `scripts/test_run_inventory.py:176:22` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `file` with type `str` in function `TestItem.__init__` |
| 262 | `scripts/test_run_inventory.py:176:22` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `test` with type `str` in function `TestItem.__init__` |
| 263 | `scripts/test_run_inventory.py:176:22` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `duration_seconds` with type `float` in function `TestItem.__init__` |
| 264 | `scripts/test_run_inventory.py:176:22` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `message` with type `str` in function `TestItem.__init__` |
| 265 | `scripts/test_run_inventory.py:176:22` | `bad-argument-type` | A1 dataclass reconstruction from untyped dict | Unpacked keyword argument `list[str] \| Any` is not assignable to parameter `details` with type `str` in function `TestItem.__init__` |
| 266 | `scripts/test_run_inventory.py:258:21` | `no-matching-overload` | A14 local narrow fix / inspect individually | No matching overload found for function `collections.Counter.__init__` called with arguments: (object) |
| 267 | `scripts/test_run_inventory.py:259:25` | `no-matching-overload` | A14 local narrow fix / inspect individually | No matching overload found for function `collections.Counter.__init__` called with arguments: (object) |
| 268 | `scripts/update_readme_badges.py:103:27` | `bad-argument-type` | A3 numeric cast from object/None | Argument `Unknown \| None` is not assignable to parameter `x` with type `Buffer \| SupportsFloat \| SupportsIndex \| str` in function `float.__new__` |

---

## Remediation pass 1 — 2026-05-15

First manual cleanup pass intentionally targeted mechanical clusters with low behavioral risk before touching the P0 API-drift surface.

| Files | Finding class | Change | Pyrefly effect |
|---|---|---|---:|
| `lib/agent_daemon.py` | Dataclass reconstruction from untyped dict | Replaced `DetachedAgentTask(**{**task.to_dict(), ...})` with `dataclasses.replace(...)`. | Removed the repeated constructor argument cluster. |
| `scripts/test_run_inventory.py` | Dataclass reconstruction + untyped Counter payloads | Added explicit `TestItem` rebuild and renderer payload normalization helpers. | Removed the inventory constructor/count clusters. |
| `scripts/private_content_audit.py` | CLI rendering over unknown dict/list shapes | Added local payload map/list guards before rendering classification, summary, and findings. | Removed the private-content rendering cluster. |
| `scripts/cos_doc_path_audit.py` | Markdown/exit rendering over `dict[str, object]` payloads | Added local map/list guards and `get(...)` accessors. | Removed the doc-path rendering cluster. |
| `lib/delete_intent.py` | Immutable default typed as mutable set + env narrowing | Accepted `Collection[str]` for option sets and narrowed environment source to `Mapping[str, str]`. | Removed the delete-intent cluster. |

Validation:

```bash
uv run pytest \
  tests/unit/test_delete_intent.py \
  tests/unit/test_agent_daemon.py \
  tests/unit/test_test_run_inventory.py \
  tests/behavior/test_private_content_projection_guard.py \
  tests/unit/test_private_content_portability.py \
  tests/audit/test_doc_path_references.py -q
# 38 passed in 6.53s

COS_PYREFLY_PRINT_REPORT=0 bash scripts/cos-pyrefly-pilot --summary-only
# PYREFLY_PILOT_SUMMARY: errors=207 elapsed_seconds=1 ...
```

Baseline moved from **268 → 207** non-import Pyrefly errors after this pass. Remaining priority stays: inspect `lib/webhook_trigger.py` API drift before ratcheting the lane.

### Remediation pass 1b — agent bus narrowings

Additional local fixes:

| Files | Finding class | Change | Pyrefly effect |
|---|---|---|---:|
| `lib/agent_bus.py` | `json.loads(...)` over Valkey message data with unknown/optional shape | Narrowed `message.get("data")` to `str | bytes | bytearray` before parsing. | Removed two message parsing findings. |
| `lib/agent_bus_metrics.py` | Float conversion from optional heartbeat timestamp payload | Added `_as_float(...)` fallback helper before age calculation. | Removed one timestamp conversion finding. |

Validation:

```bash
uv run pytest \
  tests/unit/test_agent_bus.py \
  tests/integration/test_native_agent_heartbeat.py \
  tests/unit/test_delete_intent.py \
  tests/unit/test_agent_daemon.py \
  tests/unit/test_test_run_inventory.py \
  tests/behavior/test_private_content_projection_guard.py \
  tests/unit/test_private_content_portability.py \
  tests/audit/test_doc_path_references.py -q
# 120 passed in 12.70s

COS_PYREFLY_PRINT_REPORT=0 bash scripts/cos-pyrefly-pilot --summary-only
# PYREFLY_PILOT_SUMMARY: errors=205 elapsed_seconds=2 ...
```

Running baseline after pass 1b: **268 → 205** non-import Pyrefly errors.
