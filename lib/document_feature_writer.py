# SCOPE: os-only
"""Document-feature adopter-path writer (ADR-054 Phase 2 extension).

Extends the `document-feature` skill so its output can be routed to the
10-category convention path: `<project>/docs/05-features/features-backlog.md`
(appended, not overwritten).

The original skill behavior is preserved when --project-dir is not given.
This module only handles the *append to backlog* path.

Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

__all__ = ["BacklogAppender", "AppendResult", "render_entry"]

BACKLOG_REL = Path("docs/05-features/features-backlog.md")

BACKLOG_HEADER = "# Features Backlog\n\n"
TABLE_HEADER = (
    "| ID | Feature | Status | Priority | Owner | Added |\n"
    "|---|---|---|---|---|---|\n"
)


def _next_id(existing: str) -> str:
    """Return F-NN where NN is one higher than any existing F-\\d+ in text."""
    import re

    nums = [int(m.group(1)) for m in re.finditer(r"\|\s*F-(\d+)\s*\|", existing)]
    n = (max(nums) + 1) if nums else 1
    return f"F-{n:02d}"


def render_entry(
    feature_id: str,
    feature_name: str,
    status: str = "backlog",
    priority: str = "M",
    owner: str = "<!-- TODO -->",
    added: Optional[str] = None,
) -> str:
    added = added or date.today().isoformat()
    return f"| {feature_id} | {feature_name} | {status} | {priority} | {owner} | {added} |\n"


@dataclass
class AppendResult:
    path: Path
    feature_id: str
    action: str  # "created" | "appended"

    @property
    def summary(self) -> str:
        return f"document-feature: {self.action} {self.feature_id} -> {self.path}"


class BacklogAppender:
    """Append a feature row to `docs/05-features/features-backlog.md`.

    Creates the file if absent. Assigns a monotonically-increasing F-NN id
    based on the highest id already in the file.
    """

    def __init__(
        self,
        project_dir: Path,
        feature_name: str,
        status: str = "backlog",
        priority: str = "M",
        owner: str = "<!-- TODO -->",
    ):
        if not feature_name or not feature_name.strip():
            raise ValueError("feature_name must be non-empty")
        self.project_dir = Path(project_dir).resolve()
        self.feature_name = feature_name.strip()
        self.status = status
        self.priority = priority
        self.owner = owner
        self.target = self.project_dir / BACKLOG_REL

    def append(self) -> AppendResult:
        self.target.parent.mkdir(parents=True, exist_ok=True)

        if not self.target.exists():
            fid = "F-01"
            body = (
                BACKLOG_HEADER
                + TABLE_HEADER
                + render_entry(fid, self.feature_name, self.status, self.priority, self.owner)
            )
            self.target.write_text(body)
            return AppendResult(self.target, fid, "created")

        existing = self.target.read_text()
        fid = _next_id(existing)

        # If no table header, add one before appending
        if "| ID |" not in existing:
            existing = existing.rstrip() + "\n\n" + TABLE_HEADER
        # Ensure trailing newline
        if not existing.endswith("\n"):
            existing += "\n"
        existing += render_entry(
            fid, self.feature_name, self.status, self.priority, self.owner
        )
        self.target.write_text(existing)
        return AppendResult(self.target, fid, "appended")
