# Claim Boundary Resolution — 2026-05-04

## Purpose

Resolve the remaining claim/readiness items without manufacturing evidence.

## Results

| Item | Resolution | Evidence |
|---|---|---|
| Self-building claim | Signed for the narrow claim "self-instrumenting under operator approval". | `scripts/cos_primitive_harvester.py` produced `docs/06-Daily/reports/primitive-harvester-promotion-evidence-2026-05-04.json`; `scripts/cos_primitive_harvester` moved from `sandbox` to `advisory` with `promotion_evidence.primary_signal=primitive-harvester` and `approved_by=operator`. |
| Helps-projects claim | Not signed; converted to external-evidence boundary. | `manifests/external-adoption-evidence.yaml` requires a non-maintainer 30-day `core` report. Self-owned drills and same-machine consumer repos must not sign this claim. |
| ADR-132 / Shape B | Deferred by trigger, not by memory. | `scripts/cos-federation-trigger-audit` reports Shape A deferred until real Shape-B triggers fire. |
| ADR ≤138 closure | Classified, not blindly implemented. | `docs/01-Build-Log/root/SESSION-ADR-CLOSURE-2026-05-04.md` assigns all 50 attention ADRs to evidence-only, absorbed, superseded, obsolete-by-context, or deferred; `implement-current=0`. |
| Maximum certainty | Broad validation running separately; quick/targeted gates are green. | `bash scripts/cos-ci-local.sh quick`, claim audit, readiness, boring reliability, and targeted tests. |

## Evidence commands

```bash
python3 scripts/cos_claim_signature_audit.py --json
scripts/cos-federation-trigger-audit
python3 scripts/cos_architecture_readiness.py --json
scripts/cos-boring-reliability --profile core --json
bash scripts/cos-ci-local.sh quick
```

## Boundary

The SO can now say:

- It improves and promotes its own primitives under operator approval.
- It has the pipeline to collect external project evidence.
- It does **not** yet have real non-maintainer adoption evidence.
- It does **not** build distributed federation until Shape-B triggers become true.

That boundary is deliberate. Removing the unsigned `helps-projects` boundary without real external evidence would be marketing, not governance.
