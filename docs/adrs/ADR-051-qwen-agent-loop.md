# ADR-051 — Qwen Agent Loop (Tool-Use Parity with Claude Code Agent)

- **Status**: Proposed
- **Date**: 2026-04-21
- **Owners**: Orchestration / LLM dispatch
- **Depends on**: [ADR-049](./ADR-049-llm-gateway-selection-and-overflow-providers.md) (Qwen selection), `lib/qwen_provider.py`
- **Supersedes**: —

## Context

ADR-049 landed direct-SDK dispatch to Alibaba Qwen via `lib/qwen_provider.py`
as the primary overflow provider when Claude Max quota is saturated. That
module implements a **single-turn** chat completion: one `messages` array in,
one text response out. No tool use, no file edits, no iteration.

Claude Code's native `Agent()` tool does much more. It can:
- Read files (with offset/limit for large files)
- Edit files (exact-match or regex replace)
- Run Bash commands (with permission gating)
- Grep / Glob across the repo
- Fetch URLs
- Iterate autonomously until a task is done (multi-turn, tool-driven)

Without parity, every time the orchestrator delegates to a sub-agent, it either
(a) consumes Claude Max quota, or (b) must hand-roll the iteration with multiple
`qwen_provider.call()` round-trips from the orchestrator's own context — which
is worse than useless, because it burns the orchestrator's window for work a
sub-agent should do in isolation.

The cost of not having this: we cannot dispatch meaningful coding tasks to
Qwen at all. The "overflow" provider becomes a chat endpoint, not an agent
runtime.

## Decision

Build a **Qwen agent loop** (`lib/qwen_agent_loop.py`) that mirrors the core
iteration pattern of Claude Code's Agent, using the OpenAI function-calling
protocol (which Qwen's OpenAI-compatible endpoint supports natively).

The loop is structured in four phases so Phase 1 can land without blocking
on richer features:

### Phase 1 — MVP (THIS COMMIT)

- `run_agent(task, tools_allowed, max_iterations, token_budget, model, ...)` public API
- Tool set: `read_file`, `edit_file` (exact-match replace), `run_bash` (with blocklist + timeout)
- Hard caps: 20 iterations default, 100,000 accumulated tokens default
- Safety: `run_bash` rejects `rm -rf`, `sudo`, `kill`, `git push`, `curl` via substring match
- `edit_file` requires target to exist (no silent file creation)
- `tools_allowed` subset filter fed back to the model as a tool-result error (not a Python exception)
- Tests: 13 unit tests, all mocked (no real API), pytest passes

### Phase 2 — Tool-set expansion (follow-up)

- Port `Grep` (ripgrep-backed content search)
- Port `Glob` (fast path pattern matching)
- Port `WebFetch` (URL fetch + HTML-to-markdown extraction)
- Each tool gets the same safety envelope (timeout, result-as-string errors)

### Phase 3 — Context injection (follow-up)

- Inject relevant `hooks/`, `rules/`, and `skills/` into the system prompt so
  Qwen-dispatched sub-agents follow the same governance as Claude sub-agents
- Reuse `templates/agent-mandatory-rules.md` and `agent-preamble.md`
- Honor `subagent-context-injector.sh` equivalent at the loop entry point

### Phase 4 — Parity test harness (follow-up)

- Run the same task through both the Claude Agent tool and the Qwen loop
- Compare: final output diff, files modified, tool-calls made, token cost
- Establish quality-vs-cost tradeoff data to drive the `--providers` routing
  decision in `scripts/orchestrator.py` (worked in parallel — out of scope here)

### Rationale

**Why not use LiteLLM or another gateway?** ADR-049 already rejected gateways
in favor of direct SDK for latency, debuggability, and ToS clarity. Agent-loop
iteration amplifies these reasons — every extra hop multiplies the tail latency.

**Why OpenAI function-calling format and not Anthropic's?** Qwen's endpoint
speaks OpenAI tool-calling natively. Emulating Anthropic-style on top of OpenAI
would add a translation layer for no benefit.

**Why substring blocklist instead of a proper sandbox?** Sandboxing is the
caller's responsibility (run the orchestrator in a container). The blocklist
catches the most common foot-guns cheaply. A richer policy can be added in
Phase 4 if data shows it's needed.

**Why hard-coded caps instead of config?** `cognitive-os.yaml` is already
heavy. Per-call overrides cover the 95% case; the 5% can be addressed later
with a dedicated config block if needed.

### Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Wait for Claude Code to support OpenAI-compatible sub-agents | No ETA; we need overflow capacity now |
| Reuse `scripts/orchestrator.py` for multi-turn Qwen | Orchestrator is for user-facing sessions, not sub-agent dispatch |
| Build a full sandbox (e2b, firecracker) up-front | Overkill for Phase 1; blocks delivery on infra work |
| Port Claude Code's exact tool contracts 1:1 | Some (e.g. TodoWrite, Skill) don't translate to function-calling |

## Consequences

### What improves

- Sub-agents can now do real coding work on Qwen: read -> edit -> test -> verify loops
- Claude Max quota is preserved for orchestration and critical reasoning
- `scripts/orchestrator.py --providers qwen` becomes a viable end-to-end path
  (parallel work in `lib/dispatch.py` routes to this loop)
- Cost transparency: `AgentLoopResult` returns token counts + estimated USD
  per call, feeding `rules/token-economy.md` reporting

### What breaks / risks

- **Tool-call schema drift**: if Qwen changes its function-calling behavior,
  our schemas may stop working. Mitigation: Phase 4 parity tests run in CI.
- **Silent tool failures**: returning errors as strings (rather than raising)
  means a confused model could loop on the same failing tool. Mitigation:
  `max_iterations` cap + `token_budget` cap both backstop runaway loops.
- **Blocklist gaps**: `BASH_BLOCKLIST` is a substring filter, not a parser.
  `` `rm -rf` `` (backticks) or `r""m -rf` (creative escaping) would pass.
  Accepted trade-off for Phase 1 — the model is not adversarial, and the
  orchestrator is expected to run under OS-level isolation.
- **Token-budget accounting off-by-one**: the budget check happens AFTER the
  API response (we only know usage after the call). One over-budget round-trip
  is possible. Accepted — the cap is a safety net, not an exact meter.

### What requires a follow-up

- `lib/dispatch.py` (parallel work, not in this commit) needs to import
  `run_agent` and wire it into the `--providers` flag.
- `rules/llm-dispatch.md` (parallel work) should document when sub-agents
  are routed to the Qwen loop vs. Claude.
- Phase 2/3/4 work tracked as separate ADRs or as amendments here.

## Verification plan

### Automated

- 13 unit tests in `tests/unit/test_qwen_agent_loop.py`, all mocked:
  1. `test_simple_task_no_tools` — pass-through text response
  2. `test_read_file_tool` — tool round-trip, result fed back to model
  3. `test_edit_file_tool_happy_path` — file is actually modified on disk
  4. `test_edit_file_nonexistent_file_reports_error` — error fed to model, loop continues
  5. `test_run_bash_tool_happy_path` — exit code + stdout captured
  6. `test_run_bash_blocklist_rejects_rm_rf` — blocklist fires, model informed
  7. `test_max_iterations_cap` — loop stops at N, reports "max_iterations"
  8. `test_token_budget_cap` — budget exceeded aborts with stop_reason="budget"
  9. `test_tools_allowed_filter_rejects_disallowed` — filter error fed to model
  10. `test_tools_allowed_rejects_unknown_name_upfront` — upfront validation
  11. `test_tool_call_execution_error_captured` — malformed JSON args handled
  12. `test_tool_impl_raises_surfaces_as_error` — impl-level errors as strings
  13. `test_full_api_schema_valid` — schemas are valid JSON, names match dispatch
- Run: `uv run python -m pytest tests/unit/test_qwen_agent_loop.py -v`
- Acceptance: **13 passed, 0 failed**

### Manual E2E (Phase 1 exit criterion, not required for merge)

Requires `ALIBABA_QWEN_API_KEY` in env:

```bash
uv run python -c "
from lib.qwen_agent_loop import run_agent
r = run_agent(
  'Read /tmp/hello.txt and tell me what word appears most often.',
  tools_allowed=['read_file'],
  max_iterations=5,
)
print(r.success, r.text, r.tool_calls_made, r.cost_usd)
"
```

Success: the agent reads the file, analyzes it, returns a final answer, and
`r.tool_calls_made >= 1`.

## References

- [ADR-049](./ADR-049-llm-gateway-selection-and-overflow-providers.md) — Qwen selection + direct-SDK rationale
- `lib/qwen_provider.py` — single-turn dispatcher (underlying client)
- OpenAI function-calling docs — tool schema format
- `templates/agent-preamble.md` — context injection target for Phase 3
