# ADR-127: Active Primitive Index

## Status

Accepted for Phase 1 DX.

## Context

External review found that Cognitive OS exposes too much governance surface at once. The project already has `manifests/primitive-lifecycle.yaml`, which records each agentic primitive's lifecycle state and distribution tier. Phase 1 DX needs a smaller, operator-readable active index without creating a second source of truth.

Product-facing output must stay vendor-neutral. Legacy readiness entrypoints can remain for compatibility, but new reports should describe governance readiness and active surface area without model-branded labels.

## Decision

Add `scripts/active_primitive_index.py` and the `scripts/cos-active-primitive-index` wrapper. The index derives from `manifests/primitive-lifecycle.yaml` and treats the manifest `distribution` field as the adoption tier:

- `core`
- `team`
- `maintainer`
- `lab`

The CLI emits JSON by default and supports `--human` for a compact summary. `--tier` filters returned primitives by one adoption tier.

Active surface semantics:

- `core`, `team`, and `maintainer` primitives are active unless their lifecycle state is `demoted`, `archived`, or `deleted`.
- `core` and `team` primitives are default-visible.
- `lab` primitives remain indexed but do not count as active or default-visible adoption surface.

The governance readiness report now includes an `active-primitive-surface` check with counts by tier, active counts, default-visible counts, thresholds, and findings.

## Acceptance Criteria

1. `scripts/cos-active-primitive-index --tier core` returns only core primitives.
2. Unknown tiers are rejected before producing an index.
3. Reports include counts for all four tiers: `core`, `team`, `maintainer`, and `lab`.
4. Readiness output includes the active surface check.
5. Lab/sandbox primitives do not have to become active for readiness to pass.
6. Narrow unit tests and Python syntax checks pass.

## Border Cases

- Unknown tier in CLI input: reject through argparse choices.
- Unknown tier in the manifest: fail index construction so drift is visible.
- Missing manifest: return a readiness failure instead of silently reporting an empty surface.
- Future auto-adjusted primitives: keep deriving from the lifecycle manifest; generators must update that manifest rather than bypassing this adapter.
- Vendor-neutral naming: legacy `cos_opus_readiness.py` remains callable, but human-facing report copy uses governance readiness wording.

## Consequences

The active index becomes the small DX surface for operators while preserving the richer lifecycle manifest for maintainers. The thresholds are intentionally conservative guardrails, not product claims; they can be adjusted after usage data shows a better friction budget.
