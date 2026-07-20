# SCOPE: os-only
"""No primitive may point at a lib/ module that moved to cos_lib/.

The lib/ -> cos_lib/ rename silently disabled eight OS features: each consumer
kept referencing `lib/<module>.py`, and every one of those call sites fails
soft -- `|| true`, `if [ ! -f ... ]; then exit 0`, `except: pass`. The feature
simply stopped happening. No test failed, nothing was logged, and the breakage
stayed invisible until a disk audit led back to it.

Fail-soft is correct at runtime (a missing optional module must not kill a
session) but it makes a broken path undetectable. This audit is the
counterweight: soft at runtime, loud in CI.

Detection rule -- deliberately narrow, so it is precise rather than noisy:
flag `lib/<module>.py` only when that path does NOT exist AND
`cos_lib/<module>.py` DOES. That signature is unambiguous: the module was
renamed and this caller was left behind. Placeholder paths in comments
(`lib/X.py`, `cos_lib/foo.py`) have no counterpart and are ignored for free.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.audit

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCAN_DIRS = ("hooks", "scripts", "bin")
SCAN_SUFFIXES = (".sh", ".py", "")

# `lib/<module>.py` in shell/string form, and `/ "lib" / "<module>.py"` in
# pathlib form. `_lib` is excluded via the lookbehind: hooks/_lib and
# scripts/_lib are shared shell helpers, unrelated to the Python package.
_STRING_FORM = re.compile(r"(?<!_)(?<![A-Za-z0-9])lib/(?P<module>[A-Za-z0-9_]+\.py)")
_PATHLIB_FORM = re.compile(
    r"""["']lib["']\s*/\s*["'](?P<module>[A-Za-z0-9_]+\.py)["']"""
)


def _iter_primitive_files():
    for directory in SCAN_DIRS:
        base = PROJECT_ROOT / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            if "_lib" in path.parts or "packages" in path.parts:
                continue
            if path.suffix not in SCAN_SUFFIXES:
                continue
            yield path


def _renamed_modules(text: str):
    """Yield module names referenced as lib/X.py that now live in cos_lib/."""
    for pattern in (_STRING_FORM, _PATHLIB_FORM):
        for match in pattern.finditer(text):
            module = match.group("module")
            if (PROJECT_ROOT / "lib" / module).is_file():
                continue  # still exists under the old name; not a rename victim
            if not (PROJECT_ROOT / "cos_lib" / module).is_file():
                continue  # no counterpart -> placeholder or unrelated path
            yield module


def _strip_comment_lines(text: str) -> str:
    """Drop whole-line comments.

    Every one of the eight broken hooks documents the correct path in its header
    comment ("Runs cos_lib/rule_router.py ...") while the executable guard below
    still probes the dead one. Counting a comment as a fallback would make this
    audit blind to exactly the files it exists to catch.
    """
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


def _has_cos_lib_fallback(text: str, module: str) -> bool:
    """True when the same file also probes the cos_lib/ *path* for this module.

    Only path forms count. A `from cos_lib.<module> import ...` elsewhere in the
    file does NOT rescue a dead `lib/<module>.py` existence check: that is
    exactly the shape of the eight silently-disabled hooks, where a guard clause
    tests the old path, returns early, and the correct import below it never
    runs.
    """
    return any(
        candidate in text
        for candidate in (
            f"cos_lib/{module}",
            f'"cos_lib" / "{module}"',
            f"'cos_lib' / '{module}'",
        )
    )


def test_no_primitive_references_a_renamed_lib_module() -> None:
    dead: list[str] = []

    for path in _iter_primitive_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        rel = path.relative_to(PROJECT_ROOT)
        executable = _strip_comment_lines(text)
        for module in _renamed_modules(executable):
            if _has_cos_lib_fallback(executable, module):
                continue
            dead.append(f"{rel}: references lib/{module}, which now lives in cos_lib/")

    assert not dead, (
        "These primitives point at modules that moved to cos_lib/. Every one of "
        "these call sites fails soft, so the feature is silently disabled rather "
        "than raising:\n  " + "\n  ".join(sorted(set(dead)))
    )
