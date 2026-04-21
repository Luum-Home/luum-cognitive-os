# SCOPE: both
"""Project documentation scaffolder — 10-category convention (ADR-054).

Generates the canonical `docs/` tree that Cognitive OS projects adopt:
  01-contexto, 02-arquitectura, 03-dominio-riesgo, 04-seguridad,
  05-features, 06-backoffice, 07-investigacion, 08-estandares,
  09-plan-ejecucion, 10-resumenes.

Each category has a README.md plus 1-3 starter files with section
headers and TODO markers. Content is deliberately minimal: the agent/
human fills them. The scaffolder's job is structural consistency, not
content generation.

Usage:
    from lib.project_scaffolder import ProjectScaffolder
    s = ProjectScaffolder(project_name="my-project", project_dir=Path("/tmp/x"))
    files = s.scaffold_all()
    # => list[Path] of every file written
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

__all__ = ["ProjectScaffolder", "CATEGORIES"]


# (dir_name, human_label, files_to_create)
# files_to_create: list of (filename, template_body)
CATEGORIES: List[Tuple[str, str, List[Tuple[str, str]]]] = [
    (
        "01-contexto",
        "Context",
        [
            ("README.md", "# 01 — Contexto\n\nBusiness context, stakeholders, project rationale.\n\n- [ ] business-context.md\n- [ ] stakeholders.md\n"),
            ("business-context.md", "# Business Context\n\n## Problem\n<!-- TODO -->\n\n## Users\n<!-- TODO -->\n\n## Value proposition\n<!-- TODO -->\n"),
            ("stakeholders.md", "# Stakeholders\n\n| Role | Name | Responsibility |\n|---|---|---|\n<!-- TODO -->\n"),
        ],
    ),
    (
        "02-arquitectura",
        "Architecture",
        [
            ("README.md", "# 02 — Arquitectura\n\nSystem design, components, integration points. Cross-reference `docs/adrs/` for decisions.\n\n- [ ] architecture-overview.md\n- [ ] components.md\n"),
            ("architecture-overview.md", "# Architecture Overview\n\n## High-level diagram\n<!-- TODO: ascii or mermaid -->\n\n## Tech stack\n<!-- TODO -->\n\n## Data flow\n<!-- TODO -->\n"),
            ("components.md", "# Components\n\n| Name | Responsibility | Depends on |\n|---|---|---|\n<!-- TODO -->\n"),
        ],
    ),
    (
        "03-dominio-riesgo",
        "Domain + Risk",
        [
            ("README.md", "# 03 — Dominio + Riesgo\n\nDomain model (entities, invariants, bounded contexts) and risk register.\n\n- [ ] domain-model.md\n- [ ] risk-register.md\n"),
            ("domain-model.md", "# Domain Model\n\n## Bounded contexts\n<!-- TODO -->\n\n## Core entities\n| Entity | Invariants | Aggregate root |\n|---|---|---|\n<!-- TODO -->\n\n## Ubiquitous language\n<!-- TODO -->\n"),
            ("risk-register.md", "# Risk Register\n\n| ID | Risk | Likelihood | Impact | Mitigation | Owner |\n|---|---|---|---|---|---|\n<!-- TODO: populate. Use L/M/H for likelihood, impact. -->\n"),
        ],
    ),
    (
        "04-seguridad",
        "Security",
        [
            ("README.md", "# 04 — Seguridad\n\nThreat model, security controls, incident response. Results of `security-audit` skill land here.\n\n- [ ] threat-model.md\n- [ ] security-controls.md\n- [ ] incident-response.md\n"),
            ("threat-model.md", "# Threat Model\n\n## Assets\n<!-- TODO -->\n\n## Threat actors\n<!-- TODO -->\n\n## STRIDE analysis\n| Category | Threat | Mitigation |\n|---|---|---|\n<!-- TODO -->\n"),
            ("security-controls.md", "# Security Controls\n\n## Authentication\n<!-- TODO -->\n\n## Authorization\n<!-- TODO -->\n\n## Data protection\n<!-- TODO -->\n\n## Audit logging\n<!-- TODO -->\n"),
            ("incident-response.md", "# Incident Response\n\n## Severity levels\n<!-- TODO -->\n\n## Runbook\n<!-- TODO -->\n\n## Escalation\n<!-- TODO -->\n"),
        ],
    ),
    (
        "05-features",
        "Features",
        [
            ("README.md", "# 05 — Features\n\nFeature inventory. `document-feature` skill emits entries here.\n\n- [ ] features-backlog.md\n"),
            ("features-backlog.md", "# Features Backlog\n\n| ID | Feature | Status | Priority | Owner |\n|---|---|---|---|---|\n<!-- TODO: status in (backlog|in-progress|done|blocked) -->\n"),
        ],
    ),
    (
        "06-backoffice",
        "Backoffice / Operations",
        [
            ("README.md", "# 06 — Backoffice\n\nOperational runbooks, admin processes, monitoring. Anything customer-service, ops-team, or internal-tooling related.\n\n- [ ] operations.md\n- [ ] admin-processes.md\n- [ ] monitoring.md\n"),
            ("operations.md", "# Operations\n\n## Deploy\n<!-- TODO -->\n\n## Rollback\n<!-- TODO -->\n\n## On-call runbook\n<!-- TODO -->\n"),
            ("admin-processes.md", "# Admin Processes\n\n## User management\n<!-- TODO -->\n\n## Data corrections\n<!-- TODO -->\n\n## Configuration changes\n<!-- TODO -->\n"),
            ("monitoring.md", "# Monitoring\n\n## SLOs\n<!-- TODO -->\n\n## Dashboards\n<!-- TODO: links -->\n\n## Alert routing\n<!-- TODO -->\n"),
        ],
    ),
    (
        "07-investigacion",
        "Research",
        [
            ("README.md", "# 07 — Investigación\n\nResearch spikes, competitive analysis, tech evaluations. `deep-research` and `eval-repo` skills emit here.\n\n- [ ] research-notes.md\n- [ ] competitive-analysis.md\n"),
            ("research-notes.md", "# Research Notes\n\n| Date | Topic | Question | Finding | Decision |\n|---|---|---|---|---|\n<!-- TODO -->\n"),
            ("competitive-analysis.md", "# Competitive Analysis\n\n## Direct competitors\n<!-- TODO -->\n\n## Feature comparison\n| Feature | Us | Competitor A | Competitor B |\n|---|---|---|---|\n<!-- TODO -->\n"),
        ],
    ),
    (
        "08-estandares",
        "Standards",
        [
            ("README.md", "# 08 — Estándares\n\nCoding, documentation, review standards adopted by the project. Anchored to `rules/` and `docs/adrs/` for the why.\n\n- [ ] coding-standards.md\n- [ ] documentation-standards.md\n- [ ] review-standards.md\n"),
            ("coding-standards.md", "# Coding Standards\n\n## Language conventions\n<!-- TODO -->\n\n## Formatting / Lint\n<!-- TODO: point to tool configs -->\n\n## Naming\n<!-- TODO -->\n"),
            ("documentation-standards.md", "# Documentation Standards\n\n## Required sections per document type\n<!-- TODO -->\n\n## Review cadence\n<!-- TODO -->\n"),
            ("review-standards.md", "# Review Standards\n\n## PR checklist\n<!-- TODO -->\n\n## Approvals required\n<!-- TODO -->\n"),
        ],
    ),
    (
        "09-plan-ejecucion",
        "Execution Plan",
        [
            ("README.md", "# 09 — Plan de ejecución\n\nRoadmap, sprints, estimations. `sdd-tasks` and `cos-sprint` skills emit artifacts here.\n\n- [ ] roadmap.md\n- [ ] sprint-plans.md\n- [ ] estimation.md\n"),
            ("roadmap.md", "# Roadmap\n\n## Q1\n<!-- TODO -->\n\n## Q2\n<!-- TODO -->\n\n## Later\n<!-- TODO -->\n"),
            ("sprint-plans.md", "# Sprint Plans\n\n| Sprint | Goal | Scope | Exit criteria |\n|---|---|---|---|\n<!-- TODO -->\n"),
            ("estimation.md", "# Estimation\n\n## Method\n<!-- TODO: story points / t-shirts / hours -->\n\n## History (actual vs estimated)\n<!-- TODO -->\n"),
        ],
    ),
    (
        "10-resumenes",
        "Summaries",
        [
            ("README.md", "# 10 — Resúmenes\n\nExecutive summaries and status reports. `session-wrapup` + `generate-changelog` feed this.\n\n- [ ] executive-summary.md\n- [ ] status-reports.md\n"),
            ("executive-summary.md", "# Executive Summary\n\n## Current state\n<!-- TODO -->\n\n## Recent wins\n<!-- TODO -->\n\n## Next milestones\n<!-- TODO -->\n"),
            ("status-reports.md", "# Status Reports\n\n## Template\n- Date:\n- Status: on-track|at-risk|blocked\n- Delivered this week:\n- Blocked on:\n- Next week:\n\n## Reports\n<!-- TODO: append new reports at top -->\n"),
        ],
    ),
]


@dataclass
class ScaffoldResult:
    project_dir: Path
    docs_dir: Path
    created: List[Path]
    skipped: List[Path]  # existed + overwrite=False

    @property
    def summary(self) -> str:
        return (
            f"scaffold: {len(self.created)} files created, "
            f"{len(self.skipped)} skipped (existed) in {self.docs_dir}"
        )


class ProjectScaffolder:
    """Creates the 10-category docs/ skeleton for an adopting project.

    project_dir is the project root. docs go under <project_dir>/docs/.
    Existing files are preserved unless overwrite=True.
    """

    def __init__(self, project_name: str, project_dir: Path, overwrite: bool = False):
        if not project_name or not project_name.strip():
            raise ValueError("project_name must be non-empty")
        self.project_name = project_name.strip()
        self.project_dir = Path(project_dir).resolve()
        self.docs_dir = self.project_dir / "docs"
        self.overwrite = overwrite

    def scaffold_all(self) -> ScaffoldResult:
        """Create the 10 dirs + their starter files. Idempotent."""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(exist_ok=True)

        created: List[Path] = []
        skipped: List[Path] = []

        # Top-level docs/README.md — index of the 10 categories
        self._write_or_skip(
            self.docs_dir / "README.md",
            self._top_readme(),
            created,
            skipped,
        )

        for dir_name, label, files in CATEGORIES:
            cat_dir = self.docs_dir / dir_name
            cat_dir.mkdir(exist_ok=True)
            for fname, body in files:
                self._write_or_skip(cat_dir / fname, body, created, skipped)

        return ScaffoldResult(
            project_dir=self.project_dir,
            docs_dir=self.docs_dir,
            created=created,
            skipped=skipped,
        )

    def scaffold_category(self, category_num: int) -> List[Path]:
        """Populate a single category (1-10)."""
        if not 1 <= category_num <= 10:
            raise ValueError(f"category_num must be 1..10, got {category_num}")
        dir_name, _label, files = CATEGORIES[category_num - 1]
        cat_dir = self.docs_dir / dir_name
        cat_dir.mkdir(parents=True, exist_ok=True)
        created: List[Path] = []
        skipped: List[Path] = []
        for fname, body in files:
            self._write_or_skip(cat_dir / fname, body, created, skipped)
        return created

    def _write_or_skip(
        self,
        path: Path,
        body: str,
        created: List[Path],
        skipped: List[Path],
    ) -> None:
        if path.exists() and not self.overwrite:
            skipped.append(path)
            return
        path.write_text(body)
        created.append(path)

    def _top_readme(self) -> str:
        lines = [
            f"# {self.project_name} — docs/",
            "",
            "Project documentation following the Cognitive OS 10-category convention (ADR-054).",
            "",
            "| # | Category | Purpose |",
            "|---|---|---|",
        ]
        for dir_name, label, _files in CATEGORIES:
            num = dir_name.split("-", 1)[0]
            lines.append(f"| {num} | [{label}]({dir_name}/) | — |")
        lines.append("")
        lines.append("Every category has a `README.md` with its own file index.")
        lines.append("")
        return "\n".join(lines)


def expected_file_count() -> int:
    """Total number of files a full scaffold produces (inc. top-level README)."""
    return 1 + sum(len(files) for _, _, files in CATEGORIES)


def expected_category_paths(project_dir: Path) -> Dict[str, Path]:
    """Map dir_name -> expected path under project_dir/docs/."""
    docs = Path(project_dir) / "docs"
    return {dir_name: docs / dir_name for dir_name, _, _ in CATEGORIES}
