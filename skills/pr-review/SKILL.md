---
name: pr-review
description: >
  Pull Request review skill. Gets PR diff against base branch, runs code review
  with engram context, checks tests/coverage/lint, and produces structured
  PR review output with file-level comments and PASSED/FAILED status.
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-29
license: MIT
context info:
  author: luum
  pattern: gga-pr-review
  inspired-by: GGA (Gentleman Guardian Angel) — MIT licensed
audience: project
effort: opus
---

## Purpose

Structured Pull Request review workflow that combines diff-based code review
with test verification, coverage checks, and engram memory. Produces a
PR-ready review with file-level comments and a clear PASSED/FAILED verdict.

## Invocation

`/pr-review`

Optional arguments:
- `/pr-review --base main` — specify base branch (auto-detects if omitted)
- `/pr-review --pr 123` — review a specific PR number via gh CLI
- `/pr-review --no-tests` — skip test execution (review only)

## Prerequisites

- Git repository with commits to review
- Base branch exists (main/master/develop — auto-detected)
- Engram available for memory integration (graceful degradation if unavailable)
- Optional: `gh` CLI for GitHub PR integration

## Procedure

### Step 1: Detect Base Branch

Auto-detect the base branch:

```
For each candidate in [main, master, develop]:
  Run: git rev-parse --verify {candidate}
  If exits 0: use this as base branch

If --base argument provided: override auto-detection
If --pr argument provided: use gh pr view {N} --json baseRefName
```

Report: "Base branch: {branch}"

### Step 2: Get PR Diff

```
IF --pr argument:
  Run: gh pr diff {N}
ELSE:
  Run: git diff {base}...HEAD
```

Extract:
- Changed files list: `git diff {base}...HEAD --name-only`
- Commit count: `git rev-list {base}..HEAD --count`
- Commit messages: `git log {base}..HEAD --oneline`

Report: "PR contains N commits changing M files"

### Step 3: Search Engram for Context

Same as `/code-review` Step 2:

```
For each unique service in changed files:
  mem_search(query: "review/{service}", project: "{project}")
  mem_search(query: "bugfix/{service}", project: "{project}")
```

Additionally search for the PR's topic if identifiable:
```
mem_search(query: "{branch-name or PR title keywords}", project: "{project}")
```

### Step 4: Review the Diff

Run the code review on the diff (not full files — only changed lines):

```python
from lib.code_reviewer import CodeReviewer

reviewer = CodeReviewer(project_root=".")
diff = reviewer.get_diff(base_branch="{base}")
report = reviewer.review_diff(diff, context="{PR description}")
```

Apply the same 5-dimension review as `/code-review`:
- Correctness, Security, Performance, Maintainability, Test Coverage

Follow the adversarial review protocol: at least one finding mandatory.

### Step 5: Verify Tests and Quality

Unless `--no-tests` is specified:

#### 5a. Run Tests
```
Detect test framework from project:
  - Python: pytest, unittest
  - Go: go test
  - Node: jest, vitest, mocha
  - Java: gradle test, mvn test

Run: {test_command}
Report: "Tests: N passed, M failed"
```

#### 5b. Check Lint
```
Run: {lint_command}
Report: "Lint: clean | N issues"
```

#### 5c. Check Build
```
Run: {build_command}
Report: "Build: success | failed"
```

#### 5d. Coverage Delta (if available)
```
Compare coverage before and after changes.
Report: "Coverage: X% (delta: +/-Y%)"
```

### Step 6: Produce File-Level Comments

Group findings by file for PR-style output:

```
For each file with findings:
  ## {file_path}

  - Line {N}: [{SEVERITY}] {what}
    Recommendation: {recommendation}
```

### Step 7: Save Review to Engram

```
mem_save(
  title: "PR review: {branch or PR title} ({STATUS})",
  type: "review",
  scope: "project",
  topic_key: "review/{change-name}/{date}",
  content: "**Status**: {STATUS}\n**Base**: {base}\n**Files**: {count}\n**Commits**: {count}\n\n{findings summary}"
)
```

Save important discoveries/decisions/fixes to engram via mem_save with project: '{project}'.

### Step 8: Output PR Review Summary

```
# PR Review Summary

**Status**: PASSED | FAILED
**Base branch**: {base}
**Commits**: N
**Files changed**: M
**Engram context**: Used (K past reviews) | Not available

## Verification
- Tests: PASS (N passed) | FAIL (M failed)
- Lint: CLEAN | N issues
- Build: SUCCESS | FAILED
- Coverage: X% (delta: +/-Y%)

## File Comments

### {file1.py}
- Line 42: [BLOCKER] Hardcoded API key
  Fix: Move to environment variable

### {file2.go}
- Line 15: [SUGGESTION] Consider adding error wrapping
  Fix: Use fmt.Errorf("context: %w", err)

## Findings Summary
| Severity | Count | Action |
|----------|-------|--------|
| BLOCKER | N | Must fix |
| CONCERN | N | Should fix |
| SUGGESTION | N | Nice to have |
| QUESTION | N | Need answers |

## Verdict

STATUS: PASSED
- All tests pass
- No blockers found
- N suggestions for improvement

or

STATUS: FAILED
- N blockers must be resolved
- Tests failing: list specific failures
- Action required before merge
```

## Library

Uses `lib/code_reviewer.py` for core review logic:

```python
from lib.code_reviewer import CodeReviewer

reviewer = CodeReviewer(project_root=".")
base = reviewer.detect_base_branch()
diff = reviewer.get_diff(base_branch=base)
report = reviewer.review_diff(diff)
engram_data = reviewer.save_review(report, change_name="feature/auth")
```

## Integration

| Component | Integration |
|-----------|-------------|
| Code Review | Builds on `/code-review` skill for core review logic |
| Adversarial Review | Follows `rules/adversarial-review.md` |
| Engram | Pre-review search + post-review save |
| GitHub | Optional `gh` CLI integration for PR context info |
| Pre-Commit Gate | Complements `pre-commit-gate.sh` with deeper review |
| SDD Verify | Can replace or complement `sdd-verify` for PR-based workflows |

## GGA-Inspired Features

Patterns adopted from Gentleman Guardian Angel (MIT licensed):

| Feature | GGA Pattern | Our Implementation |
|---------|-------------|-------------------|
| Base branch detection | Auto-detect main/master | `CodeReviewer.detect_base_branch()` |
| Diff-only review | Review only changed lines | `CodeReviewer.review_diff()` |
| Structured status | PASSED/FAILED verdict | `ReviewReport.status` |
| File-level comments | Per-file findings | Grouped output in Step 6 |
| Memory integration | GGA issues #51/#52 (proposed) | Engram pre/post review |

## Contextual Trigger

This skill auto-loads when: PR review, pull request review, review PR,
review pull request, pre-merge check, merge review.
