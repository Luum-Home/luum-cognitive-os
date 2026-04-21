<!-- SCOPE: both -->
---
name: smoke-test
version: 1.0.0
description: Run end-to-end smoke tests that validate the real Cognitive OS system works
triggers:
  - smoke test
  - system check
  - e2e test
  - take it out of the garage
audience: os-dev
---

# Smoke Test

Run end-to-end smoke tests that validate the real Cognitive OS system works -- not just unit tests, but actual hooks, config parsing, Python lib imports, safety mesh hooks, SDD pipeline logic, Docker services, and Claude CLI integration.

## Usage

```bash
# Default: Phases 1-3 (no Docker or Claude API needed)
bash scripts/cos-smoke.sh

# Quick: Phases 1-2 only (infrastructure + safety mesh)
bash scripts/cos-smoke.sh --quick

# Include Docker service tests
bash scripts/cos-smoke.sh --docker

# Full run including Claude CLI checks
bash scripts/cos-smoke.sh --all
```

## Phases

| Phase | Name | Requires | Tests |
|-------|------|----------|-------|
| 1 | Infrastructure | Nothing | self-install hook, config parse, hook syntax, lib imports, JSONL integrity, engram connectivity |
| 2 | Safety Mesh | jq | clarification gate (block + pass), blast radius, assumption tracker, dry-run mode |
| 3 | SDD Pipeline | Nothing | phase dependencies, PhaseTimer, domain router, notifications, batch runner |
| 4 | Docker Services | Docker | compose validation, start langfuse-pg, health check, stop + cleanup |
| 5 | Integration | Claude CLI | CLI exists, ClaudeExecutor command build, slash command format |

## Exit Codes

- `0` All required tests passed (phases 1-3). Optional phase failures (4-5) do not cause failure.
- `1` One or more required tests in phases 1-3 failed.

## When to Run

- After modifying hooks, rules, or lib/ modules
- After upgrading Cognitive OS
- Before a release or tag
- After `self-install.sh` changes
- As a CI gate (phases 1-3 need no external services)

## Output

Prints a color-coded summary per test with pass/fail/skip status, per-phase breakdown, and total time.
