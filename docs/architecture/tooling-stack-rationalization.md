# Tooling Stack Rationalization

> Purpose: keep Cognitive OS sophisticated inside but lightweight, portable, and honest outside.

## Decision Frame

Cognitive OS should not become a bundle of heavyweight services by default. External tools are valuable only when they strengthen the product promise: make coding agents more governable, verifiable, and portable in real repositories.

Every tool must earn one of four positions:

| Position | Meaning | Default expectation |
|----------|---------|---------------------|
| Core dependency | Required for the minimum product promise. | Must be fast, local-first, tested by default CI, and hard to replace. |
| Compatibility adapter | Absorbs vendor/tool churn behind a stable Cognitive OS contract. | Must be swappable without changing user-facing workflows. |
| Optional extension | Adds power for teams that need it. | Must be opt-in, documented, and tested in explicit lanes. |
| Reference only | Useful as prior art or migration target, but not a runtime expectation. | Must not appear as a default product promise. |

## Current Infrastructure Posture

`cognitive-os.yaml` already encodes an important product decision:

| Tool | Current mode | Product role | Current conclusion |
|------|--------------|--------------|--------------------|
| LiteLLM | `pip` | Model gateway and provider compatibility. | Keep as optional gateway/runtime library, but route through capability profiles first. |
| Bifrost | `disabled` | Low-latency model gateway reference. | Keep as historical/reference material unless high-throughput latency becomes a validated requirement. |
| Langfuse | `disabled` | LLM observability reference stack. | Do not make default; too many dependent containers for first-run adoption. |
| MLflow | `pip` | Lightweight local experiment/metrics surface. | Keep as a lighter default observability candidate where it supports actual outcome metrics. |
| Opik | `cloud` | LLM tracing/evaluation platform. | Keep as optional/cloud extension; local backend is reference/CI only, not default core. |
| Valkey | `on_demand` | Agent bus/cache backend. | Keep as the only Redis-compatible backend. File fallback remains important for single-session use. |
| Cognee | `pip` | Memory/knowledge graph engine. | Keep optional; default behavior should not require an HTTP service. |
| MemU | `pip` | Memory extension. | Keep optional until a clear non-overlapping role versus Engram/Cognee is proven. |
| NeMo Guardrails | `pip` | Guardrail policy runtime. | Keep optional and in-process by default. |
| Paperclip | `on_demand` | Governance/compliance dashboard. | Keep as extension; not part of the minimum wedge unless backed by a visible operator workflow. |
| Jupyter | `pip` | Compute sandbox. | Keep optional; useful for data/ML tasks but not core agent governance. |
| Crawl4AI | `cli` | Research/web crawling extension. | Keep optional and task-triggered. |
| DeepEval/RAGAS/Promptfoo | package/skill surfaces | Evaluation and red-team tooling. | Keep as explicit evaluation extensions; avoid making every project install all of them. |

## Opik Specific Finding

Opik is useful, permissively licensed, and mature, but its local self-hosted platform is not lightweight. The official local deployment includes MySQL, Redis, ClickHouse, ZooKeeper, MinIO, backend, frontend, and supporting setup containers. That is appropriate for a full observability platform, but it is too heavy for the default Cognitive OS adoption path.

Therefore:

- Cognitive OS should not treat local Opik trace ingestion as a default core test.
- The reference backend may be health-checked in `testcontainers` lanes, but full trace ingestion must be tested either against the official full stack or against a configured cloud/local Opik endpoint.
- If we want a lightweight default observability path, it should use append-only JSONL outcome metrics plus a small local viewer/exporter before pulling in a full tracing platform.
- Opik should remain an optional extension for teams that need full tracing, evaluation dashboards, and provider-level observability.

This is not a rejection of Opik. It is a boundary: Opik can be a strong extension without becoming the operating system's center of gravity.

## Lighter Observability Alternatives To Evaluate

| Alternative | Why consider it | Concern |
|-------------|-----------------|---------|
| JSONL outcome metrics + local reports | Already aligned with Cognitive OS, zero service dependency, easy to test. | Needs better visualization and aggregation before it feels product-grade. |
| OpenTelemetry/OpenLIT-style instrumentation | Vendor-neutral and portable across backends. | Requires an OTEL collector/storage choice before it becomes useful to non-experts. |
| MLflow local mode | Lighter than Langfuse/Opik stacks and already configured as `pip`. | Not agent-native; may need adapters to express tool calls, quality gates, and outcome metrics well. |
| Langfuse | Strong all-in-one observability and cost tracing. | Heavy local stack; currently disabled by product contract. |
| Helicone/Portkey-style gateway observability | Useful when the LLM gateway is the control point. | Can pull Cognitive OS back toward model/vendor-centric architecture if not wrapped by capability profiles. |

## Product Rule For Future Tool Additions

Before adding or promoting a tool, answer these questions in the PR:

1. What user-facing product promise does this strengthen?
2. Is it core, compatibility, extension, or reference-only?
3. What lighter alternative was considered?
4. Can it run without Docker in the default developer path?
5. What is the smallest real test that proves the integration works?
6. What happens when the vendor/API changes?
7. Does this duplicate logic already provided by another component?

If a tool cannot pass this review, it can still be documented as research, but it should not move into runtime, CI, or first-run onboarding.

## Next Inventory Pass

The next pass should evaluate each non-core tool with the same rigor:

| Area | Tools to review | Priority |
|------|-----------------|----------|
| Observability | Opik, Langfuse, MLflow, OpenLIT, Helicone, AgentOps | High |
| Gateway/routing | LiteLLM, Portkey, Bifrost, gateway adapters | High |
| Memory | Engram, Cognee, MemU, file-backed memory | High |
| Guardrails/security | NeMo, LLM Guard, Guardrails AI, Promptfoo, Aguara, Semgrep, Parry | High |
| Evaluation | DeepEval, RAGAS, Promptfoo, outcome metrics | Medium |
| Compute/research | Jupyter, Crawl4AI, E2B-style sandboxes | Medium |
| Dashboards/control plane | Paperclip, dashboard surfaces, squads/organization views | Medium |

The goal is not to remove powerful tools. The goal is to make power composable: default light, extension-rich, and never confusing optional infrastructure with the kernel.
