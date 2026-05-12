# Vulnerability Remediation Flow

## Status

Lab registration surface for ADR-137 and ADR-138. This document does not claim
that ADR-140, ADR-141, or ADR-142 worker execution is complete.

## Purpose

The flow receives a deterministic vulnerability input, runs inside a sandboxed
COS worker surface, and returns a proposal bundle that a maintainer can review.
It never lands changes by itself.

## Contract

- Skill: `skills/vuln-remediation-flow/SKILL.md`
- Contract: `skills/vuln-remediation-flow/flow_contract.yaml`
- Validator: `scripts/cos-flow-register.sh`
- Schema: `manifests/flow-contract-schema.yaml`

Validate registration with:

```bash
scripts/cos-flow-register.sh --check --contract skills/vuln-remediation-flow/flow_contract.yaml
```

## Falsifiable When

The flow is considered broken if any of the following are observed:

1. It emits a success result without a test command and vulnerability rescan command.
2. It proposes or performs a direct push to `main` or `master`.
3. It merges, approves, or promotes itself without a human reviewer signature.
4. It claims Framing-A execution while `cos-init`, provider dispatch, hooks, or session lifecycle did not run natively in the worker.
5. It emits evidence where `maintainer_owned`, `same_machine`, `same_repo`, or `self_reported` is true and the result is presented as external adoption signal.

## Promotion Boundary

Promotion out of `lab` requires actual worker execution evidence, not only a
valid contract. At minimum, the next implementation wave must add:

- ADR-140 worker Compose stack or equivalent documented sandbox path;
- ADR-141 Engram cloud or explicit local-only fallback proof;
- ADR-142 audit rows with `tenant_id` and `audit_class`;
- a proposal bundle signed or rejected by a human reviewer.
