# SDD Harness Consumer Workflow Audit

> Comparative audit of Cognitive OS against the small `betta-tech/harness-sdd` reference harness and the accompanying SDD harness-engineering video transcript.

## Purpose

This document preserves the product and workflow analysis of what Cognitive OS is doing well and poorly in two related domains:

1. building Cognitive OS itself as a durable operating layer for coding agents; and
2. helping real consumer projects work safely and productively after they implement Cognitive OS.

The comparison source is intentionally small: [`betta-tech/harness-sdd`](https://github.com/betta-tech/harness-sdd). Its value is not breadth. Its value is that it makes the Spec Driven Development workflow legible in minutes.

## Executive Summary

`harness-sdd` is less ambitious than Cognitive OS, but it is clearer as a workflow. Cognitive OS is stronger as a governance, verification, and portability layer, but its consumer-facing path can become harder to understand because the repository contains many adjacent subsystems.

The correct lesson is not to replace Cognitive OS with a Claude-first SDD prompt harness. The correct lesson is to productize an SDD lane inside Cognitive OS that gives consumer projects the same clarity while preserving Cognitive OS strengths: cross-harness projection, evidence, gates, durable memory, and explicit kernel boundaries.

Recommended direction:

- keep the Cognitive OS wedge centered on governable, verifiable, portable coding agents;
- add a first-class consumer SDD workflow for medium, large, and critical work;
- preserve simple fast paths for trivial and small tasks;
- make requirement-to-test traceability a core SDD acceptance criterion; and
- project the workflow through harness drivers instead of making Claude Code the source of truth.

## Reference Pattern: What `harness-sdd` Demonstrates Well

The reference harness uses a simple state machine and durable files:

| Area | Reference mechanism | Why it matters |
|---|---|---|
| Task memory | `feature_list.json` | The leader can resume and choose one feature at a time. |
| Specification | `specs/<feature>/requirements.md` | Requirements are written before implementation. |
| Technical design | `specs/<feature>/design.md` | Implementation decisions are reviewed before code changes. |
| Execution plan | `specs/<feature>/tasks.md` | The implementer receives a small, curated task list. |
| Session progress | `progress/current.md` and `progress/impl_<feature>.md` | Work survives context resets and can be inspected outside chat. |
| Review record | `progress/review_<feature>.md` | The reviewer validates against specs, docs, and tasks. |
| History | `progress/history.md` | Completed work leaves an append-only trace. |
| Human gate | `spec_ready` approval | Code does not start before a human approves the spec. |
| Role separation | leader, spec author, implementer, reviewer | Agents do not self-approve their own work. |

The most important operational pattern is anti-telephone-game context passing: subagents write durable artifacts, then downstream agents read those artifacts instead of relying on chat history.

## What Cognitive OS Is Doing Well While Building the OS

### 1. The product thesis is stronger than “more agents”

Cognitive OS is framed as an operational layer for coding agents: governance, verification, portability, and measurable reliability. That is a stronger and more durable center than multi-agent choreography alone.

The reference harness demonstrates one useful workflow. Cognitive OS should govern and project workflows like that across tools.

### 2. The kernel boundary is more durable

Cognitive OS already separates stable kernel contracts from adapters, packages, optional surfaces, and future architecture. That matters because provider APIs, IDEs, hook payloads, and model behavior will keep changing.

The reference harness is intentionally Claude-oriented. That is acceptable for a demo, but it should not become the Cognitive OS architecture.

### 3. Evidence is a first-class concern

Trust reports, claim validation, quality gates, metrics, acceptance criteria, hook receipts, and portability audits all address the hard part of AI coding: proving the generated result is correct enough to trust.

The video’s central concern is not whether an AI can write code. It is whether the surrounding harness makes the AI write the correct code. Cognitive OS is already oriented toward that problem.

### 4. Externalized memory is correctly valued

The reference harness stores state in files. Cognitive OS goes further with Engram, metrics, session summaries, and repository artifacts. The direction is correct: important context should outlive the chat window.

### 5. Cross-harness projection is a real differentiator

Cognitive OS has an explicit author-once/project-through-drivers doctrine. That is the right boundary for avoiding hidden Claude-first assumptions while still supporting Claude Code well.

## What Cognitive OS Is Doing Poorly While Building the OS

### 1. Too many visible centers of gravity

The repository contains hooks, rules, skills, package management, memory, dashboards, auto-repair, squads, an agent service, provider routing, metrics, and many research surfaces. Many are useful. Together, they can obscure the user promise.

The reference harness wins first-contact clarity because a user can understand the whole loop quickly:

```text
pending -> spec_ready -> approved -> in_progress -> review_ready -> done
```

Cognitive OS should keep its deeper architecture, but product-facing docs and demos should compress the visible path.

### 2. The consumer happy path is less obvious than the architecture

Cognitive OS has strong governance primitives. It needs an equally obvious answer to: “How should my project work tomorrow?”

A consumer should not need to understand the entire OS before benefiting from it. The first workflow should be simple: pick a task, write a spec, approve it, implement it, review it, record evidence.

### 3. OS language can hide practical value

Terms like kernel, driver, control plane, package ecosystem, and primitive are useful inside the project. They are less useful as first-contact explanation for a team adopting the tool.

Product-facing material should translate those ideas into operator outcomes:

- what command to run;
- what artifact appears;
- what gate fired;
- what proof was saved;
- what the developer should inspect next.

### 4. Governance can become overkill for small work

The video explicitly allows bypassing SDD for tiny tasks. Cognitive OS should preserve that proportionality.

Recommended task scale:

| Task size | Default lane |
|---|---|
| Trivial | Direct implementation plus compile/lint/no obvious regression. |
| Small | Direct implementation plus existing tests. |
| Medium | SDD requirements/design/tasks plus implementation and review. |
| Large | SDD plus new tests, traceability, human gates, and broader verification. |
| Critical | SDD plus security/audit/rollback/idempotency review. |

### 5. The project sometimes optimizes the system before the workflow

A new primitive is valuable only if it improves the way real projects work. The next strategic question should be less “what subsystem can we add?” and more “what does the consumer workflow look like from task intake to verified completion?”

## What Cognitive OS Is Doing Well For Consumer Projects

### 1. It does not hardcode one project’s conventions into the OS

The three-layer model is correct:

1. universal Cognitive OS primitives;
2. project-specific extensions; and
3. generated configuration from project discovery.

That prevents a consumer from inheriting another project’s architecture by accident.

### 2. It treats installation and projection as product work

Consumer projects need concrete harness files, not abstract architecture. Cognitive OS is right to invest in installation, settings projection, and harness-specific surfaces.

### 3. It already has acceptance criteria and Definition of Done language

This aligns naturally with SDD. The missing step is making the SDD artifact chain first-class for consumer work, not just a general quality standard.

### 4. It preserves human judgment

The reference harness is explicit that a human approves specs and reviews tests. Cognitive OS should retain this doctrine. The product should improve developer judgment, not hide it behind autonomous theater.

## What Cognitive OS Is Doing Poorly For Consumer Projects

### 1. It does not yet expose a simple SDD lane as the default medium-work path

The reference harness gives a very concrete artifact shape. Cognitive OS should offer the same clarity for consumer projects:

```text
.cognitive-os/workflows/sdd/<feature>/requirements.md
.cognitive-os/workflows/sdd/<feature>/design.md
.cognitive-os/workflows/sdd/<feature>/tasks.md
.cognitive-os/workflows/sdd/<feature>/review.md
```

or project-facing equivalents generated from a canonical template.

### 2. Task state is not simple enough at first contact

Engram is powerful, but teams still need a visible task state. Cognitive OS should support a small task-state adapter interface:

- local JSON or Markdown for simple repos;
- GitHub Issues for GitHub-native teams;
- Linear for product teams;
- Jira for enterprise teams.

The same state machine should work regardless of backing store.

### 3. Requirement-to-test traceability should be mandatory in SDD

The most valuable reference-harness rule is that each requirement can be traced to a concrete test. Cognitive OS should make this a gate for SDD work.

A reviewer should reject SDD completion when:

- a requirement lacks a test;
- a test cannot be mapped to a requirement;
- a task is unchecked without explanation;
- implementation diverges from design;
- prohibited files or boundaries were touched.

### 4. The reviewer role should be narrower and more adversarial

A reviewer should not be a generic “quality vibe” agent. For SDD it should check traceability, evidence, boundaries, test outputs, and spec adherence. It should not edit code or approve its own implementation.

### 5. Consumer docs need fewer abstractions and more receipts

The consumer-facing workflow should show actual artifacts and outputs:

- before/after task state;
- generated requirements;
- generated design;
- generated task checklist;
- test traceability table;
- review decision;
- Trust Report.

## Recommended Cognitive OS SDD Lane

Add a first-class workflow package or primitive lane for consumer SDD:

```text
.cognitive-os/workflows/sdd/
  workflow.yaml
  templates/
    requirements.md
    design.md
    tasks.md
    review.md
  adapters/
    local-json
    github-issues
    linear
    jira
  gates/
    spec-approval
    requirement-test-traceability
    reviewer-no-self-approval
    prohibited-boundary-check
```

Canonical states:

```text
pending
spec_drafting
spec_ready
approved
in_progress
review_ready
done
rejected
```

Required artifacts per SDD feature:

| Artifact | Owner | Required content |
|---|---|---|
| `requirements.md` | Spec author | Numbered requirements, preferably EARS-style for testability. |
| `design.md` | Spec author | Files to touch, interfaces, alternatives rejected, boundaries not to touch. |
| `tasks.md` | Spec author and implementer | Discrete implementation steps, checked off as completed. |
| `traceability.md` | Implementer | Requirement-to-test map. |
| `review.md` | Reviewer | Acceptance/rejection, evidence, test commands, boundary checks. |
| `history.md` | Leader/orchestrator | Append-only completion summary. |

## Cross-Harness Projection Requirement

The SDD lane must be canonical in Cognitive OS and projected outward. Claude Code can receive subagent prompts. Codex can receive AGENTS.md/task protocol instructions and any supported hook surfaces. Other harnesses can receive their native equivalent.

The source of truth should not be `.claude/agents/*.md`.

Correct projection model:

```text
canonical SDD contract
  -> harness capability map
  -> Claude projection
  -> Codex projection
  -> Cursor/OpenCode/etc. projection
  -> runtime/proof receipts per harness
```

This preserves the reference harness’s clarity without losing Cognitive OS portability.

## Acceptance Criteria For The Future SDD Lane

1. A new user can understand the consumer SDD workflow in less than five minutes.
2. Medium, large, and critical SDD tasks generate requirements, design, tasks, traceability, and review artifacts.
3. Code implementation does not start before human approval for SDD tasks.
4. Every numbered requirement maps to at least one test or an explicit accepted non-test proof.
5. Reviewer outputs are durable artifacts and cannot be self-approval by the implementer.
6. The same canonical workflow projects to at least Claude and Codex without false parity claims.
7. The workflow has a local backing store and at least one external task-system adapter before being presented as team-ready.

## Product Positioning Consequence

Cognitive OS should not position itself as a bigger `harness-sdd`. It should position itself as the operational layer that can safely host workflows like `harness-sdd` across real projects and real harnesses.

Short version:

> `harness-sdd` shows the shape of a good workflow. Cognitive OS should make that workflow governable, verifiable, portable, and enforceable.

## Immediate Follow-Up Work

1. Draft an ADR for a canonical consumer SDD workflow lane.
2. Add a minimal local JSON/Markdown task-state adapter.
3. Add templates for requirements, design, tasks, traceability, and review.
4. Add a reviewer gate for requirement-to-test traceability.
5. Add cross-harness projection tests for Claude and Codex.
6. Add a five-minute demo showing the workflow from pending task to reviewed completion.

## Trust Report

`TRUST_REPORT: SCORE=82 STATUS=HIGH EVIDENCE=4 UNCERTAINTIES=2`

Evidence:

1. The reference repository documents a concrete SDD flow with task state, specs, progress, and review artifacts.
2. Cognitive OS top-level docs already define the wedge as governance, verification, and portability.
3. Existing Cognitive OS strategy docs identify focus drift and complexity compression as product risks.
4. Existing cross-harness rules require canonical behavior plus explicit harness projection.

Uncertainties:

1. The exact implementation shape of a future SDD lane should be validated against current installer/projection internals before ADR acceptance.
2. External task-system adapters should be prioritized based on actual consumer demand, not assumed from this analysis alone.
