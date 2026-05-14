---
name: confidence-check
description: 'Pre-implementation confidence assessment. Before writing code, check
  5 dimensions to verify readiness: no duplicates, architecture compliance, documentation
  verified, prior art reviewed, and root cause identified.

  '
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-27
license: MIT
metadata:
  author: luum
  pattern: superclaude-confidence
audience: project
summary_line: Pre-implementation confidence assessment.
platforms:
- claude-code
prerequisites: []
triggers:
- confidence-check
- /confidence-check
- Pre-implementation confidence assessment
---
<!-- SCOPE: both -->
## Purpose

Prevent wasted implementation effort by verifying the agent is ready to write
code. This runs BEFORE `sdd-apply` (pre-implementation) while `trust-score`
runs AFTER (post-implementation). Catching gaps before coding is cheaper than
discovering them after.

## Invocation

`/confidence-check [--target=<file-or-feature>] [--skip-engram]`

## What to Do

### Step 1: Identify the Implementation Target

Read the task description, spec, or user request. Extract:
- What is being implemented (feature, fix, refactor)
- Which files/services will be affected
- What technology/framework is involved

### Step 2: Assess 5 Confidence Dimensions

Score each dimension 0-100, then compute the weighted total.

#### Dimension 1: No Duplicates (25%)

Search the codebase for existing similar implementations.

```
Actions:
├── Grep for function/type/class names similar to what you plan to create
├── Search for files with similar naming patterns
├── Check if the feature already exists under a different name
└── Look for deprecated or commented-out versions of similar code
```

**Score**:
- 100: No duplicates found, confirmed unique
- 75: Similar code exists but serves a different purpose (documented)
- 50: Partial overlap found, needs investigation
- 25: Near-duplicate exists, unclear if intentional
- 0: Exact duplicate found — should reuse, not recreate

#### Dimension 2: Architecture Compliance (25%)

Verify the planned approach follows project patterns.

```
Actions:
├── Check project rules in .claude/rules/ for architecture constraints
├── Verify correct layer placement (domain, application, infrastructure)
├── Confirm framework usage matches project standard
├── Check naming conventions (files, types, functions)
└── Verify import patterns match existing code
```

**Score**:
- 100: Approach fully aligns with documented architecture
- 75: Mostly aligned, minor deviations justified
- 50: Some patterns unclear, assumptions needed
- 25: Significant deviation from established patterns
- 0: Approach contradicts documented architecture

#### Dimension 3: Documentation Verified (20%)

Check official docs for the technology being used.

```
Actions:
├── Verify API signatures/types from official documentation
├── Check for breaking changes in the version being used
├── Confirm the approach is recommended (not deprecated)
└── Review any migration guides if upgrading
```

**Score**:
- 100: All APIs verified against current docs
- 75: Core APIs verified, edge cases not checked
- 50: Relying on memory/training data, not verified
- 25: Documentation is ambiguous or incomplete
- 0: Using undocumented or deprecated APIs

#### Dimension 4: Prior Art Reviewed (15%)

Search Engram for similar past work.

```
Actions:
├── mem_search for the feature/technology/pattern
├── Check for past decisions that affect this implementation
├── Look for known gotchas or edge cases from previous sessions
└── Review any related bug fixes or workarounds
```

If `--skip-engram` is set, score this dimension at 50 (neutral) and note it was skipped.

**Score**:
- 100: Prior art found and incorporated into plan
- 75: Some related work found, learnings applied
- 50: No prior art found (first time) or Engram skipped
- 25: Prior art exists but contradicts current approach
- 0: Previous attempt at this exact task failed

#### Dimension 5: Root Cause Identified (15%)

For bug fixes, confirm the actual cause before fixing. For features, confirm
the requirement is understood.

```
Actions:
├── For bugs: reproduce the issue, identify the exact failing line/condition
├── For bugs: confirm the fix addresses root cause, not symptoms
├── For features: verify the requirement is unambiguous
└── For refactors: confirm the motivation is clear and measurable
```

**Score**:
- 100: Root cause confirmed with evidence (stack trace, test, reproduction)
- 75: Root cause likely, good evidence but not 100% confirmed
- 50: Hypothesis formed, needs verification during implementation
- 25: Multiple possible causes, unclear which is correct
- 0: No understanding of why the issue occurs

### Step 3: Calculate Confidence Score

```
confidence = (
    no_duplicates * 0.25 +
    architecture_compliance * 0.25 +
    documentation_verified * 0.20 +
    prior_art_reviewed * 0.15 +
    root_cause_identified * 0.15
)
```

### Step 4: Apply Threshold Decision

| Score | Verdict | Action |
|-------|---------|--------|
| >= 90 | PROCEED | Implementation is well-prepared. Start coding. |
| 70-89 | INVESTIGATE | Gaps exist. Document assumptions, investigate weak dimensions, then proceed. |
| < 70 | HALT | Too many unknowns. Present findings to user and ask for guidance. |

### Step 5: Generate Report

```markdown
## Confidence Check Report

### Target
{what is being implemented}

### Score: {total}/100 — {PROCEED|INVESTIGATE|HALT}

| Dimension | Weight | Score | Notes |
|-----------|--------|-------|-------|
| No Duplicates | 25% | {score} | {brief finding} |
| Architecture Compliance | 25% | {score} | {brief finding} |
| Documentation Verified | 20% | {score} | {brief finding} |
| Prior Art Reviewed | 15% | {score} | {brief finding} |
| Root Cause Identified | 15% | {score} | {brief finding} |

### Gaps to Investigate
- {list any dimensions scoring < 75}

### Assumptions Made
- {list any assumptions, especially for dimensions scoring 50-74}

### Recommendation
{PROCEED / INVESTIGATE specific items / HALT and ask user about specific questions}
```

### Step 6: Persist

Save the confidence check result to Engram:

```
mem_save(
  title: "Confidence check: {target} — {score}/100 {verdict}",
  topic_key: "implementation/{target-slug}/confidence-check",
  type: "discovery",
  project: "{project}",
  content: "{full report}"
)
```

## Integration with SDD Pipeline

```
sdd-tasks produces task breakdown
    |
    v
/confidence-check (pre-implementation gate)
    |
    ├── >= 90: proceed to sdd-apply
    ├── 70-89: investigate gaps, then sdd-apply
    └── < 70: HALT — present to user
    |
    v
sdd-apply (implementation)
    |
    v
trust-score (post-implementation assessment)
```

## Rules

- NEVER skip the duplicate check — creating duplicates is a top agent failure mode
- If architecture rules are not documented, score dimension 2 at 50 and note the gap
- For new projects with no Engram history, score dimension 4 at 50 (neutral)
- The HALT verdict is not a failure — it is a success at catching problems early
- Return a structured envelope with: `status`, `executive_summary`, `artifacts`, `next_recommended`, and `risks`
