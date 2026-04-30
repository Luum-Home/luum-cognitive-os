<!--
RECONCILIATION STATUS: SUPERSEDED
Superseded by: ADR-027 (SO slimming — context overhead pillar), ADR-044 (context payload slimming — non-rule agentic primitives), ws1 EXCLUDED_RULES (14→87 rules excluded), ws2 SmartTruncator, ws3 prompt cache (78.5% input cost reduction)
Reconciled: 2026-04-21
Reason: the 8 largest waste sources enumerated (TO-1 through TO-8) all have shipped agentic primitives or ADR coverage. The target ">95% efficiency" is being measured via SLO 10/11 (startup-benchmark.sh) rather than this plan's KPIs.
-->

# Master Plan: Token Optimization — Orchestrator Efficiency

**Date**: 2026-04-10
**Status**: APPROVED
**Scope**: Reduce orchestrator and sub-agent token waste by 50%+
**Current efficiency**: ~70-80% (estimated)
**Target efficiency**: >95%
**Relationship**: Complements `self-optimizing-pipeline.md` WS1 (EXCLUDED_RULES) and WS2 (context compaction). Feeds directly into those workstreams.

---

## Problem Statement

| Waste Source | Estimated Tokens/Session | % of Budget |
|---|---|---|
| CLAUDE.md rules loaded at start | ~73,000 | ~30% |
| Full reads of large files | ~5,000–15,000 | ~5% |
| Wrong model (sonnet → haiku tasks) | $$0.04–0.20 waste | — |
| Verbose orchestrator responses | ~3,000–8,000 | ~3% |
| Task notification accumulation (13+) | ~6,500 | ~3% |
| No context usage awareness | unquantified — no early action | — |
| Bloated sub-agent prompts | ~2,000–5,000 per launch | ~5% |
| Redundant Engram searches | ~500–2,000 | ~1% |

**Total estimated recoverable**: 15,000–40,000 tokens per session (~20-30% of typical budget).

---

## Workstreams

### TO-1: CLAUDE.md Diet — 73K → <20K tokens

**Current state**: All 55 rules (~73K tokens) loaded at every session start regardless of relevance. WS1 of self-optimizing-pipeline already identified 12 EXCLUDED_RULES (hook-enforced). That's Phase 1 done.

**Target**: <20K tokens at session start. Remove hook-enforced rules from CLAUDE.md injection. Load contextual rules only on trigger.

**Implementation**:
1. Extend `hooks/self-install.sh` EXCLUDED_RULES list: add all rules where the hook is registered in `settings.local.json` and the rule has no orchestrator-specific guidance beyond what the hook enforces.
2. Move remaining orchestrator-specific content into RULES-COMPACT.md ultra-compact form (target: <1,500 tokens per self-optimizing-pipeline WS1 Phase 4).
3. Add `rules/lazy-load/` directory for contextual rules that load on trigger only.

**Files affected**: `hooks/self-install.sh`, `rules/RULES-COMPACT.md`, `.claude/settings.local.json`
**Effort**: 2 sessions
**Dependencies**: None (WS1 of self-optimizing-pipeline is prerequisite Phase 1)
**Success metric**: `wc -c rules/RULES-COMPACT.md` < 6,000 bytes. Session-start rule token count measured via `ccusage session` drops >60%.

---

### TO-2: Smart File Access Patterns

**Current state**: Orchestrator reads `active-tasks.json` (~700 lines), `dispatch-queue.json`, and other state files entirely when only a subset is needed.

**Target**: Zero full reads of files >100 lines when partial access suffices.

**Implementation**:
1. Create `lib/smart_access.py` with helpers: `get_in_progress_tasks()`, `get_queued_agents()`, `get_budget_remaining()` — each does targeted `jq` instead of full reads.
2. Add to RULES-COMPACT.md: "NEVER Read active-tasks.json, dispatch-queue.json, cost-events.jsonl, or skill-metrics.jsonl fully — use lib/smart_access helpers."
3. Register `hooks/large-file-advisor.sh` to warn on files >40KB (already exists per `rules/result-management.md` — verify it's registered).

**Files affected**: `lib/smart_access.py` (new), `rules/RULES-COMPACT.md`
**Effort**: 1 session
**Dependencies**: None
**Success metric**: `grep -c "Read.*active-tasks"` in session transcripts = 0 per session.

---

### TO-3: Model Routing Discipline

**Current state**: Routing table in `rules/model-routing.md` exists but orchestrator overrides it for sub-agents. Mechanical tasks (archiving, notification digests, formatting) use sonnet unnecessarily.

**Target**: haiku for all tasks matching: archive, format, rename, doc-generation, digest, status-summary. Save ~$0.04–0.10 per session.

**Implementation**:
1. Add explicit trigger list to RULES-COMPACT.md: "haiku MANDATORY for: sdd-archive, doc-sync, notification-digest, format, rename, skill-registry, capability-snapshot, session-changelog."
2. Add behavioral test in `tests/behavior/test_model_routing.py`: assert orchestrator selects haiku for archival tasks.
3. Update `lib/dispatch_model_advisor.py` to hard-block sonnet/opus for haiku-tier tasks.

**Files affected**: `rules/RULES-COMPACT.md`, `tests/behavior/test_model_routing.py`, `lib/dispatch_model_advisor.py`
**Effort**: 1 session
**Dependencies**: None
**Success metric**: `jq '[.[] | select(.model=="haiku")] | length' metrics/cost-events.jsonl` increases by 30%+ on archival tasks.

---

### TO-4: Orchestrator Response Compression

**Current state**: Orchestrator generates verbose inline responses: full risk tables, long explanations, markdown headers for 2-line answers.

**Target**: Response tokens per orchestrator turn reduced by 40%.

**Implementation**:
1. Add to RULES-COMPACT.md: Response budget rules — status update: <3 lines; delegation report: <5 lines; error report: <10 lines; no inline risk tables unless user asks.
2. Principle: "If it can go in a sub-agent report, it doesn't belong in the orchestrator response."
3. Reserve prose explanations for decisions; delegate findings summaries to sub-agents via structured result fields.

**Files affected**: `rules/RULES-COMPACT.md`, `templates/agent-preamble.md`
**Effort**: 0.5 sessions
**Dependencies**: None
**Success metric**: Average orchestrator response length (measured via ccusage output tokens per turn) drops 40%.

---

### TO-5: Notification Digest System

**Current state**: 13+ task notifications arrive as individual items; each processed separately adds ~500 tokens of context overhead and orchestrator re-parsing.

**Target**: Batch notifications into a single digest processed once.

**Implementation**:
1. Create `lib/notification_digest.py`: `accumulate(notification)`, `flush() -> DigestReport`, `format_digest()`. Digest groups by status (completed/failed/blocked), lists affected tasks, extracts key results.
2. Orchestrator rule: after each sprint (>3 agents launched), wait for all notifications before processing — call `flush()` once.
3. Add `DigestReport` to active-tasks.json completion record so post-session analysis can use it.

**Files affected**: `lib/notification_digest.py` (new), `rules/RULES-COMPACT.md`
**Effort**: 1 session
**Dependencies**: None
**Success metric**: Notification processing tokens per sprint drops from ~6,500 to <1,000.

---

### TO-6: Context Usage Awareness

**Current state**: Orchestrator doesn't know how much context it has consumed. No early action before compaction. `context-watchdog.sh` hook not registered per `rules/context-management.md` note.

**Target**: Orchestrator receives context usage % every 20 tool calls. Triggers mem_save at 70%.

**Implementation**:
1. Register `hooks/context-watchdog.sh` in `settings.local.json` — it already exists, just unregistered.
2. Add to orchestrator behavior: on receiving 70% warning, call `mem_save` for all in-progress decisions before continuing.
3. Integrate context % into notification digest header: "Sprint summary [context: 45%]: ..."

**Files affected**: `.claude/settings.local.json`, `hooks/context-watchdog.sh`
**Effort**: 0.5 sessions
**Dependencies**: TO-5 (digest header integration)
**Success metric**: Zero unplanned compactions where context >70% at compaction time (currently estimated at 30% of sessions).

---

### TO-7: Sub-Agent Prompt Compression

**Current state**: Sub-agent prompts = preamble (~2K) + rules context (~3K) + task + acceptance criteria. Average ~5K–8K tokens per launch. 10 agents/session = 50K–80K tokens on prompt overhead alone.

**Target**: Average sub-agent prompt <3K tokens. Save ~20K–50K tokens per session.

**Implementation**:
1. Audit `templates/agent-preamble.md` — strip all content that is hook-enforced or already in model training. Target: <800 tokens.
2. Use reference-style instead of inline: "Follow rules/RULES-COMPACT.md" instead of pasting content.
3. Acceptance criteria templates: use 3-line format instead of full markdown tables. Full format only for large/critical complexity.

**Files affected**: `templates/agent-preamble.md`, `templates/quality-gates.md`
**Effort**: 1 session
**Dependencies**: TO-1 (rules already slimmed before preamble references them)
**Success metric**: `wc -c templates/agent-preamble.md` < 4,000 bytes. Average prompt token count per agent drops 40%.

---

### TO-8: Memory-First Protocol Enforcement

**Current state**: Orchestrator searches Engram or rereads files for information already visible in the current conversation context window.

**Target**: Zero redundant searches for facts established in the same session.

**Implementation**:
1. Add pre-tool-call checklist to RULES-COMPACT.md: "Before any mem_search or Read: is this already in the current session context? If yes, skip the tool call."
2. Add session-start Engram context load: `mem_context()` once at session start, cache result, reference cache for duration of session.
3. Mark session-established facts in a lightweight mental register: "already know: {topic}" note in orchestrator working state.

**Files affected**: `rules/RULES-COMPACT.md`
**Effort**: 0.5 sessions
**Dependencies**: TO-6 (context awareness helps know what's been established)
**Success metric**: Redundant Engram searches (same query twice in same session) = 0, verified via session transcript analysis.

---

## Implementation DAG

```
TO-1 (CLAUDE.md diet)
  └─> TO-7 (prompt compression) — needs slim rules first

TO-2 (smart file access)          [independent]
TO-3 (model routing)              [independent]
TO-4 (response compression)       [independent]

TO-5 (notification digest)
  └─> TO-6 (context awareness) — digest header uses context %

TO-8 (memory-first)
  └─ depends on TO-6 (needs context awareness to know what's established)
```

**Wave 0 (P0, parallel)**: TO-2, TO-3, TO-4
**Wave 1 (P1, parallel)**: TO-1, TO-5
**Wave 2 (P1/P2)**: TO-6, TO-7 (TO-7 after TO-1)
**Wave 3 (P2)**: TO-8 (after TO-6)

---

## Priority Table

| WS | Priority | Effort | Token Savings | Risk |
|---|---|---|---|---|
| TO-1 | P0 | 2 sessions | ~50,000/session | Medium — rules may be needed |
| TO-2 | P0 | 1 session | ~10,000/session | Low |
| TO-3 | P0 | 1 session | $0.05–0.15/session | Low |
| TO-4 | P1 | 0.5 sessions | ~5,000/session | Low |
| TO-5 | P1 | 1 session | ~5,500/session | Low |
| TO-6 | P1 | 0.5 sessions | unquantified — prevents waste | Low |
| TO-7 | P1 | 1 session | ~20,000–50,000/session | Medium |
| TO-8 | P2 | 0.5 sessions | ~1,000–2,000/session | Very low |

---

## Overall Success Metrics

| Metric | Current | Target | Measurement |
|---|---|---|---|
| Session-start rule tokens | ~73,000 | <20,000 | `ccusage session` first turn input tokens |
| Average sub-agent prompt | ~6,000 tokens | <3,000 tokens | `ccusage session` per-agent breakdown |
| Wrong-model launches | ~30% of archival tasks | 0% | `cost-events.jsonl` model field audit |
| Notification overhead | ~6,500 tokens/sprint | <1,000 tokens | Session transcript analysis |
| Full reads of state files | ~5/session | 0/session | Grep session transcripts |
| Unplanned compactions | ~30% of sessions | <5% of sessions | Session end reports |
| Total session token cost | ~$0.50–1.50 | <$0.75 | `ccusage daily` |

## Definition of Done

- [ ] `wc -l .cognitive-os/plans/features/token-optimization-masterplan.md` < 300
- [ ] All 8 workstreams have measurable success metrics
- [ ] DAG is implementable (no circular dependencies)
- [ ] Overlaps with self-optimizing-pipeline WS1/WS2 are explicit (TO-1 references WS1)
