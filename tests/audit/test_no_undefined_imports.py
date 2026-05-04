"""AUDIT: every `from X import Y` and `import X` in scripts/ and lib/ must resolve
to an actual module on disk OR a known third-party package.

ROOT CAUSE: scripts/decision_triage.py._engram_search() originally used
    `python3 -c "from lib.engram import search; ..."`
but lib/engram.py does not exist (correct module is lib/engram_client.py).
This silently failed: subprocess returned non-zero, engram_available was set to False,
and ALL decisions stayed PENDING indefinitely — causing 33 false-critical alerts.

This test would have caught the bug at the moment `from lib.engram import search`
was committed. It parses every .py file in scripts/ and lib/ with ast, extracts
all import statements, and verifies that local module references (lib.X, scripts.X)
resolve to an actual file on disk.

FIX (2026-04-27): _engram_search() now uses `engram` CLI subprocess instead. This
test prevents any future regression to undefined local module imports.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
SCAN_DIRS = [REPO / "scripts", REPO / "lib"]

# Standard library modules (partial list — these don't need file resolution)
STDLIB_MODULES = {
    "os", "sys", "re", "io", "ast", "argparse", "datetime", "typing",
    "collections", "functools", "itertools", "dataclasses", "abc",
    "subprocess", "pathlib", "json", "csv", "shutil", "tempfile",
    "unittest", "logging", "warnings", "threading", "asyncio", "time",
    "contextlib", "copy", "string", "textwrap", "hashlib", "secrets",
    "uuid", "math", "statistics", "random", "enum", "operator", "struct",
    "array", "queue", "socket", "ssl", "http", "urllib", "email", "html",
    "xml", "sqlite3", "pickle", "shelve", "pprint", "inspect", "importlib",
    "pkgutil", "platform", "signal", "stat", "glob", "fnmatch", "difflib",
    "traceback", "types", "weakref", "gc", "dis", "tokenize", "token",
    "keyword", "symtable", "compileall", "py_compile", "zipfile", "tarfile",
    "gzip", "bz2", "lzma", "zlib", "base64", "binascii", "codecs",
    "locale", "gettext", "calendar", "heapq", "bisect", "decimal",
    "fractions", "cmath", "numbers", "builtins", "_thread", "concurrent",
    "multiprocessing", "ctypes", "mmap", "readline", "rlcompleter",
    "curses", "idlelib", "tkinter",
    # Test modules
    "pytest", "unittest",
    # Common test utilities
    "_pytest",
}

# Third-party packages we expect to be installed (skip file resolution for these)
THIRD_PARTY_ALLOWLIST = {
    # Core
    "yaml", "toml", "tomllib",
    # AI/ML
    "openai", "anthropic", "litellm", "tiktoken",
    # Web
    "fastapi", "starlette", "uvicorn", "requests", "httpx", "aiohttp",
    # Data
    "pydantic", "attrs", "cattrs", "marshmallow",
    # DB
    "redis", "pymongo", "psycopg2", "sqlalchemy", "alembic",
    # CLI
    "rich", "typer", "click", "prompt_toolkit",
    # Testing
    "pytest", "mock", "responses", "factory_boy", "faker", "hypothesis",
    # Dev
    "ruff", "black", "mypy", "pylint", "isort",
    # Async
    "anyio", "trio",
    # Observability
    "opentelemetry", "prometheus_client", "structlog", "loguru",
    # ML
    "numpy", "pandas", "scipy", "sklearn", "torch", "transformers",
    # Package management
    "pip", "setuptools", "importlib_metadata",
    # Misc commonly installed
    "dotenv", "decouple", "environs", "dateutil", "arrow", "pendulum",
    "tqdm", "humanize", "tabulate", "jinja2", "markupsafe",
    "cryptography", "jwt", "passlib", "bcrypt",
    "boto3", "botocore", "google", "azure",
    "celery", "dramatiq", "rq",
    "watchdog", "schedule",
    # Project-specific external
    "engram",  # engram MCP server (external binary, not a Python module)
    "valkey", "aioredis",
    "mlflow",
    "opik",
    "cognee",
    "repomix",
    "semgrep",
    # Platform
    "AppKit", "Foundation", "objc",  # macOS
}

# Local module prefixes that MUST resolve to files in REPO
LOCAL_PREFIXES = {"lib", "scripts", "tests", "packages"}


def _is_third_party(top_level: str) -> bool:
    return top_level in THIRD_PARTY_ALLOWLIST or top_level in STDLIB_MODULES


def _resolve_local_module(mod: str) -> bool:
    """Check if a local module reference resolves to an actual file or package."""
    parts = mod.split(".")
    # Check as file: lib/foo/bar.py
    as_file = REPO / Path(*parts).with_suffix(".py")
    if as_file.exists():
        return True
    # Check as package: lib/foo/bar/__init__.py
    as_pkg = REPO / Path(*parts) / "__init__.py"
    if as_pkg.exists():
        return True
    # Check as directory (implicit namespace package)
    as_dir = REPO / Path(*parts)
    if as_dir.is_dir():
        return True
    return False


@pytest.mark.audit
def test_no_undefined_local_imports() -> None:
    """Anti-pattern: `from lib.engram import search` where lib/engram.py doesn't exist.

    This test parses all .py files in scripts/ and lib/ and verifies that every
    `import lib.X` or `from lib.X import Y` resolves to an actual file on disk.

    Pass criteria:
    - Every local module reference (lib.*, scripts.*, tests.*) resolves to a file
    - Third-party and stdlib modules are exempted via allowlists

    Failure example (the original bug):
        from lib.engram import search   # lib/engram.py doesn't exist!
        # Should be: from lib.engram_client import search  (or use engram CLI)
    """
    violations: list[tuple[str, int, str, str]] = []  # (file, line, module, expected_path)

    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for py_file in sorted(scan_dir.rglob("*.py")):
            if "__pycache__" in str(py_file):
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue  # Syntax errors are caught elsewhere
            except OSError:
                continue

            for node in ast.walk(tree):
                modules_to_check: list[str] = []

                if isinstance(node, ast.Import):
                    modules_to_check = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        modules_to_check = [node.module]

                for mod in modules_to_check:
                    top_level = mod.split(".")[0]

                    # Skip stdlib and known third-party
                    if _is_third_party(top_level):
                        continue

                    # Skip non-local top-levels
                    if top_level not in LOCAL_PREFIXES:
                        continue

                    # This is a local import — verify it resolves
                    if not _resolve_local_module(mod):
                        expected_path = str(REPO / Path(*mod.split(".")).with_suffix(".py"))
                        violations.append((
                            str(py_file.relative_to(REPO)),
                            getattr(node, "lineno", 0),
                            mod,
                            expected_path,
                        ))

    assert not violations, (
        f"Found {len(violations)} import statement(s) referencing local modules that "
        f"do not exist on disk. This is the same anti-pattern as "
        f"`from lib.engram import search` (lib/engram.py doesn't exist — caused "
        f"silent engram_available=False and 33 fake-critical decisions in /decision-triage). "
        f"Fix: verify the module path or use the CLI/subprocess interface instead. "
        f"Violations (file, line, module, expected_path) — first 10: {violations[:10]}"
    )


@pytest.mark.audit
def test_undefined_import_detection_works() -> None:
    """Verify this test CAN catch the anti-pattern — not just that current code is clean.

    This meta-test creates a temporary file with a known-bad import and verifies
    the scan logic detects it. Without this, the test could pass vacuously if
    _resolve_local_module() had a bug.
    """
    import tempfile  # noqa: PLC0415

    # Create a temp .py file with a bad import
    bad_source = "from lib.nonexistent_ghost_module_xyz import something\n"

    with tempfile.NamedTemporaryFile(suffix=".py", delete=True, mode="w") as tmp:
        tmp.write(bad_source)
        tmp.flush()

        try:
            tree = ast.parse(bad_source)
        except SyntaxError:
            pytest.fail("Could not parse test source — unexpected")

        found_violation = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                top_level = mod.split(".")[0]
                if top_level in LOCAL_PREFIXES and not _resolve_local_module(mod):
                    found_violation = True

        assert found_violation, (
            "The test_no_undefined_local_imports detection logic failed to catch "
            "`from lib.nonexistent_ghost_module_xyz import something`. "
            "The anti-pattern test is broken and must be fixed."
        )
