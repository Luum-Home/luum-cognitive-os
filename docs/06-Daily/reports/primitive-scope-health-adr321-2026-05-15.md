# ADR-321 Primitive Scope Health Implementation — 2026-05-15

## Goal

Implement plane/balance/proof-level controls for primitive scope classification so raw `os-only`/`project`/`both` counts are not interpreted without evidence and plane context.

## Implemented surfaces

- `scripts/primitive-scope-balance-audit`
- `scripts/primitive-scope-plane-audit`
- `scripts/primitive-scope-generic-os-only-audit`
- `scripts/primitive-scope-false-both-audit`
- `scripts/primitive-scope-health`

## Baseline health summary

```json
{
  "by_kind": {
    "hooks": 278,
    "rules": 122,
    "scripts": 584,
    "skills": 181,
    "templates": 52
  },
  "by_plane": {
    "control-plane": 543,
    "factory-plane": 80,
    "runtime-plane": 278,
    "user-plane": 316
  },
  "by_proof_level": {
    "family": 110,
    "none": 498,
    "primitive-specific": 609
  },
  "by_scope": {
    "both": 531,
    "os-only": 631,
    "project": 55
  },
  "findings": 14,
  "findings_by_code": {
    "both-needs-specific-proof": 7,
    "os-only-generic-candidate": 6,
    "scope-ratio-project-low": 1
  },
  "total": 1217
}
```

## CI policy

- Scope classifier remains strict for contradictions, low confidence, and medium confidence.
- Plane audit runs strict because every primitive must derive a valid plane.
- Balance, generic-os-only, false-both, and combined health run in warning/report mode first.

## Current review queues

- `scope-ratio-project-low`: review threshold signal for project skills ratio.
- `os-only-generic-candidate`: possible over-internalization candidates.
- `both-needs-specific-proof`: possible false-both candidates, currently driven by source-checkout path signals.
