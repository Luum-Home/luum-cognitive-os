# Cognitive OS Efficiency Operating Model

## Purpose

This document turns the social-post theme — less lost context, fewer repeated decisions, fewer unnecessary iterations, lower token waste, more clarity, better code quality, and more work completed per session — into a Cognitive OS implementation and evidence plan.

It is not a wording import and not a claim that Cognitive OS already delivers every outcome in every harness. It defines how to make those outcomes real, portable, and measurable across projects.

## Core translation

The post's thesis maps to a simple operating model:

> When the specification is clear, agents are specialized, context stays alive, and workflow state is computable, AI coding stops behaving like a single chat and starts behaving like an organized engineering system.

For Cognitive OS, that means shipping the following as first-class, cross-CLI/IDE capabilities:

1. **Clear work contract** — task/source/spec, acceptance criteria, selected skills, verification plan, review budget, and stop conditions.
2. **Persistent working memory** — decisions, blockers, apply progress, review findings, verification receipts, and final verdict survive session boundaries.
3. **Specialized agent roles** — planner, implementer, reviewer, tester, release/checkpoint, and repair roles are selected by task shape instead of one thread doing everything.
4. **Live context organization** — Graphify, skill registry, context diet, budget meters, and query-tailored context decide what to read before the model burns tokens.
5. **Computable loop state** — status/next action comes from artifacts and receipts, not from the assistant guessing where it left off.
6. **Evidence-backed claims** — token savings, quality gains, and session productivity are reported only from paired evals, traces, and verification receipts.

## Outcome map

| Desired outcome | COS mechanism already present | Missing or immature mechanism | Porting target |
|---|---|---|---|
| Less wasted context | Graphify suite, context budget, context diet, preamble budget, query-tailored context | Unified context plan per task; compact skill registry path index | `cos-context-plan` plus `cos-skill-registry-refresh` |
| Fewer unnecessary iterations | `cos-loop-guard`, process-loop, retry budgets, flicker reports | Unified status dispatcher across work types | `cos status` family with nextRecommended per workflow |
| Fewer tokens consumed | token reports, token savings audit, SO impact eval, Graphify smokes | Real provider telemetry normalized across harnesses | cross-provider token usage normalization and eval receipts |
| More clarity | process contracts, SDD skills, DoD profiles, acceptance criteria rules | Default session preflight for all work, not only SDD | `cos-work-preflight` contract |
| Better code quality | DoD checks, tests, adversarial review, fresh review, license/secret guards | Stack-detected strict TDD and review workload forecast | `cos-testing-capabilities`, `cos-tdd-evidence-verify`, `cos-review-workload-forecast` |
| More work per session | background/targeted tests, process state, loop reports, SO impact eval | Operator dashboard/status that summarizes active OS health | `cos status` / `cos doctor` consolidation |
| Context stays alive | memory lifecycle docs, process traces, apply progress, verify reports | Single process ledger tying all work artifacts together | `cos-work-ledger` over process-loop, SDD, release, graph, tests |
| Organized engineering team feel | skills, router, agents, review gates, team IPC | Role-selection report and per-role budget policy | `cos-role-selection-report` and role budget contracts |

## Product promise ladder

Cognitive OS should use claim tiers instead of one broad marketing claim.

| Tier | Allowed wording | Required evidence |
|---|---|---|
| Structural | “Cognitive OS organizes context, roles, and verification.” | Installed primitives, projection checks, docs, smoke tests. |
| Directional | “This run reduced context read / retries / tool calls.” | One task report with traces and same-goal comparison caveats. |
| Measured | “In this controlled benchmark, full COS used X% fewer tokens than vanilla.” | `cos-so-impact-eval` paired run, usage normalization, verification pass, diff quality review. |
| Product | “Teams can finish more with less wasted agent capacity.” | Multiple task families, multiple stacks, repeated runs, real provider telemetry, quality oracle. |

Do not claim subscription savings, 50% remaining capacity, or universal token reductions without controlled COS receipts. Treat those as aspiration and measurement targets.

## Implementation roadmap

### Phase 1 — make the OS status computable

Deliverables:

- `cos status` top-level command that aggregates:
  - install/projection health
  - adapter capabilities
  - active process loops
  - token/context budgets
  - Graphify readiness
  - skill registry freshness
  - test lane recommendation
  - release/dependency health
- Workflow-specific dispatchers:
  - `cos-sdd-status`
  - `cos-process-status`
  - `cos-release-status`
  - `cos-token-status`
  - `cos-graphify-status`
  - `cos-skill-status`

Acceptance criteria:

- A user can ask “what should I do next?” and get one machine-derived next action with blockers and evidence paths.
- No workflow needs to infer phase from chat history alone.

### Phase 2 — reduce context before model calls

Deliverables:

- `cos-context-plan` that combines:
  - Graphify preload recommendations
  - changed-file detection
  - skill registry path index
  - query-tailored context
  - budget meter limits
- `cos-skill-registry-refresh`:
  - project-first skill discovery
  - user/global fallbacks
  - cache fingerprint
  - path and description only
  - no full skill body injection

Acceptance criteria:

- For a benchmark task, COS reports context files chosen, context lines avoided, and why each selected file was needed.

### Phase 3 — make roles explicit

Deliverables:

- `cos-role-selection-report` that chooses role lanes based on task shape:
  - planner/specifier
  - implementer
  - tester
  - reviewer
  - repair/fix-review
  - release/checkpoint
- Role budget policy:
  - max tool calls
  - max context lines
  - allowed tools
  - stop conditions
  - verification commands

Acceptance criteria:

- A multi-file task produces role selection evidence before launching agents or subagents.
- Delegation is justified by task shape, not by vague “complexity”.

### Phase 4 — make quality evidence stronger

Deliverables:

- `cos-testing-capabilities` for stack detection.
- `cos-tdd-evidence-verify` for RED/GREEN/TRIANGULATE/REFACTOR evidence when a runner exists.
- `cos-review-workload-forecast` for file/line/risk estimates before implementation or review.

Acceptance criteria:

- Strict TDD turns on only when test capability exists.
- Verify phase can distinguish strong tests from smoke-only or tautological tests.
- Oversized review work is split or explicitly accepted before apply.

### Phase 5 — make installation feel like one product

Deliverables:

- typed adapter capability registry:
  - config paths
  - lifecycle events
  - native hook support
  - subagent support
  - MCP support
  - projection level
  - proof level
- transactional projection pipeline:
  - prepare
  - apply
  - postcheck
  - rollback receipt
- operator UX:
  - `cos doctor`
  - `cos status`
  - optional TUI after CLI status is stable

Acceptance criteria:

- Installing into a consumer project produces one readable health report.
- Projection failures are caught immediately with rollback or repair commands.

### Phase 6 — prove the post-level outcomes

Deliverables:

- `cos-so-impact-eval` task families:
  - bugfix
  - refactor
  - feature
  - backend endpoint
  - frontend component
  - docs/release
  - test repair
- Modes:
  - vanilla
  - full COS
  - Graphify only
  - process-loop only
  - context optimization only
  - governance/hooks only
  - full COS minus Graphify
  - full COS minus process-loop
- Metrics:
  - total/input/output tokens
  - context lines read
  - tool calls
  - retries
  - wall-clock
  - false completions
  - relevant files found
  - tests passed
  - diff quality
  - review findings

Acceptance criteria:

- Product claims are backed by repeatable paired benchmark receipts, not anecdotes.

## Conversation triggers to add

These phrases should route to the efficiency workflow once implemented:

- `/cos-efficiency`
- `/context-efficiency`
- `/work-session-plan`
- `/cos-status`
- “quiero gastar menos tokens”
- “organizá el contexto antes de tocar código”
- “armá el equipo de agentes para esta tarea”
- “compará vanilla vs Cognitive OS”
- “cuánto contexto/tokens ahorramos”
- “qué hago después para terminar esto”

## Implemented advisory slice — 2026-06-15

ADR-339 introduced the first JSON-first, advisory implementation slice:

| Roadmap item | Command | Current status |
|---|---|---|
| `cos status` | `scripts/cos-status --json` | Aggregates adapter detection, skill count, testing capability, review risk, selected context count, roles, blockers, and `next_recommended`. |
| typed adapter capability registry | `scripts/cos-adapter-capabilities --json` | Reports config paths, lifecycle events, native hook support, subagent/MCP support, projection level, proof level, and detected evidence. |
| transactional projection pipeline | `scripts/cos-projection-transaction --path <file> [--apply] --json` | Plans projection targets and can back up existing files before projection writes; full apply/verify/rollback integration remains a later slice. |
| compact skill registry | `scripts/cos-skill-registry-refresh --json` | Writes `.cognitive-os/skill-registry.md` plus `.cognitive-os/.skill-registry.cache.json`; stores paths/descriptions only, not full skill bodies. |
| context plan | `scripts/cos-context-plan --goal "..." --json` | Suggests bounded files from git diff and goal-term overlap; Graphify/query-tailored unification remains a later slice. |
| role selection | `scripts/cos-role-selection-report --goal "..." --json` | Emits role recommendations, tool classes, budgets, and stop conditions from task shape. |
| testing capabilities | `scripts/cos-testing-capabilities --json` | Detects Node, Python, Go, Rust, Maven, and Gradle test/quality commands. |
| TDD evidence verify | `scripts/cos-tdd-evidence-verify --evidence evidence.md --json` | Checks RED/GREEN/TRIANGULATE/REFACTOR/safety-net markers and test files when runners exist. |
| review workload forecast | `scripts/cos-review-workload-forecast --json` | Reports changed files, line deltas, risk level, and split/review recommendations. |
| SO impact eval expansion | `scripts/cos-so-impact-eval catalog --json` | Lists supported task families, modes, metrics, and claim boundary for measured adoption. |

These commands are `candidate/advisory` lifecycle primitives. They are receipts and planning aids, not universal runtime enforcement yet.

## Public messaging boundary

Safe message:

> Cognitive OS turns agent work into a governed engineering loop: clear work contracts, persistent process state, specialized roles, context planning, and receipt-backed verification.

Safe measured message after evals:

> In controlled tasks, Cognitive OS can report how much context it avoided, which roles ran, which checks passed, and how token/tool usage compared with a vanilla run.

Unsafe until proven:

- “Saves 50% of every subscription.”
- “Always reduces tokens.”
- “Works equally in every IDE/CLI.”
- “Guarantees better code quality.”
- “Autonomously enforces every optimization in every harness.”

## Immediate implementation slices

1. `cos status` aggregator design and JSON contract.
2. typed adapter capability registry.
3. `cos-skill-registry-refresh` path index.
4. `cos-context-plan` integrating Graphify/context diet/skill registry.
5. role-selection report and budget policy.
6. strict TDD capability/evidence lane.
7. projection transaction/postcheck layer.
8. SO impact benchmark expansion to measure the full post-level promise.
