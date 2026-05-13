"""Unit tests for lib.agent_reflection (ADR-290 Pattern 5)."""
from __future__ import annotations

import pytest

from lib.agent_reflection import AgentReflector, ReflectionConfig, ReflectionResult


def test_reflection_exits_after_minimum_when_satisfactory() -> None:
    calls: list[str] = []

    def llm_call(prompt: str) -> tuple[str, str]:
        calls.append(prompt)
        return "looks good", "yes"

    result = AgentReflector(
        ReflectionConfig(llm_call=llm_call, min_reflect=1, max_reflect=3)
    ).reflect("draft")

    assert len(result) == 1
    assert result[0].satisfactory is True
    assert result[0].iteration == 1
    assert len(calls) == 1


def test_reflection_respects_min_reflect_floor() -> None:
    """yes on iteration 1 with min_reflect=2 must continue to iteration 2."""

    def llm_call(_prompt: str) -> tuple[str, str]:
        return "ok", "yes"

    result = AgentReflector(
        ReflectionConfig(llm_call=llm_call, min_reflect=2, max_reflect=3)
    ).reflect("draft")

    assert [item.iteration for item in result] == [1, 2]
    assert all(item.satisfactory for item in result)


def test_reflection_stops_at_max_reflect_when_not_satisfactory() -> None:
    def llm_call(_prompt: str) -> tuple[str, str]:
        return "needs work", "no"

    result = AgentReflector(
        ReflectionConfig(llm_call=llm_call, min_reflect=1, max_reflect=2)
    ).reflect("draft")

    assert [item.iteration for item in result] == [1, 2]
    assert not any(item.satisfactory for item in result)


def test_no_no_yes_exits_on_third_iteration() -> None:
    verdicts = iter(["no", "no", "yes"])

    def llm_call(_prompt: str) -> tuple[str, str]:
        return "critique", next(verdicts)

    result = AgentReflector(
        ReflectionConfig(llm_call=llm_call, min_reflect=1, max_reflect=5)
    ).reflect("draft")

    assert [item.iteration for item in result] == [1, 2, 3]
    assert [item.satisfactory for item in result] == [False, False, True]


def test_llm_call_none_raises_at_construction() -> None:
    with pytest.raises(ValueError, match="llm_call"):
        AgentReflector(ReflectionConfig(llm_call=None))


def test_min_reflect_zero_rejected() -> None:
    def llm_call(_p: str) -> tuple[str, str]:
        return "x", "yes"

    with pytest.raises(ValueError, match="min_reflect"):
        AgentReflector(ReflectionConfig(llm_call=llm_call, min_reflect=0))


def test_max_below_min_rejected() -> None:
    def llm_call(_p: str) -> tuple[str, str]:
        return "x", "yes"

    with pytest.raises(ValueError, match="max_reflect"):
        AgentReflector(
            ReflectionConfig(llm_call=llm_call, min_reflect=3, max_reflect=2)
        )


def test_reflection_rejects_noncanonical_verdict() -> None:
    def llm_call(_prompt: str) -> tuple[str, str]:
        return "maybe", "maybe"  # type: ignore[return-value]

    with pytest.raises(ValueError):
        AgentReflector(ReflectionConfig(llm_call=llm_call)).reflect("draft")


def test_reflection_trajectory_items_are_dataclass_instances() -> None:
    def llm_call(_p: str) -> tuple[str, str]:
        return "x", "yes"

    result = AgentReflector(ReflectionConfig(llm_call=llm_call)).reflect("draft")
    assert all(isinstance(r, ReflectionResult) for r in result)
