# @luum/advisor-mcp

Optional external-advisor MCP server for Cognitive OS.

Any AI coding agent (Claude Code, Cursor, Windsurf, etc.) can call
`consult_advisor` to get concise architectural guidance from a smarter model
mid-task — without that model writing code.

Inspired by Anthropic's Advisor Strategy, but vendor-agnostic: works with
local Ollama, LiteLLM proxy, OpenAI, Google, or explicitly enabled Anthropic API.

This package is an external-advisor transport. It is not the canonical Claude
Code-native advisor primitive and does not reuse a logged-in Claude Code model
session. For native Claude Code advising, use harness-native delegation/subagents
when available.

## Installation

```bash
# Core requirement
pip install fastmcp

# Install the provider SDKs you need
pip install anthropic          # Anthropic Claude
pip install openai             # OpenAI GPT-4o / o3
pip install google-generativeai  # Google Gemini
pip install litellm            # LiteLLM multi-provider proxy
pip install httpx              # Local Ollama
```

## MCP Registration

Add to `.claude/settings.json` (or your editor's MCP config):

```json
{
    "mcpServers": {
        "advisor": {
            "command": "python3",
            "args": ["-m", "packages.advisor-mcp.advisor_server"],
            "cwd": "/path/to/luum-agent-os",
            "env": {
                "OPENAI_API_KEY": "${OPENAI_API_KEY}",
                "GOOGLE_API_KEY": "${GOOGLE_API_KEY}",
                "LITELLM_API_BASE": "${LITELLM_API_BASE}",
                "LITELLM_MODEL": "${LITELLM_MODEL}"
            }
        }
    }
}
```

Or run directly:

```bash
python packages/advisor-mcp/advisor_server.py
```

## Tool: `consult_advisor`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `context` | str | required | What the executor has learned so far |
| `question` | str | required | Specific question for the advisor |
| `provider` | str | `"auto"` | `auto`, `local`, `litellm`, `openai`, `google`, `anthropic` |
| `model` | str | `""` | Override model (empty = provider default) |
| `max_tokens` | int | `500` | Max tokens in advisor response |

### Provider auto-resolution

`provider="auto"` is the default. It resolves in this order without selecting
Anthropic just because an ambient key exists:

1. `local`, only when Ollama is reachable.
2. `litellm`, only when LiteLLM is explicitly configured.
3. `openai`, only when SDK and `OPENAI_API_KEY` are present.
4. `google`, only when SDK and `GOOGLE_API_KEY`/`GEMINI_API_KEY` are present.
5. `anthropic`, only when SDK, `ANTHROPIC_API_KEY`, and
   `llm_providers.claude_sdk.enabled: true` are present.

If no provider is available, the tool returns an actionable `ERROR:` string
without making a paid API call.

### Default models per provider

| Provider | Default model |
|----------|---------------|
| anthropic | claude-opus-4-6 |
| openai | gpt-4o |
| google | gemini-2.5-pro |
| litellm | gpt-4o |
| local | llama3 |

### Example usage (from an agent prompt)

```
Use the advisor MCP tool to get strategic guidance:

consult_advisor(
    context="I'm implementing a cache layer for the users service. The service
             makes ~500 DB calls/min. I found that the current repo pattern uses
             Redis via the cache interface in lib/cache.py.",
    question="Should I use write-through or write-behind caching here? What are
              the failure risks I should design for?",
    provider="auto"
)
```

### Example with model override

```
consult_advisor(
    context="...",
    question="What's the safest migration strategy for renaming this table?",
    provider="openai",
    model="o3",
    max_tokens=300
)
```

### Using a local Ollama model

```
consult_advisor(
    context="...",
    question="...",
    provider="local",
    model="llama3.2"
)
```

Set `OLLAMA_URL` env var if Ollama is not at `http://localhost:11434`.

## Cost Tracking

Every successful consultation is logged to:
```
.cognitive-os/metrics/advisor-consultations.jsonl
```

Format:
```json
{
    "timestamp": "2026-04-09T12:00:00Z",
    "provider": "anthropic",
    "model": "claude-opus-4-6",
    "input_tokens": 823,
    "output_tokens": 312,
    "estimated_cost_usd": 0.035,
    "question_preview": "Should I use write-through or write-behind caching..."
}
```

## Graceful Degradation

If a provider SDK is not installed, `consult_advisor` returns an `ERROR:` string
describing what to install — the server never crashes. All other tools and
providers continue to work normally.

## Environment Variables

| Variable | Provider | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | anthropic | Anthropic API key; only used when `llm_providers.claude_sdk.enabled: true` |
| `OPENAI_API_KEY` | openai | OpenAI API key |
| `GOOGLE_API_KEY` | google | Google AI API key (also `GEMINI_API_KEY`) |
| `LITELLM_API_BASE` / `LITELLM_BASE_URL` / `LITELLM_PROXY_URL` | litellm | Explicit LiteLLM gateway configuration |
| `LITELLM_MODEL` | litellm | Explicit default LiteLLM model override |
| `OLLAMA_URL` | local | Ollama base URL (default: `http://localhost:11434`) |

LiteLLM may read additional provider-specific environment variables depending on the model it routes to.

## Advisor Behavior

The advisor receives this system prompt regardless of provider:

> You are a strategic advisor to a coding agent. You do NOT write code.
> You provide concise, actionable architectural and strategic guidance.
> Keep responses under 200 words. Use numbered steps when possible.
> Focus on: approach selection, risk identification, edge cases, and architecture decisions.

## Integration with Cognitive OS

The advisor is ideal for mid-task decisions that exceed the executor's
capability tier. Orchestrator routing guidance from `rules/model-routing.md`:

- Use `provider="auto"` by default for safe external-advisor resolution.
- Use `provider="local"` (llama3) for cost-free guidance when Ollama is running.
- Use `provider="litellm"` to route through an explicitly configured LiteLLM proxy.
- Use `provider="openai"` or `provider="google"` only when those provider credentials are intentionally configured.
- Use `provider="anthropic"` (claude-opus-4-6) only when direct Anthropic API is explicitly enabled via `llm_providers.claude_sdk.enabled: true`.
