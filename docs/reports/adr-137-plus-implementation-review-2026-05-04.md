# ADR-137+ Implementation Review — 2026-05-04

## Goal

Review every ADR from 137 onward and classify whether it is implemented, partially implemented, not implemented, or blocked on deeper local or external research.

## Scope

- ADRs reviewed: ADR-137 through ADR-144.
- Git window reviewed: commits since `2026-05-01 00:00`.
- Local evidence checked: ADR files, `docs/architecture/dx-cloud-flow-bootstrap-plan.md`, manifests, scripts, hooks, projection drivers, and targeted tests.
- External evidence checked only where the ADR depends on an unstable upstream surface: Engram Cloud.

## Summary

| ADR | Status | Confidence | Why |
|---|---:|---:|---|
| ADR-137 — Governance layer → embedded runtime | Partially implemented / lab registration started | Medium | Direction is documented and the first lab flow contract now carries a framing-exercise statement, but no worker has executed Framing A end-to-end. |
| ADR-138 — Flow contract schema | Implemented for first lab registration / schema still exemplary | High | `manifests/flow-contract-schema.yaml`, `scripts/cos-flow-register.sh`, tests, and `skills/vuln-remediation-flow/flow_contract.yaml` now exist and validate. Shared-schema promotion still waits for a second flow. |
| ADR-139 — Account-agnostic multi-provider runtime | Partially implemented through registration gate | Medium | The first flow contract and ADR-138 validator require `credential_source`, `billing_identity`, and `provider_capabilities`; worker launch enforcement is still absent. |
| ADR-140 — Cross-OS containerized deployment | Not implemented | High | `docker/cos-worker/docker-compose.yml` does not exist. |
| ADR-141 — Engram Cloud cross-instance replication | Not implemented in COS / upstream needs pinning | Medium | Existing `scripts/engram-sync.sh` covers git-jsonl fallback, but `scripts/cos-engram-cloud-enroll` and cloud hook wiring are absent. Web search found an upstream Engram CLI that advertises `engram cloud serve/enroll/sync`, but COS has not pinned or integrated it. |
| ADR-142 — Compliance, audit, air-gapped surface | Partially implemented through registration gate | Medium | The first flow contract and ADR-138 validator require `tenant_id`, `audit_class`, and `air_gapped_compatible`; runtime audit rows, `scripts/cos-audit-archive`, and GDPR procedure docs are still absent. |
| ADR-143 — Closure discipline gate | Implemented | High | The audit script, quick-CI wiring, manifest registration, manual test, and unit tests exist; targeted validation passes. |
| ADR-144 — Hook-enforced rule projection contract | Implemented | High | The projection audit, Bash bypass gate, projection-driver wiring, manual test, and behavior tests exist; targeted validation passes. |

## Commit Evidence

Relevant commits from the reviewed three-day window:

- `5cc9e098` (`2026-05-03`) added ADR-137 and updated the DX cloud flow plan.
- `45c3a087` (`2026-05-03`) added ADR-138.
- `99af7ff7`, `7324db1d`, `2077b087`, `e48bb11c` (`2026-05-04`) added ADR-139 through ADR-142.
- `55c87219` (`2026-05-04`) updated ADR-138 with fields from ADR-139, ADR-141, and ADR-142.
- `3a952951` (`2026-05-04`) made ADR-139 through ADR-142 explicit prerequisites before promoting flow #1 beyond lab.
- `1d454bbe` (`2026-05-04`) implemented ADR-143.
- `cb37eef6` (`2026-05-04`) implemented ADR-144.

The commit history therefore supports a split interpretation: ADR-137 through ADR-142 are mostly directional/contract decisions for the next cloud flow, while ADR-143 and ADR-144 landed with executable enforcement.

## ADR-by-ADR Findings

### ADR-137 — Operational Trajectory

**Classification:** partially implemented / accepted trajectory.

**Implemented evidence:**

- `docs/adrs/ADR-137-operational-trajectory-governance-layer-to-embedded-runtime.md` exists and is accepted.
- `docs/architecture/dx-cloud-flow-bootstrap-plan.md` references the trajectory and names ADR-139 through ADR-142 as prerequisites before promoting flow #1 beyond lab.
- ADR-136 runway primitives already exist from prior commits and provide adjacent transport concepts.

**New lab-registration evidence:**

- `skills/vuln-remediation-flow/flow_contract.yaml` is registered as the first lab contract.
- `skills/vuln-remediation-flow/SKILL.md` and the contract carry a `framing_exercise_statement`.
- `manifests/federation-triggers.yaml` exposes `framing_a_flows_active: 0` so runtime execution can increment a concrete counter later.

**Missing evidence:**

- No cloud worker has executed the flow end-to-end in Framing A.
- ADR-064 implementation status still needs to be reconciled against the first cloud-worker flow's concrete needs.

**Needs deeper local research:** yes. Before editing this ADR, review ADR-064 implementation surfaces, `docs/architecture/bootstrap-portability.md`, and the actual first cloud flow design once it exists.

**Needs internet research:** no, unless the first flow depends on external sandbox/provider APIs.

### ADR-138 — Flow Contract Schema

**Classification:** implemented for first lab registration / schema still exemplary.

**Implemented evidence:**

- ADR-138 exists and was updated to include fields introduced by ADR-139, ADR-141, and ADR-142.
- The DX cloud flow plan lists full contract registration as the next lab-entry step.
- `manifests/flow-contract-schema.yaml` exists.
- `scripts/cos-flow-register.sh` and `scripts/cos_flow_register.py` validate contracts.
- `skills/vuln-remediation-flow/flow_contract.yaml` validates against the schema.
- `tests/audit/test_flow_contract_schema.py` covers valid and invalid contracts.

**Missing evidence:**

- The schema is not yet promoted to shared status; ADR-138 requires a second flow to register without modification before that claim is valid.
- Flow runtime execution is still outside ADR-138 and belongs to ADR-140 through ADR-142.

**Needs deeper local research:** no for first registration; yes before shared-schema promotion.

**Needs internet research:** no.

### ADR-139 — Account-Agnostic Multi-Provider Runtime

**Classification:** partially implemented through registration gate; worker enforcement pending.

**Implemented evidence:**

- Direct Anthropic API governance exists elsewhere in the repo and recent commits added provider-safety policy/tests.
- The ADR-139 fields are documented as additions to ADR-138 and the DX cloud flow plan.
- `skills/vuln-remediation-flow/flow_contract.yaml` declares `credential_source`, `billing_identity`, and `provider_capabilities`.
- `scripts/cos-flow-register.sh` rejects contracts missing those fields.

**Missing evidence:**

- No cloud worker launch script exists to prove caller-supplied credentials.
- No `scripts/cos-engram-cloud-enroll` exists using generic `LLM_PRIMARY_API_KEY` / `LLM_FALLBACK_API_KEY` names.
- Provider-facing dependency license audit coverage specific to flow scripts is not yet evident.

**Needs deeper local research:** yes. Search all future flow launch surfaces once created and decide whether existing `lib/anthropic_direct_policy.py` and provider tests can be reused or must be extended.

**Needs internet research:** possibly. If new provider SDKs are introduced, verify current licenses from upstream package metadata before adding dependencies.

### ADR-140 — Cross-OS Containerized Deployment

**Classification:** not implemented.

**Implemented evidence:**

- ADR-140 exists and the DX cloud flow plan lists it as a prerequisite.

**Missing evidence:**

- `docker/cos-worker/docker-compose.yml` is missing.
- No container worker bootstrap proof exists.
- No Docker-based test proves a hook can run and append to `.cognitive-os/runtime/agent-audit-trail.jsonl`.
- `docs/architecture/bootstrap-portability.md` is not yet updated to mark the Compose stack as satisfying worker-surface portability.

**Needs deeper local research:** yes. Reconcile with existing Docker files, package install paths, harness drivers, and minimal worker runtime requirements before adding a new stack.

**Needs internet research:** no for the first implementation; Docker/Compose docs may be useful only if cross-platform mount behavior becomes ambiguous.

### ADR-141 — Engram Cloud Cross-Instance Replication

**Classification:** not implemented in COS; upstream surface needs pinning.

**Implemented evidence:**

- Existing `scripts/engram-sync.sh` preserves a git-jsonl style fallback path.
- The ADR explicitly keeps local SQLite authoritative and cloud replication optional.

**Missing evidence:**

- `scripts/cos-engram-cloud-enroll` is missing.
- No `packages/engram-sync/hooks/` cloud autosync wiring was verified in this pass.
- No cloud sync audit rows with the ADR-defined fields were found.
- No first flow contract exists with `engram_project_scope` and `air_gapped_compatible`.

**External research note:**

- The upstream `syntax-syndicate/engram-agent-memory` search result advertises `engram cloud serve`, `engram cloud enroll <project>`, `engram cloud sync`, and `engram cloud sync-status`.
- The public Engram product site advertises MCP, REST API, API-key backed hosted cloud, and self-hosting; a separate docs site describes a local daemon with SQLite and no cloud requirement.
- Because several public “Engram” surfaces exist, COS should pin the intended upstream repository, CLI version, and command contract before implementing ADR-141.

**Sources:**

- [Engram product site](https://engram.so/)
- [Engram docs site](https://engram.am/docs)
- [Search result for `syntax-syndicate/engram-agent-memory`](https://github.com/syntax-syndicate/engram-agent-memory)

**Needs deeper local research:** yes. Confirm which Engram integration in this repo maps to the upstream cloud CLI and where cloud sync hooks should live.

**Needs internet research:** yes. Pin upstream CLI semantics and license/version before writing wrapper scripts or tests.

### ADR-142 — Compliance, Audit, and Air-Gapped Surface

**Classification:** not implemented for cloud workers; existing audit doctrine is adjacent.

**Implemented evidence:**

- The ADR names `.cognitive-os/runtime/agent-audit-trail.jsonl` as the canonical compliance evidence surface.
- Existing hook governance already treats audit trail writes as important runtime evidence.

**Missing evidence:**

- No cloud worker flow emits rows with `tenant_id` and `audit_class`.
- `scripts/cos-audit-archive` is missing.
- `docs/architecture/gdpr-erasure-procedure.md` is missing.
- ADR-138 schema enforcement for `audit_class` exists in `scripts/cos-flow-register.sh`, but runtime audit-row production is still missing.
- Air-gapped local-only proof is blocked by the absence of a first flow.

**Needs deeper local research:** yes. Inventory all producers of `agent-audit-trail.jsonl` before changing row schema so backward compatibility and maintainer-local defaults are explicit.

**Needs internet research:** yes before strengthening compliance prose. Keep claims structural unless checked against current SOC 2 / ISO 27001 / GDPR expectations.

### ADR-143 — Closure Discipline Gate

**Classification:** implemented.

**Implemented evidence:**

- `scripts/cos-closure-discipline-audit` and `scripts/cos_closure_discipline_audit.py` exist.
- `scripts/cos-ci-local.sh quick` contains closure-discipline wiring.
- `manifests/primitive-lifecycle.yaml` registers the primitive.
- `docs/manual-tests/closure-discipline.md` exists.
- Targeted validation passed: `python3 -m pytest tests/unit/test_closure_discipline_audit.py tests/audit/test_hook_enforced_exclusions.py tests/behavior/test_skill_router_bash_gate.py -q` → `14 passed in 1.80s`.

**Remaining watch item:**

- Keep this gate narrow. If it grows into a broad CI runner, it will duplicate release lanes and increase DX tax.

### ADR-144 — Hook-Enforced Rule Projection Contract

**Classification:** implemented.

**Implemented evidence:**

- `hooks/skill-router-bash-gate.sh` exists and covers direct dependency/toolchain upgrade bypasses.
- `scripts/_lib/settings-driver-claude-code.sh` references the hook projection.
- `.claude/settings.json`, `.codex/hooks.json`, and `cognitive-os.yaml` were updated in the implementation commit.
- `tests/audit/test_hook_enforced_exclusions.py` exists.
- `tests/behavior/test_skill_router_bash_gate.py` exists.
- `docs/manual-tests/hook-enforced-rule-projection.md` exists.
- Targeted validation passed in the same `14 passed` run above.

**Remaining watch item:**

- Codex still supports only its native Bash subset. Non-Bash hook events remain a registry/projection concern rather than a native Codex runtime guarantee.

## Recommended Next Work

1. **Do not mark ADR-137, ADR-139, ADR-140, ADR-141, or ADR-142 fully implemented.** Treat them as accepted premises now partially exercised by the first lab contract.
2. **Treat ADR-138 as implemented for first lab registration, not shared promotion.** The second flow still decides whether the schema is promoted unchanged or extended by a follow-up ADR.
3. **Before ADR-141 implementation, pin Engram upstream.** Record repository, version, command contract, license, and cloud/server assumptions.
4. **Before ADR-142 implementation, inventory audit producers.** Add schema migration/default semantics for old rows before requiring `tenant_id` and `audit_class` everywhere.
5. **Keep ADR-143 and ADR-144 in the implemented bucket.** Their tests should remain in quick/audit lanes because they protect closure and startup context-diet correctness.

## Validation

```bash
python3 -m pytest tests/unit/test_closure_discipline_audit.py tests/audit/test_hook_enforced_exclusions.py tests/behavior/test_skill_router_bash_gate.py -q
# 14 passed in 1.80s

python3 -m pytest tests/audit/test_flow_contract_schema.py tests/unit/test_closure_discipline_audit.py -q
# 16 passed in 1.86s
```
