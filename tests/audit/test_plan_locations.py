"""Enforcement test for ADR-082: plan file location convention.

Every .md file that looks like a plan or roadmap must live under
.cognitive-os/plans/<canonical-subdir>/. Files in the explicit allowlist
(docs that describe the plan system, report artifacts, business files, etc.)
are exempt.

Canonical subdirs (ADR-082 Option A):
  .cognitive-os/plans/features/
  .cognitive-os/plans/research/
  .cognitive-os/plans/architecture/
  .cognitive-os/plans/roadmaps/
  .cognitive-os/plans/archive/   <- excluded from active count but canonical

Violation = any *plan*.md or *roadmap*.md file (case-insensitive) found outside
.cognitive-os/plans/ and not in the allowlist.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

CANONICAL_ROOT = REPO / ".cognitive-os" / "plans"

# Canonical subdirs per ADR-082.  archive/ is included here — it is canonical,
# just excluded from the startup active count.
CANONICAL_SUBDIRS = {"features", "research", "architecture", "roadmaps", "archive"}

# Allowlist: paths (relative to REPO) that are permitted to contain "plan" or
# "roadmap" in their filename without living under .cognitive-os/plans/.
# Each entry is a relative path string.  Use str.startswith() for directory
# prefixes and exact match for individual files.
#
# Rationale for each entry is documented inline per ADR-082 §"Files that stay
# in place".
ALLOWLIST_RELATIVE: list[str] = [
    # ADR-082 "stay in place" entries
    "docs/plan-system.md",                          # meta-doc about the plan system
    "docs/rules-consolidation-plan.md",             # evaluate after migration (ADR-082 note)
    "docs/roadmap.md",                              # top-level human-readable entry point
    "docs/architecture/plans-reconciliation-2026-04-21.md",  # audit artifact → docs/reports/
    "docs/release/roadmap-v1.0-full-e2e.md",        # release artifact outside plan scope
    "docs/reports/merge-readiness-master-plan-2026-04-23.md",  # report artifact
    "docs/reports/next-session-plan-dormant-to-real.md",        # session artifact
    "docs/architecture/primitive-coverage-spike-plan-2026-04.md",  # historical architecture spike report
    "docs/architecture/startup-circuit-breaker-plan.md",  # ADR-101 design companion
    "docs/architecture/boring-reliability-control-plane.md",  # control-plane architecture, not an active plan
    "docs/architecture/dx-cloud-flow-bootstrap-plan.md",  # architecture bootstrap plan linked from docs index
    "docs/architecture/harness-implementation-roadmap.md",  # architecture roadmap for harness rollout
    "docs/architecture/multi-ide-harness-implementation-plan.md",  # architecture plan linked from harness ADR batch
    "docs/architecture/primitive-duplication-audit-implementation-plan.md",  # ADR-149 implementation companion
    "docs/architecture/primitive-readiness-continuity-plan.md",  # primitive readiness architecture companion
    "docs/architecture/service-control-plane-implementation-plan.md",  # service-control-plane architecture companion
    "docs/architecture/service-control-plane-research-2026-05-04.md",  # research artifact, not active plan
    "docs/adrs/ADR-161-remote-control-plane-and-provider-adapter-boundary.md",  # ADR title includes control-plane, not active plan
    "docs/manual-tests/remote-control-plane-boundary.md",  # manual-test artifact
    "docs/manual-tests/service-control-plane-proof-drills.md",  # manual-test artifact
    "docs/reports/remote-control-plane-alternatives-2026-05-05.md",  # report artifact
    "docs/architecture/expansion-hardening-plan.md",  # expansion-hardening architecture plan linked from ADR work
    "docs/architecture/plans/",  # runtime contract plan docs are linked from product entrypoints
    "docs/reports/pending-plans-audit-2026-04-30.md",  # audit report, not active plan
    "docs/reports/task-and-plan-reconciliation-2026-05-05.md",  # reconciliation report, not active plan
    # docs/archive/plans/ contains files other than token-optimization-masterplan.md
    # that were NOT listed in ADR-082's migration table.  They remain in place.
    "docs/archive/plans/",   # directory prefix — any file under here is exempt
    # Skill example files that reference docs/plans/ as illustrative paths
    ".claude/plugins/",      # plugin skill templates use example paths
    # ADR file that defines the convention (self-referential, historic)
    "docs/adrs/ADR-082-plan-location-convention.md",
    # Measurement / audit artifacts that document the old state
    "docs/measurements/",
    # Business-scoped files (ADR-082 §"Files that stay in place")
    "docs/business/",
    # Third-party reference / benchmark material — not project plans
    "reference/",
    # Rules documents — these are rules, not plans (plan-first.md is a rule)
    "rules/",
    # Patterns documentation — describes patterns, not plans
    "docs/patterns/",
]


def _is_allowlisted(path: Path) -> bool:
    """Return True if path is covered by the allowlist."""
    rel = str(path.relative_to(REPO))
    for entry in ALLOWLIST_RELATIVE:
        if entry.endswith("/"):
            # Directory prefix match
            if rel.startswith(entry):
                return True
        else:
            if rel == entry:
                return True
    return False


_PLAN_PATTERN = re.compile(r"(plan|roadmap)", re.IGNORECASE)


def _looks_like_plan(path: Path) -> bool:
    """Return True if the filename matches the plan/roadmap pattern."""
    return bool(_PLAN_PATTERN.search(path.name))


@pytest.mark.audit
def test_no_plan_files_outside_canonical_root() -> None:
    """Walk the repo and assert no plan-like .md files live outside
    .cognitive-os/plans/<canonical-subdir>/.

    This test EXECUTES the check (walks the filesystem) rather than relying on
    a static fixture, satisfying the project's quality-gate requirement for
    audit tests that "must EXECUTE the check, not just assert file existence."
    """
    violations: list[str] = []

    for md_file in REPO.rglob("*.md"):
        # Skip symlinks — they resolve to the real file which is checked separately.
        # This avoids double-counting files exposed through .cognitive-os/docs/ symlinks.
        if md_file.is_symlink():
            continue

        # Skip git internals and virtual-env directories
        parts = md_file.parts
        if any(p.startswith(".git") for p in parts):
            continue
        rel_parts = md_file.relative_to(REPO).parts
        if rel_parts[:2] == (".claude", "worktrees"):
            continue
        if rel_parts[:2] in {
            (".cognitive-os", "sessions"),
            (".cognitive-os", "generated"),
            (".cognitive-os", "runtime"),
            (".cognitive-os", "snapshots"),
        }:
            continue
        if any(p in ("node_modules", "__pycache__", ".venv", "venv") for p in parts):
            continue

        if not _looks_like_plan(md_file):
            continue

        # If it's already under the canonical root → OK
        try:
            md_file.relative_to(CANONICAL_ROOT)
            # Verify it's in a known canonical subdir (not directly in plans/)
            sub = md_file.relative_to(CANONICAL_ROOT).parts[0]
            if sub not in CANONICAL_SUBDIRS:
                violations.append(
                    f"WRONG-SUBDIR: {md_file.relative_to(REPO)} "
                    f"(subdir '{sub}' not in {sorted(CANONICAL_SUBDIRS)})"
                )
            continue
        except ValueError:
            pass  # Not under canonical root — check allowlist

        if _is_allowlisted(md_file):
            continue

        violations.append(str(md_file.relative_to(REPO)))

    assert not violations, (
        f"ADR-082 violation: {len(violations)} plan/roadmap file(s) found outside "
        f".cognitive-os/plans/<canonical-subdir>/.\n"
        "Move them or add to the allowlist with a documented rationale.\n"
        "Violations:\n" + "\n".join(f"  - {v}" for v in sorted(violations))
    )


@pytest.mark.audit
def test_canonical_subdirs_exist() -> None:
    """All four active canonical subdirs must exist (archive is optional
    if no files have been archived yet)."""
    active_subdirs = {"features", "research", "architecture", "roadmaps"}
    for subdir in active_subdirs:
        path = CANONICAL_ROOT / subdir
        assert path.is_dir(), (
            f"Canonical plan subdir missing: .cognitive-os/plans/{subdir}/  "
            f"(ADR-082 requires this directory to exist)"
        )


@pytest.mark.audit
def test_plan_files_in_canonical_root_have_valid_subdir() -> None:
    """Every file under .cognitive-os/plans/ must be in a known canonical subdir,
    not at the top level of plans/ itself."""
    top_level_md = [
        f for f in CANONICAL_ROOT.glob("*.md")
        if f.is_file()
    ]
    assert not top_level_md, (
        f"Files found directly in .cognitive-os/plans/ (must be in a canonical subdir): "
        f"{[f.name for f in top_level_md]}"
    )
