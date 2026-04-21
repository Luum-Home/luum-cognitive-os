# LLM Dispatch Policy (ADR-049 Option B)

## Purpose

Define provider-selection semantics for sub-agent dispatches that go
through `scripts/orchestrator.py` or `lib/dispatch.py`. The goal is to
**preserve Claude Max subscription quota for the primary user↔Claude Code
chat** by routing sub-agents through cheaper providers by default.

## Scope

**Covered** (this rule applies):
- `scripts/orchestrator.py` invocations (CLI from terminal)
- `lib/dispatch.py::dispatch()` programmatic calls from skills, hooks,
  scripts, and future auto-routers
- `lib/qwen_agent_loop.py::run_agent()` tool-use sub-agents (ADR-051)

**NOT covered** (Claude Code native limitation — no workaround today):
- The primary user↔Claude Code chat session
- Sub-agents launched via Claude Code's built-in `Agent()` tool (they
  share the same Claude Max subscription quota — we cannot intercept)

For the primary-chat rate-limit scenario, the operational workaround is
**dual-IDE** (Cline/Cursor/Qwen Code configured with a Qwen key). See
`docs/runbooks/llm-dispatch.md`.

## When to use which dispatch path

| Task shape | Use | Why |
|---|---|---|
| Single-turn completion (summary, classify, Q&A, text generation) | `scripts/orchestrator.py --providers qwen,claude` | Cheap, no quota burn, Qwen handles it |
| Multi-step tool use (Read→Edit→Bash→Test iterating) | Native `Agent()` tool (Claude Code) | Full OS infrastructure (hooks, skills, rules, trust reports). Consumes Claude Max quota. |
| Multi-step tool use BUT primary chat is rate-limited | `lib/qwen_agent_loop.run_agent()` (ADR-051 Phase 1) | Tool-use loop over Qwen. Limited tool set (Read/Edit/Bash only today). No skills/rules injection until ADR-051 Phase 3. |
| Analysis/research under time pressure | Start with Qwen, escalate to Claude manually if quality insufficient | Qwen is 30-50× cheaper and often sufficient |
| Security-critical, frontier reasoning, architectural decisions | `--providers claude` (explicit opt-in) | Do not risk quality trade-off on high-stakes work |

## Cascade policy (how `--providers` behaves)

### Default list: `qwen,claude`

1. **Qwen primary** (first in list): `lib/qwen_provider.call()` direct-SDK
2. **Claude fallback** (second): `ClaudeExecutor.run()` native Anthropic

### Advance rules

- **Qwen failure (any cause)** → advance to Claude fallback unconditionally
  (unless `COS_DISABLE_LLM_FALLBACK=1`)
- **Claude failure**:
  - Rate-limit signal detected → advance to next provider (Qwen if present)
  - Any other error (network, auth, content) → stop cascade, surface error
  - Rationale: Claude's failures for non-quota reasons won't be fixed by a
    cheaper fallback

### First success wins

As soon as any provider returns `success=True`, the cascade stops. Next
invocation starts fresh (retry-primary semantic — no sticky mode).

## Kill-switches (layered, soft-to-hard)

### Soft — remove API key

```bash
# In .env — comment out or delete
# ALIBABA_QWEN_API_KEY=sk-...
```

Effect: `qwen_provider.is_configured()` returns False, cascade treats
Qwen as unavailable and advances to the next provider.

### Explicit per-provider

```bash
export COS_DISABLE_QWEN=1
```

Effect: Qwen is skipped in the cascade even if its API key is set.
Pattern for future providers: `COS_DISABLE_DEEPSEEK=1`, `COS_DISABLE_MINIMAX=1`.

### Cascade-scoped global

```bash
export COS_DISABLE_LLM_FALLBACK=1
```

Effect: primary call fires normally, but **cascade does NOT advance** to
the 2nd+ provider. Use to surface raw errors (debugging) or to enforce
a single-provider policy without editing `--providers`.

Only literal `"1"` disables. Empty string, `"0"`, `"false"` do NOT.

### Explicit Claude-primary override

```bash
export COS_FORCE_CLAUDE_PRIMARY=1
```

Effect: rewrites the `providers` list to `["claude"]` for the session,
bypassing the default `qwen,claude`. Use when debugging primary Claude
path without fallback interference, or when quality requires Claude for
all sub-tasks in a session.

## Skill model-hint propagation

Skills declare `model: opus|sonnet|haiku` in frontmatter. When dispatched
via Qwen, the hint maps to Qwen bundle equivalents via
`lib/qwen_provider.map_claude_model_to_qwen()`:

| Skill frontmatter | Qwen model used |
|---|---|
| `model: opus` | `qwen3.6-plus` (1M context, SWE-bench 64.8) |
| `model: sonnet` | `qwen3-coder-plus` (code-specialist) |
| `model: haiku` | `minimax-m2.5` (cheapest, simple tasks) |
| unspecified / unknown | `qwen3.6-plus` (safe default) |

Hard requirements (`need_long_context`, `need_vision`) override the hint
— only `qwen3.6-plus` has 1M context in the bundle.

## Metrics & observability (automatic)

Every dispatch writes one JSONL record to
`.cognitive-os/metrics/llm-dispatch.jsonl`:

```json
{
  "ts": "...", "dispatch_id": "...",
  "providers_requested": [...], "providers_tried": [...],
  "provider_used": "...", "model": "...",
  "task_type": "...", "skill_name": "...",
  "tokens_in": N, "tokens_out": N,
  "cost_usd": F, "latency_ms": N,
  "success": bool, "error": "..."
}
```

This feed is the input for:
- ADR-053 auto-optimizer (future)
- `/llm-status` skill reports
- `cos-config-audit` freshness checks

## Verification (non-aspirational)

- **101 unit tests** across `tests/unit/test_dispatch.py`,
  `test_orchestrator_fallback.py`, `test_qwen_provider.py`,
  `test_rate_limit_detector.py`, `test_qwen_agent_loop.py`
- **`scripts/smoke-qwen-fallback.sh`** — 4-check LIVE verification
  (validator IMPL, real API round-trip, helper, kill-switch)
- **`meta.llm_providers_reachable`** validator contract in
  `cos-config-audit.sh` — IMPL when API key + SDK configured

Run anytime: `bash scripts/smoke-qwen-fallback.sh`.

## ToS reminder (Qwen Coding Plan Pro specifically)

Qwen Pro subscription is **interactive coding tools only**. Prohibited:
cron jobs, application backends, scheduled batch pipelines, webhook
handlers. Dispatches via this cascade happen DURING an interactive
Claude Code session in response to user prompts — permitted.

For batch/automated LLM work, add MiniMax pay-per-use as a cascade
member (`$0.30/$1.20 per 1M tokens`, no ToS restriction). Not wired
today — add when needed.

## Anti-patterns

- ❌ Calling `lib/qwen_provider.call()` from cron/webhook/backend (ToS violation)
- ❌ Using `--providers claude` without specific frontier-quality requirement (burns quota)
- ❌ Disabling both kill-switches in production (no safety net)
- ❌ Writing skills that assume a specific provider — use `--providers` argument
- ❌ Hardcoding API keys in committed files (use `.env` — see `env.example`)

## Related

- ADR-049 — provider selection + architecture decision
- ADR-051 — Qwen agent loop (tool-use parity, Phase 1 shipped)
- ADR-050 — per-skill routing (reserved, future)
- ADR-052 — benchmark harness (reserved, future)
- ADR-053 — auto-optimizer (reserved, future)
- `lib/dispatch.py` — implementation
- `lib/qwen_provider.py` — Qwen direct-SDK
- `lib/qwen_agent_loop.py` — Qwen tool-use loop
- `scripts/orchestrator.py` — CLI entry point
- `scripts/smoke-qwen-fallback.sh` — live verification
- `hooks/rate-limit-detector.sh` — PostToolUse pattern detector
- `docs/runbooks/llm-dispatch.md` — user-facing how-to

## Contextual Trigger

Always active. Applies to every non-native-Agent sub-agent dispatch.
