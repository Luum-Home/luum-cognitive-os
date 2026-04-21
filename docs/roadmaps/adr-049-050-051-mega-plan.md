# Mega-Plan: ADR-049 Correction + ADR-050/051/052/053 Roadmap

> **Persisted 2026-04-21 to ensure continuity across session interrupts.**
> Next-session protocol: read this file + `mem_search mega-plan/adr-049-050-051-routing` before resuming.

## Context

ADR-049 originally designed "Claude primary + Qwen fallback reactive" — wrong direction for our actual use case. Corrected architecture:

- **Main chat (user↔Claude Code)**: Claude Max preserved — native Claude Code cannot be redirected.
- **Sub-agents via `scripts/orchestrator.py`**: Qwen PRIMARY — preserve Claude Max quota for main chat.
- **Fallback direction inverted**: if Qwen fails, fall back to Claude (not the reverse).

## Goals

1. Sub-agent dispatches stop consuming Claude Max quota by default.
2. Infrastructure forward-compatible with multi-provider auto-routing, benchmarking, ensemble.
3. Eventually (future): "lo nuestro" replaces native `Agent()` tool for complex multi-step work.

## Checkpoints

Each Cn is a **commit-able, interruption-safe unit**. If we stop at any Cn, repo is coherent and smoke test passes. Next session resumes at Cn+1.

### C1 — `scripts/orchestrator.py` Option B rewrite

**Scope**: `--providers qwen,claude` (plural, comma-list, priority cascade).

Changes:
- Rename CLI flag `--provider` → `--providers`
- Accept comma-separated list (default: `"qwen,claude"`)
- Iterate in priority order; first success wins
- Env vars (unchanged from correction):
  - `COS_FORCE_CLAUDE_PRIMARY=1` — session-wide revert to Claude-first
  - `COS_DISABLE_QWEN=1` — skip Qwen in the list
  - `COS_DISABLE_LLM_FALLBACK=1` — no fallback at all, surface errors raw
- Update `tests/unit/test_orchestrator_fallback.py`

**Commit**: `feat(adr-049): --providers cascade rewrite (Option B)`

**Smoke**: `bash scripts/smoke-qwen-fallback.sh` should still pass 4/4.

**Files**: `scripts/orchestrator.py`, `tests/unit/test_orchestrator_fallback.py`

---

### C2 — `lib/dispatch.py` metrics foundation

**Scope**: abstract dispatcher + structured JSONL logging.

- New module `lib/dispatch.py`:
  ```python
  def dispatch(
      prompt: str,
      providers: list[str],
      task_type: str = "general",
      skill_name: str | None = None,
  ) -> DispatchResult
  ```
- Rich metric record per dispatch:
  ```json
  {
    "ts": "...",
    "providers_tried": ["qwen"],
    "provider_used": "qwen",
    "model": "qwen3.6-plus",
    "task_type": "code",
    "skill_name": null,
    "tokens_in": 234, "tokens_out": 1890,
    "cost_usd": 0.0045,
    "latency_ms": 2340,
    "success": true,
    "error": ""
  }
  ```
- Stored at `.cognitive-os/metrics/llm-dispatch.jsonl`
- Orchestrator switches to using `dispatch()` instead of direct provider calls
- 10+ unit tests: cascade iteration, metrics logging, providers=[] handles, error propagation, skill_name capture

**Why**: Foundation for ADR-053 auto-optimizer. Auto-optimizer reads this JSONL to learn which provider is best per (skill, task_type) tuple. Without metrics today, we're flying blind.

**Commit**: `feat(dispatch): abstract router + metrics foundation`

**Files**: `lib/dispatch.py`, `tests/unit/test_dispatch.py`, `scripts/orchestrator.py`

---

### C3 — `rules/llm-dispatch.md` + gotcha + ref-key

**Scope**: Normative rule + cross-references.

- `rules/llm-dispatch.md` — behavioral rule (deletes/replaces any `rules/llm-fallback.md` if exists)
- `templates/project-gotchas.md` — entry "sub-agents via orchestrator go to Qwen by default"
- `rules/RULES-COMPACT.md` — ref-key `[llm-dispatch]` in Cost Governance section

**Commit**: `docs(rules): llm-dispatch normative rule + gotcha + ref-key`

**Files**: `rules/llm-dispatch.md`, `templates/project-gotchas.md`, `rules/RULES-COMPACT.md`

---

### C4 — `skills/llm-status` user-invocable

**Scope**: `/llm-status` skill.

- SKILL.md with frontmatter (`name`, `description`, `summary_line`)
- Reads `.cognitive-os/metrics/llm-dispatch.jsonl` (from C2)
- Reports:
  - Providers configured (env vars set + SDK importable)
  - Kill-switches state
  - Last dispatch result
  - Totals per provider (30-day window): calls, success rate, total tokens, total cost, p95 latency
- Offers copy-paste commands: disable Qwen, switch to Claude primary, smoke test

**Commit**: `feat(skills): /llm-status user-invocable provider inspector`

**Files**: `skills/llm-status/SKILL.md`, possibly a helper `scripts/llm-status.py`

---

### C5 — `docs/runbooks/llm-dispatch.md`

**Scope**: User-facing operational guide.

- How-to activate (subscribe, set env, smoke test)
- How-to test (smoke, unit, live burst)
- How-to disable (soft/explicit/global kill-switches)
- How-to debug (where metrics live, how to read)
- **Dual-IDE workaround** for primary chat rate-limit (Cline/Cursor with Qwen key)
- Troubleshooting: "key 401", "SDK not installed", "provider returns empty"

**Commit**: `docs(runbook): llm-dispatch operational guide`

**Files**: `docs/runbooks/llm-dispatch.md`

---

### C6 — ADR-049 update + ADR-050/051/052/053 stubs

**Scope**: Update canonical ADR + reserve future slots.

- Update ADR-049:
  - "Architecture correction" section (inverted from Claude-primary to Qwen-primary)
  - New `--providers` flag documented
  - "Future Extensibility" section explicit about C6 ADRs
- Create stubs:
  - `docs/adrs/ADR-050-per-skill-routing.md` — policy engine consuming skill `routing:` frontmatter
  - `docs/adrs/ADR-051-qwen-agent-loop.md` — tool-use parity (Phase 1 MVP delivered by parallel agent)
  - `docs/adrs/ADR-052-provider-benchmark-harness.md` — ensemble, A/B, quality comparison
  - `docs/adrs/ADR-053-dispatch-auto-optimizer.md` — consumes metrics JSONL to re-tune routing

**Commit**: `docs(adrs): update ADR-049 + ADR-050/051/052/053 future-work stubs`

---

### C7 — ADR-051 Phase 1 (parallel agent delivery)

**Scope**: Qwen agent loop MVP (Read/Edit/Bash tools only).

Delivered by opus agent `a12fd30538d960ddc` launched 2026-04-21 18:xx:
- `lib/qwen_agent_loop.py` — agent loop with tool calling
- `tests/unit/test_qwen_agent_loop.py` — 9 tests, mocked
- `docs/adrs/ADR-051-qwen-agent-loop.md` — full ADR (not stub)

**Commit** (when agent returns): `feat(adr-051): Qwen agent loop MVP (tool-use phase 1)`

---

### C8 — DEFERRED (next session)

ADR-051 Phase 2/3/4 — approximately 3 sessions:
- **Phase 2**: Port remaining tools (Grep, WebFetch, Glob, Edit-by-regex)
- **Phase 3**: Hooks/rules/skills pre-prompt injection
- **Phase 4**: Parity test harness (same task via native Agent + our orchestrator, compare quality metrics)

These are not interruption-safe as a unit — each should be its own follow-up PR.

## Interruption protocol

If session ends mid-checkpoint:

1. **`git status`** — confirm last committed Cn
2. **`mem_search mega-plan/adr-049-050-051-routing`** — read this plan
3. **`bash scripts/smoke-qwen-fallback.sh`** — verify last Cn still works
4. **Resume at Cn+1**

**Dirty working tree at interrupt**: stash or discard, next session starts clean. Each Cn is atomic.

## Smoke verification matrix

| After Cn | What must still pass |
|---|---|
| C1 | `smoke-qwen-fallback.sh` 4/4 (orchestrator still routes correctly) |
| C2 | C1 suite + `test_dispatch.py` new tests |
| C3 | No code changes; docs render |
| C4 | `/llm-status` command runs, emits structured output |
| C5 | docs render |
| C6 | all ADRs parse, cross-references valid |
| C7 | `test_qwen_agent_loop.py` 9/9 pass (via agent) |

## Total estimate

- This session (landing Cn 1-7): ~3-4h
- Deferred C8 (full parity): ~3 sessions after
- Grand total: 4-5 sessions from start to Agent()-native replacement
