"""
Learning Pipeline — Connects the 5 island systems into a unified feedback loop.

The pipeline orchestrates:
1. prompt_classifier  → classifies user intent
2. skill_archive      → records skill executions with trust scores
3. consequence_engine → evaluates streaks (promote/degrade/disable)
4. error_classifier   → classifies errors by type and service
5. Triggers skill review when thresholds are met

Adopted pattern: unified pass that routes each completion through all
relevant subsystems, surfaces actionable signals, and returns structured
context for agent prompt injection.

Python 3.9+ compatible. No external dependencies beyond stdlib.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from lib.skill_archive import SkillArchiveManager, SkillSnapshot
from lib.consequence_engine import (
    ConsequenceEngine,
    ConsequenceAction,
    Consequence,
    PerformanceRecord,
)
from lib.error_classifier import classify_error, ErrorCategory
from lib.prompt_classifier import classify_prompt, ClassificationResult, PromptCategory


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class LearningTrigger:
    """An actionable signal that warrants human or automated attention."""

    trigger_type: str   # "error_pattern" | "skill_degradation" | "consequence"
    target: str         # skill name, service name, or agent name
    severity: str       # "info" | "warn" | "critical"
    message: str
    detail: Dict = field(default_factory=dict)


@dataclass
class ErrorCorrelation:
    """Correlates an error with a recently-run skill."""

    error_type: str
    service: str
    message: str
    category: ErrorCategory
    skill_name: Optional[str]
    timestamp: str


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

_DEFAULT_CORRELATIONS_PATH = ".cognitive-os/metrics/error-skill-correlations.jsonl"
_DEFAULT_ERRORS_PATH = ".cognitive-os/metrics/error-learning.jsonl"

_SKILL_CONTENT_PLACEHOLDER = "skill-content-placeholder"  # used when real content unavailable


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_jsonl(path: str) -> List[Dict]:
    p = Path(path)
    if not p.exists():
        return []
    entries = []
    with open(p, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _append_jsonl(path: str, entry: Dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class LearningPipeline:
    """Unified bridge connecting the 5 learning subsystems.

    All subsystem instances are injected, allowing tests to pass mock paths.
    """

    def __init__(
        self,
        skill_archive: Optional[SkillArchiveManager] = None,
        consequence_engine: Optional[ConsequenceEngine] = None,
        correlations_path: str = _DEFAULT_CORRELATIONS_PATH,
        errors_path: str = _DEFAULT_ERRORS_PATH,
    ) -> None:
        self._archive = skill_archive or SkillArchiveManager()
        self._engine = consequence_engine or ConsequenceEngine()
        self._correlations_path = correlations_path
        self._errors_path = errors_path
        # Tracks the last skill that ran in this session (for error correlation)
        self._last_skill: Optional[str] = None

    # ------------------------------------------------------------------
    # record_agent_completion
    # ------------------------------------------------------------------

    def record_agent_completion(
        self,
        task_id: str,
        success: bool,
        trust_score: float,
        skill_name: str,
        tokens_used: int = 0,
    ) -> ConsequenceAction:
        """Record a completed agent task, feeding both archive and consequence engine.

        Returns the ConsequenceAction (PROMOTE/MAINTAIN/WARN/DEGRADE/DISABLE).
        """
        self._last_skill = skill_name

        # 1. skill_archive: record the execution snapshot
        self._archive.record_execution(
            skill_name=skill_name,
            skill_content=_SKILL_CONTENT_PLACEHOLDER,
            trust_score=trust_score,
            success=success,
            task=task_id,
            tokens=tokens_used,
        )

        # 2. consequence_engine: evaluate performance record
        record = PerformanceRecord(
            agent_or_skill=skill_name,
            task_type=task_id,
            trust_score=trust_score,
            success=success,
            cost_usd=0.0,
            tokens_used=tokens_used,
            retries=0,
            timestamp=_now_iso(),
        )
        action = self._engine.evaluate(record)
        return action

    # ------------------------------------------------------------------
    # record_error
    # ------------------------------------------------------------------

    def record_error(
        self,
        error_type: str,
        service: str,
        message: str,
        context: str = "",
    ) -> ErrorCorrelation:
        """Classify an error and correlate it with the last-run skill.

        Persists the correlation so check_learning_triggers() can surface it.
        Returns the ErrorCorrelation.
        """
        combined_text = f"{error_type} {message} {context}"
        category = classify_error(combined_text)

        correlation = ErrorCorrelation(
            error_type=error_type,
            service=service,
            message=message,
            category=category,
            skill_name=self._last_skill,
            timestamp=_now_iso(),
        )

        _append_jsonl(
            self._correlations_path,
            {
                "error_type": error_type,
                "service": service,
                "message": message,
                "category": category.value,
                "skill_name": self._last_skill,
                "timestamp": correlation.timestamp,
            },
        )
        return correlation

    # ------------------------------------------------------------------
    # record_user_feedback
    # ------------------------------------------------------------------

    def record_user_feedback(
        self,
        message: str,
        signal_type: str = "auto",
    ) -> ClassificationResult:
        """Classify user feedback and associate it with the last-run skill.

        Returns the ClassificationResult from prompt_classifier.
        The signal_type parameter is accepted for API compatibility but the
        actual category is always determined by the classifier.
        """
        result = classify_prompt(message)

        if result.category == PromptCategory.FEEDBACK and self._last_skill:
            _append_jsonl(
                self._correlations_path,
                {
                    "feedback": message[:200],
                    "category": result.category.value,
                    "should_capture": result.should_capture,
                    "confidence": result.confidence,
                    "skill_name": self._last_skill,
                    "timestamp": _now_iso(),
                },
            )
        return result

    # ------------------------------------------------------------------
    # check_learning_triggers
    # ------------------------------------------------------------------

    def check_learning_triggers(self) -> List[LearningTrigger]:
        """Inspect all subsystems for actionable signals.

        Checks:
        - Error patterns: 3+ same error_type in 24h → warn trigger
        - Skill degradation: declining trust trend → review trigger
        - Consequence actions: any DEGRADE or DISABLE → critical trigger

        Returns a list of LearningTrigger objects (may be empty).
        """
        triggers: List[LearningTrigger] = []

        # 1. Error pattern check (24h window)
        triggers.extend(self._check_error_patterns())

        # 2. Skill degradation from archive
        triggers.extend(self._check_skill_degradation())

        # 3. Consequence actions: disabled or degraded skills
        triggers.extend(self._check_consequence_state())

        return triggers

    def _check_error_patterns(self) -> List[LearningTrigger]:
        triggers = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        entries = _read_jsonl(self._correlations_path)

        # Count errors per type within 24h
        counts: Dict[Tuple[str, str], int] = {}
        for entry in entries:
            if "error_type" not in entry:
                continue
            try:
                ts = datetime.fromisoformat(entry["timestamp"])
                # Handle both aware and naive timestamps
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except (ValueError, KeyError):
                continue
            if ts >= cutoff:
                key = (entry["error_type"], entry.get("service", "unknown"))
                counts[key] = counts.get(key, 0) + 1

        for (error_type, service), count in counts.items():
            if count >= 3:
                triggers.append(
                    LearningTrigger(
                        trigger_type="error_pattern",
                        target=service,
                        severity="warn",
                        message=(
                            f"{service} has {count} {error_type} errors in the last 24h"
                        ),
                        detail={"error_type": error_type, "count": count},
                    )
                )
        return triggers

    def _check_skill_degradation(self) -> List[LearningTrigger]:
        triggers = []
        underperforming = self._archive.get_underperforming_skills(threshold=0.6)
        for skill in underperforming:
            trend = self._archive.get_skill_trend(skill)
            triggers.append(
                LearningTrigger(
                    trigger_type="skill_degradation",
                    target=skill,
                    severity="warn",
                    message=(
                        f"Skill '{skill}' is underperforming "
                        f"(trend: {trend['trend']}, last_5_avg: {trend['last_5_avg']})"
                    ),
                    detail=trend,
                )
            )
        return triggers

    def _check_consequence_state(self) -> List[LearningTrigger]:
        triggers = []
        disabled = self._engine.get_disabled_skills()
        for d in disabled:
            triggers.append(
                LearningTrigger(
                    trigger_type="consequence",
                    target=d["skill"],
                    severity="critical",
                    message=f"Skill '{d['skill']}' is DISABLED: {d['reason']}",
                    detail=d,
                )
            )
        return triggers

    # ------------------------------------------------------------------
    # get_learning_context
    # ------------------------------------------------------------------

    def get_learning_context(self, task_description: str) -> str:
        """Aggregate relevant context from all 5 systems for prompt injection.

        Returns a formatted string suitable for injection into agent prompts.
        """
        lines = ["LEARNING CONTEXT:"]

        # Recent errors from error-learning.jsonl
        error_entries = _read_jsonl(self._errors_path)
        if error_entries:
            recent = error_entries[-5:]
            lines.append("\nRecent errors:")
            for e in recent:
                svc = e.get("service", "unknown")
                etype = e.get("type", e.get("error_type", "unknown"))
                lines.append(f"  - [{etype}] {svc}: {e.get('message', '')[:80]}")

        # Skill execution history (top underperforming)
        underperforming = self._archive.get_underperforming_skills(threshold=0.6)
        if underperforming:
            lines.append("\nUnderperforming skills (success rate < 60%):")
            for skill in underperforming[:3]:
                archive = self._archive.get_archive(skill)
                lines.append(
                    f"  - {skill}: {archive.success_rate:.0%} success "
                    f"({archive.total_uses} uses)"
                )

        # Active triggers
        triggers = self.check_learning_triggers()
        if triggers:
            lines.append("\nActive warnings:")
            for t in triggers[:5]:
                lines.append(f"  - [{t.severity.upper()}] {t.message}")

        # Disabled skills
        disabled = self._engine.get_disabled_skills()
        if disabled:
            lines.append("\nDisabled skills (require /optimize-skill):")
            for d in disabled[:3]:
                lines.append(f"  - {d['skill']}: {d['reason'][:60]}")

        if len(lines) == 1:
            return "LEARNING CONTEXT: No signals — system healthy."

        return "\n".join(lines)
