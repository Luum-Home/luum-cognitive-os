# Project Backend AI Workflows

AI-powered pipeline orchestration for backend services. Multi-language support for Go, Spring Boot, NestJS, Express, and more.

## Quick Start

```bash
# Install dependencies
cd .cognitive-os/workflows
uv sync

# List available services
uv run python run.py services

# Run a feature pipeline
uv run python run.py feature --service accounts-go --ticket DEV-1234

# Run a bug fix pipeline
uv run python run.py bug --service example-api --ticket BUG-567

# Run a database migration
uv run python run.py migration --service example-go-service --description "add transfers table"

# Deploy a service
uv run python run.py deploy --service accounts-go --env staging

# Create a new Go service
uv run python run.py new-service --name analytics --port 3006

# Resume an interrupted workflow
uv run python run.py resume --workflow-id abc12345
```

## Pipelines

### Feature Pipeline (11 phases)

```
fetch -> branch -> plan -> evaluate -> apply -> implement -> build -> test -> lint -> commit -> pr
```

### Bug Fix Pipeline (11 phases)

```
fetch -> branch -> plan -> evaluate -> apply -> implement -> build -> test -> security -> commit -> pr
```

### Migration Pipeline (6 phases)

```
plan -> schema -> validate -> test -> review -> verify
```

### Deploy Pipeline (4 phases)

```
build -> test -> security -> deploy
```

### New Go Service Pipeline (4 steps)

```
scaffold -> register -> verify-build -> verify-tests
```

## Architecture

```
.cognitive-os/workflows/
  run.py                          # CLI entry point (click)
  backend_state.py                # Persistent workflow state
  backend_feature_pipeline.py     # Feature pipeline orchestrator
  backend_bug_pipeline.py         # Bug fix pipeline orchestrator
  backend_migration_pipeline.py   # Migration pipeline orchestrator
  backend_deploy_pipeline.py      # Deploy pipeline orchestrator
  go_service_pipeline.py          # New Go service creator
  lib/
    agent.py                      # Claude Code CLI wrapper
    data_types.py                 # Pydantic models (service types, state)
    shared_phases.py              # Multi-language build/test/lint/commit/PR
    clickup.py                    # ClickUp API client
    telegram.py                   # Telegram notifications
    git.py                        # Git operations
    file_parser.py                # Output parsing
    utils.py                      # Service detection, project root
  phases/
    plan.py                       # Plan generation
    evaluate.py                   # Soft-gate evaluation (0-50)
    apply.py                      # Apply evaluation fixes
    implement.py                  # Code generation
    security_check.py             # Constitutional gates + secrets + licenses
    migration_check.py            # DB migration validation
    deploy.py                     # Docker build + push + K8s/ArgoCD
  config/
    services.yaml                 # Service registry
    environments.yaml             # Environment configs
  state/                          # Workflow state persistence
  ai/
    plans/                        # Generated plans
    evaluations/                  # Evaluation results
```

## Multi-Language Support

| Language | Build | Test | Lint |
|----------|-------|------|------|
| Go | `go build ./...` | `go test ./...` | `golangci-lint run ./...` |
| Spring Boot | `./gradlew build` | `./gradlew test` | (none) |
| NestJS | `npx tsc --noEmit` | `npx jest --no-cache` | `npx eslint .` |
| Express | `npx tsc --noEmit` | `npx jest --no-cache` | `npx eslint .` |

## Key Patterns

### Soft-Gate Evaluation

Plans are scored 0-50. Score < 25 triggers the apply phase to fix the plan before implementation. The gate is soft -- it never blocks the pipeline, only improves plan quality.

### State Persistence + Resume

Every phase saves state to `state/{workflow-id}/workflow_state.json`. If a pipeline fails at any phase, resume from where it left off:

```bash
uv run python run.py resume --workflow-id abc12345
uv run python run.py resume --workflow-id abc12345 --start-from build
```

### Security Checks

The security_check phase validates:
1. Constitutional gates compliance (project-specific rules)
2. Hardcoded secrets detection
3. License policy for new dependencies

### Notifications

Configure Telegram notifications via environment variables:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Environment Variables

```bash
# Required only for workflows that call Anthropic-hosted Claude in CI
# Local/operator Claude Code sessions use native account auth instead.
ANTHROPIC_API_KEY=...

# Optional - ClickUp integration
CLICKUP_API_TOKEN=...
CLICKUP_TEAM_ID=...

# Optional - Telegram notifications
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Optional - Tuning
MAX_BUILD_FIX_ATTEMPTS=3
MAX_TEST_FIX_ATTEMPTS=3
CLAUDE_CODE_PATH=claude
```

## Adding a New Service

1. Add entry to `config/services.yaml`
2. Or use: `uv run python run.py new-service --name my-service --port 3007`
