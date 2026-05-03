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

## Integration with existing COS subsystems

ACC is additive. It MUST consume the registries and audit surfaces the host system already maintains, not re-discover or replace them. Each integration is exposed as an adapter with an explicit input → canonical-output contract.

| Existing subsystem | Source path / handle | Adapter role | Canonical output |
|---|---|---|---|
| Skill registry | `.atl/skill-registry.md` (project) plus global skills index | Skill discovery and representation | `kind: skill` entries in `C_represented` |
| Rules index | `rules/RULES-COMPACT.md` plus `rules/*.md` | Rule discovery and representation | `kind: rule` entries in `C_represented` |
| Hooks profile | `scripts/apply-efficiency-profile.sh` plus `hooks/*.sh` | Hook discovery; profile tier (lean/standard/full) and lifecycle phase as metadata | `kind: hook` entries in `C_represented` |
| Engram persistent memory | `mem_save` / `mem_search` API | Manifest storage, evidence persistence, drift history | Storage layer (see "Storage and persistence") |

Adapter contracts:

- **Read-only.** Adapters MUST NOT mutate the source registry. ACC reflects state; it does not edit it.
- **Deterministic.** Two runs against the same registry revision MUST yield the same canonical output.
- **Provenance-preserving.** Every emitted entry MUST cite its source path, symbol or anchor, and the registry revision used.
- **Failure-isolated.** If an adapter fails, the affected domain MUST be reported as `unverified`, not silently dropped (see "Gate semantics").
- **No re-implementation.** When a registry exposes a parser, query API, or canonical accessor, the adapter MUST use it instead of re-parsing the underlying file.

The adapter set above is the minimum required for an ACC implementation hosted inside the Cognitive OS. Additional registries (workflow store, MCP tool catalog, prompt library) MAY be integrated via the same contract.

## Relationship to component-reality-check / aspirational_audit

The Cognitive OS already maintains a REAL / DORMANT / ASPIRATIONAL classification of components via `component-reality-check` (`scripts/aspirational_audit.py`). ACC subsumes this classification rather than running in parallel.

Subsumption rules:

- Every capability in the ACC manifest carries a `lifecycle_status` attribute with values `real`, `dormant`, or `aspirational`, sourced from the existing audit.
- `aspirational_audit.py` is refactored as a **discovery adapter** for ACC. It continues to expose its current CLI for backward compatibility, but its output is canonicalised through the adapter contract above and contributes to `C_total`, not to a separate report.
- `dogfood_score` (`scripts/dogfood_score.py`) consumes `acc_effective` and the breakdown of `lifecycle_status` as input signals. It does not re-derive them.
- `component-reality-check` remains the user-facing command for the lifecycle question; ACC remains the user-facing surface for the coverage question. Both render from the same underlying manifest.

Migration contract:

- **Reconstruction phase**: `aspirational_audit` and ACC may coexist as separate entry points. Discrepancies between the two MUST be logged but do not block.
- **Production phase**: `aspirational_audit` runs only as an internal adapter. Its standalone report is generated from the ACC manifest, not from a parallel scan. Discrepancies block.
- The migration boundary is declared in the project phase configuration, not hard-coded in ACC.

This relationship prevents two languages for the same fact: lifecycle status is owned by the audit; coverage status is owned by ACC; both share one manifest.

## Storage and persistence

ACC has four persistence layers with distinct purposes. Mixing them silently is an anti-pattern.

| Layer | Location | Purpose | Mutability |
|---|---|---|---|
| Canonical manifest | Engram, topic key `acc/{project}/manifest` | Single source of truth for current capability state. Versioned by engram. | Mutable, incremental |
| Reviewable snapshot | `docs/acc/acc-{revision}.json` and `acc-{revision}.md` | Human review, PR diffing, CI artefact. Generated from the canonical manifest. | Append-only |
| Drift ground truth | `docs/acc/latest.json` (symlink to most recent snapshot) | Last committed manifest used to compute drift when engram is unavailable. | Updated by snapshot generator |
| Historical evidence | Engram, topic key `acc/{project}/findings/{capability_id}` | Per-capability trace of status transitions, mapping changes, and adapter provenance. | Append-only |

Rationale:

- **Engram as canonical** allows incremental mutation and search without committing every adapter run. Coverage state changes on every meaningful edit; storing each delta in git would generate constant churn with no review value.
- **Snapshots as reviewable artefacts** give PRs a diffable surface and let reviewers see "what changed in coverage" without an engram client. They are reports, not truth.
- **`latest.json` as drift baseline** means ACC can compute drift in environments where engram is degraded or unavailable (CI runners, fresh clones), preserving the gate's usefulness offline.
- **Per-capability evidence in engram** preserves the audit trail without bloating the manifest. Reviewers consult it on demand via `mem_search`.

Implementations MAY add caches or indexes, but the four layers above are normative. The snapshot generator MUST be deterministic given a manifest revision, so identical manifests produce identical snapshots.

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
9. The document declares explicit integration with the host system's skill registry, rules index, hooks profile, and engram memory, with a read-only adapter contract for each.
10. The document declares the relationship to `component-reality-check` and `aspirational_audit`, including the subsumption rule and the reconstruction-vs-production migration contract.
11. The document defines a primary canonical store (engram), a reviewable snapshot store (`docs/acc/`), a drift baseline (`docs/acc/latest.json`), and a per-capability evidence store (engram), with their mutability and purpose.

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
- the ACC manifest example includes `mapping_status`, `confidence`, and `evidence`;
- the ACC doc contains a section titled `Integration with existing COS subsystems` referencing skill registry, rules index, hooks profile, and engram;
- the ACC doc contains a section titled `Relationship to component-reality-check / aspirational_audit` declaring the subsumption rule;
- the ACC doc contains a section titled `Storage and persistence` declaring engram as canonical, `docs/acc/` as snapshot store, and `docs/acc/latest.json` as drift baseline;
- the ACC doc references `lifecycle_status` as a capability attribute.

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

## Surfaces

### CLI: `cos-coverage`

Prints ACC metrics in real-time. Backed by a 30-second cache so p95 stays well under 300 ms.

```
# Human summary (default)
bash scripts/cos-coverage

# Machine-readable JSON
bash scripts/cos-coverage --json

# One-line statusline output
bash scripts/cos-coverage --brief

# Force cache refresh
bash scripts/cos-coverage --refresh
```

**Output fields (--json)**:
- `coverage_pct` — REAL / (REAL + DORMANT + ASPIRATIONAL) * 100
- `real`, `dormant`, `aspirational`, `on_demand`, `metadata` — component counts from `aspirational-audit.jsonl`
- `mapped`, `weak_proof`, `unmapped` — claim-proof counts from `docs/reports/claim-proof-latest.md`
- `tiers` — tier counts A/B/C/D from `cos_classify_coverage.py`
- `trend` — delta arrows vs last daily snapshot (`up` / `down` / `flat`)
- `generated_at` — UTC timestamp of snapshot

**Cache**: `.cognitive-os/runtime/coverage-snapshot.json` (TTL 30 s).
**History**: each invocation appends a daily snapshot to `.cognitive-os/metrics/coverage-history.jsonl` for trend tracking.

### Statusline segment: `statusline-coverage.sh`

Opt-in statusline segment that reads the cache file only — no live computation, latency < 50 ms.

```
# Zsh/bash: append to PS1
export PS1='$(bash scripts/statusline-coverage.sh) '$PS1

# Tmux status-right (add to ~/.tmux.conf)
set -g status-right '#(bash /path/to/luum-agent-os/scripts/statusline-coverage.sh)'
set -g status-interval 30
```

When the cache is fresh (≤ 5 min) the output is:

```
ACC: 54.0%↑ | REAL: 235 DORM: 160
```

When the cache is absent or stale (> 5 min):

```
ACC: ? (run cos-coverage to refresh)
```

Environment override: `COS_COVERAGE_STALE_MAX=<seconds>` (default 300).
