# REDIRECT: This file is superseded by ADR-078-mid-task-memory-tool.md

**Status**: Accepted
**Date**: 2026-04-30
**Deciders**: Matias Nahuel Améndola
**Related**: ADR-074 (Tier-0 learning loop), ADR-075 (Stage-2 selective expansion)

---

## Status

Accepted. Superseded by ADR-078.

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
- One concrete provider: `EngramMemoryProvider` (~90 LOC), wrapping
  `engram search --json` CLI. Falls back to empty results when the binary is
  absent (CI-safe).

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
- `EngramMemoryProvider` uses `engram search --json` rather than Hermes's
  built-in memory file. The query/prefetch/tool-call surface is equivalent.

### What was rejected (out of scope)

- **Honcho provider** — requires Honcho API credentials and cloud infrastructure.
  Not applicable to local COS development environments.
- **Hindsight / Mem0 providers** — third-party SaaS providers; excluded to keep
  the dependency surface minimal.
- **`run_agent.py` wiring** — Hermes wires `MemoryManager` at agent startup in
  its run loop. COS uses Claude Code hooks instead; the manager is instantiated
  on-demand by callers (skill or hook).

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
- `EngramMemoryProvider.query()` uses the `engram search --json` CLI flag.
  If the CLI does not support `--json`, results will be empty (graceful
  degradation). Operators using an older `engram` version should upgrade.

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
| `docs/adrs/ADR-076a-mid-task-memory-tool-redirect.md` | This file |
| `docs/research-log.md` | Appended section "2026-04-30: Mid-task memory tool (Tier 1 #5)" |

---

## Alternatives rejected

- **Delete this redirect immediately**: Rejected because existing local notes may still point at the old ADR number. Keeping a lettered redirect preserves the trail without violating unique ADR numbering.

## Verification

```bash
python3 -m pytest tests/audit/test_adr_contracts.py -q --tb=short
```

## References

- Hermes `memory_manager.py`: `.claude/plugins/hermes-agent/agent/memory_manager.py`
- Hermes `memory_provider.py`: `.claude/plugins/hermes-agent/agent/memory_provider.py`
- Hermes license: MIT (confirmed at adoption, see `.cognitive-os/adoption-registry.yaml`)
- ADR-074: `docs/adrs/ADR-074-tier-0-learning-loop-closure.md`
- ADR-075: `docs/adrs/ADR-075-stage2-selective-expansion.md`
- Engram topic: `hermes-learning-loop-source-map`
- Engram topic (this impl): `cos/midtask-memory-tool-impl`
