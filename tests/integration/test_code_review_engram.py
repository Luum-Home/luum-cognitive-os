"""Integration tests for code review <-> engram bidirectional integration.

Validates:
- search_past_reviews_from_engram returns list format
- save_review_to_engram creates engram-compatible data
- Review of a file with known patterns produces findings
- Adversarial protocol: always at least 1 finding
- Full review_with_engram lifecycle

These tests use mock callables that mimic engram MCP tool signatures
so they run without a live engram connection.
"""

import textwrap
from typing import Any, Dict, List

import pytest

from lib.code_reviewer import (
    CodeReviewer,
    ReviewFinding,
    ReviewReport,
    ReviewStatus,
    Severity,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


def _make_temp_file(tmp_path, name: str, content: str) -> str:
    """Create a temp file and return its path relative to tmp_path."""
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return name


class FakeEngram:
    """In-memory engram replacement for testing.

    Stores observations in a list and supports search/get/save with
    the same keyword-arg signatures as the real MCP tools.
    """

    def __init__(self):
        self.observations: List[Dict[str, Any]] = []
        self._next_id = 1

    def mem_save(self, *, title: str = "", content: str = "", type: str = "",
                 topic_key: str = "", scope: str = "", project: str = "") -> dict:
        obs = {
            "id": self._next_id,
            "title": title,
            "content": content,
            "type": type,
            "topic_key": topic_key,
            "scope": scope,
            "project": project,
        }
        self._next_id += 1
        self.observations.append(obs)
        return obs

    def mem_search(self, *, query: str = "", project: str = "", limit: int = 5) -> list:
        results = []
        for obs in self.observations:
            if query.lower() in obs.get("topic_key", "").lower() or \
               query.lower() in obs.get("title", "").lower() or \
               query.lower() in obs.get("content", "").lower():
                results.append(obs)
        return results[:limit]

    def mem_get_observation(self, *, id: int) -> dict:
        for obs in self.observations:
            if obs["id"] == id:
                return obs
        return {}


@pytest.fixture
def fake_engram():
    return FakeEngram()


@pytest.fixture
def reviewer(tmp_path):
    return CodeReviewer(project_root=str(tmp_path))


# ---------------------------------------------------------------------------
# Test: search_past_reviews_from_engram returns list format
# ---------------------------------------------------------------------------


class TestSearchPastReviewsFromEngram:
    """search_past_reviews_from_engram must return a list of dicts."""

    def test_returns_list_when_engram_available(self, tmp_path, reviewer, fake_engram):
        # Seed engram with a past review
        fake_engram.mem_save(
            title="Code review: users (PASSED)",
            content="Past review: no blockers, 2 suggestions",
            type="review",
            topic_key="review/users/2026-03-28",
            scope="project",
            project="test-proj",
        )

        _make_temp_file(tmp_path, "internal/users/handler.go", "package users")

        results = reviewer.search_past_reviews_from_engram(
            files=["internal/users/handler.go"],
            project="test-proj",
            mem_search_fn=fake_engram.mem_search,
            mem_get_fn=fake_engram.mem_get_observation,
        )

        assert isinstance(results, list)
        assert len(results) >= 1
        first = results[0]
        assert "service" in first
        assert "content" in first
        assert "id" in first
        assert first["service"] == "users"

    def test_returns_empty_list_without_engram(self, reviewer):
        results = reviewer.search_past_reviews_from_engram(
            files=["src/auth.py"],
            project="test-proj",
            mem_search_fn=None,
        )
        assert results == []

    def test_returns_empty_list_when_no_past_reviews(self, reviewer, fake_engram):
        results = reviewer.search_past_reviews_from_engram(
            files=["internal/payments/charge.go"],
            project="test-proj",
            mem_search_fn=fake_engram.mem_search,
            mem_get_fn=fake_engram.mem_get_observation,
        )
        assert results == []

    def test_deduplicates_services(self, tmp_path, reviewer, fake_engram):
        fake_engram.mem_save(
            title="Code review: users (PASSED)",
            content="stuff",
            type="review",
            topic_key="review/users/2026-03-28",
            scope="project",
            project="test-proj",
        )

        results = reviewer.search_past_reviews_from_engram(
            files=[
                "internal/users/handler.go",
                "internal/users/dto.go",
                "internal/users/mapper.go",
            ],
            project="test-proj",
            mem_search_fn=fake_engram.mem_search,
            mem_get_fn=fake_engram.mem_get_observation,
        )

        # All files are in the same service, so deduplication should
        # produce results from only one service query set
        services = {r["service"] for r in results}
        assert services == {"users"}

    def test_graceful_degradation_on_engram_error(self, reviewer):
        def broken_search(**kwargs):
            raise ConnectionError("engram down")

        results = reviewer.search_past_reviews_from_engram(
            files=["src/auth.py"],
            project="test-proj",
            mem_search_fn=broken_search,
        )
        assert results == []


# ---------------------------------------------------------------------------
# Test: save_review_to_engram creates engram-compatible data
# ---------------------------------------------------------------------------


class TestSaveReviewToEngram:
    """save_review_to_engram must produce a valid mem_save payload."""

    def test_creates_valid_payload(self, reviewer):
        report = ReviewReport(
            status=ReviewStatus.PASSED,
            findings=[
                ReviewFinding(
                    severity=Severity.SUGGESTION,
                    file="internal/users/handler.go",
                    line=10,
                    what="Consider adding error context",
                    why="Error messages lack context for debugging",
                    recommendation="Wrap errors with fmt.Errorf",
                )
            ],
            files_reviewed=1,
        )

        payload = reviewer.save_review_to_engram(report, project="test-proj", service="users")

        assert "title" in payload
        assert "content" in payload
        assert "topic_key" in payload
        assert "project" in payload
        assert payload["project"] == "test-proj"
        assert payload["topic_key"].startswith("review/")
        assert "users" in payload["topic_key"]
        assert "SUGGESTION" in payload["content"]

    def test_calls_mem_save_when_fn_provided(self, reviewer, fake_engram):
        report = ReviewReport(
            status=ReviewStatus.FAILED,
            findings=[
                ReviewFinding(
                    severity=Severity.BLOCKER,
                    file="src/auth.py",
                    line=42,
                    what="Hardcoded password",
                    why="Security risk",
                    recommendation="Use env var",
                )
            ],
            files_reviewed=1,
        )

        reviewer.save_review_to_engram(
            report, project="test-proj", service="auth",
            mem_save_fn=fake_engram.mem_save,
        )

        assert len(fake_engram.observations) == 1
        saved = fake_engram.observations[0]
        assert saved["type"] == "review"
        assert saved["project"] == "test-proj"
        assert "BLOCKER" in saved["content"]

    def test_returns_payload_even_without_mem_save(self, reviewer):
        report = ReviewReport(
            status=ReviewStatus.PASSED,
            findings=[
                ReviewFinding(
                    severity=Severity.SUGGESTION,
                    file="lib/foo.py",
                    line=None,
                    what="Test coverage",
                    why="Missing tests",
                    recommendation="Add tests",
                )
            ],
            files_reviewed=1,
        )

        payload = reviewer.save_review_to_engram(report, project="test-proj")
        assert isinstance(payload, dict)
        assert "title" in payload
        assert "content" in payload

    def test_handles_change_name_in_topic_key(self, reviewer):
        report = ReviewReport(
            status=ReviewStatus.PASSED,
            findings=[
                ReviewFinding(
                    severity=Severity.SUGGESTION,
                    file="src/main.py",
                    line=None,
                    what="Minor style issue",
                    why="Readability",
                    recommendation="Fix style",
                )
            ],
            files_reviewed=1,
        )

        payload = reviewer.save_review_to_engram(
            report, project="test-proj", change_name="add-jwt-auth",
        )
        assert "add-jwt-auth" in payload["topic_key"]


# ---------------------------------------------------------------------------
# Test: Review of file with known patterns produces findings
# ---------------------------------------------------------------------------


class TestReviewWithKnownPatterns:
    """review_files must detect known security/quality/performance patterns."""

    def test_detects_hardcoded_password(self, tmp_path, reviewer):
        _make_temp_file(tmp_path, "src/config.py", textwrap.dedent("""\
            password = "super_secret_123"
            db_host = "localhost"
        """))

        report = reviewer.review_files(["src/config.py"])

        assert report.status == ReviewStatus.FAILED
        blocker_findings = [f for f in report.findings if f.severity == Severity.BLOCKER]
        assert len(blocker_findings) >= 1
        assert any("password" in f.what.lower() for f in blocker_findings)

    def test_detects_eval_usage(self, tmp_path, reviewer):
        _make_temp_file(tmp_path, "src/handler.py", textwrap.dedent("""\
            def handle(data):
                result = eval(data['expression'])
                return result
        """))

        report = reviewer.review_files(["src/handler.py"])
        eval_findings = [f for f in report.findings if "eval" in f.what.lower()]
        assert len(eval_findings) >= 1

    def test_detects_todo_comments(self, tmp_path, reviewer):
        _make_temp_file(tmp_path, "src/service.py", textwrap.dedent("""\
            def process():
                # TODO: implement proper error handling
                pass
        """))

        report = reviewer.review_files(["src/service.py"])
        todo_findings = [f for f in report.findings if "todo" in f.what.lower()]
        assert len(todo_findings) >= 1

    def test_detects_bare_except(self, tmp_path, reviewer):
        _make_temp_file(tmp_path, "src/handler.py", textwrap.dedent("""\
            try:
                do_work()
            except:
                pass
        """))

        report = reviewer.review_files(["src/handler.py"])
        except_findings = [f for f in report.findings if "except" in f.what.lower()]
        assert len(except_findings) >= 1


# ---------------------------------------------------------------------------
# Test: Adversarial protocol — always at least 1 finding
# ---------------------------------------------------------------------------


class TestAdversarialProtocol:
    """Per adversarial-review.md, every review MUST produce at least one finding."""

    def test_clean_file_still_has_finding(self, tmp_path, reviewer):
        _make_temp_file(tmp_path, "src/clean.py", textwrap.dedent("""\
            def add(a: int, b: int) -> int:
                return a + b
        """))

        report = reviewer.review_files(["src/clean.py"])

        assert len(report.findings) >= 1
        # The fallback finding should be a SUGGESTION
        assert any(f.severity == Severity.SUGGESTION for f in report.findings)

    def test_empty_diff_still_has_finding(self, reviewer):
        report = reviewer.review_diff("")
        assert len(report.findings) >= 1

    def test_missing_file_produces_question(self, reviewer):
        report = reviewer.review_files(["nonexistent/file.py"])
        assert len(report.findings) >= 1
        assert any(f.severity == Severity.QUESTION for f in report.findings)


# ---------------------------------------------------------------------------
# Test: Full review_with_engram lifecycle
# ---------------------------------------------------------------------------


class TestReviewWithEngram:
    """review_with_engram orchestrates the full bidirectional flow."""

    def test_full_lifecycle(self, tmp_path, reviewer, fake_engram):
        # Seed past review
        fake_engram.mem_save(
            title="Code review: users (PASSED)",
            content="Previous review had 2 suggestions about error handling",
            type="review",
            topic_key="review/users/2026-03-27",
            scope="project",
            project="test-proj",
        )

        _make_temp_file(tmp_path, "internal/users/handler.go", textwrap.dedent("""\
            package users
            // TODO: add proper validation
            func GetUser(id string) {}
        """))

        report = reviewer.review_with_engram(
            files=["internal/users/handler.go"],
            project="test-proj",
            context="Adding user endpoint",
            mem_search_fn=fake_engram.mem_search,
            mem_get_fn=fake_engram.mem_get_observation,
            mem_save_fn=fake_engram.mem_save,
        )

        # Report should reflect engram usage
        assert report.engram_context_used is True
        assert report.past_review_count >= 1

        # Findings should include the TODO detection
        assert len(report.findings) >= 1

        # A new review should have been saved to engram (original seed + new save)
        assert len(fake_engram.observations) >= 2

    def test_lifecycle_without_engram(self, tmp_path, reviewer):
        _make_temp_file(tmp_path, "src/app.py", "x = 1\n")

        report = reviewer.review_with_engram(
            files=["src/app.py"],
            project="test-proj",
        )

        assert report.engram_context_used is False
        assert report.past_review_count == 0
        assert len(report.findings) >= 1  # adversarial

    def test_lifecycle_saves_findings(self, tmp_path, reviewer, fake_engram):
        _make_temp_file(tmp_path, "internal/auth/login.py", textwrap.dedent("""\
            api_key = "sk-live-abc123def456"
            def login(user, password="admin"):
                pass
        """))

        report = reviewer.review_with_engram(
            files=["internal/auth/login.py"],
            project="test-proj",
            change_name="fix-auth",
            mem_search_fn=fake_engram.mem_search,
            mem_get_fn=fake_engram.mem_get_observation,
            mem_save_fn=fake_engram.mem_save,
        )

        assert report.status == ReviewStatus.FAILED  # has blockers
        # Verify engram received the review
        saved = [o for o in fake_engram.observations if o.get("type") == "review"]
        assert len(saved) >= 1
        assert "BLOCKER" in saved[-1]["content"]
