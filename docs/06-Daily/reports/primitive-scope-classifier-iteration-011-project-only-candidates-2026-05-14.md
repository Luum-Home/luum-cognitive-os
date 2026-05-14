# Primitive Scope Classifier — Iteration 011: Project-only candidate review

Date: 2026-05-14

## Goal

Manually review the full `project-only-semantic-candidate` bucket from Iteration 010. The bucket had 11 rows, small enough to adjudicate one by one.

## Decisions

| Primitive | Decision | Reason |
|---|---|---|
| `scripts/cos-portable-ai-consumer-smoke` | `os-only` | Symlink/CLI surface for COS maintainer smoke of generated `.ai` overlay; validates packaging but is not projected as a project primitive. |
| `scripts/portable_ai_consumer_impact.py` | `os-only` | Generates ADR-258/COS consumer-impact reports from COS source; maintainer analysis. |
| `scripts/portable_ai_consumer_smoke.py` | `os-only` | Maintainer smoke for generated `.ai` overlay in disposable fixture. |
| `scripts/primitive_authority_audit.py` | `os-only` | Audits COS primitive authority manifests and generated reports. |
| `scripts/primitive_harness_partials.py` | `os-only` | Reports unresolved COS harness/projection coverage partials. |
| `skills/domain-model/SKILL.md` | `project` | Scaffolds DDD docs inside adopting projects. |
| `skills/ops-runbook/SKILL.md` | `project` | Scaffolds operations/admin/monitoring runbooks inside adopting projects. |
| `skills/risk-register/SKILL.md` | `project` | Scaffolds STRIDE risk register docs inside adopting projects. |
| `skills/rules-export/SKILL.md` | `project` | Exports SO rules snapshots into adopting project documentation; affects project docs, not SO construction. |
| `skills/primitive-authoring/SKILL.md` | `both` | Governs primitive creation in both COS source and consumer-project overlays. |
| `skills/session-backlog/SKILL.md` | `both` | Contains explicit COS-source and consumer-project execution paths. |

## Result

The `project-only-semantic-candidate` bucket is now empty.

```json
{
  "by_suggested_scope": {
    "both": 73,
    "os-only": 534,
    "project": 90,
    "unknown": 491
  },
  "unknown_delta": -11,
  "project_only_candidate_bucket": 0
}
```

## Notes

This iteration confirmed the user's distinction: `project` is not "generic useful". It is reserved for primitives that act on adopting projects and are not required for COS construction. Several rows with the word "consumer" were actually `os-only` because they are COS maintainer audits/proofs of projection, not project-local primitives.

## Next iteration

Recommended next target: `both-semantic-candidate` rows. Those are mostly repo-agnostic rules that are likely true `both`, but they still need lifecycle/consumer metadata before the classifier can stop treating them as unknown.
