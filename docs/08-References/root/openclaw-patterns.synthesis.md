---
type: reference-synthesis
source: docs/08-References/root/openclaw-patterns.md
provenance: "Catalogs 7 production-resilience patterns extracted from the OpenClaw codebase (and, per later update, its Pi execution engine) and adapted into Cognitive OS."
---

## What it is

A pattern-adoption catalog documenting 7 specific patterns pulled from analyzing the OpenClaw agent framework, each with source rationale, concrete implementation file(s), and stated impact — plus a table of patterns considered but rejected, and a change log of files created/modified.

## Key mechanics

7 adopted patterns:
1. **Pre-Compaction Memory Flush** — `.claude/hooks/pre-compaction-flush.sh` (PreCompact hook); reminds the agent to save to Engram before context compaction truncates working memory, eliminating "amnesia" between sessions.
2. **SOUL.md + IDENTITY.md** — `.claude/SOUL.md`, `.claude/IDENTITY.md`; explicit behavioral/personality boundaries to avoid performative helpfulness in favor of direct, honestly-uncertain agent behavior.
3. **Progressive Disclosure for Skills** — `references/` subdirectories in `sre-agent` and `systematic-debugging` skills; SKILL.md acts as a navigation hub, detailed docs load only on demand, reducing per-invocation token cost.
4. **Tool Loop Detection** — `.claude/hooks/tool-loop-detector.sh` (PostToolUse, matcher `*`); tracks last 10 tool calls, detects `generic_repeat` (same tool+args 3+ times), `ping_pong` (A-B-A-B alternation), and `no_progress` (same Read/Grep on same file 3+ times).
5. **4-Tier Resilience Model** — `.claude/rules/fault-tolerance.md`; Tier 1 connection (reconnect/heartbeat/shutdown), Tier 2 LLM call (model fallback/rate limiting/retry budgets), Tier 3 context (pre-compaction flush/session summaries), Tier 4 agent (orphan detection/task recovery/idempotent re-launch).
6. **Cost Tracking Protocol** — `.claude/rules/cost-tracking.md`; model-selection matrix, budget alerts, optimization strategies to prevent default-to-most-expensive-model behavior.
7. **Credential Management** — `.claude/rules/credential-management.md`; consolidates credential rules previously scattered across constitutional-gates.md and services-config.md, adds validation/rotation guidance and startup checks.

Rejected patterns (with reasons): multi-agent supervisor tree (already covered by Agent Teams + SDD), custom MCP transport layer (standard MCP servers suffice), agent personality hot-swap (single-domain fintech agent favors consistency), custom prompt caching (delegated to Claude's built-in caching).

## Relations & where used

- A 2026-04-08 update note clarifies that Pi is the actual execution engine behind OpenClaw (160K+ stars), so some patterns attributed to "OpenClaw" here derive partly from Pi's core double-while-loop/7-package design; Pi-specific patterns (file mutation queue, compaction cut-points, structural tests, settings override) are catalogued separately in `docs/08-References/root/patterns-adopted.md` and referenced in `docs/08-References/root/competitive-landscape.md`.
- File-change table shows this work also produced `docs/ai-ecosystem/openclaw-patterns.md` and updated `docs/ai-ecosystem/INDEX.md` — a possibly separate/older doc location from the current `docs/08-References/root/` path of the source being synthesized here.

## Status / caveats

- No internal inconsistencies found in the pattern descriptions themselves.
- The file-change table lists file paths under `docs/ai-ecosystem/` while this source document itself now lives at `docs/08-References/root/openclaw-patterns.md` — suggests the KB has been reorganized since this doc was written; the historical file list may no longer reflect current paths. Not corrected here per source-fidelity rule.
