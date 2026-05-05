---
adr: 165
title: Proof Drill and Smoke Opt-In Agentic Primitives
status: accepted
date: 2026-05-05
supersedes: []
superseded_by: null
implementation_files:
  - manifests/proof-drill-registry.yaml
  - skills/proof-drill/SKILL.md
  - docs/architecture/proof-drill-and-smoke-opt-in-primitives.md
  - docs/manual-tests/proof-drill-registry.md
  - tests/contracts/test_proof_drill_registry.py
tier: maintainer
tags: [testing, proof-drills, smoke, primitives, self-build, consumer-projects]
---

# ADR-165: Proof Drill and Smoke Opt-In Agentic Primitives

## Status

**Accepted** — 2026-05-05

## Context

The repo already had several verification surfaces:

- normal SO pytest runners such as `skills/cognitive-os-test/SKILL.md`;
- consumer-project test selection through `skills/run-tests/SKILL.md`;
- one-off provider smokes such as `scripts/smoke-qwen-fallback.sh`;
- Docker/headless and service-control-plane proof ladders documented under
  `docs/architecture/` and `docs/manual-tests/`.

Those surfaces were useful but scattered. Agents could confuse three different
jobs: building this SO, testing a project that implements it, and qualifying an
optional runtime/provider path. The risk is either under-testing product claims
or adding expensive/provider-backed drills to default lanes.

## Decision

Create a governed proof-drill/smoke-opt-in primitive layer:

1. `manifests/proof-drill-registry.yaml` is the machine-readable registry of
   standard test lanes, smoke opt-ins, proof drills, and manual proofs.
2. `skills/proof-drill/SKILL.md` teaches agents how to select the correct
   validation without polluting default lanes.
3. Proof drills and smoke opt-ins are explicit opt-ins. They must not be added
   to default laptop, CI, or consumer-project test lanes.
4. Every entry declares scope: `os-self`, `consumer-project`, or `both`.
5. Provider-backed checks treat missing credentials as skipped evidence, not as
   proof of runtime failure.
6. Every proof report must record what it proves and what it does not prove.

## Consequences

### Positive

- Agents can distinguish SO self-build checks from consumer-project checks.
- Provider and Docker proof paths stay visible without becoming default tax.
- Product claims gain a path from documentation to executable or manual proof.
- Future COS instance installer work can reference a registry instead of prose.

### Negative

- Maintainers must keep the registry aligned as new proof scripts appear.
- Some entries are manual until their runtime code becomes stable enough for an
  automated lane.
- Operators still need to opt in for live provider, Docker, VM, or Kubernetes
  proof paths.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep proof drills only in docs | Agents miss scattered procedures and rerun the wrong lane. |
| Put all smokes in default CI | Adds provider cost, Docker flake, and credential assumptions to normal work. |
| Treat consumer projects like SO self-tests | Downstream projects have their own frameworks and should not inherit SO-only drills. |
| Promote every manual proof to automated tests immediately | Some proofs require accounts, Docker, cloud, or lifecycle maturity. |

## Verification

```bash
python3 -m pytest tests/contracts/test_proof_drill_registry.py -q
python3 -m pytest tests/audit/test_skills_contracts.py -q
python3 -m pytest tests/audit/test_adr_contracts.py tests/audit/test_adr_locations.py -q
```

## Implementation Evidence

- `manifests/proof-drill-registry.yaml` classifies existing SO and consumer
  validation primitives.
- `skills/proof-drill/SKILL.md` defines the operator/agent procedure.
- `tests/contracts/test_proof_drill_registry.py` enforces opt-in and path
  resolution invariants.
