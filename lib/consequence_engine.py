"""OKR-driven consequence engine for Cognitive OS.

Connects performance metrics to real consequences: when agents/skills
perform well they are promoted (snapshot saved, model upgraded, preferred
for future tasks). When they perform poorly they are warned, degraded,
or temporarily disabled.

Score >= 85% consistently (5 streak) -> PROMOTE
Score 60-85% -> MAINTAIN
Score < 60% first time -> WARN
Score < 60% 2nd consecutive -> DEGRADE
Score < 60% 3rd consecutive -> DISABLE (temporary)

Python 3.9+ compatible. No external dependencies.

Author: luum
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums and data classes
# ---------------------------------------------------------------------------


class Consequence(Enum):
    PROMOTE = "promote"
    MAINTAIN = "maintain"
    WARN = "warn"
    DEGRADE = "degrade"
    DISABLE = "disable"


@dataclass
class PerformanceRecord:
    agent_or_skill: str
    task_type: str
    trust_score: float
    success: bool
    cost_usd: float
    tokens_used: int
    retries: int
    timestamp: str


@dataclass
class ConsequenceAction:
    target: str
    consequence: Consequence
    reason: str
    actions_taken: List[str]
    timestamp: str


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_HISTORY_PATH = ".cognitive-os/metrics/consequence-history.jsonl"

_DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "promote": 85.0,
    "warn": 60.0,
    "consecutive_fails_to_disable": 3,
    "promote_streak_required": 5,
}

from lib.model_catalog import ModelCatalog


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _record_to_dict(rec: PerformanceRecord) -> Dict[str, Any]:
    return {
        "record_type": "performance",
        "agent_or_skill": rec.agent_or_skill,
        "task_type": rec.task_type,
        "trust_score": rec.trust_score,
        "success": rec.success,
        "cost_usd": rec.cost_usd,
        "tokens_used": rec.tokens_used,
        "retries": rec.retries,
        "timestamp": rec.timestamp,
    }


def _dict_to_record(d: Dict[str, Any]) -> PerformanceRecord:
    return PerformanceRecord(
        agent_or_skill=d["agent_or_skill"],
        task_type=d.get("task_type", "general"),
        trust_score=float(d["trust_score"]),
        success=bool(d["success"]),
        cost_usd=float(d.get("cost_usd", 0.0)),
        tokens_used=int(d.get("tokens_used", 0)),
        retries=int(d.get("retries", 0)),
        timestamp=d["timestamp"],
    )


def _action_to_dict(action: ConsequenceAction) -> Dict[str, Any]:
    return {
        "record_type": "action",
        "target": action.target,
        "consequence": action.consequence.value,
        "reason": action.reason,
        "actions_taken": action.actions_taken,
        "timestamp": action.timestamp,
    }


def _dict_to_action(d: Dict[str, Any]) -> ConsequenceAction:
    return ConsequenceAction(
        target=d["target"],
        consequence=Consequence(d["consequence"]),
        reason=d["reason"],
        actions_taken=d.get("actions_taken", []),
        timestamp=d["timestamp"],
    )


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class ConsequenceEngine:
    """Connects performance metrics to real consequences.

    Score >= 85% consistently -> PROMOTE
    Score 60-85% -> MAINTAIN
    Score < 60% -> WARN (first time), DEGRADE (pattern), DISABLE (3+ consecutive)
    """

    def __init__(
        self,
        history_path: str = _DEFAULT_HISTORY_PATH,
        config_path: str = "cognitive-os.yaml",
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.history_path = history_path
        self.config_path = config_path
        self.thresholds = dict(_DEFAULT_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)

    # -- persistence -------------------------------------------------------

    def _read_all_raw(self) -> List[Dict[str, Any]]:
        path = Path(self.history_path)
        if not path.exists():
            return []
        entries: List[Dict[str, Any]] = []
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries

    def _append_raw(self, entry: Dict[str, Any]) -> None:
        path = Path(self.history_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, default=str) + "\n")

    # -- core evaluation ---------------------------------------------------

    def evaluate(self, record: PerformanceRecord) -> ConsequenceAction:
        """Evaluate a single performance record and determine consequence.

        Logic:
        1. If score >= 85 and last N scores all >= 85 -> PROMOTE
        2. If score >= 60 -> MAINTAIN
        3. If score < 60 (first time) -> WARN
        4. If score < 60 (2nd consecutive) -> DEGRADE
        5. If score < 60 (3rd consecutive) -> DISABLE
        """
        # Persist the performance record
        self._append_raw(_record_to_dict(record))

        promote_threshold = float(self.thresholds["promote"])
        warn_threshold = float(self.thresholds["warn"])
        streak_required = int(self.thresholds["promote_streak_required"])
        fails_to_disable = int(self.thresholds["consecutive_fails_to_disable"])

        now = record.timestamp

        # Check for promotion: current + last (streak_required - 1) all >= promote
        if record.trust_score >= promote_threshold:
            history = self.get_performance_history(
                record.agent_or_skill, last_n=streak_required
            )
            # history includes the record we just appended
            if len(history) >= streak_required and all(
                r.trust_score >= promote_threshold for r in history[-streak_required:]
            ):
                return ConsequenceAction(
                    target=record.agent_or_skill,
                    consequence=Consequence.PROMOTE,
                    reason=(
                        f"{streak_required} consecutive scores >= {promote_threshold:.0f}% "
                        f"(latest: {record.trust_score:.0f}%)"
                    ),
                    actions_taken=[],
                    timestamp=now,
                )
            # High score but not enough streak -> MAINTAIN
            return ConsequenceAction(
                target=record.agent_or_skill,
                consequence=Consequence.MAINTAIN,
                reason=f"Score {record.trust_score:.0f}% >= {warn_threshold:.0f}%",
                actions_taken=[],
                timestamp=now,
            )

        if record.trust_score >= warn_threshold:
            return ConsequenceAction(
                target=record.agent_or_skill,
                consequence=Consequence.MAINTAIN,
                reason=f"Score {record.trust_score:.0f}% in acceptable range",
                actions_taken=[],
                timestamp=now,
            )

        # Score < warn_threshold -> count consecutive low scores
        consecutive_low = self._count_consecutive_low(
            record.agent_or_skill, warn_threshold
        )

        if consecutive_low >= fails_to_disable:
            return ConsequenceAction(
                target=record.agent_or_skill,
                consequence=Consequence.DISABLE,
                reason=(
                    f"{consecutive_low} consecutive scores below {warn_threshold:.0f}% "
                    f"(latest: {record.trust_score:.0f}%)"
                ),
                actions_taken=[],
                timestamp=now,
            )
        elif consecutive_low >= 2:
            return ConsequenceAction(
                target=record.agent_or_skill,
                consequence=Consequence.DEGRADE,
                reason=(
                    f"{consecutive_low} consecutive scores below {warn_threshold:.0f}% "
                    f"(latest: {record.trust_score:.0f}%)"
                ),
                actions_taken=[],
                timestamp=now,
            )
        else:
            return ConsequenceAction(
                target=record.agent_or_skill,
                consequence=Consequence.WARN,
                reason=f"Score {record.trust_score:.0f}% below {warn_threshold:.0f}% threshold",
                actions_taken=[],
                timestamp=now,
            )

    def _count_consecutive_low(
        self, agent_or_skill: str, threshold: float
    ) -> int:
        """Count how many of the most recent records are below threshold."""
        history = self.get_performance_history(agent_or_skill, last_n=10)
        count = 0
        for rec in reversed(history):
            if rec.trust_score < threshold:
                count += 1
            else:
                break
        return count

    # -- apply consequences ------------------------------------------------

    def apply_consequence(self, action: ConsequenceAction) -> List[str]:
        """Apply the consequence and return list of actions taken.

        PROMOTE: save skill snapshot, log promotion
        DEGRADE: downgrade model preference, log degradation
        DISABLE: add to disabled list, suggest rewrite
        WARN/MAINTAIN: log only
        """
        actions: List[str] = []

        if action.consequence == Consequence.PROMOTE:
            actions.append(f"Promoted {action.target} — saving best-version snapshot")
            # Record promotion in history
            self._append_raw({
                "record_type": "promotion",
                "target": action.target,
                "reason": action.reason,
                "timestamp": action.timestamp,
            })

        elif action.consequence == Consequence.DEGRADE:
            # Find current model and suggest downgrade
            downgrade_msg = self._suggest_model_downgrade(action.target)
            actions.append(
                f"Degraded {action.target} — {downgrade_msg}"
            )
            self._append_raw({
                "record_type": "degradation",
                "target": action.target,
                "reason": action.reason,
                "downgrade": downgrade_msg,
                "timestamp": action.timestamp,
            })

        elif action.consequence == Consequence.DISABLE:
            actions.append(
                f"Disabled {action.target} after consecutive failures — "
                f"suggest /optimize-skill rewrite"
            )
            self._append_raw({
                "record_type": "disable",
                "target": action.target,
                "reason": action.reason,
                "timestamp": action.timestamp,
            })

        elif action.consequence == Consequence.WARN:
            actions.append(
                f"Warning for {action.target}: {action.reason}"
            )

        # Update action with the actions taken
        action.actions_taken = actions
        return actions

    def _suggest_model_downgrade(self, target: str) -> str:
        """Suggest a model downgrade for the target."""
        try:
            downgraded = ModelCatalog.downgrade(target)
            if downgraded is not None:
                return f"downgrade {target} -> {downgraded}"
        except KeyError:
            # target might not be a model name but a skill/agent name;
            # try extracting a model family keyword
            for family in ("opus", "sonnet", "haiku"):
                if family in target.lower():
                    down = ModelCatalog.downgrade(family)
                    if down is not None:
                        return f"downgrade {family} -> {down}"
        return "use cheaper model + require human review"

    # -- queries -----------------------------------------------------------

    def get_performance_history(
        self, agent_or_skill: str, last_n: int = 10
    ) -> List[PerformanceRecord]:
        """Get recent performance records for an agent/skill."""
        raw = self._read_all_raw()
        records = []
        for entry in raw:
            if (
                entry.get("record_type") == "performance"
                and entry.get("agent_or_skill") == agent_or_skill
            ):
                try:
                    records.append(_dict_to_record(entry))
                except (KeyError, ValueError):
                    continue
        return records[-last_n:]

    def get_disabled_skills(self) -> List[Dict[str, Any]]:
        """List currently disabled skills with reasons and disable date.

        A skill is considered disabled if the most recent action for it
        is a 'disable' record and no subsequent 're-enable' record exists.
        """
        raw = self._read_all_raw()
        disabled: Dict[str, Dict[str, Any]] = {}

        for entry in raw:
            rt = entry.get("record_type", "")
            target = entry.get("target", "")
            if rt == "disable":
                disabled[target] = {
                    "skill": target,
                    "reason": entry.get("reason", ""),
                    "disabled_at": entry.get("timestamp", ""),
                }
            elif rt == "re-enable" and target in disabled:
                del disabled[target]

        return list(disabled.values())

    def get_skills_needing_rewrite(
        self,
        metrics_dir: str = ".cognitive-os/metrics",
        threshold: int = 3,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Return skills that have failed >= threshold times in the last N hours.

        A "failure" is any performance record with ``success=False``.
        Reads consequence-history.jsonl (self.history_path) and returns a
        list of dicts with keys:
          - skill_name: str
          - failure_count: int
          - last_error: str   (task_type of the most recent failure)
          - suggested_action: str

        Only skills with failure_count >= threshold are returned.
        Skills that are already disabled are included (they may need rewrite
        even if not re-enabled yet).
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        raw = self._read_all_raw()

        # Collect failures per skill within the time window
        failures_by_skill: Dict[str, List[Dict[str, Any]]] = {}
        for entry in raw:
            if entry.get("record_type") != "performance":
                continue
            if entry.get("success", True):
                continue
            try:
                ts_str = entry.get("timestamp", "")
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
            if ts < cutoff:
                continue
            skill = entry.get("agent_or_skill", "")
            if not skill:
                continue
            failures_by_skill.setdefault(skill, []).append(entry)

        result: List[Dict[str, Any]] = []
        for skill_name, failures in failures_by_skill.items():
            count = len(failures)
            if count < threshold:
                continue
            # Most recent failure first
            failures_sorted = sorted(failures, key=lambda e: e.get("timestamp", ""), reverse=True)
            last_failure = failures_sorted[0]
            last_error = last_failure.get("task_type", "") or last_failure.get("agent_or_skill", "")
            result.append({
                "skill_name": skill_name,
                "failure_count": count,
                "last_error": last_error,
                "suggested_action": f"/optimize-skill {skill_name}",
            })

        # Sort by failure_count descending so worst offenders come first
        result.sort(key=lambda x: x["failure_count"], reverse=True)
        return result

    def re_enable_skill(self, skill_name: str) -> bool:
        """Re-enable a disabled skill (after rewrite/optimization).

        Returns True if the skill was disabled and is now re-enabled.
        """
        disabled = self.get_disabled_skills()
        is_disabled = any(d["skill"] == skill_name for d in disabled)
        if not is_disabled:
            return False

        self._append_raw({
            "record_type": "re-enable",
            "target": skill_name,
            "reason": "Re-enabled after optimization",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return True

    def is_skill_disabled(self, skill_name: str) -> bool:
        """Return True if *skill_name* is currently disabled.

        A skill is disabled when the most recent action record for it is
        'disable' and no subsequent 're-enable' record exists.
        """
        if not skill_name:
            return False
        disabled = self.get_disabled_skills()
        return any(d["skill"] == skill_name for d in disabled)

    def get_model_override(self, skill_name: str) -> Optional[str]:
        """Return a forced model downgrade for a degraded skill, or None.

        If the most recent action for *skill_name* is a 'degradation' record,
        we return the recommended downgraded model tier (haiku/sonnet/opus).
        The caller (dispatch-gate) should use this instead of the task-derived
        model recommendation.

        Returns None when no downgrade is in effect.
        """
        if not skill_name:
            return None

        raw = self._read_all_raw()

        # Walk backwards to find the most recent action for this skill
        for entry in reversed(raw):
            target = entry.get("target", "")
            if target != skill_name:
                continue
            rt = entry.get("record_type", "")
            if rt == "degradation":
                # Extract the downgraded model from the stored message
                downgrade = entry.get("downgrade", "")
                # Format: "downgrade {from} -> {to}"
                for tier in ("haiku", "sonnet", "opus"):
                    if f"-> {tier}" in downgrade:
                        return tier
                # Fallback: one tier down from a simple keyword match
                if "opus" in downgrade:
                    return "sonnet"
                if "sonnet" in downgrade:
                    return "haiku"
                return "haiku"
            elif rt in ("promotion", "re-enable"):
                # A subsequent positive action clears the downgrade
                return None

        return None

    def get_promotions(self, last_n: int = 10) -> List[ConsequenceAction]:
        """List recent promotions (positive reinforcement tracking)."""
        raw = self._read_all_raw()
        promotions: List[ConsequenceAction] = []
        for entry in raw:
            if entry.get("record_type") == "promotion":
                promotions.append(ConsequenceAction(
                    target=entry.get("target", ""),
                    consequence=Consequence.PROMOTE,
                    reason=entry.get("reason", ""),
                    actions_taken=[],
                    timestamp=entry.get("timestamp", ""),
                ))
        return promotions[-last_n:]

    def get_okr_status(self) -> Dict[str, Any]:
        """Calculate OKR status from consequence history.

        Returns dict with quality, efficiency, and self-improvement OKRs.
        """
        raw = self._read_all_raw()
        performance_entries = [
            e for e in raw if e.get("record_type") == "performance"
        ]

        # --- Agent Quality OKR: target >90% average trust score ---
        scores = [float(e["trust_score"]) for e in performance_entries if "trust_score" in e]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        quality_pct = round(avg_score, 1)
        quality_status = (
            "ON_TRACK" if quality_pct >= 90
            else "AT_RISK" if quality_pct >= 80
            else "BEHIND"
        )

        # --- Efficiency OKR: target -20% MoM cost ---
        costs = [float(e.get("cost_usd", 0)) for e in performance_entries]
        total_cost = sum(costs)
        # Without historical baseline we report the current total
        efficiency_status = "ON_TRACK" if total_cost < 10 else "AT_RISK"

        # --- Self-improvement OKR: 0 recurring errors ---
        action_entries = [
            e for e in raw
            if e.get("record_type") == "action"
            and e.get("consequence") in ("warn", "degrade", "disable")
        ]
        consequence_count = len(action_entries)
        disable_count = sum(1 for e in raw if e.get("record_type") == "disable")
        improvement_status = (
            "ON_TRACK" if disable_count == 0
            else "AT_RISK" if disable_count <= 1
            else "BEHIND"
        )

        return {
            "agent_quality_okr": {
                "target": ">90%",
                "actual": f"{quality_pct}%",
                "status": quality_status,
                "consequence_actions": consequence_count,
            },
            "efficiency_okr": {
                "target": "-20% MoM cost",
                "actual": f"${total_cost:.2f} total",
                "status": efficiency_status,
            },
            "self_improvement_okr": {
                "target": "0 recurring errors",
                "actual": f"{disable_count} disabled",
                "status": improvement_status,
            },
        }

    # -- reporting ---------------------------------------------------------

    def format_consequence_report(self) -> str:
        """Format current consequence state as a human-readable report."""
        raw = self._read_all_raw()

        # Collect recent promotions
        promotions = [e for e in raw if e.get("record_type") == "promotion"]
        warnings_and_degrades = [
            e for e in raw
            if e.get("record_type") in ("action",)
            and e.get("consequence") in ("warn", "degrade")
        ]
        disabled = self.get_disabled_skills()
        degraded = [e for e in raw if e.get("record_type") == "degradation"]
        okr = self.get_okr_status()

        lines = [
            "OKR CONSEQUENCE REPORT",
            "=" * 40,
            "",
            "PROMOTIONS (recent):",
        ]
        if promotions:
            for p in promotions[-5:]:
                lines.append(f"  - {p.get('target', '?')}: {p.get('reason', '')}")
        else:
            lines.append("  (none)")

        lines.append("")
        lines.append("WARNINGS:")
        warn_entries = [
            e for e in raw
            if e.get("record_type") == "performance"
            and float(e.get("trust_score", 100)) < self.thresholds["warn"]
        ]
        if warn_entries:
            # Show last 5 unique targets
            seen = set()
            for w in reversed(warn_entries):
                t = w.get("agent_or_skill", "?")
                if t not in seen:
                    seen.add(t)
                    lines.append(
                        f"  - {t}: score {w.get('trust_score', '?')}% "
                        f"(below {self.thresholds['warn']}%)"
                    )
                if len(seen) >= 5:
                    break
        else:
            lines.append("  (none)")

        lines.append("")
        lines.append("DISABLED:")
        if disabled:
            for d in disabled:
                lines.append(f"  - {d['skill']}: {d['reason']}")
        else:
            lines.append("  (none)")

        lines.append("")
        lines.append("DEGRADED:")
        if degraded:
            for d in degraded[-5:]:
                lines.append(
                    f"  - {d.get('target', '?')}: {d.get('downgrade', '')}"
                )
        else:
            lines.append("  (none)")

        lines.append("")
        lines.append("OKR STATUS:")
        q = okr["agent_quality_okr"]
        e = okr["efficiency_okr"]
        s = okr["self_improvement_okr"]
        lines.append(f"  Quality: {q['actual']} (target {q['target']}) -- {q['status']}")
        lines.append(f"  Efficiency: {e['actual']} (target {e['target']}) -- {e['status']}")
        lines.append(
            f"  Self-improvement: {s['actual']} (target {s['target']}) -- {s['status']}"
        )

        return "\n".join(lines)

    # -- action persistence ------------------------------------------------

    def save_action(self, action: ConsequenceAction) -> None:
        """Persist consequence action to JSONL."""
        self._append_raw(_action_to_dict(action))
