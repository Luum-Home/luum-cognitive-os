# Stress Test Strategy: Cognitive OS Decomposing a Production Monolith

> Use the Cognitive OS itself to decompose the 170-endpoint monolith into Go microservices.
> This is the ultimate validation: a 13-component system proving itself on a massive, real-world task.

## 1. The Idea

We built a 13-component Cognitive OS. The best way to prove it works is to use it for a massive real task: decomposing a 170-endpoint monolith into Go microservices.

Instead of manually extracting each domain, we let the Cognitive OS orchestrate the entire process -- using its own memory, skills, error learning, fault tolerance, and self-improvement loops to get better at each successive extraction.

If the OS can handle this, it can handle anything we throw at it.

## 2. How Each Cognitive OS Component Is Used

| Component | Role in Decomposition |
|---|---|
| **Engram (Memory)** | Remembers decisions from previous domain migrations, avoids repeating mistakes |
| **SDD Workflow** | Structure: explore domain, propose extraction, spec, design, tasks, apply, verify |
| **Skills** | clean-arch-patterns, testing-patterns, typescript-patterns guide each agent |
| **Error Learning** | Captures compilation/test failures, warns next agents about patterns |
| **Auto-skill Generator** | When agent solves something complex, auto-generates skill for next domain |
| **Skill Metrics** | Tracks tokens, time, cost per domain extraction |
| **Model Routing** | Routes complex design decisions to Opus, implementation to Sonnet |
| **Fault Tolerance** | Tracks active tasks, recovers crashed agents |
| **Agent KPIs** | Measures overall progress: domains extracted, tests passing, cost |
| **SRE Agent** | Monitors newly deployed Go services for errors |
| **Plugin Architecture** | Each domain uses PROVIDER_* pattern for external services |
| **Constitutional Gates** | Every extracted service must pass: mock-before-integrate, test-before-merge, idempotent operations, audit trail |

## 3. The Swarm Pattern

```
Orchestrator (this session)
    |
    +-- Agent 1:  Extract "cards" domain         -> Go service
    +-- Agent 2:  Extract "crypto" domain         -> Go service
    +-- Agent 3:  Extract "qr" domain             -> Go service
    +-- Agent 4:  Extract "notifications" domain  -> Go service
    +-- Agent 5:  Extract "recharges" domain      -> Go service
    +-- Agent 6:  Extract "bills" domain          -> Go service
    +-- Agent 7:  Extract "store" domain          -> Go service
    +-- Agent 8:  Extract "admin" domain          -> Go service
    +-- Agent 9:  Extract "investments" domain    -> Go service
    +-- Agent 10: Extract "callbacks" domain      -> Go service
    +-- Agent 11: Extract "afip" domain           -> Go service
    +-- Agent 12: Extract "misc" domain           -> Go service
```

Each agent follows an identical pattern:

1. Read monolith domain (use cases, routes, data access)
2. Research open-source tools that apply (from `docs/research/`)
3. Create Go service in `${SERVICES_ROOT}/{domain}/`
4. Follow core-backend clean architecture (skills loaded)
5. Implement mock provider via plugin architecture
6. Add Kafka consumers/producers for events
7. Apply shared middleware stack
8. Create unit + integration tests
9. Add to docker-compose + go.work
10. Update decomposition tracker

## 4. Feedback Loops During Decomposition

This is where the Cognitive OS proves its value. Each extraction makes the next one better:

```
Agent extracts domain
    |
    v
error-learning captures failures
    |
    v
Next agent gets warnings about common patterns
    |
    v
auto-skill-generator creates skills from complex solutions
    |
    v
Next agent loads new skills automatically
    |
    v
skill-metrics tracks improvement over time
    |
    v
model-optimizer adjusts model routing based on data
    |
    v
agent-kpis shows overall health
```

The first domain extraction is the hardest. By domain 5 or 6, the system should be significantly faster and more reliable -- with accumulated skills, known error patterns, and optimized model routing.

## 5. Metrics We're Tracking

| Metric | Target |
|---|---|
| Domains extracted | 12/12 |
| Endpoints migrated | 170+/170+ |
| Go tests created | >80% coverage per domain |
| Cost per domain extraction | <$2 (measure and optimize) |
| Time per domain | <30 min average |
| Compilation success on first try | >90% |
| Error recurrence | 0 (same error never happens twice) |
| Constitutional gate violations | 0 |

## 6. Why This Matters

This is the first time an Cognitive OS is being used to decompose a production monolith. If it works:

- **Proves the OS handles real, complex, multi-service tasks** -- not just toy demos
- **Generates data for model optimization** -- real token counts, real cost curves
- **Creates skills that make future decompositions faster** -- each domain teaches the next
- **Documents the entire process for reproducibility** -- every decision in Engram
- **Validates fault tolerance under real load** -- agents crash, sessions compact, and the system recovers

## 7. Session Resume Protocol

If the session crashes mid-decomposition:

1. `session-resume` hook detects incomplete tasks in `active-tasks.json`
2. Read decomposition tracker for current state
3. Read Engram for context from crashed agents
4. Re-launch only incomplete domains
5. Agents are idempotent (check if files exist before creating)

## Related Documents

| Doc | Description |
|-----|-------------|
| [README.md](README.md) | Cognitive OS architecture: 13 components, self-improvement loop |
| Project migration audit | Current state: endpoint migration progress, per-feature status |
| [../plan-descomposicion-monolith.md](../plan-descomposicion-monolith.md) | Original decomposition plan: domains, phases, architecture target |
| [../ai-ecosystem/overview.md](../ai-ecosystem/overview.md) | Self-improvement loop: how agents get better over time |
