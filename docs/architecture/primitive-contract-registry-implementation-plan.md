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

## OpenSage pressure test

OpenSage ADK is now a formal pressure test for this plan, not a runtime dependency. The extracted patterns are codified in `manifests/self-programming-agent-patterns.yaml` and checked by `scripts/cos-self-programming-pattern-audit`. ADR-256 must be able to answer these OpenSage-shaped questions before any adapter lab can execute generated agents/tools:

1. Which primitive authorized dynamic subagent topology?
2. Which primitive-authoring, license, credential, discovery, and sandbox gates approved a generated tool or skill?
3. Which sandbox tier actually ran the tool, and did it fall back?
4. Which memory/itinerary rows were written without leaking contents?
5. Which benchmark result proves primitive use rather than architecture intent?

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

## OpenCode non-reinvention rule

Do not build a parallel OpenCode enforcement layer when OpenCode already exposes
the required host surfaces. Use OpenCode-native surfaces first:

1. `opencode.json` / `AGENTS.md` for advisory context.
2. OpenCode permissions for coarse `allow` / `ask` / `deny` policy.
3. OpenCode plugins for `tool.execute.before` and `tool.execute.after`
   enforcement or observation.
4. COS `primitive-interventions.jsonl` for comparable cross-harness evidence.

The current COS OpenCode projection remains structural until this adapter is
implemented and smoke-tested.

## Phase 0 — Contract freeze

Keep the plan-first documentation consistent before runtime changes:

- ADR-256.
- `docs/architecture/ide-agnostic-primitive-projection.md`.
- `/primitive-authoring`.
- `docs/architecture/opensage-self-programming-patterns.md`.
- `manifests/self-programming-agent-patterns.yaml`.

Test:

```bash
scripts/cos-self-programming-pattern-audit --json
python3 -m pytest tests/unit/test_self_programming_pattern_audit.py -q
```

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

## Phase 6 — Consumer UX

Add small commands once contract/evidence/reporting exists:

```bash
cos adapters list
cos adapters install codex
cos adapters install cursor
cos adapters verify
cos observe primitives
```

These commands should present a `.ai`-like overlay mental model without copying `.ai/` wholesale into COS.
