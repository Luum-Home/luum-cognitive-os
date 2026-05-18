---
name: release-os
command: /release-os
description: 'Use when you need this Cognitive OS skill: META — orchestrate the full
  Cognitive OS release by chaining the 5 atomic release skills; do not use when a
  narrower skill directly matches the task.'
version: 2.0.0
audience: os
tags:
- release
- meta
last-updated: 2026-04-10
disable-model-invocation: true
effort: sonnet
summary_line: META — orchestrate the full Cognitive OS release by chaining the 5 atomic…
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: "\b(tag|create)\s+(a\s+)?new\s+release\s+version\b"
  confidence: 0.99
- pattern: "\btag\s+(a\s+)?release\b"
  confidence: 0.94
routing_intents:
- intent: orchestrate_full_os_release
  description: User wants the meta release workflow that chains all atomic Cognitive OS release skills from preparation through publication.
  confidence: 0.9
- intent: coordinate_release_skill_sequence
  description: User asks which release phase to run next or wants end-to-end release coordination rather than one atomic release step.
  confidence: 0.86
triggers:
- release-os
- /release-os
- Release OS — META Skill
- META — orchestrate the full Cognitive OS release by chaining the 5 atomic…
---
<!-- SCOPE: os-only -->
# Release OS — META Skill

## Purpose

Thin orchestration wrapper that chains the 5 atomic release skills in order. Each step is independently invocable — use this META skill for a full end-to-end release, or invoke individual steps when you need fine-grained control.

## Atomic Skills (in order)

| Step | Skill | What it does |
|------|-------|--------------|
| 1 | `/validate-release` | Pre-flight checks: clean tree, correct branch, VERSION exists, CHANGELOG has content |
| 2 | `/bump-version [type\|version]` | Calculate and write new version to VERSION file |
| 3 | `/generate-changelog [version]` | Move [Unreleased] entries into a versioned section |
| 4 | `/tag-release [version]` | Create the release commit and annotated git tag |
| 5 | `/push-release` | Push commit and tags to remote (requires explicit confirmation) |

## When to Use

- `/release-os` — full release pipeline (asks for bump type, then runs all 5 steps)
- `/release-os minor` — full pipeline with bump type pre-specified
- `/release-os 1.2.3` — full pipeline with explicit version pre-specified
- Individual steps for partial releases or re-running a failed step

## Process

### Step 1: Run `/validate-release`

Load and execute the `validate-release` skill.

If FAIL: stop and report the failing check. Do NOT proceed.

### Step 2: Run `/bump-version [arg]`

If the user passed a version or bump type to `/release-os`, forward it to `/bump-version`.
If not, `/bump-version` will ask the user.

If FAIL: stop and report.

### Step 3: Run `/generate-changelog`

The version from Step 2 is used automatically (reads from VERSION file).

If FAIL: stop and report. The VERSION file was already updated — note this in the error.

### Step 4: Run `/tag-release`

If FAIL: stop and report. VERSION and CHANGELOG.md have already been updated but not committed.
Suggest: fix the issue and re-run `/tag-release` directly.

### Step 5: Run `/push-release`

This step always halts for user confirmation. The user may choose to skip (push later manually).

## Output

After each step, show that step's output. On full success:

```
RELEASE COMPLETE: vX.Y.Z
  1. validate-release: PASS
  2. bump-version: 0.1.0 → X.Y.Z
  3. generate-changelog: N entries moved
  4. tag-release: commit <hash>, tag vX.Y.Z
  5. push-release: pushed to origin | skipped

Next steps (if push was skipped):
  git push origin main --tags
```

## Safety Rules (inherited from atomic skills)

- NEVER release from a dirty working tree
- NEVER release from a branch other than `main` (unless explicitly overridden)
- NEVER auto-push — step 5 always requires confirmation
- If any step fails, stop immediately — do not continue with partial state
- Each atomic skill is safe to re-run individually after a failure

## Resuming a Partial Release

If the pipeline fails mid-way, identify the last successful step and re-run from the next step:

| Last success | Re-run from |
|---|---|
| validate-release | `/bump-version` |
| bump-version | `/generate-changelog` |
| generate-changelog | `/tag-release` |
| tag-release | `/push-release` |

## Integration

- **VERSION**: Single source of truth, updated by `/bump-version`
- **CHANGELOG.md**: Updated by `/generate-changelog`
- **git history**: Written by `/tag-release`
- **Remote**: Updated by `/push-release`
- **Engram**: Save release metadata after a successful push for cross-session tracking
