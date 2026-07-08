---
type: concept-synthesis
source: docs/04-Concepts/root/ui-platforms-evaluation.md
provenance: "COS needs a dashboard/management UI and evaluated 8 platforms for reusable components rather than building everything from scratch."
---

## What it is
Evaluation of 8 UI platforms for COS dashboard components, sorted by license compatibility and COS fit (HIGH/MEDIUM/LOW), separating adoptable code (MIT/Apache-2.0) from clean-room-only pattern study (AGPL/Custom).

## Key mechanics
- Summary matrix: AnythingLLM (57K★ MIT, MEDIUM fit, EVALUATE), AutoMaker (3K★ MIT, HIGH fit, EVALUATE), Aperant (13.6K★ AGPL-3.0, BLOCKED code / patterns-only clean-room), inngest/agent-kit (815★ Apache-2.0, MEDIUM, EVALUATE), AionUi (20.4K★ Apache-2.0, MEDIUM, EVALUATE), Agent Zero (16.5K★ Custom license, LOW, WATCH), OpenClaw (340K★ MIT, LOW, WATCH).
- License rule (per `rules/license-policy.md`): MIT/Apache-2.0 = code + patterns adoptable; AGPL-3.0 = code BLOCKED, patterns only via clean-room; Custom = blocked, per-case review.
- Reusable components by source: AutoMaker (MIT) -> Radix UI, xterm.js (hook/log viewer), XYFlow (SDD pipeline/agent graph viz), Zustand (24+ stores, dashboard state), Kanban board (SDD phase tracking); inngest/agent-kit (Apache-2.0) -> `@inngest/use-agent` hooks (real-time agent monitoring), Shadcn UI (50+ components), WebSocket event system; AionUi (Apache-2.0) -> Arco Design, CodeMirror + Monaco (`cognitive-os.yaml` editor), document preview (10+ formats), task scheduling UI; AnythingLLM (MIT) -> chat interface, document processing pipeline, vector DB UI, multi-user management; OpenClaw (MIT) -> WebSocket gateway, Live Canvas workspace.
- Clean-room patterns (no code copied): Aperant (AGPL) -> 3-tier memory injection (passive/reactive/active), 17 behavioral signals, worker threads, scratchpad-to-promotion pipeline; Agent Zero (Custom) -> plugin marketplace UI, self-updater dashboard, create-plugin-from-conversation flow.
- COS Dashboard needs table (all "Not started"): rules CRUD (HIGH, custom), hooks monitoring (HIGH, AutoMaker), skills browser (HIGH, Agent Zero pattern), cost dashboard (HIGH, custom + Langfuse), memory browser/Engram (MEDIUM, custom), security dashboard (MEDIUM, custom), SDD pipeline view (MEDIUM, AutoMaker Kanban), config editor (LOW, AionUi Monaco).
- OpenClaw already contributed the 4-tier fault tolerance model adopted in `rules/fault-tolerance.md`.

## Relations & where used
Cross-references: `docs/04-Concepts/root/component-sources.md`, `docs/08-References/root/competitive-analysis.md`, `docs/04-Concepts/root/ecosystem-comparison.md`, `rules/license-policy.md`, `rules/infra-health.md`.

## Status / caveats
Updated 2026-03-29. All items in the dashboard-needs table are "Not started". Recommendation: medium-term component extraction, then long-term custom React dashboard combining AutoMaker + inngest patterns.
