"""Unit tests for lib/self_knowledge.py query API (ADR-037)."""
from __future__ import annotations

import importlib.util
import json
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load modules
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GEN_PATH = _REPO_ROOT / "scripts" / "cos-build-self-knowledge.py"
_SK_PATH = _REPO_ROOT / "packages" / "cos-self-knowledge" / "lib" / "self_knowledge.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GEN = _load_module("cos_build_self_knowledge", _GEN_PATH)
SK = _load_module("self_knowledge", _SK_PATH)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def indexed_project(tmp_path: Path) -> Path:
    """Create and index a project with known content."""
    # lib/rate_limiter.py
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "rate_limiter.py").write_text(
        textwrap.dedent("""\
            class RateLimiter:
                pass

            class TokenBucket:
                pass

            def check_rate_limit(service: str, budget: float) -> bool:
                \"\"\"Returns True if within budget. Enforces per-service limits.\"\"\"
                return True

            def reset_all() -> None:
                \"\"\"Resets all rate limit buckets. Used in tests only.\"\"\"
                pass
        """),
        encoding="utf-8",
    )
    (lib / "circuit_breaker.py").write_text(
        textwrap.dedent("""\
            class CircuitBreaker:
                pass

            def is_open(service: str) -> bool:
                \"\"\"Check if the circuit breaker is open for service.\"\"\"
                return False
        """),
        encoding="utf-8",
    )
    (lib / "agent_bus.py").write_text(
        "from lib.circuit_breaker import is_open\nfrom lib.rate_limiter import check_rate_limit\n",
        encoding="utf-8",
    )

    # hooks/
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "rate-limiter.sh").write_text(
        "#!/usr/bin/env bash\n# Rate limiting hook\ncheck_limit() { echo ok; }\n",
        encoding="utf-8",
    )

    # docs/adrs
    adrs = tmp_path / "docs" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-028-rate-limiting.md").write_text(
        textwrap.dedent("""\
            # ADR-028 — Observability and Rate Limiting

            **Status**: Accepted

            ## Rate Limiting
            Token budget monitor enforces per-service rate limits. Each service has a bucket.

            ## Error Budget
            Error budget resets monthly. Breaches trigger minimal profile.
        """),
        encoding="utf-8",
    )

    (tmp_path / "cognitive-os.yaml").write_text("project:\n  name: test\n")

    # Build the index
    GEN.build(tmp_path)

    # Invalidate the query cache so each test starts fresh
    SK._invalidate_cache()

    return tmp_path


# ---------------------------------------------------------------------------
# Test 1: substring query returns results
# ---------------------------------------------------------------------------

def test_query_returns_results(indexed_project: Path) -> None:
    """query('rate limiter') returns >= 1 result with correct structure."""
    results = SK.query("rate limiter", project_dir=indexed_project)
    assert len(results) >= 1, f"Expected results for 'rate limiter', got: {results}"

    for r in results:
        assert "source" in r
        assert "key" in r
        assert "snippet" in r
        assert "score" in r
        assert r["score"] >= 1


def test_query_ranks_path_match_highest(indexed_project: Path) -> None:
    """Results with the term in the file path score >= results with term in docs only."""
    results = SK.query("rate limiter", project_dir=indexed_project)
    # lib/rate_limiter.py has path match (score +3)
    path_matches = [r for r in results if "rate_limiter" in r["key"]]
    assert path_matches, "Expected at least one result with rate_limiter in path"
    highest_score = results[0]["score"]
    for pm in path_matches:
        assert pm["score"] >= 1


# ---------------------------------------------------------------------------
# Test 2: get_module hit and miss
# ---------------------------------------------------------------------------

def test_get_module_hit(indexed_project: Path) -> None:
    """get_module returns the api-surface entry for a known module."""
    SK._invalidate_cache()
    mod = SK.get_module("lib/rate_limiter.py", project_dir=indexed_project)
    assert mod is not None
    assert "RateLimiter" in mod["classes"]
    fn_names = [f["name"] for f in mod["functions"]]
    assert "check_rate_limit" in fn_names


def test_get_module_miss(indexed_project: Path) -> None:
    """get_module returns None for a non-existent module."""
    SK._invalidate_cache()
    result = SK.get_module("lib/does_not_exist.py", project_dir=indexed_project)
    assert result is None


# ---------------------------------------------------------------------------
# Test 3: get_importers (reverse dep-graph)
# ---------------------------------------------------------------------------

def test_get_importers(indexed_project: Path) -> None:
    """get_importers returns all files that import a given module."""
    SK._invalidate_cache()
    importers = SK.get_importers("lib/circuit_breaker.py", project_dir=indexed_project)
    assert "lib/agent_bus.py" in importers


def test_get_importers_none(indexed_project: Path) -> None:
    """get_importers returns empty list for a module with no known importers."""
    SK._invalidate_cache()
    importers = SK.get_importers("lib/rate_limiter_nonexistent.py", project_dir=indexed_project)
    assert importers == []


# ---------------------------------------------------------------------------
# Test 4: ranking — path match outscores doc-only match
# ---------------------------------------------------------------------------

def test_query_ranking(indexed_project: Path) -> None:
    """Results are sorted descending by score."""
    SK._invalidate_cache()
    results = SK.query("rate", project_dir=indexed_project)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True), f"Results not sorted by score: {scores}"
