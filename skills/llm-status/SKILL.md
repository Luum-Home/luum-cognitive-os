<!-- SCOPE: both -->
---
name: llm-status
description: Inspect LLM dispatch state for the current Cognitive OS install — which providers are configured, kill-switches active, recent dispatch totals (calls, tokens, cost, latency), and last-dispatch outcome. Use when user asks about LLM provider state, rate-limit diagnosis, dispatch debugging, or cost accounting.
triggers: ["/llm-status", "llm status", "provider status", "/provider-status"]
audience: both
version: 1.0.0
summary_line: "Inspect LLM dispatch state — providers configured, kill-switches, recent dispatch totals."
---

# /llm-status — LLM Dispatch Transparency

Report the state of the LLM dispatch subsystem (ADR-049): which providers
are configured, what kill-switches are currently active, and what recent
dispatches looked like (totals per provider, cost, latency, success rate).

## When to use

- User asks "what providers are configured?" or "is Qwen working?"
- Debugging a rate-limit or dispatch failure
- Before committing a cost-sensitive change — verify budget impact
- Verifying ADR-049 is actually wired and not merely documented
- User says "llm status" / "provider status" / "show dispatch state"

## Data sources

- **`.env` + process environment** → API keys, kill-switches, force-primary flag
- **`.cognitive-os/metrics/llm-dispatch.jsonl`** → every dispatch logged
  here by `lib/dispatch.py::_log_metric` (C2 of mega-plan)
- **`lib/qwen_provider.is_configured()`** → live check
- **`scripts/cos-config-audit.sh`** → `meta.llm_providers_reachable` contract

## Output format

```
COS LLM Dispatch Status
═══════════════════════

Providers configured:
  claude_max      ✓  (native Agent tool, always available)
  alibaba_qwen    ✓  (ALIBABA_QWEN_API_KEY set, base_url=<redacted>)
  openai          –  (no key)

Kill-switches:
  COS_DISABLE_LLM_FALLBACK      (not set)
  COS_DISABLE_QWEN              (not set)
  COS_FORCE_CLAUDE_PRIMARY      (not set)

Cascade default:
  --providers qwen,claude   (Qwen primary, Claude fallback)

Recent dispatches (last 30 days, .cognitive-os/metrics/llm-dispatch.jsonl):
  total calls:           N
  success rate:          XX.X%
  provider breakdown:
    alibaba_qwen:  N calls | tokens: NI→NO | cost: $X.XXXX | p50 latency: Xms
    claude:        N calls | tokens: NI→NO | cost: $X.XXXX | p50 latency: Xms
  last 3 dispatches:
    1. [ts] provider=alibaba_qwen model=qwen3.6-plus success=true cost=$0.0003
    2. [ts] ...
    3. [ts] ...

Verification: bash scripts/smoke-qwen-fallback.sh
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
python3 scripts/llm-status.py
```

or via `uv run` if providers SDK not in system Python:

```bash
uv run python3 scripts/llm-status.py
```

## Implementation notes

- Never prints API keys (show `<redacted>` or truncated `sk-xxx...abc`)
- Reads JSONL line-by-line (streaming) so large metric files don't OOM
- Default window: last 30 days; override with `--days N`
- Sorts provider breakdown by cost descending
- `--json` flag emits machine-readable output for CI/monitors

## Related

- `rules/llm-dispatch.md` — normative rule
- `docs/adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md`
- `scripts/smoke-qwen-fallback.sh` — live verification
- `scripts/cos-config-audit.sh` — `meta.llm_providers_reachable` contract
