"""Unit tests for SemanticFallbackAdapter (REQ-006, CLR-1).

Mocks SemanticSkillMatcher so the test runs without FastEmbed.
Uses real SemanticMatch instances to exercise the .confidence contract
(see ADR-296). Candidates are (skill_name, description) tuples as
emitted by BenchmarkHarness._benchmark_one.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from lib.semantic_skill_matcher import SemanticMatch


def _match(skill_name: str, confidence: float) -> SemanticMatch:
    return SemanticMatch(
        skill_name=skill_name,
        confidence=confidence,
        reason="test",
        invoke_command=f"/{skill_name}",
    )


def test_predict_returns_ranked_tuples() -> None:
    from lib.routing_benchmark import SemanticFallbackAdapter

    adapter = SemanticFallbackAdapter(
        "semantic-fallback", "adr-296-runtime-fallback", "fallback"
    )
    candidates = [("add-hook", "Add hook")]
    with patch("lib.routing_benchmark.SemanticSkillMatcher") as MockMatcher:
        instance = MockMatcher.return_value
        instance.match.return_value = [_match("add-hook", 0.72)]
        result = adapter.predict("add a new hook", candidates)
    assert result == [("add-hook", 0.72)]


def test_adapter_reraises_matcher_build_failure() -> None:
    from lib.routing_benchmark import SemanticFallbackAdapter

    adapter = SemanticFallbackAdapter(
        "semantic-fallback", "adr-296-runtime-fallback", "fallback"
    )
    candidates = [("x", "x")]
    with patch(
        "lib.routing_benchmark.SemanticSkillMatcher",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError, match="failed to build matcher"):
            adapter.predict("prompt", candidates)


def test_rebuilds_matcher_when_candidates_change() -> None:
    from lib.routing_benchmark import SemanticFallbackAdapter

    adapter = SemanticFallbackAdapter(
        "semantic-fallback", "adr-296-runtime-fallback", "fallback"
    )
    first_candidates = [("add-hook", "Add hook")]
    second_candidates = [("run-tests", "Run tests")]
    with patch("lib.routing_benchmark.SemanticSkillMatcher") as MockMatcher:
        MockMatcher.side_effect = [
            type(
                "FirstMatcher",
                (),
                {"match": lambda self, prompt, threshold=0.0: [_match("add-hook", 0.7)]},
            )(),
            type(
                "SecondMatcher",
                (),
                {"match": lambda self, prompt, threshold=0.0: [_match("run-tests", 0.8)]},
            )(),
        ]
        assert adapter.predict("add a hook", first_candidates) == [("add-hook", 0.7)]
        assert adapter.predict("run tests", second_candidates) == [("run-tests", 0.8)]
    assert MockMatcher.call_count == 2


def test_registry_has_semantic_fallback() -> None:
    from lib.routing_benchmark import _ADAPTER_REGISTRY

    assert "semantic-fallback" in _ADAPTER_REGISTRY
