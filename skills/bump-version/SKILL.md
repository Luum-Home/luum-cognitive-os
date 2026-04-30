<!-- SCOPE: os-only -->
---
name: bump-version
command: /bump-version
description: Calculate and write the new version to the VERSION file
version: 0.1.0
audience: os
tags: [release, versioning]
last-updated: 2026-04-10
disable-model-invocation: true
effort: haiku
platforms: ["claude-code"]
prerequisites: []
---

# Bump Version

## Purpose

Determine the next version number and write it to the `VERSION` file. Accepts an explicit version or a bump type (`patch`, `minor`, `major`).

## Input

One of:
- Explicit version: `/bump-version 1.2.3`
- Bump type: `/bump-version patch` | `/bump-version minor` | `/bump-version major`
- If neither provided: ask the user which bump type to use before proceeding

## Output

```
BUMP VERSION: X.Y.Z
  Previous: A.B.C
  New: X.Y.Z
  Bump type: patch | minor | major | explicit
  Written to: VERSION
```

Exits 0 on success. Exits 1 if VERSION file is missing or current version is malformed.

## When to Use

- After `/validate-release` passes
- Before `/generate-changelog` (changelog needs the new version number)
- User says `/bump-version [version_or_type]`

## Process

### Step 1: Read Current Version

```bash
CURRENT=$(cat VERSION)
```

Validate it is semver (X.Y.Z). If malformed: FAIL.

### Step 2: Calculate New Version

Given the input:

- **Explicit version** (e.g., `1.2.3`): use directly. Validate it is greater than current.
- **`patch`**: increment patch: `0.2.1 → 0.2.2`
- **`minor`**: increment minor, reset patch: `0.2.1 → 0.3.0`
- **`major`**: increment major, reset minor and patch: `0.2.1 → 1.0.0`
- **No input**: ask the user: "Current version is X.Y.Z. Bump patch, minor, or major?"

### Step 3: Write VERSION

```bash
echo "X.Y.Z" > VERSION
```

Verify the write:

```bash
cat VERSION
```

Output must equal the new version string.

## Safety Rules

- NEVER downgrade the version (new must be > current)
- NEVER write a non-semver string to VERSION
- If the user provides an explicit version that is <= current, ask for confirmation before proceeding
- Do NOT commit — that is the responsibility of `/tag-release`

## Trust Report

```
TRUST_REPORT: SCORE=95 STATUS=HIGH EVIDENCE=3 UNCERTAINTIES=1
---
Score: 95/100
EVIDENCE: Read current VERSION, calculated new version, verified write
CONFIDENT: Arithmetic is deterministic; file write is verified
UNSURE: User may have intended a different bump direction than what was inferred
VERIFY: cat VERSION should show the expected new version
```
