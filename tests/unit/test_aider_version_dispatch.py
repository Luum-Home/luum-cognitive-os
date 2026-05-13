"""Unit tests for Aider version dispatch hardening (ADR-033b).

Tests:
1. Correct parser per version (0.60 / 0.65 / 0.70)
2. Unsupported version raises UnsupportedAiderVersion
3. ParseError event emitted for unknown pattern lines
4. Fixture corpus round-trips (all 3 fixture files parse without error)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib.harness_adapter.aider import AiderAdapter, UnsupportedAiderVersion
from lib.harness_adapter.base import AgentStart, ParseError, ToolUse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "aider-transcripts"


def _make_raw(lines: list[str], agent_id: str = "test-agent") -> dict:
    return {"agent_id": agent_id, "new_lines": lines, "final": True}


# ---------------------------------------------------------------------------
# Version dispatch
# ---------------------------------------------------------------------------


class TestAiderVersionDispatch:
    def test_version_060_parses_classic_tool_lines(self, tmp_path):
        """0.60 format: #### prompt + > Ran/Applied/Saved lines."""
        adapter = AiderAdapter(project_dir=tmp_path)
        raw = _make_raw(
            [
                "#### aider v0.60.1",
                "#### Fix the bug",
                "> Ran shell command: pytest tests/",
                "> Applied edit: src/fix.py",
                "> Saved file: src/fix.py",
            ]
        )
        events = adapter.parse_event(raw)
        types = [type(e) for e in events]
        assert AgentStart in types
        tool_uses = [e for e in events if isinstance(e, ToolUse)]
        assert len(tool_uses) == 3
        assert any(t.tool_name == "Ran shell command" for t in tool_uses)
        assert any(t.tool_name == "Applied edit" for t in tool_uses)
        assert any(t.tool_name == "Saved file" for t in tool_uses)

    def test_version_065_parses_linting_lines(self, tmp_path):
        """0.65 format adds Linting/Fixing lines."""
        adapter = AiderAdapter(project_dir=tmp_path)
        raw = _make_raw(
            [
                "#### aider v0.65.3",
                "#### Refactor service",
                "> Applied edit: src/service.py",
                "> Linting src/service.py: 0 issues found",
                "> Fixing src/service.py: removed unused import",
            ]
        )
        events = adapter.parse_event(raw)
        tool_uses = [e for e in events if isinstance(e, ToolUse)]
        tool_names = {t.tool_name for t in tool_uses}
        assert "Applied edit" in tool_names
        # Linting and Fixing lines should be captured (0.65+ regex)
        assert any("Linting" in name or "Fixing" in name for name in tool_names), (
            f"Expected Linting/Fixing tool names in {tool_names}"
        )

    def test_version_070_parses_test_runner_lines(self, tmp_path):
        """0.70 format adds Running tests / Tests passed lines."""
        adapter = AiderAdapter(project_dir=tmp_path)
        raw = _make_raw(
            [
                "#### aider v0.70.2",
                "#### Add integration tests",
                "> Applied edit: tests/test_pipeline.py",
                "> Running tests: pytest tests/integration/ -v",
                "> Tests passed: 7 passed, 0 failed",
            ]
        )
        events = adapter.parse_event(raw)
        tool_uses = [e for e in events if isinstance(e, ToolUse)]
        tool_names = {t.tool_name for t in tool_uses}
        assert "Applied edit" in tool_names
        assert any("Running tests" in name or "Tests passed" in name for name in tool_names), (
            f"Expected test-runner tool names in {tool_names}"
        )

    def test_unsupported_version_below_range_raises(self, tmp_path):
        """Versions below 0.60 should raise UnsupportedAiderVersion."""
        adapter = AiderAdapter(project_dir=tmp_path)
        raw = _make_raw(
            [
                "#### aider v0.59.9",
                "#### Do something",
                "> Applied edit: src/x.py",
            ]
        )
        with pytest.raises(UnsupportedAiderVersion):
            adapter.parse_event(raw)

    def test_unsupported_version_above_range_raises(self, tmp_path):
        """Versions >= 0.71 should raise UnsupportedAiderVersion."""
        adapter = AiderAdapter(project_dir=tmp_path)
        raw = _make_raw(
            [
                "#### aider v0.71.0",
                "#### Do something",
                "> Applied edit: src/x.py",
            ]
        )
        with pytest.raises(UnsupportedAiderVersion):
            adapter.parse_event(raw)

    def test_no_version_header_uses_best_effort(self, tmp_path):
        """Transcripts without a version header parse best-effort without raising."""
        adapter = AiderAdapter(project_dir=tmp_path)
        raw = _make_raw(
            [
                "#### Fix typo",
                "> Applied edit: src/typo.py",
            ]
        )
        # Must not raise
        events = adapter.parse_event(raw)
        assert any(isinstance(e, AgentStart) for e in events)


# ---------------------------------------------------------------------------
# ParseError
# ---------------------------------------------------------------------------


class TestAiderParseError:
    def test_unknown_pattern_emits_parse_error(self, tmp_path):
        """Lines that match no known pattern after AgentStart emit ParseError."""
        adapter = AiderAdapter(project_dir=tmp_path)
        raw = _make_raw(
            [
                "#### aider v0.60.1",
                "#### Fix it",
                "This is some completely unknown output format",
                "> Applied edit: src/x.py",
            ]
        )
        events = adapter.parse_event(raw)
        parse_errors = [e for e in events if isinstance(e, ParseError)]
        assert parse_errors, "Unknown line must produce ParseError (no silent skip)"
        err = parse_errors[0]
        assert "no_pattern_match" in err.reason
        assert err.adapter == "aider"

    def test_blank_lines_do_not_produce_parse_error(self, tmp_path):
        """Blank lines are silently skipped, never produce ParseError."""
        adapter = AiderAdapter(project_dir=tmp_path)
        raw = _make_raw(
            [
                "#### aider v0.60.1",
                "#### Prompt",
                "",
                "   ",
                "> Applied edit: src/x.py",
            ]
        )
        events = adapter.parse_event(raw)
        parse_errors = [e for e in events if isinstance(e, ParseError)]
        assert not parse_errors, "Blank lines must not produce ParseError"

    def test_code_fence_lines_produce_parse_error(self, tmp_path):
        """Code fence lines (```) are not in the known pattern set → ParseError."""
        adapter = AiderAdapter(project_dir=tmp_path)
        raw = _make_raw(
            [
                "#### aider v0.60.1",
                "#### Show code",
                "```python",
                "def hello(): pass",
                "```",
            ]
        )
        events = adapter.parse_event(raw)
        parse_errors = [e for e in events if isinstance(e, ParseError)]
        # Code fences + code content = multiple unknown lines
        assert parse_errors, "Code fence lines should produce ParseError"


# ---------------------------------------------------------------------------
# Fixture corpus round-trips
# ---------------------------------------------------------------------------


class TestAiderFixtureCorpus:
    @pytest.mark.parametrize(
        "fixture_name",
        ["aider-0.60.history.md", "aider-0.65.history.md", "aider-0.70.history.md"],
    )
    def test_fixture_parses_without_exception(self, tmp_path, fixture_name):
        """All fixture files parse without raising any exception."""
        fixture_path = _FIXTURES / fixture_name
        assert fixture_path.exists(), f"Fixture file missing: {fixture_path}"

        adapter = AiderAdapter(project_dir=tmp_path)
        lines = fixture_path.read_text(encoding="utf-8").splitlines()
        raw = {
            "agent_id": f"corpus-{fixture_name}",
            "new_lines": lines,
            "final": True,
        }
        # Must not raise
        events = adapter.parse_event(raw)
        assert isinstance(events, list)
        assert len(events) > 0, f"Fixture {fixture_name} produced no events"
        assert any(isinstance(e, AgentStart) for e in events), (
            f"Fixture {fixture_name} must produce at least one AgentStart"
        )

    @pytest.mark.parametrize(
        "fixture_name,expected_version",
        [
            ("aider-0.60.history.md", (0, 60)),
            ("aider-0.65.history.md", (0, 65)),
            ("aider-0.70.history.md", (0, 70)),
        ],
    )
    def test_fixture_version_detected(self, fixture_name, expected_version):
        """Each fixture has a parseable version header."""
        from lib.harness_adapter.aider import _detect_version

        fixture_path = _FIXTURES / fixture_name
        lines = fixture_path.read_text(encoding="utf-8").splitlines()
        version = _detect_version(lines)
        assert version is not None, f"No version detected in {fixture_name}"
        assert version[0] == expected_version[0]
        assert version[1] == expected_version[1]
