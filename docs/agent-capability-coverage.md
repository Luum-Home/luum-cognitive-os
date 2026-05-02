# Agent Capability Coverage (ACC)

## Status

- **Type:** Architecture specification
- **Scope:** Cognitive OS core contract plus optional ecosystem adapters
- **Phase:** reconstruction
- **Audience:** maintainers, adapter authors, governance/test authors

## Thesis

Agent Capability Coverage (ACC) measures how completely the real capabilities of a software system are represented in the agentic primitives an AI coding agent can discover, reason about, and invoke.

The operating premise is:

> If a capability is not structurally modeled, an agent cannot use it predictably, securely, or efficiently.

ACC is not a replacement for unit test coverage, SAST, runtime observability, or agent evaluation. It measures a different gap: the structural alignment between the system that exists and the system represented to agents.

## Problem

Modern agentic workflows can execute tools, follow skills, delegate to subagents, call MCP servers, read rules, and apply hooks. These mechanisms are useful only when they accurately represent the real system.

A coverage gap appears when the codebase contains a capability that is absent, stale, partially represented, or overexposed in the agentic layer. Consequences include:

- duplicated scripts around existing native functionality;
- hallucinated APIs, parameters, or workflows;
- stale business rules applied by the agent;
- excessive token spend from search-and-guess loops;
- unsafe tool use because policy and runtime hooks do not cover the capability surface.

## Definitions

### Capability

A **capability** is a behavior, interface, rule, or operational path that a project can perform and that may affect code, data, infrastructure, governance, or user-visible behavior.

Canonical capability kinds:

| Kind | Examples | Discovery signal |
|---|---|---|
| `endpoint` | REST, GraphQL, gRPC route | router registration, decorator, schema |
| `event` | Kafka topic, queue producer/consumer, webhook | subscription or publisher registration |
| `job` | cron, scheduled task, batch runner | scheduler config, hook, command |
| `integration` | Stripe, GitHub, Supabase, Vercel client | SDK/client wrapper, adapter package |
| `business_rule` | fraud check, authorization rule, pricing constraint | domain function, policy file, decision table |
| `workflow` | multi-step domain process | workflow graph, orchestrator definition |
| `hook` | pre-tool, post-tool, session, stop gate | lifecycle hook file or config |
| `skill` | procedural domain knowledge | `SKILL.md`, agent skill registry |
| `rule` | governance rule or project instruction | rules docs, policy manifests, AGENTS.md |

### Real capability set

`C_total` is the weighted set of capabilities discovered from the real system.

Sources may include source code, tests, infrastructure manifests, hook configs, skills, rules, generated schemas, package metadata, and runtime registries when available.

### Represented capability set

`C_represented` is the weighted subset of `C_total` represented to agents through agentic primitives such as tools, skills, workflows, hooks, rules, MCP schemas, structured prompts, and local memory indexes.

### Mapping

A mapping links one real capability to one or more represented capabilities and classifies its alignment.

Mapping statuses:

| Status | Meaning |
|---|---|
| `aligned` | Representation exists and matches the real capability contract. |
| `missing` | Real capability exists but is not represented. |
| `partial` | Representation exists but omits important parameters, constraints, or flow steps. |
| `stale` | Representation conflicts with current code or policy. |
| `overexposed` | Representation grants agent access beyond the safe or intended surface. |
| `unverified` | Candidate mapping exists but confidence is below the audit threshold. |

## Metric

ACC is a weighted coverage ratio:

```text
ACC = sum(weight(c) for c in C_total where status(c) == aligned)
      / sum(weight(c) for c in C_total)
```

A stricter operational score should penalize stale and overexposed mappings:

```text
ACC_effective = (
  aligned_weight
  + 0.5 * partial_weight
  - stale_penalty
  - overexposed_penalty
) / total_weight
```

The exact weights are project-configurable. The portable contract requires that every report disclose the weights used.

Suggested default weights:

| Capability kind | Default weight | Rationale |
|---|---:|---|
| `business_rule` | 5 | High hallucination and domain-risk impact. |
| `endpoint` | 4 | Direct state-changing surface. |
| `workflow` | 4 | Multi-step failure risk. |
| `integration` | 4 | External data, auth, and cost risk. |
| `event` | 3 | Async side effects are often hidden. |
| `job` | 3 | Scheduled mutation can surprise agents. |
| `hook` | 3 | Safety enforcement surface. |
| `rule` | 2 | Governance and instruction alignment. |
| `skill` | 2 | Procedural representation. |

## Core Portable Contract

The Cognitive OS core must remain provider-neutral and repository-host neutral. ACC core therefore defines contracts, not vendor-specific implementations.

### 1. Capability manifest

An ACC implementation emits a machine-readable manifest:

```yaml
schema_version: acc.v1
project:
  name: example-project
  revision: git-or-provider-revision
weights:
  business_rule: 5
  endpoint: 4
capabilities:
  - id: endpoint:create-order
    kind: endpoint
    source:
      path: services/orders/routes.ts
      symbol: POST /orders
    risk: high
    signature:
      input: CreateOrderRequest
      output: Order
      side_effects: [database_write, payment_intent]
    represented_by:
      - kind: tool
        id: mcp.orders.create_order
        source: mcp://orders/tools/create_order
    mapping_status: aligned
    confidence: 0.94
    evidence:
      - exact route/schema match
      - matching tool input schema
```

Required fields per capability:

- `id`
- `kind`
- `source`
- `risk`
- `signature`
- `represented_by`
- `mapping_status`
- `confidence`
- `evidence`

### 2. Report format

An ACC run emits both:

- `acc.json` for CI and automation;
- `acc.md` for human review.

Minimum JSON fields:

```json
{
  "schema_version": "acc.report.v1",
  "acc": 0.82,
  "acc_effective": 0.76,
  "total_weight": 100,
  "aligned_weight": 82,
  "partial_weight": 6,
  "stale_weight": 4,
  "overexposed_weight": 2,
  "thresholds": {
    "minimum_acc": 0.75,
    "minimum_effective_acc": 0.70,
    "critical_missing_allowed": 0
  },
  "findings": []
}
```

### 3. Gate semantics

ACC gates should be deterministic and configurable.

Default gate outcomes:

| Condition | Default outcome |
|---|---|
| Critical capability is `missing`, `stale`, or `overexposed` | block |
| `ACC_effective` below configured threshold | block |
| New capability has no mapping evidence | warn in reconstruction, block in production |
| Low-confidence semantic match | warn |
| Adapter unavailable | degrade gracefully and mark affected domains `unverified` |

### 4. Portability boundaries

Core ACC must not require:

- GitHub or GitHub Actions;
- a specific LLM provider;
- a specific agent framework;
- a specific MCP registry;
- a specific language parser;
- a hosted SaaS scanner.

Provider-specific systems may implement adapters, but the core contract must remain portable.

## Optional Adapters

Adapters discover capabilities or representations and translate them into the core manifest.

### Static code adapters

| Adapter | Role | Notes |
|---|---|---|
| TypeScript AST | Discover routes, exports, schemas, workflows | May use `ts-morph`, TypeScript compiler API, or dependency graph tools. |
| Go AST | Discover `net/http`, command, client, and package contracts | Should prefer `go/ast`, `go/types`, and module metadata. |
| Python AST | Discover FastAPI/Flask routes, Pydantic schemas, jobs | Should avoid executing untrusted project code. |
| IaC scanner | Discover queues, topics, cloud resources | Terraform, CDK, Kubernetes, Helm, Pulumi. |

### Representation adapters

| Adapter | Role | Notes |
|---|---|---|
| MCP | Read tool names, descriptions, and input schemas from `tools/list`. | Useful for `C_represented`, not sufficient for `C_total`. |
| Skills | Parse `SKILL.md` frontmatter and procedural sections. | Must preserve progressive-disclosure semantics. |
| Rules | Parse governance docs, AGENTS.md, `.claude/rules`, and projected rules. | Must distinguish always-active rules from contextual rules. |
| Hooks | Read lifecycle hooks and projected settings. | Should classify hook phase and enforcement mode. |
| Workflows | Read declarative workflow graphs or orchestrator code. | Framework-specific adapters belong outside core. |

### Ecosystem references

These tools can inform adapters, but they are not core dependencies:

| Tool or project | Useful for | Boundary |
|---|---|---|
| Figra (`@neabyte/figra`) | TypeScript import/export graph and alias-aware dependency mapping. | Discovery helper only; does not define ACC semantics. |
| PydanticAI | Typed Python tool/output contracts. | Optional Python representation adapter. |
| VoltAgent | TypeScript workflows and Zod schemas. | Optional TypeScript workflow adapter. |
| Microsoft Agent Governance Toolkit | Runtime policy enforcement patterns. | Optional governance reference; do not bind core to it. |
| SWE-CI | CI-loop benchmark inspiration. | Evaluation reference, not ACC mapping logic. |
| Deterministic AST hallucination correction research | API/identifier hallucination validation pattern. | Useful for stale/hallucinated mapping checks. |
| AI SAST vendors | Market signal for semantic code review. | Vendor scanners are optional inputs, not trusted core truth. |

## Pipeline

### Phase 1: Discover real capabilities

Input: source tree, configuration, tests, infrastructure manifests, package metadata.

Output: `C_total` candidates with source evidence.

Rules:

- Prefer deterministic static analysis.
- Do not execute untrusted project code to discover capabilities.
- Mark inferred business rules with lower confidence unless supported by tests or policy files.
- Keep all source paths and symbols in the manifest for auditability.

### Phase 2: Discover represented capabilities

Input: agentic primitives, tool registries, skills, rules, hooks, workflows, MCP servers, prompts, memory indexes.

Output: `C_represented` candidates with representation evidence.

Rules:

- Treat tool schemas as contracts, not prose.
- Distinguish executable tools from instructional knowledge.
- Distinguish local project primitives from globally installed user primitives.
- Record adapter provenance.

### Phase 3: Map and classify alignment

Input: `C_total`, `C_represented`.

Output: mapping statuses and findings.

Matching order:

1. exact id or declared link;
2. exact schema/signature match;
3. route/event/workflow structural match;
4. semantic similarity with confidence score;
5. human-reviewed override.

Semantic matches must not silently become `aligned`. If confidence is below the configured threshold, classify as `unverified`.

### Phase 4: Calculate, report, and gate

Input: mapping results and weights.

Output: `acc.json`, `acc.md`, CI/hook outcome.

Rules:

- Always disclose thresholds and weights.
- Show newly introduced gaps separately from existing debt.
- In reconstruction phase, warnings may be acceptable for non-critical gaps.
- In production phase, critical missing/stale/overexposed capabilities should block.

## Derived Coverage Dimensions

| Metric | Definition |
|---|---|
| Tool Coverage | State-changing or queryable real interfaces represented by executable tools with schemas. |
| Workflow Coverage | Multi-step business flows represented as declared workflows or skills with deterministic checkpoints. |
| Rule Coverage | Business and governance constraints represented as explicit rules or policies. |
| Hook Coverage | Lifecycle interception coverage for risky agent actions. |
| Prompt Surface Coverage | Fraction of relevant represented capabilities available to the agent without overloading context. |
| Drift Coverage | Fraction of changed real capabilities that trigger representation updates or warnings. |

## Risks and Anti-Patterns

| Risk | Mitigation |
|---|---|
| Counting every function as a capability | Restrict capabilities to externally relevant, domain, governance, or side-effecting surfaces. |
| Treating documentation as truth | Require source evidence and representation evidence. |
| Overexposing every tool to improve coverage | Track `overexposed` separately and penalize it. |
| Vendor lock-in | Keep core manifest and gates independent from adapters. |
| False semantic matches | Require confidence thresholds and evidence. |
| Formula without explainable weights | Disclose weights and allow project overrides. |

## Acceptance Criteria

A compliant ACC specification implementation must satisfy:

1. `docs/agent-capability-coverage.md` contains no embedded formula images.
2. All ACC formulas are represented as searchable text.
3. The document uses **agentic primitives** terminology for the agentic layer.
4. The document separates **Core Portable Contract** from **Optional Adapters**.
5. The core contract does not require GitHub, a specific LLM provider, a specific agent framework, or a SaaS scanner.
6. A generated report includes `acc`, `acc_effective`, thresholds, weights, findings, and evidence.
7. Critical `missing`, `stale`, or `overexposed` capabilities produce deterministic gate outcomes.
8. Adapter failure degrades to `unverified` evidence rather than pretending full coverage.

## Future Test Contract

A future audit test should enforce the documentation and portability contract:

```text
tests/audit/test_agent_capability_coverage_doc.py
```

Suggested assertions:

- the ACC doc contains `Core Portable Contract`;
- the ACC doc contains `Optional Adapters`;
- the ACC doc contains `ACC =` as text;
- the ACC doc does not contain embedded base64 image formulas;
- the ACC doc uses `agentic primitives`;
- the ACC doc does not introduce vendor-specific tools as core requirements;
- the ACC manifest example includes `mapping_status`, `confidence`, and `evidence`.

A later behavior test can validate a small fixture repository:

```text
tests/behavior/test_agent_capability_coverage_mapping.py
```

Fixture scenario:

- one real endpoint with a matching tool -> `aligned`;
- one real job with no representation -> `missing`;
- one represented tool whose schema no longer matches the endpoint -> `stale`;
- one tool exposing broader access than the real safe contract -> `overexposed`.

Expected result:

```text
critical_missing_allowed = 0
ACC_effective < threshold
outcome = block
```

## References

- Model Context Protocol documentation: tool discovery and schemas.
- PydanticAI documentation: typed outputs, tool arguments, and validation context.
- VoltAgent documentation: Zod-backed workflows and subagent orchestration.
- Microsoft Agent Governance Toolkit announcement and repository: runtime policy enforcement reference.
- SWE-CI paper: CI-loop framing for repository-level agent evaluation.
- arXiv 2601.19106: deterministic AST validation for hallucinated code APIs.
- Figra package metadata: TypeScript dependency graph and alias-aware import/export analysis.
