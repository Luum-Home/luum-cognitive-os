# Verification — `cos_demotion_loop_audit` Bite at Budget Expiry (2026-05-03)

**Date:** 2026-05-03
**Scope:** [`scripts/cos_demotion_loop_audit.py`](../../scripts/cos_demotion_loop_audit.py)
**Property under test:** the `roi-signed-demotion-missing` finding escalates from `severity: warn` / `status: warn` to `severity: fail` / `status: fail` when the warning budget (`ROI_WARNING_BUDGET_DAYS = 30`) expires without an ROI-signed demotion.
**Companion:** [`external-review-cycle-2026-05-02.md`](../case-studies/external-review-cycle-2026-05-02.md), §"Maturity position at end of cycle".

## Why this exists

The case study commits the system to a falsifiable trigger: *"`cos_demotion_loop_audit` reports `status: pass` with `roi_signed_demotion_count >= 1`"* invalidates the post-adolescent characterisation. That trigger only has teeth if the audit actually escalates from `warn` to `fail` at the documented deadline. A warn that lives forever is decorative. A warn with a deadline is a deadline only if the deadline mechanically bites.

This document is the bilateral-pressure replay of that claim: the reviewer must verify the bite, not assume it; the maintainer must wire the bite, not promise it.

## Method

The audit accepts a `--today YYYY-MM-DD` argument so the escalation can be exercised without waiting wall-clock. Two invocations were compared:

```bash
# baseline: today
python3 scripts/cos_demotion_loop_audit.py --json
# simulated: 33 days past the second demotion (2026-05-03 + 33 = 2026-06-05)
python3 scripts/cos_demotion_loop_audit.py --today 2026-06-05 --json
```

Both invocations operate on the same lifecycle manifest. Only the date input changes. Any difference in `severity` or `status` is therefore attributable to the budget-expiry logic, not to manifest mutation.

## Result

### Baseline (today = 2026-05-03)

```json
{
  "status": "warn",
  "demotion_count": 2,
  "roi_signed_demotion_count": 0,
  "roi_warning_budget_days": 30,
  "roi_warning_open_since": "2026-05-03",
  "roi_warning_age_days": 0,
  "findings": [
    {
      "id": "roi-signed-demotion-missing",
      "severity": "warn",
      "message": "No demotion records governance ROI as the primary signing signal; ROI dashboard remains an instrument, not a decision knife."
    }
  ]
}
```

### Simulated past expiry (today = 2026-06-05)

```json
{
  "status": "fail",
  "findings": [
    {
      "id": "roi-signed-demotion-missing",
      "severity": "fail",
      "message": "No demotion records governance ROI as the primary signing signal; ROI dashboard remains an instrument, not a decision knife. The warning budget expired after 33 days without ROI-signed demotion."
    }
  ]
}
```

Three transitions confirmed in the same call:

1. **`severity: warn` → `severity: fail`** at the finding level.
2. **`status: warn` → `status: fail`** at the report level.
3. **Message extended** with the explicit expiry sentence so the reason is self-evident in any log or CI panel that captures the finding.

### CI integration

The audit is invoked from [`scripts/cos-ci-local.sh`](../../scripts/cos-ci-local.sh) and the `quick` lane uses `--fail-on-findings`. With that flag set, the day-31 invocation returns non-zero exit, which fails the quick CI gate. The escalation is therefore not advisory: it blocks the build by default once the budget elapses.

## What this verifies

- The warn budget is a real deadline, not a comment in code.
- The escalation is mechanical and date-driven, not human-attention-driven.
- The audit's finding flips both `severity` and `status` in the same call, so any consumer that reads either field sees the same conclusion.
- The CI binding closes the loop: the deadline propagates to the build, not just to the JSON.

## What this does not verify

- That the deadline will not be silently extended. Increasing `ROI_WARNING_BUDGET_DAYS` from 30 to a larger number, without a corresponding ROI-signed demote, would defuse the bite without recording the decision. That mutation must remain visible: any commit that touches the constant should be treated as a doctrinal regression and either reverted or accompanied by an ADR explaining the new budget. The defence against this trap is not in code; it is in the review of any commit that touches the constant.
- That an ROI-signed demote will appear by 2026-06-02. The audit guarantees the consequence of inaction; it does not guarantee the action.
- That the ROI dashboard's heuristics (`MINUTES_PER_BLOCKED_INCIDENT = 5.0`, etc.) are correctly calibrated. The first ROI-signed demote will exercise the dashboard's signing path; the calibration of its inputs is a separate audit.

## How to replay

Future reviewers should re-run the verification themselves rather than trust this report:

```bash
# At any time, confirm the audit still escalates correctly:
python3 scripts/cos_demotion_loop_audit.py --today 2026-06-05 --json | jq '.status, .findings[].severity'

# To verify the budget constant has not been silently extended:
git log -L :ROI_WARNING_BUDGET_DAYS:scripts/cos_demotion_loop_audit.py
```

The first command should print `"fail"` followed by `"fail"` until and unless an ROI-signed demote is recorded. The second command should show one assignment (`30`) and no further changes; any change without an accompanying ADR is a regression worth questioning.

## What this means for the open trigger

The open trigger from the maturity-position snapshot — *"`cos_demotion_loop_audit` reports `status: pass` with `roi_signed_demotion_count >= 1`"* — now has two legitimate resolution paths and one trap:

| Path | Description | Outcome |
|---|---|---|
| Resolution by action | An ROI-signed demote lands before 2026-06-02. | `status: pass`, trigger condition met, post-adolescent characterisation revisable. |
| Resolution by escalation | No ROI-signed demote by 2026-06-02. | `status: fail`, CI breaks, intervention forced. The intervention can produce the demote, defer with explicit ADR, or remove the trigger — all three become evidence. |
| Trap | `ROI_WARNING_BUDGET_DAYS` is increased without an ROI-signed demote. | Bite defused silently. This is the failure mode the doctrine cannot mechanically prevent. |

The first two are honest; the third is the one to watch.

## Reproducibility note

This verification was performed by replaying the audit with a future date input and observing the output diff. No production state was mutated. The verification can be re-run any number of times without side effects, which is the expected property of a read-only audit primitive. If a future change to the audit makes it stateful, this report becomes stale and a new verification is required.
