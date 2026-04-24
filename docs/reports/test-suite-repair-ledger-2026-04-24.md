# Test Suite Repair Ledger — 2026-04-24

This ledger tracks full-suite repair decisions so future sessions do not lose the historical context behind each changed test or runtime fix.

## Policy

A passing test is not automatically trusted. Every test family touched during the repair pass must be classified against repository history:

- `active-contract`: the test protects current product behavior and failures should usually be fixed in runtime.
- `stale-contract`: the test protects behavior replaced by a later ADR, commit, or documented architecture decision.
- `optional-lane`: the test requires external services, credentials, packages, or platform capabilities not present in the default local lane.
- `false-positive-risk`: the test can pass while checking only structure, stale assumptions, or a weak proxy for real behavior.

## Current Evidence

- Latest full run: `177 failed, 10625 passed, 1281 skipped, 18 xfailed`.
- Command: `python3 -m pytest tests/ -n auto -q --tb=short -ra --disable-warnings --timeout=120 --timeout-method=thread --session-timeout=2400 --durations=50`.
- Log: `.cognitive-os/reports/pytest-full-latest.log`.

## Decisions So Far

| Family | Historical evidence | Classification | Decision | Validation |
|---|---|---|---|---|
| Telemetry behavior tests | `8e943b7` migrated `lib/telemetry.py` to `MetricEvent` and promised consumers remain flat via unwrap. | stale-contract + runtime bug | Keep MetricEvent, update tests to unwrap, and make `_append()` return `None` if `append_event()` fails. | `tests/behavior/test_telemetry.py tests/unit/test_metric_event_migration.py`: 30 passed. |
| Efficiency profiles | `6c5d810` and ADR-002 collapsed legacy `lean/standard/minimal` into `default/full`; `cognitive-os.yaml` documents `default | full`. | stale-contract | Update tests from `lean/standard/full` to `default/full`; preserve legacy `lean` only as old-project compatibility. | `tests/unit/test_efficiency_stress.py tests/behavior/test_efficiency_profiles.py tests/integration/test_consolidation_external.py`: 58 passed. |
| Rules source vs patterns | `c0db698` moved declarative rules to `docs/patterns`; `bb5e962` made skills/rules canonical-first. | stale-contract | Tests may resolve compact/contextual references to either enforceable `rules/` or documented `docs/patterns/`. Do not recreate deliberately moved rules. | Included in prior audit target and efficiency/consolidation runs. |
| Data pipeline / feedback loops / self-repair JSONL reads | `8e943b7` migrated `consequence_engine`, `skill_archive`, `learning_pipeline`, and `record_completion` writers to `MetricEvent`. | stale-contract + false-positive-risk | Add shared `tests.utils.jsonl` reader that flattens MetricEvent rows and preserves consequence `record_type`. | `tests/integration/test_data_pipeline.py tests/integration/test_feedback_loops.py tests/integration/test_e2e_self_repair.py`: 74 passed. |
| Skill frontmatter with SCOPE tags | `5acb797` added `<!-- SCOPE: ... -->` before skill frontmatter; `95e182d` migrated skill frontmatter. | stale-contract | Tests must parse optional leading SCOPE comments before YAML frontmatter. | Pending. |

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
