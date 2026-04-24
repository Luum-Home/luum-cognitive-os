"""Cross-platform discipline tests.

Validates that shell scripts in hooks/ and scripts/ do not contain
BSD-only or GNU-only constructs that will break on the other platform.

These tests are the enforcement layer — they run in CI on both macOS
and Linux (see .github/workflows/cross-platform.yml).

Banned patterns (per portability audit 2026-04-20):
  - date -v          (BSD-only date adjustment)
  - sed -i ''        (BSD-only in-place syntax)
  - mapfile          (bash 4+ only, breaks macOS bash 3.2)
  - readarray        (bash 4+ only, breaks macOS bash 3.2)
  - stat -f          (BSD stat flag; GNU uses stat -c)
  - stat -c          (GNU stat flag; BSD uses stat -f)

Files exempt from ALL checks:
  - hooks/_lib/portable.sh  (implements the portable wrappers)
  - hooks/_archived/**      (archived files are not executed)

Comment lines (lines whose first non-space character is #) are excluded
from pattern scanning, as comments may legitimately explain why a pattern
is banned without using it.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Iterator

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[2]
PORTABLE_SH = PROJECT_DIR / "hooks" / "_lib" / "portable.sh"

# Files that are EXEMPT from anti-pattern checks (implement the portability layer)
EXEMPT_FILES = {
    PORTABLE_SH,
}

# Files that are exempt from shebang checks (library files, not scripts)
SHEBANG_EXEMPT_PATTERNS = [
    r"hooks/_lib/",   # library files may not have shebangs
]

# Pre-existing violations that are tracked but not yet migrated.
# These use xfail so CI shows them as expected failures, not hard failures.
# Remove entries once fixed.
PRE_EXISTING_GNU_VIOLATIONS: set[str] = {
    "scripts/doctor.sh",
    "hooks/_lib/file_checker.sh",
    "hooks/adr-detector.sh",
    "hooks/recap-sync.sh",
    "hooks/subagent-context-injector.sh",
}

PRE_EXISTING_SHEBANG_VIOLATIONS: set[str] = {
    "scripts/engram-sync.sh",
    "hooks/doc-sync-detector.sh",
    "hooks/engram-auto-import.sh",
    "hooks/engram-auto-sync.sh",
    "hooks/error-pattern-detector.sh",
    "hooks/error-pipeline.sh",
    "hooks/kpi-trigger.sh",
    "hooks/result-truncator.sh",
    "hooks/session-learning.sh",
    "hooks/sync-to-repo.sh",
    # cos-config-audit.sh is a Python script with .sh extension (polyglot file).
    # It has #!/usr/bin/env python3 — intentional, not a portability bug.
    "scripts/cos-config-audit.sh",
}

# Files that contain non-bash shebangs (e.g. Python scripts named .sh).
# These are excluded from bash -n syntax checks.
NON_BASH_SH_FILES: set[str] = {
    "scripts/cos-config-audit.sh",
}


def iter_shell_files() -> Iterator[Path]:
    """Yield all .sh files under scripts/ and hooks/ (excluding _archived)."""
    for directory in [PROJECT_DIR / "scripts", PROJECT_DIR / "hooks"]:
        if not directory.is_dir():
            continue
        for f in sorted(directory.rglob("*.sh")):
            if "_archived" in f.parts:
                continue
            yield f


def is_code_line(line: str) -> bool:
    """Return True when line is actual code (not a comment or blank)."""
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


ALL_SHELL_FILES = list(iter_shell_files())
if not ALL_SHELL_FILES:
    pytest.skip("No shell files found", allow_module_level=True)


# ---------------------------------------------------------------------------
# Core banned-pattern enforcement (the acceptance-criteria check)
# ---------------------------------------------------------------------------

# Patterns that must NOT appear in production code lines.
# Tuples of: (regex, human label, fix hint)
BANNED_PATTERNS = [
    (
        r"\bdate\s+-v",
        "date -v (BSD-only date adjustment)",
        "Use portable_date_minus from hooks/_lib/portable.sh",
    ),
    (
        r"sed\s+-i\s+''",
        "sed -i '' (BSD-only in-place syntax)",
        "Use portable_sed_inplace from hooks/_lib/portable.sh",
    ),
    (
        r"\bmapfile\b",
        "mapfile (bash 4+ only, breaks macOS bash 3.2)",
        "Use portable_readlines from hooks/_lib/portable.sh",
    ),
    (
        r"\breadarray\b",
        "readarray (bash 4+ only, breaks macOS bash 3.2)",
        "Use portable_readlines from hooks/_lib/portable.sh",
    ),
    (
        r"\bstat\s+-f\b",
        "stat -f (BSD stat syntax; GNU uses stat -c)",
        "Use portable_stat_mtime or portable_stat_size from hooks/_lib/portable.sh",
    ),
    (
        r"\bstat\s+-c\b",
        "stat -c (GNU stat syntax; BSD uses stat -f)",
        "Use portable_stat_mtime or portable_stat_size from hooks/_lib/portable.sh",
    ),
]


@pytest.mark.parametrize(
    "shell_file",
    ALL_SHELL_FILES,
    ids=lambda p: str(p.relative_to(PROJECT_DIR)),
)
def test_no_banned_portability_patterns(shell_file: Path):
    """Shell files must not contain any of the 6 banned non-portable patterns.

    This is the canonical enforcement of the portability migration requirement.
    Checks: date -v, sed -i '', mapfile, readarray, stat -f, stat -c.
    Exempt: hooks/_lib/portable.sh (the implementation of the wrappers).
    Comment lines are excluded from scanning.
    """
    if shell_file in EXEMPT_FILES:
        pytest.skip(f"{shell_file.name} is the portable-helpers library — exempt")

    content = shell_file.read_text(errors="replace")
    violations: list[str] = []

    for lineno, line in enumerate(content.splitlines(), 1):
        if not is_code_line(line):
            continue
        for pattern, label, fix in BANNED_PATTERNS:
            if re.search(pattern, line):
                violations.append(
                    f"  Line {lineno}: {label}\n"
                    f"    Fix: {fix}\n"
                    f"    Code: {line.strip()}"
                )

    assert not violations, (
        f"Non-portable patterns found in {shell_file.relative_to(PROJECT_DIR)}:\n"
        + "\n".join(violations)
        + "\n\nSee hooks/_lib/portable.sh for portable replacements."
    )


# ---------------------------------------------------------------------------
# Additional discipline checks (broader portability surface)
# ---------------------------------------------------------------------------

BSD_ONLY_PATTERNS = [
    (
        r"\bdate\s+-r\s+['\"]?/",
        "date -r <file> (BSD-only mtime via date)",
        "Use portable_stat_mtime from hooks/_lib/portable.sh",
    ),
]

GNU_ONLY_PATTERNS = [
    (
        r"\bdate\s+--date[= ]",
        "date --date (GNU-only long flag)",
        "Use portable_date_minus from hooks/_lib/portable.sh",
    ),
    (
        r"\bstat\s+--format[= ]",
        "stat --format (GNU-only, macOS uses -f)",
        "Use portable_stat_mtime from hooks/_lib/portable.sh",
    ),
    (
        r"\bsort\s+--parallel[= ]",
        "sort --parallel (GNU-only)",
        "Remove --parallel or guard with OS detection",
    ),
]

PORTABILITY_PATTERNS = [
    (
        r"\breadlink\s+-f",
        "readlink -f (requires GNU coreutils on macOS)",
        "Use: python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))'",
    ),
]


@pytest.mark.parametrize(
    "shell_file",
    ALL_SHELL_FILES,
    ids=lambda p: str(p.relative_to(PROJECT_DIR)),
)
def test_no_bsd_only_patterns(shell_file: Path):
    """Shell files must not contain BSD-only constructs (beyond the 6 core banned)."""
    if shell_file in EXEMPT_FILES:
        pytest.skip(f"{shell_file.name} is the portable-helpers library — exempt")

    content = shell_file.read_text(errors="replace")
    violations = []
    for lineno, line in enumerate(content.splitlines(), 1):
        if not is_code_line(line):
            continue
        for pattern, description, suggestion in BSD_ONLY_PATTERNS:
            if re.search(pattern, line):
                violations.append(
                    f"  Line {lineno}: {description}\n"
                    f"    Fix: {suggestion}\n"
                    f"    Code: {line.strip()}"
                )

    assert not violations, (
        f"BSD-only constructs found in {shell_file.relative_to(PROJECT_DIR)}:\n"
        + "\n".join(violations)
    )


@pytest.mark.parametrize(
    "shell_file",
    ALL_SHELL_FILES,
    ids=lambda p: str(p.relative_to(PROJECT_DIR)),
)
def test_no_gnu_only_patterns(shell_file: Path):
    """Shell files must not contain GNU-only constructs."""
    if shell_file in EXEMPT_FILES:
        pytest.skip(f"{shell_file.name} is the portable-helpers library — exempt")

    rel = shell_file.relative_to(PROJECT_DIR).as_posix()
    if rel in PRE_EXISTING_GNU_VIOLATIONS:
        pytest.xfail(
            f"Pre-existing GNU-only violation in {rel} — pending migration. "
            "Remove from PRE_EXISTING_GNU_VIOLATIONS once fixed."
        )

    content = shell_file.read_text(errors="replace")
    violations = []
    for lineno, line in enumerate(content.splitlines(), 1):
        if not is_code_line(line):
            continue
        for pattern, description, suggestion in GNU_ONLY_PATTERNS + PORTABILITY_PATTERNS:
            if re.search(pattern, line):
                violations.append(
                    f"  Line {lineno}: {description}\n"
                    f"    Fix: {suggestion}\n"
                    f"    Code: {line.strip()}"
                )

    assert not violations, (
        f"GNU-only or non-portable constructs found in {shell_file.relative_to(PROJECT_DIR)}:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Shebang discipline
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "shell_file",
    ALL_SHELL_FILES,
    ids=lambda p: str(p.relative_to(PROJECT_DIR)),
)
def test_env_shebang(shell_file: Path):
    """Executable shell scripts should use #!/usr/bin/env bash for portability."""
    rel = shell_file.relative_to(PROJECT_DIR).as_posix()

    # Skip library files
    if any(re.search(pat, rel) for pat in SHEBANG_EXEMPT_PATTERNS):
        pytest.skip("Library file exempt from shebang check")

    if rel in PRE_EXISTING_SHEBANG_VIOLATIONS:
        pytest.xfail(
            f"Pre-existing shebang issue in {rel} — pending migration. "
            "Remove from PRE_EXISTING_SHEBANG_VIOLATIONS once fixed."
        )

    content = shell_file.read_text(errors="replace")
    lines = content.splitlines()
    if not lines or not lines[0].startswith("#!"):
        return  # no shebang — sourced library, not a standalone script

    first_line = lines[0]
    assert first_line in (
        "#!/usr/bin/env bash",
        "#!/usr/bin/env sh",
    ), (
        f"Non-portable shebang in {rel}: {first_line!r}\n"
        "Use '#!/usr/bin/env bash' instead of '#!/bin/bash'."
    )


# ---------------------------------------------------------------------------
# Syntax checks
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "shell_file",
    ALL_SHELL_FILES,
    ids=lambda p: str(p.relative_to(PROJECT_DIR)),
)
def test_bash_syntax(shell_file: Path):
    """Every shell file must pass bash -n syntax check.

    Files with non-bash shebangs (e.g. Python scripts with .sh extension)
    are skipped — bash -n cannot parse Python/other languages.
    """
    rel = shell_file.relative_to(PROJECT_DIR).as_posix()
    if rel in NON_BASH_SH_FILES:
        pytest.skip(
            f"{rel} has a non-bash shebang (see NON_BASH_SH_FILES) — "
            "bash -n does not apply to non-bash scripts"
        )

    result = subprocess.run(
        ["bash", "-n", str(shell_file)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"bash -n failed for {shell_file.relative_to(PROJECT_DIR)}:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# Migrated files source portable.sh
# ---------------------------------------------------------------------------

MIGRATED_FILES = [
    "hooks/error-pattern-detector.sh",
    "hooks/cognitive-os-health.sh",
    "hooks/error-pipeline.sh",
    "hooks/token-budget-monitor.sh",
    "scripts/setup-git-hooks.sh",
    "scripts/cos-bootstrap.sh",
    "scripts/version.sh",
    "scripts/register-mcps.sh",
    "scripts/cos-update.sh",
    "scripts/cos-status.sh",
    "scripts/startup-benchmark.sh",
    "hooks/pre-cleanup-snapshot.sh",
    "hooks/_lib/safe-jsonl.sh",
    "hooks/agent-working-dir-inject.sh",
    "hooks/session-init.sh",
]


@pytest.mark.parametrize("rel_path", MIGRATED_FILES)
def test_migrated_file_sources_portable_sh(rel_path: str):
    """Every migrated file must source hooks/_lib/portable.sh."""
    f = PROJECT_DIR / rel_path
    assert f.is_file(), f"Migrated file not found: {rel_path}"
    content = f.read_text(errors="replace")
    assert "portable.sh" in content, (
        f"{rel_path} does not source hooks/_lib/portable.sh.\n"
        "Add: source \"$(dirname \"${{BASH_SOURCE[0]}}\")/_lib/portable.sh\" "
        "(adjust relative path as needed)"
    )
