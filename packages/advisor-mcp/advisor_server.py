# SCOPE: both
"""Advisor MCP Server — Model-agnostic strategic advisor for coding agents.

Any AI coding agent (Claude Code, Cursor, Devin, etc.) can call the
`consult_advisor` tool to get strategic guidance from a smarter model
mid-task, without writing code themselves.

Inspired by Anthropic's Advisor Strategy, but vendor-agnostic: works with
local Ollama, OpenAI, Google, or explicitly enabled Anthropic API.

Requirements:
    pip install fastmcp
    pip install anthropic        # for provider="anthropic" (explicit policy-gated)
    pip install openai           # for provider="openai"
    pip install google-generativeai  # for provider="google"
    pip install httpx            # for provider="local" (Ollama)

Usage:
    python packages/advisor-mcp/advisor_server.py

Configure in .claude/settings.json:
    {
        "mcpServers": {
            "advisor": {
                "command": "python3",
                "args": ["-m", "packages.advisor-mcp.advisor_server"],
                "env": {
                    "OPENAI_API_KEY": "${OPENAI_API_KEY}",
                    "GOOGLE_API_KEY": "${GOOGLE_API_KEY}",
                }
            }
        }
    }
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root resolution
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _THIS_DIR.parent.parent

# ---------------------------------------------------------------------------
# FastMCP import with graceful degradation
# ---------------------------------------------------------------------------

try:
    from fastmcp import FastMCP
except ImportError:
    if __name__ == "__main__":
        print(
            "ERROR: fastmcp is not installed. Install with: pip install fastmcp",
            file=sys.stderr,
        )
        sys.exit(1)

    class _FastMCPCompat:
        """Tiny import-time stub used for direct tool tests when fastmcp is absent."""

        def __init__(self, name: str, **kwargs):
            self.name = name
            self.kwargs = kwargs

        def tool(self, *decorator_args, **decorator_kwargs):
            if decorator_args and callable(decorator_args[0]) and not decorator_kwargs:
                return decorator_args[0]

            def _decorator(func):
                return func

            return _decorator

        def run(self):
            raise RuntimeError("fastmcp is required to run the MCP server transport")


    FastMCP = _FastMCPCompat

# ---------------------------------------------------------------------------
# Server definition
# ---------------------------------------------------------------------------

mcp = FastMCP("advisor")

# ---------------------------------------------------------------------------
# System prompt for the advisor model
# ---------------------------------------------------------------------------

ADVISOR_SYSTEM_PROMPT = """\
You are a strategic advisor to a coding agent. You do NOT write code.
You provide concise, actionable architectural and strategic guidance.
Keep responses under 200 words. Use numbered steps when possible.
Focus on: approach selection, risk identification, edge cases, and architecture decisions.\
"""

# ---------------------------------------------------------------------------
# Default models per provider
# ---------------------------------------------------------------------------

_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-opus-4-6",
    "openai": "gpt-4o",
    "google": "gemini-2.5-pro",
    "local": "llama3",
}

_AUTO_PROVIDER_ORDER: tuple[str, ...] = (
    "local",
    "openai",
    "google",
    "anthropic",
)

# ---------------------------------------------------------------------------
# Cost estimation (per 1M tokens, input/output in USD)
# ---------------------------------------------------------------------------

_COST_TABLE: dict[str, tuple[float, float]] = {
    "claude-opus-4-6": (15.00, 75.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-3.5": (0.25, 1.25),
    "gpt-4o": (2.50, 10.00),
    "o3": (10.00, 40.00),
    "gemini-2.5-pro": (1.25, 5.00),
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost from token counts."""
    input_price, output_price = _COST_TABLE.get(model, (0.0, 0.0))
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000


# ---------------------------------------------------------------------------
# Cost logging
# ---------------------------------------------------------------------------

def _log_consultation(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    question: str,
) -> None:
    """Append a consultation record to the metrics file."""
    metrics_dir = PROJECT_ROOT / ".cognitive-os" / "metrics"
    try:
        metrics_dir.mkdir(parents=True, exist_ok=True)
        log_path = metrics_dir / "advisor-consultations.jsonl"
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": _estimate_cost(model, input_tokens, output_tokens),
            "question_preview": question[:100],
        }
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception:
        # Logging must never crash the server
        pass


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------


async def _call_anthropic(
    context: str, question: str, model: str, max_tokens: int
) -> tuple[str, int, int]:
    """Call the Anthropic API. Returns (reply, input_tokens, output_tokens)."""
    try:
        from lib.anthropic_direct_policy import direct_anthropic_api_enabled

        if not direct_anthropic_api_enabled():
            return (
                "ERROR: Anthropic provider disabled by "
                "llm_providers.claude_sdk.enabled in cognitive-os.yaml",
                0,
                0,
            )
    except Exception:
        return (
            "ERROR: Anthropic provider disabled; unable to read direct API policy",
            0,
            0,
        )

    try:
        import anthropic
    except ImportError:
        return (
            "ERROR: 'anthropic' SDK not installed. Run: pip install anthropic",
            0,
            0,
        )

    from lib.anthropic_direct_policy import direct_anthropic_api_key

    client = anthropic.AsyncAnthropic(api_key=direct_anthropic_api_key())
    user_content = f"Context:\n{context}\n\nQuestion:\n{question}"
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=ADVISOR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    reply = response.content[0].text if response.content else ""
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    return reply, input_tokens, output_tokens


async def _call_openai(
    context: str, question: str, model: str, max_tokens: int
) -> tuple[str, int, int]:
    """Call the OpenAI API. Returns (reply, input_tokens, output_tokens)."""
    try:
        from openai import AsyncOpenAI
    except ImportError:
        return (
            "ERROR: 'openai' SDK not installed. Run: pip install openai",
            0,
            0,
        )

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    user_content = f"Context:\n{context}\n\nQuestion:\n{question}"
    response = await client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": ADVISOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    reply = response.choices[0].message.content or ""
    input_tokens = response.usage.prompt_tokens if response.usage else 0
    output_tokens = response.usage.completion_tokens if response.usage else 0
    return reply, input_tokens, output_tokens


async def _call_google(
    context: str, question: str, model: str, max_tokens: int
) -> tuple[str, int, int]:
    """Call the Google Generative AI API. Returns (reply, input_tokens, output_tokens)."""
    try:
        import google.generativeai as genai
    except ImportError:
        return (
            "ERROR: 'google-generativeai' SDK not installed. "
            "Run: pip install google-generativeai",
            0,
            0,
        )

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    gen_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=ADVISOR_SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(max_output_tokens=max_tokens),
    )
    user_content = f"Context:\n{context}\n\nQuestion:\n{question}"
    response = await gen_model.generate_content_async(user_content)
    reply = response.text if response.text else ""

    # Google SDK may or may not expose token counts depending on version
    input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
    output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
    return reply, input_tokens, output_tokens


async def _call_local(
    context: str, question: str, model: str, max_tokens: int
) -> tuple[str, int, int]:
    """Call a local Ollama instance at localhost:11434. Returns (reply, input_tokens, output_tokens)."""
    try:
        import httpx
    except ImportError:
        return (
            "ERROR: 'httpx' not installed. Run: pip install httpx",
            0,
            0,
        )

    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
    prompt = (
        f"{ADVISOR_SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion:\n{question}"
    )
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{ollama_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    reply = data.get("response", "")
    # Ollama reports token counts in the response
    input_tokens = data.get("prompt_eval_count", 0)
    output_tokens = data.get("eval_count", 0)
    return reply, input_tokens, output_tokens


# ---------------------------------------------------------------------------
# Provider routing and safe auto-resolution
# ---------------------------------------------------------------------------

def _module_available(module_name: str) -> bool:
    """Return True when *module_name* can be imported without importing it."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def _env_present(*names: str) -> bool:
    """Return True when any named environment variable has a non-empty value."""
    return any(bool(os.getenv(name, "").strip()) for name in names)


def _anthropic_provider_available() -> bool:
    """Return True when Anthropic direct API use is explicitly allowed."""
    if not _module_available("anthropic"):
        return False
    try:
        from lib.anthropic_direct_policy import (
            direct_anthropic_api_enabled,
            direct_anthropic_api_key_present,
        )

        return direct_anthropic_api_enabled() and direct_anthropic_api_key_present()
    except Exception:
        return False


def _openai_provider_available() -> bool:
    """Return True when OpenAI has both SDK and credentials."""
    return _module_available("openai") and _env_present("OPENAI_API_KEY")


def _google_provider_available() -> bool:
    """Return True when Google Generative AI has both SDK and credentials."""
    return _module_available("google.generativeai") and _env_present(
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    )


async def _local_provider_available(model: str = "") -> bool:
    """Return True when a local Ollama service and target model are reachable."""
    if not _module_available("httpx"):
        return False

    try:
        import httpx

        target_model = model.strip() or _default_model_for_provider("local")
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        async with httpx.AsyncClient(timeout=0.5) as client:
            response = await client.get(f"{ollama_url}/api/tags")
        if response.status_code >= 500:
            return False

        tags = response.json().get("models", [])
        model_names = {item.get("name", "") for item in tags if isinstance(item, dict)}
        return target_model in model_names or any(
            name.split(":", 1)[0] == target_model for name in model_names
        )
    except Exception:
        return False


async def _provider_available(provider: str, model: str = "") -> bool:
    """Return True when *provider* can be used without implicit paid fallback."""
    checks = {
        "anthropic": _anthropic_provider_available,
        "openai": _openai_provider_available,
        "google": _google_provider_available,
    }
    if provider == "local":
        return await _local_provider_available(model)
    check = checks.get(provider)
    return bool(check and check())


def _provider_candidates_for_model(model: str) -> tuple[str, ...]:
    """Narrow auto provider candidates when the caller supplied a model name."""
    normalized = model.strip().lower()
    if not normalized:
        return _AUTO_PROVIDER_ORDER
    if normalized.startswith("claude"):
        return ("anthropic",)
    if normalized.startswith(("gpt", "o1", "o3", "o4")):
        return ("openai",)
    if normalized.startswith(("gemini", "models/gemini")):
        return ("google",)
    if "/" in normalized:
        return ("local",)
    return _AUTO_PROVIDER_ORDER


def _default_model_for_provider(provider: str) -> str:
    """Return the provider default model, honoring explicit gateway config."""
    return _DEFAULT_MODELS.get(provider, "")


async def _resolve_auto_provider(model: str = "") -> tuple[str, str]:
    """Resolve provider=auto without choosing cost-bearing providers implicitly."""
    unavailable: list[str] = []
    for candidate in _provider_candidates_for_model(model):
        if await _provider_available(candidate, model):
            return candidate, ""
        unavailable.append(candidate)

    checked = ", ".join(unavailable)
    return "", (
        "ERROR: No advisor provider available for provider=auto. "
        f"Checked: {checked}. Start Ollama for provider=local, "
        "or set openai/google credentials. Anthropic is "
        "eligible only when llm_providers.claude_sdk.enabled: true and "
        "the direct Anthropic API credential is set."
    )


_PROVIDERS = {
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    "google": _call_google,
    "local": _call_local,
}


# ---------------------------------------------------------------------------
# MCP tool
# ---------------------------------------------------------------------------


@mcp.tool
async def consult_advisor(
    context: str,
    question: str,
    provider: str = "auto",
    model: str = "",
    max_tokens: int = 500,
) -> str:
    """Consult a strategic advisor model for architectural guidance mid-task.

    The advisor does NOT write code. It provides concise, actionable strategic
    advice: approach selection, risk identification, edge cases, and
    architecture decisions.

    Args:
        context: What the executor has learned so far (files seen, errors hit,
                 constraints discovered, work completed).
        question: Specific strategic question for the advisor.
        provider: AI provider to use. One of: local, openai, google,
                  anthropic, auto. Default: auto. Auto prefers local and explicitly
                  configured non-Anthropic providers; the anthropic provider requires
                  llm_providers.claude_sdk.enabled: true.
        model: Override the model (leave empty to use provider default).
               Examples: claude-opus-4-6, gpt-4o, gemini-2.5-pro, llama3.
        max_tokens: Maximum tokens in the advisor's response. Default: 500.
                    Keep this low to get concise, actionable advice.

    Returns:
        Strategic advice from the advisor model, or an error string if the
        provider SDK is not installed or the API call fails.
    """
    provider = provider.lower().strip()
    if provider == "auto":
        provider, error = await _resolve_auto_provider(model)
        if error:
            return error

    if provider not in _PROVIDERS:
        supported = ", ".join(sorted([*_PROVIDERS.keys(), "auto"]))
        return f"ERROR: Unknown provider '{provider}'. Supported: {supported}"

    resolved_model = model.strip() if model.strip() else _default_model_for_provider(provider)
    if not resolved_model:
        return f"ERROR: No model specified and no default for provider '{provider}'."

    # Look up provider function through module globals so tests can patch it.
    import sys as _sys
    _mod = _sys.modules[__name__]
    call_fn = getattr(_mod, f"_call_{provider}", _PROVIDERS[provider])

    try:
        reply, input_tokens, output_tokens = await call_fn(
            context, question, resolved_model, max_tokens
        )
    except Exception as exc:
        return f"ERROR: Provider '{provider}' call failed — {type(exc).__name__}: {exc}"

    # Log the consultation (best-effort)
    if not reply.startswith("ERROR:"):
        _log_consultation(provider, resolved_model, input_tokens, output_tokens, question)

    return reply


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
