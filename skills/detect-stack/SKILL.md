<!-- SCOPE: both -->
---
name: detect-stack
description: Scan a project root and produce detected-stack.json with detected languages, frameworks, databases, auth, cache, messaging, and services.
version: 0.1.0
audience: both
tags: [init, setup, detection]
summary_line: Scan a project root and produce detected-stack.json with detected languages…

platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\bdetect[- ]?stack\b'
    confidence: 0.95
  - pattern: '\bscan\s+project\s+(stack|tech)\b'
    confidence: 0.85
  - pattern: '\bdetected[- ]?stack\b'
    confidence: 0.8
---

# Detect Stack

Scan the current project directory for stack indicators and write a machine-readable `detected-stack.json` to `.cognitive-os/`.

## What It Does

Reads project files (`go.mod`, `package.json`, `docker-compose.yml`, `pom.xml`, etc.) and produces a structured JSON artifact consumed by `/generate-config` and `/scaffold-project`.

## Invocation

```
/detect-stack
```

No required arguments. Run from the project root.

## Execution Protocol

### Step 1: Detect Languages and Frameworks

Scan the project root for these indicator files:

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

For each detected language/framework, record:
- `language`: primary language (go, node, java, python, rust)
- `framework`: detected framework (nestjs, express, nextjs, expo, spring-boot, etc.)
- `version`: version from the manifest file if present

### Step 2: Detect Infrastructure

Scan `docker-compose.yml` and `docker-compose.*.yml` for service images:

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

For each detected service in `docker-compose.yml` that has a `build` context, record:
- `name`: service name
- `path`: source directory (from `build.context`)
- `port`: first port mapping (host side)
- `language`: infer from path and Dockerfile if present

### Step 3: Detect Project Type

Classify the project based on service names and code signals:

| Signal | Classified As |
|--------|--------------|
| Payment/wallet/transfer in service names or code | fintech |
| Cart/product/order/inventory in service names or code | ecommerce |
| Patient/medical/health/prescription in code | healthcare |
| Multi-tenant, subscription, billing | saas |
| Default | webapp |

### Step 4: Detect Project Name

Use in priority order:
1. `name` field from `package.json` (root)
2. Module name from `go.mod`
3. Current directory name

### Step 5: Write Output

Write `.cognitive-os/detected-stack.json`:

```json
{
  "project_name": "my-project",
  "project_type": "fintech",
  "languages": [
    { "language": "go", "framework": null, "version": "1.22" }
  ],
  "infrastructure": {
    "database": [{ "name": "postgres", "port": 5432 }],
    "cache": [{ "name": "valkey", "port": 6379 }],
    "messaging": [],
    "auth": [{ "name": "keycloak", "port": 8080 }],
    "storage": [],
    "search": [],
    "proxy": []
  },
  "services": [
    { "name": "api", "path": "apps/api", "port": 3000, "language": "go" }
  ],
  "detected_at": "ISO-8601 timestamp"
}
```

### Step 6: Report

Output a summary:

```
== Detect Stack Complete ==

Project: my-project (fintech)
Languages: Go 1.22
Infrastructure: PostgreSQL (5432), Valkey (6379), Keycloak (8080)
Services: 3 detected (api:3000, users:3001, payments:3002)

Output: .cognitive-os/detected-stack.json

Next: Run /generate-config to produce cognitive-os.yaml
```

## Output Contract

Produces `.cognitive-os/detected-stack.json` — the sole output artifact. This file is the input contract for `/generate-config` and `/scaffold-project`.

## Error Handling

- If no stack indicator files are found, write a minimal JSON with defaults and warn.
- If `docker-compose.yml` is not present, set `services: []` and warn.
- Never fail silently — always output the JSON even if mostly empty.
