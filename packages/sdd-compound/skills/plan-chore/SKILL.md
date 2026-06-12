---
name: plan-chore
audience: both
description: Create a stack-agnostic engineering chore plan for maintenance, cleanup, migration, dependency, config, documentation, or refactor work before implementation. Use when a user asks to plan non-feature and non-bug work, create a chore plan, break down cleanup/refactor/migration tasks, or produce acceptance criteria and validation commands for a maintenance slice across any project stack. Do not use for new product features or root-cause bug fixes; use plan-feature or plan-bug instead.
metadata:
  user-invocable: true
  version: 1.0.0
  audience: both
  effort: opus
  summary_line: Create a portable chore plan with verified assumptions, reversible steps, and stack-specific validation.
  platforms:
  - cos-projected-cli-ide
  - generic-cli
  prerequisites: []
  triggers:
  - plan-chore
  - /plan-chore
  - chore plan
  - maintenance plan
  - cleanup plan
  - refactor plan
  - migration plan
  routing_intents:
  - create a maintenance or cleanup plan before implementation
  - plan a refactor, migration, dependency update, documentation cleanup, or configuration change
  - produce verified assumptions, reversible steps, acceptance criteria, and validation commands for a chore
  - break down non-feature non-bug engineering work into a plan
---
<!-- SCOPE: both -->
# Plan Chore

Create a stack-agnostic engineering chore plan. A chore is maintenance work that
is not primarily a new product feature and not primarily a root-cause bug fix:
cleanup, refactor, migration, dependency updates, config normalization, test
hygiene, documentation repair, generated-artifact refreshes, or operational
hardening.

Use this skill in COS itself and in adopter projects. Do not assume any stack,
folder layout, package manager, test runner, design system, or harness. Detect
those from repository evidence.

## Output Location

Prefer the first existing planning root in this order:

1. `.cognitive-os/plans/chores/`
2. `.cognitive-os/plans/chore/`
3. `ai/plans/chore/`
4. `docs/plans/chores/`

If none exists, create `.cognitive-os/plans/chores/`. Name the file
`YYYY-MM-DD-<slug>.md`.

## Workflow

1. Clarify only if the requested chore is ambiguous enough that a plan would be
   misleading. Otherwise proceed with reasonable assumptions and mark them.
2. Classify the work:
   - `maintenance`: cleanup, stale generated artifacts, dead code, docs hygiene.
   - `refactor`: internal structure changes without intended behavior changes.
   - `migration`: framework/runtime/schema/config movement.
   - `dependency`: package/tool/runtime version or adoption/removal.
   - `test-quality`: test harness, fixtures, coverage, flake reduction.
   - `ops-config`: CI, deploy, hooks, environment/config projection.
   - `docs`: documentation repair or durable artifact updates.
3. Detect stack and conventions from files, not assumptions:
   - Project config: `cognitive-os.yaml`, package manifests, build files, CI files.
   - Language/tooling: `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`,
     `pom.xml`, `build.gradle`, `.csproj`, `Gemfile`, `composer.json`, Docker/CI.
   - Existing plan examples under the output roots above.
   - Local rules under `.cognitive-os/rules/`, `.claude/rules/`, `AGENTS.md`, or
     equivalent repo instructions.
4. Research relevant source and tests with targeted search. Prefer source facts
   and command evidence over broad guesses.
5. Write the plan using the format below. Keep it implementation-ready: each step
   has a verifiable `Done when`, touched files, and reversibility.
6. If this repo has `evaluate-plan`, mention it as a next step; do not run it
   unless the user asked for evaluation.

## Stack Detection Hints

Use evidence-based validation commands. Examples, not defaults:

| Evidence | Candidate validation commands |
|---|---|
| `package.json` | package scripts such as test, lint, typecheck, build |
| `pyproject.toml` or `requirements.txt` | `python -m pytest`, type/lint tools if configured |
| `go.mod` | `go test ./...`, `go vet ./...` when configured |
| `Cargo.toml` | `cargo test`, `cargo clippy` when configured |
| Maven/Gradle files | project wrapper commands when present |
| CI workflows | smallest workflow-equivalent local commands |
| docs-only change | markdown/link/provenance checks configured by repo |

Do not invent `npm`, `pytest`, `go test`, or build commands without repository
evidence. If no command is discoverable, state that validation is manual or
requires user/project input.

## Plan Format

```markdown
---
title: <Chore Name>
type: chore
status: draft
created: <YYYY-MM-DD>
author: agent
chore_kind: <maintenance|refactor|migration|dependency|test-quality|ops-config|docs|mixed>
stack: <detected stack summary or unknown>
---

# Chore: <Chore Name>

## Chore Description

<What needs to change and why this is maintenance/refactor/migration work rather
than a feature or bug fix.>

## Classification

- **Chore Kind:** <one or more kinds>
- **Detected Stack:** <languages/frameworks/package managers inferred from files>
- **Planning Root:** <selected output root>
- **Rules/Conventions Applied:**
  - `<path>` — <why it matters>

## Assumptions

Every plan must list at least three assumptions. Mark each as `verified` with a
file/line or command result, or `unverified`. A high-impact unverified assumption
is a blocker for execution approval.

| # | Assumption | Verification | If wrong, impact |
|---|---|---|---|
| 1 | <assumption> | <file:line, command result, or unverified> | low/medium/high |
| 2 | <assumption> | <file:line, command result, or unverified> | low/medium/high |
| 3 | <assumption> | <file:line, command result, or unverified> | low/medium/high |

## Out of Scope

- <explicit non-goal or `N/A — minimal scope` with justification>

## Relevant Files

### Existing Files to Reference

- `<path>` — <why relevant>

### New Files

- `<path>` — <purpose, or `none`>

## Step by Step Tasks

### Step 1: <Step title>

**Done when:** <verifiable result>
**Files touched:** <paths or `none — analysis step`>
**Reversible:** <yes|no> — <why>

- <action>
- <action>

### Step 2: <Step title>

**Done when:** <verifiable result>
**Files touched:** <paths>
**Reversible:** <yes|no> — <why>

- <action>

### Final Step: Validation

**Done when:** all validation commands below pass or documented manual checks are complete.
**Files touched:** none
**Reversible:** N/A

- Run validation commands.
- Inspect `git diff` for unintended behavior/API/config changes.

## Acceptance Criteria

- <measurable criterion>
- <measurable criterion>
- No unrelated files are changed, or unrelated generated changes are explicitly justified.

## Testing Strategy

### Regression Tests

- <existing test suites or `none discovered`>

### New Tests

- <new tests if the chore changes logic; otherwise `none` with justification>

### Manual Verification

- <manual checks if relevant>

## Validation Commands

- `<command>` — <what it proves>

## Rollback Plan

<How to revert safely. For irreversible migrations/deletions, name backup or
restore strategy and approval needed.>

## Documentation Scope

| Area/Feature | Path | Action |
|---|---|---|
| <area> | <path> | create/update/reference-only |

If no docs are impacted, write: `No documentation updates required — <reason>`.

## Notes

<Optional implementation notes, sequencing risks, or links to evidence.>
```

## Quality Bar

- Prefer smaller reversible slices over one giant chore.
- For migrations/deletions/public API changes, include a rollback or compatibility
  step and mark irreversible work clearly.
- Treat generated artifacts as first-class: say which command regenerates them and
  why they belong in the same plan.
- Keep project-specific rules in the plan, not in the skill. This skill is
  portable; the repository supplies domain conventions.

## Report

Return the plan path and a short note with detected stack and validation command
confidence. If the caller or pipeline requires path-only output, return only the
path as the final line.

## Contextual Trigger

- User asks for `/plan-chore`, `plan-chore`, a chore plan, maintenance plan, cleanup plan, refactor plan, migration plan, dependency plan, config plan, documentation cleanup plan, or test-quality plan.
- User wants to plan non-feature and non-bug engineering work before implementation across COS or an adopter project.
