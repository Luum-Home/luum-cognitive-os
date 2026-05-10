<!-- SCOPE: both -->
---
name: code-review
description: "Use when you need this Cognitive OS skill: Engram-integrated code review with adversarial protocol. Reviews changed files for quality, security, conventions, and test coverage. Uses engram memory for past review patterns and saves findings for future reference.; do not use when a narrower skill directly matches the task."
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-29
license: MIT
context info:
  author: luum
  pattern: gga-engram-review
  inspired-by: GGA (Gentleman Guardian Angel) — MIT licensed
audience: project
effort: opus
summary_line: Engram-integrated code review with adversarial protocol.

platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\bcode[- ]?review\b'
    confidence: 0.95
  - pattern: '\b(review|revis[áa]\w*)\s+(my\s+|el\s+|la\s+|this\s+)?code\b'
    confidence: 0.88
  - pattern: '\bengram[- ]?(integrated\s+)?code[- ]?review\b'
    confidence: 0.95
---

## Purpose

AI-powered code review that leverages persistent memory (Engram) to learn from
past reviews and enforce team conventions over time. Every review follows the
adversarial review protocol: at least one finding is mandatory.

## Invocation

`/code-review` or `/review`

Optional arguments:
- `/code-review --staged` — review only staged files
- `/code-review --files path/to/file.py path/to/other.go` — review specific files
- `/code-review --context "Adding JWT auth"` — provide review context

## Prerequisites

- Git repository with changes to review
- Engram available for memory integration (graceful degradation if unavailable)

## Procedure

### Step 1: Gather Changed Files

Determine what to review:

```
IF --files argument provided:
  Use the specified files
ELIF --staged flag:
  Run: git diff --cached --name-only
ELSE:
  Run: git diff --name-only
```

Report: "Reviewing N files: [list]"

### Step 2: Search Engram for Past Context

For each service/module in the changed files, search engram:

```
For each unique service extracted from file paths:
  mem_search(query: "review/{service}", project: "{project}")
  mem_search(query: "bugfix/{service}", project: "{project}")
  mem_search(query: "implementation/{service}", project: "{project}")
```

If past reviews found:
- Note recurring patterns (issues that keep appearing)
- Note conventions established in past reviews
- Report: "Found N past reviews for context"

If no past reviews:
- Report: "No past review context found — establishing baseline"

### Step 3: Review Code

For each changed file, analyze across 5 dimensions:

#### 3a. Correctness
- Logic errors, off-by-one, null/nil handling
- Error propagation (are errors swallowed?)
- Edge cases (empty input, boundary values, concurrent access)
- Type safety and assertions

#### 3b. Security
- Hardcoded credentials, API keys, tokens
- SQL injection, command injection, XSS potential
- Unsafe deserialization, eval/exec usage
- Permission checks, authentication gaps
- Input validation and sanitization

#### 3c. Performance
- N+1 queries, unbounded loops, missing pagination
- Excessive memory allocation
- Missing caching opportunities
- Blocking operations in async contexts

#### 3d. Maintainability
- TODO/FIXME/HACK/XXX comments (should be tracked, not left)
- Dead code, commented-out blocks
- Naming conventions, code organization
- Missing documentation for public APIs
- Adherence to project conventions (from engram context)

#### 3e. Test Coverage
- Do tests exist for the changed code?
- Are edge cases covered?
- Are error paths tested?
- Is coverage likely to decrease?

### Step 4: Classify Findings

Every finding MUST be classified into exactly one tier:

| Tier | Label | Meaning | Action |
|------|-------|---------|--------|
| S1 | **BLOCKER** | Prevents shipping. Security flaw, data loss, broken functionality. | Must fix before proceeding |
| S2 | **CONCERN** | Likely to cause problems. Performance, missing edge case, weak tests. | Should fix. Requires justification to skip |
| S3 | **SUGGESTION** | Improvement opportunity. Better naming, cleaner pattern, extra test. | Fix if time allows |
| S4 | **QUESTION** | Unclear intent. Needs clarification from author or spec. | Must answer before proceeding |

### Step 5: Enforce Adversarial Protocol

Per `rules/adversarial-review.md`:

- MUST produce at least one finding
- "Looks good" and "no issues found" are PROHIBITED
- If no technical issues found, provide at least one SUGGESTION or QUESTION
- Every finding must include: location, what, why, recommendation
- Must cover at least 3 of 5 review dimensions

### Step 6: Save Review to Engram

After producing findings, save to engram for future context:

```
mem_save(
  title: "Code review: {service} ({STATUS})",
  type: "review",
  scope: "project",
  topic_key: "review/{service}/{date}",
  content: "**Status**: {PASSED|FAILED}\n**Files**: {count}\n**Findings**: {summary}\n\n{detailed findings}"
)
```

Save important discoveries/decisions/fixes to engram via mem_save with project: '{project}'.

### Step 7: Output Report

Format findings using the structured format:

```
# Code Review Report

**Status**: PASSED | FAILED
**Files reviewed**: N
**Engram context**: Used (M past reviews) | Not available
**Dimensions covered**: correctness, security, performance, maintainability, test_coverage

## Findings

### [SEVERITY] Short description

**Location**: file path (line N)
**What**: What the issue is
**Why**: Why it matters
**Recommendation**: Suggested fix or action

---

## Summary
- Blockers: N (must fix)
- Concerns: N (should fix)
- Suggestions: N (nice to have)
- Questions: N (need answers)
```

## Library

The review logic is implemented in `lib/code_reviewer.py`:

```python
from lib.code_reviewer import CodeReviewer, ReviewReport

reviewer = CodeReviewer(project_root=".")
report = reviewer.review_files(files, context="...")
print(CodeReviewer.format_report(report))
```

## Integration

| Component | Integration |
|-----------|-------------|
| Adversarial Review | Follows `rules/adversarial-review.md` — mandatory findings |
| Engram | Pre-review search + post-review save |
| Trust Score | Review thoroughness feeds trust score |
| PR Review | `/pr-review` skill builds on this skill |
| Self Review | Complements `/self-review` with deeper analysis |
| SDD Verify | Can be used within `sdd-verify` phase |

## Engram Topic Keys

| Key Pattern | Purpose |
|-------------|---------|
| `review/{service}/{date}` | Review findings for a service |
| `review/{change-name}/{date}` | Review findings for a named change |
| `bugfix/{service}/{issue}` | Past bug fixes (searched for context) |
| `implementation/{service}/*` | Implementation patterns (searched for conventions) |

## Contextual Trigger

This skill auto-loads when: code review, review code, check code quality,
review changes, review my code, pre-merge review.
