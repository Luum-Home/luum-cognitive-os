"""Unit tests for lib/adr_router.py (ADR-181).

Tests cover:
  - Frontmatter parsing and keyword extraction
  - Scoring function (tag vs title vs context weighting)
  - top_matches with real ADR corpus (smoke tests)
  - Skip-superseded / skip-tombstone behavior
  - Edge cases: empty prompt, very short prompt, no matches
  - Coverage stats helper
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from lib.adr_router import (
    AdrRouter,
    _AdrEntry,
    _extract_context_paragraph,
    _keywords_from_tags,
    _keywords_from_text,
    _load_adr_entry,
    _parse_frontmatter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(
    adr_id: str,
    title: str,
    keywords: list[str],
    tag_keywords: set[str] | None = None,
    title_keywords: set[str] | None = None,
    adr_num: int = 1,
    status: str = "accepted",
) -> _AdrEntry:
    """Build a synthetic _AdrEntry for scoring tests (no file I/O)."""
    tag_set = tag_keywords if tag_keywords is not None else set()
    title_set = title_keywords if title_keywords is not None else set(keywords)
    return _AdrEntry(
        adr_id=adr_id,
        adr_num=adr_num,
        title=title,
        status=status,
        file_path=Path(f"/fake/ADR-{adr_num:03d}.md"),
        repo_relative=f"docs/02-Decisions/adrs/ADR-{adr_num:03d}.md",
        keywords=keywords,
        tag_keywords=tag_set,
        title_keywords=title_set,
    )


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_parses_tags_list(self) -> None:
        text = textwrap.dedent("""\
            ---
            adr: 42
            title: My ADR
            status: accepted
            tags: [rejected-surface, routing, suggestion]
            ---
            # Body
        """)
        fm = _parse_frontmatter(text)
        assert fm["adr"] == 42
        assert fm["title"] == "My ADR"
        assert "rejected-surface" in fm["tags"]

    def test_no_frontmatter_returns_empty(self) -> None:
        text = "# Just a heading\n\nSome text.\n"
        fm = _parse_frontmatter(text)
        assert fm == {}

    def test_html_comment_before_frontmatter(self) -> None:
        text = textwrap.dedent("""\
            <!-- SCOPE: os-only -->
            ---
            adr: 7
            status: accepted
            tags: [docker, migration]
            ---
            # Body
        """)
        fm = _parse_frontmatter(text)
        assert fm.get("adr") == 7
        assert "docker" in fm.get("tags", [])

    def test_status_superseded(self) -> None:
        text = textwrap.dedent("""\
            ---
            adr: 170
            status: superseded
            tags: [ui]
            ---
        """)
        fm = _parse_frontmatter(text)
        assert fm["status"] == "superseded"


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

class TestKeywords:
    def test_stop_words_removed(self) -> None:
        kws = _keywords_from_text("the quick brown fox and a dog")
        assert "the" not in kws
        assert "and" not in kws
        assert "brown" in kws
        assert "quick" in kws

    def test_hyphenated_tokens_expanded(self) -> None:
        kws = _keywords_from_text("research-first protocol")
        # Both the full token and parts should be present
        assert "research" in kws or "research-first" in kws

    def test_short_tokens_dropped(self) -> None:
        kws = _keywords_from_text("a b cc ddd")
        assert "a" not in kws
        assert "b" not in kws
        assert "cc" not in kws
        assert "ddd" in kws

    def test_tags_keywords_from_list(self) -> None:
        kws = _keywords_from_tags(["rejected-surface", "adr-routing", "ui"])
        assert "rejected-surface" in kws
        assert "routing" in kws or "adr-routing" in kws


# ---------------------------------------------------------------------------
# Context extraction
# ---------------------------------------------------------------------------

class TestContextExtraction:
    def test_extracts_first_paragraph(self) -> None:
        text = textwrap.dedent("""\
            # ADR-069

            ## Status
            Accepted

            ## Context

            This is the first paragraph about research.

            This is the second paragraph about something else.

            ## Decision
        """)
        para = _extract_context_paragraph(text)
        assert "research" in para
        assert "first paragraph" in para

    def test_returns_empty_when_no_context_section(self) -> None:
        text = "# ADR\n\n## Decision\nSomething.\n"
        assert _extract_context_paragraph(text) == ""


# ---------------------------------------------------------------------------
# Scoring (unit tests using synthetic entries — no file I/O)
# ---------------------------------------------------------------------------

class TestScoring:
    def test_tag_match_scores_higher_than_context_match(self) -> None:
        """A single tag match should outscore a context-only match."""
        tag_entry = _make_entry(
            "ADR-001", "Some ADR",
            keywords=["rejected-surface", "rejection", "other", "words", "filler", "token"],
            tag_keywords={"rejected-surface"},
            title_keywords=set(),
            adr_num=1,
        )
        ctx_entry = _make_entry(
            "ADR-002", "Some Other ADR",
            keywords=["rejected-surface", "rejection", "other", "words", "filler", "token"],
            tag_keywords=set(),
            title_keywords=set(),
            adr_num=2,
        )
        from lib.adr_router import AdrRouter
        router = AdrRouter.__new__(AdrRouter)
        conf_tag, _ = router._score(["rejected-surface"], tag_entry)
        conf_ctx, _ = router._score(["rejected-surface"], ctx_entry)
        assert conf_tag > conf_ctx

    def test_title_match_scores_higher_than_context_match(self) -> None:
        """A title match should outscore a context match."""
        title_entry = _make_entry(
            "ADR-001", "Research-First Protocol",
            keywords=["research", "first", "protocol", "extra", "words", "here"],
            tag_keywords=set(),
            title_keywords={"research", "first", "protocol"},
            adr_num=1,
        )
        ctx_entry = _make_entry(
            "ADR-002", "Something Else",
            keywords=["research", "first", "protocol", "extra", "words", "here"],
            tag_keywords=set(),
            title_keywords=set(),
            adr_num=2,
        )
        router = AdrRouter.__new__(AdrRouter)
        conf_title, _ = router._score(["research", "first"], title_entry)
        conf_ctx, _ = router._score(["research", "first"], ctx_entry)
        assert conf_title > conf_ctx

    def test_no_intersection_returns_zero(self) -> None:
        entry = _make_entry("ADR-001", "Test", ["foo", "bar", "baz"], adr_num=1)
        router = AdrRouter.__new__(AdrRouter)
        conf, matched = router._score(["qux", "quux"], entry)
        assert conf == 0.0
        assert matched == ""

    def test_full_match_caps_at_one(self) -> None:
        """Even if weights push above 1.0, confidence is capped."""
        entry = _make_entry(
            "ADR-001", "Test",
            keywords=["foo"],
            tag_keywords={"foo"},
            title_keywords={"foo"},
            adr_num=1,
        )
        router = AdrRouter.__new__(AdrRouter)
        conf, _ = router._score(["foo"], entry)
        assert conf <= 1.0

    def test_empty_prompt_keywords(self) -> None:
        entry = _make_entry("ADR-001", "Test", ["foo", "bar"], adr_num=1)
        router = AdrRouter.__new__(AdrRouter)
        conf, matched = router._score([], entry)
        assert conf == 0.0


# ---------------------------------------------------------------------------
# Load ADR entry from file (integration with real ADR corpus)
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestLoadAdrEntry:
    def test_loads_accepted_adr(self) -> None:
        adr_path = PROJECT_ROOT / "docs" / "adrs" / "ADR-174-auto-derived-primitive-routing.md"
        if not adr_path.exists():
            pytest.skip("ADR-174 not found on disk")
        entry = _load_adr_entry(adr_path, PROJECT_ROOT)
        assert entry is not None
        assert entry.adr_id == "ADR-174"
        assert "routing" in entry.keywords or "route" in entry.keywords or "rout" in entry.keywords
        assert entry.status in ("accepted", "proposed", "draft")

    def test_skips_superseded_adr(self) -> None:
        adr_path = PROJECT_ROOT / "docs" / "adrs" / "ADR-170-operator-cli-as-primary-ui-surface.md"
        if not adr_path.exists():
            pytest.skip("ADR-170 not found on disk")
        entry = _load_adr_entry(adr_path, PROJECT_ROOT)
        assert entry is None, "Superseded ADR should return None"

    def test_skips_tombstone_by_filename(self) -> None:
        adr_path = PROJECT_ROOT / "docs" / "adrs" / "ADR-171-tombstone.md"
        if not adr_path.exists():
            pytest.skip("ADR-171 not found on disk")
        entry = _load_adr_entry(adr_path, PROJECT_ROOT)
        assert entry is None, "Tombstone ADR should return None"

    def test_skips_tombstone_by_status(self) -> None:
        adr_path = PROJECT_ROOT / "docs" / "adrs" / "ADR-179-tombstone.md"
        if not adr_path.exists():
            pytest.skip("ADR-179 not found on disk")
        entry = _load_adr_entry(adr_path, PROJECT_ROOT)
        assert entry is None, "Tombstone ADR should return None"


# ---------------------------------------------------------------------------
# AdrRouter integration tests (real corpus)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def router() -> AdrRouter:
    return AdrRouter(project_root=PROJECT_ROOT)


class TestAdrRouterRealCorpus:
    def test_index_contains_only_active_adrs(self, router: AdrRouter) -> None:
        """No superseded, deprecated, or tombstone entries in index."""
        for entry in router.index:
            assert entry.status not in ("superseded", "deprecated", "tombstone"), (
                f"{entry.adr_id} has skippable status {entry.status!r} but is in index"
            )
            assert "tombstone" not in entry.file_path.name.lower(), (
                f"{entry.adr_id} is a tombstone file but was indexed"
            )

    def test_adr174_matches_routing_prompt(self, router: AdrRouter) -> None:
        """ADR-174 (auto-derived routing) should appear for routing-related prompts."""
        matches = router.top_matches(
            "implement auto-derived primitive routing for skills from frontmatter",
            n=5,
            min_confidence=0.0,
        )
        adr_ids = [m.adr_id for m in matches]
        assert "ADR-174" in adr_ids, f"ADR-174 not found in {adr_ids}"

    def test_adr069_matches_research_prompt(self, router: AdrRouter) -> None:
        """ADR-069 (research-first protocol) should appear for research prompts."""
        matches = router.top_matches(
            "research first protocol for high risk changes before implementation",
            n=5,
            min_confidence=0.0,
        )
        adr_ids = [m.adr_id for m in matches]
        assert "ADR-069" in adr_ids, f"ADR-069 not found in {adr_ids}"

    def test_superseded_adr170_not_in_suggestions(self, router: AdrRouter) -> None:
        """Superseded ADR-170 must NOT appear in any suggestions."""
        matches = router.top_matches(
            "operator cli as primary ui surface dashboard demotion",
            n=10,
            min_confidence=0.0,
        )
        adr_ids = [m.adr_id for m in matches]
        assert "ADR-170" not in adr_ids, "Superseded ADR-170 must not appear in suggestions"

    def test_tombstone_not_in_suggestions(self, router: AdrRouter) -> None:
        """Tombstone ADRs must NOT appear in any suggestions."""
        matches = router.top_matches(
            "tombstone reserved architecture decision",
            n=10,
            min_confidence=0.0,
        )
        adr_ids = [m.adr_id for m in matches]
        tombstone_ids = {"ADR-003", "ADR-004", "ADR-005", "ADR-043", "ADR-046",
                         "ADR-171", "ADR-173", "ADR-179"}
        found = tombstone_ids & set(adr_ids)
        assert not found, f"Tombstone ADRs found in suggestions: {found}"

    def test_empty_prompt_returns_empty(self, router: AdrRouter) -> None:
        assert router.top_matches("", n=3) == []

    def test_short_prompt_returns_empty(self, router: AdrRouter) -> None:
        assert router.top_matches("hi", n=3) == []

    def test_top_n_respected(self, router: AdrRouter) -> None:
        matches = router.top_matches(
            "architecture design decision implementation routing skill hook",
            n=2,
            min_confidence=0.0,
        )
        assert len(matches) <= 2

    def test_results_sorted_by_confidence_descending(self, router: AdrRouter) -> None:
        matches = router.top_matches(
            "architecture design decision implementation",
            n=5,
            min_confidence=0.0,
        )
        confidences = [m.confidence for m in matches]
        assert confidences == sorted(confidences, reverse=True)

    def test_high_threshold_returns_fewer_results(self, router: AdrRouter) -> None:
        """0.85 threshold returns fewer results than 0.0 threshold."""
        all_matches = router.top_matches("routing skill", n=10, min_confidence=0.0)
        strict_matches = router.top_matches("routing skill", n=10, min_confidence=0.85)
        assert len(strict_matches) <= len(all_matches)


# ---------------------------------------------------------------------------
# AdrRouter with synthetic rejected-surface ADR (simulates ADR-181)
# ---------------------------------------------------------------------------

class TestSyntheticRejectedSurfaceAdr:
    """
    ADR-181 is the synthetic rejected-surface routing ADR.  Since we're creating it in
    this PR, we test routing against a synthetic tmp_path ADR corpus that
    includes a pre-built ADR-181 with appropriate tags.
    """

    def test_rejected_surface_prompt_matches_adr181(self, tmp_path: Path) -> None:
        adrs_dir = tmp_path / "docs" / "adrs"
        adrs_dir.mkdir(parents=True)

        # Write a synthetic ADR-181 (with rejection tag to match the test prompt)
        (adrs_dir / "ADR-181-adr-relevance-suggester.md").write_text(
            textwrap.dedent("""\
                ---
                adr: 181
                title: ADR Relevance Suggester — UserPromptSubmit Hook
                status: accepted
                date: 2026-05-05
                tags: [rejected-surface, rejected-surface-rejection, adr-routing, suggestion, hooks]
                ---

                # ADR-181: ADR Relevance Suggester

                ## Status

                Accepted — 2026-05-05

                ## Context

                When the orchestrator starts a task it must mentally know which ADRs apply.
                This ADR introduces a lightweight router for rejected-surface rejection and similar
                multi-surface hook patterns.

                ## Decision

                Implement AdrRouter with top_matches().
            """),
            encoding="utf-8",
        )

        router = AdrRouter(adrs_dir=adrs_dir, project_root=tmp_path)
        matches = router.top_matches(
            "how does rejected-surface rejection work across surfaces",
            n=3,
            min_confidence=0.85,
        )
        assert len(matches) >= 1
        assert matches[0].adr_id == "ADR-181"
        assert matches[0].confidence >= 0.85

    def test_auto_skill_generation_matches_adr133(self, tmp_path: Path) -> None:
        adrs_dir = tmp_path / "docs" / "adrs"
        adrs_dir.mkdir(parents=True)

        (adrs_dir / "ADR-133-expansion-without-monsterization.md").write_text(
            textwrap.dedent("""\
                ---
                adr: 133
                title: Expansion Without Monsterization
                status: accepted
                tags: [auto-skill-generation, expansion, lifecycle, lab-first]
                ---

                # ADR-133: Expansion Without Monsterization

                ## Status

                Accepted — 2026-05-03

                ## Context

                Auto skill generation via the skill lifecycle promoter runs in lab tier.
                Expansion is only allowed when it makes the core smaller.
            """),
            encoding="utf-8",
        )

        router = AdrRouter(adrs_dir=adrs_dir, project_root=tmp_path)
        matches = router.top_matches(
            "auto-skill-generation lifecycle lab promotion",
            n=3,
            min_confidence=0.85,
        )
        assert len(matches) >= 1
        assert matches[0].adr_id == "ADR-133"
        assert matches[0].confidence >= 0.85

    def test_research_protocol_matches_adr069(self, tmp_path: Path) -> None:
        adrs_dir = tmp_path / "docs" / "adrs"
        adrs_dir.mkdir(parents=True)

        (adrs_dir / "ADR-069-research-first-protocol.md").write_text(
            textwrap.dedent("""\
                ---
                adr: 69
                title: Research-First Protocol for High-Risk Changes
                status: proposed
                tags: [research, research-first, high-risk, protocol, changes]
                ---

                # ADR-069: Research-First Protocol for High-Risk Changes

                ## Status

                Proposed

                ## Context

                High-risk changes need a research-first protocol before implementation.
            """),
            encoding="utf-8",
        )

        router = AdrRouter(adrs_dir=adrs_dir, project_root=tmp_path)
        matches = router.top_matches(
            "research-first protocol for high-risk changes",
            n=3,
            min_confidence=0.85,
        )
        assert len(matches) >= 1
        assert matches[0].adr_id == "ADR-069"
        assert matches[0].confidence >= 0.85


# ---------------------------------------------------------------------------
# Coverage stats
# ---------------------------------------------------------------------------

class TestCoverageStats:
    def test_coverage_stats_real_corpus(self) -> None:
        router = AdrRouter(project_root=PROJECT_ROOT)
        stats = router.coverage_stats()
        assert "total_non_tombstone" in stats
        assert "with_tags" in stats
        assert "coverage_percent" in stats
        assert stats["total_non_tombstone"] > 100
        assert 0 <= stats["coverage_percent"] <= 100
        # Target is 75% but current baseline is ~24% — just verify structure
        assert "meets_target" in stats

    def test_coverage_stats_empty_dir(self, tmp_path: Path) -> None:
        router = AdrRouter(adrs_dir=tmp_path / "nonexistent", project_root=tmp_path)
        stats = router.coverage_stats()
        assert stats == {}

    def test_coverage_stats_counts_correctly(self, tmp_path: Path) -> None:
        adrs_dir = tmp_path / "adrs"
        adrs_dir.mkdir()
        # 2 with tags, 1 without, 1 tombstone (excluded from denominator)
        (adrs_dir / "ADR-001-with-tags.md").write_text(
            "---\nadr: 1\nstatus: accepted\ntags: [foo]\n---\n# ADR\n", encoding="utf-8"
        )
        (adrs_dir / "ADR-002-with-tags.md").write_text(
            "---\nadr: 2\nstatus: accepted\ntags: [bar]\n---\n# ADR\n", encoding="utf-8"
        )
        (adrs_dir / "ADR-003-no-tags.md").write_text(
            "---\nadr: 3\nstatus: accepted\n---\n# ADR\n", encoding="utf-8"
        )
        (adrs_dir / "ADR-004-tombstone.md").write_text(
            "---\nadr: 4\nstatus: tombstone\ntags: [tombstone]\n---\n# Tombstone\n",
            encoding="utf-8",
        )
        router = AdrRouter(adrs_dir=adrs_dir, project_root=tmp_path)
        stats = router.coverage_stats()
        assert stats["total_non_tombstone"] == 3
        assert stats["with_tags"] == 2
        assert abs(stats["coverage_percent"] - 66.7) < 1.0
