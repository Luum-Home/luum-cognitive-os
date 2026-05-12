"""CI gate for ADR YAML frontmatter — validates the 5 migrated ADRs.

Verifies that:
1. Each of the 5 migrated ADRs (105, 116, 119, 121, 123) has valid YAML
   frontmatter parseable by yaml.safe_load().
2. Required fields (adr, title, status, date) are present and typed correctly.
3. ADRs with status=implemented have all declared implementation_files on disk
   (resolved via Path.resolve() for symlink-awareness per project rules).
4. The audit_adrs.py script is importable and run_audit() returns no FAIL
   findings for the 5 migrated ADRs.

Lane: audit (parallel-safe — read-only checks, no mutation).

Run:
    uv run pytest tests/audit/test_adrs_frontmatter.py -v
    uv run pytest tests/audit/test_adrs_frontmatter.py -v -m audit
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

# ── Repo root and ADR paths ───────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
ADRS_DIR = REPO_ROOT / "docs" / "adrs"

MIGRATED_ADRS: dict[int, Path] = {
    105: ADRS_DIR / "ADR-105-claim-verification-contract.md",
    116: ADRS_DIR / "ADR-116-multi-session-coordination-primitives.md",
    119: ADRS_DIR / "ADR-119-session-filesystem-reaper.md",
    121: ADRS_DIR / "ADR-121-foundation-hardening-program.md",
    123: ADRS_DIR / "ADR-123-operational-stability-friction-reduction.md",
}

VALID_STATUSES = {"proposed", "exploration", "accepted", "implemented", "resolved", "superseded", "deprecated", "tombstone"}
VALID_TIERS = {"lean", "standard", "strict", "meta", "maintainer"}
VALID_IMPLEMENTATION_STATUSES = {"not-applicable", "planned", "partial", "partial-blocked", "blocked", "deferred", "implemented", "resolved"}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    """Extract and parse YAML frontmatter from an ADR file.

    Raises AssertionError with a descriptive message on any parse failure so
    that test failures are readable without stack traces.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    assert lines, f"{path.name}: file is empty"
    assert lines[0].rstrip() == "---", (
        f"{path.name}: first line must be '---' (got {lines[0]!r})"
    )

    closing_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip() == "---":
            closing_idx = i
            break

    assert closing_idx is not None, f"{path.name}: no closing '---' found"

    fm_str = "\n".join(lines[1:closing_idx])
    parsed = yaml.safe_load(fm_str)
    assert isinstance(parsed, dict), (
        f"{path.name}: frontmatter parsed but is not a YAML mapping (got {type(parsed)})"
    )
    return parsed


def _file_exists_resolved(rel_path: str) -> bool:
    """Check file existence using Path.resolve() (symlink-aware)."""
    return (REPO_ROOT / rel_path).resolve().exists()


# ── Parametrized fixtures ─────────────────────────────────────────────────────


@pytest.fixture(params=sorted(MIGRATED_ADRS.keys()), ids=lambda n: f"ADR-{n}")
def migrated_adr(request: pytest.FixtureRequest) -> tuple[int, Path, dict[str, Any]]:
    """Yield (adr_number, path, parsed_frontmatter) for each migrated ADR."""
    num: int = request.param
    path = MIGRATED_ADRS[num]
    assert path.exists(), f"ADR file not found: {path}"
    fm = _parse_frontmatter(path)
    return num, path, fm


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.audit
def test_frontmatter_file_exists(migrated_adr: tuple[int, Path, dict]) -> None:
    """Each migrated ADR file must exist on disk."""
    _, path, _ = migrated_adr
    assert path.exists(), f"ADR file missing: {path}"


@pytest.mark.audit
def test_frontmatter_parses(migrated_adr: tuple[int, Path, dict]) -> None:
    """Frontmatter must be valid YAML that parses to a dict."""
    _, _, fm = migrated_adr
    assert isinstance(fm, dict), "Frontmatter must be a YAML mapping"


@pytest.mark.audit
def test_required_fields_present(migrated_adr: tuple[int, Path, dict]) -> None:
    """Required fields adr, title, status, date must all be present."""
    _, path, fm = migrated_adr
    for field in ("adr", "title", "status", "date", "implementation_status"):
        assert field in fm, f"{path.name}: missing required field '{field}'"


@pytest.mark.audit
def test_adr_field_is_integer(migrated_adr: tuple[int, Path, dict]) -> None:
    """'adr' field must be an integer."""
    _, path, fm = migrated_adr
    assert isinstance(fm["adr"], int), (
        f"{path.name}: 'adr' must be an integer, got {type(fm['adr'])}"
    )


@pytest.mark.audit
def test_adr_number_matches_filename(migrated_adr: tuple[int, Path, dict]) -> None:
    """The 'adr' number in frontmatter must match the number in the filename."""
    expected_num, path, fm = migrated_adr
    assert fm["adr"] == expected_num, (
        f"{path.name}: frontmatter adr={fm['adr']} does not match "
        f"expected {expected_num} from filename"
    )


@pytest.mark.audit
def test_implementation_status_is_valid(migrated_adr: tuple[int, Path, dict]) -> None:
    """implementation_status must be one of the canonical taxonomy values."""
    _, path, fm = migrated_adr
    assert fm["implementation_status"] in VALID_IMPLEMENTATION_STATUSES, (
        f"{path.name}: invalid implementation_status {fm['implementation_status']!r}"
    )


@pytest.mark.audit
def test_status_is_valid_value(migrated_adr: tuple[int, Path, dict]) -> None:
    """'status' must be one of the schema-defined values."""
    _, path, fm = migrated_adr
    status = fm.get("status", "")
    assert status in VALID_STATUSES, (
        f"{path.name}: status={status!r} is not one of {sorted(VALID_STATUSES)}"
    )


@pytest.mark.audit
def test_tier_is_valid_when_present(migrated_adr: tuple[int, Path, dict]) -> None:
    """'tier' must be one of the schema-defined values when present."""
    _, path, fm = migrated_adr
    tier = fm.get("tier")
    if tier is not None:
        assert tier in VALID_TIERS, (
            f"{path.name}: tier={tier!r} is not one of {sorted(VALID_TIERS)}"
        )


@pytest.mark.audit
def test_supersedes_is_list(migrated_adr: tuple[int, Path, dict]) -> None:
    """'supersedes' must be a list when present."""
    _, path, fm = migrated_adr
    supersedes = fm.get("supersedes")
    if supersedes is not None:
        assert isinstance(supersedes, list), (
            f"{path.name}: 'supersedes' must be a list, got {type(supersedes)}"
        )


@pytest.mark.audit
def test_implementation_files_present_for_implemented(
    migrated_adr: tuple[int, Path, dict],
) -> None:
    """ADRs with status=implemented must have all implementation_files on disk."""
    _, path, fm = migrated_adr
    if fm.get("status") != "implemented":
        pytest.skip(f"ADR-{fm.get('adr')} status is {fm.get('status')!r}, skipping file check")

    impl_files: list[str] = fm.get("implementation_files") or []
    missing: list[str] = [f for f in impl_files if not _file_exists_resolved(f)]

    assert not missing, (
        f"{path.name}: status=implemented but {len(missing)} file(s) missing:\n"
        + "\n".join(f"  - {f}" for f in missing)
    )


@pytest.mark.audit
def test_implemented_adr_declares_files(
    migrated_adr: tuple[int, Path, dict],
) -> None:
    """ADRs with status=implemented should declare at least one implementation_file.

    This is a soft guard — it catches accidentally promoted status without
    corresponding implementation evidence.
    """
    _, path, fm = migrated_adr
    if fm.get("status") != "implemented":
        pytest.skip(f"ADR-{fm.get('adr')} is not 'implemented'")

    impl_files: list[str] = fm.get("implementation_files") or []
    assert impl_files, (
        f"{path.name}: status=implemented but implementation_files is empty. "
        "Add at least one implementation file or change status to 'accepted'."
    )


# ── Audit script integration test ─────────────────────────────────────────────


@pytest.mark.audit
def test_audit_script_importable() -> None:
    """scripts/audit_adrs.py must be importable without errors."""
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import audit_adrs  # noqa: F401 — import side-effect check


@pytest.mark.audit
def test_audit_script_no_fail_for_migrated_adrs() -> None:
    """run_audit() must produce no FAIL findings for the 5 migrated ADRs."""
    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import audit_adrs

    all_files = audit_adrs._collect_adr_files()
    known_adrs = audit_adrs._known_adr_numbers(all_files)

    migrated_numbers = set(MIGRATED_ADRS.keys())
    failures: list[str] = []

    for path in all_files:
        num = audit_adrs._adr_number_from_filename(path)
        if num not in migrated_numbers:
            continue
        result = audit_adrs.audit_file(path, known_adrs)
        if result.get("level") == audit_adrs.LEVEL_FAIL:
            failures.append(
                f"ADR-{num}: {result.get('code')} — {result.get('message')}"
            )

    assert not failures, (
        f"{len(failures)} FAIL finding(s) in migrated ADRs:\n"
        + "\n".join(f"  {f}" for f in failures)
    )
