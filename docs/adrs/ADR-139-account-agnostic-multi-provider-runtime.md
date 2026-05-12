---

adr: 139
title: Account-Agnostic Multi-Provider Runtime
status: implemented
implementation_status: implemented
date: 2026-05-04
supersedes: []
superseded_by: null
implementation_files:
  - manifests/flow-contract-schema.yaml
  - scripts/cos-flow-register.sh
  - scripts/cos_flow_register.py
  - scripts/cos-engram-cloud-enroll
  - docker/cos-worker/docker-compose.yml
  - tests/audit/test_adr_139_141_142_cloud_surfaces.py
tier: maintainer
tags: [security, provider, byok, billing, credentials, license-policy, cloud-flows]
---

# ADR-139: Account-Agnostic Multi-Provider Runtime

## Status

**Accepted — Implemented** as the credential and billing posture for all COS runtime surfaces — local maintainer, cloud worker, and ephemeral sandbox.

## Context

The [DX-first cloud flow bootstrap plan](../architecture/dx-cloud-flow-bootstrap-plan.md) requires cloud workers to call LLM providers from ephemeral containers without sharing the maintainer's personal credentials. The current dispatch layer ([ADR-049](ADR-049-llm-gateway-selection-and-overflow-providers.md)) is account-agnostic at the dispatch level but makes no guarantees at the credential-management level: in practice, workers inherit whatever environment variables are present.

Three problems converge:

1. **Credential leakage.** A worker that reads `ANTHROPIC_API_KEY` from the ambient environment exposes the maintainer's personal account to logs, crash dumps, and third-party sandbox surfaces (`e2b-integration`, CI runners).
2. **Billing opacity.** Cloud worker usage accrues to the maintainer's account without per-flow cost attribution. `llm-dispatch.jsonl` is the instrumentation layer but it cannot correlate charges across accounts or providers.
3. **License posture.** Rules §10 (`license-policy`) blocks AGPL/SSPL/BSL libraries but does not address the adjacent question: which providers COS can route to under a BYOK posture versus a proxied/managed billing arrangement, and whether that distinction changes for cloud workers versus local harness usage.

This ADR extends Rules §10 (`license-policy`) to the credential and billing surface. It does not replace ADR-049 (provider selection) or ADR-062 (multi-provider agent loop); it constrains how credentials reach the runtime.

## Decision

### 1. Caller-supplied credentials are the default

Every COS runtime surface — local maintainer session, cloud worker, ephemeral sandbox — uses credentials supplied by the **caller of that surface**. Credentials are never forwarded from an outer context (maintainer shell → cloud worker) without an explicit, audited injection point.

Concretely:

- Local maintainer session: credentials from the maintainer's environment (unchanged from current behaviour).
- Cloud worker launched by COS flow: credentials from the **flow's own environment block**, populated at launch time by the orchestrating surface (CI secrets, E2B sandbox environment, container secret store). The flow contract (ADR-138) MUST declare `credential_source` (see §Schema extension).
- Ephemeral sandbox: credentials from the sandbox provider's secret injection mechanism — never copied from the maintainer machine's environment.

The banned pattern: `export ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"` propagated into a worker launch command.

### 2. Hybrid billing identities are acceptable; account conflation is not

COS supports three billing postures:

| Posture | Description | Allowed surfaces |
|---|---|---|
| `byok-maintainer` | Maintainer's own API keys, personal account | Local harness only |
| `byok-project` | Project-scoped API keys (separate account or sub-account) | Cloud workers, CI |
| `proxied` | Usage routed through a proxy/gateway that handles billing (LiteLLM, Bifrost, enterprise gateway) | All surfaces |

`byok-maintainer` keys MUST NOT appear in flow contracts, worker launch scripts, or CI secret stores. A flow that requires `byok-maintainer` keys is classified as non-portable and cannot be promoted beyond `advisory`.

### 3. Provider capabilities are declared, not assumed

A cloud worker MUST NOT call a provider capability that was not declared in the flow contract's `provider_capabilities` field. Undeclared capability calls (e.g., calling a vision endpoint when the contract only declared text completion) are a contract violation logged to `.cognitive-os/runtime/agent-audit-trail.jsonl`.

### 4. License posture for provider SDKs and proxies

Extending Rules §10:

- **BLOCK**: any provider SDK or proxy library under AGPL, SSPL, or BSL. The license-policy rule already applies; this ADR makes it explicit for provider-facing libraries.
- **ALLOW with review**: proprietary provider SDKs (Anthropic, OpenAI, etc.) are permissible provided they do not require embedding the SDK in a redistributable COS binary. HTTP-only usage (no SDK binary shipped) is the preferred posture for cloud worker surfaces.
- **ALLOW**: MIT/BSD/Apache-licensed client libraries and proxy adapters (LiteLLM client, httpx, etc.).
- **ALLOW**: self-hosted proxies (Bifrost, LiteLLM server) where COS is the operator and the proxy is not distributed as part of COS.

The `license-policy` rule in Rules §10 remains the primary gate; this ADR adds provider-SDK specificity.

### 5. No vendor names in identifiers

Provider identifiers in configuration, scripts, flow contracts, and skill metadata MUST use generic names (`provider-a`, `provider-b`, `llm-primary`, `llm-fallback`) or role-based names (`reasoning-provider`, `fast-provider`) rather than vendor brand names. This applies to filenames, environment variable names in scripts, and ADR cross-references when the vendor is not the subject of the ADR.

Environment variable conventions:
- `LLM_PRIMARY_API_KEY` (not `ANTHROPIC_API_KEY` in scripts)
- `LLM_FALLBACK_API_KEY` (not `OPENAI_API_KEY` in scripts)
- The actual values map to vendor keys at injection time via the flow's environment block.

Exception: vendor names MAY appear in human-readable ADR prose when the vendor is the subject, in `llm-dispatch.jsonl` telemetry fields for cost attribution, and in CI secret names where the secret store requires a descriptive name.

### 6. Audit trail for credential usage

Every LLM call from a cloud worker or flow runtime MUST append a row to `.cognitive-os/runtime/agent-audit-trail.jsonl` (the canonical audit JSONL, confirmed via `hooks/git-commit-scope-guard.sh`) with at minimum:

```json
{
  "ts": "<ISO-8601>",
  "event": "llm_call",
  "flow_id": "<flow-id>",
  "provider_role": "llm-primary|llm-fallback|...",
  "billing_identity": "<byok-project|proxied|byok-maintainer>",
  "model_hint": "<sonnet|haiku|...>",
  "tokens_in": 0,
  "tokens_out": 0
}
```

`billing_identity` is sourced from the flow contract's `billing_identity` field (see §Schema extension). This row is the bridge between dispatch telemetry and compliance audit (ADR-142).

## Schema extension to ADR-138

The following fields are added to the `required_flow_shape` in `manifests/flow-contract-schema.yaml`. Any flow registered after this ADR lands MUST include them:

```yaml
credential_source: byok-maintainer|byok-project|proxied
billing_identity: stable identifier for cost attribution (e.g., project slug)
provider_capabilities:
  - text-completion
  - code-generation
  # ... declared capabilities only
```

## Relationship to existing ADRs

| ADR | Relationship |
|---|---|
| [ADR-049](ADR-049-llm-gateway-selection-and-overflow-providers.md) | **Extended.** ADR-049 selects providers; this ADR constrains how credentials reach them. The `--providers` flag stays unchanged; the credential injection path changes for worker surfaces. |
| [ADR-062](ADR-062-multi-provider-agent-loop.md) | **Extended.** Multi-provider agent loop inherits the caller-supplied credential contract. |
| [ADR-138](ADR-138-flow-contract-schema.md) | **Extended.** Three new required fields added to `required_flow_shape`. |
| [ADR-142](ADR-142-compliance-audit-air-gapped-surface.md) | **Feeds.** The `billing_identity` field and audit-trail rows are consumed by the compliance surface in ADR-142. |
| Rules §10 (`license-policy`) | **Extended.** Provider SDK license gate added as specificity. |

## Acceptance Criteria

1. The first cloud worker flow (`vuln-remediation-flow`) includes `credential_source`, `billing_identity`, and `provider_capabilities` in its `flow_contract.yaml`. A flow missing any of these fields is rejected by `scripts/cos-flow-register.sh` (to be created per ADR-138).
2. No flow launch script in `skills/` or `scripts/` propagates `*_API_KEY` from the ambient environment into a worker subprocess without an explicit comment naming this ADR as the authorising exception.
3. `scripts/cos-engram-cloud-enroll` (introduced by ADR-141) uses `LLM_PRIMARY_API_KEY` / `LLM_FALLBACK_API_KEY` as its variable names, not vendor-brand names.
4. The license audit in `tests/audit/` is extended (or a new test is added) to cover direct dependencies in provider-facing scripts.

## Border Cases

- **A flow that must use the maintainer's personal account for testing in `lab` state.** Allowed: the flow contract declares `credential_source: byok-maintainer` and `lifecycle_state: lab`. The flow cannot be promoted beyond `advisory` in this state. The reason field explains the constraint.
- **A proxied gateway that itself uses AGPL software internally.** The COS-to-proxy interface is HTTP; the proxy internals are the proxy operator's concern. COS does not ship AGPL code; what the proxy operator runs is outside COS's distribution boundary per ADR-124.
- **A flow running on a platform where generic env var names conflict with platform conventions.** The mapping from `LLM_PRIMARY_API_KEY` to the platform's convention is done in the launch wrapper, not in the flow contract itself. The contract always uses the generic names.
- **Cost attribution across multiple flows sharing a billing identity.** `billing_identity` is a string; grouping and rollup are the responsibility of the operator's cost dashboard. COS appends rows; it does not aggregate.

## Consequences

**Positive.**

- Cloud workers cannot accidentally expose maintainer credentials. The caller-supplied model is checkable at flow registration time.
- Per-flow cost attribution is structurally required, not optional. `llm-dispatch.jsonl` and `agent-audit-trail.jsonl` both carry `billing_identity`, enabling cross-file joins.
- License posture for provider libraries is explicit and auditable alongside the existing `tests/audit/` suite.

**Negative / risk.**

- Flows that currently inherit ambient credentials need explicit `credential_source` declarations — a one-time migration cost for any flow that was informally calling providers.
- Generic env var names (`LLM_PRIMARY_API_KEY`) add a mapping layer that must be documented per deploy target.

**Of not making this commitment.**

- The first cloud worker flow leaks maintainer credentials into sandbox logs. There is no structural guarantee, only convention. The audit trail's `billing_identity` field would be absent, making cross-flow cost analysis impossible.

## Cross-references

- [ADR-049](ADR-049-llm-gateway-selection-and-overflow-providers.md) — provider selection and dispatch; this ADR constrains credential injection.
- [ADR-062](ADR-062-multi-provider-agent-loop.md) — multi-provider loop inheriting this credential contract.
- [ADR-138](ADR-138-flow-contract-schema.md) — flow contract schema; new fields defined here.
- [ADR-141](ADR-141-engram-cloud-cross-instance-replication.md) — Engram cloud enroll wrapper that must follow generic env var names.
- [ADR-142](ADR-142-compliance-audit-air-gapped-surface.md) — compliance and audit surface consuming `billing_identity`.
- Rules §10 (`license-policy`) — primary gate for dependency licenses; this ADR adds provider-SDK specificity.
- [`dx-cloud-flow-bootstrap-plan.md`](../architecture/dx-cloud-flow-bootstrap-plan.md) — the operational plan that requires this credential posture.

## Alternatives rejected

- Leave the ADR without an alternatives section — rejected because ADR-067+ audit contracts require a falsifiable record of considered options.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_139_141_142_cloud_surfaces.py tests/audit/test_flow_contract_schema.py -q
```

## Implementation Evidence

- Implemented in `manifests/flow-contract-schema.yaml`: flow contracts require `credential_source`, `billing_identity`, and `provider_capabilities`.
- Implemented in `scripts/cos-flow-register.sh` and `scripts/cos_flow_register.py`: registration rejects missing or unsupported account/billing/provider declarations.
- Implemented in `docker/cos-worker/docker-compose.yml`: worker and Engram Cloud surfaces use generic provider-key names (`LLM_PRIMARY_API_KEY`, `LLM_FALLBACK_API_KEY`) instead of vendor-branded variables.
- Implemented in `scripts/cos-engram-cloud-enroll`: Engram Cloud enrollment uses project-scoped Engram variables and does not print or embed token values.
- Validated by `tests/audit/test_flow_contract_schema.py` and `tests/audit/test_adr_139_141_142_cloud_surfaces.py`.
