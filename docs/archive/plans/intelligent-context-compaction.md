<!--
RECONCILIATION STATUS: SUPERSEDED
Superseded by: ADR-044 (context payload slimming — non-rule startup components), ADR-027 (context overhead pillar), ws2 SmartTruncator (commit 9bd895b), ws3 prompt cache (commit 15d67eb)
Reconciled: 2026-04-21
Reason: the three largest pillars — smart truncation, prompt cache, and payload slimming — all have shipped components and an ADR framework. Remaining micro-optimizations fold into ADR-044 execution.
-->

# Plan: Intelligent Context Compaction

## Problem

The Cognitive OS wastes 40-60% of available context on redundant, verbose, or poorly structured content:

| Waste Source | Estimated Tokens | % of 200K Context |
|---|---|---|
| Sub-agent returns (verbose prose, no limit) | ~8-15K per agent | 4-7.5% each |
| Context lost on compaction (decisions, file paths) | ~20-40K unrecoverable | 10-20% |
| Dumb result truncation (head+tail, no structure) | ~3-5K wasted per command | 1.5-2.5% |
| Repeated system prompt across executor sub-agents | ~15-25K per agent spawn | 7.5-12.5% |

Over a moderate session (50 tool calls, 5 sub-agents), this wastes **60-100K tokens** -- half the usable context window. At Opus pricing ($15/$75 per 1M), this translates to **$135-285/month** in unnecessary spend for a moderate-usage team.

## Current State

### What Exists

| Component | File | What It Does | Gap |
|---|---|---|---|
| Result truncator | `hooks/result-truncator.sh` | Head+tail char truncation (first 2K + last 1K) | No command-type awareness; discards structured data |
| Context watchdog | `hooks/context-watchdog.sh` | Counts tool calls, warns at 50/70/85% thresholds | Advisory only; agent must act manually |
| Pre-compaction flush | `hooks/pre-compaction-flush.sh` | Reminds agent to save to Engram before compaction | Reactive (fires at compaction time, too late for deep save) |
| Agent preamble | `templates/agent-preamble.md` | Output Compression (Caveman-Lite) section | No hard token limit; no structured return format enforced |
| Context optimization rule | `rules/context-optimization.md` | 3-level progressive loading, dual-search protocol | Documents intent but does not enforce output size |
| Context management rule | `rules/context-management.md` | Behavioral thresholds at 50/70/85% | Agent-dependent; forgotten under cognitive load |
| Token economy rule | `rules/token-economy.md` | 5 principles for cost awareness | Principles only; no mechanical enforcement |
| Smart reader | `lib/smart_reader.py` | Auto-pagination for large file reads | Input optimization only; no output optimization |

### What Is Missing

1. **Sub-agent return contract** -- no enforced output size limit or structured format
2. **Anchored iterative summarization** -- no proactive context preservation across compaction
3. **Smart result extraction** -- truncation is char-based, not semantics-based
4. **Prompt cache optimization** -- no cache_control breakpoints for executor mode sub-agents

## Proposal: 4 Workstreams

### Workstream 1: Sub-Agent Return Contract

**Problem**: Sub-agents return 3-10K tokens of verbose prose. The orchestrator only needs ~500-1000 tokens: status, files changed, key findings, trust report. The rest is wasted context that accelerates compaction.

**Solution**: Formalize a structured return contract in the agent preamble with a hard 1K token target for the response body (excluding trust report).

**Structured return format**:

```
STATUS: {success|partial|failed}
FILES_CHANGED: {comma-separated list}
KEY_FINDINGS:
  - {finding 1, max 1 line}
  - {finding 2, max 1 line}
  - {finding 3, max 1 line}
DECISIONS_MADE:
  - {decision with rationale, max 1 line}
NEXT_STEPS:
  - {what remains, if anything}

TRUST_REPORT: SCORE=XX STATUS=YY EVIDENCE=N UNCERTAINTIES=N
---
[trust report body, ~300 tokens]
```

**Implementation**:

| Task | File | Change |
|---|---|---|
| Update agent preamble | `templates/agent-preamble.md` | Replace "Progress reporting" section with structured return contract; add "RESPONSE BUDGET: Your response body (excluding trust report) MUST be under 1000 tokens. Use the structured format below." |
| Update CLAUDE.md orchestrator instructions | `.claude/CLAUDE.md` | Add to Sub-Agent Context sections: "Sub-agents return structured output per agent-preamble.md. Parse STATUS/FILES_CHANGED/KEY_FINDINGS. Do NOT re-read full agent output." |
| Create return contract validator | `lib/return_contract.py` | `validate_return(output) -> ContractResult` -- checks structure presence, estimates token count, warns on violations |
| Optional: PostToolUse hook | `hooks/return-contract-validator.sh` | PostToolUse on Agent -- warns if output exceeds 2K tokens without structured markers |

**Measurement**:
- Before: measure average sub-agent return size across 10 completions (expected: 3-10K tokens)
- After: measure same metric (target: < 1.5K tokens including trust report)
- Method: `cat .cognitive-os/metrics/skill-metrics.jsonl | jq -s '[.[].output_tokens] | (add / length)'`

---

### Workstream 2: Anchored Iterative Summarization

**Problem**: Claude Code's auto-compaction discards working memory indiscriminately. After compaction, the agent loses: which files were modified, what decisions were made, what the current task goal is, and what errors were encountered. The pre-compaction-flush hook fires too late -- the agent may not have time for a deep save.

**Key insight from Factory.ai research**: Iterative merge into an anchor document scores 4.04/5.0 on quality vs 3.74 for full regeneration. The anchor accumulates; each compaction merges deltas, not regenerates from scratch.

**Solution**: Maintain a persistent "anchor summary" in Engram that is proactively updated at context thresholds (not just at compaction). On session resume or post-compaction, reload the anchor as ground truth.

**Anchor structure** (4 fields):

```python
class AnchoredSummary:
    intent: str           # What is the session trying to accomplish
    changes_made: list    # Files modified with 1-line description each
    decisions_taken: list # Architectural/design decisions with rationale
    next_steps: list      # Remaining work items
```

**Implementation**:

| Task | File | Change |
|---|---|---|
| Create anchored summary library | `lib/anchored_summary.py` | `AnchoredSummary` class with `update(new_messages)`, `merge(delta)`, `to_engram()`, `from_engram()`, `format_for_injection()` methods |
| Integrate with context-watchdog | `hooks/context-watchdog.sh` | At 70% threshold: call `python3 -c "from lib.anchored_summary import AnchoredSummary; AnchoredSummary.auto_save()"` to persist current anchor |
| Integrate with pre-compaction-flush | `hooks/pre-compaction-flush.sh` | Before the existing FLUSH_MSG: merge recent messages into anchor and save to Engram with topic_key `session/{session_id}/anchor` |
| Create session resume loader | `hooks/session-resume-anchor.sh` | SessionStart hook: search Engram for `session/*/anchor`, inject most recent anchor into agent context as "SESSION CONTEXT (from previous session/compaction)" |
| Add orchestrator behavioral rule | `rules/context-management.md` | Add section: "At 70%, update the anchored summary. At 85%, finalize it. After compaction, load it immediately." |

**Engram persistence**:
```python
mem_save(
    title=f"Session anchor: {session_id}",
    topic_key=f"session/{session_id}/anchor",
    type="pattern",
    scope="project",
    content=anchor.format_for_engram()
)
```

**Merge algorithm (iterative, not regenerative)**:
1. Load existing anchor from Engram
2. Extract new facts from recent conversation (files changed, decisions, errors)
3. Append to existing lists (dedup by file path for changes_made)
4. Update intent only if it changed (rare)
5. Replace next_steps (always reflects current state)
6. Save merged anchor back to Engram

**Measurement**:
- **Context drift rate**: Count how many times per session the agent asks "What was I working on?" or restates the goal after compaction
- Before: expected 2-4 goal restatements per session with compaction
- After: target 0 restatements (anchor provides full context)
- Method: `grep -c "what was\|remind me\|where were\|what were" session_transcript` (proxy metric)

---

### Workstream 3: Smart Result Truncation

**Problem**: `result-truncator.sh` does dumb char-based truncation: first 2000 chars + last 1000 chars. This discards the semantically important middle of test output (specific failure messages), build logs (actual error lines), and JSON responses (data structure). A 50-line test summary gets truncated the same way as a 50MB docker log.

**Solution**: Replace char-based truncation with command-type-aware structured extraction. Each command type gets a custom extractor that preserves the semantically important information and discards the noise.

**Extractors by command type**:

| Command Pattern | Extractor | What It Keeps | Target Output |
|---|---|---|---|
| `pytest`, `go test`, `jest`, `vitest` | `extract_test_summary()` | Pass/fail count, first 3 error messages, coverage % | ~500 chars |
| `go build`, `tsc`, `yarn build` | `extract_build_summary()` | Exit code, first error with file:line, error count | ~300 chars |
| `docker compose`, `docker ps` | `extract_docker_summary()` | Service name + status table, error lines only | ~400 chars |
| `jq`, JSON output | `extract_json_structure()` | Top-level keys, array lengths, first element sample | ~500 chars |
| `grep -c`, `wc -l`, counts | `passthrough()` | Already concise -- no truncation needed | as-is |
| `git diff`, `git log` | `extract_git_summary()` | File list + stat summary, first 3 diff hunks | ~800 chars |
| Default (unknown command) | `extract_head_tail()` | Current behavior: first 2K + last 1K | ~3K chars |

**Implementation**:

| Task | File | Change |
|---|---|---|
| Create smart truncator library | `lib/smart_truncator.py` | `SmartTruncator` class with `truncate(command, output) -> str` dispatcher and per-type extractors |
| Create test extractor | `lib/smart_truncator.py` | `extract_test_summary(output)`: regex for pass/fail lines, extract first N failures, capture coverage line |
| Create build extractor | `lib/smart_truncator.py` | `extract_build_summary(output)`: capture exit status, first error with file:line:col, total error count |
| Create docker extractor | `lib/smart_truncator.py` | `extract_docker_summary(output)`: parse `docker ps` table format, extract only NAME+STATUS columns + error lines |
| Create JSON extractor | `lib/smart_truncator.py` | `extract_json_structure(output)`: parse JSON, emit top-level keys with types, array lengths, first element sample |
| Create git extractor | `lib/smart_truncator.py` | `extract_git_summary(output)`: `--stat` summary, first 3 hunks with file context |
| Update result-truncator hook | `hooks/result-truncator.sh` | Before char-based truncation: call `python3 -c "from lib.smart_truncator import SmartTruncator; ..."` with command and output; use smart result if available, fall back to char-based |
| Add unit tests | `tests/unit/test_smart_truncator.py` | Test each extractor with real-world output samples |

**Measurement**:
- **Token reduction ratio**: Compare truncated output size for 20 common commands
- Before (current): ~60% reduction (5K -> 3K chars average)
- After (smart): target 80% reduction (5K -> 500-800 chars average)
- Method: Run same commands, compare `len(current_truncate(output))` vs `len(smart_truncate(command, output))`

---

### Workstream 4: Prompt Cache Optimization (Executor Mode Only)

**Problem**: When `ORCHESTRATOR_MODE=executor`, each sub-agent is spawned as a subprocess via `ClaudeExecutor`. Each subprocess receives the full system prompt (tools + rules + instructions). With 5 sub-agents, this means 5x the same ~15-25K token prefix is sent and billed at full input price.

**Key insight from Anthropic prompt caching**: Cached prefixes cost 90% less on input ($1.50 vs $15.00 per 1M for Opus). The cache has a 5-minute TTL (auto-extended on hit). The key requirement: the cached prefix must be an exact match from the start of the message.

**Prerequisite**: Only works with `ORCHESTRATOR_MODE=executor` and the `anthropic` Python SDK (direct API calls). Does NOT apply to the default Agent tool (fire-and-forget, no API control).

**Solution**: Structure the sub-agent system prompt to maximize prefix cache hits:

```
[STABLE: Tool definitions — changes only on SDK update]     <- cache_control: ephemeral (1hr TTL)
[SESSION-STABLE: System rules, RULES-COMPACT, preamble]     <- cache_control: ephemeral (5min auto-extend)
[DYNAMIC: Task-specific instructions, sidecar context]      <- no cache (changes per agent)
```

**Implementation**:

| Task | File | Change |
|---|---|---|
| Add cache_control to executor | `lib/claude_executor.py` | In `_build_messages()`: add `cache_control: {"type": "ephemeral"}` breakpoint after tool definitions block and after system rules block |
| Order system prompt for caching | `lib/claude_executor.py` | Reorder system message construction: (1) tool definitions, (2) RULES-COMPACT + agent preamble, (3) task-specific prompt + sidecar |
| Add cache metrics tracking | `lib/claude_executor.py` | After each API call: extract `usage.cache_creation_input_tokens` and `usage.cache_read_input_tokens` from response; log to `metrics/cache-events.jsonl` |
| Create cache dashboard | `lib/cache_dashboard.py` | `format_cache_report()`: cache hit rate %, input cost saved, tokens served from cache |
| Add cache config | `cognitive-os.yaml` | Under `resources.cache`: `enabled: true`, `system_prompt_ttl: 3600`, `tool_def_ttl: 300` |
| Document in model-routing | `rules/model-routing.md` | Add note: "When ORCHESTRATOR_MODE=executor, sub-agents benefit from prompt caching. Tool definitions and system rules are cached across agent spawns." |

**Cache hit scenarios**:

| Scenario | Cache Hit Expected | Savings |
|---|---|---|
| 5 sub-agents in 5 minutes | 4 out of 5 (80%) | ~60K tokens at 90% discount = ~$4.50 saved per batch |
| SDD pipeline (7 phases) | 6 out of 7 (86%) | ~90K tokens at 90% discount = ~$6.75 saved per pipeline |
| Single agent | 0% (no reuse) | No savings |

**Measurement**:
- **Cache hit rate**: `cache_read_input_tokens / (cache_read_input_tokens + cache_creation_input_tokens) * 100`
- Target: > 70% cache hit rate when running 3+ sub-agents within a session
- **Input cost reduction**: compare actual input cost vs theoretical uncached cost
- Target: 40-60% input cost reduction for executor-mode sessions with 3+ agents
- Method: `cat .cognitive-os/metrics/cache-events.jsonl | jq -s '[.[].cache_read_input_tokens] | add'`

## Implementation Strategy

### Phase 1: Sub-Agent Return Contract (1 session, ~$2)
- Model: Sonnet
- Tasks: Update agent-preamble.md, update CLAUDE.md, create lib/return_contract.py
- Validation: Run 3 sub-agents, verify output follows structured format and < 1.5K tokens
- Risk: Low -- additive change to existing template, no breaking changes

### Phase 2: Smart Result Truncation (1-2 sessions, ~$3-5)
- Model: Sonnet
- Tasks: Create lib/smart_truncator.py with 6 extractors, update result-truncator.sh, write unit tests
- Validation: Run test suite, build, docker commands -- verify smart extraction produces smaller, more useful output
- Risk: Low -- fallback to existing char-based truncation if smart extraction fails

### Phase 3: Anchored Iterative Summarization (2 sessions, ~$4-6)
- Model: Sonnet (implementation) + Opus (design review)
- Tasks: Create lib/anchored_summary.py, integrate with context-watchdog and pre-compaction-flush, create session-resume hook
- Validation: Simulate compaction by splitting a session -- verify anchor loads correctly and contains all critical context
- Risk: Medium -- Engram latency could slow down 70% threshold saves; merge algorithm must handle duplicates

### Phase 4: Prompt Cache Optimization (1-2 sessions, ~$3-5)
- Model: Sonnet
- Prerequisite: ORCHESTRATOR_MODE=executor must be functional
- Tasks: Modify ClaudeExecutor message construction, add cache_control breakpoints, add metrics
- Validation: Run 5 sub-agents, verify cache hit rate > 70% via metrics
- Risk: Medium -- requires anthropic SDK cache_control support; only benefits executor mode users

## Expected Outcome

| Metric | Before | After (all 4 workstreams) |
|---|---|---|
| Sub-agent return size (avg) | 3-10K tokens | < 1.5K tokens |
| Context lost on compaction | ~20-40K tokens unrecoverable | < 5K (anchor preserves critical state) |
| Result truncation efficiency | 60% reduction | 80% reduction |
| Prompt cache hit rate (executor) | 0% (no caching) | > 70% |
| Session context lifetime | ~50 tool calls before compaction pressure | ~80 tool calls (30-60% more runway) |
| Monthly token cost (moderate use) | ~$450/month estimated | ~$180-270/month (40-60% reduction) |
| Goal restatements after compaction | 2-4 per session | 0 (anchor restores context) |

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Sub-agents ignore return contract | Medium | Low | PostToolUse hook warns on violations; preamble is loaded every time |
| Smart truncation misparses a command type | Medium | Low | Fallback to char-based truncation; each extractor has try/except |
| Anchored summary grows unbounded | Low | Medium | Cap at 2K tokens; prune oldest entries when exceeded |
| Engram latency blocks 70% threshold save | Low | Medium | Run save in background; use file-based fallback if Engram is slow |
| Prompt cache not supported by SDK version | Low | High | Phase 4 is gated on SDK check; skip if unsupported |
| Compaction API (Anthropic beta) changes | Medium | Low | We use Engram anchors, not the compaction API; we're API-independent |
| Structured return format too rigid for some tasks | Medium | Low | Allow `EXTENDED_RESPONSE: true` flag for tasks that need verbose output |

## Behavioral Tests

### Workstream 1: Sub-Agent Return Contract
- **T1.1**: Launch a sub-agent with the updated preamble; verify output contains STATUS, FILES_CHANGED, KEY_FINDINGS, TRUST_REPORT markers
- **T1.2**: Measure output token count of 5 sub-agent completions; all must be < 2K tokens (1K body + 1K trust report)
- **T1.3**: If return-contract-validator hook is active, verify it warns on outputs > 2K tokens without structured markers

### Workstream 2: Anchored Iterative Summarization
- **T2.1**: After 70% context threshold, verify `session/{session_id}/anchor` exists in Engram with non-empty intent and changes_made fields
- **T2.2**: Simulate compaction by starting a new session in the same project; verify anchor loads and contains file paths from the previous work
- **T2.3**: Verify merge is iterative: modify 3 files, trigger anchor save, modify 2 more files, trigger second save -- final anchor should contain all 5 files without duplicates
- **T2.4**: Verify anchor size stays under 2K tokens after 20+ file modifications

### Workstream 3: Smart Result Truncation
- **T3.1**: Run `python -m pytest tests/ -v` (verbose output); verify smart truncation extracts pass/fail count and first error message in < 800 chars
- **T3.2**: Run `go build ./...` with a deliberate error; verify smart truncation extracts the error file:line:message
- **T3.3**: Run `docker compose ps`; verify smart truncation preserves the service status table
- **T3.4**: Pipe a large JSON file through `jq .`; verify smart truncation shows top-level structure, not raw data
- **T3.5**: Run an unknown command; verify fallback to char-based truncation works

### Workstream 4: Prompt Cache Optimization
- **T4.1**: Launch 3 sub-agents via executor mode within 5 minutes; verify `cache-events.jsonl` shows cache_read_input_tokens > 0 on agents 2 and 3
- **T4.2**: Verify cache hit rate > 60% across a batch of 5 agents
- **T4.3**: When executor mode is disabled, verify no cache-related errors or behavior changes

## Dependencies

| Dependency | Required By | Status |
|---|---|---|
| `templates/agent-preamble.md` | Workstream 1 | Exists -- needs update |
| `hooks/result-truncator.sh` | Workstream 3 | Exists -- needs integration point |
| `hooks/context-watchdog.sh` | Workstream 2 | Exists -- needs 70% threshold integration |
| `hooks/pre-compaction-flush.sh` | Workstream 2 | Exists -- needs anchor merge call |
| `lib/claude_executor.py` | Workstream 4 | Exists -- needs cache_control additions |
| Engram (mem_save/mem_search) | Workstream 2 | Exists and functional |
| `anthropic` Python SDK with cache support | Workstream 4 | Must verify SDK version supports cache_control |
| `ORCHESTRATOR_MODE=executor` | Workstream 4 | Exists but optional; WS4 is executor-only |

## Estimated Effort

| Phase | Sessions | Model | Est. Cost | Prerequisites |
|---|---|---|---|---|
| 1. Sub-Agent Return Contract | 1 | sonnet | ~$2 | None |
| 2. Smart Result Truncation | 1-2 | sonnet | ~$3-5 | None (independent) |
| 3. Anchored Iterative Summarization | 2 | sonnet + opus review | ~$4-6 | None (independent) |
| 4. Prompt Cache Optimization | 1-2 | sonnet | ~$3-5 | Executor mode functional |
| **Total** | **5-7 sessions** | -- | **~$12-18** | -- |

Phases 1-3 can run in parallel (no dependencies between them). Phase 4 depends on executor mode being operational.

## References

- **Anthropic prompt caching**: 90% input cost reduction on cached prefixes, 5-min TTL with auto-extend on hits
- **Factory.ai anchored iterative summarization**: Iterative merge scores 4.04/5.0 vs 3.74 for full regeneration (8% quality improvement)
- **LLMLingua-2**: Token compression via mutual information -- EVALUATE for future integration (Phase 5+)
- **Engram research observation**: #2971 -- full context compaction research with 6 techniques and projected savings
