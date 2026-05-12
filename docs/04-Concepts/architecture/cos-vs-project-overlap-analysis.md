# COS vs Project Overlap Analysis: reference-project Case Study

reference-project independently built a sophisticated AI pipeline without consuming COS. This analysis reveals what COS should provide as a framework vs what belongs in projects.

## Overlap Matrix

| reference-project Component | COS Equivalent | Overlap | Owner |
|---|---|---|---|
| **Commands** | | | |
| `/plan-feature` | `sdd-explore` + `sdd-propose` | HIGH | BOTH — COS provides template engine, project fills domain templates |
| `/plan-bug-resolution` | `plan-bug` skill | HIGH | BOTH |
| `/plan-chore` | No equivalent | MEDIUM | BOTH — COS should provide |
| `/plan-design-system-component` | No equivalent | LOW | PROJECT — Atomic Design, Storybook |
| `/plan-ui-from-design` | No equivalent | NONE | PROJECT — Figma-to-code |
| `/implement-approved-plan` | `sdd-apply` | HIGH | COS — executing a plan is generic |
| `/code-review-path` | `code-review` skill | HIGH | BOTH |
| `/metaprompt-workflow` | `skill-creator` | HIGH | COS — creating commands is generic |
| `/fix-build` | `auto-refine` hook | HIGH | COS — fix-then-retry is generic |
| `/fix-tests` | `auto-refine` hook | HIGH | COS |
| `/apply-evaluation` | SDD apply-verify cycle | HIGH | COS |
| **Skills** | | | |
| `evaluate-plan` (50-point rubric) | `evaluate-plan` COS skill | HIGH | COS |
| `feature-architecture` | No equivalent | LOW | PROJECT — Next.js patterns |
| `code-review` | `code-review` COS skill | HIGH | BOTH |
| `query-setup`, `routing-paths`, `form-validation`, etc. | No equivalents | NONE | PROJECT — domain knowledge |
| **Agents** | | | |
| `nextjs-architect` | Orchestrator + SDD | HIGH | BOTH — role generic, expertise domain |
| `ui-ux-reviewer` | `code-review` | MEDIUM | BOTH |
| `qa-playwright-lead` | No equivalent | LOW | PROJECT |
| **Hooks** | | | |
| File protection (PreToolUse) | `agent-security` | HIGH | COS |
| Auto-format (prettier) | No equivalent | MEDIUM | COS should provide as template |
| Auto-lint (eslint) | No equivalent | MEDIUM | COS should provide as template |
| Pattern guard | `scope-creep-detector` | LOW | PROJECT |
| SessionStart git status | `session-init.sh` | HIGH | COS |
| **Pipeline** | | | |
| Python CLI wrapping | SDD pipeline | HIGH | COS — biggest gap |
| State management (JSON) | Engram topic keys | MEDIUM | COS |
| Resume/start-from | SDD resume | HIGH | COS |
| 4 pipeline variants | Single SDD pipeline | MEDIUM | COS — should support composition |
| ClickUp/Telegram integration | No equivalent | NONE | PROJECT |

## The 7 Capabilities COS Should Extract

### 1. Pipeline Runner (External Orchestration) — CRITICAL GAP

reference-project wraps Claude CLI in Python, manages state in JSON, provides resume/retry, and orchestrates 11-phase pipelines OUTSIDE Claude. This is more robust than COS's in-session SDD: each phase is a fresh Claude invocation with no context degradation.

**Action**: Extract `packages/pipeline-runner/` from the TAC/reference-project pattern.

### 2. Auto-Format and Auto-Lint Hooks

COS has 93 hooks but none for auto-formatting. reference-project runs `prettier --write` and `eslint --fix` on every Edit/Write. This is generic.

**Action**: Add hook templates for common formatters and linters.

### 3. Plan Template Engine

reference-project has 8 `/plan-*` commands following a consistent pattern. COS should provide the engine; projects define templates.

**Action**: Create generic `plan-template` skill.

### 4. Scored Plan Evaluation with Apply Cycle

50-point rubric → score → apply findings → update plan. COS's SDD skips this.

**Action**: Add scored evaluation as explicit SDD phase.

### 5. Pipeline Variant Composition

4 pipelines sharing common phases (build, test, commit, PR) but diverging in planning and review.

**Action**: Allow pipeline composition in COS.

### 6. Agent Role Templates

Generic roles (architect, reviewer, QA lead) that projects customize with domain expertise.

**Action**: Provide agent templates in COS.

### 7. Code Review Path Skill

Read-only code audit scoring across configurable categories, generating improvement plan.

**Action**: Add as COS skill.

## The Pipeline Gap (Critical Finding)

### reference-project: External Orchestration

```
Python → subprocess("claude --print --stream-json") → fresh Claude per phase → state.json → next phase
```

**Strengths**: No context degradation, true persistence, observable, integrable, resumable.

### COS: Internal Orchestration

```
Orchestrator (Claude) → Agent tool → sub-agent → result in context → next phase
```

**Strengths**: Spec-driven correctness, verification against specs, quality governance, cross-session memory, cost awareness.

### Resolution: Support Both

- **Internal** for interactive, in-session work (current SDD)
- **External** for batch, CI/CD-like workflows (pipeline-runner)

The pipeline-runner should invoke SDD phases as individual Claude commands.

## What COS Has That reference-project Wastes

| COS Feature | reference-project Impact |
|---|---|
| Model routing | Runs Opus on `/fix-build` — direct waste |
| Adaptive bypass | Runs 11 phases for a typo fix |
| Cost governance | No budget tracking |
| Error learning | No cross-session pattern detection |
| Engram memory | No cross-session agent learning |
