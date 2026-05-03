# Automation — Session Lifecycle, CI/CD, Scheduling, Agent Teams

## Session Lifecycle

Every Claude Code session follows this automated flow:

```
SESSION START
  |
  +-> stack-detector.sh runs
  |     -> generates .claude/detected-stack.json
  |
  +-> Rules loaded from .claude/rules/
  |     -> constitutional-gates, control-manifest, license-policy
  |     -> skill-adaptation, skill-auto-loader, skill-registry-protocol
  |
  +-> Engram context loaded (mem_context)
  |     -> past session summaries, decisions, discoveries
  |
  +-> skill-auto-loader checks for missing skills
        -> suggests generation if gaps found

DURING SESSION
  |
  +-> Every Bash command
  |     -> block-prod-urls.sh (PreToolUse)
  |
  +-> Every Edit/Write
  |     -> auto-test-on-edit.sh (PostToolUse)
  |
  +-> Every Agent/Skill use
  |     -> skill-feedback-tracker.sh (PostToolUse)
  |
  +-> Engram saves (proactive)
        -> decisions, bugs, discoveries, conventions

SESSION END
  |
  +-> mem_session_summary (mandatory)
        -> Goal, Instructions, Discoveries, Accomplished, Next Steps, Files
```

---

## CI/CD Integration — GitHub Actions

### PR Review (`claude-pr-review.yml`)

**Triggers**:
- Pull request opened or updated (synchronize)
- Comment containing `@claude` on a PR

**What it does**:
1. Checks out the full repo (fetch-depth: 0)
2. Runs Claude (claude-sonnet-4-6, max 10 turns) with a structured review prompt
3. Reviews against:
   - Architecture rules (mobile-to-BFF only, allowed service dependencies)
   - Mock flags (not accidentally disabled, new providers need mocks)
   - Security (no prod URLs, no hardcoded secrets, no committed .env)
   - Quality (tests for new code, idempotent financials, audit trails, API compatibility)
4. Identifies affected services by file paths
5. Posts structured review: Summary, Architecture Compliance, Security, Test Coverage, Suggestions

**Required secret for this CI-only Claude action**: `ANTHROPIC_API_KEY`

### Issue Triage (`claude-issue-triage.yml`)

**Trigger**: Issue opened

**What it does**:
1. Checks out the repo
2. Runs Claude (claude-sonnet-4-6, max 5 turns) to analyze the issue
3. Identifies affected service(s) using label scheme:
   - `service:mobile-app`, `service:<consumer-codename-a>`, `service:<consumer-codename-b>`, etc.
4. Classifies issue type: `bug`, `feature`, `enhancement`, `chore`, `docs`
5. Estimates priority: `priority:critical`, `priority:high`, `priority:medium`, `priority:low`
6. Adds labels and posts a comment with context

**Required secret for this CI-only Claude action**: `ANTHROPIC_API_KEY`

---

## Scheduled Tasks

Claude Code supports scheduled tasks via the `mcp__scheduled-tasks` tools.

### Daily Health Check

The `daily-health-check` skill can be scheduled to run on weekdays:

```
Schedule: 0 9 * * 1-5 (9:00 AM, Mon-Fri, local time)
```

It checks:
- Docker container status
- Service health endpoints (BFF, <consumer-codename-b>, <consumer-codename-c>, onboarding, gateway, auth-provider)
- Infrastructure probes (MySQL, MongoDB, Redis, RabbitMQ)
- Reports OK/DOWN status with troubleshooting suggestions

### Creating scheduled tasks

Use the `create_scheduled_task` tool:
- `cronExpression` for recurring tasks (local timezone)
- `fireAt` for one-time tasks (ISO 8601 with offset)
- `prompt` contains the full instructions for what Claude should do

---

## Agent Teams (Experimental)

Enabled via environment variable in `settings.local.json`:
```json
{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
```

### How it works

```
Orchestrator (main thread)
  |
  +-> Delegates to sub-agents (async by default)
  |     -> Each sub-agent gets a fresh context
  |     -> Each sub-agent gets pre-resolved skill paths
  |     -> Each sub-agent saves discoveries to Engram
  |
  +-> Synthesizes results
  +-> Tracks state via Engram
```

### Orchestrator rules
- **Never** reads/writes code directly
- **Always** delegates via `delegate` (async) or `task` (sync, only when result needed immediately)
- Resolves skill paths from registry once per session, passes them to sub-agents
- Sub-agents do NOT search for skills themselves

### SDD Workflow (Spec-Driven Development)

For substantial changes, uses a structured multi-phase workflow:

```
/sdd-new "change name"
  |
  v
sdd-explore -> sdd-propose -> sdd-spec  -> sdd-tasks -> sdd-apply -> sdd-verify -> sdd-archive
                                  ^
                                  |
                              sdd-design
```

Each phase:
- Has a dedicated skill in `~/.claude/skills/`
- Reads required artifacts from Engram (topic keys: `planning/{change-name}/{phase}`)
- Writes its artifact back to Engram
- Returns: status, executive_summary, artifacts, next_recommended, risks

### Task scaling (from control-manifest)

| Complexity | Approach |
|------------|----------|
| Trivial (single file, < 20 lines) | Direct, no workflow |
| Small (1-3 files) | Consider `/opsx:propose` |
| Medium (multi-file feature) | `/opsx:propose` then `/opsx:apply` |
| Large (multi-service) | `/sdd-new` then `/sdd-ff` then `/sdd-apply` |
| Critical (security, payments) | `/sdd-new` with mandatory `/sdd-verify` |
