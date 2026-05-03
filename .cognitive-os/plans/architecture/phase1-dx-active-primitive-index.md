# Phase 1 DX Active Primitive Index

## Goal

Reduce Cognitive OS governance discovery load by exposing a filtered active agentic primitive index and surfacing active/default counts in readiness.

## Acceptance Criteria

1. Active index source of truth is `manifests/primitive-lifecycle.yaml`.
2. CLI emits JSON by default and supports optional human summary.
3. CLI filters by `core`, `team`, `maintainer`, and `lab`.
4. Invalid tiers are rejected.
5. Governance readiness includes active-surface counts and warning/fail thresholds.
6. Lab primitives remain discoverable without being required active/default surface.

## Implementation Notes

- `scripts/active_primitive_index.py` adapts lifecycle `distribution` into adoption tier.
- `scripts/cos-active-primitive-index` is a stable shell entrypoint.
- `scripts/cos_opus_readiness.py` keeps compatibility but prints vendor-neutral governance readiness wording.
- Thresholds are local constants in the index script until real DX telemetry justifies config-driven values.

## Validation

Run:

```bash
python3 -m pytest tests/unit/test_active_primitive_index.py tests/unit/test_cos_opus_readiness.py -q
python3 -m py_compile scripts/active_primitive_index.py scripts/cos_opus_readiness.py
bash -n scripts/cos-active-primitive-index
```

## Remaining Follow-up

Future phases can wire the index into generated docs, install profiles, or auto-adjusted primitive promotion flows. Those flows must continue to mutate the lifecycle manifest rather than creating another registry.
