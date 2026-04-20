<!-- SCOPE: both -->
---
name: issue-pipeline
version: 1.0.0
description: Fetch a GitHub issue, run the SDD pipeline, and open a pull request
invoke: /issue-to-pr <number>
tags: [universal, automation, pipeline]
audience: project
---

# Issue-to-PR Pipeline

Automates the full lifecycle from GitHub issue to pull request using the SDD pipeline.

## Invoke

```
/issue-to-pr <issue-number>
```

## What It Does

1. **Fetch** the GitHub issue (title, body, labels, assignees) via `gh issue view`
2. **Classify** the issue as `feature`, `bug`, or `chore` based on labels and content
3. **Create branch** with format `{feat|fix|chore}-issue-{number}-{slug}`
4. **Create worktree** at `.cognitive-os/worktrees/{workflow_id}/` with deterministic ports
5. **Run SDD pipeline** (explore -> propose -> spec -> design -> tasks -> apply -> verify)
6. **Create PR** with `Closes #{number}` reference
7. **Post status comments** on the issue with `[COS-AGENTS]` identifier
8. **Cleanup** worktree after completion

## Usage

### From skill invocation

```
/issue-to-pr 42
```

### From Python

```python
from lib.issue_pipeline import IssuePipeline

pipeline = IssuePipeline(project_dir="/path/to/repo")
result = pipeline.run(42)

if result.success:
    print(f"PR: {result.pr_url}")
```

### From CLI

```bash
python -m lib.issue_pipeline 42 --verbose
```

## Prerequisites

- `gh` CLI authenticated with repo access
- `claude` CLI available in PATH
- Git repository with remote configured

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `project_dir` | `.` | Repository root |
| `base_branch` | `main` | Target branch for PR |
| `model` | (default) | Claude model override |
| `timeout_per_phase` | 900s | Max time per SDD phase |

## Port Allocation

Each worktree gets deterministic ports based on workflow ID hash:
- Backend: `9100 + offset` (range 9100-9199)
- Frontend: `9200 + offset` (range 9200-9299)

## Error Handling

- On SDD failure: posts failure comment on issue, cleans up worktree
- On PR creation failure: posts failure comment, preserves branch for manual recovery
- All errors include workflow ID for debugging

## Status Comments

The pipeline posts `[COS-AGENTS]` prefixed comments on the issue:
- `in-progress` — when SDD pipeline starts
- `completed` — with PR link and phase timings
- `failed` — with error details and workflow ID
