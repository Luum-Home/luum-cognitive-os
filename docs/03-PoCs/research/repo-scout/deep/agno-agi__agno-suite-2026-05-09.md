---
evaluated_at: 2026-05-09
engram_id: pending
batch: targeted-post-reassessment
parent_radar: docs/06-Daily/reports/external-tools-radar-INDEX.md
repos:
  - agno-agi/agno
  - agno-agi/dash
  - agno-agi/scout
status: documentation-before-implementation
---

# Repository Evaluation: Agno Suite

## Scope

This targeted evaluation covers the Agno platform and two first-party Agno
application templates requested after the 2026-05-08 full radar reassessment:

- [`agno-agi/agno`](https://github.com/agno-agi/agno) — agent platform SDK,
  runtime, and AgentOS control-plane integration.
- [`agno-agi/dash`](https://github.com/agno-agi/dash) — self-learning data
  agent that grounds SQL answers in layered business context.
- [`agno-agi/scout`](https://github.com/agno-agi/scout) — company-intelligence
  agent that assembles context from web, workspace, database, wiki, Slack,
  Google Drive, and MCP providers.

The question is not whether Cognitive OS should become Agno. The question is
which agentic primitives or integration boundaries are better than COS behavior
and safe to extract under the external-tool adoption doctrine.

## Repository facts checked on 2026-05-09

| Repository | License | Stars | Forks | Last push | Latest release | Primary language | Notes |
|---|---:|---:|---:|---|---|---|---|
| `agno-agi/agno` | Apache-2.0 | 40,025 | 5,358 | 2026-05-08 | `v2.6.5` on 2026-05-06 | Python | Mature, active platform; README describes SDK, Runtime, and hosted/free local control-plane UI path |
| `agno-agi/dash` | Apache-2.0 | 2,057 | 233 | 2026-04-08 | none published | Python | Young example app; useful for data-agent learning loop patterns |
| `agno-agi/scout` | Apache-2.0 | 548 | 48 | 2026-05-05 | none published | Python | Young example app; useful for context-provider and company-brain patterns |

Source: GitHub repository metadata API and repository README pages for the
three URLs above. These values are a point-in-time snapshot; do not use star
counts as adoption proof.

## Classification

| Repository | Classification | Adoption kind | Rationale |
|---|---:|---|---|
| `agno-agi/agno` | **ASSESS / TRIAL-PATTERNS** | `adapter-lab`, `pattern-only` | Strong production-agent platform concepts, but direct runtime adoption would duplicate or override COS governance semantics |
| `agno-agi/dash` | **ASSESS-PATTERNS** | `pattern-only` | Self-learning SQL/data-agent loop maps to COS memory/eval gaps without needing the app runtime |
| `agno-agi/scout` | **ASSESS-PATTERNS** | `pattern-only`, possible future `adapter-lab` | Context-provider and company-brain ideas are relevant; external connectors require COS credential, policy, audit, and rollback wrappers |

## Key findings

### Agno core

Agno is not another Claw-named clone. It is a general agent-platform stack with
SDK, runtime service, persistent sessions, tracing, scheduling, RBAC, API
surface, and an AgentOS UI/control-plane path. The README also shows a Claude
Agent SDK integration path, so it overlaps with COS harness-provider work rather
than merely competing as a coding-agent wrapper.

Extractable ideas:

1. Runtime API shape for exposing governed agents as services.
2. Human approval semantics around sensitive workspace tools.
3. OpenTelemetry-first tracing as default product language.
4. Session/memory/storage separation across Postgres/ClickHouse-style stores.
5. AgentOS UI pattern for inspecting runs, sessions, and health.

Risks:

1. Runtime/platform adoption could bypass COS hooks, rules, memory lifecycle,
   and policy evidence ledgers.
2. Control-plane UX can blur local-free vs hosted/SaaS boundaries.
3. Telemetry defaults and provider metadata need explicit opt-out review before
   any local integration.
4. SDK-level abstractions may conflict with ADR-049 direct provider routing and
   ADR-064 harness-agnostic primitive projection.

### Dash

Dash is useful as a reference app for agentic SQL. Its strongest pattern is the
closed loop: retrieve knowledge and learnings, reason over intent, generate SQL,
execute, diagnose failures, save durable learnings, and optionally promote
answers into business knowledge.

Extractable ideas:

1. Layered data context taxonomy: table metadata, proven queries, business
   metrics/language, and learnings.
2. Error diagnosis that saves reusable SQL/data learnings instead of repeating
   failures.
3. Separation between durable knowledge and one-off query history.
4. Business-language grounding before query generation.

Risks:

1. It is a template application, not a general COS primitive.
2. Direct SQL execution is high-risk and must remain behind project-specific
   credential, read/write, approval, and audit policies.
3. It may duplicate Engram/Cognee memory work unless converted into a narrow
   schema/prompt/eval pattern.

### Scout

Scout is useful as a company-brain reference: it navigates fragmented sources,
builds a wiki/CRM/voice memory, and exposes context providers for web,
workspace, database, knowledge, Slack, Google Drive, and MCP servers.

Extractable ideas:

1. Context-provider registry with explicit provider trigger tools.
2. Separation between source navigation and materialized memory/wiki records.
3. Company voice/style as a first-class context surface.
4. CRM/wiki update tools as durable organizational memory, not chat-only
   context.

Risks:

1. Slack, Drive, CRM, and MCP connectors are externally visible or credentialed
   actions; COS must gate them through policy, audit, and rollback.
2. Company-brain scope can leak consumer-project data if adopted as a generic
   OS default.
3. Source navigation can become search-first context stuffing unless paired with
   COS context budget, provenance, and retention controls.

## Bidirectional implementation cross-check

| Agno-suite capability | COS state | Verdict | Action |
|---|---|---|---|
| Production agent runtime with sessions, APIs, approvals, RBAC, scheduling, tracing | COS has hooks/rules/skills/memory and emerging service/control-plane work, but not a mature app-service runtime | **MEJOR_EXTERNO for app-runtime packaging** | Assess adapter-lab only; do not replace governance core |
| Claude Agent SDK integration path | COS has ADR-064 provider/harness abstraction and direct provider routing | **IGUAL / DIFFERENT_LAYER** | Compare integration boundary; avoid SDK lock-in |
| OpenTelemetry tracing language | COS already chose Phoenix/OTel direction and deprecated Langfuse runtime/default | **COMPATIBLE** | Reuse OTel-first wording where it clarifies runtime evidence |
| Human approval for workspace write/edit/delete/shell | COS has permission hooks and policy gates | **COMPATIBLE** | Compare UX, not enforcement semantics |
| Dash layered data-agent knowledge | COS has Engram/Cognee memory and eval lanes but no dedicated agentic-SQL learning taxonomy | **MEJOR_EXTERNO for data-agent pattern** | Extract schema/prompt/eval ideas only |
| Scout context providers across live business systems | COS has connector policy and MCP posture, not company-brain app | **MEJOR_EXTERNO for provider UX** | Pattern-only unless a consumer project explicitly opts in |
| Hosted/free local control-plane UI | COS local-first doctrine requires explicit boundary between local control and SaaS | **RISKY** | Document hosted boundary before any integration |

## Recommendation

Add the Agno suite to the radar as a targeted post-reassessment addition:

- `agno-agi/agno`: **ASSESS / TRIAL-PATTERNS** for production-agent runtime
  packaging, human approval UX, tracing, session/storage separation, and
  possible adapter-lab experiments.
- `agno-agi/dash`: **ASSESS-PATTERNS** for self-learning SQL/data-agent
  knowledge taxonomy.
- `agno-agi/scout`: **ASSESS-PATTERNS** for context-provider and company-brain
  materialization patterns.

Do not install Agno by default, add it to bootstrap, or make it a COS runtime
dependency until there is an adoption manifest row with license, footprint,
telemetry, credential boundary, rollback, and consumer-proof acceptance criteria.

## Acceptance criteria for any future Agno integration

```text
ACCEPTANCE CRITERIA:
1. No Agno package is added to default requirements, package manifests, hooks, or bootstrap scripts without an adoption manifest row.
2. Any Agno adapter-lab keeps COS hooks/rules/memory/policy as the source of governance truth.
3. Telemetry and hosted-control-plane behavior are documented and disabled or made explicit for local-first use.
4. Dash-derived SQL patterns run only against project-approved read/write policies and audited credentials.
5. Scout-derived connectors require credential policy, source provenance, audit logs, and rollback before external actions are exposed.
6. A future proof compares Agno runtime behavior against ADR-049, ADR-064, ADR-247, and the external-tool adoption doctrine.
```

## Decision ledger row

| Tool/framework | Recommendation | Adoption kind | Reason | Next action |
|---|---:|---|---|---|
| agno-agi/agno | ASSESS / TRIAL-PATTERNS | adapter-lab, pattern-only | Mature Apache-2.0 production-agent platform with runtime/control-plane ideas; direct adoption risks bypassing COS governance semantics | Keep deep evaluation; run bounded adapter spike only after telemetry/control-plane review |
| agno-agi/dash | ASSESS-PATTERNS | pattern-only | Strong self-learning data-agent loop and layered business context taxonomy | Extract schema/eval prompts for data-agent memory only |
| agno-agi/scout | ASSESS-PATTERNS | pattern-only, possible adapter-lab | Context-provider and company-brain materialization patterns are relevant but connector actions are high-risk | Harvest provider UX; require credential/audit wrappers before any connector use |

## Source evidence

- GitHub: <https://github.com/agno-agi/agno>
- GitHub: <https://github.com/agno-agi/dash>
- GitHub: <https://github.com/agno-agi/scout>
- Related COS doctrine: `docs/04-Concepts/architecture/external-tool-adoption-doctrine.md`
- Related COS taxonomy: `docs/04-Concepts/architecture/external-tool-adapter-taxonomy.md`
- Prior Claw comparison context: `docs/03-PoCs/research/repo-scout/cluster-cli-claw-derivatives-2026-05-06.md`
