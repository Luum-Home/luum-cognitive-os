---
type: concept-synthesis
source: docs/04-Concepts/architecture/dx-cloud-flow-bootstrap-plan.md
status: ready-for-first-flow-lab
provenance: "Cognitive OS needs a bounded path from governance-layer-over-agents (Framing B) to a runtime that travels with the agent (Framing A) for cloud maintenance flows, without repeating pre-v0.23 surface inflation."
---

## What it is

A bounded, non-ADR bootstrap plan (same shape as `expansion-hardening-plan.md`) for building **one real flow** — vulnerability remediation in a sandbox — end-to-end on existing primitives, as the vehicle for the Framing B -> Framing A trajectory decision.

## Key mechanics

- Non-negotiable contract: agents propose, humans approve the final landing — the same contract ADR-134/135 already enforce internally, generalized to all agent work.
- Gate: `scripts/lab_first_promotion_gate.py` — every new primitive starts in `lab`/`sandbox` and earns promotion only through evidence.
- First-flow selection rationale: deterministic input (CVE/semgrep/dependabot), self-verifiable output (tests pass, scan re-run clean, PR mergeable), reuses the existing `e2b-integration` sandbox skill, ships as a GitHub PR reviewed via `cos-engram-import-propose`, survives anti-self-validation (`manifests/external-adoption-evidence.yaml` rejects self-reported/maintainer-owned/same-machine evidence).
- Bootstrap budget: `skills/vuln-remediation-flow/` (lifecycle_state `lab`), `scripts/cos-cloud-worker-bootstrap.sh` (not promoted to skill), `manifests/flow-contract-schema.yaml`, wired `llm-dispatch.jsonl` instrumentation, first non-zero counter in `manifests/federation-triggers.yaml`, one propose-only evidence bundle. Explicitly zero new default-visible primitives and zero new rules in `RULES-COMPACT.md`.
- Falsifiable-broken conditions: `llm-dispatch.jsonl` still empty after a week; `external_consumer_reports_30d` stays zero after running on a non-maintainer codebase; a second flow lands without reusing the bootstrap script or promoting the schema; `VISIBLE_WARN=12` gets crossed; an evidence bundle is signed despite `maintainer_owned`/`same_machine: true`; any promotion skips a `demotion_evidence` block.
- Ordered artefacts: ADR-137 (trajectory, landed) -> ADR-138 (flow contract schema, landed) -> ADR-139..142 (cloud premises: credential/billing isolation, containerized deployment, Engram cloud replication, compliance/audit surface — all landed) -> first flow lab entry (construction begins now).
- Priority shifts under Framing A: ADR-064 harness-agnostic completion, `bootstrap-portability.md` enforced as a gate not an aspiration, cross-machine Engram daemon discovery, cloud-worker-aware session lifecycle hooks.

## Relations & where used

ADR-137, ADR-138, ADR-139, ADR-140, ADR-141, ADR-142, ADR-064, ADR-126, ADR-132, ADR-133, ADR-134, ADR-135, ADR-136; companion docs `cognitive-prosthesis.md`, `boring-reliability-control-plane.md`, `bootstrap-portability.md`, `expansion-hardening-plan.md`.

## Status / caveats

Status advanced from `ready-for-step-3` to `ready-for-first-flow-lab` once ADR-137..142 all landed. Shape B activation is explicitly **not** decided here — it is defined as a consequence of trigger conditions firing in `manifests/federation-triggers.yaml`, not a roadmap milestone. Not an ADR (no decision committed) and not a roadmap (no dates beyond the first flow).
