---
type: concept-synthesis
source: docs/04-Concepts/architecture/context-rot-token-budget-controls.md
provenance: "Long coding-agent sessions accumulate prompt history and tool output causing context rot and unbounded token tax; this doc maps current COS controls and gaps."
---

## What it is
Current map of how Cognitive OS prevents context rot (quality degradation from filling context windows) and unbounded token growth across long sessions.

## Key mechanics
- Operator checklist: measure budget (`scripts/cos-context-budget-report --json`), measure startup hook surface (`scripts/cos-session-start-budget --profile core/current --json`), keep AGENTS.md compact, prefer progressive context loading, save durable state early, convert HTML/PDF to text before ingestion, treat failed retries as contamination.
- Risk-to-control table: silent token growth -> `lib/context_budget.py`, `hooks/context-budget-meter.sh`, ADR-186; large startup preamble -> `scripts/cos-session-start-budget`, `scripts/cos_preamble_budget.py`; default-loaded rules/skills -> `rules/context-optimization.md`, `skills/CATALOG-MICRO.md`/`CATALOG-COMPACT.md`, `lib/context_diet.py`; irrelevant context injection -> `hooks/query-tailored-context-inject.sh`, ADR-040; pre-compaction data loss -> `hooks/pre-compaction-flush.sh`, `lib/anchored_summarizer.py`; re-discovery -> `hooks/memory-prefetch.sh`, Engram; failed-retry pollution -> escalation/rollback rules; HTML ingestion -> `lib/web_crawler.py`; sub-agent bloat -> compact result contracts doc.
- Budget layers (ADR-186/ADR-038): static 4,000 tokens (preamble/static context), turn 8,000 (per tool-use round), user 12,000 (accumulated user task content), cache 32,000 (MCP/Engram/retrieval). Token estimate = len(text)/4 unless real tokenizer enabled.
- 2026-05-22 snapshot: AGENTS.md 199 lines; SessionStart hooks 20 (maintainer), 4 (core, budget 5), 6 (team, budget 8); runtime config context ~2.2K tokens vs ~18K for full cognitive-os.yaml; skill Level-1 catalog ~3.6K tokens; 385 budget entries/30d, 100% PASS, 0 WARN/BLOCK; subagent-context-injector average ratio 0.5982.
- Context-management thresholds (`rules/context-management.md`): 50% efficiency mode, 70% save+summarize, 85% stop+handoff, 95% emergency flush via `hooks/pre-compaction-flush.sh`.
- No literal `/rewind`; nearest control is escalation/rollback doctrine.
- PDF ingestion via `scripts/cos-document-ingest` / `lib/document_ingest.py`; `hooks/document-ingest-guard.sh` blocks direct Read of `.pdf`.

## Relations & where used
ADR-016 (context diet), ADR-040 (query-tailored injection), ADR-044 (payload slimming), ADR-047 (session lifecycle), ADR-078 (mid-task memory tool), ADR-186 (budget enforcement). Related docs: context-budget-observability.md, memory-lifecycle.md, session-start-runtime-diet.md, token-efficient-agent-messaging.md, minimal-context-principle.md. Rules: context-management.md, context-optimization.md, token-economy.md.

## Status / caveats
Known gaps: context-budget-meter p99 needs post-change recalibration (old samples include project-import cost); early 15% checkpoint needs ongoing tuning; PDF OCR for scanned docs not yet covered; no literal rewind equivalent; Codex Agent lifecycle partial (context-diet/subagent budgeting are safe no-op/partial projections).
