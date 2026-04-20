# SCOPE: both
"""Targeted test resolver — ADR-027 Phase 1.

Given a list of changed files (from `git diff --name-only`), returns the set
of test file paths likely to exercise the changed code. Used by
`hooks/global-verify.sh` to run a focused baseline + after suite instead of
the full 9,000-test collection.

Resolution strategy (naming conventions in this repo):

    lib/foo.py                     → tests/unit/test_foo.py
                                     tests/behavior/test_foo.py
    packages/pkg/lib/foo.py        → tests/unit/test_foo.py
                                     tests/behavior/test_foo.py
    hooks/foo.sh                   → tests/hooks/test_foo.py
                                     tests/behavior/test_foo.py
    packages/pkg/hooks/foo.sh      → tests/hooks/test_foo.py
    scripts/foo.sh                 → tests/integration/test_foo.py
    tests/**/test_*.py             → itself
    docs/**, rules/**, *.md        → skipped (no tests)

If a candidate test file does not exist, it is dropped. If zero tests resolve,
the caller should fall back to a broader suite or skip verification.

Public API:
    resolve_tests_for_changes(changed_files: List[str]) -> List[str]
        Returns existing test file paths as strings relative to the project root.

Python 3.9+ compatible, stdlib only.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, List, Set


def _project_root() -> Path:
    return Path(
        os.environ.get(
            "COGNITIVE_OS_PROJECT_DIR",
            os.environ.get("CLAUDE_PROJECT_DIR", str(Path(__file__).resolve().parent.parent)),
        )
    )


def _stem_from_filename(filename: str) -> str:
    """Return 'foo' from 'foo.py', 'foo.sh', 'test_foo.py', etc."""
    name = os.path.basename(filename)
    # Drop extension
    name = re.sub(r"\.[^.]+$", "", name)
    # Drop common test prefixes so we can re-derive test-file names
    name = re.sub(r"^test_", "", name)
    return name


def _candidate_paths_for(file_path: str) -> List[Path]:
    """Map a source path to possible test-file locations (as Path objects,
    relative to project root, not yet checked for existence)."""
    root = _project_root()
    path = Path(file_path)
    parts = path.parts

    candidates: List[Path] = []

    # A test file changed: run itself
    if len(parts) >= 2 and parts[0] == "tests" and path.name.startswith("test_"):
        candidates.append(root / path)
        return candidates

    stem = _stem_from_filename(path.name)
    suffix = path.suffix

    # Source-file conventions
    if suffix == ".py":
        if len(parts) >= 2 and parts[0] == "lib":
            candidates += [
                root / "tests" / "unit" / f"test_{stem}.py",
                root / "tests" / "behavior" / f"test_{stem}.py",
            ]
        elif len(parts) >= 4 and parts[0] == "packages" and parts[2] == "lib":
            # packages/<pkg>/lib/<file>.py
            candidates += [
                root / "tests" / "unit" / f"test_{stem}.py",
                root / "tests" / "behavior" / f"test_{stem}.py",
            ]
    elif suffix == ".sh":
        if len(parts) >= 2 and parts[0] == "hooks":
            candidates += [
                root / "tests" / "hooks" / f"test_{stem}.py",
                root / "tests" / "behavior" / f"test_{stem}.py",
            ]
        elif len(parts) >= 4 and parts[0] == "packages" and parts[2] == "hooks":
            candidates += [
                root / "tests" / "hooks" / f"test_{stem}.py",
                root / "tests" / "behavior" / f"test_{stem}.py",
            ]
        elif len(parts) >= 2 and parts[0] == "scripts":
            candidates += [
                root / "tests" / "integration" / f"test_{stem}.py",
            ]

    # docs/*, rules/*, *.md, cognitive-os.yaml: no tests
    return candidates


def resolve_tests_for_changes(changed_files: Iterable[str]) -> List[str]:
    """Return existing test file paths (strings) that cover the changed files.

    Deduplicates, returns a stable-sorted list. Callers pass the result directly
    as positional args to `pytest`.
    """
    seen: Set[Path] = set()
    resolved: List[Path] = []

    for fp in changed_files:
        fp = (fp or "").strip()
        if not fp:
            continue
        for candidate in _candidate_paths_for(fp):
            if candidate in seen:
                continue
            if candidate.is_file():
                seen.add(candidate)
                resolved.append(candidate)

    resolved.sort()
    # Return paths relative to project root for stable pytest display
    root = _project_root()
    return [str(p.relative_to(root)) for p in resolved]


__all__ = ["resolve_tests_for_changes"]


class TargetedTestResolver:
    """Namespace class for lib.targeted_test_resolver.

    Canonical API is the module-level `resolve_tests_for_changes` function.
    This class is a thin facade so `from lib.targeted_test_resolver import
    TargetedTestResolver` also works, matching ADR-027 Phase 1 references.
    """

    resolve_tests_for_changes = staticmethod(resolve_tests_for_changes)


# Re-declare __all__ at end so the class is exported too.
__all__ = ["resolve_tests_for_changes", "TargetedTestResolver"]
