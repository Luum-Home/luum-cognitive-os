# Distributed Cognitive OS Architecture

> From single-instance agent OS to distributed AI orchestration across projects and nodes.

---

## 1. Current State

Cognitive OS today operates as a single-instance, single-project system with multi-session support.

```
+---------------------------------------------------------------+
|                    SINGLE MACHINE                              |
|                                                                |
|  +---------------------------+                                 |
|  |  Cognitive OS Instance    |                                 |
|  |                           |                                 |
|  |  +---------+  +---------+ |  +----------+  +----------+    |
|  |  |Session 1|  |Session 2| |  | Engram   |  | Metrics  |    |
|  |  |(Claude) |  |(Claude) | |  | (SQLite  |  | (JSONL   |    |
|  |  +----+----+  +----+----+ |  |  WAL)    |  |  files)  |    |
|  |       |             |     |  +----------+  +----------+    |
|  |       +------+------+     |                                 |
|  |              |            |  +----------+                   |
|  |        +-----v------+    |  | Valkey   |                   |
|  |        | Agent Bus  |    |  | (pub/sub)|                   |
|  |        | (Valkey)   |----+->| Agent Bus|                   |
|  |        +------------+    |  +----------+                   |
|  +---------------------------+                                 |
|                                                                |
|  Project: my-fintech-app/                                      |
|    cognitive-os.yaml                                           |
|    .claude/rules/                                              |
|    .claude/settings.json                                       |
+---------------------------------------------------------------+
```

**What works today:**

| Capability | Implementation | Status |
|-----------|---------------|--------|
| Multi-session on same project | `sessions/{id}/` isolation, advisory locks | Working |
| Agent-to-agent communication | `lib/agent_bus.py` via Valkey pub/sub | Working |
| Autonomous monitoring | `lib/singularity.py` MAPE-K loop | Working |
| Shared persistent memory | Engram SQLite with WAL mode | Working |
| Subprocess agent execution | `lib/claude_executor.py` | Working |
| Session state persistence | `lib/session_state.py`, `active-tasks.json` | Working |
| Webhook-driven pipelines | `lib/webhook_trigger.py` + `lib/issue_pipeline.py` | Working |

**What does not exist yet:**

- No awareness of other projects on the same machine
- No cross-project knowledge sharing
- No distributed Engram
- No multi-node coordination

---

## 2. Phase 1: Multi-Project Orchestration

One COS instance managing N projects on a single machine. This is the near-term target.

```
COS Instance (single machine)
  |
  +-- Global Layer
  |     cognitive-os.yaml (global defaults)
  |     Engram (cross-project knowledge, global namespace)
  |     Agent Bus (shared Valkey, project-scoped channels)
  |     Singularity Controller (multi-project event loop)
  |
  +-- Project A: fintech-app (phase: production, profile: full)
  |     cognitive-os.yaml (overrides: strict gates, 80% coverage)
  |     .claude/rules/ (constitutional-gates, payment-guards)
  |     Engram namespace: project/fintech-app/*
  |     Metrics: fintech-app/.cognitive-os/metrics/
  |
  +-- Project B: startup-mvp (phase: reconstruction, profile: lean)
  |     cognitive-os.yaml (overrides: relaxed, 50% coverage)
  |     .claude/rules/ (minimal)
  |     Engram namespace: project/startup-mvp/*
  |     Metrics: startup-mvp/.cognitive-os/metrics/
  |
  +-- Project C: internal-tools (phase: maintenance, profile: standard)
        cognitive-os.yaml (overrides: bug-fix-only)
        .claude/rules/ (standard)
        Engram namespace: project/internal-tools/*
        Metrics: internal-tools/.cognitive-os/metrics/
```

### What needs to change

**Project Registry.** A new top-level section in the global `cognitive-os.yaml`:

```yaml
projects:
  registry:
    - name: fintech-app
      path: /home/dev/projects/fintech-app
      phase: production
      profile: full
      repo: git@github.com:org/fintech-app.git
    - name: startup-mvp
      path: /home/dev/projects/startup-mvp
      phase: reconstruction
      profile: lean
      repo: git@github.com:org/startup-mvp.git
```

**Context Switching.** When a task arrives (webhook, ticket, manual), the orchestrator:
1. Identifies the target project from the event payload or user instruction
2. Loads that project's `cognitive-os.yaml` as override on top of global defaults
3. Activates that project's `.claude/rules/` and skills
4. Scopes all Engram operations to `project/{name}/*`

**Engram Namespacing.** Extend the topic key prefix system from `rules/engram-organization.md`:

```
project/{project-name}/planning/{change}/spec
project/{project-name}/bugfix/{service}/{issue}
project/{project-name}/architecture/{topic}
global/patterns/{pattern-name}          # cross-project learnings
global/decisions/{decision-name}        # org-wide architectural decisions
```

**Singularity Multi-Project.** The `lib/singularity.py` MAPE-K loop already processes events in priority order. Extending it to multi-project means:
- Monitor: scan `metrics/` across all registered projects
- Analyze: classify events with project context attached
- Plan: route to the correct project's pipeline and phase rules
- Execute: launch `ClaudeExecutor` with the target project's working directory
- Knowledge: save outcomes scoped to the project namespace

**Cross-Project Knowledge.** Some knowledge is project-specific (bug fixes, architecture decisions). Some is universal (library evaluations, pattern discoveries). The `global/` Engram namespace stores cross-project learnings that any project can query.

### What already exists

| Component | Reuse for Multi-Project |
|-----------|------------------------|
| Session concurrency (`rules/session-concurrency.md`) | Session isolation model extends to project isolation |
| Phase-aware agents (`rules/phase-aware-agents.md`) | Each project has its own phase; agents inherit it |
| Engram organization (`rules/engram-organization.md`) | Prefix system already separates concerns; add `project/` prefix |
| Agent customization (`rules/agent-customization.md`) | Per-project agent overrides via `customizations/` |
| Efficiency profiles (`cognitive-os.yaml` profiles) | `lean`/`standard`/`full` map to project needs |
| Webhook trigger (`lib/webhook_trigger.py`) | Already routes by repo; add project-aware routing |
| Domain router (`lib/domain_router.py`) | Route issues to the correct project context |

### Estimated effort

This is primarily a configuration and routing change. The core execution engine (hooks, skills, Engram, Agent Bus) does not change. The main new code is:
- Project registry loader (~200 LOC Python)
- Context switcher in orchestrator (~300 LOC)
- Engram namespace enforcement (~100 LOC)
- Singularity multi-project scanner (~200 LOC)

---

## 3. Phase 2: Distributed COS

Multiple COS instances on different nodes, coordinating through shared infrastructure.

```
Node 1 (dev machine)                    Node 2 (CI server)
+-----------------------------+         +-----------------------------+
| COS Instance A              |         | COS Instance B              |
|                             |         |                             |
| +--------+  +--------+     |         | +--------+  +--------+     |
| |Session 1|  |Session 2|   |         | |Session 3|  |Session 4|   |
| +----+----+  +----+----+   |         | +----+----+  +----+----+   |
|      |             |       |         |      |             |       |
| +----v-------------v----+  |         | +----v-------------v----+  |
| | Local Agent Pool      |  |         | | Local Agent Pool      |  |
| | (Claude Code + Execs) |  |         | | (Claude Code + Execs) |  |
| +----------+------------+  |         | +----------+------------+  |
|            |               |         |            |               |
+------------|---------------+         +------------|---------------+
             |                                      |
             |    +------------------------------+  |
             +--->|     Shared Infrastructure     |<-+
                  |                              |
                  |  +----------+  +-----------+ |
                  |  | Valkey   |  | PostgreSQL| |
                  |  | Cluster  |  | (Engram)  | |
                  |  | (bus)    |  |           | |
                  |  +----------+  +-----------+ |
                  |                              |
                  |  +----------+  +-----------+ |
                  |  | Metrics  |  | Task      | |
                  |  | Store    |  | Queue     | |
                  |  |(ClickHse)|  | (Valkey)  | |
                  |  +----------+  +-----------+ |
                  +------------------------------+
```

### Component changes for distribution

**Engram: SQLite to PostgreSQL.** SQLite WAL supports one writer. Distribution requires a proper database:
- PostgreSQL with logical replication across nodes
- Or CockroachDB for true multi-region, but adds operational complexity
- Engram MCP server needs a PostgreSQL adapter (the current API stays the same)
- Fallback: each node keeps a local SQLite for offline operation, syncs on reconnect

**Agent Bus: Valkey to Valkey Cluster.** The `lib/agent_bus.py` already uses Valkey pub/sub. Valkey supports cluster mode natively:
- Channel namespacing: `cos:{instance-id}:agent:{agent-id}:heartbeat`
- Cross-instance channels: `cos:global:task-assignment`
- The file-based fallback in `agent_bus.py` serves as offline mode

**Metrics: JSONL to Centralized Store.** Local JSONL files do not aggregate across nodes:
- Option A: Ship JSONL to a centralized store (ClickHouse, TimescaleDB)
- Option B: Each node pushes metrics to the existing Langfuse instance
- Option C: Valkey Streams as a lightweight metrics bus, consumed by a collector
- The hook interface stays the same; only the write backend changes

**Task Registry: JSON to Distributed Queue.** `active-tasks.json` is a local file:
- Replace with Valkey-based task queue with distributed locking
- Consumers pull tasks, mark in-progress, report completion
- Dead letter queue for failed tasks
- At-most-once delivery prevents duplicate execution

**Session Management: File-based to Distributed Locks.** Advisory file locks (`rules/session-concurrency.md`) work on one machine:
- Valkey-based distributed locks (Redlock pattern)
- Lock ownership includes `{instance-id}:{session-id}`
- TTL-based expiration survives node failures

**Service Discovery.** Which COS instance handles which project:
- Simple: static mapping in shared config
- Dynamic: instances register themselves in Valkey with heartbeats
- Load balancing: round-robin for new tasks, sticky for in-progress projects

**Consensus for Task Assignment.** No two instances should process the same ticket:
- Valkey SETNX (atomic set-if-not-exists) for simple claim
- Valkey Streams consumer groups for ordered task distribution
- No need for heavy consensus (Raft/Paxos) — Valkey handles coordination

---

## 4. The Kubernetes Analogy

| Kubernetes | Cognitive OS Distributed | Current COS Component |
|-----------|------------------------|----------------------|
| Pod | Agent (sub-agent instance) | `ClaudeExecutor` subprocess |
| Deployment | Squad (agent team definition) | `squads/*.yaml` |
| Service | Skill (reusable capability) | `skills/*/SKILL.md` |
| ConfigMap | `cognitive-os.yaml` | `cognitive-os.yaml` |
| Secret | Environment variables / SecretRef | `lib/secret_ref.py` |
| Namespace | Project scope | Engram prefix `project/{name}/` |
| Control Plane | Singularity controller | `lib/singularity.py` |
| etcd | Engram (distributed) | Engram SQLite (local) |
| kubectl | `cos` CLI | `cos` Go binary |
| Helm Charts | Efficiency presets | `cognitive-os.yaml` profiles |
| Node | Machine running COS instance | Single machine today |
| DaemonSet | Always-on hooks | SessionStart hooks |
| CronJob | Scheduled tasks | `self-improvement`, `metrics-calibrator` |
| HPA (autoscaler) | Resource governance | `rules/resource-governance.md` |
| NetworkPolicy | Agent permissions | `lib/agent_permissions.py` |
| PodDisruptionBudget | Circuit breaker | `auto_repair.circuit_breaker` |
| Admission Controller | PreToolUse hooks | `clarification-gate`, `blast-radius` |

---

## 5. Distribution Readiness Assessment

| Component | File/Module | Current State | Distribution Ready? |
|-----------|------------|--------------|-------------------|
| Agent Bus | `lib/agent_bus.py` | Valkey pub/sub with file fallback | **YES** — Valkey Cluster is a config change |
| Memory | Engram MCP server | SQLite WAL mode | **PARTIAL** — needs PostgreSQL adapter |
| Config | `cognitive-os.yaml` | Local YAML per project | **YES** — can be served from shared store |
| Hooks | `hooks/*.sh` | Bash scripts, no state | **YES** — portable, run on any node |
| Skills | `skills/*/SKILL.md` | Markdown files | **YES** — portable, content-addressed |
| Rules | `rules/*.md` | Markdown files | **YES** — portable, version-controlled |
| Session Mgmt | `sessions/{id}/` + `lib/file_mutation_queue.py` | File isolation + advisory shell locks + Python thread serialization | **NO** — needs distributed locking (Python-level `FileMutationQueue` handles single-machine concurrency) |
| Metrics | `.cognitive-os/metrics/*.jsonl` | Local append-only files | **NO** — needs centralized store |
| Task Registry | `active-tasks.json` | Local JSON file | **NO** — needs distributed queue |
| Singularity | `lib/singularity.py` | Single-instance MAPE-K | **PARTIAL** — needs leader election |
| Executor | `lib/claude_executor.py` | Local subprocess | **YES** — runs where invoked |
| Webhooks | `lib/webhook_trigger.py` | Single FastAPI server | **PARTIAL** — needs load balancer |
| Notifications | `lib/notifications.py` | Stateless HTTP calls | **YES** — works from any node |
| Observability | `lib/observability.py` | Langfuse/Opik (remote) | **YES** — already centralized |

**Score: 8/14 ready, 3/14 partial, 3/14 not ready.**

The three blockers (session management, metrics, task registry) are all solved by moving state from local files to Valkey/PostgreSQL.

---

## 6. Migration Path

```
Phase 0 (NOW)          Phase 1 (NEXT)           Phase 2 (THEN)          Phase 3 (FUTURE)
+-----------------+    +-------------------+     +-------------------+   +-------------------+
| Single instance |    | Single instance   |     | Multi-instance    |   | Full distribution |
| Single project  |--->| Multi-project     |---->| Shared Engram     |-->| Service discovery |
| Multi-session   |    | Project registry  |     | Valkey Cluster    |   | Consensus         |
|                 |    | Context switching |     | PostgreSQL Engram |   | Auto-scaling      |
|                 |    | Engram namespaces |     | Distributed locks |   | Cross-region      |
+-----------------+    +-------------------+     +-------------------+   +-------------------+

Effort:   ---             ~2 weeks                  ~4 weeks               ~8 weeks
Risk:     none            low (additive)            medium (state migration) high (distributed)
```

### Phase 0 to 1: Multi-Project (low risk, high value)

1. Add `projects.registry` to `cognitive-os.yaml`
2. Implement context switcher in orchestrator (load target project config)
3. Add `project/{name}/` prefix to Engram topic keys
4. Extend Singularity to scan across registered projects
5. Extend `domain_router.py` for multi-project webhook routing

### Phase 1 to 2: Multi-Instance (medium risk)

1. Deploy Valkey Cluster (replaces standalone Valkey)
2. Implement Engram PostgreSQL adapter (keep SQLite as local cache)
3. Replace `active-tasks.json` with Valkey-backed task queue
4. Replace file-based session locks with Valkey distributed locks
5. Implement metrics shipping (JSONL to centralized store)
6. Add instance registration and heartbeat

### Phase 2 to 3: Full Distribution (high complexity)

1. Leader election for Singularity (only one MAPE-K loop active)
2. Service discovery for COS instances
3. Cross-node agent delegation (Node A delegates to Node B)
4. Centralized cost aggregation across all nodes
5. Auto-scaling: spin up COS instances based on task queue depth

---

## 7. Design Principles

**Portable by default.** Skills are Markdown. Rules are Markdown. Hooks are Bash. They work on any machine with a shell. No compilation, no runtime dependencies for the governance layer.

**Progressive distribution.** Start local, distribute when needed. A solo developer uses Phase 0. A team uses Phase 1. An organization uses Phase 2+. The same `cognitive-os.yaml` drives all modes.

**No vendor lock-in.** Valkey (BSD-3, not Redis SSPL). PostgreSQL (not proprietary). Open formats (YAML, JSONL, Markdown). Every infrastructure choice has a self-hosted option.

**Fail-local.** If the network fails, each COS instance continues operating with local Engram (SQLite), local metrics (JSONL), and local task tracking (JSON). When connectivity resumes, state syncs.

**Eventually consistent.** Engram sync between nodes can be async. An agent on Node A does not need to wait for Node B to acknowledge a memory write. The trade-off: brief windows where two nodes have different knowledge. For an AI agent system, this is acceptable — agents already operate on incomplete information.

**Shared-nothing execution.** Each agent subprocess is self-contained. It reads config, loads skills, executes, and writes results. No shared mutable state during execution. Coordination happens before (task assignment) and after (result collection), not during.

---

## 8. The Astro Analogy

Astro does not replace React, Svelte, or Vue. It orchestrates across them — you choose the right framework per component, and Astro handles the composition.

Distributed COS does not replace Claude Code, Cursor, Codex, or any individual AI coding tool. It orchestrates across them:

```
+---------------------------------------------------------------+
|              COS Distributed Control Plane                     |
|                                                                |
|  +-------------------+  +-------------------+                  |
|  | Claude Code       |  | Cursor            |                  |
|  | Session (Proj A)  |  | Session (Proj B)  |                  |
|  | governed by COS   |  | governed by COS   |                  |
|  +-------------------+  +-------------------+                  |
|                                                                |
|  +-------------------+  +-------------------+                  |
|  | Codex / Devin     |  | Custom Agent      |                  |
|  | Session (Proj C)  |  | (via Executor)    |                  |
|  | governed by COS   |  | governed by COS   |                  |
|  +-------------------+  +-------------------+                  |
|                                                                |
|  Shared across all:                                            |
|    - Engram (persistent memory)                                |
|    - Cost tracking and budget enforcement                      |
|    - Skill registry (reusable capabilities)                    |
|    - Quality gates (rules, hooks, DoD)                         |
|    - Agent Bus (coordination channel)                          |
|    - KPI dashboards (unified metrics)                          |
+---------------------------------------------------------------+
```

The value proposition: regardless of which AI tool processes a task, the governance layer (cost limits, quality gates, memory, phase-aware behavior) remains consistent. A Cursor session on Project B follows the same rules as a Claude Code session on Project A.

This requires an adapter layer per tool:
- **Claude Code**: native (hooks + settings.json)
- **Cursor**: `.cursorrules` generated from COS rules + custom extension for hooks
- **Codex**: CLI wrapper that applies COS governance pre/post execution
- **Generic**: `ClaudeExecutor` already supports any tool that accepts a prompt and returns output

---

## 9. Open Questions

| Question | Options | Decision Needed By |
|----------|---------|-------------------|
| Engram backend for Phase 2 | PostgreSQL vs CockroachDB vs TiKV | Phase 2 start |
| Metrics aggregation | ClickHouse vs Langfuse vs Valkey Streams | Phase 2 start |
| Leader election mechanism | Valkey-based vs etcd vs embedded Raft | Phase 2 design |
| Cross-tool adapter strategy | Generate config files vs wrapper scripts vs MCP | Phase 1 |
| Task queue semantics | At-most-once vs at-least-once delivery | Phase 2 design |
| Multi-project cost allocation | Per-project budgets vs shared pool | Phase 1 |

---

## References

- `docs/architecture.md` — Current system architecture
- `docs/overview.md` — Vision and component inventory
- `rules/singularity.md` — MAPE-K autonomous loop
- `rules/session-concurrency.md` — Multi-session isolation model
- `rules/agent-communication.md` — Valkey Agent Bus protocol
- `rules/orchestrator-mode.md` — ClaudeExecutor subprocess delegation
- `rules/engram-organization.md` — Topic key prefix system
- `rules/resource-governance.md` — Budget enforcement and auto-scaling
- `cognitive-os.yaml` — Configuration structure
- `lib/singularity.py` — Singularity controller implementation
- `lib/agent_bus.py` — Agent Bus implementation
- `lib/claude_executor.py` — Subprocess executor
- `lib/webhook_trigger.py` — Webhook server for event-driven pipelines
