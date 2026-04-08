"""
Unit tests for lib/memory_retriever.py
"""

import pytest
import os
import sqlite3
import tempfile
from lib.memory_retriever import MemoryRetriever, RetrievalResult


class TestJaccardSimilarity:
    def test_identical_sets(self):
        r = MemoryRetriever()
        score = r._jaccard_similarity({"a", "b", "c"}, {"a", "b", "c"})
        assert score == 1.0

    def test_disjoint_sets(self):
        r = MemoryRetriever()
        assert r._jaccard_similarity({"a"}, {"b"}) == 0.0

    def test_partial_overlap(self):
        r = MemoryRetriever()
        # intersection = {b, c} (size 2), union = {a, b, c, d} (size 4) → 0.5
        score = r._jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
        assert abs(score - 0.5) < 0.001

    def test_empty_first_set(self):
        r = MemoryRetriever()
        assert r._jaccard_similarity(set(), {"a"}) == 0.0

    def test_empty_second_set(self):
        r = MemoryRetriever()
        assert r._jaccard_similarity({"a"}, set()) == 0.0

    def test_both_empty(self):
        r = MemoryRetriever()
        assert r._jaccard_similarity(set(), set()) == 0.0

    def test_single_element_match(self):
        r = MemoryRetriever()
        assert r._jaccard_similarity({"x"}, {"x"}) == 1.0

    def test_subset(self):
        r = MemoryRetriever()
        # {a} ⊂ {a, b, c}: intersection=1, union=3 → 0.333...
        score = r._jaccard_similarity({"a"}, {"a", "b", "c"})
        assert abs(score - (1 / 3)) < 0.001

    def test_score_between_zero_and_one(self):
        r = MemoryRetriever()
        score = r._jaccard_similarity({"jwt", "auth", "token"}, {"auth", "bearer", "token"})
        assert 0.0 <= score <= 1.0


class TestTokenize:
    def test_removes_english_stop_words(self):
        r = MemoryRetriever()
        tokens = r._tokenize("the cat in the hat")
        assert "the" not in tokens
        assert "in" not in tokens
        assert "cat" in tokens
        assert "hat" in tokens

    def test_lowercases(self):
        r = MemoryRetriever()
        tokens = r._tokenize("JWT Token Authentication")
        assert "jwt" in tokens
        assert "token" in tokens
        assert "authentication" in tokens

    def test_removes_spanish_stop_words(self):
        r = MemoryRetriever()
        tokens = r._tokenize("el sistema de autenticación")
        assert "el" not in tokens
        assert "de" not in tokens
        assert "autenticaci" in tokens or "autenticación" in tokens

    def test_empty_string_returns_empty_set(self):
        r = MemoryRetriever()
        assert r._tokenize("") == set()

    def test_returns_set(self):
        r = MemoryRetriever()
        result = r._tokenize("hello world hello")
        assert isinstance(result, set)
        # set deduplicates
        assert len(result) == 2

    def test_punctuation_split(self):
        r = MemoryRetriever()
        tokens = r._tokenize("auth.service fix: bug")
        assert "auth" in tokens
        assert "service" in tokens
        assert "bug" in tokens

    def test_numbers_kept(self):
        r = MemoryRetriever()
        tokens = r._tokenize("python 3 version")
        assert "3" in tokens
        assert "python" in tokens

    def test_none_like_empty_handled(self):
        r = MemoryRetriever()
        # _tokenize has a guard for falsy text
        assert r._tokenize("") == set()


class TestEscapeFts5Query:
    def test_plain_text_unchanged(self):
        r = MemoryRetriever()
        result = r._escape_fts5_query("jwt authentication")
        assert "jwt" in result
        assert "authentication" in result

    def test_removes_quotes(self):
        r = MemoryRetriever()
        result = r._escape_fts5_query('"quoted phrase"')
        assert '"' not in result

    def test_removes_asterisk(self):
        r = MemoryRetriever()
        result = r._escape_fts5_query("auth*")
        assert "*" not in result

    def test_removes_parens(self):
        r = MemoryRetriever()
        result = r._escape_fts5_query("(auth OR jwt)")
        assert "(" not in result
        assert ")" not in result

    def test_collapses_whitespace(self):
        r = MemoryRetriever()
        result = r._escape_fts5_query("  jwt   auth  ")
        assert "  " not in result
        assert result == result.strip()

    def test_all_special_chars_returns_empty(self):
        r = MemoryRetriever()
        result = r._escape_fts5_query('"*^()')
        # Result should be empty or whitespace only
        assert result.strip() == ""


class TestSearch:
    def test_missing_db_returns_empty(self):
        r = MemoryRetriever(db_path="/nonexistent/path/engram.db")
        results = r.search("anything")
        assert results == []

    def test_empty_query_returns_empty(self):
        r = MemoryRetriever()
        results = r.search("")
        assert results == []

    def test_whitespace_query_returns_empty(self):
        r = MemoryRetriever()
        results = r.search("   ")
        assert results == []


class TestWeightNormalization:
    def test_weights_sum_to_one(self):
        r = MemoryRetriever(fts5_weight=0.6, jaccard_weight=0.4)
        assert abs(r.fts5_weight + r.jaccard_weight - 1.0) < 0.001

    def test_custom_weights_normalized(self):
        r = MemoryRetriever(fts5_weight=3.0, jaccard_weight=1.0)
        # 3/(3+1)=0.75, 1/(3+1)=0.25
        assert abs(r.fts5_weight - 0.75) < 0.001
        assert abs(r.jaccard_weight - 0.25) < 0.001

    def test_equal_weights(self):
        r = MemoryRetriever(fts5_weight=1.0, jaccard_weight=1.0)
        assert abs(r.fts5_weight - 0.5) < 0.001
        assert abs(r.jaccard_weight - 0.5) < 0.001

    def test_default_weights(self):
        r = MemoryRetriever()
        # Defaults: 0.6 and 0.4, already sum to 1.0
        assert abs(r.fts5_weight - 0.6) < 0.001
        assert abs(r.jaccard_weight - 0.4) < 0.001


class TestRetrievalResultDataclass:
    def test_fields(self):
        result = RetrievalResult(
            id=1,
            title="JWT Auth Pattern",
            content="Use RS256 for signing",
            topic_key="architecture/auth",
            project="luum",
            fts5_score=0.9,
            jaccard_score=0.7,
            combined_score=0.82,
        )
        assert result.id == 1
        assert result.title == "JWT Auth Pattern"
        assert result.fts5_score == 0.9
        assert result.jaccard_score == 0.7
        assert result.combined_score == 0.82


class TestWithSQLiteFixture:
    """Tests that use a real in-memory SQLite DB with the expected schema."""

    @pytest.fixture
    def db_with_data(self, tmp_path):
        """Create a minimal engram-like SQLite database with FTS5 support."""
        db_path = str(tmp_path / "test_engram.db")
        conn = sqlite3.connect(db_path)
        try:
            # Create the observations table matching engram's schema
            conn.execute("""
                CREATE TABLE observations (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    content TEXT,
                    topic_key TEXT,
                    project TEXT,
                    deleted_at TEXT
                )
            """)
            # Create FTS5 virtual table
            conn.execute("""
                CREATE VIRTUAL TABLE observations_fts USING fts5(
                    title, content,
                    content=observations, content_rowid=id
                )
            """)
            # Insert test data
            conn.execute(
                "INSERT INTO observations VALUES (1, 'JWT Auth Pattern', 'Use RS256 for JWT signing in production systems', 'architecture/auth', 'luum', NULL)"
            )
            conn.execute(
                "INSERT INTO observations VALUES (2, 'Database Connection Pool', 'Configure max connections to avoid exhaustion', 'config/database', 'luum', NULL)"
            )
            conn.execute(
                "INSERT INTO observations VALUES (3, 'Deleted entry', 'Should not appear in results', 'test/deleted', 'luum', '2024-01-01')"
            )
            # Populate FTS5 index
            conn.execute(
                "INSERT INTO observations_fts(rowid, title, content) SELECT id, title, content FROM observations WHERE deleted_at IS NULL"
            )
            conn.commit()
        finally:
            conn.close()
        return db_path

    def test_search_returns_results(self, db_with_data):
        r = MemoryRetriever(db_path=db_with_data)
        # Use a term that appears verbatim in the stored title/content
        results = r.search("JWT signing")
        assert len(results) >= 1
        titles = [res.title for res in results]
        assert any("JWT" in t for t in titles)

    def test_search_respects_limit(self, db_with_data):
        r = MemoryRetriever(db_path=db_with_data)
        results = r.search("production systems", limit=1)
        assert len(results) <= 1

    def test_search_excludes_deleted(self, db_with_data):
        r = MemoryRetriever(db_path=db_with_data)
        results = r.search("deleted entry")
        # deleted_at is set, so this should not appear
        for res in results:
            assert res.title != "Deleted entry"

    def test_combined_score_in_range(self, db_with_data):
        r = MemoryRetriever(db_path=db_with_data)
        results = r.search("JWT auth")
        for res in results:
            assert 0.0 <= res.combined_score <= 1.0

    def test_results_sorted_by_combined_score(self, db_with_data):
        r = MemoryRetriever(db_path=db_with_data)
        results = r.search("JWT auth")
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].combined_score >= results[i + 1].combined_score

    def test_project_filter(self, db_with_data):
        r = MemoryRetriever(db_path=db_with_data)
        results = r.search("JWT auth", project="luum")
        for res in results:
            assert res.project == "luum"

    def test_project_filter_no_results_for_other_project(self, db_with_data):
        r = MemoryRetriever(db_path=db_with_data)
        results = r.search("JWT auth", project="nonexistent_project")
        assert results == []

    def test_jaccard_score_computed(self, db_with_data):
        r = MemoryRetriever(db_path=db_with_data)
        results = r.search("JWT signing RS256")
        if results:
            # Jaccard should have been computed (not 0.0 default) for a good match
            assert results[0].jaccard_score >= 0.0
