---
related-adr: ADR-083
---

# Governed Self-Improvement Roadmap

> Date: 2026-04-29  
> Origin: competitive reassessment against OpenClaw and Hermes Agent.  
> Goal: make Cognitive OS self-improvement native, visible, and reusable without allowing uncontrolled self-modification.

## Product Contract

Cognitive OS self-improvement follows this loop:

```text
detect pattern -> propose improvement -> create draft -> verify -> approve -> promote -> reuse -> measure outcome
```

The system may detect and draft improvements automatically, but promotion into
runtime behavior is governed by approval and tests.

## Workstreams

### 1. Native Governed Self-Improvement Mode

- Detect repeated failures, repeated manual corrections, and successful multi-step workflows.
- Create a canonical draft under `.cognitive-os/improvements/drafts/`.
- Attach evidence: metrics entries, session identifiers, commands, tests, and failure/recovery proof.
- Require approval before promotion unless a project explicitly opts into `auto_promote`.
- Prove the loop with unit and CLI tests.

### 2. Skill Lifecycle Autopilot

- `suggest`: list evidence-backed signals.
- `draft`: create a draft `SKILL.md` and `improvement.json`.
- `promote`: copy an approved draft into canonical `.cognitive-os/skills/cos/<skill>/`.
- The Go CLI now exposes the governed loop as `cos skill suggest`, `cos skill draft`, `cos skill inspect`, and `cos skill promote`; these commands delegate to the canonical Python implementation so CLI and runtime behavior share one contract.

### 3. Memory/Profile Bootstrap

- First three sessions produce a local project profile draft under `.cognitive-os/project-profile/`.
- Profile entries are source-linked, conflict-checkable, editable, exportable through JSON/Markdown, and wipeable.
- No secrets or developer-specific absolute paths may be persisted.
- Codex and Claude must prove the same memory lifecycle through doctor checks.

### 4. One-Command Local and Headless Proof Path

- `cos doctor` proves harness, memory, dependencies, path portability, and test summary readiness.
- `cos run-task` or an equivalent prototype runs a small bug-repair fixture headlessly.
- Output must include patch, tests, gates, memory summary, and audit trail.

### 5. Curated Workflow/Package Proofs

- Ship a small catalog: bug repair, session recovery, provider switch, path sanitization, memory bootstrap.
- Every package must include install, run, verify, uninstall, and tests/manual proof.

### 6. Competitive Benchmark Fixture

- Compare vanilla Claude, vanilla Codex, Claude + COS, Codex + COS, and prior-art tools where runnable.
- Measure outcomes, not just speed: tests, rollback, memory recovery, gates, cost, portability.

## Current Implementation Slice

Implemented first:

- `lib/governed_self_improvement.py`
- `scripts/cos_governed_self_improvement.py`
- `tests/unit/test_governed_self_improvement.py`
- `tests/behavior/test_governed_self_improvement_cli.py`
- `cmd/cos/internal/cli/skill.go`
- `cmd/cos/internal/cli/skill_test.go`
- `cmd/cos/internal/cli/profile.go`
- `cmd/cos/internal/cli/profile_test.go`
- `lib/project_profile_bootstrap.py`
- `scripts/cos_profile_bootstrap.py`
- `tests/unit/test_project_profile_bootstrap.py`
- `tests/behavior/test_profile_bootstrap_cli.py`

This slice intentionally does **not** auto-edit live rules or root skills. It
only writes drafts under `.cognitive-os/improvements/drafts/` and promotes into
canonical `.cognitive-os/skills/cos/` when approval is explicit.

## Acceptance Criteria

- Repeated error evidence produces a deterministic improvement signal.
- Repeated skill failure evidence produces a deterministic improvement signal.
- Successful multi-step workflow evidence produces a deterministic improvement signal.
- Draft creation writes `improvement.json` and `SKILL.md` under canonical state.
- Promotion without approval fails.
- Promotion with approval writes only under `.cognitive-os/skills/cos/`.
- CLI tests cover suggest, draft, inspect, and denied/approved promotion.
- First-three-session profile bootstrap writes source-linked drafts only under `.cognitive-os/project-profile/`.
- Profile bootstrap tests prove path sanitization, conflict detection, governed promotion, wipe, and Codex SessionStart execution without `CLAUDE_PROJECT_DIR`.
- The Go CLI exposes profile bootstrap as `cos profile generate|inspect|promote|wipe`.
