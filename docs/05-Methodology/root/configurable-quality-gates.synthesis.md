---
type: methodology-synthesis
source: docs/05-Methodology/root/configurable-quality-gates.md
provenance: "Explains how a single cognitive-os.yaml coverage threshold drives three independent enforcement layers (hook, agent, CI) plus SaaS industry presets."
---

## What it is

A description of the quality-gate system where `cognitive-os.yaml` is the single source of truth for test-coverage thresholds, enforcement rules, and industry presets, read consistently by three enforcement layers of increasing severity.

## Key mechanics

- **Config shape**: `quality.coverage.minimum` (global %), `block_pr` (bool), `per_package` (bool), `exclude` (glob patterns like `*/mocks/*`, `*/test/*`, `cmd/*`).
- **Three enforcement layers**, same threshold, escalating severity:
  1. Local hook `coverage-gate.sh` (`.claude/hooks/`) — PostToolUse on `go test`/`git commit`/`git push`; warning only, never blocks.
  2. Agent `test-coverage-enforcer.md` (`.claude/agents/`) — activates on Go file changes; runs `go test -coverprofile`, identifies untested functions, produces a report.
  3. GitHub Action `claude-pr-review.yml` — runs per PR touching Go services; posts a coverage comment; **blocks the PR** when `block_pr: true` and coverage is below threshold.
- **Industry presets** for the SaaS product: fintech (80%, integration tests required, idempotency + audit trail), healthcare (90%, integration required, HIPAA tests), ecommerce (70%, integration required), startup (50%, integration optional). Selected on project creation via web dashboard, which generates `cognitive-os.yaml`; customers can override individual values afterward.
- **Broader quality-gate pipeline** (beyond coverage): ordered gates — `compilation` (`go build ./...`), `lint` (`golangci-lint run ./...`), `unit_tests` (`go test ./... -short`), `coverage` (threshold-gated), `integration_tests` (optional, non-blocking). Required gates block on failure; optional gates report only.
- Manual invocation via `/coverage-report [service]` skill.

## Relations & where used

- Complements `rules-consolidation-plan.md`'s discussion of `cognitive-os.yaml` as a config source and `automation.md`'s description of `claude-pr-review.yml` (same CI workflow file, different lens: automation.md covers architecture/security/mock review, this doc covers the coverage-blocking behavior specifically).
- References `.claude/hooks/coverage-gate.sh` and `.claude/agents/test-coverage-enforcer.md` as concrete enforcement artifacts.

## Status / caveats

- This document frames coverage presets as a **multi-tenant SaaS dashboard feature** ("Customer creates a project on the web dashboard... Selects industry preset") — a different operating context from the CLI/self-hosted repo framing used in most of the other Methodology docs in this batch (walkthrough.md, hooks.md, rules.md), which describe a single local install rather than a customer-facing dashboard. Readers should not assume the dashboard/preset flow is live in the self-hosted OS without separate confirmation.
- "Current Baseline" section defers to an external, unlinked "project's coverage baseline documentation" rather than stating a number — no baseline is asserted here.
