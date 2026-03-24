# Secret Detection (EnvGuard)

## Overview

EnvGuard is a suite of tools that ensures environment variable hygiene across the project:

1. **PostToolUse hook** (`secret-detector.sh`) — Runs on every `Edit|Write` to source files, detects new env var references without definitions
2. **Rules** (`secret-hygiene.md`) — Coding standards for env var management
3. **Audit skill** (`/secret-audit`) — Full cross-reference scan across all services

## Components

### 1. Secret Detector Hook

**File**: `.cognitive-os/hooks/secret-detector.sh`
**Trigger**: PostToolUse on `Edit|Write` to source files (`.ts`, `.go`, `.java`)
**Behavior**:
- Scans edited file for env var reference patterns:
  - `process.env.X` (TypeScript/Node)
  - `os.Getenv("X")` (Go)
  - `System.getenv("X")` (Java)
  - `@Value("${X}")` (Spring Boot)
- Cross-references found vars against `.env`, `.env.example`, `docker-compose.yml`, `dev.env`, config files
- If a referenced var has no definition anywhere: outputs WARNING
- Logs missing vars to `.cognitive-os/metrics/missing-secrets.jsonl`

**Skips**: `.md`, `.json`, `.yaml`, `.yml`, `.lock`, `.sum`, `.sh` files, and anything in `.cognitive-os/` or `.claude/`

### 2. Secret Hygiene Rules

**File**: `.cognitive-os/rules/secret-hygiene.md`
**Key rules**:
- Every new env var must be added to `.env.example`
- Never hardcode secrets in source
- Use `PROVIDER_*` naming pattern for external service credentials
- Docker Compose env sections must mirror `.env.example`
- Mock flags follow `PROVIDER_MOCK` pattern

### 3. Secret Audit Skill

**File**: `.cognitive-os/skills/secret-audit/SKILL.md`
**Invoke**: `/secret-audit`
**What it does**:
- Scans all Go, TypeScript, and Java services for env var usage
- Collects all env var definitions from `.env*`, `docker-compose*.yml`, `dev.env`
- Cross-references to find:
  - **Used but undefined** — needs action
  - **Defined but unused** — review for cleanup
  - **Hardcoded values** — security risk
- Generates structured report

## Metrics

Missing secrets are logged to `.cognitive-os/metrics/missing-secrets.jsonl`:

```json
{"timestamp":"2026-03-22T10:00:00Z","file":"src/app.ts","var":"NEW_API_KEY","status":"missing"}
```

## Registration

- Hook registered in `settings.local.json` under `PostToolUse` matcher `Edit|Write`
- Rule loaded contextually on `secret|env|credential` triggers
- Skill in CATALOG.md as `/secret-audit`
