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

## Wiring Status

### Completed (Gaps 1-4, 8)

| Gap | Component | Status | Details |
|-----|-----------|--------|---------|
| 1. SDD Pipeline Sync | `packages/paperclip-integration/hooks/paperclip-sdd-sync.sh` | DONE | PostToolUse Agent hook detects sdd-apply/verify/archive transitions, creates issues and pushes notifications |
| 2. Agent Heartbeat | `packages/paperclip-integration/hooks/paperclip-agent-status.sh` | DONE | PostToolUse Agent hook pushes agent completion status and trust scores |
| 3. Singularity Events | `lib/singularity.py` (`_push_singularity_to_paperclip`) | DONE | Inline wiring in `record_knowledge()` pushes event results as notifications |
| 4. Squad Org Chart Sync | `packages/paperclip-integration/hooks/paperclip-squad-sync.sh` | DONE | SessionStart hook reads squads/*.yaml and syncs to Paperclip org chart |
| 8. Error Recovery (Retry Queue) | `lib/paperclip_client.py` (`_RetryQueue`) | DONE | Failed POST/PUT requests queued in memory (max 100, 5min TTL), auto-retried on next success |

### Wired (Gaps 5-7)

| Gap | Component | Status | Details |
|-----|-----------|--------|---------|
| 5. Safety Mesh Block Sync | `hooks/_lib/paperclip-notify.sh` + hooks | DONE | Shared helper sourced by claim-validator.sh, confidence-gate.sh, completion-gate.sh. On exit 2 (BLOCK), pushes notification to Paperclip inbox. |
| 6. Active Task Sync | `packages/paperclip-integration/hooks/paperclip-task-sync.sh` | DONE | SessionStart hook reads active-tasks.json, pushes in_progress/pending tasks as Paperclip issues (COS -> Paperclip, one-directional). |
| 7. Cost Event Streaming | `packages/paperclip-integration/hooks/paperclip-cost-stream.sh` | DONE | PostToolUse Agent hook checks cumulative cost delta; pushes to Paperclip spend tracker when delta exceeds $0.10 threshold. |

#### Gap 5 Implementation Details

Shared helper `hooks/_lib/paperclip-notify.sh` provides `paperclip_notify()`, `paperclip_update_issue_status()`, `paperclip_push_spend()`, and `paperclip_push_tasks_as_issues()`. Any hook can source it and call these fire-and-forget functions. Currently wired into:
- `hooks/claim-validator.sh` -- notifies on hallucination BLOCK
- `hooks/confidence-gate.sh` -- notifies on low-confidence BLOCK
- `hooks/completion-gate.sh` -- sources the helper (ready for future BLOCK paths)

#### Gap 6 Implementation Details

`packages/paperclip-integration/hooks/paperclip-task-sync.sh` runs on SessionStart. It reads `.claude/tasks/active-tasks.json`, filters for `in_progress` and `pending` tasks, and creates Paperclip issues (capped at 20 to avoid flooding). One-directional: COS to Paperclip only. Bidirectional sync (Paperclip UI changes back to COS) requires Paperclip webhooks (not yet available).

#### Gap 7 Implementation Details

`packages/paperclip-integration/hooks/paperclip-cost-stream.sh` runs on PostToolUse for Agent. It reads `cost-events.jsonl`, calculates cumulative cost, and pushes to Paperclip `push_spend()` only when the delta since last push exceeds $0.10. The last-pushed amount is tracked in `metrics/.paperclip-cost-last-push` to avoid duplicate pushes.

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
