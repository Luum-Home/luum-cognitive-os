# SCOPE: both
"""Backward-compatibility shim — Qwen agent loop (ADR-062).

This module is now a thin shim over lib/openai_compatible_agent_loop.py that
pre-fills provider="qwen" for backward compatibility. All implementation has
moved to the provider-agnostic module.

Any code that imported from this module continues to work unchanged:
    from lib.qwen_agent_loop import run_agent, AgentLoopResult
    from lib.qwen_agent_loop import TOOL_SCHEMAS, ALL_TOOL_NAMES, TOOL_IMPLS

Reference: docs/adrs/ADR-062-multi-provider-agent-loop.md (Phase 1)
"""

from lib.openai_compatible_agent_loop import (  # noqa: F401 — re-export for backward compat
    AgentLoopResult,
    ALL_TOOL_NAMES,
    BASH_BLOCKLIST,
    DEFAULT_BASH_TIMEOUT_S,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_TOKEN_BUDGET,
    TOOL_IMPLS,
    TOOL_SCHEMAS,
    _execute_tool,
    _tool_edit_file,
    _tool_glob_files,
    _tool_grep_files,
    _tool_read_file,
    _tool_run_bash,
    _tool_web_fetch,
)
from lib import qwen_provider as _qp
from typing import Any, List, Optional


def run_agent(
    task: str,
    tools_allowed: Optional[List[str]] = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    model: str = _qp.DEFAULT_MODEL,
    system_prompt: Optional[str] = None,
    verbose: bool = False,
    client: Any = None,
    *,
    context_level: str = "none",
) -> AgentLoopResult:
    """Qwen-specific agent loop. Delegates to openai_compatible_agent_loop with provider='qwen'.

    Signature preserved for backward compatibility with all callers that passed
    model= as a positional or keyword argument using qwen model names.
    """
    from lib.openai_compatible_agent_loop import run_agent as _run
    return _run(
        task=task,
        provider="qwen",
        tools_allowed=tools_allowed,
        max_iterations=max_iterations,
        token_budget=token_budget,
        model=model,           # explicit qwen model name takes priority
        system_prompt=system_prompt,
        verbose=verbose,
        client=client,
        context_level=context_level,
    )
