---

adr: 138
title: Flow Contract Schema — Required Shape for Cloud Flow Manifests
status: accepted
implementation_status: implemented
date: 2026-05-03
supersedes: []
superseded_by: null
implementation_files:
  - manifests/flow-contract-schema.yaml
tier: maintainer
tags: [strategy, runtime, flows, manifest, schema, propose-only]
---

# ADR-138: Flow Contract Schema — Required Shape for Cloud Flow Manifests

## Status

**Accepted and materialized for first lab registration.** The companion
artefact (`manifests/flow-contract-schema.yaml`) now exists because the first
lab flow contract (`skills/vuln-remediation-flow/flow_contract.yaml`) registers
against it. The schema remains **exemplary**, not shared, until a second flow
registers without modification.

## Context

[ADR-137](ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md) commits Cognitive OS to the trajectory `Framing B → Framing A` and introduces the **framing-exercise statement** as a required field in flow skill metadata. [ADR-134](ADR-134-headless-self-improvement-proposer.md) and [ADR-135](ADR-135-self-evolving-doctrine-proposals.md) define the propose-only contract for the self-improvement and doctrine proposers. The [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md) commits the bootstrap path: vulnerability remediation in sandbox as flow #1, with explicit bootstrap budget caps.

What is missing: a single, declarative shape that every flow primitive must satisfy. Today the propose-only contract for ADR-134 / ADR-135 lives inside the proposer scripts as constants. The flow primitives the bootstrap plan introduces need that contract generalised so that:

1. The first flow does not invent its own contract shape.
2. The second flow does not invent a different contract shape.
3. CI can audit a flow registration mechanically and reject any flow whose contract is incomplete or violates structural rules (anti-self-validation, propose-only, framing-exercise statement, lab-first promotion).
4. Future flows opt into the contract by reference, not by re-declaration.

This ADR commits the schema. The schema is intentionally minimal — enough to make the first flow safe, not enough to anticipate every future flow.

## Decision

Commit the following shape for `manifests/flow-contract-schema.yaml`. All flow primitives registered after this ADR lands MUST satisfy the shape; partial conformance is rejected by the registration audit.

### Top-level shape

```yaml
schema_version: 1
policy: >-
  Every cloud flow primitive declares its contract before it ships. The
  contract makes the flow's promises and limits machine-checkable. A flow
  whose contract is missing fields, contradictory, or inconsistent with
  ADR-137's framing-exercise statement is rejected at registration.
required_flow_shape:
  flow_id: stable-kebab-case identifier
  lifecycle_state: lab|sandbox|advisory|blocking|default-on|demoted|archived|deleted
  owner: maintainer or external producer identity
  registered_on: timestamp
  input_source:
    type: cve-feed|semgrep|dependabot|issue|pr-comment|manual|other
    identifier: stable address of the input (URL, queue, file path)
    determinism: deterministic|best-effort
  success_condition:
    description: human-readable, single sentence
    verifier: command, script path, or external check producing exit-zero
    evidence_required:
      - test_pass: bool
      - rescan_clean: bool
      - reviewer_signature: bool
  sandboxed_write_paths:
    - relative path or glob the flow is allowed to write
  blocked_actions:
    - auto_merge
    - auto_promote_core_or_team
    - invent_evidence
    - bypass_governance_gate
    - direct_main_push
  human_approval_required: true
  evidence_shape:
    transport: pr|cos-engram-import-propose|file-drop|other
    bundle_path: relative path under .cognitive-os/ or repo
    independence:
      maintainer_owned: false
      same_machine: false
      same_repo: false
      self_reported: false
  framing_exercise_statement:
    boots_cos_init: yes|no|partial
    uses_native_engram_client: yes|no|partial
    dispatches_through_configured_providers: yes|no|partial
    hooks_fire_natively: yes|no|partial
    session_lifecycle_handled: yes|no|partial
    notes: free-form rationale per axis
  non_goals:
    - explicitly listed anti-patterns the flow must not slide into
  falsifiable_when:
    - observable conditions under which this flow is considered broken
  # Fields added by ADR-139 (account-agnostic runtime)
  credential_source: byok-maintainer|byok-project|proxied
  billing_identity: stable identifier for cost attribution (e.g., project slug)
  provider_capabilities:
    - text-completion|code-generation|...  # declared capabilities only
  # Fields added by ADR-141 (Engram cloud replication)
  engram_project_scope: stable project slug matching ENGRAM_CLOUD_ALLOWED_PROJECTS
  air_gapped_compatible: true|false
  # Fields added by ADR-142 (compliance / audit)
  tenant_id: "<flow_id>-<launch-timestamp>"  # populated at worker launch time
  audit_class: access_control|change_management|availability|processing_integrity|confidentiality|privacy|sync
```

### Field-level rules

- `flow_id` MUST be unique across the registry. Re-registration with the same ID requires a `lifecycle_state` transition, not a silent overwrite.
- `lifecycle_state` MUST start at `lab` for any new flow ([ADR-133](ADR-133-expansion-without-monsterization.md)). Promotion requires the same evidence block ADR-126 mandates for `default-on` primitives.
- `input_source.determinism: deterministic` is a precondition for promotion beyond `advisory`. `best-effort` flows stay in `lab` / `sandbox` until the input source becomes deterministic or until evidence shows best-effort is acceptable for the flow class.
- `success_condition.verifier` MUST be runnable from CI without maintainer-machine assumptions. A verifier that requires `~/.claude/` or `~/.engram/` violates [`bootstrap-portability.md`](../architecture/bootstrap-portability.md).
- `sandboxed_write_paths` MUST exclude `manifests/`, `rules/`, `docs/adrs/`, and `.cognitive-os/runtime/` by default. A flow that needs to write into any of these requires an explicit per-path opt-in and a reason field.
- `blocked_actions` MUST include the five entries above as a minimum. Flow-specific additions are allowed; removals are not. The list mirrors the proposer constants from ADR-134.
- `human_approval_required: true` is hardcoded in the schema. A flow that proposes to remove this field fails validation. The trajectory committed in ADR-137 is `Framing B → Framing A`, not `human-in-loop → autonomous`.
- `evidence_shape.independence` mirrors `manifests/external-adoption-evidence.yaml` (commit `d4535df`). A flow whose evidence is `maintainer_owned: true` produces drill output, not adoption signal.
- `framing_exercise_statement` MUST have all five axes declared per [ADR-137](ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md). Missing axes block promotion out of `lab`. `partial` is a valid value but requires the `notes` field to explain what makes it partial.
- `non_goals` MUST contain at least one entry. An empty list is signal that the flow has not been thought about adversarially.
- `falsifiable_when` MUST contain at least one observable condition. This mirrors the stage-2 maturity property from [`cognitive-prosthesis.md`](../architecture/cognitive-prosthesis.md): every capability ships alongside the conditions under which it would be considered broken.

### Promotion rule for the schema itself

The schema is committed to **exemplary** status when this ADR lands. It moves to **shared** status — i.e., promoted from a flow-specific shape to a cross-flow contract — only after the **second flow** registers against it without modification. If the second flow needs to extend the schema, the extension lands as ADR-138a (or a new ADR) and the prior schema is preserved as a read-fallback.

This rule prevents two failure modes:

1. **Premature generalisation.** A schema generalised from a single flow encodes that flow's idiosyncrasies as universal truths.
2. **Drift.** A schema that grows fields per-flow without a promotion rule becomes a feature checklist, not a contract.

The promotion rule itself is enforced by `scripts/cos-flow-contract-audit` (to be created when the second flow registers).

## Acceptance Criteria

This ADR is satisfied when:

1. The first flow registered under [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md) (`vuln-remediation-flow`) carries a `flow_contract.yaml` (or equivalent) in its skill directory whose shape matches `required_flow_shape` above.
2. CI at registration time rejects a flow whose contract is missing any required field or whose values violate the field-level rules above. The implementation lives in `scripts/cos-flow-register.sh` (to be created).
3. The schema lands as `manifests/flow-contract-schema.yaml` no later than the first flow's `lab` registration. Until that point, the schema lives in this ADR as canonical reference.
4. After the second flow lands, either: (a) it registers against the unchanged schema and the schema is promoted to shared status, or (b) it requires extensions and a new ADR carries them. Silent schema evolution is rejected by audit.

## Border Cases

- **A flow whose verifier is non-deterministic** (e.g., LLM-as-judge for a documentation flow). Registers as `input_source.determinism: best-effort`, stays in `lab` until evidence shows best-effort is acceptable for that flow class. Does not block other flows.
- **A flow whose evidence cannot satisfy `independence` flags** because the maintainer is the first reviewer. Allowed in `lab` — registration captures the gap as `notes` under `evidence_shape`. Promotion beyond `advisory` requires non-maintainer review.
- **A flow that legitimately needs to write into `manifests/` or `rules/`** (e.g., a primitive-expansion flow). Registers `sandboxed_write_paths` with explicit per-path opt-in and a `reason` field. The audit log captures the opt-in for review.
- **A flow that proposes a new `lifecycle_state` value** not in the enumeration above. Rejected at registration; the lifecycle states are governed by ADR-126 and not extensible per-flow.
- **A flow that proposes `human_approval_required: false`** for autonomous operation. Rejected at registration; a future ADR (not this one) is required to relax the contract, and would supersede ADR-137's commitment.
- **The first flow lands but a registration audit script does not exist yet.** The contract is enforced by the maintainer reading the YAML against this ADR. The audit script is required before the second flow lands.

## Consequences

**Positive.**

- Every flow shipped under the bootstrap plan inherits the safety properties of ADR-134 / ADR-135 (propose-only, blocked actions, human approval) without re-declaring them.
- The `framing_exercise_statement` requirement from ADR-137 has a concrete home and a registration-time check, rather than living as prose in an architecture doc.
- The anti-self-validation schema from `external-adoption-evidence.yaml` extends naturally to flow output, closing the loop between flow execution and adoption-evidence reporting.
- A new contributor reading a flow's contract YAML can answer "what does this flow promise, what does it refuse, and when would it be considered broken?" without reading the implementation.

**Negative / risk.**

- The schema is a contract surface; every field is a maintenance commitment. The promotion rule (shared-only-after-second-flow) is the brake on uncontrolled growth.
- Some early flows may strain the schema and feel boilerplate-heavy. That is the intended cost: the propose-only contract was previously implicit and survived only through maintainer attention. Making it explicit costs YAML lines and saves debugging cycles.
- The schema may anchor the maintainer's flow design too tightly. Mitigation: the promotion rule allows ADR-138a or a new ADR to extend or replace the schema as evidence accumulates.

**Of not committing this schema.**

- Each flow invents its own contract shape. The propose-only properties drift from flow to flow, and CI cannot audit them mechanically.
- The framing-exercise statement requirement from ADR-137 has no enforcement point and becomes aspirational.
- The bootstrap plan's first-flow construction stalls on contract design instead of building flow logic.

## Cross-references

- [ADR-137](ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md) — trajectory commitment; introduces the framing-exercise statement that this schema makes mechanical.
- [ADR-134](ADR-134-headless-self-improvement-proposer.md) / [ADR-135](ADR-135-self-evolving-doctrine-proposals.md) — propose-only contract pattern that this schema generalises.
- [ADR-126](ADR-126-agentic-primitive-lifecycle-governor.md) — lifecycle states the schema enumerates.
- [ADR-133](ADR-133-expansion-without-monsterization.md) — `lab`-first promotion gate that the schema enforces by setting `lifecycle_state` default to `lab`.
- [ADR-136](ADR-136-cross-instance-learning-runway.md) — `cos-engram-import-propose` listed as a valid `evidence_shape.transport`.
- `manifests/external-adoption-evidence.yaml` (commit `d4535df`) — the `independence` flags structure this schema reuses.
- [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md) — the operational plan that consumes this schema.
- [`cognitive-prosthesis.md`](../architecture/cognitive-prosthesis.md) — the stage-2 maturity property (`falsifiable_when`) the schema reifies as a required field.
- [`bootstrap-portability.md`](../architecture/bootstrap-portability.md) — the gate the `success_condition.verifier` rule defers to.
- [ADR-139](ADR-139-account-agnostic-multi-provider-runtime.md) — adds `credential_source`, `billing_identity`, `provider_capabilities` fields to `required_flow_shape`.
- [ADR-141](ADR-141-engram-cloud-cross-instance-replication.md) — adds `engram_project_scope`, `air_gapped_compatible` fields to `required_flow_shape`.
- [ADR-142](ADR-142-compliance-audit-air-gapped-surface.md) — adds `tenant_id`, `audit_class` fields to `required_flow_shape`.

## Alternatives rejected

- Leave the ADR without an alternatives section — rejected because ADR-067+ audit contracts require a falsifiable record of considered options.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

