# UI Platforms Evaluation for Cognitive OS

> Comprehensive evaluation of 8 platforms for COS dashboard/management UI.
> Updated: 2026-03-29

## Summary Matrix

| Platform | Stars | License | Type | UI Tech | COS Fit | Recommendation |
|----------|-------|---------|------|---------|---------|---------------|
| AnythingLLM | 57K | MIT | LLM platform | React+Vite | MEDIUM | EVALUATE (optional backend) |
| AutoMaker | 3K | MIT | Dev automation | React 19+Vite 7 | HIGH | EVALUATE (React components) |
| Aperant | 13.6K | AGPL-3.0 | Agent framework | React+Electron | BLOCKED | Patterns only (clean-room) |
| inngest/agent-kit | 815 | Apache-2.0 | Orchestration | React hooks | MEDIUM | EVALUATE (real-time hooks) |
| AionUi | 20.4K | Apache-2.0 | Desktop cowork | React+Electron | MEDIUM | EVALUATE (MCP patterns) |
| Agent Zero | 16.5K | Custom | General agent | Web UI | LOW | WATCH (plugin marketplace) |
| OpenClaw | 340K | MIT | Personal assistant | React | LOW | WATCH (WebSocket gateway) |

## License Compatibility

| License | Can adopt code? | Can adopt patterns? | Platforms |
|---------|----------------|--------------------|-----------|
| MIT | YES | YES | AnythingLLM, AutoMaker, OpenClaw |
| Apache-2.0 | YES | YES | inngest/agent-kit, AionUi |
| AGPL-3.0 | BLOCKED | YES (clean-room) | Aperant |
| Custom | BLOCKED | CAREFUL | Agent Zero |

Per `rules/license-policy.md`, AGPL-3.0 is a BLOCKER for code adoption in SaaS contexts. Custom licenses (Agent Zero) require per-case review. MIT and Apache-2.0 are fully approved for adoption.

## Reusable Components (MIT/Apache only)

### From AutoMaker (MIT)

| Component | Purpose | COS Use Case |
|-----------|---------|--------------|
| Radix UI component library | Accessible, unstyled primitives | Base component layer for dashboard |
| xterm.js terminal emulation | Browser-based terminal | Hook output viewer, agent log streaming |
| XYFlow graph visualization | Node-based flow diagrams | SDD pipeline visualization, agent dependency graph |
| Zustand state management (24+ stores) | Lightweight React state | Dashboard state (agents, rules, metrics) |
| Kanban board UI | Task tracking columns | SDD phase tracking, active-tasks visualization |

### From inngest/agent-kit (Apache-2.0)

| Component | Purpose | COS Use Case |
|-----------|---------|--------------|
| @inngest/use-agent React hooks | Streaming, threads, branching | Real-time agent monitoring, heartbeat display |
| Shadcn UI components (50+) | Pre-styled Tailwind components | Dashboard forms, tables, dialogs |
| Real-time WebSocket event system | Live event streaming | Agent bus visualization, progress tracking |

### From AionUi (Apache-2.0)

| Component | Purpose | COS Use Case |
|-----------|---------|--------------|
| Arco Design components | Enterprise-grade UI kit | Alternative component library |
| CodeMirror + Monaco editors | Code/config editing | cognitive-os.yaml editor, rule editing |
| Document preview (10+ formats) | File viewing | Skill/rule preview, spec viewing |
| Task scheduling UI | Calendar-based task view | Scheduled task management, workload visualization |

### From AnythingLLM (MIT)

| Component | Purpose | COS Use Case |
|-----------|---------|--------------|
| Chat interface | Conversational UI | Agent interaction log viewer |
| Document processing pipeline | File ingestion | Knowledge base building |
| Vector DB UI | Vector search management | Engram observation browser |
| Multi-user management | User/role CRUD | Session management dashboard |

### From OpenClaw (MIT)

| Component | Purpose | COS Use Case |
|-----------|---------|--------------|
| WebSocket gateway for real-time | Bi-directional streaming | Agent bus frontend integration |
| Live Canvas workspace | Collaborative editing | Multi-session coordination view |

## Patterns to Adopt (from AGPL/blocked sources)

These patterns are studied and reimplemented independently (clean-room). No code is copied from AGPL-licensed sources.

### From Aperant (AGPL -- clean-room only)

| Pattern | Description | COS Application |
|---------|-------------|-----------------|
| 3-tier memory injection | passive, reactive, active memory layers | Engram query optimization for dashboard |
| 17 behavioral signals for learning | Structured agent observation metrics | Agent KPI signal enrichment |
| Worker threads for non-blocking execution | Background processing architecture | Dashboard background data refresh |
| Scratchpad-to-promotion memory pipeline | Draft observations promoted to permanent | Engram observation lifecycle UI |

### From Agent Zero (Custom -- patterns only)

| Pattern | Description | COS Application |
|---------|-------------|-----------------|
| Plugin marketplace UI | Browse, install, rate plugins | cos package browser web frontend |
| Self-updater dashboard | Visual update management | COS version management UI |
| Create-plugin-from-conversation flow | Generate plugins from chat context | Skill creation wizard |

## What COS Dashboard Needs

| Feature | Priority | Best Source | Status |
|---------|----------|-------------|--------|
| Rules management (CRUD) | HIGH | Custom (no platform covers this) | Not started |
| Hooks monitoring | HIGH | AutoMaker (terminal + events) | Not started |
| Skills browser | HIGH | Agent Zero (plugin marketplace pattern) | Not started |
| Cost dashboard | HIGH | Custom + Langfuse integration | Not started |
| Memory browser (Engram) | MEDIUM | Custom | Not started |
| Security dashboard | MEDIUM | Custom | Not started |
| SDD pipeline view | MEDIUM | AutoMaker (Kanban) | Not started |
| Config editor | LOW | AionUi (Monaco editor) | Not started |

## Platform Deep Dives




### AutoMaker (EVALUATE -- HIGH fit)

React 19 + Vite 7 stack with modern tooling. The component library (Radix UI, xterm.js, XYFlow, Zustand) aligns well with COS dashboard requirements. The Kanban board pattern maps directly to SDD phase tracking.

**Verdict**: Extract reusable components for COS dashboard. The terminal emulation and graph visualization components are particularly valuable.

### inngest/agent-kit (EVALUATE -- real-time)

The `@inngest/use-agent` React hooks provide streaming agent state management that maps directly to COS agent bus monitoring. Shadcn UI components are widely adopted and well-tested.

**Verdict**: Evaluate the real-time hooks for agent monitoring. Shadcn UI as the base component library.

### AionUi (EVALUATE -- MCP patterns)

Desktop-first (Electron) with strong editor integration (CodeMirror + Monaco). The MCP integration patterns are relevant for COS dashboard-to-backend communication.

**Verdict**: Evaluate editor components for config/rule editing. The Electron architecture is not directly applicable (COS targets web), but the editor components work in any React app.

### AnythingLLM (EVALUATE -- optional)

Full-featured LLM platform with chat, document processing, and vector DB management. Heavier than needed for a COS dashboard, but individual components (chat UI, document viewer) could be extracted.

**Verdict**: Optional backend for knowledge management features. Individual components useful as reference implementations.

### Aperant (BLOCKED -- patterns only)

AGPL-3.0 license blocks code adoption per `rules/license-policy.md`. The memory architecture patterns (3-tier injection, behavioral signals) are valuable for COS design but must be reimplemented from scratch.

**Verdict**: Study architectural patterns. Clean-room reimplementation only. No code adoption.

### Agent Zero (WATCH)

Custom license with restrictions. The plugin marketplace UI and self-updater dashboard are the most relevant patterns. Already documented in `docs/04-Concepts/root/component-sources.md` and `docs/04-Concepts/root/ecosystem-comparison.md`.

**Verdict**: Watch for marketplace patterns. Do not adopt code.

### OpenClaw (WATCH)

Contributed the 4-tier fault tolerance model already adopted in `rules/fault-tolerance.md`. The WebSocket gateway pattern is relevant for real-time dashboard features.

**Verdict**: Watch for real-time communication patterns. Already adopted key architecture.

## Recommended Approach



### Medium-term: Extract reusable React components

Build a component library from MIT/Apache sources:

| Component | Source | License | Purpose |
|-----------|--------|---------|---------|
| Shadcn UI base | inngest/agent-kit examples | Apache-2.0 | Form controls, tables, dialogs |
| Terminal emulation | xterm.js (AutoMaker) | MIT | Hook output, agent logs |
| Real-time hooks | @inngest/use-agent | Apache-2.0 | Agent bus monitoring |
| Graph visualization | XYFlow (AutoMaker) | MIT | SDD pipeline, agent graph |
| Kanban board | AutoMaker pattern | MIT | Task tracking |
| Config editor | Monaco (AionUi pattern) | Apache-2.0 | cognitive-os.yaml editing |

### Long-term: Custom COS Dashboard

Build a unified React web app combining:

- AutoMaker's Kanban + terminal UI patterns for task and log management
- inngest's real-time streaming for live agent monitoring
- Custom components for COS-specific features (rules CRUD, hooks monitoring, skills browser, KPIs, Engram memory browser, cost dashboard, security dashboard)


## Cross-Reference

- For external tool integrations: see `docs/04-Concepts/root/component-sources.md`
- For competitive positioning: see `docs/08-References/root/competitive-analysis.md`
- For feature-by-feature comparison: see `docs/04-Concepts/root/ecosystem-comparison.md`
- For license policy: see `rules/license-policy.md`
- For infrastructure services: see `rules/infra-health.md`
