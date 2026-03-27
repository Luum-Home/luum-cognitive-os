# Definition of Done (DoD) System

## Overview

The DoD system ensures task completion quality scales with task complexity. Every task is classified into one of five complexity levels, each with progressively stricter completion criteria. Agents must classify task complexity before starting work and cannot mark tasks as done until all criteria for that level pass.

## Components

### 1. Configuration (`cognitive-os.yaml`)

The `definition_of_done` section defines criteria per complexity level:
- **trivial**: `code_compiles`, `no_lint_errors`
- **small**: + `unit_tests_pass`
- **medium**: + `unit_tests_added`, `coverage_maintained`, `lint_clean`, `docs_updated`
- **large**: + `readiness_check_pass`, `unit_tests_80_percent`, `integration_tests`, `architecture_compliance`, `adversarial_review`
- **critical**: + `security_review`, `idempotency_verified`, `audit_trail_present`, `rollback_tested`

### 2. Rule (`rules/definition-of-done.md`)

Defines each complexity level with:
- Classification signals (how to identify the right level)
- Criteria with verification commands
- Mapping to Scale-Adaptive Intelligence workflow
- Phase-dependent enforcement (WARN vs BLOCK)

### 3. Hook (`hooks/dod-gate.sh`)

PostToolUse hook on the Agent matcher. Fires when an agent reports completion:
- Detects completion signals in agent output
- Identifies declared complexity level (or infers from context)
- Checks for evidence of each criterion in the output
- Outputs WARNING (reconstruction/stabilization) or BLOCK (production/maintenance) if criteria are missing

### 4. Skill (`skills/dod-check/SKILL.md`)

Manual verification skill invoked via `/dod-check`:
- Takes task description and optional complexity level
- Auto-classifies if complexity not provided
- Runs all verification commands for the level
- Reports PASS / PARTIAL / FAIL with evidence per criterion

## How It Works

### Agent Workflow

1. Agent receives a task
2. Agent classifies complexity: "Complexity: medium"
3. Agent does the work
4. Before claiming done, agent runs `/dod-check` or manually verifies criteria
5. On completion, `dod-gate.sh` hook validates criteria evidence in the output
6. If criteria missing: WARNING (reconstruction) or BLOCK (production)

### Complexity Classification Guide

| Level | Files | Scope | Examples |
|-------|-------|-------|---------|
| Trivial | 1 file, <20 lines | Typo, config | Fix comment, update port |
| Small | 1-3 files | Single service | Add DTO field, fix bug |
| Medium | Multi-file | Single service, new feature | New use case, new endpoint |
| Large | Multi-service | New integration | New provider, cross-service feature |
| Critical | Any | Security, payments, auth | Payment flow, auth change, migration |

Rule: when unsure, classify UP.

### Phase Enforcement

| Phase | Missing Criteria |
|-------|-----------------|
| reconstruction | WARNING -- noted but not blocking |
| stabilization | WARNING -- noted but not blocking |
| production | BLOCK -- must fix before marking done |
| maintenance | BLOCK -- must fix before marking done |

## Integration with Existing Systems

- **Scale-Adaptive Intelligence** (control-manifest): DoD levels map 1:1 to complexity tiers
- **Readiness Check** (readiness-check skill): Required for large and critical tasks
- **Adversarial Review** (adversarial-review rule): Required for large and critical tasks
- **Verification Before Completion** (verification skill): Complementary -- DoD adds structured criteria on top
- **Auto-Refine** (auto-refine hook): If DoD check fails, auto-refine can re-launch the agent to fix gaps

## Files

| File | Path | Purpose |
|------|------|---------|
| Config | `.cognitive-os/cognitive-os.yaml` | `definition_of_done` section |
| Rule | `.cognitive-os/rules/definition-of-done.md` | Full rule with classification guide |
| Hook | `hooks/dod-gate.sh` | PostToolUse Agent hook |
| Skill | `.cognitive-os/skills/dod-check/SKILL.md` | Manual `/dod-check` skill |
| Docs | `.cognitive-os/docs/definition-of-done.md` | This file |
