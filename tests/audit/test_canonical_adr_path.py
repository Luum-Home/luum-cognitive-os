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
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

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


def test_no_hardcoded_docs_adrs_in_production_code() -> None:
    """No Python module in scripts/ or lib/ may hardcode 'docs' / 'adrs'."""
    # Use git ls-files to scan only tracked files (avoids virtualenv, build, etc).
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "scripts/", "lib/"],
        capture_output=True,
        text=True,
        check=True,
    )
    tracked = [Path(p) for p in result.stdout.splitlines() if p.endswith((".py", ".sh"))]

    # Pattern: matches both Python `"docs" / "adrs"` and shell `docs/adrs`
    # but not the canonical `docs/02-Decisions/adrs`.
    py_pattern = re.compile(r'"docs"\s*/\s*"adrs"')
    sh_pattern = re.compile(r'(?<!2-Decisions/)\bdocs/adrs(?:/|"|\s|$)')

    offenders: list[tuple[Path, int, str]] = []
    for rel in tracked:
        if rel in ALLOWED_LEGACY_REFS:
            continue
        abs_path = REPO_ROOT / rel
        try:
            text = abs_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if py_pattern.search(line) or sh_pattern.search(line):
                offenders.append((rel, lineno, line.strip()[:120]))

    if offenders:
        msg = "Legacy docs/adrs path detected. Use docs/02-Decisions/adrs:\n" + "\n".join(
            f"  {p}:{ln} -> {snippet}" for p, ln, snippet in offenders
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
