# SCOPE: os-only
"""Scored Skill Archive for Cognitive OS.

Maintains a scored history of skill configurations. When a skill succeeds
with a high trust score, its content hash is snapshotted. When it fails,
the failure is recorded. Over time this builds a "best-of" registry per
skill, enabling data-driven rollback and rewrite decisions.

Applies scored archive and fitness tracking patterns to skill
configuration management.

Python 3.9+ compatible. No external dependencies.

Author: luum
"""

import hashlib
import json
import os
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lib.metric_event import MetricEvent, append_event


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SkillSnapshot:
    """A single recorded execution of a skill."""

    skill_name: str
    version: str               # SHA-256 hash of SKILL.md content
    timestamp: str             # ISO-8601
    trust_score: float         # 0-100, from trust report
    success: bool
    task_description: str      # what task used this skill
    tokens_used: int
    cost_usd: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class SkillArchive:
    """Aggregated archive for a single skill."""

    skill_name: str
    snapshots: List[SkillSnapshot] = field(default_factory=list)
    best_version: Optional[str] = None
    best_score: float = 0.0
    total_uses: int = 0
    success_rate: float = 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_ARCHIVE_PATH = ".cognitive-os/metrics/skill-archive.jsonl"


def _content_hash(content: str) -> str:
    """Compute a deterministic SHA-256 hash of skill content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def _snapshot_to_dict(snap: SkillSnapshot) -> Dict:
    return {
        "skill_name": snap.skill_name,
        "version": snap.version,
        "timestamp": snap.timestamp,
        "trust_score": snap.trust_score,
        "success": snap.success,
        "task_description": snap.task_description,
        "tokens_used": snap.tokens_used,
        "cost_usd": snap.cost_usd,
        "metadata": snap.metadata,
    }


def _dict_to_snapshot(d: Dict) -> SkillSnapshot:
    return SkillSnapshot(
        skill_name=d["skill_name"],
        version=d["version"],
        timestamp=d["timestamp"],
        trust_score=float(d["trust_score"]),
        success=bool(d["success"]),
        task_description=d.get("task_description", ""),
        tokens_used=int(d.get("tokens_used", 0)),
        cost_usd=float(d.get("cost_usd", 0.0)),
        metadata=d.get("metadata", {}),
    )


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class SkillArchiveManager:
    """Manages the scored skill archive.

    Reads/writes a JSONL file where each line is a serialised
    ``SkillSnapshot``.  All public methods are stateless with respect
    to the file — they re-read on every call so concurrent writers
    (other sessions) are always visible.
    """

    def __init__(
        self,
        archive_path: str = _DEFAULT_ARCHIVE_PATH,
    ) -> None:
        self.archive_path = archive_path

    # -- persistence -------------------------------------------------------

    def _read_all(self) -> List[SkillSnapshot]:
        """Read all snapshots, normalising MetricEvent-wrapped rows back to snapshot dicts."""
        path = Path(self.archive_path)
        if not path.exists():
            return []
        snapshots: List[SkillSnapshot] = []
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # Unwrap MetricEvent rows
                if "schema_version" in row and "event_type" in row and "payload" in row:
                    flat = dict(row["payload"])
                    flat.setdefault("timestamp", row.get("timestamp", ""))
                    row = flat
                try:
                    snapshots.append(_dict_to_snapshot(row))
                except KeyError:
                    continue
        return snapshots

    def _append(self, snap: SkillSnapshot) -> None:
        """Append a skill snapshot as a MetricEvent."""
        snap_dict = _snapshot_to_dict(snap)
        # timestamp is a top-level MetricEvent field
        timestamp = snap_dict.pop("timestamp", "")
        event = MetricEvent(
            source="skill-archive",
            event_type="skill.execution.recorded",
            payload=snap_dict,
            timestamp=timestamp,
        )
        append_event(self.archive_path, event)

    # -- public API --------------------------------------------------------

    def record_execution(
        self,
        skill_name: str,
        skill_content: str,
        trust_score: float,
        success: bool,
        task: str,
        tokens: int = 0,
        cost: float = 0.0,
        metadata: Optional[Dict] = None,
    ) -> SkillSnapshot:
        """Record a skill execution result.

        Creates a snapshot whose ``version`` is a SHA-256 digest of
        *skill_content* (the raw SKILL.md text).
        """
        snap = SkillSnapshot(
            skill_name=skill_name,
            version=_content_hash(skill_content),
            timestamp=datetime.now(timezone.utc).isoformat(),
            trust_score=float(trust_score),
            success=bool(success),
            task_description=task,
            tokens_used=int(tokens),
            cost_usd=float(cost),
            metadata=metadata or {},
        )
        self._append(snap)
        return snap

    def get_best_version(self, skill_name: str) -> Optional[SkillSnapshot]:
        """Return the highest-scoring *successful* snapshot for *skill_name*.

        Returns ``None`` when there are no successful snapshots.
        """
        successes = [
            s for s in self._read_all()
            if s.skill_name == skill_name and s.success
        ]
        if not successes:
            return None
        return max(successes, key=lambda s: s.trust_score)

    def get_archive(self, skill_name: str) -> SkillArchive:
        """Return the full archive for a skill with computed statistics."""
        all_snaps = [s for s in self._read_all() if s.skill_name == skill_name]
        if not all_snaps:
            return SkillArchive(skill_name=skill_name)

        successes = [s for s in all_snaps if s.success]
        best = max(successes, key=lambda s: s.trust_score) if successes else None

        return SkillArchive(
            skill_name=skill_name,
            snapshots=all_snaps,
            best_version=best.version if best else None,
            best_score=best.trust_score if best else 0.0,
            total_uses=len(all_snaps),
            success_rate=(len(successes) / len(all_snaps)) if all_snaps else 0.0,
        )

    def get_skill_trend(self, skill_name: str) -> Dict:
        """Determine whether *skill_name* is improving, stable, or degrading.

        Uses the last 5 successful snapshots compared to the all-time
        average.  Returns ``{trend, last_5_avg, all_time_avg}``.
        """
        successes = [
            s for s in self._read_all()
            if s.skill_name == skill_name and s.success
        ]
        if len(successes) < 2:
            all_time = successes[0].trust_score if successes else 0.0
            return {
                "trend": "stable",
                "last_5_avg": all_time,
                "all_time_avg": all_time,
            }

        scores = [s.trust_score for s in successes]
        all_time_avg = statistics.mean(scores)
        last_5 = scores[-5:]
        last_5_avg = statistics.mean(last_5)

        diff = last_5_avg - all_time_avg
        if diff > 5:
            trend = "improving"
        elif diff < -5:
            trend = "degrading"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "last_5_avg": round(last_5_avg, 2),
            "all_time_avg": round(all_time_avg, 2),
        }

    def get_underperforming_skills(
        self,
        threshold: float = 0.6,
    ) -> List[str]:
        """Return skill names whose success rate is below *threshold*.

        Only skills with at least one recorded execution are considered.
        """
        all_snaps = self._read_all()
        by_skill: Dict[str, List[SkillSnapshot]] = {}
        for s in all_snaps:
            by_skill.setdefault(s.skill_name, []).append(s)

        result: List[str] = []
        for name, snaps in by_skill.items():
            rate = sum(1 for s in snaps if s.success) / len(snaps)
            if rate < threshold:
                result.append(name)
        return sorted(result)

    def get_top_skills(self, n: int = 10) -> List[Tuple[str, float]]:
        """Return the top *n* skills ranked by average trust score.

        Only successful executions are used for ranking.
        """
        all_snaps = self._read_all()
        by_skill: Dict[str, List[float]] = {}
        for s in all_snaps:
            if s.success:
                by_skill.setdefault(s.skill_name, []).append(s.trust_score)

        ranked = [
            (name, round(statistics.mean(scores), 2))
            for name, scores in by_skill.items()
        ]
        ranked.sort(key=lambda t: t[1], reverse=True)
        return ranked[:n]

    def should_rollback(self, skill_name: str) -> Tuple[bool, str]:
        """Decide whether *skill_name* should be rolled back.

        Returns ``(True, reason)`` when the current version's average
        score is more than 20 percentage points below the best version's
        score.  Otherwise returns ``(False, "")``.
        """
        all_snaps = [s for s in self._read_all() if s.skill_name == skill_name]
        if not all_snaps:
            return False, ""

        successes = [s for s in all_snaps if s.success]
        if not successes:
            return False, ""

        best = max(successes, key=lambda s: s.trust_score)

        # Current version = the version of the most recent snapshot
        latest = all_snaps[-1]
        current_version = latest.version

        current_snaps = [s for s in successes if s.version == current_version]
        if not current_snaps:
            # Current version has no successes — might want rollback
            if best.version != current_version:
                return True, (
                    f"Current version {current_version} has no successful "
                    f"executions. Best version {best.version} scored "
                    f"{best.trust_score:.1f}."
                )
            return False, ""

        current_avg = statistics.mean([s.trust_score for s in current_snaps])
        if best.trust_score - current_avg > 20:
            return True, (
                f"Current version {current_version} averages "
                f"{current_avg:.1f} but best version {best.version} "
                f"scored {best.trust_score:.1f} (delta "
                f"{best.trust_score - current_avg:.1f} > 20)."
            )
        return False, ""

    def format_archive_report(
        self,
        skill_name: Optional[str] = None,
    ) -> str:
        """Format the archive as a Markdown report.

        If *skill_name* is given, produce a detailed single-skill report.
        Otherwise produce a summary across all skills.
        """
        all_snaps = self._read_all()
        if not all_snaps:
            return "SKILL ARCHIVE REPORT\n\nNo skill executions recorded yet."

        if skill_name:
            return self._format_single(skill_name, all_snaps)
        return self._format_summary(all_snaps)

    # -- private formatters ------------------------------------------------

    def _format_single(
        self,
        skill_name: str,
        all_snaps: List[SkillSnapshot],
    ) -> str:
        snaps = [s for s in all_snaps if s.skill_name == skill_name]
        if not snaps:
            return f"SKILL ARCHIVE REPORT: {skill_name}\n\nNo executions recorded."

        archive = self.get_archive(skill_name)
        trend_info = self.get_skill_trend(skill_name)
        rollback, rollback_reason = self.should_rollback(skill_name)

        lines = [
            f"SKILL ARCHIVE REPORT: {skill_name}",
            "",
            f"Total uses: {archive.total_uses}",
            f"Success rate: {archive.success_rate:.0%}",
            f"Trend: {trend_info['trend']}",
            f"Last 5 avg: {trend_info['last_5_avg']}",
            f"All-time avg: {trend_info['all_time_avg']}",
        ]
        if archive.best_version:
            lines.append(f"Best version: {archive.best_version} (score: {archive.best_score:.1f})")
        if rollback:
            lines.append(f"Rollback recommended: {rollback_reason}")
        lines.append("")
        lines.append("Recent executions:")
        for s in snaps[-5:]:
            status = "OK" if s.success else "FAIL"
            lines.append(
                f"  {s.timestamp[:10]} v:{s.version} "
                f"score:{s.trust_score:.0f} [{status}] "
                f"${s.cost_usd:.4f}"
            )
        return "\n".join(lines)

    def _format_summary(self, all_snaps: List[SkillSnapshot]) -> str:
        by_skill: Dict[str, List[SkillSnapshot]] = {}
        for s in all_snaps:
            by_skill.setdefault(s.skill_name, []).append(s)

        lines = ["SKILL ARCHIVE REPORT", ""]
        names = sorted(by_skill.keys())
        for i, name in enumerate(names):
            snaps = by_skill[name]
            archive = self.get_archive(name)
            trend_info = self.get_skill_trend(name)
            is_last = i == len(names) - 1
            prefix = "└──" if is_last else "├──"
            detail_prefix = "    " if is_last else "│   "

            trend_marker = ""
            if trend_info["trend"] == "degrading":
                trend_marker = " (degrading)"
            elif trend_info["trend"] == "improving":
                trend_marker = " (improving)"

            lines.append(
                f"{prefix} {name}: {archive.total_uses} uses, "
                f"{archive.success_rate:.0%} success, "
                f"trend: {trend_info['trend']}{trend_marker}"
            )
            if archive.best_version:
                lines.append(
                    f"{detail_prefix}Best version: {archive.best_version} "
                    f"(score: {archive.best_score:.1f})"
                )
            if archive.success_rate < 0.6:
                lines.append(
                    f"{detail_prefix}Recommendation: run /optimize-skill {name}"
                )
        return "\n".join(lines)
