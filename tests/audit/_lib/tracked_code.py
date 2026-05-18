"""Shared collectors for tracked code files in audit tests.

Background: ~122 of the project's scripts under `scripts/` and `lib/` are
extensionless executables whose first line is a shebang pointing at
python, bash, or sh (e.g. `scripts/cos-adr-close`, `scripts/cos`). Audit
tests that filtered by `endswith((".py", ".sh"))` silently skipped them
for years; this is how the docs/adrs hardcoded-path regression in
`scripts/cos-adr-close` slipped past `test_canonical_adr_path.py`.

To prevent the same blind spot from being reintroduced in future audits,
all audits that scan tracked source code SHOULD use the helpers in this
module instead of rolling their own glob/extension filter. Tests that
are intentionally per-extension (e.g. "*.py files must use snake_case")
remain extension-scoped; tests that scan code content for forbidden
patterns must use `tracked_code_files()`.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

_SHEBANG_RE = re.compile(rb"\b(python|bash|sh)\b")


def _has_code_shebang(abs_path: Path) -> bool:
    """True if the file's first line is a shebang naming python/bash/sh."""
    try:
        with abs_path.open("rb") as fh:
            head = fh.read(80)
    except OSError:
        return False
    if not head.startswith(b"#!"):
        return False
    first_line = head.split(b"\n", 1)[0]
    return bool(_SHEBANG_RE.search(first_line))


def _git_ls_files(roots: tuple[str, ...]) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", *roots],
        capture_output=True,
        text=True,
        check=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line]


def tracked_code_files(
    *roots: str,
    include_extensions: tuple[str, ...] = (".py", ".sh"),
    include_shebanged_extensionless: bool = True,
) -> list[Path]:
    """Enumerate tracked code files under the given git roots.

    By default returns files matching `include_extensions` plus extensionless
    files whose first line is a python/bash/sh shebang. Set
    `include_shebanged_extensionless=False` to restrict to extensions only
    (intentionally narrower audits).

    Paths are returned RELATIVE to repo root.
    """
    if not roots:
        roots = ("scripts/", "lib/")
    out: list[Path] = []
    for rel in _git_ls_files(roots):
        if rel.suffix in include_extensions:
            out.append(rel)
            continue
        if rel.suffix or not include_shebanged_extensionless:
            continue
        abs_path = REPO_ROOT / rel
        if abs_path.is_file() and _has_code_shebang(abs_path):
            out.append(rel)
    return out


def tracked_python_files(*roots: str) -> list[Path]:
    """Python source files (.py) plus extensionless scripts with a python shebang."""
    if not roots:
        roots = ("scripts/", "lib/")
    out: list[Path] = []
    for rel in _git_ls_files(roots):
        if rel.suffix == ".py":
            out.append(rel)
            continue
        if rel.suffix:
            continue
        abs_path = REPO_ROOT / rel
        if not abs_path.is_file():
            continue
        try:
            with abs_path.open("rb") as fh:
                first_line = fh.readline(80)
        except OSError:
            continue
        if first_line.startswith(b"#!") and b"python" in first_line:
            out.append(rel)
    return out


def tracked_bash_files(*roots: str) -> list[Path]:
    """Bash/sh source files (.sh) plus extensionless scripts with a bash/sh shebang."""
    if not roots:
        roots = ("scripts/", "hooks/", "lib/", "packages/")
    out: list[Path] = []
    for rel in _git_ls_files(roots):
        if rel.suffix == ".sh":
            out.append(rel)
            continue
        if rel.suffix:
            continue
        abs_path = REPO_ROOT / rel
        if not abs_path.is_file():
            continue
        try:
            with abs_path.open("rb") as fh:
                first_line = fh.readline(80)
        except OSError:
            continue
        if first_line.startswith(b"#!") and (b"bash" in first_line or first_line.rstrip().endswith(b"/sh")):
            out.append(rel)
    return out
