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
    "docs/04-Concepts/root/plan-system.md",                          # meta-doc about the plan system
    "docs/04-Concepts/root/plan-system.md",         # vaulted meta-doc about the plan system
    "docs/05-Methodology/root/rules-consolidation-plan.md",             # evaluate after migration (ADR-082 note)
    "docs/05-Methodology/root/rules-consolidation-plan.md",  # vaulted methodology artifact
    "docs/01-Build-Log/root/roadmap.md",                              # top-level human-readable entry point
    "docs/01-Build-Log/root/roadmap.md",            # vaulted human-readable entry point
    "docs/04-Concepts/architecture/plans-reconciliation-2026-04-21.md",  # audit artifact → docs/06-Daily/reports/
    "docs/04-Concepts/architecture/plans-reconciliation-2026-04-21.md",  # vaulted location during docs taxonomy migration
    "docs/01-Build-Log/release/roadmap-v1.0-full-e2e.md",        # release artifact outside plan scope
    "docs/01-Build-Log/release/roadmap-v1.0-full-e2e.md",  # vaulted release artifact outside plan scope
    "docs/06-Daily/reports/merge-readiness-master-plan-2026-04-23.md",  # report artifact
    "docs/06-Daily/reports/merge-readiness-master-plan-2026-04-23.md",  # vaulted report artifact
    "docs/06-Daily/reports/next-session-plan-dormant-to-real.md",        # session artifact
    "docs/06-Daily/reports/next-session-plan-dormant-to-real.md",  # vaulted session artifact
    "docs/04-Concepts/architecture/primitive-coverage-spike-plan-2026-04.md",  # historical architecture spike report
    "docs/04-Concepts/architecture/primitive-coverage-spike-plan-2026-04.md",  # vaulted architecture artifact
    "docs/04-Concepts/architecture/startup-circuit-breaker-plan.md",  # ADR-101 design companion
    "docs/04-Concepts/architecture/startup-circuit-breaker-plan.md",  # vaulted architecture artifact
    "docs/04-Concepts/architecture/boring-reliability-control-plane.md",  # control-plane architecture, not an active plan
    "docs/04-Concepts/architecture/boring-reliability-control-plane.md",  # vaulted architecture artifact
    "docs/04-Concepts/architecture/dx-cloud-flow-bootstrap-plan.md",  # architecture bootstrap plan linked from docs index
    "docs/04-Concepts/architecture/dx-cloud-flow-bootstrap-plan.md",  # vaulted architecture artifact
    "docs/04-Concepts/architecture/harness-implementation-roadmap.md",  # architecture roadmap for harness rollout
    "docs/04-Concepts/architecture/harness-implementation-roadmap.md",  # vaulted architecture artifact
    "docs/04-Concepts/architecture/surface-5-and-secure-cosd-roadmap.md",  # architecture roadmap companion for Surface 5 and secure cosd ADRs
    "docs/04-Concepts/architecture/surface-5-and-secure-cosd-roadmap.md",  # vaulted architecture artifact
    "docs/04-Concepts/architecture/multi-ide-harness-implementation-plan.md",  # architecture plan linked from harness ADR batch
    "docs/04-Concepts/architecture/multi-ide-harness-implementation-plan.md",  # vaulted architecture artifact
    "docs/04-Concepts/architecture/primitive-duplication-audit-implementation-plan.md",  # ADR-149 implementation companion
    "docs/04-Concepts/architecture/primitive-duplication-audit-implementation-plan.md",  # vaulted architecture artifact
    "docs/04-Concepts/architecture/primitive-readiness-continuity-plan.md",  # primitive readiness architecture companion
    "docs/04-Concepts/architecture/primitive-readiness-continuity-plan.md",  # vaulted architecture artifact
    "docs/04-Concepts/architecture/service-control-plane-implementation-plan.md",  # service-control-plane architecture companion
    "docs/04-Concepts/architecture/service-control-plane-implementation-plan.md",  # vaulted architecture artifact
    "docs/04-Concepts/architecture/service-control-plane-research-2026-05-04.md",  # research artifact, not active plan
    "docs/04-Concepts/architecture/service-control-plane-research-2026-05-04.md",  # vaulted architecture artifact
    "docs/04-Concepts/architecture/external-tool-intelligence-plane.md",  # architecture companion, not active plan inventory
    "docs/04-Concepts/architecture/external-tool-intelligence-plane.md",  # vaulted architecture artifact
    "docs/04-Concepts/architecture/primitive-contract-registry-implementation-plan.md",  # ADR-256 architecture companion
    "docs/04-Concepts/architecture/primitive-contract-registry-implementation-plan.md",  # vaulted architecture artifact
    "docs/02-Decisions/adrs/ADR-248-control-plane-audit-loop.md",  # ADR title contains control-plane, not active plan inventory
    "docs/02-Decisions/adrs/ADR-248-control-plane-audit-loop.md",  # vaulted ADR artifact
    "docs/02-Decisions/adrs/ADR-254-external-tool-intelligence-plane-and-project-overlays.md",  # ADR title contains plane, not active plan inventory
    "docs/02-Decisions/adrs/ADR-254-external-tool-intelligence-plane-and-project-overlays.md",  # vaulted ADR artifact
    "docs/02-Decisions/adrs/ADR-321-primitive-scope-plane-balance-and-proof-ratchets.md",  # ADR title contains plane, not active plan inventory
    "docs/02-Decisions/adrs/ADR-161-remote-control-plane-and-provider-adapter-boundary.md",  # ADR title includes control-plane, not active plan
    "docs/02-Decisions/adrs/ADR-161-remote-control-plane-and-provider-adapter-boundary.md",  # vaulted ADR artifact
    "docs/02-Decisions/adrs/ADR-082-plan-location-convention.md",  # ADR defines the plan convention; not an active plan
    "docs/09-Quality/manual-tests/remote-control-plane-boundary.md",  # manual-test artifact
    "docs/09-Quality/manual-tests/remote-control-plane-boundary.md",  # vaulted manual-test artifact
    "docs/09-Quality/manual-tests/service-control-plane-proof-drills.md",  # manual-test artifact
    "docs/09-Quality/manual-tests/service-control-plane-proof-drills.md",  # vaulted manual-test artifact
    "docs/06-Daily/reports/remote-control-plane-alternatives-2026-05-05.md",  # report artifact
    "docs/06-Daily/reports/remote-control-plane-alternatives-2026-05-05.md",  # vaulted report artifact
    "docs/04-Concepts/architecture/expansion-hardening-plan.md",  # expansion-hardening architecture plan linked from ADR work
    "docs/04-Concepts/architecture/expansion-hardening-plan.md",  # vaulted architecture artifact
    "docs/04-Concepts/architecture/plans/",  # runtime contract plan docs are linked from product entrypoints
    "docs/04-Concepts/architecture/plans/",  # vaulted runtime contract plan docs
    "docs/06-Daily/reports/pending-plans-audit-2026-04-30.md",  # audit report, not active plan
    "docs/06-Daily/reports/pending-plans-audit-2026-04-30.md",  # vaulted audit report
    "docs/06-Daily/reports/task-and-plan-reconciliation-2026-05-05.md",  # reconciliation report, not active plan
    "docs/06-Daily/reports/task-and-plan-reconciliation-2026-05-05.md",  # vaulted reconciliation report
    "docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md",  # disposition report from plan closure audit, not an active plan
    "templates/agent-planning.md",  # prompt template; filename includes planning but is not an active plan
    # docs/99-Archive/archive/plans/ contains files other than token-optimization-masterplan.md
    # that were NOT listed in ADR-082's migration table.  They remain in place.
    "docs/99-Archive/archive/plans/",   # directory prefix — any file under here is exempt
    "docs/99-Archive/archive/plans/",   # vaulted archive plan artifacts
    # Skill example files that reference docs/plans/ as illustrative paths
    ".claude/plugins/",      # plugin skill templates use example paths
    # ADR file that defines the convention (self-referential, historic)
    "docs/02-Decisions/adrs/ADR-082-plan-location-convention.md",
    "docs/02-Decisions/adrs/ADR-082-plan-location-convention.md",
    # Private strategy/research workspace (gitignored), not active OS plan inventory
    ".cognitive-os/strategy/",  # private strategy/research workspace; not canonical active OS plans
    # Measurement / audit artifacts that document the old state
    "docs/06-Daily/measurements/",
    "docs/06-Daily/measurements/",
    # Business-scoped files (ADR-082 §"Files that stay in place")
    "docs/08-References/business/",
    "docs/08-References/business/",
    # Third-party reference / benchmark material — not project plans
    "reference/",
    # Rules documents — these are rules, not plans (plan-first.md is a rule)
    "rules/",
    # Patterns documentation — describes patterns, not plans
    "docs/04-Concepts/patterns/",
    "docs/04-Concepts/patterns/",
    # Reports and research artifacts produced by agents; not active plan inventory
    "docs/06-Daily/reports/plans-discovery-triage-2026-05-11.md",
    "docs/06-Daily/reports/plans-discovery-triage-2026-05-11.md",
    "docs/06-Daily/reports/p2-plan-reconciliation-2026-05-10.md",
    "docs/06-Daily/reports/p2-plan-reconciliation-2026-05-10.md",
    "docs/06-Daily/reports/p3-plan-triage-2026-05-10.md",
    "docs/06-Daily/reports/p3-plan-triage-2026-05-10.md",
    "docs/06-Daily/reports/sprint-3-physical-rename-plan-2026-05-12.md",
    "docs/06-Daily/reports/sprint-3-physical-rename-plan-2026-05-12.md",
    # Archived reports directory; historical artifacts, not active plans
    "docs/06-Daily/reports/archive/",
    "docs/06-Daily/reports/archive/",
    # Private research workspace (gitignored)
    ".private/",
    # Third-party test plan from external-source-cache; not an OS plan
    ".cognitive-os/external-source-cache/",
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
            (".cognitive-os", "checkpoints"),
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
