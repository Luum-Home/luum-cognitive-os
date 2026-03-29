"""Escalation Detector -- Self-detect when agents are stuck and should escalate.

Agents currently retry 3 times mechanically then fail. They don't detect loops,
don't measure their own progress, and don't escalate with diagnosis. This module
gives agents the ability to self-detect unproductive patterns and escalate early
with structured diagnosis instead of spinning.

Detectable patterns:
- loop_detected: same file edited 3+ times, or same command run 3+ times
- no_progress: >N tool calls since last PROGRESS marker
- confidence_drop: error rate >50% in recent tool calls
- error_repeat: same error message seen 2+ times
- timeout_risk: >80% of expected tool call budget used

Usage:
    from lib.escalation_detector import EscalationDetector

    detector = EscalationDetector()
    detector.record_tool_call("Edit", success=True)
    detector.record_tool_call("Bash", success=False, error_msg="exit code 1")
    detector.record_progress("step 1/3: created entity")

    signal = detector.check_should_escalate()
    if signal:
        print(detector.format_escalation(signal))

Python 3.9+ compatible. No external dependencies.
Author: luum
"""

import hashlib
import json
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# After this many tool calls without a PROGRESS marker, flag no_progress.
DEFAULT_MAX_CALLS_BEFORE_CHECK = 10

# Same error message seen this many times triggers error_repeat.
DEFAULT_MAX_SAME_ERROR = 2

# Same file edited this many times triggers loop_detected.
SAME_FILE_EDIT_THRESHOLD = 3

# Same command run this many times triggers loop_detected.
SAME_COMMAND_THRESHOLD = 3

# Error rate above this in the last N calls triggers confidence_drop.
CONFIDENCE_DROP_RATE = 0.5

# Number of recent calls to consider for confidence_drop.
CONFIDENCE_WINDOW = 5

# Budget usage above this triggers timeout_risk.
TIMEOUT_RISK_THRESHOLD = 0.8

# Default expected tool call budget per agent.
DEFAULT_TOOL_CALL_BUDGET = 50

# Severity level thresholds (tool calls since last progress).
SUGGEST_CALLS_THRESHOLD = 8
RECOMMEND_CALLS_THRESHOLD = 15
URGENT_CALLS_THRESHOLD = 25


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ToolCallRecord:
    """Record of a single tool call."""

    tool_name: str
    success: bool
    error_msg: str = ""
    target_file: str = ""
    command: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class EscalationSignal:
    """Signal indicating an agent should escalate.

    Attributes:
        type: One of loop_detected, no_progress, confidence_drop,
              error_repeat, timeout_risk.
        severity: One of suggest, recommend, urgent.
        evidence: Human-readable description of what triggered this.
        tool_calls_so_far: Total tool calls recorded at signal time.
        diagnosis: Best-guess root cause (if determinable).
        recommendation: Suggested next action for orchestrator/human.
    """

    type: str
    severity: str
    evidence: str
    tool_calls_so_far: int
    diagnosis: str = ""
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict for JSON serialization."""
        return asdict(self)


# ---------------------------------------------------------------------------
# EscalationDetector
# ---------------------------------------------------------------------------


class EscalationDetector:
    """Analyze agent tool-call patterns and detect when escalation is needed.

    The detector is instantiated once per agent run. Each tool call and
    progress marker is recorded, and ``check_should_escalate`` evaluates
    all accumulated data for escalation signals.
    """

    def __init__(
        self,
        max_tool_calls_before_check: int = DEFAULT_MAX_CALLS_BEFORE_CHECK,
        max_same_error: int = DEFAULT_MAX_SAME_ERROR,
        tool_call_budget: int = DEFAULT_TOOL_CALL_BUDGET,
    ) -> None:
        self.max_tool_calls_before_check = max_tool_calls_before_check
        self.max_same_error = max_same_error
        self.tool_call_budget = tool_call_budget

        self.tool_calls: List[ToolCallRecord] = []
        self.progress_markers: List[str] = []
        self.files_modified: List[str] = []
        self.commands_run: List[str] = []

        # Index of the tool call when last PROGRESS marker was recorded.
        self._last_progress_at: int = 0

        # Track escalation signals emitted.
        self._escalations: List[EscalationSignal] = []

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_tool_call(
        self,
        tool_name: str,
        success: bool,
        error_msg: str = "",
        target_file: str = "",
        command: str = "",
    ) -> None:
        """Record a tool call for pattern analysis.

        Args:
            tool_name: Name of the tool (Edit, Bash, Write, Read, etc.).
            success: Whether the call succeeded.
            error_msg: Error message if the call failed.
            target_file: File path if the tool targeted a specific file.
            command: The command string if tool_name is Bash.
        """
        record = ToolCallRecord(
            tool_name=tool_name,
            success=success,
            error_msg=error_msg,
            target_file=target_file,
            command=command,
        )
        self.tool_calls.append(record)

        if target_file and tool_name in ("Edit", "Write"):
            self.files_modified.append(target_file)

        if command and tool_name == "Bash":
            self.commands_run.append(command)

    def record_progress(self, marker: str) -> None:
        """Record a PROGRESS: marker from agent output.

        This resets the no-progress counter. Agents that report progress
        regularly will not trigger the no_progress escalation.
        """
        self.progress_markers.append(marker)
        self._last_progress_at = len(self.tool_calls)

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def check_should_escalate(self) -> Optional[EscalationSignal]:
        """Analyze accumulated patterns and return an escalation signal.

        Returns the highest-severity signal found, or ``None`` if the
        agent appears to be making normal progress.

        Detection order (highest severity first):
        1. loop_detected -- same file edited 3+ times or same command 3+ times
        2. error_repeat  -- same error message seen max_same_error+ times
        3. confidence_drop -- error rate >50% in last CONFIDENCE_WINDOW calls
        4. no_progress   -- >max_tool_calls_before_check calls since last marker
        5. timeout_risk  -- >80% of tool call budget used
        """
        signals: List[EscalationSignal] = []

        sig = self._check_loop_detected()
        if sig:
            signals.append(sig)

        sig = self._check_error_repeat()
        if sig:
            signals.append(sig)

        sig = self._check_confidence_drop()
        if sig:
            signals.append(sig)

        sig = self._check_no_progress()
        if sig:
            signals.append(sig)

        sig = self._check_timeout_risk()
        if sig:
            signals.append(sig)

        if not signals:
            return None

        # Return highest severity signal.
        severity_order = {"urgent": 0, "recommend": 1, "suggest": 2}
        signals.sort(key=lambda s: severity_order.get(s.severity, 99))
        best = signals[0]
        self._escalations.append(best)
        return best

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_loop_detected(self) -> Optional[EscalationSignal]:
        """Detect repeated edits to the same file or repeated commands."""
        total = len(self.tool_calls)

        # Same file edited N+ times.
        if self.files_modified:
            file_counts = Counter(self.files_modified)
            top_file, count = file_counts.most_common(1)[0]
            if count >= SAME_FILE_EDIT_THRESHOLD:
                return EscalationSignal(
                    type="loop_detected",
                    severity=self._severity_from_count(count, SAME_FILE_EDIT_THRESHOLD),
                    evidence=f"File {top_file} edited {count} times",
                    tool_calls_so_far=total,
                    diagnosis=(
                        f"Repeated edits to {top_file} suggest the fix attempt "
                        "is not converging. The approach may be wrong."
                    ),
                    recommendation=(
                        "Re-launch with a different approach or escalate to human "
                        "for architectural guidance."
                    ),
                )

        # Same command run N+ times.
        if self.commands_run:
            cmd_counts = Counter(self.commands_run)
            top_cmd, count = cmd_counts.most_common(1)[0]
            if count >= SAME_COMMAND_THRESHOLD:
                short_cmd = top_cmd[:120]
                return EscalationSignal(
                    type="loop_detected",
                    severity=self._severity_from_count(count, SAME_COMMAND_THRESHOLD),
                    evidence=f"Command '{short_cmd}' run {count} times",
                    tool_calls_so_far=total,
                    diagnosis=(
                        "Repeated execution of the same command without success "
                        "indicates the error is not being addressed between retries."
                    ),
                    recommendation=(
                        "Analyze the error output for root cause before retrying. "
                        "Consider a fundamentally different approach."
                    ),
                )

        return None

    def _check_error_repeat(self) -> Optional[EscalationSignal]:
        """Detect the same error message appearing multiple times."""
        errors = [tc.error_msg for tc in self.tool_calls if tc.error_msg]
        if not errors:
            return None

        # Fingerprint errors by first 200 chars to catch near-duplicates.
        fingerprints: List[str] = []
        for msg in errors:
            fp = hashlib.md5(msg[:200].encode()).hexdigest()
            fingerprints.append(fp)

        fp_counts = Counter(fingerprints)
        top_fp, count = fp_counts.most_common(1)[0]
        if count >= self.max_same_error:
            # Find the original error message for evidence.
            for i, fp in enumerate(fingerprints):
                if fp == top_fp:
                    original_msg = errors[i][:200]
                    break
            else:
                original_msg = "(unknown)"

            return EscalationSignal(
                type="error_repeat",
                severity="recommend" if count >= 3 else "suggest",
                evidence=f"Same error seen {count} times: {original_msg}",
                tool_calls_so_far=len(self.tool_calls),
                diagnosis=(
                    "The same error is recurring without being resolved. "
                    "The current fix strategy is not addressing the root cause."
                ),
                recommendation=(
                    "Escalate with the error details. A fresh perspective "
                    "or different approach is needed."
                ),
            )

        return None

    def _check_confidence_drop(self) -> Optional[EscalationSignal]:
        """Detect high error rate in recent tool calls."""
        if len(self.tool_calls) < CONFIDENCE_WINDOW:
            return None

        recent = self.tool_calls[-CONFIDENCE_WINDOW:]
        failures = sum(1 for tc in recent if not tc.success)
        error_rate = failures / len(recent)

        if error_rate > CONFIDENCE_DROP_RATE:
            return EscalationSignal(
                type="confidence_drop",
                severity="recommend" if error_rate > 0.8 else "suggest",
                evidence=(
                    f"Error rate {error_rate:.0%} in last {CONFIDENCE_WINDOW} "
                    f"tool calls ({failures}/{len(recent)} failed)"
                ),
                tool_calls_so_far=len(self.tool_calls),
                diagnosis=(
                    "High failure rate indicates the agent is struggling "
                    "with the current approach."
                ),
                recommendation=(
                    "Consider re-launching with a different model or approach. "
                    "The task may require capabilities the current agent lacks."
                ),
            )

        return None

    def _check_no_progress(self) -> Optional[EscalationSignal]:
        """Detect extended periods without progress markers."""
        calls_since_progress = len(self.tool_calls) - self._last_progress_at

        if calls_since_progress > self.max_tool_calls_before_check:
            severity = "suggest"
            if calls_since_progress > RECOMMEND_CALLS_THRESHOLD:
                severity = "recommend"
            if calls_since_progress > URGENT_CALLS_THRESHOLD:
                severity = "urgent"

            return EscalationSignal(
                type="no_progress",
                severity=severity,
                evidence=(
                    f"{calls_since_progress} tool calls since last PROGRESS marker"
                ),
                tool_calls_so_far=len(self.tool_calls),
                diagnosis=(
                    "The agent has been working without reporting progress. "
                    "This may indicate the agent is stuck in an unproductive loop."
                ),
                recommendation=(
                    "Check agent output for signs of progress. If none, "
                    "re-launch with clearer instructions or escalate."
                ),
            )

        return None

    def _check_timeout_risk(self) -> Optional[EscalationSignal]:
        """Detect when a large portion of the tool call budget is consumed."""
        if self.tool_call_budget <= 0:
            return None

        usage = len(self.tool_calls) / self.tool_call_budget

        if usage > TIMEOUT_RISK_THRESHOLD:
            severity = "suggest"
            if usage > 0.9:
                severity = "recommend"
            if usage > 0.95:
                severity = "urgent"

            return EscalationSignal(
                type="timeout_risk",
                severity=severity,
                evidence=(
                    f"Used {len(self.tool_calls)}/{self.tool_call_budget} "
                    f"tool calls ({usage:.0%} of budget)"
                ),
                tool_calls_so_far=len(self.tool_calls),
                diagnosis=(
                    "The agent is running out of tool call budget. "
                    "Remaining work may not fit in the available budget."
                ),
                recommendation=(
                    "Save progress to Engram, report partial results, "
                    "and let the orchestrator decide whether to continue."
                ),
            )

        return None

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_escalation(self, signal: EscalationSignal) -> str:
        """Format a structured escalation output.

        The output uses the ``ESCALATION:`` marker that the orchestrator's
        PostToolUse hooks can detect and act on.
        """
        lines = [
            "ESCALATION:",
            f"  Type: {signal.type}",
            f"  Severity: {signal.severity}",
            f"  Evidence: {signal.evidence}",
            f"  Tool calls: {signal.tool_calls_so_far}",
        ]
        if signal.diagnosis:
            lines.append(f"  Diagnosis: {signal.diagnosis}")
        if signal.recommendation:
            lines.append(f"  Recommendation: {signal.recommendation}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_escalation_metrics(self) -> Dict[str, Any]:
        """Return metrics for KPI tracking.

        Returns a dict with:
            escalation_count: number of escalation signals emitted.
            tool_calls_total: total tool calls recorded.
            progress_markers: number of PROGRESS markers recorded.
            error_rate: overall error rate across all tool calls.
            error_count: number of failed tool calls.
            files_modified_unique: number of unique files modified.
            stuck_duration: tool calls since last progress marker.
            escalation_types: counter of escalation signal types.
        """
        total = len(self.tool_calls)
        failures = sum(1 for tc in self.tool_calls if not tc.success)
        error_rate = failures / total if total > 0 else 0.0
        calls_since_progress = total - self._last_progress_at

        type_counts: Dict[str, int] = {}
        for sig in self._escalations:
            type_counts[sig.type] = type_counts.get(sig.type, 0) + 1

        return {
            "escalation_count": len(self._escalations),
            "tool_calls_total": total,
            "progress_markers": len(self.progress_markers),
            "error_rate": round(error_rate, 3),
            "error_count": failures,
            "files_modified_unique": len(set(self.files_modified)),
            "stuck_duration": calls_since_progress,
            "escalation_types": type_counts,
        }

    def save_metrics(self, metrics_dir: str) -> None:
        """Persist escalation metrics to a JSONL file.

        Appends one JSON object per call to ``escalation-events.jsonl``
        inside *metrics_dir*.
        """
        metrics = self.get_escalation_metrics()
        metrics["timestamp"] = datetime.now(timezone.utc).isoformat()

        path = Path(metrics_dir) / "escalation-events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(metrics) + "\n")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _severity_from_count(count: int, threshold: int) -> str:
        """Derive severity from how far count exceeds threshold."""
        ratio = count / threshold
        if ratio >= 3:
            return "urgent"
        if ratio >= 2:
            return "recommend"
        return "suggest"
