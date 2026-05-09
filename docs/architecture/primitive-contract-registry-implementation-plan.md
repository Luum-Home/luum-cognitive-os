# Primitive Contract Registry Implementation Plan

**Date:** 2026-05-09  
**Status:** Plan-first; do not implement broad runtime changes until ADR-256 is accepted  
**ADR:** `docs/adrs/ADR-256-primitive-contract-registry-and-runtime-evidence-ledger.md`

## Purpose

Resolve primitive portability and observability at the root:

```text
canonical primitive contract
  -> harness projection fidelity
  -> consumer-fleet impact
  -> service/headless impact
  -> runtime primitive intervention
  -> codebase itinerary
  -> joined run trace
```

## Existing assets to reuse

- `manifests/harness-projection.yaml`
- `manifests/harness-driver-capabilities.yaml`
- `manifests/primitive-projection-profiles.yaml`
- `scripts/primitive_harness_coverage.py`
- `scripts/cos-consumer-fleet-audit` / `lib/consumer_fleet_audit.py`
- `scripts/cos-service-readiness-gate` / `lib/service_mode_readiness.py`
- `docs/architecture/cos-service-runtime-boundary.md`
- `lib/trace_joiner.py`
- `skills/primitive-authoring/SKILL.md`

## Phase 1 — Minimal registry

Create `manifests/primitive-contracts.yaml` with five initial contracts:

1. `destructive-git-blocker`
2. `destructive-rm-blocker`
3. `reinvention-check`
4. `large-file-advisor`
5. `skill-router`

Test:

```bash
python3 -m pytest tests/contracts/test_primitive_contract_registry.py -q
```

## Phase 2 — Intervention ledger

Create `.cognitive-os/metrics/primitive-interventions.jsonl` writer/helper and
bridge destructive git/rm first.

Test:

```bash
python3 -m pytest tests/contracts/test_primitive_intervention_ledger.py -q
```

## Phase 3 — Codebase itinerary

Record safe Read/Grep/Glob/LS metadata without contents.

Test:

```bash
python3 -m pytest tests/contracts/test_codebase_itinerary.py -q
```

## Phase 4 — Projection and impact report

Generate `docs/reports/primitive-projection-fidelity-latest.{json,md}` by joining:

- primitive contracts;
- harness projection/capability manifests;
- `scripts/cos-consumer-fleet-audit --json` when install/update/projection may impact consumers;
- `scripts/cos-service-readiness-gate --json` when service/headless/cosd claims may be affected.

Test:

```bash
python3 -m pytest tests/contracts/test_primitive_projection_fidelity.py -q
```

## Phase 5 — Trace joiner integration

Extend run trace to answer:

```text
What did the agent inspect?
Which primitives intervened?
Which consumer projects are impacted or stale?
Does this work outside IDEs in shell/CI, headless worker, or cosd mode?
```

Test:

```bash
python3 -m pytest tests/unit/test_trace_joiner.py tests/contracts/test_observable_primitive_self_use.py -q
```

## Stop conditions

Pause if:

- itinerary redaction cannot be proven safe;
- consumer-fleet audit reports stale/missing projects and the primitive changes projection/update behavior;
- service-readiness is red and the primitive is used for service/headless claims;
- the registry duplicates lifecycle/readiness manifests without adding join value;
- intervention rows cannot correlate to sessions reliably.
