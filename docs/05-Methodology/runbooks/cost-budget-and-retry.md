# Cost Budget and Retry Runbook

ADR-228 requires retry behavior and cost limits to be operator-visible before service-mode or long-running dispatch.

## Before dispatch

- Review `manifests/retry-contract.yaml` and `manifests/session-budget.yaml`.
- Estimate cost with `lib/dispatch_cost_predictor.py` through the dispatch gate path.
- Refuse service-mode execution when no per-session and per-task budget cap is configured.

## During dispatch

- Treat retryable infrastructure errors separately from deterministic task failures.
- Require idempotency keys for actions that mutate external state.
- Stop retrying when the session or task budget cap would be exceeded.

## After dispatch

- Persist retry classification and budget outcome in the dispatch receipt.
- Escalate repeated deterministic failures instead of spending retries.
- Update the manifests only through reviewed commits.
