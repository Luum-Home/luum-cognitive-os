# SCOPE: both
"""Prompt Builder — wires context_diet + prompt_cache into agent orchestration.

This module is the integration point between:
  - lib/context_diet.py  (select only relevant rules for a task type)
  - lib/prompt_cache.py  (mark stable content with Anthropic cache_control)

It is designed to be called from two places:
  1. Python orchestrator code (ClaudeExecutor, batch_runner, etc.)
  2. Bash hooks via a thin subprocess call (see build_prompt_for_hook())

Usage — Python API::

    from lib.prompt_builder import PromptBuilder

    builder = PromptBuilder.from_project("/path/to/project")

    # Get a minimal, cache-ready system prompt for a sub-agent
    system_blocks = builder.build_system_prompt(
        task_type="implement",
        task_description="Build a new payment endpoint",
        preamble="You are a sub-agent...",
    )
    # Returns list[dict] with cache_control breakpoints set on stable content.

    # Or get the full message list with caching applied
    messages = builder.build_messages(
        task_type="review",
        task_description="Review the auth module",
        preamble=preamble_text,
        conversation=[
            {"role": "user", "content": "Please review this code"},
        ],
    )

Usage — Hook/shell subprocess::

    python3 -c "
    import sys, os
    sys.path.insert(0, os.environ.get('CLAUDE_PROJECT_DIR', '.'))
    from lib.prompt_builder import build_prompt_for_hook
    result = build_prompt_for_hook(task_type='implement', project_dir='.')
    print(result)
    "
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.config_loader import find_config_path as _cl_find_config_path
from lib.context_diet import ContextDiet
from lib.prompt_cache import apply_cache_to_system_prompt, apply_message_cache

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# Approximate token budgets
_DEFAULT_TASK_TYPE = "implement"
_RULES_SECTION_HEADER = "## Active Rules\n\n"


def _load_preamble(project_dir: str, phase: str = "reconstruction") -> str:
    """Load the agent preamble template with phase interpolated."""
    preamble_path = Path(project_dir) / "templates" / "agent-preamble.md"
    if not preamble_path.exists():
        return f"Project phase: {phase}"

    text = preamble_path.read_text(encoding="utf-8")
    return text.replace("{{phase}}", phase)


def _load_planning_template(project_dir: str) -> str:
    """Load the ADR-038 Wave 4 planning template when present."""
    planning_path = Path(project_dir) / "templates" / "agent-planning.md"
    if not planning_path.exists():
        return ""
    return planning_path.read_text(encoding="utf-8")


def _should_include_planning_template(task_type: str, task_description: str = "") -> bool:
    """Return true when the task should receive the separate planning template."""
    haystack = f"{task_type} {task_description}".lower()
    planning_tokens = (
        "plan",
        "planning",
        "design",
        "architecture",
        "research-first",
        "spike",
        "roadmap",
    )
    return any(token in haystack for token in planning_tokens)


# ---------------------------------------------------------------------------
# PromptBuilder class
# ---------------------------------------------------------------------------


class PromptBuilder:
    """Composes cache-ready sub-agent prompts using minimal rules.

    Combines:
      - ContextDiet: selects only the rules relevant to the task type.
      - apply_cache_to_system_prompt / apply_message_cache: adds
        Anthropic cache_control breakpoints to stable content (system
        prompt + preamble + rules) so repeated agent launches reuse
        cached tokens at ~10% of the normal input token cost.

    Args:
        diet: Configured ContextDiet instance.
        project_dir: Absolute path to the project root.
        enable_cache: Whether to apply cache_control markers.
            Default True.  Set False for non-Anthropic providers.
        cache_ttl: Cache time-to-live passed to prompt_cache.
            "5m" (default) or "1h".
    """

    def __init__(
        self,
        diet: ContextDiet,
        project_dir: str = ".",
        *,
        enable_cache: bool = True,
        cache_ttl: str = "5m",
    ) -> None:
        self._diet = diet
        self._project_dir = project_dir
        self._enable_cache = enable_cache
        self._cache_ttl = cache_ttl

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_project(
        cls,
        project_dir: str = ".",
        *,
        enable_cache: bool = True,
        cache_ttl: str = "5m",
    ) -> "PromptBuilder":
        """Create a PromptBuilder by auto-discovering project config.

        Args:
            project_dir: Root of the project (contains cognitive-os.yaml).
            enable_cache: Enable cache_control markers (default True).
            cache_ttl: Cache TTL ("5m" or "1h").

        Returns:
            Configured PromptBuilder ready for use.
        """
        # Search project_dir first, then fall back to canonical env-var / cwd search.
        _proj_candidates = [
            os.path.join(project_dir, "cognitive-os.yaml"),
            os.path.join(project_dir, ".cognitive-os", "cognitive-os.yaml"),
        ]
        config_path: Optional[str] = next(
            (p for p in _proj_candidates if os.path.isfile(p)), None
        ) or _cl_find_config_path()

        diet = ContextDiet.from_yaml(
            config_path=config_path or "cognitive-os.yaml",
        )
        return cls(
            diet=diet,
            project_dir=project_dir,
            enable_cache=enable_cache,
            cache_ttl=cache_ttl,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_system_prompt(
        self,
        task_type: str = _DEFAULT_TASK_TYPE,
        task_description: str = "",
        preamble: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Build a cache-ready system prompt block list.

        Selects the minimal rules for the given task type, combines them
        with the preamble, and wraps the result in an Anthropic-style
        content block with cache_control set.

        Args:
            task_type: Task type string (see ContextDiet.select_rules).
                Examples: "implement", "review", "debug", "archive".
            task_description: Optional description passed to ContextDiet
                for future keyword-based rule expansion.
            preamble: Optional preamble text.  If None, loads from
                templates/agent-preamble.md with phase interpolated.

        Returns:
            List of content blocks suitable for the Anthropic ``system``
            parameter.  When enable_cache=True, the last block carries a
            ``cache_control: {type: "ephemeral"}`` marker.
        """
        if preamble is None:
            preamble = _load_preamble(self._project_dir, self._diet.phase)

        # Select only the rules relevant to this task type
        rules_content = self._diet.get_lean_context(task_type, task_description)
        planning_template = (
            _load_planning_template(self._project_dir)
            if _should_include_planning_template(task_type, task_description)
            else ""
        )

        # Assemble stable system prompt content
        system_text = "\n\n".join(
            part
            for part in [preamble, planning_template, _RULES_SECTION_HEADER + rules_content]
            if part
        )

        if self._enable_cache:
            return apply_cache_to_system_prompt(system_text, cache_ttl=self._cache_ttl)

        # Cache disabled — return a plain text block (no cache_control)
        return [{"type": "text", "text": system_text}]

    def build_messages(
        self,
        task_type: str = _DEFAULT_TASK_TYPE,
        task_description: str = "",
        preamble: Optional[str] = None,
        conversation: Optional[List[Dict[str, Any]]] = None,
        native_anthropic: bool = False,
    ) -> List[Dict[str, Any]]:
        """Build a full message list with cache breakpoints applied.

        Composes: system message (preamble + lean rules) + conversation
        history with up to 4 cache_control breakpoints using the
        system_and_3 strategy from prompt_cache.

        Args:
            task_type: Task type for rule selection.
            task_description: Optional task description.
            preamble: Optional preamble override.
            conversation: Existing conversation messages (role+content).
                If None, returns just the system message.
            native_anthropic: Pass True when calling Anthropic directly
                (not via OpenRouter/LiteLLM) for tool-message caching.

        Returns:
            Message list with cache_control markers applied.
        """
        if preamble is None:
            preamble = _load_preamble(self._project_dir, self._diet.phase)

        rules_content = self._diet.get_lean_context(task_type, task_description)
        planning_template = (
            _load_planning_template(self._project_dir)
            if _should_include_planning_template(task_type, task_description)
            else ""
        )
        system_text = "\n\n".join(
            part
            for part in [preamble, planning_template, _RULES_SECTION_HEADER + rules_content]
            if part
        )

        system_msg: Dict[str, Any] = {"role": "system", "content": system_text}
        messages: List[Dict[str, Any]] = [system_msg] + list(conversation or [])

        if self._enable_cache:
            return apply_message_cache(
                messages,
                cache_ttl=self._cache_ttl,
                native_anthropic=native_anthropic,
            )

        return messages

    def selected_rules(
        self, task_type: str = _DEFAULT_TASK_TYPE, task_description: str = ""
    ) -> List[str]:
        """Return the rule filenames selected for this task type.

        Delegates to ContextDiet.select_rules — exposed here so callers
        do not need to import context_diet directly.

        Args:
            task_type: Task type string.
            task_description: Optional description for future expansion.

        Returns:
            List of rule filenames (e.g. ["RULES-COMPACT.md", "trust-score.md"]).
        """
        return self._diet.select_rules(task_type, task_description)

    @property
    def phase(self) -> str:
        """Current project phase from cognitive-os.yaml."""
        return self._diet.phase


# ---------------------------------------------------------------------------
# Shell / hook integration helper
# ---------------------------------------------------------------------------


def build_prompt_for_hook(
    task_type: str = "unknown",
    project_dir: str = ".",
    include_rules_list: bool = True,
) -> str:
    """Return a concise context string suitable for stderr hook output.

    Called from context-diet.sh (or any other hook) to provide a
    minimal, human-readable summary of which rules are active for the
    detected task type.

    Args:
        task_type: Detected task type (from prompt keyword matching).
        project_dir: Project root directory.
        include_rules_list: Whether to include the list of selected rules.

    Returns:
        One-line or multi-line advisory string (no cache markers —
        those apply to API calls, not hook output).
    """
    try:
        builder = PromptBuilder.from_project(project_dir)
        rules = builder.selected_rules(task_type)
        rule_count = len(rules)
        rule_names = ", ".join(rules)

        lines = [f"PROMPT BUILDER: task_type={task_type}, {rule_count} rules selected"]
        if include_rules_list:
            lines.append(f"  Rules: {rule_names}")
        lines.append(f"  Cache: {'enabled' if builder._enable_cache else 'disabled'}")
        lines.append(f"  Phase: {builder.phase}")
        return "\n".join(lines)

    except Exception as exc:  # noqa: BLE001 — graceful degradation in hooks
        return f"PROMPT BUILDER: degraded ({exc})"
