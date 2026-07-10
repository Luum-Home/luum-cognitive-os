# SCOPE: both
"""Risk register scaffolder — STRIDE + impact/likelihood (ADR-054 Phase 2).

SCAFFOLDER only. Emits a STRIDE-organized template with a seed row per
category and an impact/likelihood matrix legend. Content is filled by
human/agent — this module never generates risks from prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List

__all__ = ["RiskRegisterScaffolder", "STRIDE_CATEGORIES", "render_template", "ScaffoldResult"]

DOC_REL = Path("docs/03-domain-risk/risk-register.md")

HEADER_MARKER = "<!-- risk-register:autogen-header -->"
FOOTER_MARKER = "<!-- risk-register:autogen-footer -->"

STRIDE_CATEGORIES: List[str] = [
    "Spoofing",
    "Tampering",
    "Repudiation",
    "Information Disclosure",
    "Denial of Service",
    "Elevation of Privilege",
]


def render_template(project_name: str, assets_brief: str = "") -> str:
    today = date.today().isoformat()
    assets_line = (assets_brief or "").strip() or "<!-- TODO: list top assets (data, services, keys) -->"

    stride_rows = []
    for i, cat in enumerate(STRIDE_CATEGORIES, start=1):
        rid = f"R-{i:02d}"
        stride_rows.append(
            f"| {rid} | {cat} | <!-- TODO: threat --> | L | L | <!-- TODO --> | <!-- TODO --> | open |"
        )
    stride_block = "\n".join(stride_rows)

    return (
        f"# Risk Register — {project_name}\n\n"
        f"_Last scaffolded: {today}_\n\n"
        f"{HEADER_MARKER}\n\n"
        "## Assets\n"
        f"{assets_line}\n\n"
        "## Likelihood / Impact legend\n\n"
        "- **L** (Low): unlikely / minor\n"
        "- **M** (Medium): plausible / moderate\n"
        "- **H** (High): expected / severe\n\n"
        "## Impact × Likelihood matrix\n\n"
        "|            | Low | Medium | High |\n"
        "|---|---|---|---|\n"
        "| **High impact**   | Watch | Mitigate | Critical |\n"
        "| **Medium impact** | Accept | Watch | Mitigate |\n"
        "| **Low impact**    | Accept | Accept | Watch |\n\n"
        "## STRIDE threats\n\n"
        "| ID | Category | Threat | Likelihood | Impact | Mitigation | Owner | Status |\n"
        "|---|---|---|---|---|---|---|---|\n"
        f"{stride_block}\n\n"
        "## Residual risks\n"
        "<!-- TODO: anything accepted after mitigation -->\n\n"
        f"{FOOTER_MARKER}\n\n"
        "<!-- Content below footer preserved across re-runs. -->\n"
    )


@dataclass
class ScaffoldResult:
    path: Path
    action: str  # created | extended | skipped | overwritten

    @property
    def summary(self) -> str:
        return f"risk-register: {self.action} {self.path}"


class RiskRegisterScaffolder:
    def __init__(
        self,
        project_dir: Path,
        assets_brief: str = "",
        project_name: str = "",
        overwrite: bool = False,
    ):
        self.project_dir = Path(project_dir).resolve()
        self.assets_brief = assets_brief or ""
        self.project_name = (project_name or self.project_dir.name).strip() or "project"
        self.overwrite = overwrite
        self.target = self.project_dir / DOC_REL

    def scaffold(self) -> ScaffoldResult:
        self.target.parent.mkdir(parents=True, exist_ok=True)
        body = render_template(self.project_name, self.assets_brief)

        if not self.target.exists():
            self.target.write_text(body)
            return ScaffoldResult(self.target, "created")

        if self.overwrite:
            self.target.write_text(body)
            return ScaffoldResult(self.target, "overwritten")

        existing = self.target.read_text()
        if HEADER_MARKER in existing and FOOTER_MARKER in existing:
            tail = existing.split(FOOTER_MARKER, 1)[1]
            new_body = body.split(FOOTER_MARKER, 1)[0] + FOOTER_MARKER + tail
            self.target.write_text(new_body)
            return ScaffoldResult(self.target, "extended")

        return ScaffoldResult(self.target, "skipped")
