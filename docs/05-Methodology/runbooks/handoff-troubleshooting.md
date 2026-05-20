# Handoff Troubleshooting Runbook

Use this runbook for ADR-230 handoff envelopes, receiver routing, and cycle deduplication.

## Validate the envelope

- Check `manifests/handoff-protocol.yaml` for required fields.
- Confirm the sender emitted a stable handoff id and call-chain id.
- Verify `lib/handoff_envelope.py` accepts the envelope before dispatch.

## Diagnose receiver failures

1. Inspect `lib/handoff_dispatcher.py` output and receiver status.
2. Confirm the receiver is declared idempotent before replaying mutating work.
3. Check cycle detection when the same call-chain id reappears.
4. If the receiver died mid-dispatch, preserve the envelope and retry only through the dispatcher.

## Recovery

- For read-only query handoffs, retry after receiver restart.
- For mutating handoffs, require idempotency evidence or human approval.
- Record the recovery action in the session handoff log.
