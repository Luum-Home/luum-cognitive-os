"""Unit tests for lib/query_tailored_context.select_context (ADR-040).

Scenarios:
1. Semantic query matches relevant code.
2. max_chunks is respected.
3. Empty query returns empty list.
4. max_chunks < 1 raises ValueError.
5. Unrelated query does not surface rate-limiter content.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.query_tailored_context import select_context  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def minimal_project(tmp_path: Path) -> Path:
    """Create a minimal project structure with a code index and ADRs."""
    # ADRs
    adrs = tmp_path / "docs" / "02-Decisions" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-028-rate-limiter.md").write_text(
        "# ADR-028 — Rate Limiter\n\n"
        "Controls agent bash_command call frequency. "
        "lib/rate_limiter.py is the primary implementation.\n"
    )
    (adrs / "ADR-001-ui-components.md").write_text(
        "# ADR-001 — UI Components\n\n"
        "Frontend React component library and styling decisions.\n"
    )

    # Jaccard code index
    cos = tmp_path / ".cognitive-os"
    cos.mkdir()
    index_items = [
        {
            "path": "lib/rate_limiter.py",
            "kind": "python",
            "tokens": ["rate", "limiter", "quota", "minute", "window", "bucket", "throttle"],
            "docstring_excerpt": "Rate limiter: per-minute quota enforcement for bash_command calls.",
        },
        {
            "path": "lib/dispatch.py",
            "kind": "python",
            "tokens": ["dispatch", "llm", "provider", "qwen", "claude", "route", "fallback"],
            "docstring_excerpt": "LLM dispatch: routes prompts to Qwen/Claude based on quota.",
        },
        {
            "path": "lib/ui_renderer.py",
            "kind": "python",
            "tokens": ["ui", "renderer", "component", "frontend", "react", "render", "page"],
            "docstring_excerpt": "UI renderer: React component rendering helper.",
        },
    ]
    (cos / "reinvention-index.json").write_text(
        json.dumps({"version": 1, "items": index_items})
    )

    # Empty debt register
    (cos / "debt-register.jsonl").write_text("")

    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSelectContext:
    """Tests for select_context()."""

    def test_semantic_query_matches_relevant_code(self, minimal_project: Path) -> None:
        """Query 'rate limiter throttling' should surface rate_limiter content."""
        chunks = select_context(
            "rate limiter throttling quota",
            max_chunks=5,
            project_root=minimal_project,
        )

        assert chunks, "Expected at least one match for rate-limiter query"
        files = [c["file"] for c in chunks]
        assert any("rate" in f.lower() or "rate_limiter" in f.lower() for f in files), (
            f"Expected rate_limiter or rate-related file in results, got: {files}"
        )

    def test_max_chunks_respected(self, minimal_project: Path) -> None:
        """Result list must not exceed max_chunks."""
        for limit in (1, 2, 3):
            chunks = select_context(
                "rate limiter quota dispatch ui renderer",
                max_chunks=limit,
                project_root=minimal_project,
            )
            assert len(chunks) <= limit, (
                f"Expected <= {limit} chunks, got {len(chunks)}"
            )

    def test_empty_query_returns_empty_list(self, minimal_project: Path) -> None:
        """Empty or whitespace-only query must return []."""
        assert select_context("", project_root=minimal_project) == []
        assert select_context("   ", project_root=minimal_project) == []

    def test_invalid_max_chunks_raises(self, minimal_project: Path) -> None:
        """max_chunks < 1 must raise ValueError."""
        with pytest.raises(ValueError, match="max_chunks"):
            select_context("any query", max_chunks=0, project_root=minimal_project)
        with pytest.raises(ValueError, match="max_chunks"):
            select_context("any query", max_chunks=-1, project_root=minimal_project)

    def test_chunk_schema_fields_present(self, minimal_project: Path) -> None:
        """Each returned chunk must have file, lineno, content_snippet, score."""
        chunks = select_context(
            "rate limiter",
            max_chunks=3,
            project_root=minimal_project,
        )
        for chunk in chunks:
            assert "file" in chunk, f"Missing 'file' key: {chunk}"
            assert "lineno" in chunk, f"Missing 'lineno' key: {chunk}"
            assert "content_snippet" in chunk, f"Missing 'content_snippet' key: {chunk}"
            assert "score" in chunk, f"Missing 'score' key: {chunk}"
            assert isinstance(chunk["score"], float), f"score should be float: {chunk}"
            assert 0.0 <= chunk["score"] <= 1.0, f"score out of range: {chunk}"

    def test_unrelated_query_no_rate_limiter(self, minimal_project: Path) -> None:
        """Query about UI rendering should not surface rate-limiter content."""
        chunks = select_context(
            "frontend component page render",
            max_chunks=2,
            project_root=minimal_project,
        )
        files = [c["file"] for c in chunks]
        # rate_limiter.py must not be the top hit for a UI query
        if files:
            assert "rate_limiter" not in files[0].lower(), (
                f"rate_limiter was top hit for UI query, unexpected: {files}"
            )
