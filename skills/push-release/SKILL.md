<!-- SCOPE: os-only -->
---
name: push-release
command: /push-release
description: Push the release commit and tags to the remote — always requires explicit confirmation
version: 0.1.0
audience: os
tags: [release, git]
last-updated: 2026-04-10
disable-model-invocation: true
effort: haiku
summary_line: Push the release commit and tags to the remote — always requires explicit…

---

# Push Release

## Purpose

Push the release commit and all tags to the remote repository. This is the final, irreversible step of the release process. ALWAYS requires explicit user confirmation before executing.

## Input

- Optional `--remote <name>` to specify the remote (default: `origin`)
- Optional `--branch <name>` to specify the branch (default: `main`)

## Output

```
PUSH RELEASE: vX.Y.Z
  Remote: origin
  Branch: main
  Tags: pushed
  URL: <remote URL>
```

Exits 0 on success. Exits 1 if push fails. Never auto-executes — always waits for confirmation.

## When to Use

- After `/tag-release` has created the commit and tag
- Only when the user is ready to make the release public
- User says `/push-release`

## Process

### Step 1: Show What Will Be Pushed

Before asking for confirmation, show:

```bash
git log origin/main..HEAD --oneline
git tag --list "v*" | tail -5
```

Format the summary:

```
About to push to origin:
  Commits: N new commits
    - <hash> release: vX.Y.Z
  Tags: vX.Y.Z
  Remote: git@github.com:org/repo.git

This is IRREVERSIBLE. Proceed? (yes/no)
```

### Step 2: Wait for Explicit Confirmation

HALT. Do NOT proceed until the user explicitly types "yes" or equivalent.

Accepted: "yes", "y", "proceed", "push", "go"
Rejected: everything else → STOP with message "Push cancelled."

### Step 3: Push Branch

```bash
git push origin main
```

If push is rejected (remote has diverged): FAIL with message and instructions to reconcile.

### Step 4: Push Tags

```bash
git push origin --tags
```

### Step 5: Confirm Success

```bash
git log --oneline -1
```

And verify the remote received the tag by attempting a remote ls (optional, non-blocking):

```bash
git ls-remote origin "refs/tags/vX.Y.Z" 2>/dev/null | head -1
```

## Safety Rules

- NEVER auto-push — the explicit confirmation is mandatory, not optional
- NEVER use `--force` or `--force-with-lease` — if push is rejected, report and stop
- If the user says "no", "cancel", or anything other than explicit confirmation: stop cleanly
- If the remote tag already exists: warn and ask whether to skip tags or abort

## Post-Release Notes

After a successful push, output next-step suggestions:

```
RELEASE PUSHED: vX.Y.Z

Next steps:
  - Announce the release (GitHub Release, Slack, etc.)
  - Archive release notes in Engram for cross-session tracking
  - Update any documentation that references the version
```

## Trust Report

```
TRUST_REPORT: SCORE=95 STATUS=HIGH EVIDENCE=3 UNCERTAINTIES=1
---
Score: 95/100
EVIDENCE: Show pre-push summary, verify push output, check remote tag
CONFIDENT: Git push output clearly indicates success or failure
UNSURE: Network failures or auth issues may cause partial pushes not detected here
VERIFY: git ls-remote origin refs/tags/vX.Y.Z to confirm tag is on remote
```
