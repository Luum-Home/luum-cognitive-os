---
name: generate-changelog
invocation_pattern: on-demand
command: /generate-changelog
description: 'Use when you need this Cognitive OS skill: Move [Unreleased] CHANGELOG
  entries into a versioned release section; do not use when a narrower skill directly
  matches the task.'
version: 0.1.0
audience: os
tags:
- release
- changelog
last-updated: 2026-04-10
disable-model-invocation: true
effort: haiku
platforms:
- claude-code
prerequisites: []
triggers:
- generate-changelog
- /generate-changelog
- Generate Changelog
- 'Use when you need this Cognitive OS skill: Move [Unreleased] CHANGELOG entries
  into a versioned release section; do not '
---
<!-- SCOPE: os-only -->
# Generate Changelog

## Purpose

Update `CHANGELOG.md` by moving the `[Unreleased]` section into a versioned release section with today's date. Leaves an empty `[Unreleased]` section at the top for future entries.

## Input

- Version string (X.Y.Z) — from `VERSION` file or passed directly: `/generate-changelog 1.2.3`

## Output

```
GENERATE CHANGELOG: X.Y.Z
  Date: YYYY-MM-DD
  Entries moved: N lines
  Section created: ## [X.Y.Z] - YYYY-MM-DD
  Unreleased section: reset (empty)
```

Exits 0 on success. Exits 1 if CHANGELOG.md is missing or `[Unreleased]` section has no content.

## When to Use

- After `/bump-version` (needs the new version number)
- Before `/tag-release` (changelog must be updated before commit)
- User says `/generate-changelog [version]`

## Process

### Step 1: Read Version

If version not passed as argument, read from VERSION file:

```bash
VERSION=$(cat VERSION)
```

### Step 2: Read CHANGELOG

Read the full contents of `CHANGELOG.md`.

### Step 3: Validate [Unreleased] Has Content

The section between `## [Unreleased]` and the next `## [` header must have at least one non-empty, non-whitespace line. If empty: FAIL with message "Nothing to release — [Unreleased] section is empty."

### Step 4: Transform the Changelog

Perform the following transformation:

**Before:**
```markdown
## [Unreleased]

### Added
- New feature X

## [0.1.0] - 2026-03-01
...
```

**After:**
```markdown
## [Unreleased]

## [X.Y.Z] - YYYY-MM-DD

### Added
- New feature X

## [0.1.0] - 2026-03-01
...
```

Algorithm:
1. Find the line containing `## [Unreleased]`
2. Collect all lines between that header and the next `## [` header (exclusive) — this is the "unreleased content"
3. Replace the original `[Unreleased]` block with:
   - `## [Unreleased]` (empty, followed by a blank line)
   - `## [X.Y.Z] - YYYY-MM-DD` (new section header)
   - The collected unreleased content
4. Write the updated file back to `CHANGELOG.md`

### Step 5: Verify

Confirm the new section exists:

```bash
grep "## \[$VERSION\]" CHANGELOG.md
```

And that `[Unreleased]` section is now empty:

```bash
grep -A 1 '## \[Unreleased\]' CHANGELOG.md
```

The line after `[Unreleased]` must be blank or start with `## [`.

## Format Compliance

Follows [Keep a Changelog](https://keepachangelog.com/) format:
- Version headers: `## [X.Y.Z] - YYYY-MM-DD`
- Change types: `### Added`, `### Changed`, `### Fixed`, `### Removed`, `### Security`, `### Deprecated`

## Safety Rules

- NEVER delete any existing versioned sections
- NEVER modify content from previously released sections
- If CHANGELOG.md does not exist: FAIL with message "CHANGELOG.md not found"
- Do NOT commit — that is the responsibility of `/tag-release`
- Use today's date (`date +%Y-%m-%d`) for the release date

## Trust Report

```
TRUST_REPORT: SCORE=90 STATUS=HIGH EVIDENCE=3 UNCERTAINTIES=1
---
Score: 90/100
EVIDENCE: Verify [Unreleased] has content before transforming; verify new section exists after
CONFIDENT: Changelog format transformation is deterministic
UNSURE: Edge cases with non-standard changelog formats may not be handled
VERIFY: grep "## [X.Y.Z]" CHANGELOG.md to confirm section was created
```
