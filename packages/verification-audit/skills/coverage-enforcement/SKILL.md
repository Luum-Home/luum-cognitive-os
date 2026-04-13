---
name: coverage-enforcement
version: 1.0.0
command: /coverage-report
description: Run Go test coverage for all services, enforce thresholds from cognitive-os.yaml, report per-package results. Service root read from project.architecture.services_root.go config.
last-updated: 2026-04-13
auto-generated: false
tech: go
audience: project
---

# Coverage Enforcement Skill

## Purpose

Run Go test coverage across all Go services (per `cognitive-os.yaml -> project.architecture.services_root.go`), enforce minimum thresholds, and generate a per-package coverage report with actionable guidance on what needs more tests.

## Invocation

```
/coverage-report [service]
```

- No arguments: run coverage on ALL Go services discovered from config
- With service name: run coverage only for that service (e.g., `/coverage-report wallet`)

## Steps

### 1. Read Configuration

Read `cognitive-os.yaml` from the project root to get:
- `project.architecture.services_root.go` — root path for Go services (default: `apps`)
- `quality.coverage.minimum` — global minimum coverage % (default: 80)
- `quality.coverage.per_package` — whether to enforce per-package (default: true)
- `quality.coverage.exclude` — glob patterns to exclude from enforcement

If `cognitive-os.yaml` is missing, use defaults: `apps` services root, 80% minimum, per-package enforcement, exclude `*/mocks/*`, `*/test/*`, `cmd/*`.

Store the services root in a variable: `SERVICES_ROOT` (read from config, fallback to `apps`).

### 2. Discover Services

List all directories in `${SERVICES_ROOT}/` that contain a `go.mod` file. Each is a Go service module.

If `${SERVICES_ROOT}` does not exist, check if a `go.mod` exists at the project root (mono-module project) and adjust discovery accordingly.

### 3. Run Coverage Per Service

For each service (or the specified one):

```bash
cd $(dirname ${SERVICES_ROOT})
go test -coverprofile=/tmp/{service}-coverage.out ./${SERVICES_ROOT##*/}/{service}/... 2>&1
```

If tests fail, capture the output but continue to next service.

### 4. Parse Coverage Output

For each successful coverage profile:

```bash
go tool cover -func=/tmp/{service}-coverage.out
```

Parse the output to extract:
- Per-function coverage percentages
- Per-package coverage (aggregate functions by package)
- Overall service coverage (the `total:` line)

### 5. Apply Exclusions

Skip packages matching any pattern in `quality.coverage.exclude`:
- `*/mocks/*` — mock implementations
- `*/test/*` — test helpers
- `cmd/*` — main entry points (usually trivial)

### 6. Identify Violations

For each non-excluded package, check if coverage is below the threshold.

A package **violates** the threshold if:
- `per_package: true` and the package coverage < minimum
- `per_package: false` and only the overall service coverage < minimum

### 7. Generate Report

Output a structured report with:

#### Summary Table

```
| Service | Overall % | Status | Packages Below |
|---------|-----------|--------|----------------|
| wallet  | 82.3%     | PASS   | 0              |
| cards   | 45.1%     | FAIL   | 3              |
```

#### Per-Package Detail (for failing services)

```
Service: cards
  FAIL  internal/domain/card.go          — 32.1% (need 80%)
  FAIL  internal/usecase/issue_card.go   — 41.5% (need 80%)
  PASS  internal/adapter/http/handler.go — 88.2%
```

#### Uncovered Functions

List the top 10 functions with 0% coverage per failing service, formatted as:
```
Suggested tests for cards:
  - TestCreateCard (internal/domain/card.go:CreateCard)
  - TestValidateCardNumber (internal/domain/card.go:ValidateCardNumber)
  - TestIssueCardUseCase (internal/usecase/issue_card.go:Execute)
```

#### Configuration Reference

Show current config:
```
Threshold: 80% (from cognitive-os.yaml)
Per-package: true
Excluded: */mocks/*, */test/*, cmd/*
```

### 8. Exit Code

- Exit 0 if all services pass
- Exit 1 if any service fails (for CI integration)

## Error Handling

- If a service has no test files, report it as "NO TESTS" (not PASS or FAIL)
- If `go test` fails (compilation error), report the error and continue
- If `cognitive-os.yaml` is missing or malformed, use defaults and warn

## Integration

- **Hook**: `coverage-gate.sh` runs a lightweight version on `go test` / `git commit` / `git push`
- **GitHub Action**: `claude-pr-review.yml` runs the full version and blocks PRs
- **Agent**: `test-coverage-enforcer.md` auto-triggers on Go file changes
