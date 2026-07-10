# SCOPE: both
"""Qwen context injector — governance templates for sub-agent dispatches (ADR-051 Phase 3).

Claude sub-agents receive governance context via the `subagent-context-injector.sh`
hook, which reads `templates/agent-mandatory-rules.md` and `templates/agent-preamble.md`
and prepends them to the sub-agent's system prompt. Qwen sub-agents dispatched via
`lib/qwen_agent_loop.run_agent()` do NOT go through that hook — so without this
module they would miss HALT protocol, escalation rules, trust-report requirements,
acceptance-criteria discipline, etc.

This module loads the same templates and exposes `build_context_prefix(level)`.
Three levels:

    "none"    — no injection (backward-compatible default).
    "minimal" — agent-preamble.md only (~1.5K tokens). Fits haiku-tier tasks.
    "full"    — preamble + mandatory-rules (~5K tokens). Default for opus-tier.

The loader is resilient: missing template files degrade to an empty string
rather than raising, so Qwen dispatches never fail because a template was moved.

Reference: docs/02-Decisions/adrs/ADR-051-qwen-agent-loop.md (Phase 3).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

VALID_LEVELS: tuple = ("none", "minimal", "full")

# Repo root = two levels up from this file (lib/qwen_context_injector.py -> repo/).
_REPO_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATES_DIR = _REPO_ROOT / "templates"

PREAMBLE_PATH = _TEMPLATES_DIR / "agent-preamble.md"
MANDATORY_RULES_PATH = _TEMPLATES_DIR / "agent-mandatory-rules.md"


@lru_cache(maxsize=4)
def _load_template(path_str: str) -> str:
    """Read a template file. Returns empty string if missing (degraded mode).

    Accepts a string (not Path) so lru_cache works cleanly with hashable args.
    """
    path = Path(path_str)
    try:
        return path.read_text()
    except FileNotFoundError:
        logger.warning("qwen-context-injector: template missing: %s", path)
        return ""
    except Exception as exc:  # noqa: BLE001 — never crash the dispatch
        logger.warning("qwen-context-injector: template read failed for %s: %s", path, exc)
        return ""


def build_context_prefix(level: str = "none") -> str:
    """Return the governance-context prefix for a Qwen sub-agent system prompt.

    Args:
        level: "none" | "minimal" | "full".
            "none"    -> "" (no injection; backward-compatible default).
            "minimal" -> agent-preamble.md content only.
            "full"    -> mandatory-rules.md + agent-preamble.md (in that order).

    Returns:
        A string suitable to PREPEND to a caller-supplied system prompt. Always
        ends with a trailing newline when non-empty so concatenation is clean.
    """
    if level == "none":
        return ""
    if level not in VALID_LEVELS:
        logger.warning(
            "qwen-context-injector: unknown level %r, falling back to 'none'", level
        )
        return ""

    parts: list = []
    header = (
        "# Governance Context (injected by lib/qwen_context_injector — ADR-051 Phase 3)\n\n"
        "You are a sub-agent running under the Cognitive OS governance rules.\n"
        "These rules are NOT optional — follow them as strictly as a Claude sub-agent would.\n"
    )
    parts.append(header)

    if level == "full":
        rules_body = _load_template(str(MANDATORY_RULES_PATH))
        if rules_body:
            parts.append(rules_body.rstrip() + "\n")

    # Preamble is included for both "minimal" and "full".
    preamble_body = _load_template(str(PREAMBLE_PATH))
    if preamble_body:
        parts.append(preamble_body.rstrip() + "\n")

    # If all templates were missing, don't return just the header stub.
    if len(parts) == 1:
        logger.warning(
            "qwen-context-injector: level=%s but no templates loaded — returning empty prefix",
            level,
        )
        return ""

    return "\n".join(parts) + "\n"


def compose_system_prompt(
    level: str = "none",
    user_system_prompt: Optional[str] = None,
) -> Optional[str]:
    """Compose a full system prompt by prepending the governance prefix.

    Args:
        level: context injection level.
        user_system_prompt: caller-supplied system prompt (may be None).

    Returns:
        Combined prompt, or None if the result would be empty (preserves the
        existing behavior where run_agent only emits a system message when
        one is provided).
    """
    prefix = build_context_prefix(level)
    if not prefix and not user_system_prompt:
        return None
    if not prefix:
        return user_system_prompt
    if not user_system_prompt:
        return prefix.rstrip() + "\n"
    return prefix + "\n---\n\n" + user_system_prompt
