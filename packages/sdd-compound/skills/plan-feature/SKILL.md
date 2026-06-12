---
name: plan-feature
description: Create a stack-agnostic feature implementation plan before coding. Use when a user asks to plan a new product capability, extend an existing feature, turn a ticket into implementation steps, or define acceptance criteria and validation for feature work across any project stack. Do not use for root-cause bug fixes or maintenance chores; use plan-bug or plan-chore instead.
metadata:
  user-invocable: true
  version: 1.1.0
  audience: both
  effort: opus
  summary_line: Create a portable feature plan with detected stack, assumptions, acceptance criteria, validation, and rollback.
  platforms:
  - cos-projected-cli-ide
  - generic-cli
  prerequisites: []
  triggers:
  - plan-feature
  - /plan-feature
  - feature plan
  - plan feature
  - create a feature implementation plan
  routing_intents:
  - create a feature implementation plan with acceptance criteria before coding
  - plan a new product capability or user-facing workflow
  - extend an existing feature with implementation steps and validation
  - turn a ticket or feature request into a durable plan
  - score a feature design proposal before implementation
---
<!-- SCOPE: both -->
# Plan Feature

Create a structured, stack-agnostic implementation plan for feature work before
coding. Use this skill in COS itself and in adopter projects. The skill is a
canonical source procedure that can be projected into any supported CLI or IDE;
do not encode Claude-only, Codex-only, OpenCode-only, or one-editor execution
semantics in the plan.

A feature is a new or expanded product capability. If the primary intent is to
fix a defect, route to `plan-bug`. If the primary intent is cleanup, migration,
dependency, config, docs, or refactor work, route to `plan-chore`.

## Output Location

Prefer the first existing planning root in this order:

1. `.cognitive-os/plans/features/`
2. `.cognitive-os/plans/feature/`
3. `ai/plans/features/`
4. `docs/plans/features/`

If none exists, create `.cognitive-os/plans/features/`. Name the file
`YYYY-MM-DD-<slug>.md`. If the user supplies a deterministic ticket ID such as
`MVP-123`, include it in the slug when it improves traceability.

## Workflow

1. Clarify only if the feature request is ambiguous enough that a plan would be
   misleading. Otherwise proceed with reasonable assumptions and mark them.
2. Classify the request:
   - `new-feature`: net-new capability, page, endpoint, workflow, integration,
     report, automation, or user-visible behavior.
   - `feature-update`: expansion or behavior change for an existing capability.
   - `boundary`: adjacent design-system, platform, or data work that may need a
     feature plan plus another skill.
3. Detect stack, surfaces, and local conventions from repository evidence:
   - Instructions: `AGENTS.md`, `.cognitive-os/`, `.claude/`, `.codex/`,
     `.opencode/`, `.ai/`, docs, and manifests when present.
   - Language/tooling: `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`,
     `pom.xml`, `build.gradle`, `.csproj`, `Gemfile`, `composer.json`, Docker/CI.
   - Product surfaces: routes/screens, APIs, jobs, schemas, storage, shared UI,
     design-system packages, generated clients, tests, docs, and deployment files.
   - Existing plan examples under the output roots above.
4. Research relevant source and tests with targeted search. Prefer source facts
   and command evidence over broad guesses.
5. Write the plan using the format below. Keep it implementation-ready: every
   step has a verifiable `Done when`, touched files, and rollback or reversibility
   notes.
6. Self-evaluate the plan using the score table. Improve once if the score is
   below 25/50 and the improvement is based on evidence, not speculation.
7. If this repo has `evaluate-plan`, mention it as a next step; do not run it
   unless the user asked for evaluation.
8. Do not implement the feature until the user or governing workflow approves the
   plan.

## Stack Detection Hints

Use evidence-based validation commands. Examples, not defaults:

| Evidence | Candidate validation commands |
|---|---|
| `package.json` | package scripts such as test, lint, typecheck, build |
| `pyproject.toml` or `requirements.txt` | `python -m pytest`, type/lint tools if configured |
| `go.mod` | `go test ./...`, `go vet ./...` when configured |
| `Cargo.toml` | `cargo test`, `cargo clippy` when configured |
| Maven/Gradle files | project wrapper commands when present |
| UI/story files | local component, visual, accessibility, or story commands when configured |
| CI workflows | smallest workflow-equivalent local commands |

Do not invent `npm`, `pytest`, `go test`, Storybook, database, cloud, auth, or
design-system commands without repository evidence. If no command is
discoverable, state that validation is manual or requires user/project input.

## Plan Format

```markdown
---
title: <Feature Name>
type: feature
status: draft
score: 0
created: <YYYY-MM-DD>
author: agent
feature_kind: <new-feature|feature-update|boundary|mixed>
stack: <detected stack summary or unknown>
---

# Feature: <Feature Name>

## Context

<Why this feature is needed, user story/background, and what success means.>

## Classification

- **Feature Kind:** <one or more kinds>
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

## Approach

<High-level implementation approach and architecture decisions.>

## Affected Files

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

## Test Strategy

### Regression Tests

- <existing test suites or `none discovered`>

### New Tests

- <new tests if the feature changes logic; otherwise `none` with justification>

### Manual Verification

- <manual checks if relevant>

## Validation Commands

- `<command>` — <what it proves>

## Risks

- <risk> -> <mitigation>

## Rollback Plan

<How to revert safely. For irreversible migrations, data changes, public API
changes, or user-visible behavior changes, name compatibility or restore steps.>

## Documentation Scope

| Area/Feature | Path | Action |
|---|---|---|
| <area> | <path> | create/update/reference-only |

If no docs are impacted, write: `No documentation updates required — <reason>`.

## Self-Evaluation

| Category | Score | Justification |
|---|---:|---|
| Completeness | X/10 | <justification> |
| Feasibility | X/10 | <justification> |
| Risk Assessment | X/10 | <justification> |
| Architecture Alignment | X/10 | <justification> |
| Test Coverage Plan | X/10 | <justification> |

**Total:** X/50
```

## Quality Bar

- Keep project-specific rules in the plan, not in the skill. This skill is
  portable; the repository supplies domain conventions.
- Bind backend, frontend, UI, data, infra, and docs guidance to detected files,
  not assumed stacks.
- Prefer smaller reversible slices over one giant feature rollout.
- Include user-visible acceptance criteria and test evidence appropriate to the
  detected stack.
- Preserve boundaries: Graph/query/navigation tools can suggest context, but
  source inspection and tests remain the authority.

## Report

Return the plan path, score, detected stack summary, validation command
confidence, and any high-impact unverified assumptions. If the caller or pipeline
requires path-only output, return only the path as the final line.

## Contextual Trigger

- User asks for `/plan-feature`, `plan-feature`, a feature plan, product feature
  plan, new capability plan, ticket-to-plan conversion, or acceptance criteria for
  a feature before implementation.
