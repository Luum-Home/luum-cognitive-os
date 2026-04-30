"""Enforcement test for ADR-087: ADR file location convention.

Every .md file matching the ADR naming pattern (ADR-[digits]*.md, case-insensitive)
must live in `docs/adrs/` — the single canonical root established by ADR-087.

Two explicit exemptions (per ADR-087 §"Canonical structure"):
  1. `docs/architecture/cos-dispatch/adrs/CD-*.md` — subsystem namespace with CD- prefix
  2. One-line redirect stubs (first line is `# Moved`) at old paths — migration artifacts
     governed by ADR-087, to be removed after one release cycle.

Violation = any file matching the ADR pattern found outside `docs/adrs/` that is
neither a cos-dispatch CD- file nor a one-line redirect stub.

This test EXECUTES the check (walks the filesystem) rather than relying on a
static fixture, satisfying the project's quality-gate requirement for audit tests.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

CANONICAL_ROOT = REPO / "docs" / "adrs"

# The cos-dispatch subsystem ADR directory.  Files in here with the CD- prefix
# are explicitly exempted per ADR-087 §"cos-dispatch namespace decision".
COS_DISPATCH_ADR_DIR = REPO / "docs" / "architecture" / "cos-dispatch" / "adrs"

# Pattern that identifies ADR files: starts with ADR- (case-insensitive) followed
# by digits, then anything, ending in .md.
_ADR_PATTERN = re.compile(r"^adr-\d", re.IGNORECASE)

# Pattern for cos-dispatch subsystem ADRs: starts with CD- followed by digits.
_CD_PATTERN = re.compile(r"^CD-\d", re.IGNORECASE)

# Text that marks a one-line redirect stub (first non-empty line of file).
_STUB_MARKER = "# Moved"


# Paths (relative to REPO) that contain "adr-" in their name but are NOT ADR
# documents — they are implementation plans, report artifacts, pending tasks,
# or other work products that legitimately reference an ADR by number in their
# filename.  Each entry is a relative path string; directory prefixes end with /.
#
# Rationale for each group:
#   .cognitive-os/pending-tasks/   — task queue files for individual ADR work items,
#                                    not the ADRs themselves.  Named by convention
#                                    to link task to its governing ADR.
#   .cognitive-os/plans/           — implementation plans (e.g. adr-049-050-051-mega-plan.md
#                                    is a sprint plan, not an ADR).
#   docs/reports/                  — audit/report artifacts that reference ADRs by number.
#   docs/architecture/harness-adoption-gap/adr-003-hook-registration-pending.md
#                                  — a pending-work note file, not the ADR itself (the
#                                    actual ADR-003 was migrated to ADR-094).
ALLOWLIST_RELATIVE: list[str] = [
    ".cognitive-os/pending-tasks/",
    ".cognitive-os/plans/",
    "docs/reports/",
    "docs/architecture/harness-adoption-gap/adr-003-hook-registration-pending.md",
]


def _is_allowlisted(path: Path) -> bool:
    """Return True if path is covered by the allowlist."""
    rel = str(path.relative_to(REPO))
    for entry in ALLOWLIST_RELATIVE:
        if entry.endswith("/"):
            if rel.startswith(entry):
                return True
        else:
            if rel == entry:
                return True
    return False


def _is_adr_file(path: Path) -> bool:
    """Return True if the filename matches the ADR naming pattern."""
    return bool(_ADR_PATTERN.match(path.name))


def _is_cos_dispatch_cd_file(path: Path) -> bool:
    """Return True if this is a cos-dispatch CD- subsystem ADR (exempted)."""
    try:
        path.relative_to(COS_DISPATCH_ADR_DIR)
    except ValueError:
        return False
    return bool(_CD_PATTERN.match(path.name))


def _is_redirect_stub(path: Path) -> bool:
    """Return True if the file is a one-line redirect stub.

    A redirect stub has '# Moved' as its first non-empty line — it was left
    at the old path after a git mv so external links continue to resolve.
    Per ADR-087 these stubs are migration artifacts, not real ADRs.
    """
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    return stripped == _STUB_MARKER
    except (OSError, UnicodeDecodeError):
        pass
    return False


def _skip_directory(parts: tuple[str, ...]) -> bool:
    """Return True if this path should be skipped entirely."""
    return any(
        p.startswith(".git") or p in ("node_modules", "__pycache__", ".venv", "venv")
        for p in parts
    )


@pytest.mark.audit
def test_no_adr_files_outside_canonical_root() -> None:
    """Walk the repo and assert no ADR-pattern .md files live outside
    `docs/adrs/`, except for exempted cos-dispatch CD- files and redirect stubs.

    Exemptions (per ADR-087):
      - docs/architecture/cos-dispatch/adrs/CD-NNN-*.md  (subsystem namespace)
      - Any file whose first non-empty line is '# Moved'  (migration stub)
    """
    violations: list[str] = []

    for md_file in REPO.rglob("*.md"):
        if md_file.is_symlink():
            continue

        if _skip_directory(md_file.parts):
            continue

        if not _is_adr_file(md_file):
            continue

        # File is in the canonical root → OK
        try:
            md_file.relative_to(CANONICAL_ROOT)
            continue
        except ValueError:
            pass

        # Exemption 1: cos-dispatch subsystem CD- file
        if _is_cos_dispatch_cd_file(md_file):
            continue

        # Exemption 2: redirect stub left after git mv
        if _is_redirect_stub(md_file):
            continue

        # Exemption 3: allowlisted non-ADR files that reference ADR numbers in name
        if _is_allowlisted(md_file):
            continue

        violations.append(str(md_file.relative_to(REPO)))

    assert not violations, (
        f"ADR-087 violation: {len(violations)} ADR file(s) found outside "
        f"`docs/adrs/`.\n"
        "Move them to docs/adrs/ or, if they are redirect stubs, ensure the first "
        "line is exactly '# Moved'.\n"
        "For cos-dispatch subsystem ADRs, rename with the CD- prefix.\n"
        "Violations:\n" + "\n".join(f"  - {v}" for v in sorted(violations))
    )


@pytest.mark.audit
def test_canonical_root_exists() -> None:
    """The canonical ADR root must exist."""
    assert CANONICAL_ROOT.is_dir(), (
        f"Canonical ADR root missing: {CANONICAL_ROOT.relative_to(REPO)}  "
        "(ADR-087 requires this directory to exist)"
    )


@pytest.mark.audit
def test_cos_dispatch_adrs_use_cd_prefix() -> None:
    """All .md files in the cos-dispatch ADR directory must use the CD- prefix.

    Files without the CD- prefix in that directory would be ambiguous — they
    could be confused with project-level ADRs by a recursive ADR search.
    The README is exempt.
    """
    if not COS_DISPATCH_ADR_DIR.is_dir():
        pytest.skip("cos-dispatch ADR directory does not exist")

    bad_files = []
    for md_file in COS_DISPATCH_ADR_DIR.glob("*.md"):
        if md_file.name == "README.md":
            continue
        if not _CD_PATTERN.match(md_file.name):
            bad_files.append(md_file.name)

    assert not bad_files, (
        f"cos-dispatch ADR files without CD- prefix (ADR-087 policy): {bad_files}\n"
        "Rename to CD-NNN-slug.md to make the subsystem namespace explicit."
    )


@pytest.mark.audit
def test_renumbered_adrs_have_front_matter_comment() -> None:
    """ADRs migrated with a number change must carry a Renumbered-from comment.

    This test verifies the four files renumbered during the ADR-087 migration:
      - ADR-091 (was 027 in docs/architecture/adrs/)
      - ADR-092 (was ADR-001 in harness-adoption-gap/)
      - ADR-093 (was ADR-002 in harness-adoption-gap/)
      - ADR-094 (was ADR-003 in harness-adoption-gap/)
    """
    renumbered = {
        "ADR-091-headless-clustered-runtime-direction.md": "Renumbered-from",
        "ADR-092-harness-skills-sync-path.md": "Renumbered-from",
        "ADR-093-simplify-profiles.md": "Renumbered-from",
        "ADR-094-agent-git-safety.md": "Renumbered-from",
    }
    missing_marker: list[str] = []

    for filename, marker in renumbered.items():
        path = CANONICAL_ROOT / filename
        if not path.exists():
            missing_marker.append(f"{filename} (file not found)")
            continue
        content = path.read_text(encoding="utf-8")
        if marker not in content:
            missing_marker.append(f"{filename} (missing '{marker}' comment)")

    assert not missing_marker, (
        "Renumbered ADRs must contain 'Renumbered-from' in their front matter "
        "(ADR-087 §'Renumbering policy'):\n"
        + "\n".join(f"  - {m}" for m in missing_marker)
    )
