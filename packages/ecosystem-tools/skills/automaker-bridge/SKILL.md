<!-- SCOPE: os-only -->
---
name: automaker-bridge
description: Configure AutoMaker to use Cognitive OS as its execution brain
version: 1.0.0
last-updated: 2026-03-24
user-invocable: true
auto-generated: false
trigger: automaker, setup automaker, kanban, visual board, automaker bridge
model: sonnet
audience: os-dev
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bautomaker[- ]?bridge\b
  confidence: 0.95
- pattern: \bautomaker\s+(config|setup|integration)\b
  confidence: 0.8
summary_line: Configure AutoMaker to use Cognitive OS as its execution brain.
routing_intents:
- intent: automaker_bridge_request
  description: User asks to configure AutoMaker to use Cognitive OS as its execution brain.
  confidence: 0.85
---

# AutoMaker Bridge

Configure a project so AutoMaker's Kanban tasks are executed with Cognitive OS governance (hooks, rules, quality gates, auto-repair).

## How It Works

```
AutoMaker Kanban --> User moves task to "In Progress"
       |
       v
AutoMaker launches Claude Code session in git worktree
       |
       v
COS hooks fire automatically (.cognitive-os/ exists):
  - SessionStart: health check, metrics rotation
  - PreToolUse:   completeness check, phase context
  - PostToolUse:  error learning, auto-repair, trust score
       |
       v
Agent completes task under COS governance
       |
       v
AutoMaker shows results in Kanban UI
```

AutoMaker launches Claude Code agents in isolated git worktrees. Because COS hooks live in `.claude/hooks/` and COS config lives in `.cognitive-os/`, every agent session inherits the full governance stack automatically. No custom launcher needed.

## Execution Protocol

### Step 1: Verify Prerequisites

Check that all required components are available:

```bash
# AutoMaker: check CLI or running instance
which automaker 2>/dev/null || curl -sf http://localhost:4200 >/dev/null 2>&1
# Result: AutoMaker available / not found

# Cognitive OS: config directory must exist
test -d ".cognitive-os" && test -f ".cognitive-os/cognitive-os.yaml"
# Result: COS initialized / not initialized (run cognitive-os-init first)

# Git repo: required for worktree isolation
git rev-parse --git-dir >/dev/null 2>&1
# Result: Git repo / not a repo
```

If COS is not initialized, instruct the user to run `/cognitive-os-init` first.
If AutoMaker is not installed, provide installation instructions from the AutoMaker repo.

### Step 2: Create Bridge Config

Create `.automaker/cognitive-os.json` in the project root. This file tells any AutoMaker-aware tooling that COS governance is active.

```json
{
  "bridge": {
    "enabled": true,
    "cognitive_os_path": ".cognitive-os",
    "hooks_active": true,
    "phase_gate": true,
    "auto_repair": true,
    "quality_gates": ["build", "test", "lint"],
    "metrics_sync": {
      "enabled": true,
    }
  }
}
```

**Fields:**

| Field | Purpose |
|-------|---------|
| `enabled` | Master switch for bridge integration |
| `cognitive_os_path` | Relative path to COS config directory |
| `hooks_active` | Whether COS hooks should fire during AutoMaker sessions |
| `phase_gate` | Enforce phase-based Definition of Done before task completion |
| `auto_repair` | Enable MAPE-K auto-repair loop on errors |
| `quality_gates` | Array of gate names that must pass before a task is marked done |

### Step 3: Create AutoMaker Agent Profile

AutoMaker uses agent profiles to configure how Claude agents behave. Create a `cognitive-os` profile that injects COS rules.

Write `.automaker/agents/cognitive-os.md`:

```markdown
# Cognitive OS Agent Profile

You are an agent operating under Cognitive OS governance.

## Before starting work
- Read `.cognitive-os/cognitive-os.yaml` for the current phase and infrastructure config
- Identify the task's complexity level (S / M / L / XL) to determine the Definition of Done

## During work
- Follow the rules in `.claude/rules/` -- they are loaded automatically
- If you encounter an error, check the remediation registry before retrying blindly
- Use skills from `.claude/skills/` when they match the task type

## Before marking a task as done
Run all quality gates for the detected stack:

1. **Build**: `go build ./...` / `npm run build` / `mvn compile` (as appropriate)
2. **Test**: `go test ./...` / `npm test` / `mvn test` (as appropriate)
3. **Lint**: `golangci-lint run` / `npm run lint` / project linter (as appropriate)
4. **Architecture compliance**: Verify changes follow patterns in `.claude/rules/`

## On completion
- Register a trust score for the work done
- If you fixed an error, register it in the remediation registry via the error-analyzer skill
- Provide a session summary with what was accomplished and any risks
```

### Step 4: Verify Integration

After creating the config files, verify the integration works:

1. Confirm `.automaker/cognitive-os.json` is valid JSON
2. Confirm `.automaker/agents/cognitive-os.md` exists and is non-empty
3. Confirm `.cognitive-os/cognitive-os.yaml` exists (COS is initialized)
4. Confirm `.claude/hooks/` directory exists with hook scripts
5. If AutoMaker is running, suggest the user create a test task to validate the full flow

### Step 5: Report

Output a summary:

```
AutoMaker Bridge configured:
  Bridge config:   .automaker/cognitive-os.json
  Agent profile:   .automaker/agents/cognitive-os.md
  COS config:      .cognitive-os/cognitive-os.yaml
  Hooks active:    yes
  Quality gates:   build, test, lint
  Metrics sync:    enabled -> http://localhost:3456

Next steps:
  1. Start AutoMaker (automaker or http://localhost:4200)
  2. Create a task on the Kanban board
  3. Move it to "In Progress" -- COS governance activates automatically
```

## Docker Integration

For projects using Docker, AutoMaker can be added to `docker-compose.cognitive-os.yml`.
This is documented here for reference but should NOT be applied automatically -- it is a separate infrastructure decision that requires user approval.

```yaml
# Add to docker-compose.cognitive-os.yml
automaker:
  # No stable public GHCR image as of 2026-05-04. Clone upstream and use its
  # source-build Docker Compose flow until a public digest exists.
  build: /path/to/automaker
  container_name: cognitive-os-automaker
  restart: unless-stopped
  ports:
    - "${AUTOMAKER_PORT:-4200}:4200"
  volumes:
    - .:/workspace
  environment:
    - CLAUDE_API_KEY=${CLAUDE_API_KEY}
    - ALLOWED_ROOT_DIRECTORY=/workspace
    - DATA_DIR=/workspace/.automaker/data
  networks:
    - cognitive-os-network
```

**Important**: The Docker approach mounts the entire project as `/workspace`, so COS hooks in `.claude/hooks/` are available inside the container. The agent profile at `.automaker/agents/cognitive-os.md` is also accessible.

## Notes

- AutoMaker is v0.x software. Pin the Docker image tag in production rather than using `:latest`.
- Both AutoMaker and COS use git worktrees for isolation. They use separate base directories and do not conflict: AutoMaker manages its own worktrees, COS repair-worktree uses `.cognitive-os/worktrees/`.
- AutoMaker's REST API runs on port 3008 internally (3007 in headless web mode). The Kanban UI is served on port 4200.
