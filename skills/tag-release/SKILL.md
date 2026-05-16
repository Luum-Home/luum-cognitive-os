---
name: tag-release
invocation_pattern: on-demand
command: /tag-release
description: 'Use when you need this Cognitive OS skill: Create the release commit
  (VERSION + CHANGELOG) and annotated git tag; do not use when a narrower skill directly
  matches the task.'
routing_intents:
  - "Create a release commit for VERSION and CHANGELOG updates"
  - "Make an annotated git tag for a Cognitive OS release version"
  - "Finalize release metadata and tag the repository for publishing"
  - "Stage release files and produce the official release tag"
  - "Prepare versioned release history with changelog and annotated tag"
version: 0.1.0
audience: os
tags:
- release
- git
last-updated: 2026-04-10
disable-model-invocation: true
effort: haiku
platforms:
- claude-code
prerequisites: []
triggers:
- tag-release
- /tag-release
- Tag Release
- 'Use when you need this Cognitive OS skill: Create the release commit (VERSION +
  CHANGELOG) and annotated git tag; do not'

---
<!-- SCOPE: os-only -->
# Tag Release

## Purpose

Create the release commit and annotated git tag. This is the only step that writes to git history. Commit includes `VERSION` and `CHANGELOG.md`. Optionally also creates package-level tags via `cos release-all`.

## Input

- Version string (X.Y.Z) — from `VERSION` file or passed directly: `/tag-release 1.2.3`
- Optional `--packages` flag to also create package tags via `cos release-all`

## Output

```
TAG RELEASE: vX.Y.Z
  Commit: <short hash>  "release: vX.Y.Z"
  Tag: vX.Y.Z (annotated)
  Package tags: created | skipped
```

Exits 0 on success. Exits 1 if commit or tag creation fails.

## When to Use

- After `/bump-version` and `/generate-changelog` have both run
- Before `/push-release`
- User says `/tag-release [version]`

## Prerequisites

Before running, verify:
1. `VERSION` file contains the expected version
2. `CHANGELOG.md` has a `## [X.Y.Z]` section for the version being released
3. Working tree has only `VERSION` and `CHANGELOG.md` as modified files

If other files are modified: warn the user and ask for confirmation.

## Process

### Step 1: Read Version

```bash
VERSION=$(cat VERSION)
```

If argument provided, use that and verify it matches VERSION file.

### Step 2: Stage Release Files

```bash
git add VERSION CHANGELOG.md
```

### Step 3: Create Release Commit

```bash
git commit -m "release: v${VERSION}"
```

Verify commit was created:

```bash
git log --oneline -1
```

Output must contain `release: v${VERSION}`.

### Step 4: Create Annotated Tag

```bash
git tag -a "v${VERSION}" -m "Release v${VERSION}"
```

Verify tag exists:

```bash
git tag --list "v${VERSION}"
```

### Step 5: Package Tags (Optional)

Only if user passes `--packages` or confirms when prompted:

```bash
cos release-all --patch --dry-run  # Preview what would be tagged
```

Show output and ask: "Create these package tags? (yes/no)"

If confirmed:

```bash
cos release-all --patch
```

If `cos` is not installed, skip with note.

## Safety Rules

- NEVER commit files other than VERSION and CHANGELOG.md (unless user explicitly adds them)
- NEVER use `git commit --amend` — always create a new commit
- NEVER force-tag — if the tag already exists, FAIL with message "Tag vX.Y.Z already exists"
- The commit message MUST follow the exact format: `release: vX.Y.Z`
- Do NOT push — that is the responsibility of `/push-release`

## Trust Report

```
TRUST_REPORT: SCORE=95 STATUS=HIGH EVIDENCE=4 UNCERTAINTIES=1
---
Score: 95/100
EVIDENCE: Verify staged files, verify commit message, verify tag exists
CONFIDENT: Git operations are verifiable immediately after execution
UNSURE: Tag signing may be required in some repo configurations (not handled here)
VERIFY: git log --oneline -1 and git tag --list "vX.Y.Z" to confirm
```
