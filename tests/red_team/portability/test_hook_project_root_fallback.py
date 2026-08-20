# SPDX-License-Identifier: MIT
"""Gate: a hook invoked WITHOUT CLAUDE_PROJECT_DIR must resolve the project root.

Claude Code always exports ``CLAUDE_PROJECT_DIR``, so a broken fallback is
invisible there. Other harnesses (codex, opencode) and direct invocation do not
export it, and that is where the fallback decides where the hook reads config
from and where it writes caches, checkpoints and metrics.

The class of bug this gate exists for::

    PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

For a hook at ``<root>/hooks/x.sh`` that resolves to the PARENT of the repo; for
the same file at ``<root>/packages/<pkg>/hooks/x.sh`` it resolves to
``<root>/packages``. Both are outside the project.

Anti-tautology note: the expected root is NOT derived with the same expression
the hooks use. It is found by walking up from this test file until a directory
is reached that *contains* both ``.git`` and ``hooks/_lib`` — an identity check
on directory contents, not path arithmetic over ``$0``. Mutating the number of
``..`` segments in any hook flips this gate red.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

# The assignment this gate reads out of each hook, e.g.
#   PROJECT_DIR="${CLAUDE_PROJECT_DIR:-...}"
#   PROJECT_DIR="$(cos_project_root)"
_ASSIGN_RE = re.compile(r'^[ \t]*PROJECT_DIR=', re.MULTILINE)

# Plain scalar assignment at column 0, e.g. SCRIPT_DIR=... / HOOK_DIR=...
_SCALAR_ASSIGN_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')

# The defective idiom itself, kept as a fast static signal with a precise message.
_BAD_IDIOM_RE = re.compile(r'dirname\s+"\$0"\s*\)/\.\./\.\.')


def _find_project_root() -> Path:
    """Walk up from this file to the directory that IS the project root.

    Identity is decided by contents (a ``.git`` entry plus the canonical
    ``hooks/_lib`` directory), never by counting ``..`` segments.
    """
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".git").exists() and (candidate / "hooks" / "_lib").is_dir():
            return candidate
    raise RuntimeError("project root not found above %s" % __file__)


PROJECT_ROOT = _find_project_root()


def _hooks_declaring_project_dir(root: Path) -> list[Path]:
    return sorted(
        path
        for path in (root / "hooks").glob("*.sh")
        if _ASSIGN_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    )


_HOOK_ENV = {
    k: v
    for k, v in os.environ.items()
    if k not in {"CLAUDE_PROJECT_DIR", "COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR"}
}


def _is_self_contained(line: str) -> bool:
    """True when the line closes every quote and paren it opens.

    Prologue assignments that spill over several lines (an inline ``python3 -c``
    block, a ``CATEGORIES=(`` array) must not be carried in half, or the snippet
    stops parsing and a healthy hook is reported as unmeasurable.
    """
    return (
        line.count('"') % 2 == 0
        and line.count("'") % 2 == 0
        and line.count("(") == line.count(")")
        and line.count("{") == line.count("}")
    )


def _assignment_snippet(hook: Path) -> str | None:
    """Read the hook's PROJECT_DIR assignment verbatim, with the vars it needs.

    Three details matter for this to measure the shipped expression rather than
    a mangled excerpt:

    * A few hooks spread the assignment over two physical lines, so the window
      grows until ``bash -n`` accepts it.
    * Many hooks resolve the root through an earlier ``SCRIPT_DIR=``/``HOOK_DIR=``
      definition. Every plain scalar assignment appearing before the
      ``PROJECT_DIR=`` line is carried along; dropping them turned five correct
      hooks into false positives on the first run of this gate.
    * ``${BASH_SOURCE[0]}`` is rewritten to ``$0``. Under ``bash -c`` there is no
      source file, and for a hook that a harness executes directly the two
      denote the same path.
    """
    lines = hook.read_text(encoding="utf-8", errors="replace").splitlines()
    start = next((i for i, ln in enumerate(lines) if _ASSIGN_RE.match(ln)), None)
    if start is None:
        return None
    prologue = [
        ln
        for ln in lines[:start]
        if _SCALAR_ASSIGN_RE.match(ln) and _is_self_contained(ln)
    ]
    for end in range(start + 1, min(start + 6, len(lines)) + 1):
        snippet = "\n".join(prologue + lines[start:end])
        snippet = snippet.replace("${BASH_SOURCE[0]}", "$0")
        syntax = subprocess.run(
            ["bash", "-n", "-c", snippet], capture_output=True, text=True, timeout=30
        )
        if syntax.returncode == 0:
            return snippet
    return None


def resolve_as_hook_would(hook: Path, root: Path, cwd: Path) -> tuple[bool, str]:
    """Execute the hook's own PROJECT_DIR assignment with no harness env set.

    The snippet evaluated is read verbatim from the hook, so this measures the
    shipped expression, not a restatement of it. ``$0`` is set to the hook path
    exactly as a harness would invoke it. Returns ``(ok, value_or_error)``.
    """
    assignment = _assignment_snippet(hook)
    if assignment is None:
        return False, "PROJECT_DIR assignment could not be isolated"

    lib = root / "hooks" / "_lib" / "project-root.sh"
    preamble = f'source "{lib}"\n' if lib.is_file() else ""
    script = f"{preamble}{assignment}\nprintf '%s' \"$PROJECT_DIR\"\n"

    completed = subprocess.run(
        ["bash", "-c", script, str(hook)],
        cwd=str(cwd),
        env=_HOOK_ENV,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        return False, f"exit {completed.returncode}: {completed.stderr.strip()}"
    return True, completed.stdout.strip()


def check_root_resolution(root: Path, expected: Path) -> list[str]:
    """Return one failure line per hook that misresolves the root. Empty == green."""
    failures: list[str] = []
    for hook in _hooks_declaring_project_dir(root):
        ok, value = resolve_as_hook_would(hook, root, cwd=root)
        if not ok:
            failures.append(f"{hook.name}: {value}")
        elif Path(value).resolve() != expected.resolve():
            failures.append(f"{hook.name}: resolved {value!r}, expected {str(expected)!r}")
    return failures


@pytest.mark.red_team
def test_hooks_resolve_project_root_without_claude_project_dir() -> None:
    failures = check_root_resolution(PROJECT_ROOT, PROJECT_ROOT)
    assert not failures, (
        "Hooks resolve a project root outside the repository when "
        "CLAUDE_PROJECT_DIR is unset (codex / opencode / direct invocation):\n  "
        + "\n  ".join(failures)
        + "\n\nFix: source hooks/_lib/project-root.sh and use "
        '`PROJECT_DIR="$(cos_project_root)"`.'
    )


@pytest.mark.red_team
def test_no_hook_uses_the_two_level_dollar_zero_idiom() -> None:
    offenders = [
        path.name
        for path in sorted((PROJECT_ROOT / "hooks").glob("*.sh"))
        if _BAD_IDIOM_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    ]
    assert not offenders, (
        '`$(cd "$(dirname "$0")/../.." && pwd)` resolves to the PARENT of the '
        "repository for a hook in hooks/, and to <root>/packages for the same "
        "file at its package path. Offenders:\n  " + "\n  ".join(offenders)
    )


@pytest.mark.red_team
def test_gate_discriminates_against_a_planted_defect(tmp_path: Path) -> None:
    """Falsification: the checker must go red on a layout that has the bug.

    Without this, a checker that always returns [] would pass the two gates
    above forever.
    """
    fake_root = tmp_path / "proj"
    (fake_root / "hooks" / "_lib").mkdir(parents=True)
    (fake_root / ".git").mkdir()
    bad = fake_root / "hooks" / "planted.sh"
    bad.write_text(
        '#!/usr/bin/env bash\n'
        'PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"\n',
        encoding="utf-8",
    )
    failures = check_root_resolution(fake_root, fake_root)
    assert failures, "checker did not flag a hook carrying the known-bad idiom"
    assert "planted.sh" in failures[0]
