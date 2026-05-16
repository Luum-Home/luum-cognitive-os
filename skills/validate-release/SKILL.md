---
name: validate-release
command: /validate-release
description: 'Use when you need this Cognitive OS skill: Pre-release readiness check
  — validates working tree, branch, changelog, and VERSION file; do not use when a
  narrower skill directly matches the task.'
routing_intents:
  - "Check release readiness before tagging a Cognitive OS version"
  - "Validate working tree branch VERSION and CHANGELOG before release"
  - "Run the pre-release checklist and report blocking release issues"
  - "Confirm release metadata is consistent before creating a tag"
  - "Inspect dependency freshness and repository state for release approval"
version: 0.1.0
audience: os
tags:
- release
- validation
last-updated: 2026-04-10
disable-model-invocation: true
effort: haiku
summary_line: Pre-release readiness check — validates working tree, branch, changelog,
  and…
platforms:
- claude-code
prerequisites: []
triggers:
- validate-release
- /validate-release
- Validate Release
- Pre-release readiness check — validates working tree, branch, changelog, and…

---
<!-- SCOPE: os-only -->
# Validate Release

## Purpose

Run all pre-release checks before any release artifacts are created. This is the gate that must pass before `/bump-version`, `/generate-changelog`, `/tag-release`, or `/push-release` are run.

## Input

- Optional `--branch <name>` to allow releasing from a branch other than `main` (override)

## Output

```
VALIDATE RELEASE: PASS | FAIL
  Working tree: clean | DIRTY (N files)
  Branch: main | OTHER (current: <name>)
  VERSION file: found (X.Y.Z) | MISSING
  CHANGELOG [Unreleased]: has content | EMPTY
  cos check: passed | failed | skipped (not installed)
```

Exits 0 on PASS. Exits 1 on FAIL with the first failing check listed.

## When to Use

- As the first step before any release operation
- Can be run standalone to check readiness without committing to a release
- User says `/validate-release`

## Process

### Step 1: Check Working Tree

```bash
git status --porcelain
```

If output is non-empty: FAIL — list the dirty files.

### Step 2: Check Branch

```bash
git branch --show-current
```

Must be `main` (or the value passed via `--branch`). If not: FAIL.

### Step 3: Check VERSION File

```bash
cat VERSION
```

Must exist and contain a valid semver string (X.Y.Z). If missing or malformed: FAIL.

### Step 4: Check CHANGELOG

```bash
grep -A 3 '## \[Unreleased\]' CHANGELOG.md
```

The `[Unreleased]` section must have at least one non-empty line of content below the header. If empty or missing: FAIL.

### Step 5: cos Readiness (Optional)

```bash
cos release --check 2>/dev/null && echo "PASS" || echo "skipped (cos not installed)"
```

Failure here is advisory — report it but do NOT fail the overall check.

### Step 6: Dependency Freshness (Advisory)

```bash
bash scripts/deps-update.sh --audit 2>&1 | tail -15
```

Run the dependency audit and include its summary in the release readiness report. This is **advisory only** — stale deps warn but do NOT block the release. Operators should review and decide whether to upgrade before tagging.

## Safety Rules

- NEVER modify any files — this skill is read-only
- Report ALL failures, not just the first one
- If any non-advisory check fails, output FAIL and stop

## Trust Report

```
TRUST_REPORT: SCORE=90 STATUS=HIGH EVIDENCE=5 UNCERTAINTIES=1
---
Score: 90/100
EVIDENCE: All 5 checks run with concrete command output
CONFIDENT: Working tree state, branch name, file existence
UNSURE: cos CLI version compatibility varies across environments
VERIFY: Run git status --porcelain manually to confirm clean state
```
