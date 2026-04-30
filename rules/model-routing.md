<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Model Routing — Auto-Updated by /model-optimizer

## Routing Table

| Skill | Recommended Model | Confidence | Avg Cost | Notes |
|---|---|---|---|---|
| sdd-init | sonnet | default | — | Reads structure only |
| sdd-explore | sonnet | default | — | Code exploration |
| sdd-propose | opus | default | — | Deep reasoning needed |
| sdd-spec | sonnet | default | — | Structured writing |
| sdd-design | opus | default | — | Architecture decisions |
| sdd-tasks | sonnet | default | — | Mechanical decomposition |
| sdd-apply | sonnet+advisor | high | — | Sonnet executes, Opus advises on architecture |
| sdd-verify | sonnet+advisor | high | — | Sonnet verifies, Opus advises on edge cases |
| sdd-archive | haiku | default | — | Simple documentation |
| systematic-debugging | sonnet+advisor | high | — | Sonnet debugs, Opus advises on root cause |
| test-driven-development | sonnet | default | — | Fast red-green cycles |
| verification-before-completion | sonnet | default | — | Evidence checking |

> **sonnet+advisor** requires `ORCHESTRATOR_MODE=executor` and the `anthropic` Python package.
> When preconditions are not met, falls back to `sonnet` automatically.

## How This Works

The orchestrator checks this table before delegating to sub-agents.
- **high** confidence: Always use recommended model
- **medium** confidence: Use recommended, continue collecting data
- **default** confidence: Initial guess, needs real data from /model-optimizer

> Prices as of March 2026. Verify current pricing at provider documentation.
> The cost predictor (lib/cost_predictor.py) calculates real prices from actual API responses.

## Model Cost Reference

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Best For |
|---|---|---|---|
| opus | $15 | $75 | Deep reasoning, architecture, debugging |
| sonnet+advisor | $3 + ~$0.12/advice | $15 + ~$0.60/advice | Deep reasoning at fraction of Opus cost |
| sonnet | $3 | $15 | General tasks, implementation, specs |
| haiku | $0.25 | $1.25 | Simple documentation, archiving |
| openrouter/free | $0.00 | $0.00 | Last-resort fallback when budget exhausted |

> `sonnet+advisor` billing: executor tokens at Sonnet rates + each advisory call costs ~500 in + ~1000 out at Opus rates (~$0.075/advice at current pricing). With `max_uses=3`, worst-case overhead is ~$0.23 vs full Opus.

## Dynamic Multi-Provider Routing

The `lib/model_router.py` module extends static routing with dynamic, multi-provider model selection.

### Supported Models

| Model | Provider | Reasoning | Speed | Code | Context | Input $/1M | Output $/1M | Local |
|---|---|---|---|---|---|---|---|---|
| claude-opus-4-6 | Anthropic | 9 | 3 | 8 | 1M | $15.00 | $75.00 | No |
| claude-sonnet-4 | Anthropic | 6 | 7 | 7 | 200K | $3.00 | $15.00 | No |
| claude-haiku-3.5 | Anthropic | 3 | 9 | 4 | 200K | $0.25 | $1.25 | No |
| gpt-4o | OpenAI | 7 | 6 | 7 | 128K | $2.50 | $10.00 | No |
| gemini-2.5-pro | Google | 8 | 5 | 8 | 1M | $1.25 | $5.00 | No |
| deepseek-r1 | DeepSeek | 8 | 4 | 7 | 128K | $0.55 | $2.19 | No |
| llama-3-70b | Local | 5 | 5 | 6 | 128K | $0.00 | $0.00 | Yes |
| qwen-3-32b | Local | 4 | 7 | 5 | 32K | $0.00 | $0.00 | Yes |
| openrouter/free | OpenRouter | 4 | 6 | 4 | 128K | $0.00 | $0.00 | No |
| qwen/qwen3-32b:free | OpenRouter | 5 | 7 | 5 | 40K | $0.00 | $0.00 | No |
| nvidia/llama-3.1-nemotron-ultra-253b:free | OpenRouter | 6 | 4 | 6 | 128K | $0.00 | $0.00 | No |

### Task Capability Mapping

| Capability | Tasks |
|---|---|
| reasoning | sdd-propose, sdd-design, systematic-debugging, sdd-improve |
| speed | sdd-archive, doc-sync, format |
| code | sdd-apply, sdd-tasks, test-driven-development |
| long_context | sdd-explore, repo-scout, exhaustive-prompt |
| budget | document-feature, skill-creator, sdd-archive, openrouter/free fallback |

### Python API

```python
from lib.model_router import select_model, estimate_cost, format_routing_table

# Pick best model for a task
model = select_model("sdd-propose")  # -> "claude-opus-4-6"

# With budget constraint
model = select_model("sdd-apply", budget_remaining=0.01)  # -> cheapest capable

# Prefer local models
model = select_model("sdd-apply", prefer_local=True)  # -> "llama-3-70b"

# Estimate cost
cost = estimate_cost("claude-sonnet-4", input_tokens=10000, output_tokens=5000)

# Pretty print the full routing table
print(format_routing_table())
```

## Usage

Run `/model-optimizer` to analyze collected metrics and update the static routing table above.

This table is auto-updated by running `/model-optimizer`.
Last updated: 2026-03-21 (initial defaults)
