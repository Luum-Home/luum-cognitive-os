# scope: both
"""Pre-development artifact completeness checker."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


REQUIRED_ARTIFACTS = {
    "context": "docs/01-context/",
    "threat-model": "docs/04-security/",
    "execution-plan": "docs/09-execution-plan/",
}

OPTIONAL_ARTIFACTS = {
    "architecture": "docs/02-architecture/",
    "features": "docs/05-features/",
    "research": "docs/07-research/",
    "standards": "docs/08-standards/",
    "summaries": "docs/10-summaries/",
}

_RECOMMENDED_SKILLS = {
    "context": "/sdd-explore",
    "threat-model": "/security-audit",
    "execution-plan": "/plan-feature",
}


@dataclass
class ArtifactStatus:
    exists: bool
    path: str
    file_count: int
    last_modified: Optional[float]


@dataclass
class CompletenessReport:
    artifacts: Dict[str, ArtifactStatus]
    verdict: str
    missing: List[str] = field(default_factory=list)
    present: List[str] = field(default_factory=list)
    optional_present: List[str] = field(default_factory=list)
    optional_missing: List[str] = field(default_factory=list)


def check_artifact(project_dir: str, artifact_path: str) -> ArtifactStatus:
    """Check if a directory exists under project_dir and contains .md files."""
    directory = Path(project_dir) / artifact_path

    if not directory.exists() or not directory.is_dir():
        return ArtifactStatus(exists=False, path=str(directory), file_count=0, last_modified=None)

    md_files = list(directory.glob("*.md"))
    file_count = len(md_files)

    last_modified: Optional[float] = None
    if md_files:
        last_modified = max(f.stat().st_mtime for f in md_files)

    return ArtifactStatus(
        exists=directory.exists(),
        path=str(directory),
        file_count=file_count,
        last_modified=last_modified,
    )


def check_predev_artifacts(project_dir: str) -> CompletenessReport:
    """Check all required and optional pre-development artifacts."""
    artifacts: Dict[str, ArtifactStatus] = {}
    present: List[str] = []
    missing: List[str] = []
    optional_present: List[str] = []
    optional_missing: List[str] = []

    for name, path in REQUIRED_ARTIFACTS.items():
        status = check_artifact(project_dir, path)
        artifacts[name] = status
        if status.exists and status.file_count > 0:
            present.append(name)
        else:
            missing.append(name)

    for name, path in OPTIONAL_ARTIFACTS.items():
        status = check_artifact(project_dir, path)
        artifacts[name] = status
        if status.exists and status.file_count > 0:
            optional_present.append(name)
        else:
            optional_missing.append(name)

    total_required = len(REQUIRED_ARTIFACTS)
    present_count = len(present)

    if present_count == total_required:
        verdict = "READY"
    elif present_count > 0:
        verdict = "PARTIAL"
    else:
        verdict = "NOT_READY"

    return CompletenessReport(
        artifacts=artifacts,
        verdict=verdict,
        missing=missing,
        present=present,
        optional_present=optional_present,
        optional_missing=optional_missing,
    )


def format_report(report: CompletenessReport) -> str:
    """Format a CompletenessReport as a human-readable string."""
    lines: List[str] = []

    verdict_emoji = {"READY": "✅", "PARTIAL": "⚠️", "NOT_READY": "❌"}.get(report.verdict, "?")
    lines.append(f"Pre-Development Artifact Completeness: {verdict_emoji} {report.verdict}")
    lines.append("")

    lines.append("Required Artifacts:")
    for name in REQUIRED_ARTIFACTS:
        status = report.artifacts.get(name)
        if status and status.exists and status.file_count > 0:
            lines.append(f"  ✓ {name} ({status.file_count} file(s))")
        else:
            skill = _RECOMMENDED_SKILLS.get(name, "")
            hint = f" — run {skill}" if skill else ""
            lines.append(f"  ✗ {name} [MISSING]{hint}")

    if OPTIONAL_ARTIFACTS:
        lines.append("")
        lines.append("Optional Artifacts:")
        for name in OPTIONAL_ARTIFACTS:
            status = report.artifacts.get(name)
            if status and status.exists and status.file_count > 0:
                lines.append(f"  ✓ {name} ({status.file_count} file(s))")
            else:
                lines.append(f"  · {name} [not present]")

    if report.missing:
        lines.append("")
        lines.append("Missing required artifacts:")
        for name in report.missing:
            skill = _RECOMMENDED_SKILLS.get(name, "")
            hint = f" (run {skill})" if skill else ""
            lines.append(f"  - {name}{hint}")

    return "\n".join(lines)
