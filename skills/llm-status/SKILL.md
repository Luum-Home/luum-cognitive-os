<!-- SCOPE: both -->
---
name: llm-status
description: Inspect LLM dispatch state for the current Cognitive OS install — which providers are configured (with tier and model_map), kill-switches active, cascade config from cognitive-os.yaml, active environment keys detected, recent dispatch totals (calls, tokens, cost, latency), and last-dispatch outcome. Use when user asks about LLM provider state, rate-limit diagnosis, dispatch debugging, or cost accounting.
triggers: ["/llm-status", "llm status", "provider status", "/provider-status"]
audience: both
version: 2.0.0
summary_line: "Inspect LLM dispatch state — provider inventory, kill-switches, cascade config, recent dispatch totals."
---

# /llm-status — LLM Dispatch Transparency

Report the state of the LLM dispatch subsystem (ADR-062): which providers are
configured, their tier and model_map, what kill-switches are active, the
default cascade from `cognitive-os.yaml`, active environment keys (names only,
never values), and recent dispatch outcomes from metrics.

## When to use

- User asks "what providers are configured?" or "is Qwen working?"
- Debugging a rate-limit or dispatch failure
- Before committing a cost-sensitive change — verify budget impact
- Verifying ADR-062 multi-provider cascade is actually wired
- User says "llm status" / "provider status" / "show dispatch state"
- Checking which providers are enabled in config vs actually configured in env

## Data sources

- **`lib/providers/REGISTRY`** (`packages/llm-providers/lib/__init__.py`) → canonical provider list with tier, model_map, `is_configured()` live check
- **`cognitive-os.yaml` `llm_providers:` block** → enabled/disabled per provider, tier, advance_on policy, model_map from config
- **`.env` + process environment** → API keys (names only, never values), kill-switches
- **`.cognitive-os/metrics/llm-dispatch.jsonl`** → every dispatch logged by `lib/dispatch.py::_log_metric`
- **`scripts/cos-config-audit.sh`** → `meta.llm_providers_reachable` contract

## Output format

```
COS LLM Dispatch Status (ADR-062)
══════════════════════════════════

Provider Inventory (lib/providers/REGISTRY):
  Provider       Tier  Configured  advance_on       opus-model           sonnet-model         haiku-model
  ─────────────────────────────────────────────────────────────────────────────────────────────────────────
  qwen           1     Y           any_failure      qwen3.6-plus         qwen3-coder-plus     qwen3-coder-plus
  openrouter     2     N           any_failure      anthropic/claude-3-o meta-llama/llama-3-7 openrouter/auto
  gemini         3     N           any_failure      gemini-2.0-pro       gemini-2.0-flash     gemini-2.0-flash-lite
  ollama         4     N           any_failure      llama3.3:70b         qwen3:32b            llama3.2:3b
  openai         5     N           rate_limit_only  gpt-5.5              gpt-5.4              gpt-5.4-mini
  deepseek       5     N           any_failure      deepseek-reasoner    deepseek-chat        deepseek-chat
  claude_sdk     6     N           rate_limit_only  claude-opus-4-7      claude-sonnet-4-6    claude-haiku-3-5

Cascade config (cognitive-os.yaml llm_providers block):
  qwen       enabled=true   tier=1  advance_on=any_failure
  openrouter enabled=true   tier=2  advance_on=any_failure
  gemini     enabled=true   tier=3  advance_on=any_failure
  ollama     enabled=false  tier=4  advance_on=any_failure
  openai     enabled=false  tier=5  advance_on=rate_limit_only
  deepseek   enabled=false  tier=5  advance_on=any_failure
  claude_sdk enabled=false  tier=6  advance_on=rate_limit_only

Active environment keys detected (names only):
  ALIBABA_QWEN_API_KEY          set
  OPENROUTER_API_KEY            not set
  GEMINI_API_KEY                not set
  OLLAMA_BASE_URL               not set
  OPENAI_API_KEY                not set
  DEEPSEEK_API_KEY              not set
  ANTHROPIC_API_KEY             not set

Kill-switches:
  COS_DISABLE_LLM_FALLBACK      (not set)
  COS_DISABLE_QWEN              (not set)
  COS_FORCE_CLAUDE_PRIMARY      (not set)

Cascade default (from config):
  qwen → openrouter → gemini → (ollama/openai/deepseek/claude_sdk opt-in) → claude

Recent dispatches (last 30 days, .cognitive-os/metrics/llm-dispatch.jsonl):
  total calls:           N
  success rate:          XX.X%
  provider breakdown:
    qwen:          N calls | tokens: NI→NO | cost: $X.XXXX | p50 latency: Xms
    claude:        N calls | tokens: NI→NO | cost: $X.XXXX | p50 latency: Xms
  last 3 dispatches:
    1. [ts] provider=qwen  model=qwen3.6-plus success=true cost=$0.0003
    2. [ts] ...
    3. [ts] ...

Verification: bash scripts/smoke-multi-provider-fallback.sh
Smoke:        bash scripts/smoke-qwen-fallback.sh
Validator:    python3 scripts/cos-config-audit.sh | grep llm_providers

Actions:
  - Disable Qwen:     export COS_DISABLE_QWEN=1
  - Force Claude:     export COS_FORCE_CLAUDE_PRIMARY=1
  - No fallback:      export COS_DISABLE_LLM_FALLBACK=1
  - Re-enable Qwen:   unset COS_DISABLE_QWEN
```

## Invocation

Run the companion script:

```bash
python3 scripts/llm_status.py
```

or via `uv run` if providers SDK not in system Python:

```bash
uv run python3 scripts/llm_status.py
```

For provider inventory (ADR-062 REGISTRY + config):

```bash
uv run python3 scripts/llm_status.py --providers
```

## Implementation notes

- Never prints API key values (shows `set` / `not set` for key presence)
- Reads JSONL line-by-line (streaming) so large metric files don't OOM
- Default window: last 30 days; override with `--days N`
- Sorts provider breakdown by cost descending
- `--json` flag emits machine-readable output for CI/monitors
- Provider inventory sourced from `lib/providers/REGISTRY` — canonical ADR-062 source
- Config cascade sourced from `cognitive-os.yaml llm_providers:` block via `lib/config_loader.load_structured()`

## Related

- `rules/llm-dispatch.md` — normative rule
- `docs/adrs/ADR-062-multi-provider-agent-loop.md` — multi-provider cascade
- `docs/adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md`
- `scripts/smoke-multi-provider-fallback.sh` — exercises all configured providers
- `scripts/smoke-qwen-fallback.sh` — Qwen-specific verification
- `scripts/cos-config-audit.sh` — `meta.llm_providers_reachable` contract
- `packages/llm-providers/lib/__init__.py` — REGISTRY definition
- `lib/dispatch.py` — cascade executor with config-driven provider filtering
