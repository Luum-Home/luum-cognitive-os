---
adr: 78
title: Mid-Task Memory Tool (Port from Hermes)
status: accepted
implementation_status: partial
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
partial_remaining: Automated per-turn invocation (the full Hermes pattern) is a follow-up item and
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-078: Mid-Task Memory Tool (Port from Hermes)

**Status**: Accepted
**Date**: 2026-04-30
**Deciders**: Maintainer
**Related**: ADR-074 (Tier-0 learning loop), ADR-075 (Stage-2 selective expansion)

---

## Status

Accepted.

## Context

Engram topic: `hermes-learning-loop-source-map` (see Engram for full source map)

ADR-074 introduced the Tier-0 learning loop by porting Hermes's
`tools/memory_tool.py:65-102` as `lib/memory_scanner.py`. That port covered
the *write-time* security scan path — content is vetted before being saved to
Engram. However, the Hermes design includes a second primitive: the agent
invoking memory scanning **mid-task as a callable tool**, enabling in-session
reflection before acting on recalled context.

The Hermes source files in scope:

- `.claude/plugins/hermes-agent/agent/memory_manager.py` (ported: lines 83–374)
- `.claude/plugins/hermes-agent/agent/memory_provider.py` (ported: abstract class,
  used as the thin local equivalent)

The gap closed by this ADR: sub-agents and orchestrators have no programmatic
way to query Engram mid-task or check content safety in a reusable way without
re-implementing the scanner logic inline.

---

## Decision

### What was ported

**`lib/memory_manager.py`** (~420 LOC total including the local provider ABC):

- `MemoryManager` class ported verbatim from Hermes `memory_manager.py:83-374`.
  All methods preserved: `add_provider`, `prefetch_all`, `queue_prefetch_all`,
  `sync_all`, `get_all_tool_schemas`, `handle_tool_call`, `build_system_prompt`,
  `on_turn_start`, `on_session_end`, `on_pre_compress`, `on_memory_write`,
  `on_delegation`, `shutdown_all`, `initialize_all`.
- `MemoryProvider` abstract class ported from Hermes `memory_provider.py` as a
  thin local ABC (~50 LOC) in the same file, removing the cross-module import
  dependency on Hermes internals.
- Context fencing helpers `sanitize_context` and `build_memory_context_block`
  ported verbatim.
- One concrete provider: `EngramMemoryProvider` (~90 LOC), wrapping the
  structured Engram HTTP search path. Falls back to empty results when the
  daemon is absent (CI-safe).

**`skills/memory-scan/SKILL.md`** — exposes `lib.memory_scanner.MemoryScanner`
as an agent-callable skill. Agents invoke `/memory-scan <text>` or
`/memory-scan --file <path>` mid-task to vet content before persisting.

**`hooks/memory-prefetch.sh`** — registered under `UserPromptSubmit` (async) to
warm the Engram recall cache before each agent turn. Non-blocking: exits 0 silently
when Engram is unavailable.

### What was adapted

- Replaced `from agent.memory_provider import MemoryProvider` and
  `from tools.registry import tool_error` with local equivalents. No Hermes
  package imports remain in the ported code.
- `initialize_all` drops the automatic `hermes_home` injection (Hermes injects
  the profile-scoped `~/.hermes` path; Cognitive OS uses Engram paths instead).
  Method signature is preserved for API compatibility.
- `EngramMemoryProvider` uses Engram's structured HTTP search rather than
  Hermes's built-in memory file. The query/prefetch/tool-call surface is
  equivalent. The provider does **not** rely on undocumented `engram --json`
  CLI flags.

---

## Consequences

### Positive

- Sub-agents can now call `MemoryManager.prefetch_all(query)` mid-task to
  warm Engram recall without implementing query logic themselves.
- `EngramMemoryProvider` is CI-safe: no test fails when Engram is absent.
- `memory-scan` skill enables defensive scanning before any memory persist
  operation, closing the read-path security gap identified in ADR-074.
- `memory-prefetch.sh` hook warms the cache on every user prompt (async, so
  no agent launch latency is added).

### Negative / Trade-offs

- Actual mid-task invocation is **opt-in**: sub-agents must explicitly call the
  `/memory-scan` skill or instantiate `MemoryManager`. There is no automatic
  recall injection per agent turn (that would require rewriting the agent prompt
  assembly pipeline, which is out of scope for reconstruction phase).
- `EngramMemoryProvider.query()` requires the local Engram daemon for
  structured results. If the daemon is not running, results are empty
  (graceful degradation).

### Migration

The skill is opt-in. No agent is required to call it. Orchestrators that want
automatic recall should:

1. Instantiate `MemoryManager` with `EngramMemoryProvider` in their planning step.
2. Call `mm.prefetch_all(user_query)` before launching sub-agents.
3. Pass the returned context block (via `build_memory_context_block()`) in the
   sub-agent prompt.

Automated per-turn invocation (the full Hermes pattern) is a follow-up item and
does not block this ADR.

---

## Files Changed

| File | Change |
|------|--------|
| `lib/memory_manager.py` | New — MemoryManager + MemoryProvider ABC + EngramMemoryProvider |
| `skills/memory-scan/SKILL.md` | New — agent-callable memory scan skill |
| `hooks/memory-prefetch.sh` | New — async UserPromptSubmit hook |
| `scripts/apply-efficiency-profile.sh` | Registered `memory-prefetch.sh|async` under UserPromptSubmit |
| `tests/unit/test_memory_manager.py` | New — 30 unit tests, MemoryManager + context fencing |
| `tests/unit/test_engram_memory_provider.py` | New — 23 unit tests, EngramMemoryProvider + scanner smoke |
| `docs/02-Decisions/adrs/ADR-078-mid-task-memory-tool.md` | This file |
| `docs/03-PoCs/root/research-log.md` | Appended section "2026-04-30: Mid-task memory tool (Tier 1 #5)" |

---

## Alternatives rejected

- **Honcho provider**: Rejected because it requires Honcho API credentials and
  cloud infrastructure, which conflicts with COS's local-first memory model.
- **Hindsight / Mem0 providers**: Rejected because third-party SaaS providers
  expand the dependency and credential surface for a core memory path.
- **`run_agent.py` wiring**: Rejected because Hermes wires `MemoryManager` at
  agent startup in its run loop, while COS uses harness hooks and should keep
  the manager invokable on demand by skills/hooks.

## Verification

```bash
python3 -m pytest tests/unit/test_memory_manager.py tests/unit/test_engram_memory_provider.py -q --tb=short
python3 -m pytest tests/behavior/test_core_skills_check.py -q --tb=short
```

## References

- Hermes `memory_manager.py`: `.claude/plugins/hermes-agent/agent/memory_manager.py`
- Hermes `memory_provider.py`: `.claude/plugins/hermes-agent/agent/memory_provider.py`
- Hermes license: MIT (confirmed at adoption, see `.cognitive-os/adoption-registry.yaml`)
- ADR-074: `docs/02-Decisions/adrs/ADR-074-tier-0-learning-loop-closure.md`
- ADR-075: `docs/02-Decisions/adrs/ADR-075-stage2-selective-expansion.md`
- Engram topic: `hermes-learning-loop-source-map`
- Engram topic (this impl): `cos/midtask-memory-tool-impl`
