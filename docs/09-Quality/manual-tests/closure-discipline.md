# Closure Discipline Manual Test

Purpose: prove an agent batch did not only pass feature-local tests; it also
closed the validation surfaces it invalidated.

## When to run

Run this manually before calling a multi-file maintainer batch “done” when it
touches any of these surfaces:

- `.github/workflows/` or ADR-130/131 local-CI migration files;
- hook projection, `.claude/settings.json`, `.codex/hooks.json`, or
  `manifests/primitive-lifecycle.yaml`;
- validation capsule, worktree cleanup, WIP inventory, or broad validation lanes;
- tests that assert repository-wide counts, generated artifacts, or preserved
  disabled files;
- ADRs that claim a new gate, lifecycle state, or validation contract.

## Procedure

1. Confirm the structural closure audit is green:

   ```bash
   scripts/cos-closure-discipline-audit --fail-on-findings --json
   ```

2. Re-run the targeted regression set for the known closure-drift classes:

   ```bash
   python3 -m pytest \
     tests/unit/test_closure_discipline_audit.py \
     tests/unit/test_test_lanes_workflow.py \
     tests/unit/test_primitive_gap_workflow.py \
     tests/unit/test_primitive_coverage.py \
     tests/unit/test_cos_work_inventory.py::TestCollectWorktreesDirect \
     tests/unit/test_runtime_hook_reality.py::test_repository_settings_hook_count_is_report_derived_not_hardcoded \
     tests/unit/test_validation_capsule.py::test_validation_capsule_runs_in_isolated_worktree \
     -q
   ```

3. Verify lifecycle metadata has no structural findings:

   ```bash
   python3 scripts/primitive_lifecycle.py --json
   ```

   The JSON must contain `"valid": true` and `"finding_count": 0`.

4. Run maintainer quick CI:

   ```bash
   bash scripts/cos-ci-local.sh quick
   ```

5. For uncommitted WIP closure, run the broad direct lane after the quick gate:

   ```bash
   make test-laptop-direct
   ```

6. After committing, run the isolated capsule lane for release-safe closure:

   ```bash
   make test-laptop
   ```

   The capsule validates `HEAD`, not uncommitted edits. If either broad lane fails, do not claim release-safe closure. Triage whether the failure
   is a product bug, a stale test, or a validator drift; record the category.

## Pass criteria

- The closure audit exits 0 with `status: pass`.
- Targeted closure regression tests pass.
- Primitive lifecycle JSON reports zero findings.
- Quick CI includes and passes the closure discipline audit step.
- Any skipped broad/release lane is explicitly named as skipped, with reason and
  risk, in the final trust report.

## Failure handling

Do not revert the feature batch by reflex. First classify:

| Failure type | Action |
|---|---|
| Stale validator/test | Update the validator/test and add a closure-audit fixture if the class can recur. |
| Real product regression | Fix the product behavior and add/repair the feature test. |
| Ambiguous | Leave the batch unclosed; write an escalation with the failing command and evidence. |

A closure claim without this evidence is a partial-completion claim, not a done
claim.
