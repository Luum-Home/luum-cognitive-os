# SCOPE: both
"""Domain model scaffolder — DDD template generator (ADR-054 Phase 2).

SCAFFOLDER only — emits templates with prompts and TODO markers.
Does NOT generate domain content from prose (would require LLM).

Usage:
    from lib.domain_model import DomainModelScaffolder
    s = DomainModelScaffolder(project_dir=Path("/tmp/x"), brief="ecommerce platform")
    result = s.scaffold()
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List

__all__ = ["DomainModelScaffolder", "ScaffoldResult", "render_template"]

DOC_REL = Path("docs/03-dominio-riesgo/domain-model.md")

HEADER_MARKER = "<!-- domain-model:autogen-header -->"
FOOTER_MARKER = "<!-- domain-model:autogen-footer -->"


def render_template(project_name: str, brief: str) -> str:
    """Produce a domain-model.md template body.

    Includes header/footer markers so idempotent extension can replace
    just the auto-generated scaffold without touching user content added
    outside the markers.
    """
    today = date.today().isoformat()
    brief_line = (brief or "").strip() or "<!-- TODO: describe domain in one paragraph -->"
    return (
        f"# Domain Model — {project_name}\n\n"
        f"_Last scaffolded: {today}_\n\n"
        f"{HEADER_MARKER}\n\n"
        "## Brief\n"
        f"{brief_line}\n\n"
        "## Bounded Contexts\n\n"
        "| Context | Purpose | Upstream | Downstream |\n"
        "|---|---|---|---|\n"
        "| <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n\n"
        "## Core Entities\n\n"
        "| Entity | Aggregate root | Invariants | Context |\n"
        "|---|---|---|---|\n"
        "| <!-- TODO --> | <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n\n"
        "## Value Objects\n\n"
        "| Name | Shape | Used by |\n"
        "|---|---|---|\n"
        "| <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n\n"
        "## Domain Events\n\n"
        "| Event | Emitted by | Consumed by |\n"
        "|---|---|---|\n"
        "| <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n\n"
        "## Ubiquitous Language\n\n"
        "| Term | Definition | Notes |\n"
        "|---|---|---|\n"
        "| <!-- TODO --> | <!-- TODO --> | <!-- TODO --> |\n\n"
        f"{FOOTER_MARKER}\n\n"
        "<!-- Content below the footer marker is preserved across re-runs. -->\n"
    )


@dataclass
class ScaffoldResult:
    path: Path
    action: str  # "created" | "extended" | "skipped" | "overwritten"

    @property
    def summary(self) -> str:
        return f"domain-model: {self.action} {self.path}"


class DomainModelScaffolder:
    """Emit/extend docs/03-dominio-riesgo/domain-model.md idempotently."""

    def __init__(
        self,
        project_dir: Path,
        brief: str = "",
        project_name: str = "",
        overwrite: bool = False,
    ):
        self.project_dir = Path(project_dir).resolve()
        self.brief = brief or ""
        self.project_name = (project_name or self.project_dir.name).strip() or "project"
        self.overwrite = overwrite
        self.target = self.project_dir / DOC_REL

    def scaffold(self) -> ScaffoldResult:
        self.target.parent.mkdir(parents=True, exist_ok=True)
        body = render_template(self.project_name, self.brief)

        if not self.target.exists():
            self.target.write_text(body)
            return ScaffoldResult(self.target, "created")

        if self.overwrite:
            self.target.write_text(body)
            return ScaffoldResult(self.target, "overwritten")

        existing = self.target.read_text()
        # If our markers already exist, replace the auto-block only,
        # preserving any user content AFTER the footer marker.
        if HEADER_MARKER in existing and FOOTER_MARKER in existing:
            tail = existing.split(FOOTER_MARKER, 1)[1]
            # Keep tail as-is (user content below footer is preserved)
            new_body = body.split(FOOTER_MARKER, 1)[0] + FOOTER_MARKER + tail
            self.target.write_text(new_body)
            return ScaffoldResult(self.target, "extended")

        # Existing file with no markers — don't destroy, skip
        return ScaffoldResult(self.target, "skipped")
