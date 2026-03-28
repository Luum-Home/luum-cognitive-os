# Cognitive OS Architecture

> System architecture, component inventory, data flow, and technology stack.

---

## System Diagram

```
+===========================================================================+
|                          COGNITIVE OS ARCHITECTURE                         |
+===========================================================================+

   HUMAN                              EVENTS
     |                                  |
     v                                  v
+--------------------+    +---------------------------+
|    Claude Code     |    |   Singularity Controller  |
|   (Interactive)    |    |     (Autonomous Loop)     |
+--------+-----------+    +------+----+---+-----------+
         |                       |    |   |
         |    +-----------+      |    |   |
         +--->| Orchestr. |<-----+    |   |
              | (Claude)  |           |   |
              +-----+-----+          |   |
                    |                 |   |
        +-----------+-----------+     |   |
        |           |           |     |   |
   +----v----+ +----v----+ +---v---+  |   |
   |  HOOKS  | |  RULES  | | SKILLS|  |   |
   | (bash)  | |  (.md)  | | (.md) |  |   |
   +----+----+ +----+----+ +---+---+  |   |
        |           |           |     |   |
        +-----+-----+-----+----+     |   |
              |           |           |   |
        +-----v-----+ +---v--------+ |   |
        |  ENGRAM   | |  METRICS   | |   |
        | (SQLite)  | |  (JSONL)   | |   |
        +-----------+ +------------+ |   |
                                     |   |
              +----------------------+   |
              |                          |
        +-----v------+   +--------------v-----------+
        | ClaudeExec | --| Issue Pipeline           |
        | (lib/py)   |   | Webhook Trigger          |
        +-----+------+   | Batch Runner             |
              |           | Notifications            |
              |           +--------------------------+
              |
        +-----v------+
        | Agent Bus  |
        | (Valkey    |
        |  pub/sub)  |
        +------------+
```

### Agent Communication Bus

The Agent Bus (`lib/agent_bus.py`) provides bidirectional real-time communication between agents and the orchestrator using Valkey (Redis-compatible) pub/sub channels. It enables heartbeat monitoring (5s interval, 15s timeout), progress tracking on each tool use, clarification request/answer flows, and control commands (stop/pause/resume). When Valkey is unavailable, it falls back to file-based signaling under `.cognitive-os/agent-bus/`. The terminal dashboard (`lib/agent_dashboard.py`) subscribes to all channels and displays live agent status. Enable with `AGENT_BUS_ENABLED=true`.

---

## The MAPE-K Loop

Cognitive OS implements a MAPE-K (Monitor, Analyze, Plan, Execute, Knowledge) autonomous control loop. This is the core self-healing and self-improvement mechanism.

```
+--------+     +---------+     +------+     +---------+
|MONITOR |---->| ANALYZE |---->| PLAN |---->| EXECUTE |
+--------+     +---------+     +------+     +---------+
     ^                                           |
     |              +----------+                 |
     +--------------| KNOWLEDGE|<----------------+
                    +----------+

MONITOR:   Hooks capture metrics, errors, and events in real time
ANALYZE:   Pattern detectors classify events (3+ same error = pattern)
PLAN:      Singularity routes events to the right pipeline
EXECUTE:   ClaudeExecutor launches agents via CLI subprocess
KNOWLEDGE: Engram stores outcomes for future reference
```

### Concrete implementation:

| MAPE-K Phase | Cognitive OS Component |
|--------------|----------------------|
| Monitor | `error-learning.sh`, `skill-tracker.sh`, `kpi-trigger.sh`, `doc-sync-detector.sh` |
| Analyze | `error-pattern-detector.sh`, `epic-task-detector.sh`, `singularity.py` event classification |
| Plan | `singularity.py` pipeline routing, `sdd_resume.py` phase planning, `domain_router.py` |
| Execute | `claude_executor.py`, `issue_pipeline.py`, `batch_runner.py` |
| Knowledge | Engram (`mem_save`, `mem_search`), metrics JSONL files, remediation registry |

---

## Pipeline Flow: Issue to PR

The complete automation pipeline from GitHub issue to merged pull request:

```
GitHub Issue #42 ("Add password reset flow")
    |
    v
[1] Webhook Trigger (lib/webhook_trigger.py)
    Receives GitHub webhook, validates HMAC signature,
    detects trigger keywords, classifies issue
    |
    v
[2] Issue Pipeline (lib/issue_pipeline.py)
    Fetches issue data via `gh` CLI,
    creates git worktree for isolation
    |
    v
[3] SDD Pipeline (skills/sdd-*)
    explore -> propose -> spec -> design -> tasks
    |
    v
[4] Apply Phase (skills/sdd-apply)
    Sub-agent implements tasks in worktree,
    runs PITER loop (implement -> test -> evaluate -> refine)
    |
    v
[5] Verify Phase (skills/sdd-verify)
    Adversarial review against spec,
    verify-apply retry loop (max 3)
    |
    v
[6] PR Creation
    `gh pr create` with summary from SDD artifacts
    |
    v
[7] Notification
    Telegram/Slack/webhook notification with PR link
    |
    v
[8] Archive
    Lessons learned saved to Engram
```

---

## Component Inventory

### Hooks (57)

Hooks are bash scripts that intercept Claude Code tool calls at four lifecycle points.

| Lifecycle Point | Count | Key Hooks |
|----------------|-------|-----------|
| **SessionStart** | 8 | `session-init`, `session-resume`, `stack-detector`, `self-install`, `inject-phase-context`, `engram-auto-import` |
| **PreToolUse** | 10 | `error-pattern-detector`, `completeness-check`, `epic-task-detector`, `agent-prelaunch`, `resource-check`, `pre-cleanup-snapshot`, `guardrails-validator`, `semgrep-scan` |
| **PostToolUse** | 24 | `error-learning`, `auto-verify`, `auto-refine`, `skill-tracker`, `trust-score-validator`, `dod-gate`, `secret-detector`, `doc-sync-detector`, `auto-skill-generator`, `result-truncator`, `agent-bus-monitor`, `observability-trace` |
| **Stop** | 5 | `session-cleanup`, `kpi-trigger`, `session-learning`, `pre-compaction-flush`, `jupyter-sandbox` |
| **Shared library** | - | `hooks/_lib/` (common functions) |

### Rules (55)

Rules are always-on behavioral contracts in Markdown.

| Category | Rules |
|----------|-------|
| **Quality** | agent-quality, acceptance-criteria, definition-of-done, trust-score, adversarial-review, closed-loop-prompts |
| **Safety** | license-policy, credential-management, secret-hygiene, capability-protection |
| **Governance** | phase-aware-agents, resource-governance, cost-tracking, model-routing, agent-kpis |
| **Memory** | engram-organization, context-management, context-optimization, fault-tolerance |
| **Process** | plan-first, cognitive-os-changes, dogfooding, step-files, result-management |
| **Self-improvement** | error-learning, auto-skill-generation, self-improvement-protocol, metrics-calibration, skill-management |
| **Organization** | squad-protocol, agent-identity, agent-customization, agent-sidecars, session-concurrency |
| **Detection** | infra-intent, sandbox-sampling, auto-repair, library-selection |
| **Compatibility** | model-compatibility, os-vs-project, doc-sync, prompt-composition |
| **Special** | private-mode |

### Skills (72)

Skills are domain-specific knowledge packages.

| Category | Skills |
|----------|--------|
| **SDD Phases** | sdd-continue, sdd-resume, singularity |
| **Planning** | plan-feature, plan-bug, evaluate-plan, readiness-check |
| **Quality** | dod-check, exhaustive-prompt, sandbox-sample, trust-audit, verification-before-completion |
| **Testing** | cognitive-os-test, compat-test, test-driven-development |
| **Self-improvement** | self-improve, error-analyzer, model-optimizer (now called resource-governor) |
| **Operations** | sre-agent, cognitive-os-status, repair-status, resolve-blockers |
| **Memory** | conversation-memory, session-manager, resume-tasks |
| **Organization** | squad-manager, retrospective, agent-kpis, sprint |
| **Development** | doc-sync, coverage-enforcement, recommend-library, skill-creator (now called compose-prompt) |
| **Automation** | issue-pipeline, webhook-trigger, batch-runner, singularity |
| **Infrastructure** | cognitive-os-init, validate-config, capability-snapshot, tool-discovery |
| **Evaluation** | arena, eval-repo, cognitive-os-benchmark |
| **Auto-generated** | Created automatically by `auto-skill-generator.sh` after complex tasks |

### Squads

Squads organize agents into teams with governance policies.

| Squad | Domain |
|-------|--------|
| `platform-team` | Core infrastructure, shared libraries |
| `payments-team` | Payment processing, billing |
| `mobile-team` | Mobile app, React Native |
| `infra-team` | DevOps, CI/CD, Docker |
| `organization.yaml` | Cross-squad governance |

### Agents

Persistent agent definitions with specific roles:

| Agent | Role |
|-------|------|
| `service-health-checker` | Monitor service health |
| `stack-validator` | Validate technology stack compliance |
| `test-coverage-enforcer` | Enforce test coverage thresholds |

### Library Modules (22 Python modules)

| Module | Purpose |
|--------|---------|
| `agent_bus.py` | Bidirectional real-time agent communication via Valkey pub/sub |
| `agent_dashboard.py` | Terminal dashboard for live agent status monitoring |
| `batch_runner.py` | Batch execution of multiple pipelines |
| `capability_levels.py` | Auto-disable components based on model capability level |
| `claude_executor.py` | Programmatic Claude Code invocation via CLI subprocess |
| `cognee_client.py` | Client for Cognee knowledge graph and RAG engine |
| `domain_router.py` | Route issues to the right squad/pipeline |
| `guardrails_validators.py` | NeMo Guardrails validation helpers |
| `impact_analysis.py` | Change impact analysis: importers, coverage, risk classification |
| `issue_pipeline.py` | GitHub issue to PR automation |
| `jupyter_client.py` | Client for Jupyter notebook execution sandbox |
| `litellm_client.py` | Client for LiteLLM model routing and cost tracking |
| `model_router.py` | Dynamic multi-provider model selection and cost estimation |
| `notifications.py` | Telegram, Slack, webhook notifications |
| `observability.py` | Unified observability: Langfuse and Opik tracing integration |
| `paperclip_client.py` | Client for Paperclip governance dashboard |
| `phase_timing.py` | Phase duration tracking and estimation |
| `sdd_resume.py` | SDD state management and phase continuation |
| `session_state.py` | Session state persistence with atomic writes |
| `singularity.py` | MAPE-K autonomous controller |
| `web_crawler.py` | Web content extraction via Crawl4AI (markdown, structured, crawl) |
| `webhook_trigger.py` | FastAPI server for GitHub webhooks |

---

## Technology Stack

```
+------------------------------------------------------------------+
|                        TECHNOLOGY LAYERS                          |
+------------------------------------------------------------------+
|                                                                   |
|  RUNTIME        Claude Code CLI + Claude Opus 4.6 (1M context)   |
|                                                                   |
|  HOOKS          Bash (57 scripts, <100ms each, zero deps)        |
|                                                                   |
|  RULES          Markdown (55 files, loaded progressively)        |
|                                                                   |
|  SKILLS         Markdown (72 SKILL.md files, 3-level loading)    |
|                                                                   |
|  LIBRARY        Python 3.9+ (stdlib-only where possible)         |
|                 FastAPI (webhook server only)                     |
|                                                                   |
|  CLI TOOLS      Go 1.21+ (cos-test TUI binary)                  |
|                                                                   |
|  PERSISTENCE    Engram (SQLite via MCP, WAL mode)                |
|                 JSONL metrics files (append-only)                 |
|                 active-tasks.json (session state)                 |
|                                                                   |
|  TESTING        pytest + testcontainers (Python)                 |
|                 bash assertion scripts (infrastructure)           |
|                 promptfoo (LLM-evaluated quality)                |
|                                                                   |
|  CI/CD          GitHub Actions (PR review, issue triage)         |
|                 gh CLI (issue/PR operations)                     |
|                                                                   |
|  OPTIONAL       Langfuse (observability)                         |
|  INFRA          LiteLLM (cost control)                           |
|                 NeMo Guardrails (content safety)                 |
|                 Paperclip (governance dashboard)                 |
|                                                                   |
+------------------------------------------------------------------+
```

### Why each technology:

| Technology | Why |
|-----------|-----|
| **Bash** for hooks | Claude Code hooks must be shell scripts. Fast startup (<100ms), no dependencies, runs everywhere. |
| **Markdown** for rules/skills | Directly consumed by the LLM. No parsing needed. Human-readable and version-controlled. |
| **Python** for library | Best ecosystem for HTTP servers, testing, JSON processing. Stdlib-only for core modules (no pip install). |
| **Go** for CLI | Single binary, no runtime. Fast compilation. Cross-platform. |
| **SQLite** for Engram | WAL mode supports concurrent readers. Single file. No server process needed. |
| **JSONL** for metrics | Append-only, no corruption risk. Easy to grep, jq, and tail. Git-friendly diffs. |

---

## Multi-Tool Adapter Architecture

Cognitive OS is designed for portability across AI coding tools. The adapter layer translates tool-specific formats (hooks, settings, rules) while the core remains tool-agnostic.

```
                    Cognitive OS
                         |
          +--------------+--------------+
          |              |              |
     Claude Code     OpenCode      Aider/Cursor
          |              |              |
     adapters/cc    adapters/oc    adapters/cursor
          |              |              |
          +--------------+--------------+
                         |
              +----------+----------+
              |          |          |
          Python libs   MCP     Docker infra
          (agnostic)  (universal) (agnostic)
```

### Portability Layers

| Layer | Portable? | Notes |
|-------|-----------|-------|
| **Python libs** (lib/*.py) | Yes | No tool-specific code. model_router, cost_dashboard, singularity all work with any caller. |
| **MCP servers** (Engram, Context7) | Yes | MCP is a universal protocol. Works with Claude Code, Cursor, Continue, Cline. |
| **Docker infrastructure** | Yes | docker-compose is tool-agnostic. |
| **Hooks** (hooks/*.sh) | No -- adapter needed | Claude Code hooks format. Adapters translate to other tool formats. |
| **Rules** (rules/*.md) | Partially | Markdown is universal but .claude/rules/ path is Claude Code-specific. Adapters map to .cursorrules, .aider, etc. |
| **Skills** (skills/*/SKILL.md) | Partially | Content is universal but invocation mechanism varies by tool. |

---

## Data Flow

### Write paths (data enters the system)

```
Tool Call
    |
    +--[PostToolUse hooks]
    |   |
    |   +-- error-learning.sh      -> metrics/error-learning.jsonl
    |   +-- skill-tracker.sh       -> metrics/skill-metrics.jsonl
    |   +-- trust-score-validator  -> metrics/trust-scores.jsonl
    |   +-- doc-sync-detector.sh   -> metrics/stale-docs.jsonl
    |   +-- auto-verify.sh         -> metrics/auto-verify.jsonl
    |   +-- secret-detector.sh     -> metrics/missing-secrets.jsonl
    |
    +--[Agent completion]
    |   |
    |   +-- mem_save               -> Engram (SQLite)
    |   +-- mem_session_summary    -> Engram (SQLite)
    |
    +--[Session lifecycle]
        |
        +-- session-init.sh        -> sessions/{id}/meta.json
        +-- agent-prelaunch.sh     -> tasks/active-tasks.json
        +-- agent-checkpoint.sh    -> tasks/active-tasks.json
        +-- kpi-trigger.sh         -> metrics/kpi-history.jsonl
```

### Read paths (data exits the system)

```
Session Start
    |
    +-- engram-auto-import.sh   <- Engram (SQLite)
    +-- session-resume.sh       <- tasks/active-tasks.json
    +-- stack-detector.sh       <- package.json, go.mod, etc.
    +-- inject-phase-context.sh <- cognitive-os.yaml

Agent Launch
    |
    +-- error-pattern-detector  <- metrics/error-learning.jsonl
    +-- completeness-check.sh   <- (inspects prompt content)
    +-- resource-check.sh       <- metrics/cost-events.jsonl

Singularity Controller
    |
    +-- singularity.py          <- metrics/*.jsonl, GitHub API, Engram
```

### Engram topic key hierarchy

```
Engram
  |
  +-- planning/
  |     +-- {change}/proposal
  |     +-- {change}/spec
  |     +-- {change}/design
  |     +-- {change}/tasks
  |     +-- {change}/state
  |     +-- {change}/verify-report
  |
  +-- implementation/
  |     +-- {service}/patterns
  |     +-- {change}/apply-progress
  |
  +-- architecture/
  |     +-- {topic}
  |
  +-- bugfix/
  |     +-- {service}/{issue}
  |
  +-- agent/
  |     +-- {agent-name}/sidecar
  |
  +-- config/
  |     +-- {project}/sdd-init
  |
  +-- sre/
        +-- {container}/{error-type}
```

---

## Configuration

All behavior is driven by `cognitive-os.yaml` at the project root.

Key sections:

| Section | What It Controls |
|---------|-----------------|
| `project.phase` | Agent behavior (reconstruction/stabilization/production/maintenance) |
| `project.infrastructure` | Detected services, ports, databases |
| `phases.*` | Per-phase behavioral flags |
| `environment.tool` | Dev environment (devbox, nix, etc.) |
| `resources.budget` | Daily/monthly cost limits |
| `resources.compute` | Max parallel agents, timeouts |
| `resources.tokens` | Context management thresholds |
| `skills.loading` | Progressive loading configuration |
| `rules.loading` | Compact vs full rule loading |
| `sessions` | Concurrency, locking, cleanup |
| `self_improvement` | Auto-improvement limits and guards |

The configuration file is the single source of truth. Hooks, rules, and skills read from it at runtime.

---

## Self-Improvement Architecture

```
                    EXECUTION
                       |
                       v
+----------+    +------------+    +-----------+
| Error     |--->| Pattern    |--->| Skill     |
| Learning  |    | Detection  |    | Adaptation|
| (capture) |    | (classify) |    | (improve) |
+----------+    +------------+    +-----------+
                       |
                       v
              +----------------+
              | Self-Improve   |
              | Protocol       |
              | (rules/skills) |
              +--------+-------+
                       |
              +--------v-------+
              | /cognitive-os  |
              |     -test      |
              | (validate)     |
              +--------+-------+
                       |
               PASS -> Commit
               FAIL -> Revert
```

The self-improvement loop:

1. **Capture**: `error-learning.sh` logs every test/lint/build failure to JSONL
2. **Detect**: `error-pattern-detector.sh` identifies patterns (3+ same error in 24h)
3. **Analyze**: `/error-analyzer` groups patterns by root cause
4. **Improve**: `/self-improve` proposes rule/skill updates
5. **Validate**: `/cognitive-os-test` verifies no capabilities were lost
6. **Apply or revert**: Safe changes auto-apply; risky changes need human approval

Safety guards: max 5 improvements per run, mandatory test gate, no deletions, 24-hour cooldown, improvement blocklist for failed attempts.
