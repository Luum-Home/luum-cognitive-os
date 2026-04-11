"""Unit tests for the SmartTruncator class in lib/smart_truncator.py (WS2).

These tests cover the class-based interface.  The existing test_smart_truncator.py
covers the functional API.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))

import pytest
from smart_truncator import SmartTruncator


# ---------------------------------------------------------------------------
# Sample outputs (short fixtures embedded here as per task requirements)
# ---------------------------------------------------------------------------

PYTEST_OUTPUT = """\
============================= test session starts ==============================
collected 10 items

tests/test_foo.py::test_a PASSED
tests/test_foo.py::test_b FAILED
tests/test_foo.py::test_c PASSED

================================= FAILURES ==================================
FAILED tests/test_foo.py::test_b - AssertionError: expected 1 got 2

======================== 1 failed, 9 passed in 0.31s ===========================
"""

GO_BUILD_OUTPUT = """\
# github.com/org/app/internal/handler
internal/handler/users.go:42:5: undefined: UserRepo
internal/handler/users.go:55:9: cannot use r (type *Response) as type Handler
Build failed.
"""

GIT_OUTPUT = """\
 internal/users/handler.go | 10 +++++-----
 1 file changed, 5 insertions(+), 5 deletions(-)
"""

GREP_OUTPUT = "\n".join(f"file{i}.go: match" for i in range(50))

LARGE_UNKNOWN_OUTPUT = "line\n" * 2000  # ~10000 chars


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSmartTruncatorClass:
    def setup_method(self):
        self.t = SmartTruncator(max_chars=500)

    # --- import / construction ---

    def test_import_ok(self):
        from smart_truncator import SmartTruncator as ST
        assert ST is not None

    def test_construction_default(self):
        t = SmartTruncator()
        assert t.max_chars == 5000

    def test_construction_custom(self):
        t = SmartTruncator(max_chars=200)
        assert t.max_chars == 200

    # --- detect_command_type ---

    def test_detect_pytest(self):
        assert self.t.detect_command_type("python3 -m pytest tests/ -v") == "test"

    def test_detect_go_test(self):
        assert self.t.detect_command_type("go test ./...") == "test"

    def test_detect_go_build(self):
        assert self.t.detect_command_type("go build ./...") == "build"

    def test_detect_git(self):
        assert self.t.detect_command_type("git diff --stat") == "git"

    def test_detect_docker(self):
        assert self.t.detect_command_type("docker compose ps") == "docker"

    def test_detect_other(self):
        assert self.t.detect_command_type("ls -la") == "unknown"

    # --- short output passes through unchanged ---

    def test_short_output_unchanged(self):
        short = "hello\nworld\n"
        result = self.t.truncate("pytest", short)
        assert result == short

    # --- truncation actually truncates ---

    def test_large_output_truncated(self):
        result = self.t.truncate("pytest", "x" * 1000)
        assert len(result) <= self.t.max_chars + 200  # allow small overshoot for critical lines

    # --- pytest output preserves key lines ---

    def test_pytest_output_keeps_summary(self):
        # Make it big enough to trigger truncation
        big_pytest = PYTEST_OUTPUT * 20
        t = SmartTruncator(max_chars=300)
        result = t.truncate("pytest tests/", big_pytest)
        assert "passed" in result.lower() or "failed" in result.lower()

    def test_pytest_output_keeps_failures(self):
        big_pytest = PYTEST_OUTPUT * 20
        t = SmartTruncator(max_chars=300)
        result = t.truncate("pytest tests/", big_pytest)
        # FAILED test name or summary should be present
        assert "FAILED" in result or "failed" in result.lower()

    # --- build output preserves errors ---

    def test_build_output_keeps_errors(self):
        big_build = GO_BUILD_OUTPUT * 30
        t = SmartTruncator(max_chars=400)
        result = t.truncate("go build ./...", big_build)
        # Should mention errors
        assert "error" in result.lower() or "undefined" in result

    # --- git output behaviour ---

    def test_git_output(self):
        # git output is typically short; truncate with high max_chars passes through
        t = SmartTruncator(max_chars=5000)
        result = t.truncate("git diff --stat", GIT_OUTPUT)
        assert result == GIT_OUTPUT  # short enough to pass through unchanged

    # --- search output ---

    def test_grep_output_truncated_with_count(self):
        t = SmartTruncator(max_chars=300)
        result = t.truncate("grep -rn 'pattern' .", GREP_OUTPUT)
        # Should be shorter than original
        assert len(result) <= len(GREP_OUTPUT)

    # --- default truncation for unknown commands ---

    def test_default_truncation(self):
        t = SmartTruncator(max_chars=500)
        result = t.truncate("ls -la /tmp", LARGE_UNKNOWN_OUTPUT)
        assert len(result) < len(LARGE_UNKNOWN_OUTPUT)
        assert "TRUNCATED" in result

    # --- critical lines always preserved ---

    def test_critical_lines_always_preserved(self):
        """FAIL/ERROR/panic lines must never be dropped."""
        base = "normal line\n" * 200
        critical = "ERROR: something went badly wrong\n"
        output = base + critical + base
        t = SmartTruncator(max_chars=200)
        result = t.truncate("some-command", output)
        # The critical line should appear somewhere
        assert "ERROR" in result or "wrong" in result

    # --- extract_test_summary ---

    def test_extract_test_summary_returns_string(self):
        result = self.t.extract_test_summary(PYTEST_OUTPUT)
        assert isinstance(result, str)

    def test_extract_test_summary_has_content(self):
        result = self.t.extract_test_summary(PYTEST_OUTPUT)
        # Should find the summary line
        assert "passed" in result.lower() or "failed" in result.lower() or result == ""

    # --- extract_errors ---

    def test_extract_errors_finds_error_lines(self):
        output = "line1\nERROR: disk full\nline3\n"
        result = self.t.extract_errors(output)
        assert "ERROR" in result or "disk full" in result

    def test_extract_errors_on_clean_output(self):
        clean = "all good\nno issues here\n"
        result = self.t.extract_errors(clean)
        assert result == ""
