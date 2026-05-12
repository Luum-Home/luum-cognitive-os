---

adr: 142
title: Compliance, Audit, and Air-Gapped Surface (SOC 2 / ISO 27001 / GDPR)
status: implemented
implementation_status: implemented
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - scripts/cos-audit-archive
  - docs/architecture/gdpr-erasure-procedure.md
  - docker/cos-worker/entrypoint.sh
  - tests/unit/test_cos_engram_cloud_enroll_and_audit_archive.py
  - tests/audit/test_adr_139_141_142_cloud_surfaces.py
tier: maintainer
tags: [security, compliance, audit, air-gap, gdpr, soc2, iso27001, cloud-flows, tenant-isolation]
---

# ADR-142: Compliance, Audit, and Air-Gapped Surface (SOC 2 / ISO 27001 / GDPR)

## Status

**Accepted — Implemented** as the compliance posture and audit-trail bridge for all COS cloud worker surfaces.

This ADR does not certify COS for any standard. It names the structural properties that make COS *auditable towards* SOC 2 Type II, ISO 27001, and GDPR, and the constraints that make air-gapped deployment viable. Certification is an operator-level concern; this ADR provides the underlying machinery.

## Context

Cloud worker flows (ADR-137 Framing A) execute agent logic in ephemeral containers under human audit. As soon as a flow writes code, modifies dependencies, or reads project data, three compliance regimes become relevant:

1. **SOC 2 Type II** — continuous evidence of access control, availability, processing integrity, confidentiality, and privacy over time.
2. **ISO 27001** — information security management controls covering risk assessment, access management, incident response, and supplier relationships.
3. **GDPR** — data minimisation, purpose limitation, and right-to-erasure for personal data processed by or flowing through the runtime.

COS already produces significant audit signal: `agent-audit-trail.jsonl`, `blast-radius.jsonl`, `hook-timing.jsonl`, `clarification-events.jsonl`, `cost-events.jsonl` (named in the bootstrap plan). The problem is that this signal is not bridged to a compliance-consumable shape, and three structural gaps exist:

1. **Tenant isolation.** Multiple flows running concurrently may write to the same Engram project namespace or the same audit JSONL without per-flow tagging. SOC 2 processing integrity requires per-flow attribution.
2. **Air-gap surface.** The bootstrap plan names `air_gapped_compatible` as a flow contract field (ADR-141). A deployment without internet access must still produce auditable evidence. The current JSONL-append model is already compatible, but it is not explicitly committed as the air-gap audit surface.
3. **Personal data in observations.** Engram observations may contain code snippets, commit messages, or error outputs that include personal data (developer names, email addresses in code, etc.). GDPR requires a path to identify and erase such data without dropping the entire Engram database.

## Decision

### 1. `agent-audit-trail.jsonl` is the canonical compliance evidence surface

The file `.cognitive-os/runtime/agent-audit-trail.jsonl` (confirmed canonical via `hooks/git-commit-scope-guard.sh`) is the single JSONL that aggregates compliance-relevant events. All other per-domain JOSNLs (`blast-radius.jsonl`, `hook-timing.jsonl`, etc.) remain as they are; compliance queries join against `agent-audit-trail.jsonl` as the primary index.

Row producers (hooks, flow scripts, sync operations) MUST include a `tenant_id` field as defined in §2. Rows without `tenant_id` are valid (backward compat) but classified as `maintainer` tenant by default.

The audit trail is **append-only**. No COS component truncates or rotates it autonomously. Rotation (archiving old rows to compressed storage) is an operator-level concern; COS provides a `scripts/cos-audit-archive` helper that compresses rows older than a configurable retention window without deleting them.

### 2. Tenant isolation: `tenant_id` per flow

Every audit row produced by a cloud worker flow MUST carry:

```json
{
  "tenant_id": "<flow_id>-<launch-timestamp>",
  "flow_id": "<flow-id from flow contract>",
  ...
}
```

`tenant_id` is a stable compound key: the flow's `flow_id` from the contract plus a launch timestamp (ISO-8601, second precision). This allows the same flow to run multiple times without colliding audit rows. The `tenant_id` is also injected into Engram observations (as the `project` tag suffix) when cloud sync is active, so sync audit rows (ADR-141 §8) carry the same key.

Server-side enforcement: when `engram cloud serve` is the sync target, `ENGRAM_CLOUD_ALLOWED_PROJECTS` is set to the `tenant_id`-derived scope. Workers cannot write to namespaces outside their `tenant_id`.

### 3. Audit class: classifying events for compliance queries

Each audit row MUST include an `audit_class` field drawn from the following enumeration:

| `audit_class` | Description | SOC 2 relevance | ISO 27001 | GDPR |
|---|---|---|---|---|
| `access_control` | Hook firing, gate pass/block, credential usage | CC6 | A.9 | Art. 32 |
| `change_management` | File write, git commit, branch creation | CC8 | A.12 | Art. 32 |
| `availability` | Session start/stop, container boot/teardown | CC7 | A.17 | — |
| `processing_integrity` | LLM call, provider dispatch, cost event | CC5 | A.14 | Art. 22 |
| `confidentiality` | Secret detection, credential check, blast-radius gate | CC6 | A.10 | Art. 5 |
| `privacy` | Observation containing personal data flag, erasure request | CC2 | A.18 | Art. 17 |
| `sync` | Engram push/pull, git-jsonl export/import | CC7 | A.12 | — |

The `audit_class` field is added to the `required_flow_shape` in ADR-138 (see §Schema extension). A flow that does not produce at least one `change_management` and one `processing_integrity` row is considered not instrumented.

### 4. Air-gap deployment surface

A deployment where `ENGRAM_CLOUD_AUTOSYNC` is unset and no external network calls are required is classified as **air-gapped compatible**. The compliance evidence surface in air-gap mode is:

- `.cognitive-os/runtime/agent-audit-trail.jsonl` — append-only, local filesystem
- `.engram/exports/{project}.jsonl` — git-jsonl Engram snapshot (ADR-141 git-jsonl mode)
- `.cognitive-os/metrics/*.jsonl` — per-domain metric files (existing)

All three exist on the local filesystem and are committed to the project repo on each `scripts/engram-sync.sh` run. An air-gapped SOC 2 audit can be served entirely from the git history of these files.

**Hard constraint**: no audit row MUST require a network call to be produced. Hooks, flow scripts, and sync operations that produce audit rows MUST write to local JSONL first; network transmission is additive.

### 5. GDPR: personal data identification and erasure path

COS does not guarantee Engram observations are free of personal data. The GDPR erasure path:

1. **Identification**: the operator runs `engram search "email|name|@"` (or an equivalent narrower query) to surface observations potentially containing personal data. COS does not automate this search; it documents the command.
2. **Erasure from local DB**: current Engram v1.15.x does not expose a documented `engram delete` CLI command. The operator must use an available Engram MCP admin/API deletion path for the installed version, or perform a documented DB-level erasure procedure under maintenance mode. COS does not silently mutate the Engram store.
3. **Erasure from git-jsonl export**: the operator removes the corresponding line from `.engram/exports/{project}.jsonl` and commits. History erasure (rewriting git history) is outside COS scope and must be performed by the operator via `git filter-repo` or equivalent.
4. **Erasure from cloud sync**: current Engram v1.15.x does not expose a documented `engram cloud delete` command. The operator must use the cloud server's supported admin/API deletion path for the installed version, or rotate/rebuild the cloud store from redacted local state. COS records the procedure and audit evidence, but does not pretend a nonexistent CLI exists.
5. **Audit log**: each erasure MUST be recorded in `agent-audit-trail.jsonl` with `audit_class: privacy`, `event: observation_erased`, and the observation ID. The erasure record itself is retained (the audit of the erasure, not the erased content).

COS's role in GDPR compliance is to provide the erasure path and to ensure the audit trail is auditable. COS does not implement automated erasure or data retention policies; these are operator responsibilities.

### 6. ISO 27001 supplier relationship clause

When a flow uses an external LLM provider (non-self-hosted), the flow contract MUST include a `provider_capabilities` declaration (ADR-139) and the operator MUST verify that the provider's data processing agreement (DPA) is in place. COS cannot enforce DPA existence; it exposes the `provider_capabilities` list as the evidence surface for this control.

For self-hosted providers (proxies, local models), the supplier clause does not apply. The flow contract's `credential_source: proxied` is sufficient evidence of self-hosted routing.

### 7. Governance hooks as access-control evidence

The existing hard governance hooks (`secret-detector`, `destructive-git-blocker`, `lethal-trifecta-gate`, `safe-worktree-remove`, `concurrent-write-guard`) already produce `audit_class: access_control` rows via the hook timing and audit trail infrastructure. No change to these hooks is required. This ADR formally classifies their output as `access_control` evidence for SOC 2 CC6.

Each hook that fires (pass or block) MUST produce an `agent-audit-trail.jsonl` row with `audit_class: access_control` and `outcome: pass|block`. Hooks that currently do not produce such rows gain this as a backlog item; the gap is not blocking for first-flow deployment but MUST be closed before a flow is promoted to `default-on`.

### 8. Schema extension to ADR-138

```yaml
tenant_id: "<flow_id>-<launch-timestamp>"  # populated at worker launch time
audit_class: access_control|change_management|availability|processing_integrity|confidentiality|privacy|sync
```

`audit_class` in the flow contract is the *minimum expected class* for this flow's audit rows. A flow that only produces `processing_integrity` rows when it also writes files is considered under-instrumented.

## Relationship to existing ADRs

| ADR | Relationship |
|---|---|
| [ADR-033](ADR-033-harness-agnostic-event-capture.md) | **Foundation.** Canonical event capture schema. ADR-142 adds compliance-specific fields (`audit_class`, `tenant_id`) on top of the existing schema. |
| [ADR-088](ADR-088-provenance-trailer-ppid-chain.md) | **Complements.** Provenance chain is the change-management evidence. ADR-142 classifies it as `audit_class: change_management`. |
| [ADR-094](ADR-094-agent-git-safety.md) | **Contributes.** Git safety gates produce `access_control` evidence. |
| [ADR-139](ADR-139-account-agnostic-multi-provider-runtime.md) | **Feeds.** `billing_identity` and provider call rows are `audit_class: processing_integrity`. |
| [ADR-141](ADR-141-engram-cloud-cross-instance-replication.md) | **Feeds.** Sync audit rows (§8 of ADR-141) land in `agent-audit-trail.jsonl` as `audit_class: sync`. |
| [ADR-138](ADR-138-flow-contract-schema.md) | **Extended.** Two new fields: `tenant_id`, `audit_class`. |

## Acceptance Criteria

1. Every audit row produced by a cloud worker flow carries `tenant_id` and `audit_class`.
2. A flow running in `local-only` Engram mode produces all required audit rows without any network call.
3. `scripts/cos-audit-archive` exists and compresses rows older than a configurable window without deleting them (dry-run tested).
4. The GDPR erasure procedure is documented in `docs/architecture/gdpr-erasure-procedure.md` (created lazily when the first flow enters `advisory` state).
5. The `audit_class` enumeration is added to the ADR-138 flow contract schema; CI rejects a flow contract missing the field.

## Border Cases

- **A flow that does not write to the repo** (documentation-only flow). Produces `processing_integrity` rows (LLM calls) but no `change_management` rows. Acceptable; the instrumentation requirement is per-class, not exhaustive.
- **Air-gapped deployment with no git access.** The operator appends audit rows locally. The audit surface is the local JSONL files; git commits are not required for the audit to be valid, only for the cross-device sync path.
- **SOC 2 auditor requires log immutability.** The append-only JSONL model provides soft immutability. An operator that requires cryptographic immutability (hash-chained logs) implements this at the filesystem or storage layer; COS does not provide it natively. The `scripts/cos-audit-archive` helper can pipe rows to an immutable storage backend as an operator extension.
- **GDPR erasure request for a git-history observation.** COS documents the `git filter-repo` path but does not automate it. The operator accepts responsibility for history rewriting; COS records the erasure event in the audit trail.
- **A flow running multiple workers with the same `flow_id`** (parallel execution). Each worker uses a distinct `tenant_id` (`flow_id + launch-timestamp`). Parallel workers do not share a tenant namespace.

## Consequences

**Positive.**

- The existing JSONL audit signal — already produced, already committed to git — becomes compliance-queryable with the addition of two fields per row. No new infrastructure is required for air-gap deployments.
- `tenant_id` closes the concurrent-flow attribution gap: operators can filter all audit rows for a single flow execution without ambiguity.
- The GDPR erasure path is documented and auditable (erasure records in the audit trail). COS does not need to be a GDPR processor to enable operator compliance.

**Negative / risk.**

- Adding `tenant_id` and `audit_class` to every row is a schema change. Existing rows without these fields are classified as `maintainer` tenant and `audit_class: change_management` by default during migration queries — a reasonable but not guaranteed interpretation.
- SOC 2 Type II requires *continuous* evidence over a 6–12 month audit period. COS provides the append-only JSONL; the operator must not rotate or truncate it during the audit window. `scripts/cos-audit-archive` is the mitigant, not a substitute for operator discipline.
- GDPR erasure from git history is irreversible and outside COS scope. The documentation in §5 is guidance; misapplication by an operator is not a COS defect.

**Of not making this commitment.**

- Cloud worker flows produce per-flow JSONL in different formats and locations. Cross-flow compliance queries require per-flow parsing. The air-gap deployment is undocumented and must be re-derived by each operator. The GDPR erasure path is undocumented.

## Cross-references

- [ADR-033](ADR-033-harness-agnostic-event-capture.md) — canonical event capture; `audit_class` and `tenant_id` are additive fields.
- [ADR-088](ADR-088-provenance-trailer-ppid-chain.md) — provenance chain; `change_management` evidence.
- [ADR-138](ADR-138-flow-contract-schema.md) — flow contract schema; new fields defined here.
- [ADR-139](ADR-139-account-agnostic-multi-provider-runtime.md) — credential and billing audit rows; `processing_integrity` class.
- [ADR-141](ADR-141-engram-cloud-cross-instance-replication.md) — Engram sync audit rows; `sync` class.
- `hooks/git-commit-scope-guard.sh` — confirms `.cognitive-os/runtime/agent-audit-trail.jsonl` as the canonical audit file.
- [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md) — the plan whose audit-trail signal this ADR formalises.

## Alternatives rejected

- Leave the ADR without an alternatives section — rejected because ADR-067+ audit contracts require a falsifiable record of considered options.

## Verification

```bash
python3 -m pytest tests/unit/test_cos_engram_cloud_enroll_and_audit_archive.py tests/audit/test_adr_139_141_142_cloud_surfaces.py tests/audit/test_flow_contract_schema.py -q
```

## Implementation Evidence

- Implemented in `docker/cos-worker/entrypoint.sh`: cloud-worker audit rows carry `tenant_id`, `audit_class`, credential source, billing identity, and Engram project scope.
- Implemented in `scripts/cos-engram-cloud-enroll` and `scripts/engram-sync.sh`: Engram Cloud enrollment/sync rows use `audit_class: sync` and `tenant_id`.
- Implemented in `scripts/cos-audit-archive`: old audit rows are copied into gzip archives without truncating or deleting the source JSONL.
- Implemented in `docs/architecture/gdpr-erasure-procedure.md`: GDPR erasure workflow and required privacy audit row shape.
- Validated by `tests/unit/test_cos_engram_cloud_enroll_and_audit_archive.py`, `tests/audit/test_adr_139_141_142_cloud_surfaces.py`, and `tests/audit/test_flow_contract_schema.py`.
