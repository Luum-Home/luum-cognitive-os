---
name: release-os
command: /release-os
description: Validate, version, tag, and release the Cognitive OS
version: 1.0.0
audience: os-dev
last-updated: 2026-03-28
---

# Release OS -- Cognitive OS Release Skill

## Purpose

Automate the release process for Cognitive OS: validate readiness, bump version, update changelog, commit, tag, and optionally push. Ensures consistent, repeatable releases.

## When to Use

- Before publishing a new version of Cognitive OS
- After a batch of features/fixes are ready for release
- When the user says `/release-os`

## Prerequisites

Before running, the skill validates:
1. Working tree is clean (`git status --porcelain` is empty)
2. On the `main` branch
3. CHANGELOG.md has content under `[Unreleased]`
4. VERSION file exists
5. `cos release --check` passes (if cos CLI is available)

## Process

### Step 1: Pre-Validation

Run pre-release checks:

```bash
# Clean working tree
git status --porcelain

# On main branch
git branch --show-current

# CHANGELOG has unreleased content
grep -A1 '## \[Unreleased\]' CHANGELOG.md

# VERSION file exists
cat VERSION

# cos release readiness (optional, skip if cos not installed)
cos release --check 2>/dev/null || echo "cos CLI not available, skipping"
```

If any check fails, report the issue and stop. Do not proceed with a dirty tree or missing changelog entries.

### Step 2: Determine Version

Accept version from user or prompt for bump type:

- If user provides explicit version (e.g., `/release-os 1.0.0`): use it
- If user provides bump type (e.g., `/release-os minor`): calculate from current VERSION
  - `patch`: 0.2.0 -> 0.2.1
  - `minor`: 0.2.0 -> 0.3.0
  - `major`: 0.2.0 -> 1.0.0
- If neither: ask the user which bump type to use

### Step 3: Update VERSION File

Write the new version to `VERSION`:

```bash
echo "X.Y.Z" > VERSION
```

### Step 4: Update CHANGELOG.md

Move `[Unreleased]` content to a new version section:

1. Read current CHANGELOG.md
2. Replace `## [Unreleased]` section:
   - Add empty `## [Unreleased]` at the top
   - Create `## [X.Y.Z] - YYYY-MM-DD` with the previous unreleased content
3. Write updated CHANGELOG.md

The format follows [Keep a Changelog](https://keepachangelog.com/).

### Step 5: Commit

Create a release commit:

```bash
git add VERSION CHANGELOG.md
git commit -m "release: vX.Y.Z"
```

### Step 6: Create Git Tag

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

### Step 7: Package Tags (Optional)

If `cos` CLI is available, create package-level tags for packages with unreleased changes:

```bash
cos release-all --patch --dry-run  # Show what would be tagged
cos release-all --patch            # Create package tags
```

Only run if the user confirms.

### Step 8: Push (Optional)

Ask the user before pushing:

```bash
git push origin main --tags
```

Only push if the user explicitly confirms. Never auto-push.

## Safety Rules

- NEVER release from a dirty working tree
- NEVER release from a branch other than main (unless user explicitly overrides)
- NEVER auto-push -- always ask for confirmation
- NEVER skip CHANGELOG validation
- If any step fails, stop and report -- do not continue partial releases
- The release commit message MUST follow the format: `release: vX.Y.Z`

## Output

After successful release:

```
RELEASE COMPLETE:
  Version: vX.Y.Z
  Commit: {short hash}
  Tag: vX.Y.Z
  Changelog: Updated with {N} entries
  Package tags: {created|skipped}
  Pushed: {yes|no}

Next steps:
  - Push if not yet pushed: git push origin main --tags
  - Announce the release
```

## Integration

- **VERSION**: Single source of truth for OS version
- **CHANGELOG.md**: Human-readable release notes
- **cos CLI**: Package-level releases for monorepo packages
- **Engram**: Save release metadata for cross-session tracking
