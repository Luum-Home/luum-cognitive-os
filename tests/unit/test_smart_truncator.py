"""Unit tests for lib/smart_truncator.py — Workstream 3: Smart Result Truncation."""

import sys
import os

# Ensure lib/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))

from smart_truncator import (
    smart_truncate,
    extract_test_summary,
    extract_build_summary,
    extract_docker_summary,
    extract_json_summary,
    extract_git_summary,
    extract_lint_summary,
    _detect_command_type,
    _head_tail,
)


# ---------------------------------------------------------------------------
# Fixtures — realistic command outputs
# ---------------------------------------------------------------------------

PYTEST_OUTPUT_WITH_FAILURES = """\
============================= test session starts ==============================
platform linux -- Python 3.11.9, pytest-8.2.0
collected 42 items

tests/unit/test_foo.py::test_add PASSED
tests/unit/test_foo.py::test_subtract PASSED
tests/unit/test_bar.py::test_parse_json FAILED
tests/unit/test_bar.py::test_validate_schema FAILED
tests/unit/test_baz.py::test_connect PASSED
tests/unit/test_baz.py::test_disconnect PASSED
tests/unit/test_baz.py::test_reconnect PASSED

================================= FAILURES ==================================
_______________________ test_parse_json ______________________________

    def test_parse_json():
        data = parse_json("invalid")
E       ValueError: invalid JSON at position 0
E       assert result is not None

tests/unit/test_bar.py:12: ValueError
_______________________ test_validate_schema _______________________________

    def test_validate_schema():
        schema = load_schema("missing.yaml")
E       FileNotFoundError: [Errno 2] No such file or directory: 'missing.yaml'

tests/unit/test_bar.py:23: FileNotFoundError
=========================== short test summary info ============================
FAILED tests/unit/test_bar.py::test_parse_json - ValueError: invalid JSON at position 0
FAILED tests/unit/test_bar.py::test_validate_schema - FileNotFoundError
======================== 2 failed, 5 passed in 0.42s ===========================
"""

GO_TEST_OUTPUT_WITH_COVERAGE = """\
=== RUN   TestUserCreate
--- PASS: TestUserCreate (0.00s)
=== RUN   TestUserCreate_InvalidEmail
--- PASS: TestUserCreate_InvalidEmail (0.00s)
=== RUN   TestUserDelete
--- FAIL: TestUserDelete (0.01s)
    user_test.go:45: expected status 200, got 404
=== RUN   TestGetUserByID
--- PASS: TestGetUserByID (0.00s)
--- FAIL: TestUserDelete (0.01s)
FAIL	github.com/org/project/internal/users	coverage: 78.5% of statements
ok  	github.com/org/project/internal/orders	coverage: 92.3% of statements
ok  	github.com/org/project/internal/payments	coverage: 88.1% of statements
"""

GO_BUILD_ERROR = """\
# github.com/org/project/internal/users
internal/users/handler.go:42:15: undefined: UserRepository
internal/users/handler.go:58:9: cannot use resp (type *UserResponse) as type Response
internal/users/dto.go:12:3: unknown field 'CreatedBy' in struct literal of type UserDTO
# github.com/org/project/internal/orders
internal/orders/service.go:71:5: undefined: OrderStatus
"""

TSC_BUILD_ERROR = """\
src/api/users/UserController.ts(42,15): error TS2304: Cannot find name 'UserRepository'.
src/api/users/UserController.ts(58,9): error TS2322: Type 'UserResponse' is not assignable to type 'Response'.
src/common/dto/UserDTO.ts(12,3): error TS2322: Object literal may only specify known properties.
Found 3 errors in 3 files.
"""

DOCKER_COMPOSE_PS = """\
NAME                    IMAGE                STATUS          PORTS
api-server              org/api:v1.2.3       Up 2 hours      0.0.0.0:3000->3000/tcp
postgres                postgres:15          Up 2 hours      5432/tcp
redis-cache             redis:7              Up 2 hours      6379/tcp
worker                  org/worker:v1.2.3    Up 1 hour
langfuse-web            langfuse/langfuse    Exited (1)
nemo-guardrails         org/nemo:latest      Restarting
"""

DOCKER_LOGS_WITH_ERROR = """\
2026-04-10T10:00:00.000Z INFO  Starting server on :3000
2026-04-10T10:00:01.000Z INFO  Connected to database
2026-04-10T10:00:02.000Z ERROR Failed to connect to Redis: connection refused
2026-04-10T10:00:02.100Z ERROR Retrying connection (1/3)
2026-04-10T10:00:03.000Z ERROR Retrying connection (2/3)
2026-04-10T10:00:04.000Z FATAL Redis connection failed after 3 attempts, shutting down
""" * 30  # make it long

ESLINT_OUTPUT = """\

/app/src/api/users/UserController.ts
  42:15  error    'UserRepository' is not defined       no-undef
  58:9   error    Type 'string' is not assignable       @typescript-eslint/no-unsafe-assignment
  71:3   warning  Prefer const over let                 prefer-const

/app/src/common/dto/UserDTO.ts
  12:3   error    Object literal may only specify known properties  no-extra-parens

✖ 10 problems (3 errors, 1 warning)
  3 errors and 1 warning potentially fixable with the `--fix` option.
"""

JSON_ARRAY_RESPONSE = """\
[
  {
    "id": "usr_001",
    "name": "Alice",
    "email": "alice@example.com",
    "roles": ["admin", "editor"],
    "createdAt": "2026-01-01T00:00:00Z"
  },
  {
    "id": "usr_002",
    "name": "Bob",
    "email": "bob@example.com",
    "roles": ["viewer"],
    "createdAt": "2026-02-01T00:00:00Z"
  }
]
""" + '  {"id": "usr_%03d", "name": "User%d"}\n' * 200

JSON_OBJECT_RESPONSE = """\
{
  "users": [{"id": 1}, {"id": 2}, {"id": 3}],
  "total": 3,
  "page": 1,
  "pageSize": 20,
  "metadata": {
    "requestId": "req_abc123",
    "timestamp": "2026-04-10T10:00:00Z"
  },
  "longDescription": "This is a very long description that spans many characters and should be truncated appropriately in the output so that we do not waste context tokens on verbose string values that the agent does not need to see in full detail for diagnostic purposes."
}
"""

GIT_DIFF_STAT = """\
 internal/users/handler.go         | 45 +++++++++++++++++++++++++++++++++------
 internal/users/dto.go             | 12 +++++++----
 internal/users/repository.go      |  8 +++++---
 tests/unit/test_user_handler.go   | 31 +++++++++++++++++++++++++
 docs/api/users.md                 |  6 ++++--
 6 files changed, 89 insertions(+), 13 deletions(-)
"""

UNKNOWN_COMMAND_LARGE = "line content\n" * 1000  # > 5000 chars, unknown command type


# ---------------------------------------------------------------------------
# _detect_command_type tests
# ---------------------------------------------------------------------------

class TestDetectCommandType:
    def test_pytest(self):
        assert _detect_command_type("python3 -m pytest tests/ -v") == "test"

    def test_go_test(self):
        assert _detect_command_type("go test ./...") == "test"

    def test_jest(self):
        assert _detect_command_type("yarn test --coverage") == "test"

    def test_vitest(self):
        assert _detect_command_type("npx vitest run") == "test"

    def test_go_build(self):
        assert _detect_command_type("go build ./...") == "build"

    def test_tsc_no_emit_is_lint(self):
        assert _detect_command_type("tsc --noEmit") == "lint"  # tsc --noEmit is lint

    def test_tsc_plain_is_build(self):
        assert _detect_command_type("tsc") == "build"  # plain tsc is build

    def test_yarn_build(self):
        assert _detect_command_type("yarn build") == "build"

    def test_docker_compose_ps(self):
        assert _detect_command_type("docker compose ps") == "docker"

    def test_docker_ps(self):
        assert _detect_command_type("docker ps") == "docker"

    def test_git_diff(self):
        assert _detect_command_type("git diff --stat HEAD~1") == "git"

    def test_git_log(self):
        assert _detect_command_type("git log --oneline -10") == "git"

    def test_eslint(self):
        assert _detect_command_type("eslint src/ --ext .ts") == "lint"

    def test_golangci_lint(self):
        assert _detect_command_type("golangci-lint run ./...") == "lint"

    def test_jq(self):
        assert _detect_command_type("jq '.users[]' data.json") == "json"

    def test_grep_count(self):
        assert _detect_command_type("grep -c 'pattern' file.txt") == "count"

    def test_wc(self):
        assert _detect_command_type("wc -l output.txt") == "count"

    def test_unknown(self):
        assert _detect_command_type("ls -la /tmp") == "unknown"

    def test_unknown_cat(self):
        assert _detect_command_type("cat README.md") == "unknown"


# ---------------------------------------------------------------------------
# extract_test_summary tests
# ---------------------------------------------------------------------------

class TestExtractTestSummary:
    def test_pytest_with_failures(self):
        result = extract_test_summary(PYTEST_OUTPUT_WITH_FAILURES)
        assert result  # non-empty
        assert "[smart-truncator: test output extracted]" in result
        assert "2 failed" in result or "FAILED" in result
        assert "test_parse_json" in result or "test_validate_schema" in result
        assert len(result) < len(PYTEST_OUTPUT_WITH_FAILURES)

    def test_pytest_extracts_error_message(self):
        result = extract_test_summary(PYTEST_OUTPUT_WITH_FAILURES)
        assert "ValueError" in result or "FileNotFoundError" in result

    def test_go_test_with_coverage(self):
        result = extract_test_summary(GO_TEST_OUTPUT_WITH_COVERAGE)
        assert result
        assert "78.5%" in result or "coverage" in result.lower()
        assert "TestUserDelete" in result

    def test_go_test_extracts_fail_status(self):
        result = extract_test_summary(GO_TEST_OUTPUT_WITH_COVERAGE)
        assert "FAIL" in result

    def test_empty_output_returns_empty(self):
        result = extract_test_summary("")
        assert result == ""

    def test_output_is_compact(self):
        result = extract_test_summary(PYTEST_OUTPUT_WITH_FAILURES)
        # Smart extraction should produce a much shorter result
        assert len(result) < len(PYTEST_OUTPUT_WITH_FAILURES) // 2


# ---------------------------------------------------------------------------
# extract_build_summary tests
# ---------------------------------------------------------------------------

class TestExtractBuildSummary:
    def test_go_build_error(self):
        result = extract_build_summary(GO_BUILD_ERROR)
        assert result
        assert "[smart-truncator: build output extracted]" in result
        assert "undefined" in result or "UserRepository" in result
        assert "ERRORS" in result

    def test_tsc_error(self):
        result = extract_build_summary(TSC_BUILD_ERROR)
        assert result
        assert "TS2304" in result or "Cannot find name" in result or "ERRORS" in result

    def test_build_shows_file_location(self):
        result = extract_build_summary(GO_BUILD_ERROR)
        # Should contain file:line references
        assert "handler.go" in result or "internal/" in result

    def test_error_count_captured(self):
        result = extract_build_summary(GO_BUILD_ERROR)
        assert "ERRORS" in result

    def test_empty_returns_empty(self):
        result = extract_build_summary("")
        assert result == ""


# ---------------------------------------------------------------------------
# extract_docker_summary tests
# ---------------------------------------------------------------------------

class TestExtractDockerSummary:
    def test_docker_compose_ps(self):
        result = extract_docker_summary(DOCKER_COMPOSE_PS)
        assert result
        assert "[smart-truncator: docker output extracted]" in result
        # Should show service names and statuses
        assert "api-server" in result or "Up" in result or "Exited" in result

    def test_docker_logs_with_errors(self):
        result = extract_docker_summary(DOCKER_LOGS_WITH_ERROR)
        assert result
        assert "ERROR" in result or "FATAL" in result or "error" in result.lower()

    def test_output_is_compact(self):
        result = extract_docker_summary(DOCKER_LOGS_WITH_ERROR)
        # Should be much shorter than the raw log
        assert len(result) < len(DOCKER_LOGS_WITH_ERROR) // 3

    def test_empty_returns_empty(self):
        result = extract_docker_summary("")
        assert result == ""


# ---------------------------------------------------------------------------
# extract_json_summary tests
# ---------------------------------------------------------------------------

class TestExtractJsonSummary:
    def test_json_array(self):
        result = extract_json_summary(JSON_ARRAY_RESPONSE)
        assert result
        assert "[smart-truncator: json output extracted]" in result
        assert "array" in result.lower() or "LENGTH" in result

    def test_json_object(self):
        result = extract_json_summary(JSON_OBJECT_RESPONSE)
        assert result
        assert "object" in result.lower() or "KEYS" in result
        # Should show top-level keys
        assert "users" in result
        assert "total" in result

    def test_json_shows_array_lengths(self):
        result = extract_json_summary(JSON_OBJECT_RESPONSE)
        # users is a list of 3 items
        assert "list[3]" in result or "array" in result.lower()

    def test_json_compact_vs_raw(self):
        result = extract_json_summary(JSON_ARRAY_RESPONSE)
        assert len(result) < len(JSON_ARRAY_RESPONSE) // 3

    def test_invalid_json_returns_empty(self):
        result = extract_json_summary("this is not json at all { broken")
        assert result == "" or "[smart-truncator" not in result

    def test_empty_returns_empty(self):
        result = extract_json_summary("")
        assert result == ""


# ---------------------------------------------------------------------------
# extract_git_summary tests
# ---------------------------------------------------------------------------

class TestExtractGitSummary:
    def test_git_diff_stat(self):
        result = extract_git_summary(GIT_DIFF_STAT)
        assert result
        assert "[smart-truncator: git output extracted]" in result
        assert "handler.go" in result or "files changed" in result.lower()

    def test_git_shows_summary_line(self):
        result = extract_git_summary(GIT_DIFF_STAT)
        # Should include the "N files changed" summary
        assert "6 files changed" in result or "89" in result or "SUMMARY" in result

    def test_empty_returns_empty(self):
        result = extract_git_summary("")
        assert result == ""

    def test_git_log_output(self):
        log_output = """\
commit abc1234567890abcdef1234567890abcdef123456
Author: Dev User <dev@example.com>
Date:   Wed Apr 10 10:00:00 2026 +0000

    feat: add user endpoint

 internal/users/handler.go | 20 +++++++++++
 1 file changed, 20 insertions(+)
"""
        result = extract_git_summary(log_output)
        assert result  # should find something


# ---------------------------------------------------------------------------
# extract_lint_summary tests
# ---------------------------------------------------------------------------

class TestExtractLintSummary:
    def test_eslint_output(self):
        result = extract_lint_summary(ESLINT_OUTPUT)
        assert result
        assert "[smart-truncator: lint output extracted]" in result
        # Should capture error lines or summary
        assert "error" in result.lower() or "ERRORS" in result

    def test_eslint_shows_first_errors(self):
        result = extract_lint_summary(ESLINT_OUTPUT)
        # Should show at least one specific error
        assert "UserController" in result or "no-undef" in result or "ERRORS" in result

    def test_lint_compact_output(self):
        # Create a large lint output
        big_lint = ESLINT_OUTPUT * 20
        result = extract_lint_summary(big_lint)
        assert result
        assert len(result) < len(big_lint) // 5

    def test_empty_returns_empty(self):
        result = extract_lint_summary("")
        assert result == ""


# ---------------------------------------------------------------------------
# smart_truncate dispatcher tests
# ---------------------------------------------------------------------------

class TestSmartTruncate:
    def _pad(self, text: str, min_chars: int = 6000) -> str:
        """Pad text to exceed max_chars threshold so smart extraction is triggered."""
        while len(text) < min_chars:
            text = text + "\n# padding line to exceed threshold\n"
        return text

    def test_pytest_dispatch(self):
        big = self._pad(PYTEST_OUTPUT_WITH_FAILURES)
        result = smart_truncate("python3 -m pytest tests/ -v", big)
        assert "[smart-truncator: test output extracted]" in result
        assert len(result) < len(big)

    def test_go_test_dispatch(self):
        big = self._pad(GO_TEST_OUTPUT_WITH_COVERAGE)
        result = smart_truncate("go test ./...", big)
        assert "FAIL" in result or "coverage" in result.lower()

    def test_go_build_dispatch(self):
        big = self._pad(GO_BUILD_ERROR)
        result = smart_truncate("go build ./...", big)
        assert "[smart-truncator: build output extracted]" in result

    def test_docker_dispatch(self):
        big = self._pad(DOCKER_COMPOSE_PS)
        result = smart_truncate("docker compose ps", big)
        assert "[smart-truncator: docker output extracted]" in result

    def test_jq_dispatch(self):
        big = self._pad(JSON_OBJECT_RESPONSE)
        result = smart_truncate("jq '.users' data.json", big)
        assert "[smart-truncator: json output extracted]" in result

    def test_git_dispatch(self):
        big = self._pad(GIT_DIFF_STAT)
        result = smart_truncate("git diff --stat HEAD~1", big)
        assert "[smart-truncator: git output extracted]" in result

    def test_eslint_dispatch(self):
        big = self._pad(ESLINT_OUTPUT)
        result = smart_truncate("eslint src/ --ext .ts", big)
        assert "[smart-truncator: lint output extracted]" in result

    def test_unknown_command_falls_back_to_head_tail(self):
        """Unknown commands fall back to head+tail truncation."""
        big_output = UNKNOWN_COMMAND_LARGE  # ~12000 chars
        result = smart_truncate("ls -la /tmp", big_output, max_chars=5000)
        assert "TRUNCATED" in result
        assert "[smart-truncator" not in result  # no smart extraction header

    def test_output_below_threshold_returned_unchanged(self):
        """Output under max_chars threshold is returned unchanged."""
        short_output = "hello world\n"
        result = smart_truncate("pytest tests/", short_output, max_chars=5000)
        assert result == short_output

    def test_empty_output_returned_unchanged(self):
        result = smart_truncate("pytest tests/", "", max_chars=5000)
        assert result == ""

    def test_count_command_passthrough(self):
        """grep -c / wc output is already concise — returned as-is when under limit."""
        count_output = "42\n"
        result = smart_truncate("grep -c 'pattern' file.txt", count_output)
        assert result == count_output

    def test_npm_test_dispatch(self):
        npm_test_output = """\
PASS src/utils/parser.test.ts
PASS src/api/users.test.ts
FAIL src/api/orders.test.ts
  ✕ should return 200 (15ms)

Test Suites: 1 failed, 2 passed, 3 total
Tests:       1 failed, 8 passed, 9 total
Snapshots:   0 total
Time:        1.234s
""" * 10  # make it large enough to trigger truncation
        result = smart_truncate("npm test -- --coverage", npm_test_output)
        assert result  # should extract something


# ---------------------------------------------------------------------------
# _head_tail fallback tests
# ---------------------------------------------------------------------------

class TestHeadTailFallback:
    def test_includes_truncation_marker(self):
        big = "x" * 10000
        result = _head_tail(big, max_chars=5000)
        assert "TRUNCATED" in result

    def test_under_limit_unchanged(self):
        small = "x" * 100
        result = _head_tail(small, max_chars=5000)
        assert result == small

    def test_preserves_head_and_tail(self):
        output = "HEAD_CONTENT" + "middle " * 1000 + "TAIL_CONTENT"
        result = _head_tail(output, max_chars=5000)
        assert "HEAD_CONTENT" in result
        assert "TAIL_CONTENT" in result
