# Cognitive OS -- Plug-and-Play Architecture

> How to add a full AI agent operating system to ANY project with 1 file and 1 command.

## Quick Start

```bash
# In any project root:
cp path/to/cognitive-os/docker-compose.cognitive-os.yml .
docker compose -f docker-compose.cognitive-os.yml up -d

# Done. Cognitive OS is running with:
# - Langfuse (observability)        on port 3100
# - LiteLLM (cost control)          on port 4000
# - NeMo Guardrails (security)      on port 8088
```

No code changes. No framework lock-in. No vendor dependency.

## Architecture: 3-Layer Docker Compose

The Cognitive OS uses a layered Docker Compose architecture. Each layer is independent and composable.

```
docker-compose.yml               # Layer 1: Infrastructure (DB, cache, queues)
docker-compose.services.yml      # Layer 2: Application services (your app)
docker-compose.cognitive-os.yml      # Layer 3: Cognitive OS (observability, cost, security, governance)
```

### Layer 1: Infrastructure (`docker-compose.yml`)

Project-specific. Databases, caches, message brokers -- whatever the project needs.

```yaml
# Example for a typical project
services:
  postgres:
    image: postgres:16
    ports: ["5432:5432"]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  rabbitmq:
    image: rabbitmq:3-management
    ports: ["5672:5672", "15672:15672"]

networks:
  app-network:
    driver: bridge
```

### Layer 2: Application Services (`docker-compose.services.yml`)

Project-specific. Your microservices, BFF, workers.

```yaml
services:
  api:
    build: ./api
    ports: ["8080:8080"]
    networks: [app-network]
  worker:
    build: ./worker
    networks: [app-network]

networks:
  app-network:
    external: true
```

### Layer 3: Cognitive OS (`docker-compose.cognitive-os.yml`)

Universal. Same file works for any project.

```yaml
version: "3.8"

services:
  # Observability -- traces every LLM call, measures quality
  langfuse:
    image: langfuse/langfuse:latest
    ports: ["3100:3000"]
    environment:
      DATABASE_URL: postgresql://langfuse:langfuse@langfuse-db:5432/langfuse
      NEXTAUTH_SECRET: ${COGNITIVE_OS_SECRET:-changeme}
      NEXTAUTH_URL: http://localhost:3100
    depends_on: [langfuse-db]
    networks: [cognitive-os-network]

  langfuse-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: langfuse
      POSTGRES_PASSWORD: langfuse
      POSTGRES_DB: langfuse
    volumes: ["langfuse-data:/var/lib/postgresql/data"]
    networks: [cognitive-os-network]

  # Cost Control -- routes LLM calls, enforces budgets
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    ports: ["4000:4000"]
    volumes: ["./cognitive-os/litellm-config.yaml:/app/config.yaml"]
    command: ["--config", "/app/config.yaml"]
    networks: [cognitive-os-network]

  # Security -- guardrails on every LLM interaction
  nemo-guardrails:
    image: nvcr.io/nvidia/nemo-guardrails:latest
    ports: ["8088:8088"]
    volumes: ["./cognitive-os/guardrails:/config"]
    networks: [cognitive-os-network]

  # Governance UI -- dashboard for agent performance
    ports: ["3200:3000"]
    environment:
      LANGFUSE_URL: http://langfuse:3000
      LITELLM_URL: http://litellm:4000
    networks: [cognitive-os-network]

networks:
  cognitive-os-network:
    driver: bridge
  # Connect to the project's network if needed:
  # app-network:
  #   external: true

volumes:
  langfuse-data:
```

## Network Sharing

Projects connect to Cognitive OS via a shared Docker network.

```yaml
# In docker-compose.cognitive-os.yml, add:
networks:
  shared-network:        # or any custom name
    external: true
  cognitive-os-network:
    driver: bridge

# In your project's docker-compose.yml:
networks:
  shared-network:
    driver: bridge
```

This allows application services to send LLM requests through LiteLLM for cost tracking, and Cognitive OS services to observe application behavior without modifying application code.

### Network Topology

```
┌─────────────────────────────────────────────────┐
│                  shared-network                    │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ your-api │  │ your-bff │  │ your-workers │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │              │               │           │
│       └──────────────┼───────────────┘           │
│                      │                           │
│              ┌───────▼───────┐                   │
│              │   LiteLLM     │ (cost routing)    │
│              │   :4000       │                   │
│              └───────┬───────┘                   │
│                      │                           │
│              ┌───────▼───────┐                   │
│              │   Langfuse    │ (observability)    │
│              │   :3100       │                   │
│              └───────────────┘                   │
│                                                  │
│  ┌───────────────┐  ┌────────────────────────┐  │
│  │ Guardrails    │  │ (governance dashboard) │  │
│  │ :8088         │  │ :3200                  │  │
│  └───────────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## Configuration: `cognitive-os.yaml`

Every project using Cognitive OS has a single configuration file at the project root.

```yaml
# cognitive-os.yaml
version: "1.0"

project:
  name: "my-project"
  phase: "reconstruction"        # reconstruction | stabilization | production | maintenance
  engram_namespace: "my-project" # Engram memory isolation (see engram-namespaces.md)

observability:
  langfuse:
    enabled: true
    port: 3100
    trace_all_llm_calls: true

cost_control:
  litellm:
    enabled: true
    port: 4000
    monthly_budget: 500          # USD
    per_agent_budget: 2.00       # USD per task
  model_routing:
    default: "sonnet"
    reasoning: "opus"
    documentation: "haiku"

security:
  nemo_guardrails:
    enabled: true
    port: 8088
    block_pii: true
    block_prompt_injection: true

governance:
    enabled: true
    port: 3200

quality_gates:
  test_coverage_minimum: 80
  architecture_compliance: true
  license_check: true

squads:
  enabled: false                 # Enable squad system for team projects
  config: ".claude/squads/"
```

### Phase System

The `project.phase` field controls agent behavior globally:

| Phase | Agent Behavior |
|-------|---------------|
| `reconstruction` | Rewrite freely. Break patterns. No backward compatibility concerns. |
| `stabilization` | Follow standards strictly. Maintain compatibility where possible. |
| `production` | Feature flags required. No breaking changes. Document proposals. |
| `maintenance` | Bug fixes and security patches only. Minimal changes. |

Phase transitions are manual (edit `cognitive-os.yaml`). Agents read the phase on every task and adjust their approach.

## Skills Portability

Skills are the Cognitive OS's reusable procedures. They follow a universal `SKILL.md` format that works across any project.

### SKILL.md Standard

```markdown
---
name: systematic-debugging
version: 1.2.0
description: Root-cause analysis with bisection
tags: [debugging, analysis]
model: opus
---

# Systematic Debugging

## When to Use
- Production bug with unclear root cause
- Test failure that resists simple fixes

## Procedure
1. Reproduce the issue
2. Bisect to find the failing component
3. Analyze root cause
4. Propose fix with test
5. Verify fix resolves the original issue

## Inputs
- Bug description or error message
- Affected service/file (if known)

## Outputs
- Root cause analysis
- Fix implementation
- Verification test
```

### Portability Guarantees

| Aspect | Portable? | Notes |
|--------|-----------|-------|
| SKILL.md format | Yes | Plain markdown with YAML frontmatter |
| Skill logic | Yes | Procedural instructions, no IDE-specific APIs |
| Skill location | Configurable | `.claude/skills/` default, customizable in `cognitive-os.yaml` |
| Project skills | Per-project | `.claude/skills/` -- checked into repo |
| Global skills | Per-user | `~/.claude/skills/` -- shared across projects |
| Auto-generated skills | Per-project | `.claude/skills/auto-generated/` -- created from successful complex tasks |

### Adding Skills to a New Project

```bash
# Copy universal skills
cp -r ~/.claude/skills/_shared/ .claude/skills/

# Or use skill-auto-loader to detect the stack and suggest skills
# The auto-loader reads detected-stack.json and maps technologies to skills
```

## Hooks Portability

Hooks are shell scripts triggered by agent lifecycle events. They provide extensibility without modifying the core system.

### Hook Architecture

```
.claude/hooks/
├── PreToolUse/           # Before any tool execution
│   ├── error-pattern-detector.sh
│   └── architecture-compliance.sh
├── PostToolUse/          # After any tool execution
│   ├── error-learning.sh
│   ├── skill-metrics-tracker.sh
│   └── auto-skill-generator.sh
├── PreCompact/           # Before context compaction
│   └── pre-compaction-flush.sh
└── Notification/         # On session events
    └── session-resume.sh
```

### Hook Portability

Hooks are plain shell scripts. They work on any POSIX system. Project-specific behavior is handled via JSON config adapters:

```json
// .claude/hooks/config.json
{
  "error-learning": {
    "commands": ["jest", "vitest", "go test", "gradlew test"],
    "output": ".claude/metrics/error-learning.jsonl"
  },
  "architecture-compliance": {
    "rules_path": ".claude/rules/",
    "phase_source": "cognitive-os.yaml"
  }
}
```

To add hooks to a new project, copy the hooks directory and adjust `config.json` for the project's tech stack.

## Squad System

For team projects, the squad system organizes agents into teams with defined responsibilities.

```yaml
# .claude/squads/payments-team.yaml
apiVersion: cognitive-os/v1alpha1
kind: Squad
metadata:
  name: payments-team
spec:
  repos:
    - services/acme-gateway
    - services/payments-go
  skills:
    - systematic-debugging
    - test-driven-development
  agents:
    - name: backend-agent
      count: 2
      model: sonnet
    - name: sre-agent
      count: 1
      model: sonnet
  governance:
    constitutional_gates: [gate-6-idempotent, gate-7-audit-trail]
    test_coverage_minimum: 85
```

Squads are optional. A solo developer gets the full Cognitive OS without defining any squads.

## Adding Cognitive OS to an Existing Project

### Step-by-Step

1. **Copy the compose file**
   ```bash
   cp cognitive-os/docker-compose.cognitive-os.yml ./
   ```

2. **Create the config**
   ```bash
   cat > cognitive-os.yaml << 'EOF'
   version: "1.0"
   project:
     name: "my-project"
     phase: "reconstruction"
     engram_namespace: "my-project"
   EOF
   ```

3. **Start Cognitive OS**
   ```bash
   docker compose -f docker-compose.cognitive-os.yml up -d
   ```

4. **Add Claude Code config** (optional, for AI agent integration)
   ```bash
   mkdir -p .claude/rules .claude/skills .claude/hooks
   # Copy universal rules and skills from the Cognitive OS template
   ```

5. **Connect your app's network** (optional, for LLM proxy)
   ```bash
   docker network connect cognitive-os_cognitive-os-network your-api-container
   ```

### What You Get

| Component | Port | What It Does |
|-----------|------|-------------|
| Langfuse | 3100 | Traces every LLM call. Quality scores. Cost attribution. |
| LiteLLM | 4000 | Routes LLM calls. Enforces budgets. Model fallback chains. |
| NeMo Guardrails | 8088 | Blocks PII leaks. Prevents prompt injection. Content filtering. |

### What You DON'T Need

- No changes to your application code
- No new dependencies in your services
- No vendor SDK integration
- No cloud account required (everything runs locally)

## Engram Namespace Separation

Each project gets its own Engram namespace, preventing memory leaks between projects. See [engram-namespaces.md](engram-namespaces.md) for the full design.

```
cognitive-os          # Universal patterns (shared across ALL projects)
my-project        # Project-specific knowledge (NEVER shared)
cognitive-os-meta     # KPIs and metrics (shared for global improvement)
```

## Comparison: With vs Without Cognitive OS

| Capability | Without Cognitive OS | With Cognitive OS |
|-----------|-----------------|---------------|
| LLM cost tracking | None | Per-agent, per-task attribution |
| Error learning | Manual | Automatic pattern detection + prevention |
| Agent quality | Trust and hope | Measured, scored, improved |
| Security guardrails | Prompt-level only | Runtime content filtering + PII blocking |
| Skill reuse | Copy-paste | Registry + auto-loader + adaptation |
| Multi-agent coordination | Ad-hoc | Squad system with KPIs |
| Incident response | Manual | SRE auto-repair with known-fix database |
| Context loss | Every session | Engram persistent memory |
