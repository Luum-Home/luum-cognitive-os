# Configurable Quality Gates

> How `cognitive-os.yaml` drives test coverage enforcement across the platform.

## Overview

The quality gate system uses `cognitive-os.yaml` as a single source of truth for all coverage thresholds, enforcement rules, and industry presets. This configuration is read by three enforcement layers: a local hook (developer feedback), an agent (auto-detection), and a GitHub Action (CI gate).

## Configuration Source: cognitive-os.yaml

The file lives at the project root:

```yaml
quality:
  coverage:
    minimum: 80           # Global minimum coverage %
    block_pr: true        # Block PRs below threshold
    per_package: true     # Enforce per-package, not just global
    exclude:              # Patterns to skip
      - "*/mocks/*"
      - "*/test/*"
      - "cmd/*"
```

### Setting the Threshold

Edit `quality.coverage.minimum` in `cognitive-os.yaml`. All three enforcement layers read this value:

| Layer | When | Severity |
|-------|------|----------|
| Hook (`coverage-gate.sh`) | On `go test`, `git commit`, `git push` | Warning |
| Agent (`test-coverage-enforcer.md`) | On Go file change | Report |
| GitHub Action (`claude-pr-review.yml`) | On PR open/sync | Blocking |

### Per-Package Enforcement

When `per_package: true`, every non-excluded package must individually meet the threshold. When `false`, only the aggregate service-level coverage is checked.

### Exclusions

Patterns in `exclude` are matched against package paths. Common exclusions:
- `*/mocks/*` — generated mock implementations
- `*/test/*` — test utilities and helpers
- `cmd/*` — main entry points with minimal logic

## Industry Presets

For the Cognitive OS SaaS product, presets provide sensible defaults by industry:

| Preset | Coverage | Integration Tests | Special Requirements |
|--------|----------|-------------------|---------------------|
| fintech | 80% | Required | Idempotency tests, audit trail |
| healthcare | 90% | Required | HIPAA compliance tests |
| ecommerce | 70% | Required | - |
| startup | 50% | Optional | - |

SaaS customers select a preset when creating their project. The preset populates `cognitive-os.yaml` with the appropriate values. Customers can then customize individual settings.

### How Presets Work for SaaS

1. Customer creates a project on the web dashboard
2. Selects industry preset (e.g., "fintech")
3. Dashboard generates `cognitive-os.yaml` with preset values
4. Customer can override any value via dashboard or direct file edit
5. All enforcement layers read from the same config

## Enforcement Layers

### Layer 1: Local Hook (coverage-gate.sh)

PostToolUse hook on the Bash tool. Triggers on `go test`, `git commit`, `git push`.

**What it does:**
- Reads threshold from `cognitive-os.yaml`
- On `go test`: reminds to use `-coverprofile`
- On `git commit/push`: warns if Go files changed without coverage check
- Never blocks -- warning only

**Location:** `.claude/hooks/coverage-gate.sh`

### Layer 2: Agent (test-coverage-enforcer.md)

Activates when Go source files change in the services root (per `cognitive-os.yaml -> project.architecture.services_root.go`).

**What it does:**
- Runs `go test -coverprofile` on the affected service
- Parses per-package coverage
- Identifies functions without tests
- Suggests test names for uncovered functions
- Reports overall vs threshold

**Location:** `.claude/agents/test-coverage-enforcer.md`

### Layer 3: GitHub Action (claude-pr-review.yml)

Runs on every PR that touches the Go services root.

**What it does:**
- Detects which Go services changed
- Runs coverage for each changed service
- Posts a coverage report as a PR comment
- Blocks the PR if any service is below threshold (when `block_pr: true`)

**Location:** `.github/workflows/claude-pr-review.yml`

## Quality Gates Pipeline

Beyond coverage, `cognitive-os.yaml` defines a full quality gate pipeline:

```yaml
quality:
  gates:
    - name: compilation
      required: true
      command: "go build ./..."
    - name: lint
      required: true
      command: "golangci-lint run ./..."
    - name: unit_tests
      required: true
      command: "go test ./... -short"
    - name: coverage
      required: true
      command: "go test ./... -coverprofile=coverage.out"
      threshold: 80
    - name: integration_tests
      required: false
      command: "go test ./... -tags=integration"
```

Gates run in order. Required gates block the pipeline on failure. Optional gates report but do not block.

## Invoking Coverage Manually

Use the `/coverage-report` skill:

```
/coverage-report          # All services
/coverage-report wallet   # Single service
```

## Current Baseline

See the project's coverage baseline documentation for the current state of coverage across all Go services.
