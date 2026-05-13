# SCOPE: os-only
"""Agent reflection loop (ADR-290 Pattern 5).

Iterative critique step that wraps an existing response. The caller supplies
an ``llm_call(prompt) -> (reflection_text, "yes"|"no")`` callable; the loop
runs until either the LLM emits a satisfactory verdict (``"yes"``) **and** the
minimum number of iterations has been reached, or the maximum iteration
budget is exhausted.

This is a leaf module — wiring it into ``agent_runner`` is intentionally out
of scope for ADR-290 and left to a future change.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

Verdict = Literal["yes", "no"]
LLMCall = Callable[[str], tuple[str, Verdict]]

DEFAULT_REFLECTION_PROMPT_TEMPLATE = (
    "You are a critic. Inspect the following draft response and answer:\n"
    "1) Provide a brief critique of weaknesses or improvements.\n"
    "2) On the final line, write exactly 'yes' if the response is\n"
    "   satisfactory as-is, otherwise 'no'.\n\n"
    "DRAFT:\n{response}"
)


@dataclass(frozen=True)
class ReflectionResult:
    """One iteration of the reflection loop."""

    reflection: str
    satisfactory: bool
    iteration: int  # 1-indexed


@dataclass
class ReflectionConfig:
    """Configuration for :class:`AgentReflector`.

    ``llm_call`` MUST return a tuple ``(reflection_text, verdict)`` where
    ``verdict`` is the literal string ``"yes"`` or ``"no"``. It is the
    caller's responsibility to coerce raw LLM output into this contract.
    """

    llm_call: LLMCall | None = None
    min_reflect: int = 1
    max_reflect: int = 3
    reflection_prompt_template: str = DEFAULT_REFLECTION_PROMPT_TEMPLATE
    extra_context: dict[str, str] = field(default_factory=dict)


class AgentReflector:
    """Run a bounded reflection loop over a draft response."""

    def __init__(self, config: ReflectionConfig) -> None:
        if config.llm_call is None:
            raise ValueError("ReflectionConfig.llm_call is required")
        if config.min_reflect < 1:
            raise ValueError("min_reflect must be >= 1")
        if config.max_reflect < config.min_reflect:
            raise ValueError("max_reflect must be >= min_reflect")
        self._config = config

    def reflect(self, response: str) -> list[ReflectionResult]:
        """Return the full reflection trajectory for ``response``.

        The loop exits when:
          - the LLM returns ``"yes"`` AND ``min_reflect`` has been reached, OR
          - ``max_reflect`` iterations have run, regardless of verdict.
        """
        assert self._config.llm_call is not None  # validated in __init__
        cfg = self._config
        trajectory: list[ReflectionResult] = []

        for i in range(1, cfg.max_reflect + 1):
            prompt = cfg.reflection_prompt_template.format(
                response=response, **cfg.extra_context
            )
            reflection_text, verdict = cfg.llm_call(prompt)
            if verdict not in ("yes", "no"):
                raise ValueError(
                    f"llm_call returned non-canonical verdict: {verdict!r}"
                )
            satisfactory = verdict == "yes"
            trajectory.append(
                ReflectionResult(
                    reflection=reflection_text,
                    satisfactory=satisfactory,
                    iteration=i,
                )
            )
            if satisfactory and i >= cfg.min_reflect:
                break
        return trajectory
