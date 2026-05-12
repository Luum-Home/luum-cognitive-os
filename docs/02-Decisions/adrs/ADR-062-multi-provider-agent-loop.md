---
adr: 62
title: Multi-Provider Agent Loop
status: proposed
implementation_status: planned
date: '2026-04-24'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit proposed status without accepted status
---

# ADR-062 — Multi-Provider Agent Loop

## Status

**Proposed** — 2026-04-24. Extends ADR-049 (provider cascade) and ADR-051
(Qwen agent loop) to any OpenAI-compatible provider.

## Context

`lib/qwen_agent_loop.py` is misnamed. It's not Qwen-specific — it uses the
OpenAI SDK against Alibaba's OpenAI-compatible endpoint. The same code
runs against any provider that speaks the OpenAI protocol, which in
2026 includes OpenAI itself, Gemini (since 2024 OpenAI-compat layer),
OpenRouter, DeepSeek, Groq, Ollama, LMStudio, and vLLM.

Today's dispatch is limited to `qwen,claude`. When Claude Max quota runs
out AND Qwen fails, we have no third-tier fallback. This is the gap
that made the 2026-04-23 18:30 incident painful (operator left without
a working dispatch path mid-session).

Operator requested (2026-04-24): tier 1 Qwen, tier 2 OpenRouter, tier 3
Gemini, tier 4 Ollama local, opt-in OpenAI/ChatGPT 5.5/5.4 and
DeepSeek. No cloud as default-supported; OpenAI/ChatGPT keys opt-in
because paid.

ADR-060 principle (local-first) still applies: defaults pick local/free
where possible. OpenAI/ChatGPT are explicitly opt-in via env keys, not
active without.

## Decision

### Generalize the agent loop

Rename and refactor:
- `lib/qwen_agent_loop.py` → `lib/openai_compatible_agent_loop.py`.
- Keep `qwen_agent_loop.py` as a thin shim that imports from the new
  module and pre-fills `provider="qwen"` for backward compatibility.
- Loop logic is provider-agnostic; only `base_url`, `api_key`, model
  choice, and pricing vary per provider.

### Provider wrappers

New `lib/providers/` directory, one file per provider:

- `lib/providers/qwen.py` — Alibaba Qwen (existing qwen_provider moved here)
- `lib/providers/openai.py` — OpenAI native (ChatGPT-5.x, Codex)
- `lib/providers/openrouter.py` — aggregator, 100+ models, free tier
- `lib/providers/gemini.py` — Google Gemini via OpenAI-compat endpoint
- `lib/providers/deepseek.py` — DeepSeek reasoning
- `lib/providers/ollama.py` — Local LLM via Ollama (default port 11434)

Each wrapper exposes:
- `is_configured() -> bool`
- `get_client()` — returns an OpenAI-compatible client
- `MODEL_MAP: Dict[str, str]` — opus/sonnet/haiku → provider-native
- `call(prompt, model_hint, ...)` — normalized response dict

### Extended dispatch cascade

`lib/dispatch.py` accepts comma-separated provider list:

```bash
# Default (operator preference 2026-04-24):
uv run python3 scripts/orchestrator.py run \
    --task "..." \
    --providers qwen,openrouter,gemini,ollama,claude

# Opt-in OpenAI tier:
export OPENAI_API_KEY=sk-...
uv run python3 scripts/orchestrator.py run \
    --task "..." \
    --providers qwen,openai,openrouter,gemini,ollama,claude
```

Advance rules (per provider):
- **qwen**: advance on any failure (overflow provider, no quota guarantee)
- **openrouter**: advance on any failure or rate-limit
- **gemini**: advance on any failure (free tier has rate limits)
- **openai**: advance only on rate-limit (paid tier expensive — failure often real)
- **deepseek**: advance on any failure
- **ollama**: advance on timeout (local can be slow/unavailable)
- **claude**: advance only on rate-limit (same rationale as openai)

### Default cascade (per operator 2026-04-24)

```
Tier 1: qwen          (paid $50/mo, Alibaba Coding Pro, generous quota)
Tier 2: openrouter    (free + paid, 100+ models, aggregator)
Tier 3: gemini        (free tier generous)
Tier 4: ollama local  (zero cost, quality varies by hardware/model)
Final:  claude        (last resort, preserves Claude Max for primary chat)
```

Opt-in additions via env:
- `OPENAI_API_KEY` → `openai` tier (ChatGPT-5.x/Codex) — caller adds to `--providers`
- `DEEPSEEK_API_KEY` → `deepseek` tier

### Config surface

`cognitive-os.yaml` gets a new `llm_providers` block:

```yaml
llm_providers:
  qwen:
    enabled: true
    model_map: {opus: qwen3.6-plus, sonnet: qwen3-coder-plus, haiku: qwen3-coder-plus}
  openrouter:
    enabled: true
    default_model: "openrouter/auto"
    model_map: {opus: "anthropic/claude-3-opus", sonnet: "meta-llama/llama-3-70b", haiku: "openrouter/auto"}
  gemini:
    enabled: true
    base_url: "https://generativelanguage.googleapis.com/v1beta/openai/"
    model_map: {opus: gemini-2.0-pro, sonnet: gemini-2.0-flash, haiku: gemini-2.0-flash-lite}
  ollama:
    enabled: false  # opt-in, requires local daemon
    base_url: "http://localhost:11434/v1"
    model_map: {opus: llama3.3:70b, sonnet: qwen3:32b, haiku: llama3.2:3b}
  openai:
    enabled: false  # opt-in, paid
    model_map: {opus: gpt-5.5, sonnet: gpt-5.4, haiku: gpt-5.4-mini}
  deepseek:
    enabled: false  # opt-in, paid
    model_map: {opus: deepseek-reasoner, sonnet: deepseek-chat, haiku: deepseek-chat}
```

### Model name conventions

All skill frontmatter keeps `model: opus|sonnet|haiku` as the abstract
tier. Per-provider map in `cognitive-os.yaml` resolves to the
provider's actual model name.

Existing `CLAUDE_TO_QWEN_MAP` is replaced by this config-driven map
(preserved as shim in `lib/providers/qwen.py`).

### Env file

`env.example` adds (all commented-out, opt-in):

```bash
# === Multi-provider agent loop (ADR-062) ===
# OpenRouter (100+ models, free + paid tiers)
# OPENROUTER_API_KEY=sk-or-...
# Gemini (free tier)
# GEMINI_API_KEY=...
# Ollama (local, no API key, requires daemon at http://localhost:11434)
# (no env needed; set enabled: true in cognitive-os.yaml)
# OpenAI (opt-in, paid)
# OPENAI_API_KEY=sk-...
# DeepSeek (opt-in, paid, SOTA reasoning)
# DEEPSEEK_API_KEY=sk-...
```

## Implementation phases

### Phase 1 — Refactor loop + 3 providers (~1.5h sonnet)

- Rename qwen_agent_loop → openai_compatible_agent_loop
- Shim qwen_agent_loop for backward compat
- Ship providers/qwen.py, providers/openrouter.py, providers/gemini.py
- Tests for the 3 with dependency-injection (no live calls)

### Phase 2 — Ollama + dispatch cascade (~1h sonnet)

- providers/ollama.py
- Extend dispatch.py for N-provider cascade
- Config loader for llm_providers block
- Tests for cascade advance rules per provider

### Phase 3 — Opt-in providers (~1h sonnet)

- providers/openai.py (ChatGPT-5.x/Codex)
- providers/deepseek.py
- Tests

### Phase 4 — Verification (~1h sonnet)

- Live smoke test per provider (gated on API key presence)
- /llm-status skill updates to show all configured providers
- scripts/smoke-multi-provider-fallback.sh

Total: ~4.5h sonnet, ~$4 in agent costs.

## Consequences

### Positive
- Independence from Claude Max quota during peak usage
- True local fallback (Ollama) when everything else fails
- Cost optimization: automatic route to cheapest capable provider
- Foundation for ADR-052 benchmarking harness (different providers comparable)

### Negative
- Config surface grows (cognitive-os.yaml llm_providers block)
- Each new provider = new .env var + quality variance
- OpenAI-compat is NOT 100% compatible across providers (subtle diffs in
  function-calling format, response shape). Expect edge cases.

### Neutral
- Claude stays in the cascade at the last tier — behavior unchanged when
  all other tiers exhausted.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| LiteLLM proxy | ADR-049 rejected it (supply chain compromise March 2026) |
| Cloud-only providers | ADR-060 rejected cloud as default-supported path |
| Single OpenAI-compat wrapper with dynamic base_url switching at runtime | More brittle; per-provider wrapper gets per-provider auth/cost/quirks correctly |
| Replicate full Claude Agent SDK | ADR-062 scope is narrower — just tool-loop dispatch, not full Agent() semantics |

## Verification

- `uv run python3 scripts/orchestrator.py run --task "say hi" --providers qwen,openrouter,gemini,ollama,claude --show-text` — runs successfully, first available tier answers.
- `uv run python3 -c "from lib.providers.qwen import is_configured; print(is_configured())"` — returns True iff ALIBABA_QWEN_API_KEY set. Same pattern for every provider.
- `uv run pytest tests/unit/test_providers/ -v` — all pass, each provider has ≥5 tests.
- `scripts/smoke-multi-provider-fallback.sh` — live verification (skips tiers without API keys).

## Related

- ADR-049 — Provider selection + overflow cascade (predecessor)
- ADR-051 — Qwen agent loop (Phase 1-4 shipped; this ADR generalizes)
- ADR-060 — Local-only policy (informs opt-in rules for OpenAI/DeepSeek)
- ADR-056 — Adaptive agent dispatch (L1/L2/L3 still relevant, apply across all providers)
- `lib/qwen_agent_loop.py` — existing implementation, source of the refactor
- `lib/dispatch.py` — consumer of the cascade

## Open questions

1. **OpenRouter routing model**: `openrouter/auto` routes to best-for-task.
   Do we want that or explicit model selection per task? Start with auto;
   revisit when we have dogfood data per-task.
2. **Ollama model defaults**: llama3.3:70b requires 40GB+ RAM. Smaller
   default (qwen3:32b = ~20GB)? Operator-dependent.
3. **Rate-limit detection per provider**: OpenRouter, Gemini, Ollama each
   return different error codes. Need per-provider `_is_rate_limit_error()`
   or we mis-classify.
4. **Failover on malformed tool-call**: some providers emit non-spec
   tool_use payloads. Loop must tolerate + retry. Observed? TBD.
