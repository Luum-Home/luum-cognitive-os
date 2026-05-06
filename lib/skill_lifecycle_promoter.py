# SCOPE: both
"""Skill lifecycle promotion evidence for Cognitive OS.

The promotion ladder is intentionally propose-only: this module reads sandbox
skill evidence and returns reviewable candidates. It never moves, edits, or
promotes a skill by itself.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:  # PyYAML is a project dependency, but keep import-time degradation clear.
    import yaml
except Exception:  # pragma: no cover - exercised only in broken environments
    yaml = None  # type: ignore[assignment]


@dataclass(frozen=True)
class SkillLifecycleCandidate:
    """A propose-only skill lifecycle transition candidate."""

    skill_name: str
    skill_path: str
    from_state: str
    proposed_state: str
    invocation_count: int
    successful_feedback_count: int
    feedback_count: int
    success_rate: float
    last_used: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkillLifecycleReport:
    """Aggregated skill lifecycle evidence."""

    status: str
    promotion_candidates: list[SkillLifecycleCandidate]
    demotion_candidates: list[SkillLifecycleCandidate]
    thresholds: dict[str, Any]
    policy: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "promotion_candidates": [candidate.to_dict() for candidate in self.promotion_candidates],
            "demotion_candidates": [candidate.to_dict() for candidate in self.demotion_candidates],
            "thresholds": self.thresholds,
            "policy": self.policy,
        }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _slug_from_path(path: Path) -> str:
    return path.parent.name


def _frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.match(r"\A(?:<!--.*?-->\s*)*---\s*\n(.*?)\n---\s*\n", text, flags=re.DOTALL)
    if not match or yaml is None:
        return {}
    try:
        loaded = yaml.safe_load(match.group(1)) or {}
    except Exception:  # noqa: BLE001 - malformed skill frontmatter must not break proposal generation
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _name_for(path: Path, frontmatter: dict[str, Any]) -> str:
    return str(frontmatter.get("name") or _slug_from_path(path))


def _is_sandbox_skill(project_root: Path, path: Path, frontmatter: dict[str, Any]) -> bool:
    rel = path.relative_to(project_root).as_posix()
    markers = {
        str(frontmatter.get("status", "")).lower(),
        str(frontmatter.get("tier", "")).lower(),
        str(frontmatter.get("lifecycle_state", "")).lower(),
        str(frontmatter.get("maturity", "")).lower(),
    }
    tags = frontmatter.get("tags") or []
    tag_set = {str(tag).lower() for tag in tags} if isinstance(tags, list) else set()
    return (
        rel.startswith(".cognitive-os/skills/auto-generated/")
        or rel.startswith("skills/auto-generated/")
        or rel.startswith("skills/experimental/")
        or bool(frontmatter.get("auto-generated") is True)
        or bool({"sandbox", "draft", "experimental"} & markers)
        or "auto-generated" in tag_set
    )


def _is_advisory_skill(project_root: Path, path: Path, frontmatter: dict[str, Any]) -> bool:
    rel = path.relative_to(project_root).as_posix()
    if _is_sandbox_skill(project_root, path, frontmatter):
        return False
    markers = {
        str(frontmatter.get("status", "")).lower(),
        str(frontmatter.get("tier", "")).lower(),
        str(frontmatter.get("lifecycle_state", "")).lower(),
        str(frontmatter.get("maturity", "")).lower(),
        str(frontmatter.get("risk_class", "")).lower(),
    }
    return rel.startswith("skills/") and "advisory" in markers


def discover_skills(project_root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    """Discover skill files keyed by frontmatter name or directory slug."""
    roots = [project_root / ".cognitive-os" / "skills", project_root / "skills"]
    discovered: dict[str, tuple[Path, dict[str, Any]]] = {}
    for root in roots:
        if not root.exists():
            continue
        for skill_file in sorted(root.glob("**/SKILL.md")):
            fm = _frontmatter(skill_file)
            discovered[_name_for(skill_file, fm)] = (skill_file, fm)
    return discovered


def _metric_skill_name(row: dict[str, Any]) -> str | None:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else row
    for key in ("skill_name", "name", "skill"):
        value = payload.get(key) if isinstance(payload, dict) else None
        if value:
            return str(value)
    return None


def _metric_time(row: dict[str, Any]) -> datetime | None:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    return _parse_time(row.get("timestamp") or (payload.get("timestamp") if isinstance(payload, dict) else None))


def _empty_usage() -> dict[str, Any]:
    return {"invocations": 0, "feedback": 0, "successful_feedback": 0, "last_used": None}


def _usage_entry(usage: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
    return usage.setdefault(name, _empty_usage())


def _collect_jsonl_usage(project_root: Path, window_start: datetime) -> dict[str, dict[str, Any]]:
    metrics_dir = project_root / ".cognitive-os" / "metrics"
    usage: dict[str, dict[str, Any]] = {}

    for filename in ("skill-invocations.jsonl", "skill-usage.jsonl", "skill-archive.jsonl"):
        for row in _read_jsonl(metrics_dir / filename):
            name = _metric_skill_name(row)
            ts = _metric_time(row)
            if not name or not ts or ts < window_start:
                continue
            item = _usage_entry(usage, name)
            item["invocations"] += 1
            if item["last_used"] is None or ts > item["last_used"]:
                item["last_used"] = ts
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else row
            if isinstance(payload, dict) and "success" in payload:
                item["feedback"] += 1
                if payload.get("success") is True:
                    item["successful_feedback"] += 1

    for row in _read_jsonl(metrics_dir / "skill-feedback.jsonl"):
        name = _metric_skill_name(row)
        ts = _metric_time(row)
        if not name or not ts or ts < window_start:
            continue
        item = _usage_entry(usage, name)
        item["feedback"] += 1
        if row.get("success") is True:
            item["successful_feedback"] += 1
        if item["last_used"] is None or ts > item["last_used"]:
            item["last_used"] = ts

    return usage


def _skillstore_has_execution_events(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='skill_execution_events'"
    ).fetchone()
    return row is not None


def _collect_skillstore_usage(project_root: Path, window_start: datetime) -> dict[str, dict[str, Any]]:
    """Collect exact lifecycle-window usage from SkillStore execution events."""

    db_path = project_root / ".cognitive-os" / "skill_store.db"
    if not db_path.exists():
        return {}

    usage: dict[str, dict[str, Any]] = {}
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        if not _skillstore_has_execution_events(conn):
            conn.close()
            return {}
        rows = conn.execute(
            """
            SELECT name, timestamp, applied
            FROM skill_execution_events
            ORDER BY timestamp ASC
            """
        ).fetchall()
        conn.close()
    except sqlite3.Error:
        return {}

    for row in rows:
        name = str(row["name"] or "")
        ts = _parse_time(row["timestamp"])
        if not name or not ts or ts < window_start:
            continue
        item = _usage_entry(usage, name)
        item["invocations"] += 1
        item["feedback"] += 1
        if int(row["applied"] or 0) == 1:
            item["successful_feedback"] += 1
        if item["last_used"] is None or ts > item["last_used"]:
            item["last_used"] = ts
    return usage


def _collect_usage(project_root: Path, window_start: datetime) -> dict[str, dict[str, Any]]:
    """Collect usage with SkillStore as primary and JSONL as compatibility fallback.

    SkillStore is the canonical evidence path after ADR-176/177 because it is
    queryable and shared by the proposers. JSONL remains a per-skill fallback
    for older fixtures and installations that have not yet populated
    skill_execution_events.
    """

    primary = _collect_skillstore_usage(project_root, window_start)
    fallback = _collect_jsonl_usage(project_root, window_start)
    merged = dict(primary)
    for name, row in fallback.items():
        if name not in merged:
            merged[name] = row
    return merged


def build_skill_lifecycle_report(
    project_root: Path,
    *,
    now: datetime | None = None,
    promotion_invocation_threshold: int = 50,
    promotion_window_days: int = 30,
    min_success_rate: float = 0.8,
    min_successful_feedback: int = 5,
    demotion_window_days: int = 90,
) -> SkillLifecycleReport:
    """Return propose-only promotion/demotion candidates from skill evidence."""
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    promotion_start = current - timedelta(days=promotion_window_days)
    demotion_cutoff = current - timedelta(days=demotion_window_days)
    promotion_usage = _collect_usage(project_root, promotion_start)
    demotion_usage = _collect_usage(project_root, demotion_cutoff)
    skills = discover_skills(project_root)

    empty_usage = _empty_usage()
    promotions: list[SkillLifecycleCandidate] = []
    demotions: list[SkillLifecycleCandidate] = []

    for skill_name, (skill_path, fm) in sorted(skills.items()):
        row = promotion_usage.get(skill_name, empty_usage)
        feedback = int(row["feedback"])
        successful = int(row["successful_feedback"])
        success_rate = round(successful / feedback, 4) if feedback else 0.0
        last_used = row["last_used"]
        last_used_text = last_used.isoformat() if isinstance(last_used, datetime) else None
        rel = skill_path.relative_to(project_root).as_posix()

        if _is_sandbox_skill(project_root, skill_path, fm):
            if (
                int(row["invocations"]) >= promotion_invocation_threshold
                and successful >= min_successful_feedback
                and success_rate >= min_success_rate
            ):
                promotions.append(
                    SkillLifecycleCandidate(
                        skill_name=skill_name,
                        skill_path=rel,
                        from_state="sandbox",
                        proposed_state="advisory",
                        invocation_count=int(row["invocations"]),
                        successful_feedback_count=successful,
                        feedback_count=feedback,
                        success_rate=success_rate,
                        last_used=last_used_text,
                        reason="sandbox skill crossed usage and judged-usefulness thresholds; propose advisory review only",
                    )
                )
            continue

        if _is_advisory_skill(project_root, skill_path, fm):
            row = demotion_usage.get(skill_name, empty_usage)
            feedback = int(row["feedback"])
            successful = int(row["successful_feedback"])
            success_rate = round(successful / feedback, 4) if feedback else 0.0
            last_used = row["last_used"]
            last_used_text = last_used.isoformat() if isinstance(last_used, datetime) else None
            if last_used is None or last_used < demotion_cutoff:
                demotions.append(
                    SkillLifecycleCandidate(
                        skill_name=skill_name,
                        skill_path=rel,
                        from_state="advisory",
                        proposed_state="demoted",
                        invocation_count=int(row["invocations"]),
                        successful_feedback_count=successful,
                        feedback_count=feedback,
                        success_rate=success_rate,
                        last_used=last_used_text,
                        reason="advisory skill has no recent usage evidence; propose demotion review only",
                    )
                )

    status = "proposals_available" if promotions or demotions else "pass"
    return SkillLifecycleReport(
        status=status,
        promotion_candidates=promotions,
        demotion_candidates=demotions,
        thresholds={
            "promotion_invocation_threshold": promotion_invocation_threshold,
            "promotion_window_days": promotion_window_days,
            "min_success_rate": min_success_rate,
            "min_successful_feedback": min_successful_feedback,
            "demotion_window_days": demotion_window_days,
        },
        policy="skill lifecycle transitions are propose-only; generated evidence never mutates SKILL.md routing canon",
    )
