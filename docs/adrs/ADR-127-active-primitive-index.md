# ADR-127: Active Primitive Index

## Status

Accepted for Phase 1 DX.

## Context

External review found that Cognitive OS exposes too much governance surface at once. The project already has `manifests/primitive-lifecycle.yaml`, which records each agentic primitive's lifecycle state and distribution tier. Phase 1 DX needs a smaller, operator-readable active index without creating a second source of truth.

Product-facing output must stay vendor-neutral. Readiness entrypoints use architecture/readiness naming; model-branded compatibility wrappers are not kept.

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

The architecture readiness report now includes an `active-primitive-surface` check with counts by tier, active counts, default-visible counts, thresholds, and findings.

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
- Vendor-neutral naming: the canonical readiness module is `cos_architecture_readiness.py`; there are no model-named compatibility wrappers.

## Consequences

The active index becomes the small DX surface for operators while preserving the richer lifecycle manifest for maintainers. The thresholds are intentionally conservative guardrails, not product claims; they can be adjusted after usage data shows a better friction budget.


### 2026-05-03 Runtime Coverage Hardening

The index now compares `manifests/primitive-lifecycle.yaml` against the active
Claude hook projection in `.claude/settings.json`. A readiness report can no
longer pass while runtime-projected hooks are absent from lifecycle metadata.

Current hardened baseline:

- Runtime-projected unique hooks: 116
- Lifecycle-covered projected hooks: 116
- Missing projected hooks: 0
- Runtime coverage ratio: 1.0

Active-surface thresholds still warn because this maintainer repository projects
a large runtime surface, but that warning is now about real represented surface,
not undercounted metadata. The companion runtime reality audit reports the
current behavior split as 29 real blocking hooks, 59 real advisory hooks, and 28
observe-only hooks, with zero projected/documentation drift.


## Alternatives rejected

- **Create a second active-surface manifest**: rejected because it would create
  another source of truth and drift from ADR-126 lifecycle metadata.
- **Count only current runtime projection**: rejected for the initial slice
  because projection is harness-specific and would not preserve lifecycle state,
  distribution, governance class, or promotion/demotion evidence. The accepted
  path is lifecycle-first plus explicit runtime-coverage reporting.
- **Keep model-branded readiness aliases for compatibility**: rejected because
  product-facing entrypoints must be vendor/model-neutral and the user explicitly
  asked not to keep legacy model-named wrappers.


## Verification

Initial implementation and naming checks:

```bash
python3 -m pytest tests/unit/test_active_primitive_index.py tests/unit/test_cos_architecture_readiness.py -q
python3 -m py_compile scripts/active_primitive_index.py scripts/cos_architecture_readiness.py
bash -n scripts/cos-active-primitive-index scripts/cos-architecture-readiness scripts/cos
scripts/cos-active-primitive-index --tier core --json | python3 -m json.tool >/dev/null
scripts/cos-architecture-readiness --json | python3 -m json.tool >/dev/null
```

Runtime hardening verification:

```bash
python3 -m pytest tests/contracts/test_primitive_runtime_reality.py tests/unit/test_active_primitive_index.py tests/unit/test_runtime_hook_reality.py -q
python3 scripts/active_primitive_index.py --json
python3 scripts/runtime_hook_reality.py --fail-on-findings
```
