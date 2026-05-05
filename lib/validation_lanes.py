"""Validation lane budgets, report retention, and diff-aware recommendations."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable
import json
import time


@dataclass(frozen=True)
class LaneBudget:
    lane: str
    timeout_seconds: int
    max_runtime_seconds: int
    owner: str
    failure_semantics: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


LANE_BUDGETS: dict[str, LaneBudget] = {
    "fast": LaneBudget("fast", 120, 180, "active-agent", "fail-fast local confidence"),
    "landing": LaneBudget("landing", 600, 900, "merge-queue", "blocks main landing"),
    "laptop": LaneBudget("laptop", 1800, 2400, "maintainer", "broad non-cost local confidence"),
    "full": LaneBudget("full", 3600, 5400, "release-maintainer", "release confidence"),
    "chaos": LaneBudget("chaos", 900, 1200, "safety-maintainer", "race-regression evidence"),
}


def lane_budgets() -> dict[str, dict[str, Any]]:
    return {name: budget.to_dict() for name, budget in LANE_BUDGETS.items()}


def active_report_paths(project_dir: Path) -> set[Path]:
    project_dir = project_dir.resolve()
    runtime = project_dir / ".cognitive-os" / "runtime"
    paths: set[Path] = set()
    for lock_name in ("validation-capsule.lock", "active-report.lock"):
        lock = runtime / lock_name
        if not lock.exists():
            continue
        try:
            data = json.loads(lock.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for key in ("report_path", "report_dir", "capsule_dir"):
            value = data.get(key)
            if value:
                paths.add(Path(value).resolve())
    return paths


def can_cleanup_report(project_dir: Path, report_path: Path, *, now: float | None = None, retention_seconds: int = 7 * 24 * 3600) -> tuple[bool, str]:
    report = report_path.resolve()
    for active in active_report_paths(project_dir):
        if report == active or active in report.parents or report in active.parents:
            return False, "active validation report/capsule is protected"
    now = time.time() if now is None else now
    try:
        age = now - report.stat().st_mtime
    except OSError:
        return False, "report path missing"
    if age < retention_seconds:
        return False, "report retention grace"
    return True, "report retention expired"


@dataclass(frozen=True)
class LaneRecommendation:
    recommended_lane: str
    rationale: list[str]
    changed_files: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def recommend_lane(changed_files: Iterable[str]) -> LaneRecommendation:
    files = sorted({path.strip() for path in changed_files if path.strip()})
    rationale: list[str] = []
    if not files:
        return LaneRecommendation("fast", ["no changed files detected"], files)
    if any(path.startswith("hooks/") for path in files):
        rationale.append("hook changes require laptop lane")
        return LaneRecommendation("laptop", rationale, files)
    if any(path.startswith("scripts/") or path.startswith("lib/") for path in files):
        rationale.append("runtime script/library changes require landing lane")
        return LaneRecommendation("landing", rationale, files)
    if any(path.startswith("tests/chaos/") for path in files):
        rationale.append("chaos fixture changes require chaos lane")
        return LaneRecommendation("chaos", rationale, files)
    if any(path in {"cognitive-os.yaml", "manifests/hook-quality.yaml"} or path.startswith((".claude/", ".codex/", "manifests/")) for path in files):
        rationale.append("projection or harness artifact changes require landing lane")
        return LaneRecommendation("landing", rationale, files)
    if all(path.startswith("docs/adrs/") or path.startswith(".cognitive-os/plans/") or path.endswith(".md") for path in files):
        rationale.append("ADR/docs-only diff fits fast lane")
        return LaneRecommendation("fast", rationale, files)
    if any(path.startswith("tests/") for path in files):
        rationale.append("test-only diff fits fast targeted lane")
        return LaneRecommendation("fast", rationale, files)
    rationale.append("mixed or unclassified diff requires landing lane")
    return LaneRecommendation("landing", rationale, files)
