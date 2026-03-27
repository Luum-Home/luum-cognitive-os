# Cognitive OS — AI Ecosystem Overview

## Why "Cognitive OS"

Cognitive OS is not a metaphor — it's an architecturally accurate name. Like a traditional operating system manages hardware resources, Cognitive OS manages **cognition**: tokens, context, decisions, and agent coordination.

| OS Concept | Cognitive OS Equivalent |
|---|---|
| **Kernel** | `cognitive-os.yaml` + `hooks/_lib/` (core runtime) |
| **Process Scheduler** | Hook chain (SessionStart → PreToolUse → PostToolUse → Stop) |
| **Memory Management** | Engram (persistent) + context management (session) |
| **File System** | Metrics JSONL + remediation registry + transcripts |
| **Device Drivers** | Skills (interface between the agent and tools) |
| **System Calls** | Rules (contracts that processes must respect) |
| **Networking** | Squads + agent delegation (inter-process communication) |
| **Self-Healing** | MAPE-K loop (like a kernel watchdog) |
| **Package Manager** | Tool discovery + skill auto-generation |
| **Init System** | `cognitive-os-init` (like systemd) |

The difference: a traditional OS manages hardware. Cognitive OS manages **cognition** — the resources are tokens, context, and decisions, not CPU and RAM. But the architecture is isomorphic: abstraction layers, lifecycle management, resource governance, fault tolerance.

## Architecture Diagram

```
                         +-----------------------+
                         |    Claude Code CLI     |
                         |  (Developer Session)   |
                         +-----------+-----------+
                                     |
              +----------------------+----------------------+
              |                      |                      |
    +---------v---------+  +---------v---------+  +---------v---------+
    |    HOOKS (57)     |  |    RULES (55)     |  |    SKILLS (72)    |
    |  (runtime gates)  |  | (always-on laws)  |  | (domain knowledge)|
    +---------+---------+  +---------+---------+  +---------+---------+
    | SessionStart:     |  | constitutional-   |  | Project (9):      |
    |  stack-detector   |  |   gates           |  |  typescript       |
    |  session-resume   |  | control-manifest  |  |  nestjs, testing  |
    | PreToolUse:       |  | license-policy    |  |  clean-arch       |
    |  block-prod-urls  |  | skill-adaptation  |  |  daily-health     |
    |  error-pattern-   |  | skill-auto-loader |  |  error-analyzer   |
    |    detector       |  | skill-registry    |  |  model-optimizer  |
    |  agent-prelaunch  |  | model-routing     |  |  agent-kpis       |
    | PostToolUse:      |  | error-learning    |  |  resume-tasks     |
    |  auto-test-on-edit|  | fault-tolerance   |  | Global (10+):     |
    |  skill-feedback   |  | agent-kpis        |  |  SDD phases       |
    |  skill-metrics    |  | services-config   |  |  skill-creator    |
    |  error-learning   |  |                   |  |  openspec, etc.   |
    |  agent-checkpoint |  |                   |  |                   |
    +-------------------+  +-------------------+  +-------------------+
              +----------------------+----------------------+
              |                      |                      |
    +---------v---------+  +---------v---------+  +---------v---------+
    |   GITHUB ACTIONS  |  |   MCP SERVERS     |  |   AGENT TEAMS     |
    |  (CI/CD layer)    |  | (external brains) |  |  (experimental)   |
    +-------------------+  +-------------------+  +-------------------+
    | claude-pr-review  |  | Engram: persistent|  | Orchestrator +    |
    | claude-issue-     |  |   memory across   |  |   sub-agents      |
    |   triage          |  |   sessions        |  | Delegate-first    |
    |                   |  | Context7: live    |  |   pattern          |
    |                   |  |   library docs    |  |                   |
    +-------------------+  +-------------------+  +-------------------+
```

## Self-Improvement Loop

The AI ecosystem implements a closed-loop self-improvement cycle. Each agent execution feeds data back into the system, which uses it to improve future executions.

```
Agentes ejecutan tareas
    |
    v
Hooks capturan: metricas (tokens, tiempo, costo) + errores (test/lint/build)
    |
    v
Pattern detector inyecta warnings en proximos agentes
    |
    v
/error-analyzer propone skill updates
    |
    v
/model-optimizer ajusta routing de modelos
    |
    v
/agent-kpis mide todo con 20 KPIs
    |
    v
Alertas -> remediation automatica
    |
    v
Skills mejorados -> agentes mas eficientes
    |
    v
KPIs suben -> loop cerrado
```

### All Components of the Loop

| Component | File | Type | Role |
|-----------|------|------|------|
| skill-metrics-tracker.sh | `.claude/hooks/` | PostToolUse Agent | Captures tokens, time, model per agent execution |
| error-learning.sh | `.claude/hooks/` | PostToolUse Bash | Captures test/lint/build failures |
| error-pattern-detector.sh | `.claude/hooks/` | PreToolUse Agent | Injects warnings when 3+ similar errors detected |
| agent-prelaunch.sh | `.claude/hooks/` | PreToolUse Agent | Registers tasks for fault tolerance |
| agent-checkpoint.sh | `.claude/hooks/` | PostToolUse Agent | Marks tasks completed/failed |
| session-resume.sh | `.claude/hooks/` | SessionStart | Auto-recovers incomplete tasks from previous sessions |
| /error-analyzer | `.claude/skills/` | Skill | Groups error patterns, proposes skill updates |
| /model-optimizer | `.claude/skills/` | Skill | Analyzes model performance, updates routing table |
| /agent-kpis | `.claude/skills/` | Skill | Calculates 20 KPIs across 5 OKRs |
| /resume-tasks | `.claude/skills/` | Skill | Manual recovery fallback for incomplete tasks |
| model-routing.md | `.claude/rules/` | Rule | Routing table per skill (model selection) |
| error-learning.md | `.claude/rules/` | Rule | Error capture protocol |
| fault-tolerance.md | `.claude/rules/` | Rule | Task lifecycle management |
| agent-kpis.md | `.claude/rules/` | Rule | KPI calculation triggers |
| skill-adaptation.md | `.claude/rules/` | Rule | Feedback loop protocol |
| skill-metrics.jsonl | `.claude/` | Data | Agent execution metrics (tokens, time, cost) |
| error-learning.jsonl | `.claude/` | Data | Error pattern data |
| active-tasks.json | `.claude/` | Data | Task state for fault tolerance |

---

## Component Inventory

### Hooks (57) — Runtime Interceptors

Hooks fire automatically at specific lifecycle points. They run shell scripts.

| Hook | Trigger | Purpose |
|------|---------|---------|
| `stack-detector.sh` | SessionStart | Scans project, generates `detected-stack.json` |
| `session-resume.sh` | SessionStart | Auto-recovers incomplete tasks from previous sessions |
| `metrics-rotation.sh` | SessionStart | JSONL rotation to prevent unbounded growth |
| `metrics-calibrator-trigger.sh` | SessionStart | Weekly KPI calibration check |
| `tool-discovery-trigger.sh` | SessionStart | Weekly tool scan check |
| `block-prod-urls.sh` | PreToolUse (Bash) | Blocks production URLs in commands |
| `error-pattern-detector.sh` | PreToolUse (Agent) | Injects warnings for recurring error patterns (3+) |
| `agent-prelaunch.sh` | PreToolUse (Agent) | Registers tasks in active-tasks.json for fault tolerance |
| `auto-test-on-edit.sh` | PostToolUse (Edit/Write) | Auto-runs tests for the edited service |
| `skill-feedback-tracker.sh` | PostToolUse (Agent/Skill) | Tracks skill failures in Engram |
| `skill-metrics-tracker.sh` | PostToolUse (Agent) | Captures tokens, time, model per execution to skill-metrics.jsonl |
| `error-learning.sh` | PostToolUse (Bash) | Captures test/lint/build failures to error-learning.jsonl |
| `auto-repair-dispatcher.sh` | PostToolUse (Bash) | MAPE-K repair brain — analyzes errors, dispatches fixes |
| `agent-checkpoint.sh` | PostToolUse (Agent) | Marks tasks completed/failed in active-tasks.json |
| `conversation-capture.sh` | Stop | Session transcript indexing |
| `session-knowledge-extractor.sh` | Stop | Pattern mining from session activity |

*Plus 41 additional hooks for phase injection, squad management, auto-repair, security scanning, and infrastructure.*

### Rules (55) — Always-Active Constraints

Rules are loaded at session start and enforced throughout. They live in `.claude/rules/`.

| Rule | Scope |
|------|-------|
| `constitutional-gates.md` | 7 immutable architectural principles |
| `control-manifest.md` | Protected libraries, prohibited zones, performance/security constraints |
| `license-policy.md` | Dependency license vetting (AGPL/SSPL blocked for SaaS) |
| `skill-adaptation.md` | Auto-improvement protocol for skills via Engram feedback |
| `skill-auto-loader.md` | Maps detected tech stack to skills, suggests missing ones |
| `skill-registry-protocol.md` | Skill priority, versioning, refresh rules |
| `model-routing.md` | Model routing table per skill (which model for which task) |
| `error-learning.md` | Error capture protocol and pattern detection |
| `fault-tolerance.md` | Task lifecycle: registration, checkpointing, recovery |
| `agent-kpis.md` | KPI calculation triggers and OKR definitions |
| `services-config.md` | Service ports, credentials, environment variables |

### Skills (72) — Domain Knowledge

Skills are markdown files with structured instructions for specific domains.

| Skill | Type | Purpose |
|-------|------|---------|
| `typescript-patterns` | Project | Strict types, imports, error handling conventions |
| `nestjs-patterns` | Project | Module structure, guards, DTOs, conditional providers |
| `clean-arch-patterns` | Project | Layer rules, use cases, repository interfaces |
| `testing-patterns` | Project | Per-service testing: Jest, WireMock, TestContainers, Go |
| `daily-health-check` | Project | Check all service/infra health endpoints |
| `error-analyzer` | Project | Groups error patterns, proposes skill updates |
| `model-optimizer` | Project | Analyzes model performance, updates routing table |
| `agent-kpis` | Project | Calculates 20 KPIs across 5 OKRs |
| `resume-tasks` | Project | Manual recovery fallback for incomplete tasks |
| `repair-status` | Project | Auto-repair system status and circuit breaker state |
| `metrics-calibrator` | Project | Weekly KPI threshold calibration |
| `conversation-memory` | Project | Session transcript indexing and retrieval |
| `tool-discovery` | Project | Weekly GitHub scan for new MCP tools |
| SDD phases (7) | Global | Spec-Driven Development workflow phases |
| `skill-creator` | Global | Creates/updates skill files |
| `openspec` | Global | File-based artifact management |
| `go-testing` | Global | Go-specific testing patterns |

### GitHub Actions (2) — CI/CD Integration

| Action | Trigger | Purpose |
|--------|---------|---------|
| `claude-pr-review.yml` | PR opened/updated, `@claude` comment | Architecture/security/test review |
| `claude-issue-triage.yml` | Issue opened | Auto-label, classify, identify affected services |

### MCP Servers (2) — External Capabilities

| Server | Purpose |
|--------|---------|
| **Engram** | Persistent memory across sessions. Stores decisions, bugs, feedback, session summaries |
| **Context7** | Live documentation for any library. Used when generating/updating skills |

### Agent Teams (Experimental)

Enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.

- **Orchestrator** coordinates work, never reads/writes code directly
- **Sub-agents** are delegated specific tasks with skill references pre-resolved
- **SDD workflow** uses this for multi-phase planning (proposal -> spec -> design -> tasks -> apply -> verify)

## Data Flow: How Pieces Connect

```
1. Session starts
   -> stack-detector.sh scans project, generates detected-stack.json
   -> session-resume.sh checks active-tasks.json for incomplete tasks
   -> skill-auto-loader rule suggests missing skills for detected tech

2. Agent/sub-agent launches
   -> agent-prelaunch.sh registers task in active-tasks.json
   -> error-pattern-detector.sh checks error-learning.jsonl for similar past errors
   -> if 3+ matches found, injects warning into agent context

3. Developer edits code
   -> auto-test-on-edit.sh runs affected tests
   -> block-prod-urls.sh prevents production URL usage

4. Agent/sub-agent completes
   -> agent-checkpoint.sh marks task completed/failed in active-tasks.json
   -> skill-metrics-tracker.sh logs tokens, time, model to skill-metrics.jsonl
   -> error-learning.sh captures any test/lint/build failures to error-learning.jsonl

5. Skill/agent fails
   -> skill-feedback-tracker.sh saves failure to Engram
   -> skill-adaptation rule reads past failures next time
   -> after 3+ failures, suggests skill-creator to rewrite the skill

6. Periodic analysis (on-demand skills)
   -> /error-analyzer groups error patterns, proposes skill updates
   -> /model-optimizer analyzes model performance, updates routing table
   -> /agent-kpis calculates 20 KPIs across 5 OKRs, triggers alerts

7. PR is opened on GitHub
   -> claude-pr-review action reviews against constitutional gates

8. Issue is opened on GitHub
   -> claude-issue-triage action labels and classifies it
```

## Tool Discovery & Tech Radar

Cognitive OS continuously discovers new open-source tools via the `/tool-discovery` skill and classifies them using the [Thoughtworks Tech Radar](https://www.thoughtworks.com/radar) pattern:

```
    ┌─────────────────────────────┐
    │         ADOPT               │  ← Proven, integrate now
    │   ┌─────────────────────┐   │
    │   │      TRIAL          │   │  ← Test in one project
    │   │  ┌───────────────┐  │   │
    │   │  │   ASSESS       │  │   │  ← Evaluate deeper
    │   │  │  ┌─────────┐  │  │   │
    │   │  │  │  HOLD   │  │  │   │  ← Watch, don't act
    │   │  │  └─────────┘  │  │   │
    │   │  └───────────────┘  │   │
    │   └─────────────────────┘   │
    └─────────────────────────────┘
```

**4 quadrants**: Platforms & Infrastructure, Agent Frameworks, Code Quality & Repair, Developer Experience.

Current radar state: 10 ADOPT, 9 TRIAL, 10 ASSESS, 4 HOLD, 6 REJECTED.

See [reference/tool-watchlist.md](../reference/tool-watchlist.md) for the full radar.

## Configuration

All configuration lives in `.claude/settings.json`:

- **permissions.allow**: Whitelisted Bash commands
- **hooks.PreToolUse**: block-prod-urls on Bash commands
- **hooks.PostToolUse**: auto-test on Edit/Write, skill-feedback/metrics/error-learning/checkpoint on Agent/Bash
- **env**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

## Auto-Repair System (MAPE-K)

A closed-loop self-healing system based on the MAPE-K (Monitor, Analyze, Plan, Execute, Knowledge) architecture pattern. Errors detected during development are automatically analyzed, repaired in isolated worktrees, verified, and registered for future reuse.

```
                    ┌─── MAPE-K Auto-Repair Loop ───┐
                    │                                 │
  Error occurs ──→ Monitor (error-learning.sh)        │
                    │                                 │
                    ▼                                 │
              Analyze (auto-repair-dispatcher.sh)     │
                    │                                 │
              ┌─────┴──────┐                          │
              ▼            ▼                          │
         Registry     LLM repair                      │
         lookup       (async, worktree)               │
              │            │                          │
              ▼            ▼                          │
         Execute (worktree isolation)                 │
              │                                       │
              ▼                                       │
         Verify (build + test + lint)                 │
              │                                       │
         ┌────┴────┐                                  │
         ▼         ▼                                  │
      Success    Failure                              │
         │         │                                  │
         ▼         ▼                                  │
    Register    Circuit breaker                       │
    in registry  (2 strikes → OPEN)                   │
         │                                            │
         └──── Knowledge (Engram + JSONL) ────────────┘

  + Metrics auto-calibration (weekly)
  + Conversation memory (every session)
  + Tool discovery (weekly GitHub scan)
```

### Supporting Subsystems

| Subsystem | Hook/Skill | Frequency |
|-----------|-----------|-----------|
| MAPE-K repair | `auto-repair-dispatcher.sh` / `repair-status` | On every error |
| Metrics calibration | `metrics-calibrator-trigger.sh` / `metrics-calibrator` | Weekly |
| Conversation memory | `conversation-capture.sh` / `conversation-memory` | Every session |
| Tool discovery | `tool-discovery-trigger.sh` / `tool-discovery` | Weekly |
| JSONL rotation | `metrics-rotation.sh` | Every session start |
| Knowledge extraction | `session-knowledge-extractor.sh` | Every session end |
