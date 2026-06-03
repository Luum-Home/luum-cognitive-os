---
name: bump-version
invocation_pattern: on-demand
command: /bump-version
description: 'Use when you need this Cognitive OS skill: Calculate and write the new
  version to the VERSION file. Prefer a narrower skill when it directly matches
  the task.'
version: 0.1.0
audience: os
tags:
- release
- versioning
last-updated: 2026-04-10
disable-model-invocation: true
effort: haiku
platforms:
- claude-code
prerequisites: []
routing_intents:
- intent: update_version_file
  description: User wants the project VERSION file calculated and rewritten for a
    release or version bump, without broader release note generation.
  confidence: 0.86
- intent: determine_next_project_version
  description: User asks for the next Cognitive OS version value to be derived and
    persisted, rather than only inspecting current version metadata.
  confidence: 0.83
triggers:
- bump-version
- /bump-version
- Bump Version
- 'Use when you need this Cognitive OS skill: Calculate and write the new version
  to the VERSION file. Prefer a narrower skill when it directly matches the task.'
---
<!-- SCOPE: os-only -->
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

### Step 3: Write VERSION (lockstep — both files)

The OS uses TWO version files in lockstep (decided 2026-05-06):
- `VERSION` (root) — canonical Cognitive OS version stream
- `cmd/cos/VERSION` — Go binary build version, equal to root VERSION

Write to BOTH:

```bash
echo "X.Y.Z" > VERSION
echo "X.Y.Z" > cmd/cos/VERSION
```

Verify both:

```bash
test "$(cat VERSION)" = "$(cat cmd/cos/VERSION)" || { echo "VERSION drift"; exit 1; }
cat VERSION
```

Output equals the new version string and both files match.

Rationale: `cos` Go binary is Surface 1 of the OS (ADR-172). Streams stay
synced unless a future ADR explicitly bifurcates (e.g. `cos-vX.Y` prefix
tags). Until then, keep them in lockstep.

## Safety Rules

- Keep version monotonic: new version > current version
- Write only valid semver strings to VERSION
- Write VERSION + cmd/cos/VERSION in lockstep — drift is a release blocker
- If the user provides an explicit version that is <= current, ask for confirmation before proceeding
- Leave committing to `/tag-release`

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
