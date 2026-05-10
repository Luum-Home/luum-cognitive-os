# SCOPE: both
"""Read-only helpers for vendored agentapi msgfmt fixtures."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent / "testdata" / "agentapi" / "msgfmt"


@dataclass(frozen=True)
class AgentApiFixtureSummary:
    schema_version: str
    fixture_root: str
    harnesses: list[str]
    format_case_count: int
    initialization_case_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_fixtures(root: Path = ROOT) -> AgentApiFixtureSummary:
    format_dir = root / "format"
    init_dir = root / "initialization"
    harnesses = sorted({path.name for path in format_dir.iterdir() if path.is_dir()} | {path.name for path in init_dir.iterdir() if path.is_dir()}) if root.exists() else []
    return AgentApiFixtureSummary(
        schema_version="agentapi-msgfmt-fixtures/v1",
        fixture_root=str(root),
        harnesses=harnesses,
        format_case_count=sum(1 for path in format_dir.glob("*/*") if path.is_dir()) if format_dir.exists() else 0,
        initialization_case_count=sum(1 for path in init_dir.glob("*/*") if path.is_dir()) if init_dir.exists() else 0,
    )
