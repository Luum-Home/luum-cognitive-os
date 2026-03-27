---
name: cognitive-os-init
description: Initialize Cognitive OS for a project. Detects stack, generates cognitive-os.yaml config, and creates project-specific skills/rules/hooks in {project}/.claude/.
version: 1.0.0
last-updated: 2026-03-22
user-invocable: true
auto-generated: false
---

# Cognitive OS Init

Initialize Cognitive OS for the current project. Detects your stack automatically and generates project-specific configuration.

## What It Does

1. **Detects** your project's language, framework, database, auth provider, messaging, and services
2. **Generates** `cognitive-os.yaml` with detected infrastructure
3. **Creates** project-specific files in `{project}/.claude/`:
   - Rules: architecture patterns, constitutional gates, service configs
   - Skills: SRE agent configured for this project's containers, health checks
   - Hooks: production URL blocking, auto-test with project's test commands

## Execution Protocol

### Step 1: Detect Project Stack

Scan the project root for stack indicators:

**Languages & Frameworks:**

| File | Detected Stack |
|------|---------------|
| `go.mod` | Go |
| `package.json` with `@nestjs/core` | NestJS (Node.js) |
| `package.json` with `express` | Express.js (Node.js) |
| `package.json` with `next` | Next.js (Node.js) |
| `package.json` with `react-native` or `expo` | React Native / Expo |
| `pom.xml` with `spring-boot` | Spring Boot (Java) |
| `build.gradle` with `spring-boot` | Spring Boot (Java/Kotlin) |
| `requirements.txt` or `pyproject.toml` | Python |
| `Cargo.toml` | Rust |

**Infrastructure (from docker-compose.yml or docker-compose.*.yml):**

| Image/Service Pattern | Detected Infrastructure |
|-----------------------|------------------------|
| `postgres` / `postgresql` | PostgreSQL database |
| `mysql` / `mariadb` | MySQL database |
| `mongo` / `mongodb` | MongoDB database |
| `redis` / `valkey` / `keydb` | Redis/Valkey cache |
| `rabbitmq` | RabbitMQ messaging |
| `kafka` / `redpanda` / `confluentinc` | Kafka messaging |
| `keycloak` | Keycloak auth |
| `auth0` | Auth0 auth |
| `elasticsearch` / `opensearch` | Search engine |
| `meilisearch` / `typesense` | Search engine |
| `minio` / `localstack` | S3-compatible storage |
| `nginx` / `traefik` / `caddy` | Reverse proxy |

**Services (from docker-compose.yml build contexts or service directories):**

For each service with a `build` context, extract:
- Service name
- Source directory (from `build.context`)
- Port (from `ports` mapping)

### Step 2: Generate cognitive-os.yaml

Update `cognitive-os.yaml` with detected values:

```yaml
project:
  name: {detected_from_directory_name_or_package_json}
  type: {auto_classify: fintech|ecommerce|saas|webapp|startup|healthcare}
  phase: reconstruction
  infrastructure:
    auth:
      name: {detected_auth_provider}
      port: {detected_port}
    database:
      - name: {detected_db}
        port: {detected_port}
    cache:
      name: {detected_cache}
      port: {detected_port}
    messaging:
      name: {detected_broker}
      port: {detected_port}
    services:
      - name: {service_name}
        path: {source_directory}
        port: {port}
        language: {detected_language}
```

Also populate `quality.gates` based on detected language:

**Go:** `go build ./...`, `golangci-lint run ./...`, `go test ./...`
**Node.js:** `npx tsc --noEmit`, `npx eslint .`, `npx jest --no-cache`
**Java:** `./gradlew build`, `./gradlew test`
**Python:** `python -m pytest`, `ruff check .`

And populate `rules.loading.contextual_triggers` based on detected stack.

### Step 3: Generate Project-Specific Rules

Create in `{project}/.claude/rules/`:

**architecture.md** -- Based on detected stack:
- For multi-service projects: document the communication flow (which services call which)
- For monoliths: document the module structure
- Read from existing code or docker-compose to detect service dependencies

**constitutional-gates.md** -- Based on project type:
- `fintech`: idempotency, audit trails, mock-before-integrate
- `ecommerce`: inventory consistency, payment mock-first
- `healthcare`: HIPAA compliance, data encryption, PHI audit
- `webapp` (default): test-before-merge, secrets-in-env-vars, backward-compatible-APIs

**services-config.md** -- From detected infrastructure:
- Port mapping for all services
- Default credentials (local only)
- Required environment variables

### Step 4: Generate Project-Specific Skills

Create in `{project}/.claude/skills/`:

**sre-agent-config/SKILL.md** -- SRE agent overlay with:
- Container-to-directory mapping for THIS project
- Port-to-service mapping
- Project-specific health check endpoints

**health-check/SKILL.md** -- Health check skill with:
- Endpoints for each detected service
- Expected response codes
- Dependency health chain

### Step 5: Generate Project-Specific Hooks

Create in `{project}/.claude/hooks/`:

**block-prod-urls.sh** -- Block production URLs:
- Detect production URLs from .env files or config
- Create hook that warns on usage of production URLs in local dev

### Step 6: Populate Workflow Config

Update `.cognitive-os/workflows/config/services.yaml` with detected services.

### Step 7: Report

Output a summary:

```
== Cognitive OS Init Complete ==

Detected stack:
  Language: {languages}
  Framework: {frameworks}
  Database: {databases}
  Auth: {auth_provider}
  Cache: {cache}
  Messaging: {messaging}
  Services: {count} services detected

Generated files:
  cognitive-os.yaml (updated)
  .claude/rules/architecture.md
  .claude/rules/constitutional-gates.md
  .claude/rules/services-config.md
  .claude/skills/sre-agent-config/SKILL.md
  .claude/skills/health-check/SKILL.md
  .cognitive-os/workflows/config/services.yaml

Next steps:
  1. Review generated files and adjust as needed
  2. Run /cognitive-os-test to verify configuration
  3. Run /sre-agent to verify service monitoring
```

## Project Type Auto-Classification

| Signal | Classified As |
|--------|--------------|
| Payment/wallet/transfer in service names or code | fintech |
| Cart/product/order/inventory in service names or code | ecommerce |
| Patient/medical/health/prescription in code | healthcare |
| Multi-tenant, subscription, billing | saas |
| Default | webapp |

## Important Notes

- This skill ONLY generates project-specific files in `.claude/` -- it does NOT modify Cognitive OS universal files
- Generated files are starting points -- they should be reviewed and customized
- Re-running `/cognitive-os-init` will regenerate files (with confirmation before overwriting)
- The skill is idempotent: running it twice produces the same result
