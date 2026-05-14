---
name: webhook-trigger
description: GitHub webhook server that receives issue events and launches SDD pipelines
  automatically via ClaudeExecutor.
version: 1.0.0
last-updated: 2026-03-26
user-invocable: true
auto-generated: false
tech: python, fastapi
audience: project
summary_line: GitHub webhook server that receives issue events and launches SDD pipelines…
platforms:
- claude-code
prerequisites: []
triggers:
- webhook-trigger
- /webhook-trigger
- Webhook Trigger
- GitHub webhook server that receives issue events and launches SDD pipelines…
---
<!-- SCOPE: both -->
# Webhook Trigger

GitHub webhook server that receives issue events and launches SDD pipelines automatically.

## What It Does

1. **Receives** GitHub webhook events: `issues.opened`, `issues.labeled`, `issue_comment.created`
2. **Detects** trigger keywords in issue body or comments: `[sdd-auto]`, `[ai-workflow]`, `@luum-bot`
3. **Classifies** the issue as feature, bug, or chore based on labels or `/classify_issue` pattern
4. **Launches** the SDD pipeline in background via `ClaudeExecutor`
5. **Posts** status comments on the GitHub issue as each phase completes or fails

## Architecture

```
GitHub Issue Event
       |
       v
  [Webhook Server]  (lib/webhook_trigger.py)
       |
       +-- Verify HMAC-SHA256 signature
       +-- Parse event type + action
       +-- Detect trigger keyword
       +-- Classify issue (labels -> title -> body -> default)
       +-- Derive change name: issue-{N}-{slug}
       |
       v
  [Background Thread]
       |
       +-- Post "Pipeline Started" comment via gh CLI
       +-- Run SDD phases sequentially via ClaudeExecutor:
       |     explore -> propose -> spec -> design -> tasks -> apply -> verify
       +-- Post status comment after each phase
       +-- On failure: halt pipeline, post error details
       +-- On success: post "Pipeline Complete" summary
```

## Prerequisites

- Python 3.9+
- `fastapi` and `uvicorn` (in requirements.txt)
- `gh` CLI installed and authenticated
- `claude` CLI available in PATH
- GitHub webhook configured to point to this server

## Configuration (Environment Variables)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_WEBHOOK_SECRET` | Recommended | _(empty)_ | HMAC-SHA256 secret for webhook validation |
| `GITHUB_TOKEN` | Recommended | _(empty)_ | GitHub token passed to `gh` CLI for posting comments |
| `WEBHOOK_PORT` | No | `8001` | HTTP port for the webhook server |
| `WEBHOOK_PROJECT_DIR` | No | `cwd` | Working directory for ClaudeExecutor |
| `CLAUDE_BIN` | No | `claude` | Path to the Claude CLI binary |
| `CLAUDE_TIMEOUT` | No | `900` | Timeout per phase in seconds |

## Running Locally

```bash
# Set required env vars
export GITHUB_WEBHOOK_SECRET="your-secret"
export GITHUB_TOKEN="ghp_..."

# Run directly
python lib/webhook_trigger.py

# Or with uvicorn
uvicorn lib.webhook_trigger:app --host 0.0.0.0 --port 8001
```

## Running with Docker

```bash
cd infra/webhook
docker build -t luum-webhook-trigger -f Dockerfile ../..
docker run -d \
  -p 8001:8001 \
  -e GITHUB_WEBHOOK_SECRET="your-secret" \
  -e GITHUB_TOKEN="ghp_..." \
  -e WEBHOOK_PROJECT_DIR=/workspace \
  -v /path/to/your/project:/workspace \
  luum-webhook-trigger
```

## GitHub Webhook Setup

1. Go to your repo Settings -> Webhooks -> Add webhook
2. **Payload URL**: `https://your-server:8001/gh-webhook`
3. **Content type**: `application/json`
4. **Secret**: Same value as `GITHUB_WEBHOOK_SECRET`
5. **Events**: Select individual events:
   - Issues
   - Issue comments

## Trigger Keywords

Include any of these in the issue body or a comment to trigger the pipeline:

- `[sdd-auto]` -- Recommended for automated workflows
- `[ai-workflow]` -- Backward-compatible with legacy AI-Workflow system
- `@luum-bot` -- Mention-style trigger

## Issue Classification

Priority order:
1. **Labels**: `bug`/`fix`/`hotfix` -> bug, `feature`/`enhancement`/`feat` -> feature, `chore`/`refactor`/`docs`/`ci` -> chore
2. **Body command**: `/classify_issue feature` (or `bug`, `chore`)
3. **Title heuristics**: Words like "bug", "fix", "error" -> bug; "chore", "refactor" -> chore
4. **Default**: feature

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/gh-webhook` | GitHub webhook receiver |

## Bot Loop Prevention

The bot tags every comment with `<!-- luum-bot -->`. Comments containing this marker are ignored to prevent self-triggering loops.

## Integration with Cognitive OS

- Uses `lib/claude_executor.py` for SDD phase execution
- Follows the SDD dependency chain: explore -> propose -> spec -> design -> tasks -> apply -> verify
- Posts progress as GitHub issue comments for full traceability
- Change name derived from issue number + title slug for Engram topic key compatibility
