"""Tests for sdd-propose conflict detection step.

Validates that the conflict detection logic correctly identifies
overlapping proposals, excludes archived ones, and handles
engram unavailability gracefully.
"""

from typing import List, Optional

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Helpers — pure-Python simulators for conflict detection logic
# ---------------------------------------------------------------------------

def extract_affected_areas(proposal_md: str) -> List[dict]:
    """Parse the Affected Areas table from a proposal markdown string.

    Returns a list of dicts with keys: area, impact, description.
    """
    lines = proposal_md.splitlines()
    in_table = False
    header_seen = False
    areas = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## Affected Areas"):
            in_table = True
            continue
        if in_table and stripped.startswith("##"):
            break
        if in_table and stripped.startswith("|"):
            if not header_seen:
                header_seen = True
                continue
            # skip separator row
            if set(stripped.replace("|", "").strip()) <= {"-", " "}:
                continue
            parts = [p.strip().strip("`") for p in stripped.split("|") if p.strip()]
            if len(parts) >= 3:
                areas.append({
                    "area": parts[0],
                    "impact": parts[1],
                    "description": parts[2],
                })
    return areas


def detect_conflicts(
    current_areas: List[dict],
    other_proposals: List[dict],
    archived_changes: set[str],
) -> List[dict]:
    """Detect file-path and domain overlaps between current proposal and others.

    Parameters
    ----------
    current_areas : list of area dicts from the current proposal
    other_proposals : list of dicts with keys: change_name, areas (list of area dicts)
    archived_changes : set of change names that have been archived

    Returns a list of conflict dicts: {proposal, overlapping_area, risk}
    """
    conflicts = []
    current_paths = {a["area"] for a in current_areas}

    for other in other_proposals:
        if other["change_name"] in archived_changes:
            continue
        other_paths = {a["area"] for a in other["areas"]}
        overlap = current_paths & other_paths
        for area in sorted(overlap):
            conflicts.append({
                "proposal": other["change_name"],
                "overlapping_area": area,
                "risk": "Both proposals modify the same area",
            })

    return conflicts


def format_conflicts_section(
    conflicts: Optional[List[dict]],
    engram_available: bool = True,
) -> str:
    """Format the ## Conflicts section for the proposal markdown."""
    if not engram_available:
        return (
            "## Conflicts\n\n"
            "Conflict check skipped \u2014 unable to query existing proposals."
        )
    if not conflicts:
        return "## Conflicts\n\nNone detected."
    lines = [
        "## Conflicts",
        "",
        "| Proposal | Overlapping Area | Risk |",
        "|----------|-----------------|------|",
    ]
    for c in conflicts:
        lines.append(
            f"| {c['proposal']} | `{c['overlapping_area']}` | {c['risk']} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROPOSAL_TEMPLATE = """\
# Proposal: {title}

## Intent
Test proposal.

## Scope
### In Scope
- Something

### Out of Scope
- Nothing

## Approach
Do the thing.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
{area_rows}

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| None | Low | N/A |
"""


def _make_proposal(title: str, areas: List[tuple]) -> str:
    rows = "\n".join(
        f"| `{path}` | {impact} | {desc} |"
        for path, impact, desc in areas
    )
    return PROPOSAL_TEMPLATE.format(title=title, area_rows=rows)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestOverlappingFilesDetected:
    def test_overlapping_files_detected(self):
        current_md = _make_proposal("add-auth", [
            ("src/auth/middleware.go", "New", "JWT middleware"),
            ("src/server/routes.go", "Modified", "Add auth routes"),
        ])
        current_areas = extract_affected_areas(current_md)

        other_md = _make_proposal("add-logging", [
            ("src/server/routes.go", "Modified", "Add logging middleware"),
            ("src/logging/logger.go", "New", "Logger module"),
        ])
        other_areas = extract_affected_areas(other_md)

        conflicts = detect_conflicts(
            current_areas,
            [{"change_name": "add-logging", "areas": other_areas}],
            archived_changes=set(),
        )

        assert len(conflicts) == 1
        assert conflicts[0]["overlapping_area"] == "src/server/routes.go"
        assert conflicts[0]["proposal"] == "add-logging"


class TestDomainOverlapDetected:
    def test_domain_overlap_detected(self):
        current_areas = [{"area": "internal/auth", "impact": "Modified", "description": "Refactor"}]
        other_areas = [{"area": "internal/auth", "impact": "New", "description": "New handler"}]

        conflicts = detect_conflicts(
            current_areas,
            [{"change_name": "auth-revamp", "areas": other_areas}],
            archived_changes=set(),
        )

        assert len(conflicts) == 1
        assert conflicts[0]["overlapping_area"] == "internal/auth"
        assert conflicts[0]["proposal"] == "auth-revamp"


class TestNoConflicts:
    def test_no_conflicts(self):
        current_areas = [{"area": "src/auth/handler.go", "impact": "New", "description": "New"}]
        other_areas = [{"area": "src/billing/invoice.go", "impact": "New", "description": "New"}]

        conflicts = detect_conflicts(
            current_areas,
            [{"change_name": "add-billing", "areas": other_areas}],
            archived_changes=set(),
        )

        assert len(conflicts) == 0

        section = format_conflicts_section(conflicts)
        assert "None detected" in section


class TestArchivedProposalExcluded:
    def test_archived_proposal_excluded(self):
        current_areas = [{"area": "src/server/routes.go", "impact": "Modified", "description": "Change"}]
        other_areas = [{"area": "src/server/routes.go", "impact": "Modified", "description": "Old change"}]

        conflicts = detect_conflicts(
            current_areas,
            [{"change_name": "old-feature", "areas": other_areas}],
            archived_changes={"old-feature"},
        )

        assert len(conflicts) == 0


class TestEngramUnavailableGraceful:
    def test_engram_unavailable_graceful(self):
        section = format_conflicts_section(None, engram_available=False)
        assert "Conflict check skipped" in section
        assert "unable to query existing proposals" in section

    def test_engram_available_no_conflicts(self):
        section = format_conflicts_section([], engram_available=True)
        assert "None detected" in section
