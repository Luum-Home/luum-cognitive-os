---
type: concept-synthesis
source: docs/04-Concepts/root/distributed-architecture.md
provenance: "Path from today's single-instance, single-project Cognitive OS to distributed AI orchestration across projects and nodes."
---

## What it is

Phased roadmap (Phase 0 current → Phase 1 multi-project → Phase 2 distributed → Phase 3 full distribution) plus a component-by-component distribution-readiness assessment.

## Key mechanics

**Phase 0 (current, working)**: multi-session on same project (`sessions/{id}/` isolation, advisory locks), agent-to-agent comms (`lib/agent_bus.py` via Valkey pub/sub), autonomous monitoring (`lib/singularity.py` MAPE-K), shared memory (Engram SQLite WAL), subprocess execution (`lib/claude_executor.py`), session state (`lib/session_state.py`, `active-tasks.json`), webhook pipelines (`lib/webhook_trigger.py`+`lib/issue_pipeline.py`). Missing: cross-project awareness, distributed Engram, multi-node coordination.

**Phase 1 — Multi-Project Orchestration** (~2 weeks, low/additive risk): one COS instance managing N projects. New: `projects.registry` section in global `cognitive-os.yaml` (name/path/phase/profile/repo per project); context switcher loads target project's config as override; Engram namespace extended with `project/{name}/` prefix, plus `global/patterns/*` and `global/decisions/*` for cross-project learnings; Singularity MAPE-K extended to scan/route across all registered projects. Reuses: session-concurrency isolation model, phase-aware agents, engram-organization prefix system, agent-customization overrides, efficiency profiles, webhook-trigger repo routing, domain_router.py. Estimated new code: ~800 LOC total (registry loader ~200, context switcher ~300, Engram enforcement ~100, Singularity scanner ~200).

**Phase 2 — Distributed COS** (~4 weeks, medium/state-migration risk): Engram SQLite→PostgreSQL (logical replication, or CockroachDB for multi-region; SQLite kept as offline local cache); Agent Bus Valkey→Valkey Cluster (channel namespacing `cos:{instance-id}:agent:{agent-id}:heartbeat`, cross-instance `cos:global:task-assignment`); metrics JSONL→centralized store (ClickHouse/TimescaleDB, or Langfuse, or Valkey Streams); task registry `active-tasks.json`→Valkey-backed distributed queue w/ dead-letter queue, at-most-once delivery; session locks→Valkey Redlock pattern with `{instance-id}:{session-id}` ownership + TTL; service discovery via Valkey heartbeat registration; task-assignment consensus via Valkey SETNX or Streams consumer groups (no Raft/Paxos needed).

**Phase 3 — Full Distribution** (~8 weeks, high complexity): leader election for Singularity (single active MAPE-K loop), service discovery, cross-node agent delegation, centralized cost aggregation, auto-scaling by task queue depth.

**Kubernetes analogy table**: Pod=Agent/`ClaudeExecutor`, Deployment=Squad, Service=Skill, ConfigMap=`cognitive-os.yaml`, Secret=`lib/secret_ref.py`, Namespace=Engram `project/{name}/` prefix, Control Plane=Singularity, etcd=Engram(distributed), kubectl=`cos` CLI, Helm Charts=efficiency presets, HPA=`rules/resource-governance.md`, NetworkPolicy=`lib/agent_permissions.py`, PodDisruptionBudget=circuit breaker, Admission Controller=PreToolUse hooks.

**Distribution readiness (8/14 YES, 3/14 PARTIAL, 3/14 NO)**: YES = Agent Bus, Config, Hooks, Skills, Rules, Executor, Notifications, Observability. PARTIAL = Memory/Engram (needs PostgreSQL adapter), Singularity (needs leader election), Webhooks (needs load balancer). NO = Session Mgmt (needs distributed locking beyond `FileMutationQueue`), Metrics (needs centralized store), Task Registry (needs distributed queue). All 3 blockers solved by moving local-file state to Valkey/PostgreSQL.

**Design principles**: portable by default (skills/rules=Markdown, hooks=Bash, no compilation); progressive distribution (solo=Phase0, team=Phase1, org=Phase2+); no vendor lock-in (Valkey BSD-3 not Redis SSPL, PostgreSQL not proprietary); fail-local (SQLite/JSONL/JSON continue working offline, sync on reconnect); eventually consistent (async Engram sync across nodes is acceptable); shared-nothing execution (each agent subprocess self-contained, coordination only before/after not during).

**Astro analogy**: COS orchestrates across tools (Claude Code native, Cursor via generated `.cursorrules`+extension, Codex via CLI wrapper, generic via `ClaudeExecutor`) rather than replacing them — governance (cost, quality gates, memory, phase-aware behavior) stays consistent regardless of which tool executes.

## Relations & where used

`docs/04-Concepts/architecture.md`, `docs/00-MOCs/entrypoints/overview.md`, `rules/singularity.md`, `rules/session-concurrency.md`, `rules/agent-communication.md`, `rules/orchestrator-mode.md`, `rules/engram-organization.md`, `rules/resource-governance.md`.

## Status / caveats

Open questions explicitly unresolved: Engram backend for Phase 2 (PostgreSQL vs CockroachDB vs TiKV), metrics aggregation choice (ClickHouse vs Langfuse vs Valkey Streams), leader-election mechanism, cross-tool adapter strategy, task-queue delivery semantics, multi-project cost allocation model. This is a design roadmap, not yet implemented beyond Phase 0.
