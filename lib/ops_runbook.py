# SCOPE: both
"""Ops runbook scaffolder — operations.md + admin-processes.md + monitoring.md
under docs/06-backoffice/ (ADR-054 Phase 2).

SCAFFOLDER only: emits three structured templates with TODO markers.
Content generation is out of scope (would require LLM).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Dict, List

__all__ = ["OpsRunbookScaffolder", "ScaffoldResult", "FILES"]

CAT_REL = Path("docs/06-backoffice")

HEADER = "<!-- ops-runbook:autogen-header -->"
FOOTER = "<!-- ops-runbook:autogen-footer -->"


def _ops_body(project: str) -> str:
    today = date.today().isoformat()
    return (
        f"# Operations — {project}\n\n_Last scaffolded: {today}_\n\n"
        f"{HEADER}\n\n"
        "## Deploy\n\n"
        "### Preconditions\n"
        "- [ ] CI green on main\n"
        "- [ ] Changelog updated\n"
        "- [ ] Secrets present in target env\n\n"
        "### Steps\n"
        "1. <!-- TODO: build/tag command -->\n"
        "2. <!-- TODO: push to registry -->\n"
        "3. <!-- TODO: apply manifests / update service -->\n"
        "4. <!-- TODO: smoke-test endpoint -->\n\n"
        "### Verification\n"
        "- [ ] `curl <health-url>` returns 200\n"
        "- [ ] Version endpoint reports new SHA\n"
        "- [ ] Error rate unchanged after 5 min\n\n"
        "## Rollback\n\n"
        "### Trigger conditions\n"
        "- Error rate > <!-- TODO --> for 5 min\n"
        "- p95 latency > <!-- TODO -->\n"
        "- Critical alert fired\n\n"
        "### Steps\n"
        "1. <!-- TODO: revert command -->\n"
        "2. <!-- TODO: verify previous version running -->\n"
        "3. Post-mortem issue opened\n\n"
        "## On-call runbook\n\n"
        "### Primary contact\n"
        "- Rotation: <!-- TODO -->\n"
        "- Escalation after: 15 min\n\n"
        "### Common incidents\n\n"
        "| Symptom | Likely cause | First action | Owner |\n"
        "|---|---|---|---|\n"
        "| <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n\n"
        f"{FOOTER}\n\n"
        "<!-- Content below footer preserved across re-runs. -->\n"
    )


def _admin_body(project: str) -> str:
    today = date.today().isoformat()
    return (
        f"# Admin Processes — {project}\n\n_Last scaffolded: {today}_\n\n"
        f"{HEADER}\n\n"
        "## User management\n\n"
        "| Action | Who can perform | Audit log | Tooling |\n"
        "|---|---|---|---|\n"
        "| Create user | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n"
        "| Suspend user | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n"
        "| Reset password | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n\n"
        "## Data corrections\n\n"
        "### Approval required\n"
        "- Any write to production data requires 2-person review\n"
        "- All changes logged to audit trail\n\n"
        "### Procedure\n"
        "1. Open ticket describing the correction\n"
        "2. <!-- TODO: how to preview the change -->\n"
        "3. <!-- TODO: who approves -->\n"
        "4. Apply change, record before/after snapshot\n\n"
        "## Configuration changes\n\n"
        "| Config | Owner | Change cadence | Requires restart |\n"
        "|---|---|---|---|\n"
        "| <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n\n"
        f"{FOOTER}\n\n"
        "<!-- Content below footer preserved across re-runs. -->\n"
    )


def _monitoring_body(project: str) -> str:
    today = date.today().isoformat()
    return (
        f"# Monitoring — {project}\n\n_Last scaffolded: {today}_\n\n"
        f"{HEADER}\n\n"
        "## SLOs\n\n"
        "| SLO | Target | Measurement | Error budget |\n"
        "|---|---|---|---|\n"
        "| Availability | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n"
        "| p95 latency | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n"
        "| Error rate | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n\n"
        "## Dashboards\n\n"
        "| Dashboard | URL | What it shows |\n"
        "|---|---|---|\n"
        "| <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n\n"
        "## Alert routing\n\n"
        "| Alert | Severity | Routes to | Runbook link |\n"
        "|---|---|---|---|\n"
        "| <!-- TODO --> | P1/P2/P3 | <!-- TODO --> | operations.md#on-call-runbook |\n\n"
        "## Log aggregation\n"
        "- Source: <!-- TODO -->\n"
        "- Retention: <!-- TODO -->\n"
        "- Query tool: <!-- TODO -->\n\n"
        f"{FOOTER}\n\n"
        "<!-- Content below footer preserved across re-runs. -->\n"
    )


# (relative filename, builder)
FILES = [
    ("operations.md", _ops_body),
    ("admin-processes.md", _admin_body),
    ("monitoring.md", _monitoring_body),
]


@dataclass
class ScaffoldResult:
    project_dir: Path
    created: List[Path] = field(default_factory=list)
    extended: List[Path] = field(default_factory=list)
    skipped: List[Path] = field(default_factory=list)
    overwritten: List[Path] = field(default_factory=list)

    @property
    def summary(self) -> str:
        return (
            f"ops-runbook: {len(self.created)} created, "
            f"{len(self.extended)} extended, "
            f"{len(self.overwritten)} overwritten, "
            f"{len(self.skipped)} skipped"
        )


class OpsRunbookScaffolder:
    def __init__(self, project_dir: Path, project_name: str = "", overwrite: bool = False):
        self.project_dir = Path(project_dir).resolve()
        self.project_name = (project_name or self.project_dir.name).strip() or "project"
        self.overwrite = overwrite
        self.cat_dir = self.project_dir / CAT_REL

    def scaffold(self) -> ScaffoldResult:
        self.cat_dir.mkdir(parents=True, exist_ok=True)
        result = ScaffoldResult(project_dir=self.project_dir)

        for fname, builder in FILES:
            target = self.cat_dir / fname
            body = builder(self.project_name)

            if not target.exists():
                target.write_text(body)
                result.created.append(target)
                continue

            if self.overwrite:
                target.write_text(body)
                result.overwritten.append(target)
                continue

            existing = target.read_text()
            if HEADER in existing and FOOTER in existing:
                tail = existing.split(FOOTER, 1)[1]
                new_body = body.split(FOOTER, 1)[0] + FOOTER + tail
                target.write_text(new_body)
                result.extended.append(target)
            else:
                result.skipped.append(target)

        return result
