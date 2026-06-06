# Task Closure Ledger Gate

`cos-task-closure-gate` is a project-local honesty gate for large work fronts that cannot be collapsed into a single “done” claim.

Use it when a project has several fronts that may be partially proved, deferred, or ready for the next implementation slice. The ledger is project-owned; Cognitive OS owns only the reusable schema and validator.

## Contract

A ledger uses:

```json
{
  "schemaVersion": 1,
  "contract": "cos.task-closure-ledger.v1",
  "fronts": []
}
```

Each front must include:

- `id`
- `title`
- `status`
- `canClaimComplete`
- `closureGate`
- `doneEvidence`
- `remaining`
- `nextPrimitive`

`canClaimComplete=true` is valid only with `status=closed`. `status=closed` is valid only with `canClaimComplete=true`.

## Commands

```bash
.cognitive-os/bin/cos-task-closure-gate docs/closure.json
.cognitive-os/bin/cos-task-closure-gate docs/closure.json --json
.cognitive-os/bin/cos-task-closure-gate docs/closure.json --require-closed
.cognitive-os/bin/cos-task-closure-gate docs/closure.json --require-gates-passed
.cognitive-os/bin/cos-task-closure-gate docs/closure.json --run-closure-gates
```

## Migration from project-specific ledgers

Keep the project-specific front names and gates, but change only the top-level contract to `cos.task-closure-ledger.v1` and keep the canonical `fronts[]` field. Do not move domain-specific front ids or evidence into the SO.

If a front remains open, keep `canClaimComplete=false` and list concrete `remaining` plus `nextPrimitive`. Agents must report those remaining items instead of claiming global completion.
