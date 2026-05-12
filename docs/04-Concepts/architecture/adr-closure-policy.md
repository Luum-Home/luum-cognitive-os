# ADR Closure Policy

ADR closure is not a permission to implement old decisions blindly. It is a
triage contract for deciding whether an ADR still represents current runtime
work, historical evidence debt, or deliberately deferred scope.

## Closure classes

| Closure class | Runtime action | Meaning |
|---|---|---|
| `implement-current` | Implement now. | The ADR still describes desired current behavior and lacks implementation. It must remain visible in the implementation ledger until code/config/tests/docs land. |
| `deferred` | Do not implement now. | The ADR remains valid, but only re-enters implementation after its explicit trigger fires. Example: ADR-132 Shape B / federation / multi-maintainer work. |
| `evidence-only` | Do not implement runtime. | Runtime already exists or the ADR is historically satisfied. Fix stale status, evidence, docs, ledger parsing, or tests instead. |
| `absorbed` | Do not implement the old shape. | The useful intent is covered by later ADRs or current primitives. Re-implementing the original ADR risks duplication or regression. |
| `superseded` | Do not implement. | A later ADR explicitly replaces this ADR. Follow the successor if current work is still needed. |
| `obsolete-by-context` | Do not implement. | The ADR solved a historical context that no longer applies to the current phase or architecture. Preserve rationale only. |

## Operational rule

Only `implement-current` is current implementation backlog.

All other closure classes are non-runtime actions unless a later audit finds
concrete drift. If drift is found, create or reference a current ADR/task rather
than reviving the old ADR's original implementation shape.

## Evidence boundary

The ADR implementation ledger consumes
`manifests/adr-closure-metadata.yaml`. That manifest is the source of truth for
historical reconciliation. Chat discussion, stale ADR prose, or broad words like
"pending" in old documents are not enough to create implementation work after a
closure class is assigned.

## Current historical closure result

The 2026-05-04 reconciliation found no `implement-current` items for the ADR≤138
historical closure pass. Therefore those ADRs should not be attacked as runtime
work from history alone.

Future ADRs can still create implementation work. They must do so through their
own current acceptance criteria, tests, and readiness findings.

## Verification

```bash
python3 -m pytest tests/unit/test_adr_implementation_ledger.py -q
python3 scripts/adr_implementation_ledger.py --json
```
