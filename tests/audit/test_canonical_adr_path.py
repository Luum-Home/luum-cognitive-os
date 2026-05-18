"""Regression audit — canonical docs/02-Decisions/adrs path.

Prevents the legacy `docs/adrs` bridge from being reintroduced as either
a symlink/directory or as a hardcoded path string in production code.

History: A compatibility symlink `docs/adrs -> 02-Decisions/adrs` existed
historically and was removed in favour of using the canonical path
directly. 14 modules in `scripts/` and `lib/` were patched to reference
`docs/02-Decisions/adrs` (fix(audit): canonical docs/02-Decisions/adrs
path). This test prevents reintroduction.

If this test fails:
- A `docs/adrs` symlink or directory has been re-created. Remove it.
- A new script/module is hardcoding `"docs" / "adrs"` again. Use the
  canonical `"docs" / "02-Decisions" / "adrs"` path.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.audit._lib.tracked_code import REPO_ROOT, tracked_code_files

# Allowlist: paths where the legacy string is acceptable.
#   - This test file itself (we name the legacy path to forbid it).
#   - Documentation describing the historical decision (ADR-284 area).
ALLOWED_LEGACY_REFS = {
    Path("tests/audit/test_canonical_adr_path.py"),
}


def test_docs_adrs_bridge_does_not_exist() -> None:
    """The legacy bridge `docs/adrs` must not exist as symlink or dir."""
    bridge = REPO_ROOT / "docs" / "adrs"
    if bridge.exists() or bridge.is_symlink():
        pytest.fail(
            f"Legacy bridge {bridge.relative_to(REPO_ROOT)} exists "
            f"(symlink={bridge.is_symlink()}, dir={bridge.is_dir()}). "
            "Remove it; refer to ADRs via docs/02-Decisions/adrs instead."
        )


# Legacy doc paths that were moved during the docs/ reorganization
# (00-MOCs … 09-Quality numbering). Each entry: (regex, canonical hint).
# History: the docs/ tree was reorganized into numbered top-level
# sections; any code still pointing at the pre-reorg paths is silently
# broken. Production scripts must reference the canonical paths.
_LEGACY_DOC_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r'"docs"\s*/\s*"adrs"'), "docs/02-Decisions/adrs"),
    (re.compile(r'(?<!2-Decisions/)\bdocs/adrs(?:/|"|\s|$)'), "docs/02-Decisions/adrs"),
    (re.compile(r'"docs"\s*/\s*"measurements"'), "docs/06-Daily/measurements"),
    (re.compile(r'"docs"\s*/\s*"security"'), "docs/09-Quality/security"),
    (re.compile(r'"docs"\s*/\s*"architecture"'), "docs/04-Concepts/architecture"),
    (re.compile(r'"docs"\s*/\s*"runtime-env-flags\.md"'), "docs/04-Concepts/root/runtime-env-flags.md"),
)


def test_no_hardcoded_docs_adrs_in_production_code() -> None:
    """No tracked code file in scripts/ or lib/ may hardcode legacy doc
    paths that were moved during the docs/ reorganization. Covers .py, .sh,
    and extensionless shebanged scripts."""
    offenders: list[tuple[Path, int, str, str]] = []
    for rel in tracked_code_files("scripts/", "lib/"):
        if rel in ALLOWED_LEGACY_REFS:
            continue
        abs_path = REPO_ROOT / rel
        try:
            text = abs_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern, canonical in _LEGACY_DOC_PATTERNS:
                if pattern.search(line):
                    offenders.append((rel, lineno, line.strip()[:120], canonical))

    if offenders:
        msg = "Legacy doc path detected in production code:\n" + "\n".join(
            f"  {p}:{ln} -> {snippet}\n    expected: {canonical}"
            for p, ln, snippet, canonical in offenders
        )
        pytest.fail(msg)


def test_canonical_adr_directory_is_reachable() -> None:
    """The canonical ADR directory must exist with at least one ADR file."""
    canonical = REPO_ROOT / "docs" / "02-Decisions" / "adrs"
    assert canonical.is_dir(), (
        f"Canonical ADR directory {canonical.relative_to(REPO_ROOT)} missing."
    )
    adrs = list(canonical.glob("ADR-*.md"))
    assert len(adrs) > 0, (
        f"No ADR files found under {canonical.relative_to(REPO_ROOT)}; "
        "expected docs/02-Decisions/adrs/ADR-*.md."
    )
