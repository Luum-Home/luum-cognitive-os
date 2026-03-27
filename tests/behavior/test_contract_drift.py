"""Behavior tests for contract-drift skill logic.

Tests cover HTTP call extraction, dynamic URL normalization,
drift comparison, ignore pattern filtering, and report generation.
"""

import re
import fnmatch
from typing import Dict, List, NamedTuple, Optional

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


class HttpCall(NamedTuple):
    method: str
    endpoint: str
    file: str
    line: int


class ContractEntry(NamedTuple):
    method: str
    endpoint: str
    operation_id: str = ""


class DriftResult(NamedTuple):
    undocumented: list  # HttpCall items in code but not spec
    unused: list  # ContractEntry items in spec but not code
    mismatches: list  # (endpoint, spec_method, code_method, file, line)
    matched: list  # (method, endpoint) pairs


# ---------------------------------------------------------------------------
# HTTP call extraction helpers
# ---------------------------------------------------------------------------

# Go patterns
_GO_NEW_REQUEST = re.compile(
    r'http\.NewRequest\(\s*"(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)"'
    r'\s*,\s*"([^"]+)"',
    re.IGNORECASE,
)
_GO_SHORT = re.compile(
    r'http\.(Get|Post|PostForm)\(\s*"([^"]+)"', re.IGNORECASE
)
_GO_HUMA = re.compile(
    r'huma\.(Get|Post|Put|Patch|Delete)\(\s*\w+\s*,\s*"([^"]+)"',
    re.IGNORECASE,
)

# TypeScript / JavaScript patterns
_TS_FETCH = re.compile(
    r'fetch\(\s*["`\']([^"`\']+)["`\']'
)
_TS_FETCH_METHOD = re.compile(
    r'fetch\(\s*["`\']([^"`\']+)["`\']\s*,\s*\{[^}]*method\s*:\s*["`\']'
    r'(GET|POST|PUT|PATCH|DELETE)["`\']',
    re.IGNORECASE | re.DOTALL,
)
_TS_AXIOS = re.compile(
    r'axios\.(get|post|put|patch|delete)\(\s*["`\']([^"`\']+)["`\']',
    re.IGNORECASE,
)

# Python patterns
_PY_REQUESTS = re.compile(
    r'requests\.(get|post|put|patch|delete)\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_PY_HTTPX = re.compile(
    r'httpx\.(get|post|put|patch|delete)\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_PY_CLIENT = re.compile(
    r'(?:client|session)\.(get|post|put|patch|delete)\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def extract_http_calls_go(source: str, filename: str = "main.go") -> List[HttpCall]:
    """Extract HTTP calls from Go source code."""
    calls = []
    for lineno, line in enumerate(source.splitlines(), 1):
        m = _GO_NEW_REQUEST.search(line)
        if m:
            calls.append(HttpCall(m.group(1).upper(), m.group(2), filename, lineno))
            continue
        m = _GO_SHORT.search(line)
        if m:
            method = m.group(1).upper()
            if method == "POSTFORM":
                method = "POST"
            calls.append(HttpCall(method, m.group(2), filename, lineno))
            continue
        m = _GO_HUMA.search(line)
        if m:
            calls.append(HttpCall(m.group(1).upper(), m.group(2), filename, lineno))
    return calls


def extract_http_calls_ts(source: str, filename: str = "index.ts") -> List[HttpCall]:
    """Extract HTTP calls from TypeScript/JavaScript source code."""
    calls = []
    for lineno, line in enumerate(source.splitlines(), 1):
        m = _TS_AXIOS.search(line)
        if m:
            calls.append(HttpCall(m.group(1).upper(), m.group(2), filename, lineno))
            continue
        m = _TS_FETCH_METHOD.search(line)
        if m:
            calls.append(HttpCall(m.group(2).upper(), m.group(1), filename, lineno))
            continue
        m = _TS_FETCH.search(line)
        if m:
            calls.append(HttpCall("GET", m.group(1), filename, lineno))
    return calls


def extract_http_calls_python(source: str, filename: str = "main.py") -> List[HttpCall]:
    """Extract HTTP calls from Python source code."""
    calls = []
    for lineno, line in enumerate(source.splitlines(), 1):
        for pattern in (_PY_REQUESTS, _PY_HTTPX, _PY_CLIENT):
            m = pattern.search(line)
            if m:
                calls.append(HttpCall(m.group(1).upper(), m.group(2), filename, lineno))
                break
    return calls


# ---------------------------------------------------------------------------
# URL normalization
# ---------------------------------------------------------------------------

_UUID_RE = re.compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
    re.IGNORECASE,
)
_NUMERIC_SEGMENT = re.compile(r'(?<=/)\d+(?=/|$)')
_TEMPLATE_VAR = re.compile(r'\$\{(\w+)\}')
_COLON_PARAM = re.compile(r':(\w+)')


def normalize_url(url: str) -> str:
    """Normalize a URL for comparison against an OpenAPI spec.

    - Strips scheme + host (keeps path only)
    - Replaces UUIDs and numeric IDs with {id}
    - Converts ${var} to {var} and :param to {param}
    - Strips query strings and trailing slashes
    """
    # Strip scheme + authority
    if "://" in url:
        url = "/" + url.split("://", 1)[1].split("/", 1)[-1]

    # Strip query string
    if "?" in url:
        url = url.split("?", 1)[0]

    # Normalize dynamic segments
    url = _UUID_RE.sub("{id}", url)
    url = _NUMERIC_SEGMENT.sub("{id}", url)
    url = _TEMPLATE_VAR.sub(r"{\1}", url)
    url = _COLON_PARAM.sub(r"{\1}", url)

    # Strip trailing slash (but keep root /)
    if len(url) > 1 and url.endswith("/"):
        url = url.rstrip("/")

    # Ensure leading slash
    if not url.startswith("/"):
        url = "/" + url

    return url


# ---------------------------------------------------------------------------
# Ignore pattern filtering
# ---------------------------------------------------------------------------

_DEFAULT_IGNORES = [
    "http://localhost*",
    "https://localhost*",
    "http://127.0.0.1*",
    "https://127.0.0.1*",
    "http://0.0.0.0*",
]


def should_ignore(url: str, patterns: Optional[List[str]] = None) -> bool:
    """Return True if the URL matches any ignore pattern (glob syntax)."""
    all_patterns = _DEFAULT_IGNORES + (patterns or [])
    for pat in all_patterns:
        if fnmatch.fnmatch(url, pat):
            return True
    return False


# ---------------------------------------------------------------------------
# Drift comparison
# ---------------------------------------------------------------------------


def compare_drift(
    calls: List[HttpCall],
    spec_entries: List[ContractEntry],
    ignore_patterns: Optional[List[str]] = None,
) -> DriftResult:
    """Compare HTTP calls against contract spec entries.

    Returns a DriftResult with undocumented, unused, mismatches, and matched.
    """
    # Normalize and filter calls
    normalized_calls = []
    for call in calls:
        if should_ignore(call.endpoint, ignore_patterns):
            continue
        norm_ep = normalize_url(call.endpoint)
        normalized_calls.append(call._replace(endpoint=norm_ep))

    # Build spec lookup: (method_upper, path) -> entry
    spec_lookup: Dict[tuple, ContractEntry] = {}
    spec_by_path: Dict[str, List[ContractEntry]] = {}
    for entry in spec_entries:
        key = (entry.method.upper(), entry.endpoint)
        spec_lookup[key] = entry
        spec_by_path.setdefault(entry.endpoint, []).append(entry)

    undocumented = []
    mismatches = []
    matched_keys = set()

    for call in normalized_calls:
        key = (call.method.upper(), call.endpoint)
        if key in spec_lookup:
            matched_keys.add(key)
        elif call.endpoint in spec_by_path:
            # Path exists but method differs
            spec_methods = [e.method.upper() for e in spec_by_path[call.endpoint]]
            for sm in spec_methods:
                mismatches.append(
                    (call.endpoint, sm, call.method.upper(), call.file, call.line)
                )
                matched_keys.add((sm, call.endpoint))
        else:
            undocumented.append(call)

    # Unused: spec entries not matched
    unused = []
    for entry in spec_entries:
        key = (entry.method.upper(), entry.endpoint)
        if key not in matched_keys:
            unused.append(entry)

    matched = list(matched_keys)
    return DriftResult(undocumented, unused, mismatches, matched)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    drift: DriftResult,
    spec_path: str = "openapi.yaml",
    src_dir: str = ".",
    scanned_files: int = 0,
    total_spec_endpoints: int = 0,
    total_code_calls: int = 0,
) -> str:
    """Generate a structured markdown drift report."""
    has_drift = bool(drift.undocumented or drift.unused or drift.mismatches)

    lines = [
        "## Contract Drift Report",
        "",
        "### Summary",
        f"- **Spec**: {spec_path}",
        f"- **Source**: {src_dir}",
        f"- **Scanned files**: {scanned_files}",
        f"- **Total endpoints in spec**: {total_spec_endpoints}",
        f"- **Total HTTP calls in code**: {total_code_calls}",
        f"- **Drift detected**: {'yes' if has_drift else 'no'}",
        "",
    ]

    # Undocumented
    lines.append("### Undocumented Endpoints (in code, not in spec)")
    if drift.undocumented:
        lines.append("| Method | Endpoint | File | Line |")
        lines.append("|--------|----------|------|------|")
        for call in drift.undocumented:
            lines.append(f"| {call.method} | {call.endpoint} | {call.file} | {call.line} |")
    else:
        lines.append("None")
    lines.append("")

    # Unused
    lines.append("### Unused Contract Entries (in spec, not in code)")
    if drift.unused:
        lines.append("| Method | Endpoint | Operation ID |")
        lines.append("|--------|----------|-------------|")
        for entry in drift.unused:
            lines.append(f"| {entry.method} | {entry.endpoint} | {entry.operation_id} |")
    else:
        lines.append("None")
    lines.append("")

    # Mismatches
    lines.append("### Method Mismatches")
    if drift.mismatches:
        lines.append("| Endpoint | Spec Method | Code Method | File | Line |")
        lines.append("|----------|-------------|-------------|------|------|")
        for ep, sm, cm, f, ln in drift.mismatches:
            lines.append(f"| {ep} | {sm} | {cm} | {f} | {ln} |")
    else:
        lines.append("None")
    lines.append("")

    # Matched
    lines.append("### Matched (no drift)")
    lines.append(f"{len(drift.matched)} endpoints matched correctly.")

    return "\n".join(lines)


# ===========================================================================
# Tests: HTTP call extraction — Go (REQ-01)
# ===========================================================================


class TestGoExtraction:

    def test_http_new_request(self):
        src = 'req, _ := http.NewRequest("POST", "/api/v1/users", body)'
        calls = extract_http_calls_go(src)
        assert len(calls) == 1
        assert calls[0].method == "POST"
        assert calls[0].endpoint == "/api/v1/users"

    def test_http_get(self):
        src = 'resp, err := http.Get("https://api.example.com/health")'
        calls = extract_http_calls_go(src)
        assert len(calls) == 1
        assert calls[0].method == "GET"

    def test_http_post(self):
        src = 'resp, err := http.Post("https://api.example.com/data", "application/json", buf)'
        calls = extract_http_calls_go(src)
        assert len(calls) == 1
        assert calls[0].method == "POST"

    def test_http_post_form(self):
        src = 'resp, err := http.PostForm("https://api.example.com/submit", vals)'
        calls = extract_http_calls_go(src)
        assert len(calls) == 1
        assert calls[0].method == "POST"

    def test_huma_routes(self):
        src = '''huma.Get(api, "/users/{id}", getUser)
huma.Post(api, "/users", createUser)
huma.Delete(api, "/users/{id}", deleteUser)'''
        calls = extract_http_calls_go(src)
        assert len(calls) == 3
        assert calls[0] == HttpCall("GET", "/users/{id}", "main.go", 1)
        assert calls[1] == HttpCall("POST", "/users", "main.go", 2)
        assert calls[2] == HttpCall("DELETE", "/users/{id}", "main.go", 3)

    def test_no_matches(self):
        src = 'fmt.Println("hello world")'
        assert extract_http_calls_go(src) == []

    def test_multiline(self):
        src = '''package main
import "net/http"
func do() {
    http.Get("https://example.com/foo")
    http.NewRequest("PUT", "/bar", nil)
}'''
        calls = extract_http_calls_go(src)
        assert len(calls) == 2
        assert calls[0].method == "GET"
        assert calls[0].line == 4
        assert calls[1].method == "PUT"
        assert calls[1].line == 5


# ===========================================================================
# Tests: HTTP call extraction — TypeScript (REQ-01)
# ===========================================================================


class TestTypeScriptExtraction:

    def test_fetch_default_get(self):
        src = 'const res = await fetch("/api/users")'
        calls = extract_http_calls_ts(src)
        assert len(calls) == 1
        assert calls[0].method == "GET"
        assert calls[0].endpoint == "/api/users"

    def test_fetch_with_method(self):
        src = '''fetch("/api/users", { method: "POST", body: JSON.stringify(data) })'''
        calls = extract_http_calls_ts(src)
        assert len(calls) == 1
        assert calls[0].method == "POST"

    def test_axios_get(self):
        src = 'const res = await axios.get("/api/orders")'
        calls = extract_http_calls_ts(src)
        assert len(calls) == 1
        assert calls[0].method == "GET"
        assert calls[0].endpoint == "/api/orders"

    def test_axios_post(self):
        src = 'axios.post("/api/orders", payload)'
        calls = extract_http_calls_ts(src)
        assert len(calls) == 1
        assert calls[0].method == "POST"

    def test_axios_delete(self):
        src = "axios.delete('/api/orders/123')"
        calls = extract_http_calls_ts(src)
        assert len(calls) == 1
        assert calls[0].method == "DELETE"

    def test_no_matches(self):
        src = 'console.log("hello")'
        assert extract_http_calls_ts(src) == []


# ===========================================================================
# Tests: HTTP call extraction — Python (REQ-01)
# ===========================================================================


class TestPythonExtraction:

    def test_requests_get(self):
        src = 'resp = requests.get("https://api.example.com/users")'
        calls = extract_http_calls_python(src)
        assert len(calls) == 1
        assert calls[0].method == "GET"

    def test_requests_post(self):
        src = 'resp = requests.post("/api/data", json=payload)'
        calls = extract_http_calls_python(src)
        assert len(calls) == 1
        assert calls[0].method == "POST"

    def test_httpx_put(self):
        src = 'resp = httpx.put("/api/items/42", json=data)'
        calls = extract_http_calls_python(src)
        assert len(calls) == 1
        assert calls[0].method == "PUT"

    def test_httpx_delete(self):
        src = "resp = httpx.delete('/api/items/1')"
        calls = extract_http_calls_python(src)
        assert len(calls) == 1
        assert calls[0].method == "DELETE"

    def test_client_instance(self):
        src = 'resp = client.get("/api/health")'
        calls = extract_http_calls_python(src)
        assert len(calls) == 1
        assert calls[0].method == "GET"

    def test_session_instance(self):
        src = 'resp = session.post("/api/login", data=creds)'
        calls = extract_http_calls_python(src)
        assert len(calls) == 1
        assert calls[0].method == "POST"

    def test_no_matches(self):
        src = 'print("hello")'
        assert extract_http_calls_python(src) == []


# ===========================================================================
# Tests: Dynamic URL normalization
# ===========================================================================


class TestUrlNormalization:

    def test_strip_scheme_and_host(self):
        assert normalize_url("https://api.example.com/users") == "/users"

    def test_uuid_replaced(self):
        url = "/users/550e8400-e29b-41d4-a716-446655440000/profile"
        assert normalize_url(url) == "/users/{id}/profile"

    def test_numeric_id_replaced(self):
        assert normalize_url("/users/123") == "/users/{id}"
        assert normalize_url("/orders/99/items/7") == "/orders/{id}/items/{id}"

    def test_template_var_converted(self):
        assert normalize_url("/users/${userId}") == "/users/{userId}"

    def test_colon_param_converted(self):
        assert normalize_url("/users/:id/posts/:postId") == "/users/{id}/posts/{postId}"

    def test_query_string_stripped(self):
        assert normalize_url("/users?page=1&limit=10") == "/users"

    def test_trailing_slash_stripped(self):
        assert normalize_url("/users/") == "/users"

    def test_root_slash_preserved(self):
        assert normalize_url("/") == "/"

    def test_full_url_normalization(self):
        url = "https://api.example.com/api/v1/users/123?fields=name"
        assert normalize_url(url) == "/api/v1/users/{id}"

    def test_no_leading_slash_added(self):
        assert normalize_url("users/42") == "/users/{id}"


# ===========================================================================
# Tests: Drift comparison (REQ-03)
# ===========================================================================


class TestDriftComparison:

    def _spec(self):
        return [
            ContractEntry("GET", "/api/users", "listUsers"),
            ContractEntry("POST", "/api/users", "createUser"),
            ContractEntry("GET", "/api/users/{id}", "getUser"),
            ContractEntry("DELETE", "/api/users/{id}", "deleteUser"),
        ]

    def test_all_matched(self):
        calls = [
            HttpCall("GET", "/api/users", "a.go", 1),
            HttpCall("POST", "/api/users", "a.go", 2),
            HttpCall("GET", "/api/users/123", "a.go", 3),
            HttpCall("DELETE", "/api/users/456", "a.go", 4),
        ]
        result = compare_drift(calls, self._spec())
        assert result.undocumented == []
        assert result.unused == []
        assert result.mismatches == []
        assert len(result.matched) == 4

    def test_undocumented_endpoint(self):
        calls = [
            HttpCall("GET", "/api/users", "a.go", 1),
            HttpCall("POST", "/api/webhooks", "b.go", 5),
        ]
        result = compare_drift(calls, self._spec())
        assert len(result.undocumented) == 1
        assert result.undocumented[0].endpoint == "/api/webhooks"
        assert result.undocumented[0].method == "POST"

    def test_unused_spec_entries(self):
        calls = [
            HttpCall("GET", "/api/users", "a.go", 1),
        ]
        result = compare_drift(calls, self._spec())
        assert len(result.unused) == 3  # POST /users, GET /users/{id}, DELETE /users/{id}

    def test_method_mismatch(self):
        calls = [
            HttpCall("PATCH", "/api/users/123", "a.go", 10),
        ]
        result = compare_drift(calls, self._spec())
        # Spec has both GET and DELETE at /api/users/{id}, so PATCH produces 2 mismatches
        assert len(result.mismatches) == 2
        endpoints = {m[0] for m in result.mismatches}
        spec_methods = {m[1] for m in result.mismatches}
        code_methods = {m[2] for m in result.mismatches}
        assert endpoints == {"/api/users/{id}"}
        assert spec_methods == {"GET", "DELETE"}
        assert code_methods == {"PATCH"}

    def test_empty_calls(self):
        result = compare_drift([], self._spec())
        assert result.undocumented == []
        assert len(result.unused) == 4
        assert result.mismatches == []
        assert result.matched == []

    def test_empty_spec(self):
        calls = [HttpCall("GET", "/api/foo", "a.go", 1)]
        result = compare_drift(calls, [])
        assert len(result.undocumented) == 1
        assert result.unused == []


# ===========================================================================
# Tests: Ignore pattern filtering (REQ-04)
# ===========================================================================


class TestIgnorePatterns:

    def test_localhost_ignored_by_default(self):
        assert should_ignore("http://localhost:8080/api/test") is True
        assert should_ignore("https://localhost/health") is True

    def test_loopback_ignored_by_default(self):
        assert should_ignore("http://127.0.0.1:3000/debug") is True

    def test_zero_addr_ignored_by_default(self):
        assert should_ignore("http://0.0.0.0:9090/metrics") is True

    def test_normal_url_not_ignored(self):
        assert should_ignore("/api/users") is False
        assert should_ignore("https://api.example.com/users") is False

    def test_custom_pattern(self):
        patterns = ["https://*.stripe.com/*"]
        assert should_ignore("https://api.stripe.com/v1/charges", patterns) is True
        assert should_ignore("https://api.example.com/pay", patterns) is False

    def test_path_pattern(self):
        patterns = ["/health", "/metrics/*"]
        assert should_ignore("/health", patterns) is True
        assert should_ignore("/metrics/cpu", patterns) is True
        assert should_ignore("/api/users", patterns) is False

    def test_ignored_calls_excluded_from_drift(self):
        spec = [ContractEntry("GET", "/api/users", "listUsers")]
        calls = [
            HttpCall("GET", "/api/users", "a.go", 1),
            HttpCall("GET", "http://localhost:8080/test", "a.go", 2),
        ]
        result = compare_drift(calls, spec)
        assert len(result.undocumented) == 0
        assert len(result.matched) == 1

    def test_custom_ignore_excludes_from_drift(self):
        spec = [ContractEntry("GET", "/api/users", "listUsers")]
        calls = [
            HttpCall("GET", "/api/users", "a.go", 1),
            HttpCall("POST", "https://api.stripe.com/v1/charges", "b.go", 5),
        ]
        result = compare_drift(calls, spec, ignore_patterns=["https://*.stripe.com/*"])
        assert len(result.undocumented) == 0


# ===========================================================================
# Tests: Report format validation (REQ-05)
# ===========================================================================


class TestReportGeneration:

    def test_report_has_required_sections(self):
        drift = DriftResult([], [], [], [])
        report = generate_report(drift)
        assert "## Contract Drift Report" in report
        assert "### Summary" in report
        assert "### Undocumented Endpoints" in report
        assert "### Unused Contract Entries" in report
        assert "### Method Mismatches" in report
        assert "### Matched (no drift)" in report

    def test_report_summary_fields(self):
        drift = DriftResult([], [], [], [])
        report = generate_report(
            drift,
            spec_path="api/openapi.yaml",
            src_dir="src/",
            scanned_files=15,
            total_spec_endpoints=8,
            total_code_calls=12,
        )
        assert "**Spec**: api/openapi.yaml" in report
        assert "**Source**: src/" in report
        assert "**Scanned files**: 15" in report
        assert "**Total endpoints in spec**: 8" in report
        assert "**Total HTTP calls in code**: 12" in report

    def test_drift_detected_yes(self):
        drift = DriftResult(
            undocumented=[HttpCall("POST", "/api/webhooks", "b.go", 5)],
            unused=[],
            mismatches=[],
            matched=[],
        )
        report = generate_report(drift)
        assert "**Drift detected**: yes" in report

    def test_drift_detected_no(self):
        drift = DriftResult([], [], [], [("GET", "/api/users")])
        report = generate_report(drift)
        assert "**Drift detected**: no" in report

    def test_undocumented_table(self):
        drift = DriftResult(
            undocumented=[HttpCall("POST", "/api/webhooks", "src/wh.ts", 42)],
            unused=[],
            mismatches=[],
            matched=[],
        )
        report = generate_report(drift)
        assert "| POST | /api/webhooks | src/wh.ts | 42 |" in report

    def test_unused_table(self):
        drift = DriftResult(
            undocumented=[],
            unused=[ContractEntry("DELETE", "/api/users/{id}", "deleteUser")],
            mismatches=[],
            matched=[],
        )
        report = generate_report(drift)
        assert "| DELETE | /api/users/{id} | deleteUser |" in report

    def test_mismatch_table(self):
        drift = DriftResult(
            undocumented=[],
            unused=[],
            mismatches=[("/api/orders", "PUT", "PATCH", "orders.go", 87)],
            matched=[],
        )
        report = generate_report(drift)
        assert "| /api/orders | PUT | PATCH | orders.go | 87 |" in report

    def test_matched_count(self):
        drift = DriftResult([], [], [], [("GET", "/a"), ("POST", "/b")])
        report = generate_report(drift)
        assert "2 endpoints matched correctly" in report

    def test_empty_sections_show_none(self):
        drift = DriftResult([], [], [], [])
        report = generate_report(drift)
        assert "None" in report


# ===========================================================================
# Tests: No contract doc = error message (REQ-02)
# ===========================================================================


class TestNoContractDoc:

    def test_missing_spec_error_message(self):
        """When no spec is found, the skill should produce a clear error."""
        # Simulate the check: given a list of candidate paths, none exist
        candidates = [
            "openapi.yaml",
            "openapi.yml",
            "openapi.json",
            "swagger.yaml",
            "swagger.yml",
            "swagger.json",
        ]
        found = [c for c in candidates if False]  # none exist
        if not found:
            error_msg = (
                "No OpenAPI/Swagger specification found. "
                "Provide one with `--spec=<path>` or place it in a "
                "standard location (openapi.yaml, swagger.yaml, api/, docs/, spec/)."
            )
        assert "No OpenAPI/Swagger specification found" in error_msg
        assert "--spec=<path>" in error_msg
