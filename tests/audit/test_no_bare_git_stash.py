"""ADR-117 compliance gate: no bare 'git stash' in hook files.

Any hook file that contains 'git stash push', 'git stash pop', or a bare
'git stash' invocation MUST either:
  (a) Import/call stash_ops (or stash_lock), OR
  (b) Carry a '# STASH-LOCK-EXEMPT:' annotation in the file.

Files that fail this check are in violation of ADR-117 §5.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# Patterns that indicate bare stash usage (forbidden without exemption)
_BARE_STASH_RE = re.compile(
    r"^\s*(?:git stash(?:\s+push|\s+pop|$))",
    re.MULTILINE,
)

# Patterns that indicate compliant stash usage via the governed library
_STASH_OPS_RE = re.compile(r"stash_ops|stash_lock|STASH-LOCK-EXEMPT", re.MULTILINE)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_HOOK_DIRS = [
    _PROJECT_ROOT / "hooks",
    *sorted((_PROJECT_ROOT / "packages").glob("*/hooks")),
]


def _collect_hook_files() -> list[Path]:
    files: list[Path] = []
    for d in _HOOK_DIRS:
        if d.is_dir():
            for f in sorted(d.rglob("*")):
                if f.is_file() and not f.name.startswith("."):
                    try:
                        # Only process text files (skip binaries)
                        f.read_text(encoding="utf-8", errors="strict")
                        files.append(f)
                    except (UnicodeDecodeError, OSError):
                        pass
    return files


_HOOK_FILES = _collect_hook_files()


@pytest.mark.parametrize("hook_file", _HOOK_FILES, ids=lambda f: str(f.relative_to(_PROJECT_ROOT)))
def test_no_bare_git_stash_without_exemption(hook_file: Path):
    """Hook files must not use bare git stash without stash_ops or an exemption annotation."""
    text = hook_file.read_text(encoding="utf-8", errors="replace")

    if not _BARE_STASH_RE.search(text):
        # No bare stash usage — compliant
        return

    if _STASH_OPS_RE.search(text):
        # Uses stash_ops/stash_lock or has explicit exemption — compliant
        return

    pytest.fail(
        f"{hook_file.relative_to(_PROJECT_ROOT)}: contains bare 'git stash' usage "
        f"without importing stash_ops/stash_lock or a '# STASH-LOCK-EXEMPT:' annotation. "
        f"This violates ADR-117 §5. Either migrate to stash_ops.push_named() / "
        f"stash_ops.apply_by_name() or add a documented exemption comment."
    )


def test_hook_dirs_exist():
    """At least the main hooks/ directory must exist."""
    assert (_PROJECT_ROOT / "hooks").is_dir(), (
        "hooks/ directory not found — update _HOOK_DIRS if hook location changed."
    )


def test_bare_stash_regex_detects_forbidden_forms():
    """The compliance regex must catch the three forbidden git stash forms
    and reject benign mentions (comments, string substrings). This is the
    behavioral contract of the gate; mutating the regex must break a test."""
    assert _BARE_STASH_RE.search("git stash push -m foo")
    assert _BARE_STASH_RE.search("    git stash pop")
    assert _BARE_STASH_RE.search("git stash\n")
    assert not _BARE_STASH_RE.search("# discuss git stash strategy")
    assert not _BARE_STASH_RE.search("echo 'use stash_ops.push_named()'")
    # The compliance escape hatch must be recognized
    assert _STASH_OPS_RE.search("import stash_ops")
    assert _STASH_OPS_RE.search("# STASH-LOCK-EXEMPT: reason")
    assert not _STASH_OPS_RE.search("from foo import bar")
