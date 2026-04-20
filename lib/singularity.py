#!/usr/bin/env python3
# SCOPE: os-only
# /// script
# requires-python = ">=3.9"
# ///
"""Codebase Singularity Controller — the central MAPE-K autonomous loop.

Monitors the codebase for actionable events (failing tests, stale docs,
KPI degradation, GitHub issues, skill failures, circuit breaker states),
classifies them, plans execution strategy, launches the right pipeline
via ClaudeExecutor, and feeds outcomes back into persistent knowledge.

Usage:
    # Single pass (for cron)
    python lib/singularity.py run

    # Continuous daemon
    python lib/singularity.py daemon --interval 300

    # Preview what would run
    python lib/singularity.py dry-run

    # Show active pipelines
    python lib/singularity.py status

Python 3.9+ compatible.
"""

import argparse
import hashlib
import json
import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Resolve lib/ directory for sibling imports
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from claude_executor import ClaudeExecutor, ClaudeResult
from notifications import send_raw
from metric_event import MetricEvent, append_event as _me_append_event

logger = logging.getLogger("singularity")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
_METRICS_DIR = os.path.join(_PROJECT_ROOT, "metrics")
_COGNITIVE_OS_METRICS = os.path.join(_PROJECT_ROOT, ".cognitive-os", "metrics")
_SINGULARITY_LOG = os.path.join(_COGNITIVE_OS_METRICS, "singularity-events.jsonl")
_COOLDOWN_SECONDS = 3600  # 1 hour per event type
_MAX_PARALLEL = 3
_ERROR_PATTERN_THRESHOLD = 3  # 3+ same-type errors in 24h
_SKILL_FAILURE_THRESHOLD = 3  # 3 consecutive failures

# Budget guard: read from cognitive-os.yaml defaults
_DEFAULT_DAILY_BUDGET_USD = 10.0


class EventType(str, Enum):
    """Classification of detected events."""
    NEW_FEATURE = "new_feature"
    BUG_REPORT = "bug_report"
    TEST_FAILURE = "test_failure"
    STALE_DOCS = "stale_docs"
    ERROR_PATTERN = "error_pattern"
    KPI_DEGRADATION = "kpi_degradation"
    COVERAGE_DROP = "coverage_drop"
    SKILL_FAILURE = "skill_failure"
    CIRCUIT_OPEN = "circuit_open"


# Priority order: lower index = higher priority
_PRIORITY_ORDER: List[EventType] = [
    EventType.CIRCUIT_OPEN,
    EventType.TEST_FAILURE,
    EventType.BUG_REPORT,
    EventType.ERROR_PATTERN,
    EventType.KPI_DEGRADATION,
    EventType.COVERAGE_DROP,
    EventType.NEW_FEATURE,
    EventType.SKILL_FAILURE,
    EventType.STALE_DOCS,
]

# Pipeline routing: event_type -> (pipeline_skill_or_prompt, model)
_PIPELINE_ROUTING: Dict[EventType, Tuple[str, str]] = {
    EventType.NEW_FEATURE: ("issue-to-pr", "sonnet"),
    EventType.BUG_REPORT: ("issue-to-pr", "sonnet"),
    EventType.TEST_FAILURE: ("auto-repair", "sonnet"),
    EventType.STALE_DOCS: ("doc-sync", "haiku"),
    EventType.ERROR_PATTERN: ("self-improve", "sonnet"),
    EventType.KPI_DEGRADATION: ("metrics-calibrator", "sonnet"),
    EventType.COVERAGE_DROP: ("coverage-enforcement", "sonnet"),
    EventType.SKILL_FAILURE: ("skill-creator", "sonnet"),
    EventType.CIRCUIT_OPEN: ("", ""),  # Never auto-acted on
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SingularityEvent:
    """A detected event that may need action."""
    event_type: EventType
    source: str  # e.g. "error-learning.jsonl", "gh-issues", "stale-docs.jsonl"
    description: str
    dedup_key: str  # hash for deduplication
    details: Dict[str, Any] = field(default_factory=dict)
    priority: int = 99  # lower = higher priority

    def __post_init__(self) -> None:
        try:
            self.priority = _PRIORITY_ORDER.index(self.event_type)
        except ValueError:
            self.priority = 99


@dataclass
class PipelineExecution:
    """Tracks an active or completed pipeline execution."""
    event: SingularityEvent
    pipeline: str
    model: str
    started_at: float
    finished_at: Optional[float] = None
    success: Optional[bool] = None
    result_text: str = ""
    cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Safe JSONL helpers
# ---------------------------------------------------------------------------

def _read_jsonl(path: str, max_lines: int = 5000) -> List[Dict[str, Any]]:
    """Read a JSONL file safely, returning at most max_lines entries.

    MetricEvent-wrapped rows are transparently unwrapped so consumers receive
    the same flat dict shape as legacy rows.
    """
    results: List[Dict[str, Any]] = []
    if not os.path.isfile(path):
        return results
    try:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                # Unwrap MetricEvent rows back to flat shape
                if "schema_version" in row and "event_type" in row and "payload" in row:
                    flat = dict(row["payload"])
                    flat.setdefault("timestamp", row.get("timestamp", ""))
                    # Restore phase/action from event_type for callers that use them
                    event_type = row.get("event_type", "")
                    if event_type.startswith("singularity.") and "phase" not in flat:
                        parts = event_type[len("singularity."):].split(".", 1)
                        flat.setdefault("phase", parts[0])
                        if len(parts) > 1:
                            flat.setdefault("action", parts[1])
                    results.append(flat)
                else:
                    results.append(row)
    except (OSError, IOError) as e:
        logger.warning("Failed to read %s: %s", path, e)
    return results


def _append_jsonl(path: str, entry: Dict[str, Any]) -> None:
    """Append a single JSON entry as a MetricEvent to a JSONL file."""
    try:
        entry = dict(entry)  # defensive copy
        # Derive event_type from 'phase' or 'action' keys; fall back to generic
        phase = entry.get("phase", "")
        action = entry.get("action", "")
        if phase and action:
            event_type = f"singularity.{phase}.{action}"
        elif phase:
            event_type = f"singularity.{phase}"
        elif action:
            event_type = f"singularity.{action}"
        else:
            event_type = "singularity.event"
        timestamp = entry.pop("timestamp", "")
        event = MetricEvent(
            source="singularity",
            event_type=event_type,
            payload=entry,
            timestamp=timestamp,
        )
        _me_append_event(path, event)
    except (OSError, IOError) as e:
        logger.warning("Failed to write to %s: %s", path, e)


def _dedup_key(event_type: str, source: str, detail: str) -> str:
    """Generate a deduplication key from event attributes."""
    raw = "%s:%s:%s" % (event_type, source, detail)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# MONITOR phase — event detection
# ---------------------------------------------------------------------------

def _monitor_github_issues(project_root: str) -> List[SingularityEvent]:
    """Detect GitHub issues with [sdd-auto] label."""
    events: List[SingularityEvent] = []
    try:
        result = subprocess.run(
            ["gh", "issue", "list", "--label", "sdd-auto", "--json",
             "number,title,labels,body", "--limit", "20"],
            capture_output=True, text=True, timeout=30,
            cwd=project_root,
        )
        if result.returncode != 0:
            logger.debug("gh issue list failed: %s", result.stderr[:200])
            return events

        issues = json.loads(result.stdout) if result.stdout.strip() else []
        for issue in issues:
            number = issue.get("number", 0)
            title = issue.get("title", "")
            labels = [l.get("name", "") for l in issue.get("labels", [])]
            body = issue.get("body", "")[:500]

            # Classify: bug if 'bug' label, else new_feature
            is_bug = "bug" in labels
            etype = EventType.BUG_REPORT if is_bug else EventType.NEW_FEATURE

            events.append(SingularityEvent(
                event_type=etype,
                source="github-issues",
                description="Issue #%d: %s" % (number, title),
                dedup_key=_dedup_key(etype.value, "gh", str(number)),
                details={"issue_number": number, "title": title,
                         "labels": labels, "body": body},
            ))
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug("GitHub issue detection failed: %s", e)

    return events


def _monitor_error_patterns(project_root: str) -> List[SingularityEvent]:
    """Detect 3+ same-type errors in 24h from error-learning.jsonl."""
    events: List[SingularityEvent] = []

    # Try both possible locations
    for metrics_dir in [_METRICS_DIR, _COGNITIVE_OS_METRICS]:
        path = os.path.join(metrics_dir, "error-learning.jsonl")
        entries = _read_jsonl(path)
        if not entries:
            continue

        cutoff = time.time() - 86400  # 24 hours ago
        recent = [e for e in entries if e.get("timestamp_epoch", 0) > cutoff]

        # Group by type + service
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for entry in recent:
            key = "%s:%s" % (entry.get("type", "unknown"),
                             entry.get("service", "unknown"))
            groups.setdefault(key, []).append(entry)

        for key, group in groups.items():
            if len(group) >= _ERROR_PATTERN_THRESHOLD:
                error_type, service = key.split(":", 1)
                events.append(SingularityEvent(
                    event_type=EventType.ERROR_PATTERN,
                    source="error-learning.jsonl",
                    description="%d %s errors in %s (24h)" % (
                        len(group), error_type, service),
                    dedup_key=_dedup_key("error_pattern", key,
                                        str(len(group))),
                    details={"error_type": error_type, "service": service,
                             "count": len(group)},
                ))

        # Also check for test failures specifically
        test_failures = [e for e in recent
                         if e.get("type") == "TEST_FAILURE"]
        if len(test_failures) >= _ERROR_PATTERN_THRESHOLD:
            events.append(SingularityEvent(
                event_type=EventType.TEST_FAILURE,
                source="error-learning.jsonl",
                description="%d test failures in 24h" % len(test_failures),
                dedup_key=_dedup_key("test_failure", "error-learning",
                                    str(len(test_failures))),
                details={"count": len(test_failures)},
            ))

    return events


def _monitor_stale_docs(project_root: str) -> List[SingularityEvent]:
    """Detect stale documentation from stale-docs.jsonl."""
    events: List[SingularityEvent] = []

    for metrics_dir in [_METRICS_DIR, _COGNITIVE_OS_METRICS]:
        path = os.path.join(metrics_dir, "stale-docs.jsonl")
        entries = _read_jsonl(path)
        if not entries:
            continue

        if len(entries) > 0:
            events.append(SingularityEvent(
                event_type=EventType.STALE_DOCS,
                source="stale-docs.jsonl",
                description="%d stale documentation entries" % len(entries),
                dedup_key=_dedup_key("stale_docs", "stale-docs",
                                    str(len(entries))),
                details={"count": len(entries),
                         "files": [e.get("file", "") for e in entries[:10]]},
            ))

    return events


def _monitor_kpi_degradation(project_root: str) -> List[SingularityEvent]:
    """Detect KPI degradation by comparing last 2 snapshots."""
    events: List[SingularityEvent] = []

    for metrics_dir in [_METRICS_DIR, _COGNITIVE_OS_METRICS]:
        path = os.path.join(metrics_dir, "kpi-history.jsonl")
        entries = _read_jsonl(path)
        if len(entries) < 2:
            continue

        last = entries[-1]
        prev = entries[-2]

        # Compare composite scores if available
        last_score = last.get("composite_score", last.get("quality_score"))
        prev_score = prev.get("composite_score", prev.get("quality_score"))

        if last_score is not None and prev_score is not None:
            if isinstance(last_score, (int, float)) and isinstance(prev_score, (int, float)):
                if last_score < prev_score * 0.9:  # 10%+ drop
                    events.append(SingularityEvent(
                        event_type=EventType.KPI_DEGRADATION,
                        source="kpi-history.jsonl",
                        description="KPI score dropped from %.1f to %.1f" % (
                            prev_score, last_score),
                        dedup_key=_dedup_key("kpi_degradation", "kpi",
                                            "%.1f" % last_score),
                        details={"previous": prev_score,
                                 "current": last_score,
                                 "drop_pct": round(
                                     (1 - last_score / prev_score) * 100, 1)},
                    ))

    return events


def _monitor_skill_failures(project_root: str) -> List[SingularityEvent]:
    """Detect 3+ consecutive skill failures from skill-metrics.jsonl."""
    events: List[SingularityEvent] = []

    for metrics_dir in [_METRICS_DIR, _COGNITIVE_OS_METRICS]:
        path = os.path.join(metrics_dir, "skill-metrics.jsonl")
        entries = _read_jsonl(path)
        if not entries:
            continue

        # Group by skill name, check last N entries
        by_skill: Dict[str, List[Dict[str, Any]]] = {}
        for entry in entries:
            skill = entry.get("skill", entry.get("name", "unknown"))
            by_skill.setdefault(skill, []).append(entry)

        for skill, runs in by_skill.items():
            # Check last N runs for consecutive failures
            recent = runs[-_SKILL_FAILURE_THRESHOLD:]
            if len(recent) >= _SKILL_FAILURE_THRESHOLD:
                all_failed = all(
                    not r.get("success", True) for r in recent
                )
                if all_failed:
                    events.append(SingularityEvent(
                        event_type=EventType.SKILL_FAILURE,
                        source="skill-metrics.jsonl",
                        description="Skill '%s' failed %d consecutive times" % (
                            skill, len(recent)),
                        dedup_key=_dedup_key("skill_failure", skill,
                                            str(len(recent))),
                        details={"skill": skill,
                                 "consecutive_failures": len(recent)},
                    ))

    return events


def _monitor_circuit_breakers(project_root: str) -> List[SingularityEvent]:
    """Detect OPEN circuit breaker states."""
    events: List[SingularityEvent] = []

    cb_dir = os.path.join(_COGNITIVE_OS_METRICS, "circuit-breaker")
    if not os.path.isdir(cb_dir):
        # Also check metrics/ directly
        cb_dir = os.path.join(_METRICS_DIR, "circuit-breaker")
    if not os.path.isdir(cb_dir):
        return events

    try:
        for filename in os.listdir(cb_dir):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(cb_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    state = json.load(f)
                if state.get("state") == "OPEN":
                    service = state.get("service", filename.replace(".json", ""))
                    error_type = state.get("error_type", "unknown")
                    events.append(SingularityEvent(
                        event_type=EventType.CIRCUIT_OPEN,
                        source="circuit-breaker",
                        description="Circuit breaker OPEN: %s/%s" % (
                            service, error_type),
                        dedup_key=_dedup_key("circuit_open", service,
                                            error_type),
                        details={"service": service, "error_type": error_type,
                                 "state": state},
                    ))
            except (json.JSONDecodeError, OSError):
                continue
    except OSError:
        pass

    return events


def _monitor_coverage(project_root: str) -> List[SingularityEvent]:
    """Detect coverage drops from coverage reports."""
    events: List[SingularityEvent] = []

    for metrics_dir in [_METRICS_DIR, _COGNITIVE_OS_METRICS]:
        path = os.path.join(metrics_dir, "coverage-history.jsonl")
        entries = _read_jsonl(path)
        if len(entries) < 2:
            continue

        last = entries[-1]
        prev = entries[-2]

        # Support both flat schema (legacy) and MetricEvent-wrapped schema
        # (payload.coverage_pct) written by pre-commit-gate.sh.
        def _extract_coverage(entry: Dict[str, Any]) -> Any:
            flat = entry.get("coverage_pct", entry.get("coverage"))
            if flat is not None:
                return flat
            return entry.get("payload", {}).get("coverage_pct")

        last_cov = _extract_coverage(last)
        prev_cov = _extract_coverage(prev)

        if (last_cov is not None and prev_cov is not None
                and isinstance(last_cov, (int, float))
                and isinstance(prev_cov, (int, float))):
            if last_cov < prev_cov - 5:  # 5+ percentage point drop
                events.append(SingularityEvent(
                    event_type=EventType.COVERAGE_DROP,
                    source="coverage-history.jsonl",
                    description="Coverage dropped from %.1f%% to %.1f%%" % (
                        prev_cov, last_cov),
                    dedup_key=_dedup_key("coverage_drop", "coverage",
                                        "%.1f" % last_cov),
                    details={"previous": prev_cov, "current": last_cov},
                ))

    return events


def monitor_all(project_root: str) -> List[SingularityEvent]:
    """Run all monitors and return detected events sorted by priority."""
    all_events: List[SingularityEvent] = []

    monitors = [
        ("github-issues", _monitor_github_issues),
        ("error-patterns", _monitor_error_patterns),
        ("stale-docs", _monitor_stale_docs),
        ("kpi-degradation", _monitor_kpi_degradation),
        ("skill-failures", _monitor_skill_failures),
        ("circuit-breakers", _monitor_circuit_breakers),
        ("coverage", _monitor_coverage),
    ]

    for name, monitor_fn in monitors:
        try:
            events = monitor_fn(project_root)
            all_events.extend(events)
            if events:
                logger.info("Monitor '%s' detected %d events", name, len(events))
        except Exception as e:
            logger.warning("Monitor '%s' failed: %s", name, e)

    # Sort by priority (lower = higher priority)
    all_events.sort(key=lambda e: e.priority)
    return all_events


# ---------------------------------------------------------------------------
# ANALYZE phase — classify and filter
# ---------------------------------------------------------------------------

def analyze(
    events: List[SingularityEvent],
    processed_keys: Set[str],
    cooldowns: Dict[str, float],
) -> List[SingularityEvent]:
    """Filter events: deduplicate, apply cooldowns, remove already-processed."""
    now = time.time()
    actionable: List[SingularityEvent] = []

    for event in events:
        # Skip already processed
        if event.dedup_key in processed_keys:
            logger.debug("Skipping already-processed event: %s",
                         event.description[:80])
            continue

        # Skip if in cooldown
        last_time = cooldowns.get(event.event_type.value, 0.0)
        if now - last_time < _COOLDOWN_SECONDS:
            remaining = _COOLDOWN_SECONDS - (now - last_time)
            logger.debug("Skipping event in cooldown (%ds remaining): %s",
                         int(remaining), event.description[:80])
            continue

        # Circuit breaker events are ALWAYS included (but never auto-acted on)
        actionable.append(event)

    return actionable


# ---------------------------------------------------------------------------
# PLAN phase — determine execution strategy
# ---------------------------------------------------------------------------

def _get_daily_spend(project_root: str) -> float:
    """Read today's total spend from cost-events.jsonl."""
    total = 0.0
    today = time.strftime("%Y-%m-%d")

    for metrics_dir in [_METRICS_DIR, _COGNITIVE_OS_METRICS]:
        path = os.path.join(metrics_dir, "cost-events.jsonl")
        entries = _read_jsonl(path)
        for entry in entries:
            ts = entry.get("timestamp", "")
            if ts.startswith(today):
                total += entry.get("estimated_cost_usd", 0.0)

    return total


def _read_phase(project_root: str) -> str:
    """Read the current project phase from cognitive-os.yaml."""
    config_path = os.path.join(project_root, "cognitive-os.yaml")
    if not os.path.isfile(config_path):
        return "reconstruction"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Simple YAML parsing for phase field (avoid pyyaml dependency)
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("phase:"):
                return stripped.split(":", 1)[1].strip().strip('"').strip("'")
    except (OSError, IOError):
        pass
    return "reconstruction"


def plan(
    events: List[SingularityEvent],
    project_root: str,
    active_count: int,
    daily_budget_usd: float = _DEFAULT_DAILY_BUDGET_USD,
) -> List[SingularityEvent]:
    """Determine which events to execute based on constraints.

    Returns the events that should be executed in this cycle.
    """
    daily_spend = _get_daily_spend(project_root)
    phase = _read_phase(project_root)

    planned: List[SingularityEvent] = []

    for event in events:
        # Circuit breaker events are logged but NEVER auto-executed
        if event.event_type == EventType.CIRCUIT_OPEN:
            logger.warning(
                "CIRCUIT OPEN detected — requires human intervention: %s",
                event.description,
            )
            # Log it but don't add to planned
            _append_jsonl(_SINGULARITY_LOG, {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "phase": "plan",
                "action": "escalate_human",
                "event_type": event.event_type.value,
                "description": event.description,
                "reason": "Circuit breaker OPEN — requires human intervention",
            })
            send_raw(
                "[SINGULARITY] Circuit breaker OPEN: %s — human intervention required"
                % event.description
            )
            continue

        # Budget check
        if daily_spend >= daily_budget_usd:
            logger.warning(
                "Daily budget exhausted ($%.2f/$%.2f). Skipping: %s",
                daily_spend, daily_budget_usd, event.description[:60],
            )
            _append_jsonl(_SINGULARITY_LOG, {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "phase": "plan",
                "action": "budget_block",
                "event_type": event.event_type.value,
                "daily_spend": daily_spend,
                "daily_budget": daily_budget_usd,
            })
            break

        # Concurrency check
        if active_count + len(planned) >= _MAX_PARALLEL:
            logger.info(
                "Concurrency limit reached (%d). Deferring: %s",
                _MAX_PARALLEL, event.description[:60],
            )
            break

        # Phase-dependent gating
        if phase in ("production", "maintenance"):
            # In production/maintenance, only allow infra-safe events
            allowed_in_prod = {
                EventType.TEST_FAILURE,
                EventType.STALE_DOCS,
                EventType.KPI_DEGRADATION,
                EventType.COVERAGE_DROP,
            }
            if event.event_type not in allowed_in_prod:
                logger.info(
                    "Phase '%s': skipping %s (not allowed in conservative mode)",
                    phase, event.event_type.value,
                )
                _append_jsonl(_SINGULARITY_LOG, {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "phase": "plan",
                    "action": "phase_block",
                    "event_type": event.event_type.value,
                    "project_phase": phase,
                })
                continue

        planned.append(event)

    return planned


# ---------------------------------------------------------------------------
# EXECUTE phase — launch pipelines
# ---------------------------------------------------------------------------

def _build_pipeline_prompt(event: SingularityEvent) -> str:
    """Build the prompt for the pipeline agent."""
    routing = _PIPELINE_ROUTING.get(event.event_type)
    if not routing or not routing[0]:
        return ""

    pipeline_name = routing[0]

    if event.event_type == EventType.NEW_FEATURE:
        return (
            "Process GitHub issue #%d as a new feature using the SDD pipeline. "
            "Title: %s. Body: %s"
            % (event.details.get("issue_number", 0),
               event.details.get("title", ""),
               event.details.get("body", "")[:300])
        )

    if event.event_type == EventType.BUG_REPORT:
        return (
            "Process GitHub issue #%d as a bug report. "
            "Investigate, fix, and create a PR. "
            "Title: %s. Body: %s"
            % (event.details.get("issue_number", 0),
               event.details.get("title", ""),
               event.details.get("body", "")[:300])
        )

    if event.event_type == EventType.TEST_FAILURE:
        return (
            "Auto-repair test failures. "
            "There are %d test failures detected in the last 24 hours. "
            "Analyze the error patterns and apply fixes."
            % event.details.get("count", 0)
        )

    if event.event_type == EventType.STALE_DOCS:
        return (
            "Run /doc-sync to update %d stale documentation entries. "
            "Files affected: %s"
            % (event.details.get("count", 0),
               ", ".join(event.details.get("files", [])[:5]))
        )

    if event.event_type == EventType.ERROR_PATTERN:
        return (
            "Run /self-improve to analyze error pattern: "
            "%d %s errors in service '%s' over the last 24 hours. "
            "Identify root cause and propose improvements."
            % (event.details.get("count", 0),
               event.details.get("error_type", "unknown"),
               event.details.get("service", "unknown"))
        )

    if event.event_type == EventType.KPI_DEGRADATION:
        return (
            "Run /metrics-calibrator. KPI score dropped from %.1f to %.1f "
            "(%.1f%% decrease). Analyze and recalibrate thresholds."
            % (event.details.get("previous", 0),
               event.details.get("current", 0),
               event.details.get("drop_pct", 0))
        )

    if event.event_type == EventType.COVERAGE_DROP:
        return (
            "Run /coverage-enforcement. Coverage dropped from %.1f%% to %.1f%%. "
            "Identify uncovered code and generate tests."
            % (event.details.get("previous", 0),
               event.details.get("current", 0))
        )

    if event.event_type == EventType.SKILL_FAILURE:
        return (
            "Skill '%s' has failed %d consecutive times. "
            "Run /optimize-skill %s to analyze failures and improve the skill."
            % (event.details.get("skill", "unknown"),
               event.details.get("consecutive_failures", 0),
               event.details.get("skill", "unknown"))
        )

    return "Handle event: %s" % event.description


def execute_event(
    event: SingularityEvent,
    executor: ClaudeExecutor,
    dry_run: bool = False,
) -> PipelineExecution:
    """Launch the appropriate pipeline for an event."""
    routing = _PIPELINE_ROUTING.get(event.event_type, ("unknown", "sonnet"))
    pipeline_name = routing[0]
    model = routing[1]

    execution = PipelineExecution(
        event=event,
        pipeline=pipeline_name,
        model=model,
        started_at=time.time(),
    )

    prompt = _build_pipeline_prompt(event)
    if not prompt:
        execution.finished_at = time.time()
        execution.success = False
        execution.result_text = "No pipeline configured for event type: %s" % (
            event.event_type.value)
        return execution

    if dry_run:
        execution.finished_at = time.time()
        execution.success = True
        execution.result_text = "[DRY RUN] Would execute: %s" % prompt[:200]
        return execution

    logger.info("Executing pipeline '%s' for: %s",
                pipeline_name, event.description[:80])

    result = executor.run_with_retry(
        prompt=prompt,
        model=model,
        timeout=600,
        max_retries=1,
    )

    execution.finished_at = time.time()
    execution.success = result.success
    execution.result_text = result.result_text[:2000]
    execution.cost_usd = result.cost_usd

    return execution


# ---------------------------------------------------------------------------
# KNOWLEDGE phase — feed outcomes back
# ---------------------------------------------------------------------------

def _push_singularity_to_paperclip(execution: PipelineExecution) -> None:
    """Push Singularity event result to Paperclip inbox (fire-and-forget).

    Imports PaperclipClient lazily to avoid hard dependency. If Paperclip
    is unavailable, silently does nothing.
    """
    try:
        # Lazy import -- packages/ecosystem-tools/lib may not be on path
        _pkg_lib = os.path.join(_PROJECT_ROOT, "packages", "ecosystem-tools", "lib")
        if _pkg_lib not in sys.path:
            sys.path.insert(0, _pkg_lib)
        from paperclip_client import PaperclipClient  # type: ignore[import-untyped]

        client = PaperclipClient()
        if not client.is_available():
            return

        event = execution.event
        severity = "critical" if not execution.success else "info"
        title = "Singularity: %s %s" % (
            execution.pipeline,
            "FAILED" if not execution.success else "OK",
        )
        body = "Event: %s\nSource: %s\nDuration: %.1fs\nCost: $%.4f" % (
            event.description[:120],
            event.source,
            (execution.finished_at - execution.started_at)
            if execution.finished_at else 0.0,
            execution.cost_usd,
        )
        client.push_notification(title, body, severity)
    except Exception:
        pass  # Fire-and-forget -- never fail the main flow


def record_knowledge(
    execution: PipelineExecution,
    project_root: str,
) -> None:
    """Record execution outcome for learning."""
    event = execution.event
    duration_s = (
        (execution.finished_at - execution.started_at)
        if execution.finished_at else 0.0
    )

    # Log to singularity-events.jsonl
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "phase": "knowledge",
        "event_type": event.event_type.value,
        "source": event.source,
        "description": event.description[:200],
        "pipeline": execution.pipeline,
        "model": execution.model,
        "success": execution.success,
        "duration_s": round(duration_s, 2),
        "cost_usd": execution.cost_usd,
        "dedup_key": event.dedup_key,
    }
    _append_jsonl(_SINGULARITY_LOG, log_entry)

    # Log cost event
    if execution.cost_usd > 0:
        _append_jsonl(
            os.path.join(_METRICS_DIR, "cost-events.jsonl"),
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "agent": "singularity:%s" % execution.pipeline,
                "model": execution.model,
                "estimated_cost_usd": execution.cost_usd,
            },
        )

    # Notification for failures
    if not execution.success:
        send_raw(
            "[SINGULARITY] Pipeline '%s' FAILED for: %s\nError: %s"
            % (execution.pipeline, event.description[:100],
               execution.result_text[:300])
        )

    # Push event to Paperclip dashboard (fire-and-forget)
    _push_singularity_to_paperclip(execution)


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class SingularityController:
    """The central autonomous loop that monitors, classifies, and routes
    events to the right pipeline.

    Implements the MAPE-K (Monitor-Analyze-Plan-Execute-Knowledge) loop
    for continuous codebase health management.
    """

    def __init__(
        self,
        project_root: Optional[str] = None,
        daily_budget_usd: float = _DEFAULT_DAILY_BUDGET_USD,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        self.project_root = project_root or _PROJECT_ROOT
        self.daily_budget_usd = daily_budget_usd
        self.dry_run = dry_run
        self.verbose = verbose
        self._shutdown = False

        # State
        self._processed_keys: Set[str] = set()
        self._cooldowns: Dict[str, float] = {}
        self._active_executions: List[PipelineExecution] = []
        self._completed_executions: List[PipelineExecution] = []

        # Success rate tracking per event type
        self._success_counts: Dict[str, int] = {}
        self._total_counts: Dict[str, int] = {}

        # Executor
        self._executor = ClaudeExecutor(
            working_dir=self.project_root,
            verbose=verbose,
        )

        # Load previously processed keys from log
        self._load_processed_keys()

    def _load_processed_keys(self) -> None:
        """Load dedup keys from the singularity log to avoid reprocessing."""
        entries = _read_jsonl(_SINGULARITY_LOG, max_lines=10000)
        for entry in entries:
            key = entry.get("dedup_key")
            if key and entry.get("phase") == "knowledge":
                self._processed_keys.add(key)

    def _setup_signal_handlers(self) -> None:
        """Register SIGTERM/SIGINT for graceful shutdown."""
        def handler(signum: int, frame: Any) -> None:
            logger.info("Received signal %d, shutting down gracefully...", signum)
            self._shutdown = True

        signal.signal(signal.SIGTERM, handler)
        signal.signal(signal.SIGINT, handler)

    def run_once(self) -> Dict[str, Any]:
        """Execute a single pass through the MAPE-K loop.

        Returns a summary dict with events detected, planned, executed,
        and their outcomes.
        """
        cycle_start = time.time()
        summary: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "dry_run": self.dry_run,
            "events_detected": 0,
            "events_actionable": 0,
            "events_planned": 0,
            "events_executed": 0,
            "events_succeeded": 0,
            "events_failed": 0,
            "total_cost_usd": 0.0,
            "details": [],
        }

        # MONITOR
        logger.info("=== MONITOR phase ===")
        events = monitor_all(self.project_root)
        summary["events_detected"] = len(events)

        if not events:
            logger.info("No events detected. Codebase is healthy.")
            _append_jsonl(_SINGULARITY_LOG, {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "phase": "monitor",
                "action": "no_events",
                "message": "No actionable events detected",
            })
            return summary

        logger.info("Detected %d events", len(events))

        # ANALYZE
        logger.info("=== ANALYZE phase ===")
        actionable = analyze(events, self._processed_keys, self._cooldowns)
        summary["events_actionable"] = len(actionable)

        if not actionable:
            logger.info("No actionable events after filtering.")
            return summary

        logger.info("%d actionable events after dedup/cooldown", len(actionable))

        # PLAN
        logger.info("=== PLAN phase ===")
        active_count = len(self._active_executions)
        planned = plan(
            actionable, self.project_root, active_count, self.daily_budget_usd
        )
        summary["events_planned"] = len(planned)

        if not planned:
            logger.info("No events planned for execution.")
            return summary

        logger.info("Planned %d events for execution", len(planned))

        # EXECUTE
        logger.info("=== EXECUTE phase ===")
        for event in planned:
            if self._shutdown:
                logger.info("Shutdown requested, stopping execution.")
                break

            execution = execute_event(event, self._executor, self.dry_run)
            summary["events_executed"] += 1

            if execution.success:
                summary["events_succeeded"] += 1
            else:
                summary["events_failed"] += 1

            summary["total_cost_usd"] += execution.cost_usd

            # Track success rates
            etype = event.event_type.value
            self._total_counts[etype] = self._total_counts.get(etype, 0) + 1
            if execution.success:
                self._success_counts[etype] = self._success_counts.get(etype, 0) + 1

            summary["details"].append({
                "event_type": event.event_type.value,
                "description": event.description[:200],
                "pipeline": execution.pipeline,
                "success": execution.success,
                "cost_usd": execution.cost_usd,
                "duration_s": round(
                    (execution.finished_at or time.time()) - execution.started_at, 2
                ),
            })

            # KNOWLEDGE (per-execution)
            logger.info("=== KNOWLEDGE phase ===")
            record_knowledge(execution, self.project_root)

            # Update state
            self._processed_keys.add(event.dedup_key)
            self._cooldowns[event.event_type.value] = time.time()
            self._completed_executions.append(execution)

        cycle_duration = time.time() - cycle_start
        summary["cycle_duration_s"] = round(cycle_duration, 2)

        # Log cycle summary
        _append_jsonl(_SINGULARITY_LOG, {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "phase": "cycle_complete",
            "detected": summary["events_detected"],
            "actionable": summary["events_actionable"],
            "planned": summary["events_planned"],
            "executed": summary["events_executed"],
            "succeeded": summary["events_succeeded"],
            "failed": summary["events_failed"],
            "total_cost_usd": summary["total_cost_usd"],
            "cycle_duration_s": summary["cycle_duration_s"],
        })

        return summary

    def run_daemon(self, interval_seconds: int = 300) -> None:
        """Run the MAPE-K loop continuously at the given interval.

        Handles SIGTERM/SIGINT for graceful shutdown.
        """
        self._setup_signal_handlers()
        logger.info(
            "Singularity daemon starting (interval=%ds, budget=$%.2f/day, dry_run=%s)",
            interval_seconds, self.daily_budget_usd, self.dry_run,
        )
        send_raw("[SINGULARITY] Daemon started (interval=%ds)" % interval_seconds)

        _append_jsonl(_SINGULARITY_LOG, {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "phase": "daemon_start",
            "interval_seconds": interval_seconds,
            "daily_budget_usd": self.daily_budget_usd,
            "dry_run": self.dry_run,
        })

        cycle = 0
        while not self._shutdown:
            cycle += 1
            logger.info("--- Cycle %d ---", cycle)

            try:
                summary = self.run_once()
                if summary["events_executed"] > 0:
                    logger.info(
                        "Cycle %d: %d executed, %d succeeded, %d failed, $%.4f",
                        cycle,
                        summary["events_executed"],
                        summary["events_succeeded"],
                        summary["events_failed"],
                        summary["total_cost_usd"],
                    )
            except Exception as e:
                logger.error("Cycle %d failed: %s", cycle, e, exc_info=True)
                _append_jsonl(_SINGULARITY_LOG, {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "phase": "cycle_error",
                    "cycle": cycle,
                    "error": str(e)[:500],
                })

            # Wait for next cycle (interruptible)
            for _ in range(interval_seconds):
                if self._shutdown:
                    break
                time.sleep(1)

        logger.info("Singularity daemon stopped after %d cycles.", cycle)
        send_raw("[SINGULARITY] Daemon stopped after %d cycles" % cycle)

        _append_jsonl(_SINGULARITY_LOG, {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "phase": "daemon_stop",
            "total_cycles": cycle,
        })

    def status(self) -> Dict[str, Any]:
        """Return current state of the singularity controller."""
        # Read recent events from log
        recent_events = _read_jsonl(_SINGULARITY_LOG, max_lines=100)
        recent_executions = [
            e for e in recent_events
            if e.get("phase") == "knowledge"
        ][-20:]

        # Calculate success rates
        success_rates: Dict[str, float] = {}
        for etype in self._total_counts:
            total = self._total_counts[etype]
            success = self._success_counts.get(etype, 0)
            if total > 0:
                success_rates[etype] = round(success / total * 100, 1)

        return {
            "processed_events": len(self._processed_keys),
            "active_cooldowns": {
                k: int(_COOLDOWN_SECONDS - (time.time() - v))
                for k, v in self._cooldowns.items()
                if time.time() - v < _COOLDOWN_SECONDS
            },
            "completed_this_session": len(self._completed_executions),
            "success_rates": success_rates,
            "daily_spend_usd": _get_daily_spend(self.project_root),
            "daily_budget_usd": self.daily_budget_usd,
            "recent_executions": recent_executions,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_summary(summary: Dict[str, Any]) -> None:
    """Pretty-print a cycle summary."""
    print("\n  Singularity Cycle Summary")
    print("  " + "-" * 40)
    print("  Detected:   %d events" % summary["events_detected"])
    print("  Actionable: %d events" % summary["events_actionable"])
    print("  Planned:    %d events" % summary["events_planned"])
    print("  Executed:   %d events" % summary["events_executed"])
    print("  Succeeded:  %d" % summary["events_succeeded"])
    print("  Failed:     %d" % summary["events_failed"])
    print("  Cost:       $%.4f" % summary["total_cost_usd"])
    if "cycle_duration_s" in summary:
        print("  Duration:   %.1fs" % summary["cycle_duration_s"])

    if summary.get("details"):
        print("\n  Details:")
        for d in summary["details"]:
            status = "OK" if d["success"] else "FAIL"
            print("    [%s] %s -> %s ($%.4f, %.1fs)" % (
                status, d["event_type"], d["pipeline"],
                d["cost_usd"], d["duration_s"],
            ))
    print()


def _print_status(status_data: Dict[str, Any]) -> None:
    """Pretty-print controller status."""
    print("\n  Singularity Status")
    print("  " + "-" * 40)
    print("  Processed events: %d" % status_data["processed_events"])
    print("  Completed (session): %d" % status_data["completed_this_session"])
    print("  Daily spend: $%.4f / $%.2f" % (
        status_data["daily_spend_usd"], status_data["daily_budget_usd"],
    ))

    cooldowns = status_data.get("active_cooldowns", {})
    if cooldowns:
        print("\n  Active cooldowns:")
        for etype, remaining in cooldowns.items():
            print("    %s: %ds remaining" % (etype, remaining))

    rates = status_data.get("success_rates", {})
    if rates:
        print("\n  Success rates:")
        for etype, rate in rates.items():
            print("    %s: %.1f%%" % (etype, rate))

    recent = status_data.get("recent_executions", [])
    if recent:
        print("\n  Recent executions (last %d):" % len(recent))
        for ex in recent[-10:]:
            status = "OK" if ex.get("success") else "FAIL"
            print("    [%s] %s %s ($%.4f)" % (
                status,
                ex.get("event_type", "?"),
                ex.get("description", "")[:60],
                ex.get("cost_usd", 0),
            ))

    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Codebase Singularity — autonomous MAPE-K control loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python lib/singularity.py run\n"
            "  python lib/singularity.py dry-run\n"
            "  python lib/singularity.py daemon --interval 300\n"
            "  python lib/singularity.py status\n"
        ),
    )
    parser.add_argument(
        "command",
        choices=["run", "daemon", "dry-run", "status"],
        help="Command to execute",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("SINGULARITY_INTERVAL", "86400")),
        help="Polling interval in seconds for daemon mode (default: 86400 = 1 day, via SINGULARITY_INTERVAL env var)",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=_DEFAULT_DAILY_BUDGET_USD,
        help="Daily budget in USD (default: %.2f)" % _DEFAULT_DAILY_BUDGET_USD,
    )
    parser.add_argument(
        "--project-dir",
        default=_PROJECT_ROOT,
        help="Project root directory (default: auto-detected)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    # Off by default — must explicitly enable via env var
    enabled = os.environ.get("SINGULARITY_ENABLED", "false").lower()
    if enabled not in ("true", "1", "yes"):
        print("Singularity is disabled. Set SINGULARITY_ENABLED=true to enable.")
        print("This is off by default to avoid unintended API costs.")
        return 0

    parser = build_parser()
    args = parser.parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    dry_run = args.command == "dry-run"

    controller = SingularityController(
        project_root=args.project_dir,
        daily_budget_usd=args.budget,
        dry_run=dry_run,
        verbose=args.verbose,
    )

    if args.command == "status":
        status_data = controller.status()
        _print_status(status_data)
        return 0

    if args.command in ("run", "dry-run"):
        summary = controller.run_once()
        _print_summary(summary)
        return 1 if summary["events_failed"] > 0 else 0

    if args.command == "daemon":
        controller.run_daemon(interval_seconds=args.interval)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
