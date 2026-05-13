"""Tests for lib/reinvention_semantic.py (ADR-029b Phase B-α).

Five cases covering: build, exact match, partial/paraphrase match, no-match,
threshold enforcement.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from lib.reinvention_semantic import SemanticIndex


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Minimal project tree with lib/ and hooks/ files to index."""
    (tmp_path / "lib").mkdir()
    (tmp_path / "hooks").mkdir()
    (tmp_path / "scripts").mkdir()

    (tmp_path / "lib" / "rate_limiter.py").write_text(textwrap.dedent('''\
        """Rate Limiter — prevents token flooding and excessive tool usage.

        Tracks tool calls, agent launches, bash commands per minute and hour.
        """
        class RateLimiter:
            def check(self, action):
                """Return whether the action is allowed."""
                return True
    '''))

    (tmp_path / "lib" / "agent_bus.py").write_text(textwrap.dedent('''\
        """Agent Bus — Valkey pub/sub for heartbeat, liveness, and progress."""
        class AgentBus:
            def publish_heartbeat(self, agent_id):
                """Emit a liveness ping."""
                pass
    '''))

    (tmp_path / "lib" / "tiny.py").write_text('"""x"""\n')  # too thin, filtered

    (tmp_path / "hooks" / "auto-verify.sh").write_text(textwrap.dedent('''\
        #!/usr/bin/env bash
        # Auto verify — runs acceptance criteria commands after agent completion.
        # Detects PASS / FAIL and re-launches on failure.
        verify_task() {
          echo "running"
        }
    '''))

    return tmp_path


def test_build_index_populates_items(sample_project: Path):
    idx = SemanticIndex(sample_project / ".cognitive-os" / "reinvention-index.json")
    idx.build_index(sample_project)

    paths = {item["path"] for item in idx.items}
    assert "lib/rate_limiter.py" in paths
    assert "lib/agent_bus.py" in paths
    assert "hooks/auto-verify.sh" in paths
    # tiny.py has < 2 tokens after filtering -> dropped
    assert "lib/tiny.py" not in paths
    assert idx.index_path.is_file()

    # Persisted JSON is valid and round-trips.
    other = SemanticIndex(idx.index_path)
    assert other.load() is True
    assert len(other.items) == len(idx.items)


def test_exact_name_match_scores_highest(sample_project: Path):
    idx = SemanticIndex(sample_project / ".cognitive-os" / "idx.json")
    idx.build_index(sample_project)

    matches = idx.find_similar(
        "create lib/rate_limiter.py to cap tool calls per minute",
        top_k=3,
        min_score=0.05,
    )
    assert matches, "expected at least one match"
    assert matches[0]["path"] == "lib/rate_limiter.py"
    assert matches[0]["score"] > 0.1
    # The matched_tokens should include the real overlap.
    assert "rate" in matches[0]["matched_tokens"]


def test_paraphrase_match_surfaces_agent_bus(sample_project: Path):
    """Phase B motivating case: 'agent heartbeat' should surface agent_bus.py."""
    idx = SemanticIndex(sample_project / ".cognitive-os" / "idx.json")
    idx.build_index(sample_project)

    matches = idx.find_similar(
        "add lib/agent_heartbeat.py to emit liveness pings for each agent",
        top_k=3,
        min_score=0.05,
    )
    paths = [m["path"] for m in matches]
    assert "lib/agent_bus.py" in paths, f"expected agent_bus.py in {paths}"
    # agent_bus must outrank rate_limiter on this query.
    bus_score = next(m["score"] for m in matches if m["path"] == "lib/agent_bus.py")
    rl_scores = [m["score"] for m in matches if m["path"] == "lib/rate_limiter.py"]
    if rl_scores:
        assert bus_score > rl_scores[0]


def test_no_match_when_query_is_unrelated(sample_project: Path):
    idx = SemanticIndex(sample_project / ".cognitive-os" / "idx.json")
    idx.build_index(sample_project)

    matches = idx.find_similar(
        "render a quantum chromodynamics lattice visualisation",
        top_k=3,
        min_score=0.3,
    )
    assert matches == []


def test_threshold_filters_low_scores(sample_project: Path):
    idx = SemanticIndex(sample_project / ".cognitive-os" / "idx.json")
    idx.build_index(sample_project)

    # One shared token ("agent") between the query and agent_bus.py → tiny Jaccard.
    loose = idx.find_similar("agent", top_k=5, min_score=0.01)
    strict = idx.find_similar("agent", top_k=5, min_score=0.9)
    assert len(strict) <= len(loose)
    assert strict == []  # nothing realistically scores > 0.9 on a single-word query
    for m in loose:
        assert m["score"] >= 0.01
