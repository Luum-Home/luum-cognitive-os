# Test Suite Repair Ledger — 2026-04-24

This ledger tracks full-suite repair decisions so future sessions do not lose the historical context behind each changed test or runtime fix.

## Policy

A passing test is not automatically trusted. Every test family touched during the repair pass must be classified against repository history:

- `active-contract`: the test protects current product behavior and failures should usually be fixed in runtime.
- `stale-contract`: the test protects behavior replaced by a later ADR, commit, or documented architecture decision.
- `optional-lane`: the test requires external services, credentials, packages, or platform capabilities not present in the default local lane.
- `false-positive-risk`: the test can pass while checking only structure, stale assumptions, or a weak proxy for real behavior.

## Current Evidence

- Latest full run: `102 failed, 10735 passed, 1283 skipped, 18 xfailed`.
- Previous comparison point during the same repair effort: `177 failed, 10625 passed, 1281 skipped, 18 xfailed`.
- Command: `python3 -m pytest tests/ -n auto -q --tb=short -ra --disable-warnings --timeout=120 --timeout-method=thread --session-timeout=2400 --durations=25`.
- Log: `.cognitive-os/reports/pytest-full-latest.log`.
- Focused repair lanes after canonical projection work:
  - orphan/registration subset: `46 passed`
  - native heartbeat integration: `4 passed`
  - usage-health + quick tracker subset: `2 passed`
  - metrics rotation: `5 passed`
  - cos-index: `13 passed`
  - agent-bus smart-infra subset: `6 passed`
  - orchestrator capabilities live: `9 passed`

## Decisions So Far

| Family | Historical evidence | Classification | Decision | Validation |
|---|---|---|---|---|
| Telemetry behavior tests | `8e943b7` migrated `lib/telemetry.py` to `MetricEvent` and promised consumers remain flat via unwrap. | stale-contract + runtime bug | Keep MetricEvent, update tests to unwrap, and make `_append()` return `None` if `append_event()` fails. | `tests/behavior/test_telemetry.py tests/unit/test_metric_event_migration.py`: 30 passed. |
| Efficiency profiles | `6c5d810` and ADR-002 collapsed legacy `lean/standard/minimal` into `default/full`; `cognitive-os.yaml` documents `default | full`. | stale-contract | Update tests from `lean/standard/full` to `default/full`; preserve legacy `lean` only as old-project compatibility. | `tests/unit/test_efficiency_stress.py tests/behavior/test_efficiency_profiles.py tests/integration/test_consolidation_external.py`: 58 passed. |
| Rules source vs patterns | `c0db698` moved declarative rules to `docs/patterns`; `bb5e962` made skills/rules canonical-first. | stale-contract | Tests may resolve compact/contextual references to either enforceable `rules/` or documented `docs/patterns/`. Do not recreate deliberately moved rules. | Included in prior audit target and efficiency/consolidation runs. |
| Data pipeline / feedback loops / self-repair JSONL reads | `8e943b7` migrated `consequence_engine`, `skill_archive`, `learning_pipeline`, and `record_completion` writers to `MetricEvent`. | stale-contract + false-positive-risk | Add shared `tests.utils.jsonl` reader that flattens MetricEvent rows and preserves consequence `record_type`. | `tests/integration/test_data_pipeline.py tests/integration/test_feedback_loops.py tests/integration/test_e2e_self_repair.py`: 74 passed. |
| Skill frontmatter with SCOPE tags | `5acb797` added `<!-- SCOPE: ... -->` before skill frontmatter; `95e182d` migrated skill frontmatter. | stale-contract | Tests must parse optional leading SCOPE comments before YAML frontmatter. | `tests/behavior/test_code_review_skill.py tests/behavior/test_semgrep_integration.py::TestSemgrepSkillFile tests/behavior/test_pentest_self.py::TestPentestSelfSkill`: 35 passed. |
| Subagent context injection | `931aaef` introduced mandatory sub-agent context; `6e2cf8b` added mandatory rules; current hook emits Claude modern `hookSpecificOutput.additionalContext`. | stale-contract + active bug | Tests read the current nested output shape; runtime now exits 0 for invalid JSON before jq-dependent parsing can trip `set -e`. | `tests/hooks/test_subagent_context_injector.py`: 14 passed. |
| Auto-update/cos-init settings driver fixtures | `e5fe9ad` introduced harness-aware settings projection; `7821f73` shared harness autodetection in init. Fake COS sources that copied scripts without `scripts/_lib/settings-driver.sh` no longer represented a runnable release tree. | stale-fixture + active-contract | Test fixtures must copy the settings-driver helper; `cos-update.sh` settings regeneration must not explode under isolated function tests when settings-driver globals are absent. | `tests/integration/test_auto_update_flow.py tests/integration/test_auto_update_safety.py tests/behavior/test_cos_update.py tests/unit/test_cos_update_regenerate_settings.py`: 56 passed. |
| Canonical projection behavior | ADR-057 and `docs/architecture/skills-rules-canonicalization-workplan.md` define `.cognitive-os/` as source-of-truth and `.claude/.codex` as driver projections. Structural tests could pass while `cos-init.sh` only wrote rules to `.claude/rules/cos`, duplicated skill content in the driver projection, and generated settings could reference hooks excluded by scope. | false-positive-risk + active bug | Add behavioral install contracts that verify full skill/rule projection to canonical storage, runtime discovery without `.claude/skills`, and Codex hook commands pointing at installed canonical hooks. Update `cos-init.sh` to dual-write rules, preserve `--full`, filter skills by audience, project Claude skills as flat symlinks, and clean canonical rule projection on auto-update. | `tests/contracts/test_canonical_projection_behavior.py tests/integration/test_project_settings_generation.py tests/integration/test_auto_update_safety.py::TestCosInitNamespacing::test_cos_init_installs_to_cos_namespace tests/integration/test_install_scope.py`: 35 passed. Auto-update regression lane: 56 passed. |
| Behavioral test doctrine | Current repair work found green tests that checked shape without proving runtime effect. | false-positive-risk | Add a reusable testing doctrine so future tests prove installation, projection, discovery, execution, metrics, or safety effects instead of relying on file-existence proxies alone. | `docs/architecture/behavioral-test-contracts.md` added; enforcement grows through contract tests. |
| Claude settings projection drift | `settings.json.bak-before-regen` proved the repository previously projected a wider Claude default hook surface. A later regeneration collapsed `scripts/apply-efficiency-profile.sh default`, dropping real hooks such as `docker-drift-detector.sh`, `session-startup-protocol.sh`, `session-heartbeat.sh`, `native-agent-heartbeat.sh`, `rate-limit-detector.sh`, `work-queue-sync.sh`, and stop/audit hooks. That created false orphan-hook failures plus multiple registration regressions. | active-contract + runtime bug | Restore the lost default projection from the historical baseline, keep the remaining truly opt-in ADR-056 quota hooks and compatibility heartbeat aliases explicitly whitelisted, and regenerate committed `.claude/settings.json` from the repaired script so the installer and repo baseline converge again. | `tests/contracts/test_orphan_hooks.py tests/unit/test_docker_drift_detector.py tests/unit/test_rate_limit_detector.py tests/unit/test_startup_protocol.py tests/unit/test_work_queue_sync.py tests/unit/test_surface_fix_detector.py`: 46 passed. `tests/integration/test_native_agent_heartbeat.py`: 4 passed. |
| Cost prediction discoverability | Routing/tests treated `cost-predict` as a public command alias, but the repository had no real skill implementation behind it. | false-positive-risk + active bug | Materialize the command as a real skill (`skills/cost-predictor/SKILL.md`) and a runnable CLI wrapper (`scripts/cost-predict.py`) backed by `lib.cost_predictor.py`, then re-register it in `skills/CATALOG.md`. | `tests/behavior/test_skill_auto_selection.py::TestSkillsExistOnFilesystem::test_every_routing_skill_is_known tests/unit/test_skill_router.py::TestRoutingTableIntegrity::test_all_routing_entries_have_existing_skills`: 2 passed. CLI smoke output validated locally. |
| Package integrity drift | `packages/cos-self-knowledge/` had runtime code but no top-level package documentation, so integrity tests correctly treated it as an undocumented stub. | active-contract | Add package README describing purpose, contents, and ADR reference so the package is both discoverable and auditable. | `tests/audit/test_integrity.py::test_every_package_has_readme_or_skill_md[cos-self-knowledge]`: 1 passed. |
| Usage health startup timeout | `hooks/usage-health-check.sh` called `ComponentUsageTracker.generate_usage_report()` from SessionStart. That code scans lib imports across the full repo and was taking long enough to trip multiple hook timeout tests. | active-contract + runtime bug | Keep the full report for explicit analysis, but add `generate_quick_health_report()` for startup use and switch the hook to the fast path. The hook now behaves like a real SessionStart advisory instead of a full dead-weight audit. | `tests/behavior/test_usage_health_check.py tests/hooks/test_hook_graceful_degradation.py -k usage-health-check`: 2 passed. Manual runtime check: ~25 ms. |
| cos-index generation drift | `packages/cos-index/index/packages.yaml` missed `@cos/advisory-llm`, and the generator's bash parser produced invalid YAML when `keywords:` used multiline bullets. | active-contract + runtime bug | Fix the generator to parse bullet-list keywords with portable whitespace handling, regenerate the index, and validate it from source instead of hand-editing only the output. | `packages/cos-index/scripts/generate-index.sh && validate-index.sh` passed; `tests/behavior/test_cos_index_and_global_init.py`: 13 passed. |
| Metrics rotation archive path | `hooks/metrics-rotation.sh` wrote archives to `metrics/archive/` while the active integration contract expected `.cognitive-os/metrics/.archive/`. Archive creation and retention cleanup therefore appeared broken to the tests. | active-contract + runtime bug | Align the hook to `.archive/` for the current contract and migrate legacy `archive/` gzip files into the active location so existing data is not stranded. | `tests/integration/test_metrics_rotation.py`: 5 passed. |
| Agent bus smart-infra tests vs ADR-042 | ADR-042 changed Valkey resolution order to `primary -> local daemon fallback -> smart_infra`, but the smart-infra unit tests still modeled “first failure goes straight to Docker start.” | stale-contract | Update the tests to fail both pre-smart-infra probes before asserting the `ensure_service('valkey')` path. Preserve the runtime's daemon-first behavior. | `tests/unit/test_agent_bus.py -k SmartInfraIntegration`: 6 passed. |
| Executor capability live check | `OrchestratorCapabilities._check_executor()` now accepts either `ORCHESTRATOR_MODE=executor` or a live executor daemon marker in `.cognitive-os/runtime/`, but the integration test still asserted env-var-only behavior. | stale-contract | Update the live integration test to reflect the current runtime contract: env var OR a live daemon state file with an alive PID. | `tests/integration/test_orchestrator_capabilities_live.py`: 9 passed. |

## Passes Still Needing Trust Review

Passing tests remain subject to audit when they guard master-plan claims. Priority areas:

- Structural-only tests that assert file existence, headings, or catalog mentions without executing behavior.
- Tests that inspect `.claude/settings.json` only and ignore Codex/canonical `.cognitive-os` projections.
- Tests that pass because they skip optional dependencies silently.
- Tests that assert historical counts instead of deriving contracts from source of truth.
- Tests that validate docs wording but not runtime capability.

## Skips/Xfails Policy

Skips and xfails are not automatically acceptable. Each must be moved to one of:

- default lane: install/provide the dependency and run it locally;
- optional lane: explicitly documented command/environment with reason;
- active bug: remove skip/xfail by implementing the missing behavior;
- stale test: update or delete after historical confirmation.
