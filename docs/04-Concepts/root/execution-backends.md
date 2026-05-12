# Execution Backends Architecture

> COS does not replace execution engines -- it governs them. Like Linux abstracts hardware through drivers, COS abstracts execution through backends.

---

## 1. The Driver Model

Cognitive OS is a control plane. It decides WHAT to build, HOW MUCH to spend, and WHETHER the output is good enough. Backends decide HOW to execute.

```
+------------------------------------------------------------+
|              Cognitive OS (Control Plane)                    |
|                                                              |
|  Adaptive Bypass -> Workflow Selection -> Dispatch            |
|  Budget Check -> Context Prep -> Validation                  |
|  Engram Memory -> Cost Tracking -> Trust Scoring             |
+------+----------+-----------+-----------+-------------------+
       |          |           |           |
  +----v---+ +---v------+ +--v-------+ +-v-----------+
  | claude | | cursor   | | kagent   | | agentfield  |
  | -code  | | cloud    | | (K8s)    | | (microsvcs) |
  |        | | agents   | |          | |             |
  | Local  | | VM+Video | | CRDs     | | APIs        |
  | process| | isolated | | scaled   | | routed      |
  +--------+ +----------+ +----------+ +-------------+
```

Each backend is a "driver" that COS loads on demand. Adding a new backend does not change the core -- it registers in `cognitive-os.yaml` and implements the standard interface.

Before implementing a new backend, run `lib/reinvention_guard.py` to check whether the adopted upstreams (Hermes, Pi) or the competitive landscape already provide the capability.

---

## 2. Backend Registry

| Backend | Type | Isolation | Video | Scale | Best For | Status |
|---------|------|-----------|-------|-------|----------|--------|
| `claude-code` | local | Process (sub-agent) | No | 1-5 parallel | Trivial/Small, fast iteration | Available now |
| `cursor` | cloud-agent | VM (full desktop) | Yes | 10-100 parallel | Medium/Large, visual testing | Requires Cursor API |
| `kagent` | kubernetes | Pod (gVisor/Kata) | No | 100-1000+ | Large/Critical, enterprise | Requires K8s cluster |
| `agentfield` | microservice | Container | No | Unlimited | Distributed, cross-service | Requires AgentField setup |
| `agent-sandbox` | kubernetes | Sandbox CRD | No | 100-1000+ | Untrusted, multi-tenant | Requires K8s 1.32+ |

---

## 3. Routing Logic

COS selects the backend based on five signals: task complexity (from `definition-of-done` classification), available backends (configured and reachable), project phase (`cognitive-os.yaml -> project.phase`), budget constraints (`resources.budget`), and special requirements (video proof, K8s isolation).

```
TASK ARRIVES
    |
    v
[Classify complexity: trivial/small/medium/large/critical]
    |
    v
[Check available backends in cognitive-os.yaml]
    |
    v
[Apply routing strategy]
    |
    +-- complexity=TRIVIAL, any phase
    |       -> claude-code (fastest, cheapest)
    |
    +-- complexity=SMALL, reconstruction/stabilization
    |       -> claude-code
    |
    +-- complexity=SMALL, production/maintenance
    |       -> cursor (if available) or claude-code
    |
    +-- complexity=MEDIUM
    |       -> cursor (preferred) or claude-code with delegation
    |
    +-- complexity=LARGE
    |       -> kagent (if K8s) or cursor (multiple agents)
    |
    +-- complexity=CRITICAL
    |       -> kagent with agent-sandbox isolation
    |
    +-- distributed=true
            -> agentfield
```

Fallback is always `claude-code`. If the preferred backend is unreachable, COS downgrades gracefully.

---

## 4. Configuration

```yaml
# cognitive-os.yaml (new section)
execution:
  default_backend: claude-code

  backends:
    claude-code:
      enabled: true
      type: local
      complexity: [trivial, small]
      max_parallel: 5               # maps to resources.compute.max_parallel_agents
      cost_per_minute: 0.00         # included in Claude API cost

    cursor:
      enabled: false                # opt-in
      type: cloud-agent
      complexity: [small, medium, large]
      endpoint: ${CURSOR_API_URL}
      api_key: ${CURSOR_API_KEY}
      max_parallel: 10
      cost_per_minute: 0.02
      features:
        video_proof: true
        vm_isolation: true
        self_hosted: true

    kagent:
      enabled: false                # opt-in, requires K8s
      type: kubernetes
      complexity: [large, critical]
      namespace: cognitive-os
      operator_version: "0.5"
      max_parallel: 50
      cost_per_minute: 0.01         # infrastructure cost only
      features:
        gvisor_isolation: true
        kata_containers: false

    agentfield:
      enabled: false                # opt-in
      type: microservice
      complexity: [critical]
      endpoint: ${AGENTFIELD_URL}
      max_parallel: 100
      features:
        routing: true
        memory: true                # AgentField has its own memory
        audit_trails: true

  routing:
    strategy: complexity-match      # complexity-match | cheapest | fastest | most-isolated
    fallback: claude-code
    require_video_for: [large, critical]  # only if cursor available
```

---

## 5. Backend Interface

Every backend implements this contract (conceptually):

```
dispatch(task, context, acceptance_criteria) -> task_id
status(task_id) -> pending | running | completed | failed
result(task_id) -> {pr_url, video_url, files_changed, trust_report}
cancel(task_id) -> ok
```

COS does not care HOW the backend executes. It dispatches, polls status, validates results, and tracks cost. This is the driver abstraction.

### What COS sends to every backend

| Field | Source | Purpose |
|-------|--------|---------|
| `task` | SDD tasks artifact or user instruction | What to build |
| `context` | Engram observations, relevant rules | Project knowledge |
| `acceptance_criteria` | From `acceptance-criteria` rule | How to verify completion |
| `phase` | `cognitive-os.yaml -> project.phase` | Behavioral constraints |
| `budget_limit` | `resources.budget.per_agent_max_usd` | Spending cap |

### What COS expects back

| Field | Purpose | Validated by |
|-------|---------|-------------|
| `files_changed` | Diff of modifications | `claim-validator.sh` (anti-hallucination) |
| `test_results` | Pass/fail counts | `auto-verify.sh` (acceptance criteria) |
| `trust_report` | Agent's self-assessment | `trust-score-validator.sh` |
| `cost` | Tokens and time consumed | `resource-governance` rule |
| `pr_url` | Pull request (if applicable) | Human review |
| `video_url` | Screen recording (Cursor only) | Human review |

---

## 6. Control Plane vs Execution Plane

| Concern | COS (control plane) | Backend (execution) |
|---------|--------------------|--------------------|
| What to build | Decides (SDD pipeline, Singularity) | Executes instructions |
| Budget | Enforces (`resource-governance`) | Reports cost |
| Quality | Validates (`trust-score`, `auto-verify`, `dod-gate`) | Produces output |
| Memory | Manages (Engram) | Stateless per task |
| Retry logic | Decides when (`closed-loop-prompts`, max 3) | Re-executes |
| Security | Checks permissions (`agent-security`) | Provides isolation |
| Scheduling | Routes to backend | Manages its own queue |
| Observability | Aggregates metrics (JSONL, Langfuse) | Emits events |

Backends are stateless from COS's perspective. All persistent state lives in Engram and metrics. If a backend dies, COS re-dispatches to another.

---

## 7. The Linux Analogy

| Linux Kernel | Cognitive OS |
|-------------|--------------|
| Kernel | COS core (rules, hooks, Engram) |
| Drivers | Execution backends (`claude-code`, `cursor`, `kagent`, `agentfield`) |
| `/dev/` | Backend registry in `cognitive-os.yaml -> execution.backends` |
| Syscalls | Backend interface (`dispatch`/`status`/`result`/`cancel`) |
| Process scheduler | Adaptive bypass + complexity routing |
| Filesystem | Engram (persistent storage via SQLite WAL) |
| `/etc/` | `cognitive-os.yaml` + `rules/` |
| Package manager | `cos` CLI with `sources` registries |
| Init system | `self-install.sh` + `session-init.sh` |
| Cron | Scheduled tasks + `singularity.py` MAPE-K loop |
| Users & permissions | `agent-identity` + `agent-security` (`lib/agent_permissions.py`) |
| Kernel modules | Skills (loaded on demand via progressive loading) |
| Syslog | Metrics (`.cognitive-os/metrics/*.jsonl`) |
| `/proc/` | `/cognitive-os-status` skill |

---

## 8. Integration with Existing Components

### SDD Pipeline

Each SDD phase can target a different backend:

```
explore (claude-code)  ->  propose (claude-code)  ->  spec (claude-code)
    -> design (claude-code)  ->  tasks (claude-code)
    -> apply (cursor or kagent)  ->  verify (claude-code)
    -> archive (claude-code)
```

The expensive phase (`sdd-apply`) benefits most from backend routing. Planning phases stay on `claude-code` because they are fast and benefit from local context.

### Singularity Controller

`lib/singularity.py` already routes events to pipelines. Adding backend awareness means the controller selects the execution backend per event:

- `test_failure` -> `claude-code` (fast local fix)
- `new_feature` -> `cursor` (VM isolation, video proof)
- `critical_bug` -> `kagent` (scaled, isolated)

### Agent Bus

When `AGENT_BUS_ENABLED=true`, `lib/agent_bus.py` provides heartbeat and progress tracking. Remote backends (Cursor, kagent) publish to the same Valkey channels via adapter, giving the orchestrator unified visibility across all backends.

### Cost Tracking

Every backend reports cost. COS aggregates into `metrics/cost-events.jsonl` with a `backend` field. The `resource-governance` rule enforces budgets across all backends combined, and `lib/cost_predictor.py` factors backend cost into predictions.

---

## 9. Migration Path

```
Phase 1 (NOW)        Phase 2 (NEXT)        Phase 3 (THEN)       Phase 4 (FUTURE)
+----------------+   +------------------+   +-----------------+  +------------------+
| claude-code    |   | + cursor cloud   |   | + kagent (K8s)  |  | + agentfield     |
| only           |-->| agents           |-->| enterprise      |->| distributed      |
|                |   | VM isolation     |   | scale           |  | microservice     |
| Local process  |   | Video proof      |   | gVisor/Kata     |  | agents           |
| 1-5 parallel   |   | 10-100 parallel  |   | 100-1000+       |  | unlimited        |
+----------------+   +------------------+   +-----------------+  +------------------+

Effort:  ---           ~2 weeks              ~4 weeks             ~6 weeks
Risk:    none          low (additive)        medium (K8s ops)     medium (new arch)
```

Each phase adds a backend without changing the core. The routing logic in `execution.routing` adapts automatically. Existing `claude-code` sessions continue working unchanged.

---

## 10. Open Source Ecosystem

| Tool | What it provides | License | Reference |
|------|-----------------|---------|-----------|
| kagent | K8s CRDs for AI agents, MCP integration | Apache 2.0 | kagent.dev |
| AgentField | Agent-as-microservice, routing, audit | Open source | github.com/Agent-Field/agentfield |
| agent-sandbox | K8s Sandbox CRD for isolated runtimes | Apache 2.0 | github.com/kubernetes-sigs/agent-sandbox |
| Firecracker | MicroVM for agent isolation | Apache 2.0 | firecracker-microvm.github.io |
| gVisor | User-space kernel for container isolation | Apache 2.0 | gvisor.dev |

All tools use permissive licenses (Apache 2.0), compatible with COS's license policy.

---

## References

- `docs/04-Concepts/root/distributed-architecture.md` -- Multi-project and distributed COS vision
- `docs/08-References/integrations/cursor-cloud-agents.md` -- Cursor integration design
- `docs/04-Concepts/architecture.md` -- Current system architecture and component inventory
- `rules/resource-governance.md` -- Budget enforcement and model downgrade chain
- `rules/definition-of-done.md` -- Task complexity classification
- `rules/agent-security.md` -- Permission system and least privilege
- `rules/closed-loop-prompts.md` -- Retry logic and HALT protocol
- `lib/claude_executor.py` -- Current local backend implementation
- `lib/singularity.py` -- MAPE-K autonomous controller
- `lib/agent_bus.py` -- Agent communication via Valkey pub/sub
- `cognitive-os.yaml` -- Configuration structure (new `execution` section)
