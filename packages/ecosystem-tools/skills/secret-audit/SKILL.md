---
name: secret-audit
description: Scan all services for env var usage, cross-reference with definitions,
  report gaps
invoke: /secret-audit
version: 1.0.0
model: sonnet
audience: project
summary_line: Scan all services for env var usage, cross-reference with definitions,
  report…
platforms:
- claude-code
prerequisites: []
routing_intents:
- audit environment variable usage across services
- find missing secret definitions across environment templates
- cross check env vars against configured secrets
- scan for secret configuration gaps before deployment
- report inconsistent environment variable references across services
triggers:
- secret-audit
- /secret-audit
- Secret Audit — Environment Variable Cross-Reference
- Scan all services for env var usage, cross-reference with definitions, report…
---
<!-- SCOPE: both -->
# Secret Audit — Environment Variable Cross-Reference

## Purpose

Full scan of all services for environment variable usage. Cross-references with `.env`, `.env.example`, `docker-compose.yml`, and config files. Reports defined-but-unused, used-but-undefined, and hardcoded values.

## Procedure

### Step 0: Load Service Paths from Config

Read `cognitive-os.yaml -> project.architecture.service_paths` to get the list of directories to scan.
If config is missing, auto-discover by:
1. Reading `docker-compose.yml` for service build contexts
2. Falling back to `find . -name 'go.mod' -o -name 'package.json' -o -name 'pom.xml'` to locate service roots

Store the discovered paths in `SERVICE_PATHS`.

### Step 1: Collect All Env Var References

Scan source code across all services listed in `SERVICE_PATHS`:

```bash
# TypeScript/Node services (auto-detected from SERVICE_PATHS entries containing package.json)
grep -rn 'process\.env\.\([A-Z_][A-Z0-9_]*\)' ${TS_SERVICE_PATHS}

# Go services (auto-detected from SERVICE_PATHS entries containing go.mod)
grep -rn 'os\.Getenv("[A-Z_][A-Z0-9_]*")' ${GO_SERVICE_PATHS} \
  --include='*.go'

# Java/Spring Boot services (auto-detected from SERVICE_PATHS entries containing pom.xml)
grep -rn 'System\.getenv("[A-Z_][A-Z0-9_]*")\|@Value("${[A-Z_][A-Z0-9_]*' \
  ${JAVA_SERVICE_PATHS} \
  --include='*.java' --include='*.properties' --include='*.yml'
```

The service path classification (TS vs Go vs Java) is determined by which project files exist in each path (`package.json` = TS, `go.mod` = Go, `pom.xml` = Java).

### Step 2: Collect All Env Var Definitions

```bash
# .env and .env.example files
find . -name '.env*' -not -path '*/node_modules/*' -exec grep -h '^[A-Z_][A-Z0-9_]*=' {} \;

# docker-compose env sections
grep -A 50 'environment:' docker-compose*.yml | grep '^\s*[A-Z_][A-Z0-9_]*[:=]'

# dev.env files
find . -name 'dev.env' -exec grep -h '^[A-Z_][A-Z0-9_]*=' {} \;
```

### Step 3: Cross-Reference and Classify

For each env var found, classify as:

| Status | Meaning | Action |
|--------|---------|--------|
| `defined_and_used` | OK | None |
| `used_but_undefined` | Referenced in code but no definition found | Add to `.env.example` |
| `defined_but_unused` | In `.env` but no code references it | Consider removing |
| `hardcoded` | Value appears directly in source (not via env var) | Extract to env var |

### Step 4: Check for Hardcoded Secrets

Scan for patterns that suggest hardcoded secrets:

```bash
# API keys, tokens, passwords in source
grep -rn 'apiKey\s*[:=]\s*["\x27][a-zA-Z0-9]{20,}' --include='*.ts' --include='*.go' --include='*.java'
grep -rn 'password\s*[:=]\s*["\x27][^$]' --include='*.ts' --include='*.go' --include='*.java'
grep -rn 'secret\s*[:=]\s*["\x27][a-zA-Z0-9]' --include='*.ts' --include='*.go' --include='*.java'
```

Exclude test files and mock data from hardcoded-secret warnings.

### Step 5: Generate Report

Output structured report:

```
## Secret Audit Report — {date}

### Summary
- Total env vars referenced: N
- Defined and used: N
- Used but undefined: N (NEEDS ACTION)
- Defined but unused: N (REVIEW)
- Hardcoded values found: N (SECURITY)

### Used But Undefined
| Var | Service | File | Line |
|-----|---------|------|------|

### Defined But Unused
| Var | Defined In |
|-----|-----------|

### Hardcoded Values (Security Risk)
| Pattern | File | Line |
|---------|------|------|

### Recommendations
- ...
```

## Notes

- Exclude `node_modules/`, `build/`, `dist/`, `.gradle/` from scans
- Test files and mock data are excluded from hardcoded-secret warnings
- Results saved to `.cognitive-os/metrics/secret-audit-{timestamp}.json`
