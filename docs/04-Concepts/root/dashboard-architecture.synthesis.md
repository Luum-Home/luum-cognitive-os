---
type: concept-synthesis
source: docs/04-Concepts/root/dashboard-architecture.md
status: "ADR-001: Build Custom COS Dashboard — Accepted. Updated 2026-03-29"
provenance: "Architecture decision record for a custom React (Next.js) web dashboard for managing, monitoring, and configuring COS."
---

## What it is

ADR + implementation plan for the COS-specific web dashboard: rules CRUD, hooks monitoring, agent trust scores, Engram browser, cost/security views — distinct from the pre-existing agent-coordination dashboard (port 3200).

## Key mechanics

**Tech stack** (all MIT/ISC): Next.js 15 App Router (React 19+SSR+API routes), Shadcn UI+Radix primitives, Zustand (state, ~1KB), Tailwind CSS 4, WebSocket+SSE (real-time, bridges Valkey pub/sub), xterm.js (terminal), CodeMirror 6 (YAML/MD/JSON editing), Recharts (charts), XYFlow+Dagre (graph viz for SDD pipeline/skill deps), Lucide React (icons), React Hook Form+Zod (validation), TanStack Query v5 (server state), Turborepo (optional monorepo). Rejected: Arco Design, Monaco Editor, Redux/Jotai, Tremor, standalone Vite.

**Pages** (route | source | phase): Dashboard `/` (Phase 1), Rules `/rules` (Phase 1), Skills `/skills` (Phase 1), Hooks `/hooks` (Phase 2), Agents `/agents` (Phase 2, WebSocket+trust-scores.jsonl), Memory `/memory` (Phase 2, Engram), Cost `/cost` (Phase 2), Security `/security` (Phase 3), Config `/config` (Phase 3, cognitive-os.yaml editor), SDD Pipeline `/sdd` (Phase 3, Kanban), Releases `/releases` (Phase 4), Terminal `/terminal` (Phase 4, xterm.js).

**API layer**: Browser → Next.js API routes (`/api/*`) → COS MCP server (`mcp-server/cos_mcp.py`, 8 tools: `cos_status`, `cos_get_rules`, `cos_search_memory`, `cos_save_memory`, `cos_get_tasks`, `cos_check_quality`, `cos_get_metrics`, `cos_suggest_skill`) → COS libs (`lib/*.py`) + filesystem. Additional direct file-reading routes beyond MCP: `/api/rules/list`, `/api/hooks/list`, `/api/skills/catalog`, `/api/config`, `/api/agents/bus` (WebSocket), `/api/sdd/[change]`. Bridge options: Phase 1 = Next.js routes spawn Python subprocess (~200ms overhead); Phase 2 = FastAPI sidecar wrapping `cos_mcp.py`; Phase 3 = TypeScript MCP client direct.

**Auth**: Phase 1 none (localhost/Docker network); Phase 2 basic auth/API key via `COS_DASHBOARD_API_KEY`; Phase 3 OAuth2/SSO with per-user permissions mapped to COS agent security levels.

**Real-time**: Agent monitoring via WebSocket bridge subscribing to Valkey `cos:agent:*:{heartbeat,progress,question}` channels, forwarding to Zustand; falls back to polling `.cognitive-os/agent-bus/` JSONL when Valkey unavailable. Metrics streaming via SSE tailing JSONL files.

**Dual-dashboard model**: port 3200 (already running, Docker) = agent coordination/squad org chart/SDD-as-issues/inbox/monthly spend; port 3300 (custom-built) = COS-specific rules/hooks/skills/memory/cost/security/config. No cross-dependency; each runs independently.

**Deployment**: `cos-dashboard` service in `docker-compose.cognitive-os.yml`, profile `ui`, port 3300:3000, multi-stage Dockerfile (node:22-alpine builder+runner), read-only volume mount of project root, depends on `langfuse-valkey`. Resources: dev 256MB/0.5 core, prod 512MB/1 core.

**Local toolchain (canonical, not future-tense)**: `dashboard/` uses Bun exclusively (not npm/pnpm/Yarn); `install.ignoreScripts = true` blocks preinstall/install/postinstall/prepare hooks. Validation: `bun --version && cd dashboard && bun install --frozen-lockfile --ignore-scripts && bun run build`. Known-good: bun 1.3.14 (observed 2026-05-06). `bun run lint` delegates to deprecated `next lint` and may prompt interactively — do not answer the prompt or generate ESLint config as part of an unrelated change; treat dashboard lint as unavailable until migration.

**Component extraction** (source license → COS use): Shadcn/Radix (Apache-2.0/MIT, direct use), Zustand store pattern from AutoMaker (MIT, 24+ stores adapted), xterm.js/XYFlow/Kanban from AutoMaker (MIT), CodeMirror 6 from AionUi (Apache-2.0), WebSocket pattern from OpenClaw (MIT), Chat UI from AnythingLLM (MIT). Built from scratch (no equivalent elsewhere): Trust Score Gauge, Budget Gauge, Phase Indicator, Hook Timing Chart, Engram Topic Tree, Security Profile Switcher, SDD Phase Tracker, Escalation Alert Panel.

## Relations & where used

`docs/04-Concepts/root/ui-platforms-evaluation.md`, `docs/08-References/root/competitive-analysis.md`, `mcp-server/cos_mcp.py`, `docs/07-Capabilities/root/agent-teams.md`, `packages/agent-coordination/rules/agent-communication.md`, `rules/infra-health.md`, `rules/hook-security-profiles.md`, `rules/license-policy.md`.

## Status / caveats

ADR-001 accepted. Consequence explicitly noted: COS-specific features get first-class UI, but the dashboard becomes another component to test/ship (maintenance burden). Acceptance criteria for any dashboard-touching change: `bun --version` exits 0; frozen-lockfile install with scripts disabled exits 0; `bun run build` exits 0; if lint prompts for ESLint setup, stop and report — do not mutate config implicitly.
