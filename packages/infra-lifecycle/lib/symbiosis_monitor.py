# scope: both
"""Symbiosis Monitor — Overhead-to-Value Ratio Tracking

A symbiotic organism provides more value than it consumes.
This module measures the ratio of COS overhead (rules, hooks, context)
to useful work (actual code changes, task completions).

If the ratio exceeds the parasitic threshold (30%), the organism
should alert and suggest reducing its footprint.

Python 3.9+ compatible. No external dependencies beyond stdlib.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# 24 hours in seconds
_24H_SECONDS = 86400


def _iso_now() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _epoch_now() -> float:
    """Return current UTC epoch seconds."""
    return time.time()


def _read_jsonl_last_24h(path: Path) -> List[Dict[str, Any]]:
    """Read JSONL file and return entries from the last 24 hours.

    Handles missing files, empty files, and malformed lines gracefully.
    Filters by ``timestamp_epoch`` (int/float) first, falls back to parsing
    ``timestamp`` (ISO 8601 string).
    """
    if not path.exists():
        return []

    cutoff = _epoch_now() - _24H_SECONDS
    entries: List[Dict[str, Any]] = []

    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue

                # Determine entry age
                ts_epoch = entry.get("timestamp_epoch")
                if ts_epoch is not None:
                    try:
                        if float(ts_epoch) >= cutoff:
                            entries.append(entry)
                    except (TypeError, ValueError):
                        entries.append(entry)  # keep if unparseable
                    continue

                ts_str = entry.get("timestamp", "")
                if ts_str:
                    try:
                        # Handles both Z suffix and +00:00
                        ts_str_clean = ts_str.replace("Z", "+00:00")
                        dt = datetime.fromisoformat(ts_str_clean)
                        if dt.timestamp() >= cutoff:
                            entries.append(entry)
                    except (ValueError, TypeError):
                        entries.append(entry)  # keep if unparseable
                else:
                    # No timestamp at all — include it (conservative)
                    entries.append(entry)
    except OSError:
        pass

    return entries


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token (conservative for English)."""
    return max(0, len(text) // 4)


@dataclass
class SymbiosisReport:
    """Symbiosis health for a session."""

    # Overhead (what COS costs)
    rules_tokens: int            # Tokens consumed by RULES-COMPACT.md
    claude_md_tokens: int        # Tokens consumed by CLAUDE.md
    hook_latency_ms: int         # Total hook execution time in session
    hook_count: int              # Number of hook invocations
    governance_tokens: int       # Tokens consumed by contextual rule injection
    total_overhead_tokens: int   # Sum of all overhead

    # Value (what COS produced)
    tasks_completed: int         # Tasks marked completed
    errors_caught: int           # Errors detected by hooks
    errors_auto_fixed: int       # Errors auto-repaired
    skills_used: int             # Skills invoked
    memory_saves: int            # Engram saves (knowledge preserved)

    # Ratio
    overhead_ratio: float        # overhead / (overhead + useful_work)
    health: str                  # "symbiotic" | "neutral" | "parasitic"

    # Recommendation
    recommendation: Optional[str]


class SymbiosisMonitor:
    """Measures and reports on the organism's symbiosis with its host project."""

    PARASITIC_THRESHOLD = 0.30   # >30% overhead = parasitic
    HEALTHY_THRESHOLD = 0.10     # <10% = healthy symbiosis

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.metrics_dir = self.project_dir / ".cognitive-os" / "metrics"

    def measure_overhead(self) -> Dict[str, int]:
        """Measure COS overhead tokens and latency."""
        overhead: Dict[str, int] = {
            "rules_tokens": 0,
            "claude_md_tokens": 0,
            "hook_latency_ms": 0,
            "hook_count": 0,
            "governance_tokens": 0,
        }

        # Measure RULES-COMPACT.md tokens
        rules_compact = self.project_dir / "rules" / "RULES-COMPACT.md"
        if rules_compact.exists():
            try:
                overhead["rules_tokens"] = _estimate_tokens(rules_compact.read_text())
            except OSError:
                pass

        # Measure CLAUDE.md tokens (project-level first, then global)
        for claude_md_path in [
            self.project_dir / ".claude" / "CLAUDE.md",
            Path.home() / ".claude" / "CLAUDE.md",
        ]:
            if claude_md_path.exists():
                try:
                    overhead["claude_md_tokens"] = _estimate_tokens(
                        claude_md_path.read_text()
                    )
                except OSError:
                    pass
                break

        # Measure hook latency from performance.jsonl (last 24h)
        perf_file = self.metrics_dir / "performance.jsonl"
        perf_entries = _read_jsonl_last_24h(perf_file)
        total_hook_ms = 0
        hook_invocations = 0
        for entry in perf_entries:
            component = entry.get("component", "")
            if isinstance(component, str) and component.startswith("hook:"):
                duration = entry.get("duration_ms", 0)
                try:
                    total_hook_ms += int(float(duration))
                except (TypeError, ValueError):
                    pass
                hook_invocations += 1

        overhead["hook_latency_ms"] = total_hook_ms
        overhead["hook_count"] = hook_invocations

        # Measure contextual rule injections (estimate tokens from context-usage.jsonl)
        ctx_file = self.metrics_dir / "contextual-rules.jsonl"
        ctx_entries = _read_jsonl_last_24h(ctx_file)
        governance_tokens = 0
        for entry in ctx_entries:
            tokens = entry.get("tokens", 0)
            try:
                governance_tokens += int(float(tokens))
            except (TypeError, ValueError):
                pass
        overhead["governance_tokens"] = governance_tokens

        overhead["total_overhead_tokens"] = (
            overhead["rules_tokens"]
            + overhead["claude_md_tokens"]
            + overhead["governance_tokens"]
        )

        return overhead

    def measure_value(self) -> Dict[str, int]:
        """Measure value COS provided in the last 24 hours."""
        value: Dict[str, int] = {
            "tasks_completed": 0,
            "errors_caught": 0,
            "errors_auto_fixed": 0,
            "skills_used": 0,
            "memory_saves": 0,
        }

        # Count completed tasks from active-tasks.json
        # Check both possible locations
        for tasks_path in [
            self.project_dir / ".cognitive-os" / "tasks" / "active-tasks.json",
            self.project_dir / ".claude" / "tasks" / "active-tasks.json",
        ]:
            if tasks_path.exists():
                try:
                    data = json.loads(tasks_path.read_text())
                    tasks = data.get("tasks", [])
                    for task in tasks:
                        if task.get("status") == "completed":
                            value["tasks_completed"] += 1
                except (json.JSONDecodeError, OSError, TypeError):
                    pass
                break

        # Count errors from error-learning.jsonl (last 24h)
        error_file = self.metrics_dir / "error-learning.jsonl"
        error_entries = _read_jsonl_last_24h(error_file)
        value["errors_caught"] = len(error_entries)

        # Count auto-repairs from repair-outcomes.jsonl (last 24h)
        repair_file = self.metrics_dir / "repair-outcomes.jsonl"
        repair_entries = _read_jsonl_last_24h(repair_file)
        for entry in repair_entries:
            outcome = entry.get("outcome", "")
            if outcome == "success":
                value["errors_auto_fixed"] += 1

        # Count skill invocations from skill-metrics.jsonl (last 24h)
        skill_file = self.metrics_dir / "skill-metrics.jsonl"
        skill_entries = _read_jsonl_last_24h(skill_file)
        value["skills_used"] = len(skill_entries)

        # Count memory saves from session-learnings.jsonl (last 24h) as proxy
        # Each session learning represents at least one memory save
        learnings_file = self.metrics_dir / "session-learnings.jsonl"
        learning_entries = _read_jsonl_last_24h(learnings_file)
        value["memory_saves"] = len(learning_entries)

        return value

    def calculate_ratio(self, overhead: Dict[str, int], value: Dict[str, int]) -> float:
        """Calculate overhead ratio. Lower is better.

        The ratio represents what fraction of total token activity is overhead.
        A ratio of 0.10 means 10% overhead (healthy). A ratio of 0.35 means
        35% overhead (parasitic).

        Returns 0.0 when there is no data at all.
        """
        total_overhead = overhead["total_overhead_tokens"]

        # Estimate useful work tokens:
        # - Each completed task ~ 5000 tokens of useful work
        # - Each error caught saves ~ 3000 tokens of rework
        # - Each auto-fix saves ~ 8000 tokens (fix + verify)
        # - Each skill use ~ 2000 tokens of directed work
        # - Each memory save ~ 500 tokens of preserved knowledge
        useful_estimate = (
            value["tasks_completed"] * 5000
            + value["errors_caught"] * 3000
            + value["errors_auto_fixed"] * 8000
            + value["skills_used"] * 2000
            + value["memory_saves"] * 500
        )

        total = useful_estimate + total_overhead
        if total == 0:
            return 0.0

        return total_overhead / total

    def classify_health(self, ratio: float) -> str:
        """Classify the symbiosis health based on overhead ratio.

        Returns:
            "symbiotic" if ratio <= 10% (healthy)
            "neutral" if 10% < ratio <= 30%
            "parasitic" if ratio > 30%
        """
        if ratio <= self.HEALTHY_THRESHOLD:
            return "symbiotic"
        elif ratio <= self.PARASITIC_THRESHOLD:
            return "neutral"
        else:
            return "parasitic"

    def recommend(self, health: str, overhead: Dict[str, int]) -> Optional[str]:
        """Generate a recommendation based on health status and overhead breakdown."""
        if health == "parasitic":
            suggestions: List[str] = []
            if overhead["rules_tokens"] > 3000:
                suggestions.append(
                    "Reduce rules loading: switch to lean efficiency profile"
                )
            if overhead["hook_count"] > 20:
                suggestions.append(
                    "Reduce hook chain: raise capability level or switch to standard/lean profile"
                )
            if overhead["governance_tokens"] > 2000:
                suggestions.append(
                    "Reduce contextual rule injections: fewer triggers in cognitive-os.yaml"
                )
            if overhead["claude_md_tokens"] > 5000:
                suggestions.append(
                    "Reduce CLAUDE.md size: move project-specific content to .claude/rules/"
                )
            return (
                ". ".join(suggestions)
                if suggestions
                else "Consider raising capability level to reduce overhead."
            )
        elif health == "neutral":
            return (
                "Overhead is acceptable but could be optimized. "
                "Consider standard efficiency profile."
            )
        return None

    def generate_report(self) -> SymbiosisReport:
        """Generate full symbiosis report."""
        overhead = self.measure_overhead()
        value = self.measure_value()
        ratio = self.calculate_ratio(overhead, value)
        health = self.classify_health(ratio)
        rec = self.recommend(health, overhead)

        return SymbiosisReport(
            rules_tokens=overhead["rules_tokens"],
            claude_md_tokens=overhead["claude_md_tokens"],
            hook_latency_ms=overhead["hook_latency_ms"],
            hook_count=overhead["hook_count"],
            governance_tokens=overhead["governance_tokens"],
            total_overhead_tokens=overhead["total_overhead_tokens"],
            tasks_completed=value["tasks_completed"],
            errors_caught=value["errors_caught"],
            errors_auto_fixed=value["errors_auto_fixed"],
            skills_used=value["skills_used"],
            memory_saves=value["memory_saves"],
            overhead_ratio=ratio,
            health=health,
            recommendation=rec,
        )

    def format_report(self, report: SymbiosisReport) -> str:
        """Format human-readable symbiosis report."""
        icon = {"symbiotic": "●", "neutral": "◐", "parasitic": "○"}[report.health]

        lines = [
            "SYMBIOSIS REPORT",
            "=" * 40,
            f"Health: {icon} {report.health.upper()}",
            f"Overhead ratio: {report.overhead_ratio:.0%} (threshold: {self.PARASITIC_THRESHOLD:.0%})",
            "",
            "OVERHEAD (what COS costs):",
            f"  Rules tokens: {report.rules_tokens:,}",
            f"  CLAUDE.md tokens: {report.claude_md_tokens:,}",
            f"  Governance tokens: {report.governance_tokens:,}",
            f"  Hook invocations: {report.hook_count}",
            f"  Hook latency: {report.hook_latency_ms:,}ms",
            f"  Total overhead: {report.total_overhead_tokens:,} tokens",
            "",
            "VALUE (what COS provided):",
            f"  Tasks completed: {report.tasks_completed}",
            f"  Errors caught: {report.errors_caught}",
            f"  Errors auto-fixed: {report.errors_auto_fixed}",
            f"  Skills used: {report.skills_used}",
            f"  Memory saves: {report.memory_saves}",
        ]

        if report.recommendation:
            lines.extend(["", f"RECOMMENDATION: {report.recommendation}"])

        return "\n".join(lines)

    def log_report(self, report: SymbiosisReport) -> None:
        """Append report summary to metrics/symbiosis.jsonl."""
        log_file = self.metrics_dir / "symbiosis.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "timestamp": _iso_now(),
            "health": report.health,
            "overhead_ratio": round(report.overhead_ratio, 4),
            "overhead_tokens": report.total_overhead_tokens,
            "rules_tokens": report.rules_tokens,
            "claude_md_tokens": report.claude_md_tokens,
            "governance_tokens": report.governance_tokens,
            "hook_count": report.hook_count,
            "hook_latency_ms": report.hook_latency_ms,
            "tasks_completed": report.tasks_completed,
            "errors_caught": report.errors_caught,
            "errors_auto_fixed": report.errors_auto_fixed,
            "skills_used": report.skills_used,
            "memory_saves": report.memory_saves,
        }

        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass  # Never crash the session cleanup
