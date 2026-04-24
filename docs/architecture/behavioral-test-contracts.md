# Behavioral Test Contracts

Cognitive OS tests must prove product behavior, not only repository shape.

Structural assertions are allowed as hygiene checks, but they are not enough to
support product claims such as portability, governance, verification, or
canonical-first runtime behavior.

## Rule

If a test supports a product or architecture claim, it must exercise at least
one observable effect:

- install an artifact into a throwaway project;
- project canonical state into a harness driver;
- execute a hook or script against realistic input;
- load runtime state through the same resolver used by production code;
- write and read a metric, trace, or state file through the canonical schema;
- prove a safety guard blocks or preserves something under a real filesystem
  scenario.

## False-Positive Risk

Mark or upgrade tests when they only verify:

- a file exists;
- `SKILL.md` exists without proving discovery;
- a heading or catalog entry exists without proving runtime lookup;
- `.claude/settings.json` wiring while ignoring the active settings driver;
- historical counts that are not derived from a source of truth;
- docs wording without a command, contract, or proof path.

These tests should not be deleted automatically. Convert them into behavioral
contracts or keep them as hygiene checks paired with behavioral coverage.

## Canonical-First Pattern

For skills and rules, prefer this test shape:

1. Install Cognitive OS into a temporary project.
2. Assert canonical artifacts exist under `.cognitive-os/.../cos`.
3. Assert driver projections exist only where that harness requires them.
4. Remove or ignore the driver projection.
5. Verify runtime discovery still succeeds through canonical resolvers.

For hooks and settings drivers, prefer this test shape:

1. Generate or install the active harness settings driver.
2. Extract every registered hook command.
3. Assert each command points at an installed executable hook.
4. Assert the command uses the correct harness project expression.
5. Assert no command points at source-repo-only paths.

## Historical Discipline

Before changing a failing test, classify it against repository history:

- `active-contract`: fix runtime or fixture behavior;
- `stale-contract`: update the test only after finding the ADR or commit that
  replaced the behavior;
- `optional-lane`: document the dependency and command;
- `false-positive-risk`: strengthen it so it can fail for real regressions.

Do not delete or relax tests just to make the suite green.

## Current Enforcing Examples

- `tests/contracts/test_canonical_projection_behavior.py`
- `tests/integration/test_project_settings_generation.py`
- `tests/integration/test_auto_update_safety.py`
- `docs/reports/test-suite-repair-ledger-2026-04-24.md`
