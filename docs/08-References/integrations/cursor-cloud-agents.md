# Integration Design: Cognitive OS + Cursor Cloud Agents

> Status: Design phase
> Last updated: 2026-03-27

## Vision

Cursor provides the best AI code execution engine available (isolated VMs, video proof, enterprise-scale workers). Cognitive OS provides the governance, memory, and orchestration layer that Cursor lacks. Together they form a complete AI-driven software development system.

## Architecture

```
                    ┌─────────────────────────────┐
                    │        Human (Decision)       │
                    │   Reviews video + Trust Report │
                    │   Approves / gives feedback    │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────v──────────────────┐
                    │    Cognitive OS (Layer 2)     │
                    │                              │
                    │  ┌─────────┐ ┌────────────┐  │
                    │  │ Engram  │ │ Cost Track  │  │
                    │  │ Memory  │ │ Budget Mgmt │  │
                    │  └─────────┘ └────────────┘  │
                    │  ┌─────────┐ ┌────────────┐  │
                    │  │ Quality │ │ Adaptive   │  │
                    │  │ Gates   │ │ Bypass     │  │
                    │  └─────────┘ └────────────┘  │
                    │  ┌─────────┐ ┌────────────┐  │
                    │  │   SDD   │ │   Squads   │  │
                    │  │Pipeline │ │ Coordinate │  │
                    │  └─────────┘ └────────────┘  │
                    └──────────┬──────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────v──────┐ ┌──────v───────┐ ┌──────v───────┐
     │ Cursor Agent 1│ │Cursor Agent 2│ │Cursor Agent 3│
     │   (VM #1)     │ │   (VM #2)    │ │   (VM #3)    │
     │ ┌───────────┐ │ │ ┌──────────┐ │ │ ┌──────────┐ │
     │ │ Terminal   │ │ │ │ Terminal │ │ │ │ Terminal │ │
     │ │ Browser    │ │ │ │ Browser  │ │ │ │ Browser  │ │
     │ │ Desktop    │ │ │ │ Desktop  │ │ │ │ Desktop  │ │
     │ └───────────┘ │ │ └──────────┘ │ │ └──────────┘ │
     │  Video proof  │ │ Video proof  │ │ Video proof  │
     │  PR ready     │ │ PR ready     │ │ PR ready     │
     └───────────────┘ └──────────────┘ └──────────────┘
```

## Integration Points

### 1. Task Dispatch (COS -> Cursor)

When COS receives a task (from user, ticket system, or Singularity):

1. COS classifies complexity (adaptive bypass)
2. COS checks budget (rate limiting, cost governance)
3. COS selects workflow:
   - Trivial: handle directly in COS, no Cursor agent needed
   - Small-Medium: dispatch to single Cursor agent
   - Large-Critical: dispatch to multiple Cursor agents via SDD phases
4. COS prepares agent context:
   - Relevant Engram observations (selective retrieval)
   - Applicable rules (from contextual trigger matching)
   - Acceptance criteria (measurable, verifiable)
   - Phase-specific behavior instructions
5. COS triggers Cursor agent via API/webhook with prepared context

### 2. Result Validation (Cursor -> COS)

When a Cursor agent completes:

1. COS receives the PR + video artifact
2. COS runs acceptance criteria commands
3. COS validates claims (anti-hallucination: do the files exist? do tests pass?)
4. COS calculates trust score
5. COS saves learnings to Engram
6. COS tracks cost (tokens used, time elapsed)
7. COS presents human with: video + Trust Report + PR diff

### 3. Multi-Agent Coordination

For large tasks requiring multiple Cursor agents:

1. COS breaks task via SDD: spec -> design -> tasks
2. Each task dispatched to a separate Cursor agent
3. COS tracks progress via Agent Bus (if enabled) or polling
4. COS handles dependencies between tasks (task B waits for task A)
5. COS aggregates results and runs cross-agent verification
6. COS manages retry loop (if agent fails, re-dispatch with error context)

### 4. Memory Sharing

Cursor agents start fresh (no memory). COS bridges this:

1. Before dispatch: COS queries Engram for relevant context, injects into agent prompt
2. After completion: COS extracts learnings from agent output, saves to Engram
3. Next agent for same project: COS injects accumulated learnings
4. Cross-project: COS shares relevant patterns across projects via Engram namespaces

## Configuration

```yaml
# cognitive-os.yaml addition
integrations:
  cursor:
    enabled: false                    # Opt-in
    mode: self-hosted                 # self-hosted | cloud
    worker_endpoint: localhost:8080   # For self-hosted workers
    api_key: ${CURSOR_API_KEY}        # For cloud API triggers
    max_parallel_agents: 5            # COS-enforced limit
    dispatch_method: api              # api | webhook | slack
    video_review: true                # Include video in Trust Report
    cost_per_agent_minute: 0.02       # For budget tracking
```

## Prerequisites

- Cursor Business/Enterprise plan (for cloud agents API)
- `agent worker start` running on target infrastructure (for self-hosted)
- Cognitive OS installed with Engram configured
- API key or webhook URL for agent dispatch

## Implementation Phases

### Phase 1: Manual Integration (now possible)
- User triggers Cursor agent manually
- COS provides context via copy-paste or CLAUDE.md
- COS validates result after PR is created
- Manual cost tracking

### Phase 2: API Integration (requires Cursor API)
- COS dispatches tasks to Cursor via API
- COS receives completion webhooks
- Automated acceptance criteria verification
- Automated cost tracking

### Phase 3: Full Orchestration (future)
- Singularity controller dispatches to Cursor agents
- SDD pipeline phases execute as Cursor agent tasks
- Multi-agent squad coordination via COS
- Engram-bridged memory across all agents

## Competitive Moat

This integration creates a moat that neither Cursor nor COS has alone:

- **Cursor alone**: Powerful execution, but no governance, no memory, no coordination at scale
- **COS alone**: Powerful governance, but limited execution (relies on Claude Code sub-agents)
- **COS + Cursor**: Governed execution at enterprise scale with persistent memory

No other tool combination offers this today (March 2026).
