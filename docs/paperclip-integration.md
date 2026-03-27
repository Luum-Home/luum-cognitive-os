# Paperclip Integration -- UI Layer for Cognitive OS

> Updated: 2026-03-27

## Vision

**Paperclip is the UI, Cognitive OS is the engine.**

Paperclip handles the visual layer: dashboard views, org chart visualization, issue tracking, spend display, and agent status monitoring. Cognitive OS handles the execution layer: SDD pipeline, safety mesh, quality gates, persistent memory (Engram), and model routing.

This integration eliminates the need to build a custom web dashboard (originally planned as Phase 2). Instead, Cognitive OS pushes state to Paperclip via its REST API, and Paperclip renders the UX.

## Architecture

```
User <---> Paperclip (UI on localhost:3200)
           |-- Dashboard: agents, goals, issues, spend
           |-- Inbox: notifications, blocked tasks, approvals
           |-- Org Chart: squad visualization
           '-- Issues: SDD pipeline phases as "issues"
                 |
                 '-- powered by Cognitive OS (engine)
                       |-- SDD pipeline       -> Paperclip "projects" + "issues"
                       |-- Agent Bus           -> Paperclip agent heartbeats
                       |-- Metrics JSONL       -> Paperclip spend tracking
                       |-- Squads YAML         -> Paperclip org chart
                       |-- cos packages        -> Paperclip skills marketplace
                       |-- Singularity events  -> Paperclip inbox
                       '-- Safety mesh blocks  -> Paperclip blocked status
```

## Concept Mapping

| Cognitive OS Concept | Paperclip Equivalent | Sync Direction |
|---|---|---|
| SDD change | Paperclip "project" | COS -> Paperclip |
| SDD phase (explore, propose, spec, design, tasks, apply, verify, archive) | Paperclip "issue" within project | COS -> Paperclip |
| Squad | Paperclip "org chart" team | COS -> Paperclip |
| Agent (sub-agent) | Paperclip "agent" with heartbeat | COS -> Paperclip |
| Safety mesh BLOCK | Paperclip "blocked" status on issue | COS -> Paperclip |
| Singularity event | Paperclip "inbox" notification | COS -> Paperclip |
| cost-events.jsonl | Paperclip monthly spend view | COS -> Paperclip |
| skill-metrics.jsonl | Paperclip agent performance | COS -> Paperclip |
| Planning Poker result | Paperclip issue estimate | COS -> Paperclip |
| Trust Report | Paperclip issue quality badge | COS -> Paperclip |

## What Already Exists

### Infrastructure

- **Docker services**: `paperclip` + `paperclip-pg` are defined in `docker-compose.cognitive-os.yml`. Paperclip runs on port 3200 (mapped from internal 3100).
- **Hook**: `hooks/paperclip-sync.sh` syncs session metrics to Paperclip on session Stop. It gathers error stats, cost events, skill metrics, and KPI snapshots, then pushes via the Python client (with curl fallback).
- **Python client**: `lib/paperclip_client.py` provides a thin REST API wrapper with `push_metrics()`, `push_kpis()`, `push_cost_events()`, `push_error_stats()`, and `push_session_summary()`.
- **Skill**: `skills/paperclip-dashboard/SKILL.md` displays health/repair stats from Paperclip.
- **Config**: `cognitive-os.yaml` has a `paperclip:` section with `enabled`, `url`, `sync_on_session_end`, and `artifacts` fields.

### API Endpoints Used

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check (availability detection) |
| POST | `/api/artifacts` | Push metrics, KPIs, cost events, session summaries |
| POST | `/api/projects` | Create/update SDD projects |
| POST | `/api/issues` | Create/update SDD phase issues |
| PUT | `/api/issues/{id}/status` | Update issue status (open/in_progress/blocked/done) |
| POST | `/api/agents/status` | Push agent heartbeat and status |
| POST | `/api/spend` | Push cost/spend data |
| POST | `/api/notifications` | Push inbox notifications |
| POST | `/api/org-chart` | Sync squad org chart |

## What Needs to Be Built

### 1. Expand `lib/paperclip_client.py`

The existing client covers metrics push. It needs to be expanded with:

- `PaperclipClient` class with configurable base URL
- `create_project()` -- maps SDD changes to Paperclip projects
- `create_issue()` -- maps SDD phases to Paperclip issues
- `update_issue_status()` -- sync phase state (open/in_progress/blocked/done)
- `update_agent_status()` -- push agent heartbeats from Agent Bus
- `push_spend()` -- push per-model cost data
- `push_notification()` -- push Singularity events to inbox
- `sync_org_chart()` -- sync squad YAML definitions to org chart API

### 2. Enhance `hooks/paperclip-sync.sh`

The hook currently pushes session summaries. It should also push:

- Active task list from `.claude/tasks/active-tasks.json` as Paperclip issues
- Agent completion statuses from the Agent Bus
- Session cost totals to the spend tracker

### 3. Singularity Integration

Update `lib/singularity.py` to push events to Paperclip inbox:
- Test failures, error patterns, coverage drops as notifications
- Severity mapping: `circuit_open` -> critical, `test_failure` -> warning, `stale_docs` -> info

### 4. Squad Sync

Map `squads/*.yaml` to the Paperclip org chart API:
- Each squad becomes a team
- Agent definitions within squads become team members
- Roles (manager, member) are mapped to Paperclip roles

### 5. SDD Pipeline Sync

When SDD phases transition (via `sdd-apply`, `sdd-verify`, etc.):
- Create or update a Paperclip "project" for the SDD change
- Create "issues" for each phase
- Update issue status as phases progress
- Mark issues as "blocked" when safety mesh blocks execution

## Data Flow

```
Session Start
    |
    v
infra-health.sh checks Paperclip availability
    |
    v
During Session:
  - SDD phases create/update Paperclip issues
  - Agent Bus heartbeats pushed to Paperclip agent status
  - Safety mesh blocks update issue status to "blocked"
  - Singularity events pushed to Paperclip inbox
    |
    v
Session End:
  - paperclip-sync.sh pushes session summary
  - Cost events pushed to spend tracker
  - KPI snapshot pushed to dashboard
```

## Configuration

In `cognitive-os.yaml`:

```yaml
paperclip:
  enabled: true
  url: ${COGNITIVE_OS_PAPERCLIP_URL:-http://localhost:3200}
  sync_on_session_end: true
  artifacts:
    - session_metrics
    - repair_outcomes
    - registry_snapshot
    - cost_events
    - agent_status
    - sdd_pipeline
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PAPERCLIP_URL` | `http://localhost:3200` | Paperclip server URL |
| `COGNITIVE_OS_PAPERCLIP_URL` | `http://localhost:3200` | Alternative env var (preferred) |

## Roadmap Impact

This integration **replaces** the "Phase 2: Visual Dashboard" item from the roadmap. Instead of building a custom Next.js dashboard:

- Paperclip provides the UX layer (already built, open-source)
- Cognitive OS pushes data via REST API (thin integration layer)
- The web dashboard roadmap item becomes "Paperclip integration" (smaller scope, faster delivery)

## Graceful Degradation

All Paperclip operations are fire-and-forget. If Paperclip is unavailable:

- `is_available()` returns `False`, all push operations are skipped silently
- The hook exits cleanly (exit 0)
- All Cognitive OS functionality works without Paperclip
- Metrics are still logged to local JSONL files regardless of Paperclip status

## Testing

Unit tests in `tests/unit/test_paperclip_client.py` cover:

- Availability detection (positive and negative)
- All CRUD operations with mocked HTTP
- Connection error handling (refused, timeout)
- URL configuration from environment variables
- Graceful degradation on failure
