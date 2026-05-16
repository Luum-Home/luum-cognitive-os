---
report_type: external-tools-radar-targeted-addendum
scope: agno-agi/agno + agno-agi/dash + agno-agi/scout
source_index: docs/06-Daily/reports/external-tools-radar-INDEX.md
generated_at: 2026-05-09
status: documentation-before-implementation
source_artifacts:
  - docs/03-PoCs/research/repo-scout/deep/agno-agi__agno-suite-2026-05-09.md
related_docs:
  - docs/04-Concepts/architecture/external-tool-adoption-doctrine.md
  - docs/04-Concepts/architecture/external-tool-adapter-taxonomy.md
  - docs/06-Daily/reports/external-tools-radar-full-reassessment-2026-05-08.md
  - docs/06-Daily/reports/external-tools-radar-openswarm-addendum-2026-05-09.md
---

# External Tools Radar Addendum — Agno Suite 2026-05-09

## Why this addendum exists

The 2026-05-08 full reassessment covered the broad repository-derived external-tool corpus already visible in Cognitive OS. The user then asked whether Agno,
Dash, Scout, and the Claw variants had been reviewed. The Claw variants were in
the prior corpus; the Agno suite was not. This addendum records the missing
Agno review so future radar queries do not rediscover the same gap.

## Executive verdict

| Field | Decision |
|---|---|
| Radar status | **ASSESS / TRIAL-PATTERNS** |
| Recommendation | Pattern extraction plus possible bounded adapter-lab; no default runtime adoption |
| Adoption kind | `pattern-only`, possible future `adapter-lab` |
| License | Apache-2.0 across the three checked repositories |
| Default-install posture | **Do not install by default** |
| Primary value | Production-agent runtime packaging, context-provider UX, and self-learning data-agent loops |
| Primary risk | Framework/control-plane adoption could bypass COS governance, telemetry, credential, and local-first boundaries |

Agno is materially different from the Claw naming cluster. It should not be
treated as a thin coding-agent wrapper. It is a platform/runtime suite with
first-party example apps that overlap COS service/runtime ambitions. That makes
it relevant, but also too broad to import wholesale.

## Current metadata snapshot

| Repository | License | Stars | Last push | Radar call |
|---|---:|---:|---|---|
| [`agno-agi/agno`](https://github.com/agno-agi/agno) | Apache-2.0 | 40,025 | 2026-05-08 | **ASSESS / TRIAL-PATTERNS** |
| [`agno-agi/dash`](https://github.com/agno-agi/dash) | Apache-2.0 | 2,057 | 2026-04-08 | **ASSESS-PATTERNS** |
| [`agno-agi/scout`](https://github.com/agno-agi/scout) | Apache-2.0 | 548 | 2026-05-05 | **ASSESS-PATTERNS** |

Checked on 2026-05-09 through GitHub repository metadata and README pages.
Star counts are not adoption proof.

## Bidirectional implementation cross-check

| Agno-suite capability | COS state | Verdict | Action |
|---|---|---|---|
| SDK/runtime/control-plane for production agents | COS owns governance primitives and has emerging service-control-plane work | **EXTERNAL_BETTER for runtime packaging** | Assess adapter-lab only; keep COS governance authoritative |
| Persistent sessions, tracing, scheduling, RBAC | COS has memory, metrics, OTel direction, and policy gates but not a polished app-runtime package | **EXTERNAL_BETTER for product packaging** | Harvest boundaries and UX; do not import runtime by default |
| Human approval flows for workspace mutations | COS has permission/policy hooks | **COMPATIBLE** | Compare UX language; preserve hook enforcement |
| Dash self-learning SQL agent | COS has memory/eval primitives but no dedicated data-agent learning taxonomy | **EXTERNAL_BETTER for data-agent pattern** | Extract taxonomy and eval ideas, not direct SQL runtime |
| Scout context providers and company brain | COS has connector/MCP posture but no default company-brain app | **EXTERNAL_BETTER for provider UX** | Pattern-only; gate all connectors through credentials/audit/rollback |
| Hosted/local AgentOS UI | COS local-first doctrine requires explicit SaaS boundary | **RISKY** | Review telemetry and hosted-control-plane boundary before adapter work |

## What to extract

1. **Runtime packaging vocabulary** — agent service, sessions, approvals,
   scheduling, tracing, and health are good product-level primitives to compare
   against future COS control-plane work.
2. **Human approval UX** — sensitive workspace tools requiring confirmation map
   well to COS policy gates, as long as COS remains the enforcement source.
3. **Dash data-agent learning loop** — diagnose SQL/data failures, save reusable
   learnings, and separate business knowledge from query history.
4. **Scout context-provider registry** — named providers with explicit trigger
   tools provide a clean UX for source-specific context retrieval.
5. **Company-brain materialization** — wiki/CRM/voice memory as durable records,
   not only transient chat context.

## What not to extract

- No default Agno runtime dependency in COS bootstrap, requirements, hooks, or
  package manifests.
- No hosted control-plane coupling without local-first, telemetry, and data-flow
  review.
- No direct Slack, Drive, CRM, database, or MCP connector execution without COS
  credential policy, source provenance, audit log, and rollback story.
- No replacement of ADR-049 provider routing or ADR-064 harness-agnostic
  primitive projection with framework-specific abstractions.
- No direct SQL write/update capability from Dash-style patterns without
  project-owned read/write policy and approval gates.

## Claw comparison note

The prior radar already evaluated the Claw cluster. `openclaw/openclaw` was put
on HOLD because of a star-inflation/provenance verification flag, while
`nearai/ironclaw` moved to TRIAL for privacy/security primitive deep-dive and
`nullclaw`, `zeptoclaw`, `nanoclaw`, `picoclaw`, and `zeroclaw` remained monitor
confirmed. Agno should be evaluated on a separate axis: production-agent
platform and first-party product templates, not Claw-like wrapper naming.

## Recommended next action

```text
ACCEPTANCE CRITERIA:
1. Agno stays radar-only until an adoption manifest row exists.
2. A future adapter spike proves COS hooks/rules/memory/policy remain authoritative.
3. Telemetry, hosted-control-plane, and credential flows are documented before any connector/runtime use.
4. Dash/Scout ideas are first extracted as schemas, prompts, eval fixtures, or docs, not as default runtime dependencies.
5. Any consumer-facing connector requires audit log, source provenance, rollback, and explicit project opt-in.
```

## Decision ledger row

| Tool/framework | Recommendation | Adoption kind | Reason | Next action |
|---|---:|---|---|---|
| agno-agi/agno | ASSESS / TRIAL-PATTERNS | adapter-lab, pattern-only | Mature Apache-2.0 production-agent platform with useful runtime/control-plane packaging; direct adoption risks bypassing COS governance semantics | Keep deep evaluation; optionally design a bounded adapter spike after telemetry/control-plane review |
| agno-agi/dash | ASSESS-PATTERNS | pattern-only | Strong self-learning SQL/data-agent loop and layered business context taxonomy | Extract schema/eval ideas for project-specific data-agent memory |
| agno-agi/scout | ASSESS-PATTERNS | pattern-only, possible adapter-lab | Strong context-provider and company-brain materialization patterns; external connectors are high-risk | Harvest provider UX; require credential/audit wrappers before connector execution |

## Source evidence

- Deep evaluation: `docs/03-PoCs/research/repo-scout/deep/agno-agi__agno-suite-2026-05-09.md`
- GitHub repository: <https://github.com/agno-agi/agno>
- GitHub repository: <https://github.com/agno-agi/dash>
- GitHub repository: <https://github.com/agno-agi/scout>
- Prior Claw cluster: `docs/03-PoCs/research/repo-scout/cluster-cli-claw-derivatives-2026-05-06.md`
