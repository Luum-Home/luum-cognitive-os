# llm-providers

Multi-provider OpenAI-compatible wrappers for the Cognitive OS agent loop (ADR-062).

## Contents

| File | Provider |
|------|----------|
| `lib/qwen.py` | Qwen / local Ollama-served models |
| `lib/openrouter.py` | OpenRouter (free-tier + paid routing) |
| `lib/gemini.py` | Google Gemini |
| `lib/ollama.py` | Local Ollama endpoint |
| `lib/openai.py` | OpenAI-compatible endpoint |
| `lib/deepseek.py` | DeepSeek (R1 / Chat) |
| `lib/claude_sdk.py` | Anthropic Claude via the official SDK (opt-in) |
| `lib/__init__.py` | Package exports and provider registry |

## Symlink

`lib/providers` in the repo root is a symlink to this package's `lib/` directory,
allowing code to import as `from lib.providers.qwen import QwenProvider`.

## Design

See [ADR-062](../../docs/adrs/ADR-062-multi-provider-agent-loop.md) for the full
architecture decision: provider priority order, Qwen-primary strategy, Claude SDK
opt-in flag, and fallback chain configuration.
