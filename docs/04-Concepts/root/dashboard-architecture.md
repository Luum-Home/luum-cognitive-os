# COS Web Dashboard Architecture

> Architecture decision record for the Cognitive OS web dashboard.
> A custom React application for managing, monitoring, and configuring COS.
> Updated: 2026-03-29

## ADR-001: Build Custom COS Dashboard

### Status
Accepted

### Context

### Decision

### Consequences
- COS-specific features get first-class UI support (rules CRUD, hooks monitoring, agent trust scores, Engram browser).
- Maintenance burden increases; the dashboard becomes another component to test and ship.

---

## 1. Tech Stack Decision

| Layer | Choice | Why | License |
|-------|--------|-----|---------|
| Framework | Next.js 15 (App Router) | React 19 + SSR + API routes; proven at scale; community momentum | MIT |
| UI Library | Shadcn UI + Radix primitives | Accessible, composable, copy-paste model (no runtime dependency); used in inngest/agent-kit | MIT |
| State Management | Zustand | Lightweight (~1 KB), no boilerplate; AutoMaker uses 24+ Zustand stores successfully | MIT |
| Styling | Tailwind CSS 4 | Utility-first; every evaluated platform uses it; Shadcn requires it | MIT |
| Real-time | WebSocket + SSE | Agent Bus already uses Valkey pub/sub; bridge to WebSocket for browser; SSE as fallback for simpler streams | N/A |
| Terminal | xterm.js | Browser terminal emulation from AutoMaker; hook output and agent log streaming | MIT |
| Code Editor | CodeMirror 6 | YAML/Markdown/JSON editing for rules, cognitive-os.yaml, skills; from AionUi evaluation | MIT |
| Charts | Recharts | Declarative React charting built on D3; lightweight; MIT licensed | MIT |
| Graph Visualization | XYFlow (React Flow) + Dagre | Node graph for SDD pipeline, skill/rule dependency visualization; from AutoMaker | MIT |
| Icons | Lucide React | Icon set bundled with Shadcn | ISC |
| Form Handling | React Hook Form + Zod | Validation for config editing, rule creation | MIT |
| Data Fetching | TanStack Query v5 | Server state management with caching, auto-refetch, optimistic updates | MIT |
| Monorepo | Turborepo (optional) | If dashboard lives in the COS repo; otherwise standalone | MIT |

### Rejected Alternatives

| Option | Why Rejected |
|--------|-------------|
| Arco Design (from AionUi) | Heavier than Shadcn; Ant-Design-derived; larger bundle for comparable features |
| Monaco Editor | Heavier than CodeMirror 6 for the editing needs (YAML, Markdown); Monaco pulls VS Code dependencies |
| Redux / Jotai | Zustand is simpler for the dashboard's state shape; Redux adds boilerplate without benefit at this scale |
| Tremor (charts) | Good but opinionated about Tailwind classes; Recharts gives more control |
| Vite (standalone) | Next.js provides SSR and API routes that reduce the need for a separate backend |

---

## 2. Pages and Views

| Page | Route | Features | Primary Data Source | Priority |
|------|-------|----------|---------------------|----------|
| **Dashboard** | `/` | Overview cards: rule/hook/skill/package counts, active sessions, phase, KPI sparklines, cost gauge, recent errors | `cos_status()`, `cos_get_metrics()` | Phase 1 |
| **Rules** | `/rules` | List all rules with search/filter, enable/disable toggle, inline editor (CodeMirror), create new rule, contextual trigger viewer | `cos_get_rules()` + filesystem via API route | Phase 1 |
| **Skills** | `/skills` | Catalog browser with category filter, audience tags, invoke button, skill detail with SKILL.md preview, auto-generated badge | `cos_suggest_skill()` + CATALOG.md parse | Phase 1 |
| **Hooks** | `/hooks` | Hook list from settings.json, security profile switcher (minimal/standard/paranoid), timing metrics per hook, enable/disable | `settings.json` + `performance.jsonl` | Phase 2 |
| **Agents** | `/agents` | Real-time agent cards with heartbeat indicator, trust score badge, escalation alerts, progress bar, agent dependency graph (XYFlow) | Agent Bus (WebSocket) + `trust-scores.jsonl` | Phase 2 |
| **Memory** | `/memory` | Engram observation browser with search, topic key tree, session timeline, observation detail with full content | `cos_search_memory()` + `cos_save_memory()` | Phase 2 |
| **Cost** | `/cost` | Budget gauge (daily/monthly), model routing table, spend-per-session chart, cost prediction, model downgrade status | `cos_get_metrics("cost")` + `cost-events.jsonl` | Phase 2 |
| **Security** | `/security` | Scan results (Semgrep, Aguara, Parry), vulnerability timeline, security profile status, always-blocked paths list | `security metrics JSONL files` | Phase 3 |
| **Config** | `/config` | cognitive-os.yaml editor (CodeMirror with YAML schema validation), settings.json viewer, environment variable status | Config files via API route | Phase 3 |
| **SDD Pipeline** | `/sdd` | Kanban board for SDD phases (explore through archive), per-change status, retry count, verify/apply loop visualization | Engram SDD topic keys + `active-tasks.json` | Phase 3 |
| **Releases** | `/releases` | COS version, package versions, changelog viewer, release-all trigger | `cos_status()` + git tags | Phase 4 |
| **Terminal** | `/terminal` | xterm.js embedded terminal for direct COS CLI interaction, hook output streaming | WebSocket to host shell | Phase 4 |

### View Components (Shared)

| Component | Used In | Source Pattern |
|-----------|---------|----------------|
| `MetricCard` | Dashboard, Cost, Agents | Custom (Shadcn Card + Recharts sparkline) |
| `DataTable` | Rules, Hooks, Skills, Memory | Shadcn Table + TanStack Table |
| `CodeEditor` | Rules, Config, Skills | CodeMirror 6 wrapper |
| `StatusBadge` | Dashboard, Agents, SDD | Shadcn Badge with phase-aware colors |
| `SearchBar` | Rules, Skills, Memory | Shadcn Input + Command palette |
| `GraphView` | Agents, SDD | XYFlow + Dagre layout |
| `TerminalView` | Terminal, Agents | xterm.js wrapper |
| `TrustScoreGauge` | Agents, Dashboard | Custom SVG gauge |
| `BudgetGauge` | Cost, Dashboard | Recharts radial bar |
| `TimelineView` | Memory, Security | Custom vertical timeline |

---

## 3. API Layer

The COS MCP server (`mcp-server/cos_mcp.py`) provides 8 tools that serve as the primary backend API. The dashboard communicates with the MCP server through a thin API bridge.

### Architecture

```
Browser (Next.js App)
    |
    | HTTP / WebSocket
    v
Next.js API Routes (/api/*)
    |
    | FastMCP client OR direct Python lib calls
    v
COS MCP Server (cos_mcp.py)
    |
    | Python imports
    v
COS Libraries (lib/*.py) + File System (rules/, hooks/, metrics/)
```

### MCP Tool to Dashboard Endpoint Mapping

| MCP Tool | Dashboard API Route | Dashboard Page |
|----------|--------------------|----|
| `cos_status()` | `GET /api/status` | Dashboard, Releases |
| `cos_get_rules(context)` | `GET /api/rules?context=` | Rules |
| `cos_search_memory(query)` | `GET /api/memory/search?q=` | Memory |
| `cos_save_memory(...)` | `POST /api/memory` | Memory |
| `cos_get_tasks(status)` | `GET /api/tasks?status=` | Dashboard, SDD Pipeline |
| `cos_check_quality(code)` | `POST /api/quality/check` | Rules (live validation) |
| `cos_get_metrics(type)` | `GET /api/metrics?type=` | Cost, Dashboard, Security |
| `cos_suggest_skill(message)` | `GET /api/skills/suggest?q=` | Skills |

### Additional API Routes (Beyond MCP Tools)

These routes read COS files directly, extending the MCP server's coverage:

| Route | Method | Purpose | Source |
|-------|--------|---------|--------|
| `/api/rules/list` | GET | List all rule files with metadata | `rules/*.md` + `packages/*/rules/*.md` |
| `/api/rules/[name]` | GET/PUT | Read or update a single rule file | File system |
| `/api/hooks/list` | GET | List registered hooks with timing data | `settings.json` + `performance.jsonl` |
| `/api/hooks/profile` | GET/PUT | Get or set security profile | `scripts/set-security-profile.sh` |
| `/api/skills/catalog` | GET | Parse CATALOG.md into structured JSON | `CATALOG.md` |
| `/api/skills/[name]` | GET | Read SKILL.md content | `skills/*/SKILL.md` |
| `/api/config` | GET/PUT | Read or update cognitive-os.yaml | `cognitive-os.yaml` |
| `/api/config/settings` | GET | Read settings.json (redacted secrets) | `.claude/settings.json` |
| `/api/agents/bus` | WebSocket | Real-time agent heartbeats and progress | Valkey pub/sub bridge |
| `/api/agents/teams` | GET | Active Agent Teams status | `~/.claude/teams/` |
| `/api/security/scans` | GET | Aggregated security scan results | `metrics/*-findings.jsonl` |
| `/api/sdd/[change]` | GET | SDD pipeline state for a change | Engram `planning/{change}/*` |

### API Bridge Implementation Options

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Next.js API routes calling Python subprocess** | Simple; no extra server | Process spawn overhead per request (~200ms) | Phase 1 (MVP) |
| **FastAPI sidecar wrapping cos_mcp.py** | Native Python; fast; proper HTTP server | Extra service to maintain | Phase 2 (production) |
| **MCP client in TypeScript** | Direct MCP protocol; future-proof | MCP client ecosystem still maturing | Phase 3 (when MCP HTTP stabilizes) |

**Phase 1 approach**: Next.js API routes spawn a Python helper script that imports COS libraries directly. This avoids running a separate FastAPI server while keeping the MCP tools as the canonical API.

**Phase 2 migration**: Extract the Python bridge into a FastAPI service (`cos-api`) that wraps all MCP tools as REST endpoints plus the additional file-based routes. The Next.js app becomes a pure frontend calling the FastAPI backend.

### Authentication

Phase 1 (local development): No authentication. Dashboard runs on localhost behind Docker network.

Phase 2 (team access): Basic auth or API key via environment variable. The `COS_DASHBOARD_API_KEY` is validated in API route middleware.

Phase 3 (production): OAuth2 / SSO integration if COS is deployed for team use. Per-user permissions map to COS agent security levels.

---

## 4. Real-Time Architecture

### Agent Monitoring (WebSocket)

```
Valkey (Agent Bus)                    Browser
    |                                    ^
    | pub/sub: cos:agent:*:heartbeat     |
    | pub/sub: cos:agent:*:progress      | WebSocket
    | pub/sub: cos:agent:*:question      |
    v                                    |
WebSocket Bridge (Python/Node)  --->  Next.js App
    |                                    |
    | Subscribes to Valkey channels       | Updates Zustand store
    | Forwards as WebSocket frames        | Re-renders agent cards
```

The WebSocket bridge is a lightweight process that subscribes to Valkey `cos:agent:*` channels and forwards events to connected browser clients. When Valkey is unavailable, the bridge falls back to polling `.cognitive-os/agent-bus/` JSONL files (matching the Agent Bus graceful degradation pattern).

### Metrics Streaming (SSE)

For non-critical real-time updates (new metric entries, stale doc notifications), Server-Sent Events provide a simpler alternative to WebSocket:

```
GET /api/metrics/stream?types=cost,errors,trust
Content-Type: text/event-stream

data: {"type":"cost","entry":{...}}
data: {"type":"error","entry":{...}}
```

The SSE endpoint tails JSONL metric files and emits new entries as they appear.

---

## 5. Dual-Dashboard Architecture

COS uses **two complementary dashboards**, not one monolithic UI:

```
                      Browser
                     /       \
            (port 3200)        (port 3300)
                |                    |
            Agent coord         COS-specific
            Squad org chart     Rules, hooks, skills
            SDD issues          Memory, cost, security
            Inbox/notifs        Trust scores, KPIs
            Monthly spend       Config editor
```

### Why Two Dashboards?

|-----------|---------------|
| Agent coordination (heartbeats, status) | Rules/hooks/skills management |
| Org chart of squads | Engram memory browser |
| Issue tracking (SDD phases as issues) | Cost dashboard + budget gauges |
| Inbox/notifications | Security scan results |
| Monthly spend view | Trust score gauges |
| Already running (Docker, port 3200) | Custom-built (port 3300) |



### Integration Between Dashboards

- **COS MCP server** (`mcp-server/cos_mcp.py`): COS Dashboard reads rules, metrics, tasks, memory via 8 MCP tools
- **Shared data**: both read from the same metrics files (`.cognitive-os/metrics/`), Engram, and `active-tasks.json`
- **No cross-dependency**: each dashboard runs independently. If one is down, the other continues.

### When to Use Which

| Task | Go to |
|------|-------|
| Edit/create rules | COS Dashboard |
| Browse skills catalog | COS Dashboard |
| Search Engram memory | COS Dashboard |
| Check cost/budget | COS Dashboard |
| View security scan results | COS Dashboard |
| Configure cognitive-os.yaml | COS Dashboard |

## 6. Deployment

### Docker Compose Addition

```yaml
# In docker-compose.cognitive-os.yml
cos-dashboard:
  build:
    context: ./dashboard
    dockerfile: Dockerfile
  ports:
    - "3300:3000"
  environment:
    - COS_PROJECT_ROOT=/app/cos
    - COS_MCP_URL=http://cos-mcp:8000
    - VALKEY_URL=redis://langfuse-valkey:6379
    - NODE_ENV=production
  volumes:
    - .:/app/cos:ro                    # Read-only access to COS project
    - ./dashboard:/app/dashboard       # Dashboard source (for dev hot-reload)
  depends_on:
    - langfuse-valkey                  # For agent bus WebSocket bridge
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
    interval: 30s
    timeout: 5s
    retries: 3
  profiles:
    - ui                               # Only starts with --profile ui
```

### Dockerfile

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
```

### Infrastructure Integration

| Service | Role | Required |
|---------|------|----------|
| `langfuse-valkey` | Agent Bus WebSocket bridge (real-time) | Optional (degrades to polling) |
| `cos-mcp` | Backend API (if running as separate service) | Phase 2+ |
| `litellm` | Model routing info for cost dashboard | Optional |
| `langfuse-web` | Link to traces from agent detail view | Optional |

### Resource Requirements

| Resource | Development | Production |
|----------|-------------|------------|
| Memory | 256 MB | 512 MB |
| CPU | 0.5 cores | 1 core |
| Disk | 100 MB (build artifacts) | 50 MB (standalone) |
| Network | localhost only | Docker network |

---

## 6. Phase Plan

### Phase 1: MVP (Weeks 1-3)

**Goal**: Functional dashboard with read-only views for the three most-requested features.

| Deliverable | Description |
|-------------|-------------|
| Dashboard overview | Status cards, phase indicator, component counts, recent errors |
| Rules browser | List all rules, search, read content, contextual trigger viewer |
| Skills catalog | Parse CATALOG.md, category filter, skill detail view |
| API bridge | Next.js API routes calling Python COS libs via subprocess |
| Docker service | `cos-dashboard` service in docker-compose with `ui` profile |

**Definition of Done**: Dashboard loads in browser, displays accurate rule/skill counts matching `cos_status()`, rules are browsable and searchable.

### Phase 2: Monitoring and Memory (Weeks 4-6)

**Goal**: Real-time agent monitoring and Engram memory browser.

| Deliverable | Description |
|-------------|-------------|
| Agent monitoring | Real-time cards with heartbeat, trust score, progress bars |
| WebSocket bridge | Valkey-to-WebSocket bridge for Agent Bus events |
| Memory browser | Engram search, topic key tree, observation detail |
| Cost dashboard | Budget gauge, spend-per-session chart, model routing table |
| Hooks viewer | Hook list, timing metrics, security profile display |

**Definition of Done**: Agent heartbeats display within 2 seconds of emission. Engram search returns results matching CLI `mem_search`. Cost gauge reflects actual `cost-events.jsonl` data.

### Phase 3: Configuration and Security (Weeks 7-9)

**Goal**: Writable configuration and security visibility.

| Deliverable | Description |
|-------------|-------------|
| Config editor | CodeMirror YAML editor for cognitive-os.yaml with schema validation |
| Security dashboard | Aggregated scan results, vulnerability timeline, profile status |
| SDD pipeline view | Kanban board for SDD changes, phase progression, retry visualization |
| FastAPI backend | Extract Python bridge into standalone FastAPI service |

**Definition of Done**: Config edits persist to disk correctly. Security findings from all scanners display in unified view. SDD Kanban reflects Engram pipeline state.

### Phase 4: Advanced Features (Weeks 10-12)

**Goal**: Full interactive experience.

| Deliverable | Description |
|-------------|-------------|
| Terminal integration | xterm.js for COS CLI interaction |
| Releases view | Version management, changelog, release trigger |
| Agent Teams view | Team topology, teammate status, shared task list |
| Notification system | Browser notifications for escalations, budget alerts, security findings |
| Authentication | API key auth for team access |

**Definition of Done**: Terminal executes COS commands. Notifications fire on agent escalation events. Auth blocks unauthorized access.

---

## 7. Component Extraction Plan

Components extracted from MIT/Apache-2.0 evaluated platforms, adapted for COS.

| Component | Source Platform | Source License | What We Take | COS Adaptation |
|-----------|---------------|----------------|--------------|----------------|
| Shadcn UI primitives | inngest/agent-kit | Apache-2.0 | Button, Card, Table, Dialog, Input, Badge, Command | Direct use; Shadcn is copy-paste, no runtime dep |
| Radix UI accessibility | AutoMaker | MIT | Dropdown, Popover, Tooltip, Tabs, Accordion | Direct use via Shadcn wrappers |
| Zustand store pattern | AutoMaker | MIT | Store architecture pattern (24+ stores) | Adapt for COS state: agents, rules, metrics, config |
| xterm.js terminal | AutoMaker | MIT | Terminal component with fit addon | Wrap for hook output streaming, agent logs |
| XYFlow graph | AutoMaker | MIT | Node graph rendering with Dagre layout | Adapt for SDD pipeline view, agent dependency graph |
| Kanban board pattern | AutoMaker | MIT | Drag-and-drop column layout | Adapt for SDD phases (explore through archive) |
| CodeMirror 6 editor | AionUi | Apache-2.0 | YAML, Markdown, JSON language support | Wrap for cognitive-os.yaml editing, rule editing |
| WebSocket event pattern | OpenClaw | MIT | Bidirectional streaming architecture | Adapt for Agent Bus browser bridge |
| Chat UI pattern | AnythingLLM | MIT | Message list, input, streaming display | Adapt for agent interaction log viewer |

### What We Build From Scratch

These components are COS-specific with no equivalent in evaluated platforms:

| Component | Why Custom |
|-----------|-----------|
| Trust Score Gauge | COS-specific scoring (0-100 with 4 components) |
| Budget Gauge | COS-specific budget model (daily/monthly caps, model downgrade chain) |
| Phase Indicator | COS 4-phase system (reconstruction/stabilization/production/maintenance) |
| Hook Timing Chart | COS performance metrics (p50/p95/p99 per hook) |
| Engram Topic Tree | COS Engram organization (prefixed topic keys as tree) |
| Security Profile Switcher | COS 3-profile system (minimal/standard/paranoid) |
| SDD Phase Tracker | COS SDD pipeline with retry loops and verify-apply cycles |
| Escalation Alert Panel | COS agent escalation protocol (suggest/recommend/urgent) |

---

## 8. State Management

### Zustand Store Structure

```
stores/
  useStatusStore.ts       -- COS status (phase, counts, health)
  useRulesStore.ts        -- Rules list, selected rule, editor state
  useSkillsStore.ts       -- Skills catalog, categories, selected skill
  useHooksStore.ts        -- Hooks list, timing data, profile
  useAgentsStore.ts       -- Agent cards, heartbeats, trust scores
  useMemoryStore.ts       -- Engram search results, selected observation
  useCostStore.ts         -- Budget data, spend history, model routing
  useSecurityStore.ts     -- Scan results, vulnerability counts
  useConfigStore.ts       -- cognitive-os.yaml parsed, editor state
  useSDDStore.ts          -- SDD changes, pipeline state, kanban columns
  useWebSocketStore.ts    -- Connection status, event buffer
```

Each store follows the pattern from AutoMaker: thin slices with selectors, no global store. TanStack Query handles server state (fetching, caching, invalidation); Zustand handles client state (UI selections, editor state, WebSocket connection).

---

## 9. Testing Strategy

| Layer | Tool | What We Test |
|-------|------|-------------|
| Unit | Vitest | Store logic, utility functions, data transformers |
| Component | Vitest + Testing Library | Individual component rendering, interactions |
| Integration | Playwright | Page flows (navigate to rules, search, select) |
| API | Vitest | API route handlers with mocked COS libs |
| E2E | Playwright | Full user journeys (dashboard load, rule edit, agent view) |
| Visual regression | Playwright screenshots | Layout stability across changes |

### Behavior tests (COS convention)

`tests/behavior/test_dashboard_architecture.py` validates the architecture document structure. See the test file for details.


---

## 9.1 Local Toolchain and Validation

The dashboard lives under `dashboard/` and uses the repository's local Node
toolchain through `fnm`. Do not assume `node` or `npm` are available in a fresh
non-interactive shell until `fnm` has initialized the environment.

Use this validation sequence from the repository root:

```bash
eval "$(fnm env --shell zsh)"
node --version
npm --version
cd dashboard
npm run build
```

Current known-good local versions observed on 2026-05-06:

```text
node v22.14.0
npm 10.9.2
```

`npm run build` is the current reliable dashboard validation command. It runs
Next.js production compilation and type checking and should pass before landing
dashboard changes.

`npm run lint` currently delegates to deprecated `next lint`. In this repository
it may open an interactive ESLint setup prompt when no ESLint config is present.
Do not answer that prompt or generate ESLint config as part of an unrelated
change. Treat dashboard lint as unavailable until the project deliberately
migrates to the ESLint CLI or commits an explicit config.

Acceptance criteria for dashboard-touching changes:

```text
ACCEPTANCE CRITERIA:
1. `eval "$(fnm env --shell zsh)"` exposes node and npm.
2. `cd dashboard && npm run build` exits 0.
3. If `npm run lint` prompts for ESLint setup, stop and report that lint is not configured; do not mutate config implicitly.
```
---

## 10. Security Considerations

| Concern | Mitigation |
|---------|-----------|
| Dashboard reads COS files | Read-only Docker volume mount; write operations go through API validation |
| Config editing writes to disk | Validation layer (Zod schema) before write; git diff shown before confirm |
| WebSocket unauthenticated | Phase 1: localhost only; Phase 2+: API key in WebSocket handshake |
| Credential exposure | API routes redact `.env` values, API keys, tokens before sending to browser |
| CSRF on write endpoints | Next.js CSRF protection + same-origin policy |
| XSS in code display | CodeMirror handles sanitization; no `dangerouslySetInnerHTML` |

---

## 11. Performance Targets

| Metric | Target | How |
|--------|--------|-----|
| Initial page load | < 2s | Next.js SSR + code splitting |
| Navigation between pages | < 200ms | Client-side routing + prefetch |
| Agent heartbeat latency | < 2s from emission | WebSocket bridge, no polling |
| Search results (rules, memory) | < 500ms | TanStack Query cache + server-side filtering |
| Config editor save | < 1s | Direct file write via API route |
| Dashboard data refresh | 30s auto-refresh | TanStack Query `refetchInterval` |

---

## Cross-Reference

- UI platforms evaluation: `docs/ui-platforms-evaluation.md`
- Competitive analysis: `docs/competitive-analysis.md`
- COS MCP server (backend API): `mcp-server/cos_mcp.py`
- Agent monitoring needs: `docs/agent-teams.md`
- Agent Bus protocol: `packages/agent-coordination/rules/agent-communication.md`
- Infrastructure services: `rules/infra-health.md`
- Hook security profiles: `rules/hook-security-profiles.md`
- License policy: `rules/license-policy.md`
