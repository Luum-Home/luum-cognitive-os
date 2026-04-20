# SCOPE: both
"""
Smart Result Truncator — command-type-aware structured extraction.

Replaces dumb head+tail truncation with per-command-type extractors that
preserve semantically important information and discard noise.

Part of Workstream 3: Smart Result Truncation (intelligent-context-compaction plan).
"""

from __future__ import annotations

import json
import re
from typing import Optional


# ---------------------------------------------------------------------------
# Command type detection
# ---------------------------------------------------------------------------

_TEST_PATTERNS = re.compile(
    r"\b(pytest|py\.test|go\s+test|jest|vitest|npm\s+test|yarn\s+test|npx\s+jest|"
    r"npx\s+vitest|python\s+-m\s+pytest|python3\s+-m\s+pytest|"
    r"gradlew\s+test|mvn\s+test)\b",
    re.IGNORECASE,
)
# Lint detection must come before build so "tsc --noEmit" routes to lint, not build.
_LINT_PATTERNS = re.compile(
    r"\b(eslint|golangci-lint|go\s+vet|flake8|ruff|pylint|mypy|"
    r"black\s+--check|prettier\s+--check)\b|tsc\s+--noEmit",
    re.IGNORECASE,
)
_BUILD_PATTERNS = re.compile(
    r"\b(go\s+build|tsc\b|yarn\s+build|npm\s+run\s+build|npm\s+build|"
    r"gradlew\s+build|mvn\s+package|make\b|cargo\s+build|"
    r"python\s+setup\.py|pip\s+install)\b",
    re.IGNORECASE,
)
_DOCKER_PATTERNS = re.compile(
    r"\b(docker(\s+compose|\s+ps|\s+logs|\s+stats|\s+inspect)?|"
    r"docker-compose)\b",
    re.IGNORECASE,
)
_GIT_PATTERNS = re.compile(r"\bgit\b", re.IGNORECASE)
_JSON_PATTERNS = re.compile(
    r"\bjq\b|python3?\s+-c\s+['\"].*json.*['\"]|cat\s+\S+\.json\b",
    re.IGNORECASE,
)
_COUNT_PATTERNS = re.compile(
    r"\bgrep\s+-c\b|\bwc\s+-[lLwc]\b|\bcount\b",
    re.IGNORECASE,
)


def _detect_command_type(command: str) -> str:
    """Return the command category for a shell command string."""
    if _TEST_PATTERNS.search(command):
        return "test"
    # Lint must be checked before build (tsc --noEmit is lint, tsc alone is build)
    if _LINT_PATTERNS.search(command):
        return "lint"
    if _BUILD_PATTERNS.search(command):
        return "build"
    if _DOCKER_PATTERNS.search(command):
        return "docker"
    if _GIT_PATTERNS.search(command):
        return "git"
    if _JSON_PATTERNS.search(command):
        return "json"
    if _COUNT_PATTERNS.search(command):
        return "count"
    return "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def smart_truncate(command: str, output: str, max_chars: int = 5000) -> str:
    """
    Detect command type and extract a structured summary instead of dumb truncation.

    Returns:
        A compact structured summary if the output exceeds max_chars and a
        known extractor exists.  Returns the original output unchanged if it
        is within the limit, or falls back to head+tail truncation for unknown
        command types.
    """
    if not output:
        return output

    if len(output) <= max_chars:
        return output

    cmd_type = _detect_command_type(command)

    extractors = {
        "test": extract_test_summary,
        "build": extract_build_summary,
        "lint": extract_lint_summary,
        "docker": extract_docker_summary,
        "git": extract_git_summary,
        "json": extract_json_summary,
        "count": _passthrough,
    }

    extractor = extractors.get(cmd_type)
    if extractor is None:
        return _head_tail(output, max_chars)

    try:
        result = extractor(output)
        if result:
            return result
    except Exception:
        pass

    # Fallback: head+tail
    return _head_tail(output, max_chars)


# ---------------------------------------------------------------------------
# Per-type extractors
# ---------------------------------------------------------------------------

def extract_test_summary(output: str) -> str:
    """
    Extract from test output: pass/fail counts, failed test names,
    first error/traceback, coverage %.
    """
    lines = output.splitlines()
    summary_parts: list[str] = []

    # --- pytest / Python ---
    # "N passed", "N failed", "N error" in the last summary line
    _pytest_result = None
    for line in reversed(lines):
        if re.search(r"\b(passed|failed|error|warning)\b", line, re.IGNORECASE):
            _pytest_result = line.strip()
            break

    # --- go test ---
    _go_result = None
    for line in lines:
        if re.match(r"^(ok|FAIL|---\s+(FAIL|PASS))\s+", line):
            if _go_result is None:
                _go_result = []
            _go_result.append(line.strip())

    # Coverage
    coverage_line = None
    for line in lines:
        if re.search(r"(coverage|cov):?\s+[\d.]+\s*%", line, re.IGNORECASE):
            coverage_line = line.strip()
            break

    # Failed test names (pytest, go test, jest)
    failed_tests: list[str] = []
    for line in lines:
        # pytest: "FAILED tests/foo.py::test_bar"
        m = re.match(r"^FAILED\s+(\S+)", line)
        if m:
            failed_tests.append(m.group(1))
            continue
        # go test: "--- FAIL: TestXxx"
        m = re.match(r"^--- FAIL:\s+(\S+)", line)
        if m:
            failed_tests.append(m.group(1))
            continue
        # jest: "✕ test description" or "× test description"
        m = re.match(r"^[✕×✗]\s+(.+)", line)
        if m:
            failed_tests.append(m.group(1)[:80])

    # First error block (up to 10 lines after "ERROR" / "FAILED" / "Error:")
    first_error_lines: list[str] = []
    in_error = False
    error_line_count = 0
    for line in lines:
        if not in_error:
            if re.match(
                r"^(E\s+|ERROR\s+|error:|FAILED\b|AssertionError|panic:|"
                r"\s+Error:|\s+FAIL\b)",
                line,
            ):
                in_error = True
                first_error_lines.append(line.rstrip())
                error_line_count = 1
        else:
            if error_line_count < 12 and line.strip():
                first_error_lines.append(line.rstrip())
                error_line_count += 1
            elif not line.strip():
                # Blank line ends the error block
                break

    # Assemble
    if _pytest_result:
        summary_parts.append(f"RESULT: {_pytest_result}")
    elif _go_result:
        summary_parts.append("RESULT:\n" + "\n".join(_go_result[:10]))

    if coverage_line:
        summary_parts.append(f"COVERAGE: {coverage_line}")

    if failed_tests:
        listed = failed_tests[:10]
        summary_parts.append("FAILED TESTS:\n  " + "\n  ".join(listed))
        if len(failed_tests) > 10:
            summary_parts.append(f"  ... and {len(failed_tests) - 10} more")

    if first_error_lines:
        summary_parts.append("FIRST ERROR:\n" + "\n".join(first_error_lines[:15]))

    if not summary_parts:
        # No structured data found — fall back to caller
        return ""

    header = "[smart-truncator: test output extracted]"
    return header + "\n" + "\n\n".join(summary_parts)


def extract_build_summary(output: str) -> str:
    """
    Extract from build output: first error with file:line, error/warning counts.
    """
    if not output.strip():
        return ""
    lines = output.splitlines()

    error_lines: list[str] = []
    warning_count = 0
    error_count = 0

    # Patterns for file:line:col errors (Go, tsc, gcc, rustc, etc.)
    _file_err = re.compile(
        r"^(\S+\.(?:go|ts|js|java|py|cpp|c|rs|swift)):\d+",
        re.IGNORECASE,
    )
    # Generic error markers
    _err_marker = re.compile(
        r"\b(error|Error|ERROR|failed|FAILED|panic:|exception)\b"
    )
    _warn_marker = re.compile(r"\b(warning|Warning|WARNING|warn)\b")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        is_error = _err_marker.search(line) is not None
        is_file_diag = _file_err.match(stripped) is not None  # file:line:col diagnostic
        if is_error or is_file_diag:
            error_count += 1
            if len(error_lines) < 5:
                error_lines.append(stripped[:200])
        if _warn_marker.search(line):
            warning_count += 1

    summary_parts = []

    if error_count > 0:
        summary_parts.append(f"ERRORS: {error_count}  WARNINGS: {warning_count}")
    else:
        summary_parts.append(f"WARNINGS: {warning_count}  (no errors detected)")

    if error_lines:
        shown = error_lines[:5]
        summary_parts.append("FIRST ERRORS:\n" + "\n".join(f"  {e}" for e in shown))
        if error_count > 5:
            summary_parts.append(f"  ... and {error_count - 5} more errors")

    if not summary_parts:
        return ""

    header = "[smart-truncator: build output extracted]"
    return header + "\n" + "\n\n".join(summary_parts)


def extract_docker_summary(output: str) -> str:
    """
    Extract from docker output: service status table, error lines.
    """
    lines = output.splitlines()

    # Look for docker ps / compose ps table rows
    status_rows: list[str] = []
    error_lines: list[str] = []
    _status_re = re.compile(
        r"\b(Up|Exited|Restarting|Created|Dead|Paused|running|stopped|"
        r"unhealthy|healthy|starting)\b",
        re.IGNORECASE,
    )
    _err_re = re.compile(r"\b(error|Error|ERROR|failed|FAILED|fatal)\b")

    header_found = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Keep the header line (NAME, STATUS, etc.)
        if re.search(r"\bNAME\b.*\bSTATUS\b|\bCONTAINER\s+ID\b", line, re.IGNORECASE):
            header_found = True
            status_rows.append(stripped[:120])
            continue
        if _status_re.search(line) and (header_found or _status_re.search(line)):
            status_rows.append(stripped[:120])
        if _err_re.search(line):
            error_lines.append(stripped[:200])

    summary_parts = []

    if status_rows:
        shown = status_rows[:20]
        summary_parts.append("SERVICE STATUS:\n" + "\n".join(f"  {r}" for r in shown))
        if len(status_rows) > 20:
            summary_parts.append(f"  ... and {len(status_rows) - 20} more services")

    if error_lines:
        shown = error_lines[:5]
        summary_parts.append("ERRORS:\n" + "\n".join(f"  {e}" for e in shown))

    if not summary_parts:
        return ""

    header = "[smart-truncator: docker output extracted]"
    return header + "\n" + "\n\n".join(summary_parts)


def extract_json_summary(output: str) -> str:
    """
    Extract from JSON output: top-level keys with types, array lengths,
    truncated preview of first element.
    """
    stripped = output.strip()
    if not stripped:
        return ""

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        # Try to find JSON in the output
        m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", stripped)
        if not m:
            return ""
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return ""

    parts: list[str] = []

    if isinstance(data, dict):
        parts.append(f"TYPE: object  KEYS: {len(data)}")
        key_info: list[str] = []
        for k, v in list(data.items())[:20]:
            if isinstance(v, list):
                key_info.append(f"  {k!r}: list[{len(v)}]")
            elif isinstance(v, dict):
                key_info.append(f"  {k!r}: dict[{len(v)} keys]")
            elif isinstance(v, str) and len(v) > 100:
                key_info.append(f"  {k!r}: str({len(v)} chars)")
            else:
                key_info.append(f"  {k!r}: {json.dumps(v)[:80]}")
        parts.append("STRUCTURE:\n" + "\n".join(key_info))

    elif isinstance(data, list):
        parts.append(f"TYPE: array  LENGTH: {len(data)}")
        if data:
            first = data[0]
            if isinstance(first, dict):
                parts.append(f"ELEMENT KEYS: {list(first.keys())[:15]}")
            preview = json.dumps(first, indent=2)
            if len(preview) > 300:
                preview = preview[:300] + "\n  ... (truncated)"
            parts.append(f"FIRST ELEMENT:\n{preview}")
        if len(data) > 1:
            parts.append(f"... and {len(data) - 1} more elements")

    else:
        # Scalar
        parts.append(f"VALUE: {json.dumps(data)[:200]}")

    if not parts:
        return ""

    header = "[smart-truncator: json output extracted]"
    return header + "\n" + "\n".join(parts)


def extract_git_summary(output: str) -> str:
    """
    Extract from git output: files changed stat summary, first 3 diff hunks.
    """
    lines = output.splitlines()

    # git diff --stat / git log --stat lines: "file | N +/-"
    stat_lines: list[str] = []
    hunk_lines: list[str] = []
    summary_line = None  # "3 files changed, 45 insertions(+), 12 deletions(-)"
    in_hunk = False
    hunk_count = 0

    for line in lines:
        # Stat lines
        if re.match(r"^\s+\S+.*\|\s+\d+", line):
            stat_lines.append(line.strip()[:100])
            continue
        # Summary line
        if re.search(r"\d+\s+files?\s+changed", line):
            summary_line = line.strip()
            continue
        # Diff hunks
        if line.startswith("@@") and hunk_count < 3:
            in_hunk = True
            hunk_count += 1
            hunk_lines.append(line[:120])
            continue
        if in_hunk:
            if line.startswith("@@"):
                if hunk_count >= 3:
                    in_hunk = False
                    continue
                hunk_count += 1
                hunk_lines.append(line[:120])
            elif line.startswith("diff --git") or line.startswith("index "):
                in_hunk = False
                hunk_lines.append(line[:120])
            else:
                # Keep up to 6 lines per hunk
                if len(hunk_lines) < hunk_count * 8:
                    hunk_lines.append(line[:120])

        # Commit log lines
        if re.match(r"^commit [0-9a-f]{40}", line):
            stat_lines.append(line[:80])
        elif re.match(r"^(Author|Date|Merge):", line):
            stat_lines.append(line.strip()[:80])

    parts: list[str] = []

    if summary_line:
        parts.append(f"SUMMARY: {summary_line}")

    if stat_lines:
        shown = stat_lines[:20]
        parts.append("FILES:\n" + "\n".join(f"  {s}" for s in shown))
        if len(stat_lines) > 20:
            parts.append(f"  ... and {len(stat_lines) - 20} more files")

    if hunk_lines:
        parts.append("DIFF HUNKS (first 3):\n" + "\n".join(hunk_lines[:25]))

    if not parts:
        # No structured git data: show first/last lines
        return ""

    header = "[smart-truncator: git output extracted]"
    return header + "\n" + "\n\n".join(parts)


def extract_lint_summary(output: str) -> str:
    """
    Extract from lint output: error count, warning count, first 3 errors with
    file:line location.
    """
    lines = output.splitlines()

    error_lines: list[str] = []
    warning_lines: list[str] = []
    total_errors = 0
    total_warnings = 0

    # file:line:col: error/warning
    _loc_re = re.compile(
        r"^(\S+\.(?:go|ts|js|jsx|tsx|py|java|rs|cpp|c)):\d+", re.IGNORECASE
    )
    # eslint format: "  file  line:col  error  message  rule"
    _eslint_re = re.compile(r"^\s+\d+:\d+\s+(error|warning)\s+", re.IGNORECASE)
    _err_re = re.compile(r"\berror\b", re.IGNORECASE)
    _warn_re = re.compile(r"\bwarning\b", re.IGNORECASE)
    # Summary: "5 errors, 3 warnings" or "5 problems (3 errors, 2 warnings)"
    _summary_re = re.compile(
        r"(\d+)\s+(error|problem|issue)s?.*?(\d+)\s+warning", re.IGNORECASE
    )

    summary_line = None
    for line in lines:
        m = _summary_re.search(line)
        if m:
            summary_line = line.strip()
            continue

        if _loc_re.match(line.strip()):
            if _err_re.search(line):
                total_errors += 1
                if len(error_lines) < 5:
                    error_lines.append(line.strip()[:200])
            elif _warn_re.search(line):
                total_warnings += 1
                if len(warning_lines) < 3:
                    warning_lines.append(line.strip()[:200])
            continue

        if _eslint_re.match(line):
            if "error" in line.lower():
                total_errors += 1
                if len(error_lines) < 5:
                    error_lines.append(line.strip()[:200])
            else:
                total_warnings += 1
                if len(warning_lines) < 3:
                    warning_lines.append(line.strip()[:200])

    parts: list[str] = []

    if summary_line:
        parts.append(f"SUMMARY: {summary_line}")
    elif total_errors or total_warnings:
        parts.append(f"ERRORS: {total_errors}  WARNINGS: {total_warnings}")

    if error_lines:
        parts.append("FIRST ERRORS:\n" + "\n".join(f"  {e}" for e in error_lines))
    if warning_lines:
        parts.append("FIRST WARNINGS:\n" + "\n".join(f"  {w}" for w in warning_lines))

    if not parts:
        return ""

    header = "[smart-truncator: lint output extracted]"
    return header + "\n" + "\n\n".join(parts)


# ---------------------------------------------------------------------------
# SmartTruncator class — object-oriented wrapper for the functional API
# ---------------------------------------------------------------------------

class SmartTruncator:
    """Class-based wrapper around the smart_truncate functional API.

    Provides the same interface described in WS2 while delegating to the
    existing per-type extractors above.
    """

    def __init__(self, max_chars: int = 5000):
        self.max_chars = max_chars

    def truncate(self, command: str, output: str) -> str:
        """Truncate *output* intelligently based on *command* type.

        Always preserves lines containing FAIL/ERROR/panic/CRITICAL/WARN/PASS/coverage.
        """
        result = smart_truncate(command, output, max_chars=self.max_chars)
        # Guarantee critical lines are never lost regardless of strategy
        if len(output) > self.max_chars:
            result = self._ensure_critical_lines(output, result)
        return result

    def _ensure_critical_lines(self, original: str, truncated: str) -> str:
        """Inject any critical lines from *original* that are absent in *truncated*."""
        _critical = re.compile(
            r"\b(FAIL(ED)?|ERROR|panic|CRITICAL|WARN(ING)?|PASS|coverage:)\b",
            re.IGNORECASE,
        )
        missing = [l for l in original.splitlines()
                   if _critical.search(l) and l not in truncated]
        if not missing:
            return truncated
        suffix = "\n[preserved critical lines]\n" + "\n".join(missing)
        # Trim to stay within budget
        available = self.max_chars - len(suffix)
        return truncated[:max(0, available)] + suffix

    def detect_command_type(self, command: str) -> str:
        """Classify command into: test, build, lint, git, docker, json, count, other."""
        return _detect_command_type(command)

    def extract_test_summary(self, output: str) -> str:
        """Extract just the test summary from pytest/go test/jest output."""
        return extract_test_summary(output)

    def extract_errors(self, output: str) -> str:
        """Extract error/failure lines with context."""
        lines = output.splitlines()
        _err_re = re.compile(
            r"\b(FAIL(ED)?|ERROR|panic|CRITICAL|exception)\b", re.IGNORECASE
        )
        collected: list[str] = []
        seen: set[int] = set()
        for i, line in enumerate(lines):
            if _err_re.search(line):
                for j in range(max(0, i - 1), min(len(lines), i + 2)):
                    if j not in seen:
                        collected.append(lines[j])
                        seen.add(j)
        return "\n".join(collected)


# ---------------------------------------------------------------------------
# Fallback helpers
# ---------------------------------------------------------------------------

def _passthrough(output: str) -> str:
    """Return output unchanged (for already-concise commands like wc, grep -c)."""
    return output


def _head_tail(output: str, max_chars: int = 5000) -> str:
    """Existing head+tail truncation behaviour."""
    head_chars = max_chars * 2 // 5  # ~40%
    tail_chars = max_chars // 5      # ~20%
    if len(output) <= max_chars:
        return output
    head = output[:head_chars]
    tail = output[-tail_chars:]
    msg = (
        f"\n... [TRUNCATED: {len(output)} chars total, "
        f"showing first {head_chars} + last {tail_chars}] ...\n"
    )
    return head + msg + tail
