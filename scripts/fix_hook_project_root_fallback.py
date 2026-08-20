#!/usr/bin/env python3
# SCOPE: os-only
# SPDX-License-Identifier: MIT
"""Apply the project-root fallback fix to hooks that resolve the wrong root.

Thirteen hooks derive their fallback project root as::

    PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

For a hook at ``<root>/hooks/x.sh`` that is the PARENT of the repository; at the
package path ``<root>/packages/<pkg>/hooks/x.sh`` it is ``<root>/packages``.
Claude Code always exports ``CLAUDE_PROJECT_DIR`` so the fallback never fires
there — it fires under codex/opencode/bare invocation.

This script (idempotent):
  1. writes ``hooks/_lib/project-root.sh`` (the shared resolver), and
  2. rewrites each offending assignment to ``PROJECT_DIR="$(cos_project_root)"``,
     inserting the ``source`` line for the resolver if the hook lacks it.

``hooks/**`` is a protected control-plane path in this repo, so running this
against the real tree needs the operator's own approval:

    COS_ALLOW_PROTECTED_CONFIG_WRITE=1 .venv/bin/python3 \\
        scripts/fix_hook_project_root_fallback.py

``--root`` points the same transformation at a throwaway tree, which is how the
counterfactual for ``tests/red_team/portability/test_hook_project_root_fallback.py``
is produced (red before, green after, same tree).

Exit codes: 0 nothing to do / 1 files changed / 2 error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LIB_RELPATH = Path("hooks/_lib/project-root.sh")

LIB_SOURCE = '''#!/usr/bin/env bash
# SCOPE: both
# project-root.sh — single source of truth for "which directory is the project root".
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/_lib/project-root.sh"
#   PROJECT_DIR="$(cos_project_root)"
#
# Why this exists:
#   Hooks used to derive their fallback root as
#       PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
#   For a hook living in <root>/hooks/ that resolves to the PARENT of the
#   repository; for the same file at <root>/packages/<pkg>/hooks/ it resolves to
#   <root>/packages. Neither is the project root. Claude Code always exports
#   CLAUDE_PROJECT_DIR, so the fallback never fires there; it fires under
#   codex/opencode/bare invocation, where nobody is watching.
#
# Resolution order:
#   1. COGNITIVE_OS_PROJECT_DIR   (harness-agnostic override)
#   2. CODEX_PROJECT_DIR
#   3. CLAUDE_PROJECT_DIR
#   4. Structural anchor: this library's own PHYSICAL location. Every hook
#      reaches this file through <root>/hooks/_lib/ — package hook dirs expose
#      _lib as a symlink to ../../../hooks/_lib, so `pwd -P` collapses every
#      invocation path onto the one canonical directory. Two segments up from
#      <root>/hooks/_lib is <root>, by construction.
#
# Deliberately NOT used as the anchor:
#   - "$0" / "${BASH_SOURCE[0]}" of the CALLING hook: varies with invocation
#     path — that is precisely the bug being fixed.
#   - "$(pwd)" or `git rev-parse --show-toplevel` from the cwd: a hook may run
#     with any cwd, including inside a worktree or a nested repository.

[ "${_COS_PROJECT_ROOT_SH_LOADED:-}" = "true" ] && return 0
_COS_PROJECT_ROOT_SH_LOADED="true"

# Physical directory of THIS file (symlinks resolved by `pwd -P`).
_COS_PROJECT_ROOT_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Two path segments up from <root>/hooks/_lib.
_COS_PROJECT_ROOT_ANCHORED="${_COS_PROJECT_ROOT_LIB_DIR%/*/*}"

cos_project_root() {
  if [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
    printf '%s\\n' "$COGNITIVE_OS_PROJECT_DIR"
  elif [ -n "${CODEX_PROJECT_DIR:-}" ]; then
    printf '%s\\n' "$CODEX_PROJECT_DIR"
  elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    printf '%s\\n' "$CLAUDE_PROJECT_DIR"
  else
    printf '%s\\n' "$_COS_PROJECT_ROOT_ANCHORED"
  fi
}
'''

SOURCE_LINE = 'source "$(dirname "${BASH_SOURCE[0]}")/_lib/project-root.sh"'
NEW_ASSIGNMENT = 'PROJECT_DIR="$(cos_project_root)"'

# The defective assignment, in both shapes that occur in the tree.
BAD_ASSIGN_RE = re.compile(
    r'^[ \t]*PROJECT_DIR="\$\{[^\n]*\$\(cd "\$\(dirname "\$0"\)/\.\./\.\." && pwd\)[^\n]*$',
    re.MULTILINE,
)


def resolve_target(root: Path, name: str) -> Path:
    """Return the real file behind hooks/<name>, following the package symlink.

    Six of the offenders are symlinks into ``packages/*/hooks/``; writing through
    the symlink would be refused, and editing the wrong end would leave the two
    out of sync.
    """
    return (root / "hooks" / name).resolve()


def patch_hook(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if not BAD_ASSIGN_RE.search(text):
        return False
    patched = BAD_ASSIGN_RE.sub(NEW_ASSIGNMENT, text)
    if SOURCE_LINE not in patched:
        lines = patched.splitlines()
        target = next(
            (i for i, ln in enumerate(lines) if ln.startswith(NEW_ASSIGNMENT)), None
        )
        if target is None:  # pragma: no cover - sub() just inserted it
            raise RuntimeError(f"{path}: patched assignment vanished")
        # Sit next to the existing _lib sourcing block when there is one, so the
        # resolver is loaded before anything that might early-exit.
        last_source = max(
            (i for i, ln in enumerate(lines[:target]) if ln.startswith("source ")),
            default=None,
        )
        insert_at = (last_source + 1) if last_source is not None else target
        lines.insert(insert_at, SOURCE_LINE)
        patched = "\n".join(lines) + "\n"
    path.write_text(patched, encoding="utf-8")
    return True


def offenders(root: Path) -> list[str]:
    return sorted(
        p.name
        for p in (root / "hooks").glob("*.sh")
        if BAD_ASSIGN_RE.search(p.read_text(encoding="utf-8", errors="replace"))
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent.parent),
        help="tree to patch (default: this repository)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not (root / "hooks").is_dir():
        print(f"error: {root} has no hooks/ directory", file=sys.stderr)
        return 2

    names = offenders(root)
    if not names:
        print("nothing to do: no hook carries the two-level $0 fallback")
        return 0

    print(f"root: {root}")
    print(f"offending hooks: {len(names)}")
    if args.dry_run:
        for name in names:
            print(f"  would patch {name} -> {resolve_target(root, name)}")
        return 1

    lib_path = root / LIB_RELPATH
    lib_path.parent.mkdir(parents=True, exist_ok=True)
    if lib_path.read_text(encoding="utf-8") != LIB_SOURCE if lib_path.exists() else True:
        lib_path.write_text(LIB_SOURCE, encoding="utf-8")
        lib_path.chmod(0o755)
        print(f"  wrote {LIB_RELPATH}")

    for name in names:
        target = resolve_target(root, name)
        changed = patch_hook(target)
        print(f"  {'patched' if changed else 'unchanged'} {name} -> {target.relative_to(root)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
