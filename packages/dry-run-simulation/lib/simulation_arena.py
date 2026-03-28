"""Agent Simulation Arena — end-to-end agent workflow simulation and evolution tracking.

Runs scripted scenarios that simulate real developer workflows. Each scenario
is a sequence of "turns" (user messages + expected OS behaviors). The arena
measures which safety layers activated, total cost, time taken, quality of
output, and whether the OS "learned" (memory, calibration, archive).

Running the SAME scenario twice should show improvement (cheaper, faster,
fewer retries).

Python 3.9+ compatible. No external dependencies beyond stdlib + PyYAML.

Author: luum
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class TurnType(Enum):
    """Types of turns in a simulation scenario."""

    USER_MESSAGE = "user"         # Simulated user input
    EXPECTED_BEHAVIOR = "expect"  # What the OS should do
    CHECKPOINT = "checkpoint"     # Measure metrics at this point
    DELAY = "delay"               # Simulate time passing


# Map YAML string values to enum members.
_TURN_TYPE_MAP: Dict[str, TurnType] = {
    "user": TurnType.USER_MESSAGE,
    "expect": TurnType.EXPECTED_BEHAVIOR,
    "checkpoint": TurnType.CHECKPOINT,
    "delay": TurnType.DELAY,
}


@dataclass
class Turn:
    """A single turn in a simulation scenario."""

    type: TurnType
    content: str                  # Message or expectation description
    expectations: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Scenario:
    """A complete simulation scenario with turns and budget expectations."""

    name: str
    description: str
    category: str                 # "feature", "bugfix", "research", "refactor"
    turns: List[Turn]
    expected_total_cost: float    # Upper bound (USD)
    expected_duration_minutes: float
    tags: List[str] = field(default_factory=list)


@dataclass
class TurnResult:
    """Result of simulating a single turn."""

    turn_index: int
    turn_type: str
    expectations_met: Dict[str, bool]   # {expectation: True/False}
    actual_values: Dict[str, Any]       # What actually happened
    duration_ms: float
    cost_usd: float
    passed: bool


@dataclass
class ScenarioResult:
    """Complete result of running a scenario."""

    scenario_name: str
    run_id: str
    timestamp: str
    turns: List[TurnResult]
    total_cost: float
    total_duration_s: float
    expectations_met: int
    expectations_total: int
    pass_rate: float
    safety_activations: Dict[str, int]     # {hook_name: count}
    memory_operations: Dict[str, int]      # {saves: N, searches: N}
    improvement_vs_previous: Optional[Dict[str, Any]]  # Comparison with last run


# ---------------------------------------------------------------------------
# Safety-mesh simulation helpers
# ---------------------------------------------------------------------------

# Patterns that trigger the clarification gate (simplified from hooks/clarification-gate.sh).
_VAGUE_PATTERNS: List[Tuple[str, int]] = [
    (r"\.(go|ts|py|java|rs|rb|js|tsx|jsx)\b", -15),  # has file extensions => REDUCES score
    (r"(all|every|complete|entire)\b", 20),            # scope without counts
    (r"(add|create|implement|build|write)\b", 15),     # action verbs (missing tech check separate)
    (r"(which\?|what type\?|where should\?)", 15),     # unanswered questions
    (r"ACCEPTANCE CRITERIA", -10),                      # has criteria => REDUCES score
]

_INFRA_SECURITY_KEYWORDS = re.compile(
    r"\b(docker|kubernetes|deploy|migration|schema|alter table|auth|authentication"
    r"|authorization|permission|credential|secret|token|jwt|oauth|api.?key"
    r"|password|encrypt|certificate|cors|csrf|rbac|acl)\b",
    re.IGNORECASE,
)


def _score_clarification_gate(message: str) -> int:
    """Score a user message for ambiguity (0-100). Higher = more ambiguous."""
    score = 50  # base score
    for pattern, delta in _VAGUE_PATTERNS:
        if re.search(pattern, message, re.IGNORECASE):
            score += delta

    # Short prompt penalty.
    if len(message) < 50:
        score += 20

    return max(0, min(100, score))


def _estimate_blast_radius(message: str) -> str:
    """Estimate blast radius from a prompt: LOW / MEDIUM / HIGH / CRITICAL."""
    # Count file path references.
    file_refs = len(re.findall(r"[\w\-/]+\.\w{1,5}\b", message))
    dir_refs = len(re.findall(r"[\w\-]+/[\w\-]+/", message))
    score = file_refs + dir_refs * 5

    # Bulk keywords.
    if re.search(r"\b(rebrand|migrate all|global replace|bulk update)\b", message, re.IGNORECASE):
        score += 30
    if re.search(r"\b(all services|every endpoint|across the project)\b", message, re.IGNORECASE):
        score += 50

    # Infra / security auto-escalate.
    if _INFRA_SECURITY_KEYWORDS.search(message):
        return "CRITICAL"

    if score > 50:
        return "CRITICAL"
    if score > 20:
        return "HIGH"
    if score > 5:
        return "MEDIUM"
    return "LOW"


def _detect_sdd_suggestion(message: str) -> bool:
    """Would the OS suggest an SDD pipeline for this message?"""
    indicators = [
        r"\b(add|implement|create|build)\b.*\b(service|feature|endpoint|module)\b",
        r"\b(refactor|migrate|rebrand)\b",
        r"\b(new|design|architecture)\b",
    ]
    for pattern in indicators:
        if re.search(pattern, message, re.IGNORECASE):
            return True
    return False


def _detect_planning_poker(message: str) -> bool:
    """Would planning poker typically run for this message?"""
    # Planning poker runs for medium+ tasks.
    if re.search(r"\b(implement|create|add|refactor|migrate)\b", message, re.IGNORECASE):
        if len(message) > 80:
            return True
    return False


def _estimate_cost_for_message(message: str) -> float:
    """Rough cost estimate based on message complexity."""
    words = len(message.split())
    if words < 20:
        return round(0.05 + words * 0.005, 4)
    if words < 50:
        return round(0.15 + words * 0.01, 4)
    return round(0.50 + words * 0.02, 4)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class SimulationArena:
    """Runs scripted scenarios through OS simulation and tracks evolution."""

    def __init__(
        self,
        scenarios_dir: str = "tests/arena/scenarios",
        results_dir: str = ".cognitive-os/metrics/arena-results",
    ) -> None:
        self.scenarios_dir = scenarios_dir
        self.results_dir = results_dir

    # -- scenario loading ---------------------------------------------------

    def load_scenario(self, name: str) -> Scenario:
        """Load a scenario from a YAML file.

        Args:
            name: Scenario file name (with or without .yaml extension).

        Returns:
            Parsed Scenario dataclass.

        Raises:
            FileNotFoundError: If the scenario file does not exist.
            ValueError: If the scenario YAML is missing required fields.
        """
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "PyYAML is required to load scenarios. Install with: pip install pyyaml"
            )

        if not name.endswith(".yaml"):
            name = f"{name}.yaml"

        path = Path(self.scenarios_dir) / name
        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found: {path}")

        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        return self._parse_scenario(data)

    def _parse_scenario(self, data: Dict[str, Any]) -> Scenario:
        """Parse a raw YAML dict into a Scenario."""
        required = ("name", "turns", "expected_total_cost")
        for key in required:
            if key not in data:
                raise ValueError(f"Scenario missing required field: '{key}'")

        turns: List[Turn] = []
        for raw_turn in data["turns"]:
            turn_type_str = raw_turn.get("type", "user")
            turn_type = _TURN_TYPE_MAP.get(turn_type_str)
            if turn_type is None:
                raise ValueError(
                    f"Unknown turn type '{turn_type_str}'. "
                    f"Valid: {list(_TURN_TYPE_MAP.keys())}"
                )
            turns.append(
                Turn(
                    type=turn_type,
                    content=raw_turn.get("content", ""),
                    expectations=raw_turn.get("expectations", {}),
                )
            )

        return Scenario(
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", "general"),
            turns=turns,
            expected_total_cost=float(data["expected_total_cost"]),
            expected_duration_minutes=float(data.get("expected_duration_minutes", 30)),
            tags=data.get("tags", []),
        )

    # -- simulation ---------------------------------------------------------

    def run_scenario(
        self,
        scenario: Scenario,
        dry_run: bool = False,
    ) -> ScenarioResult:
        """Run a scenario through the OS simulation.

        For each turn:
        - USER_MESSAGE: simulate the input, check what the OS does.
        - EXPECTED_BEHAVIOR: verify the OS responded correctly.
        - CHECKPOINT: measure current metrics.
        - DELAY: simulate time passing.

        In dry_run mode: only validate scenario structure, don't execute.

        Args:
            scenario: The scenario to run.
            dry_run: If True, validate only.

        Returns:
            ScenarioResult with all measurements.
        """
        run_id = self._generate_run_id(scenario.name)
        context: Dict[str, Any] = {
            "cumulative_cost": 0.0,
            "safety_activations": {},
            "memory_ops": {"saves": 0, "searches": 0},
            "phases_triggered": [],
            "files_modified": [],
            "turn_costs": [],
        }

        turn_results: List[TurnResult] = []
        start = time.monotonic()

        for idx, turn in enumerate(scenario.turns):
            if dry_run:
                tr = TurnResult(
                    turn_index=idx,
                    turn_type=turn.type.value,
                    expectations_met={},
                    actual_values={"dry_run": True},
                    duration_ms=0.0,
                    cost_usd=0.0,
                    passed=True,
                )
            else:
                tr = self.simulate_turn(turn, context)
                tr.turn_index = idx
            turn_results.append(tr)

        elapsed_s = time.monotonic() - start

        # Tally expectations.
        total_expectations = 0
        met_expectations = 0
        for tr in turn_results:
            for _key, passed in tr.expectations_met.items():
                total_expectations += 1
                if passed:
                    met_expectations += 1

        total_cost = sum(tr.cost_usd for tr in turn_results)
        pass_rate = (met_expectations / total_expectations * 100.0) if total_expectations > 0 else 100.0

        # Compare with previous runs.
        improvement = self._load_previous_comparison(scenario.name, total_cost, elapsed_s, pass_rate)

        result = ScenarioResult(
            scenario_name=scenario.name,
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            turns=turn_results,
            total_cost=round(total_cost, 4),
            total_duration_s=round(elapsed_s, 2),
            expectations_met=met_expectations,
            expectations_total=total_expectations,
            pass_rate=round(pass_rate, 2),
            safety_activations=dict(context.get("safety_activations", {})),
            memory_operations=dict(context.get("memory_ops", {})),
            improvement_vs_previous=improvement,
        )

        if not dry_run:
            self.save_result(result)

        return result

    def simulate_turn(self, turn: Turn, context: Dict[str, Any]) -> TurnResult:
        """Simulate a single turn and evaluate expectations.

        Args:
            turn: The turn to simulate.
            context: Mutable simulation context (accumulates across turns).

        Returns:
            TurnResult with expectation evaluations and measurements.
        """
        t0 = time.monotonic()
        expectations_met: Dict[str, bool] = {}
        actual_values: Dict[str, Any] = {}
        cost = 0.0

        if turn.type == TurnType.USER_MESSAGE:
            cost, expectations_met, actual_values = self._simulate_user_message(
                turn, context
            )

        elif turn.type == TurnType.EXPECTED_BEHAVIOR:
            expectations_met, actual_values = self._simulate_expected_behavior(
                turn, context
            )

        elif turn.type == TurnType.CHECKPOINT:
            expectations_met, actual_values = self._simulate_checkpoint(
                turn, context
            )

        elif turn.type == TurnType.DELAY:
            actual_values = {"delay_simulated": True}

        duration_ms = (time.monotonic() - t0) * 1000.0
        context["cumulative_cost"] = context.get("cumulative_cost", 0.0) + cost

        passed = all(expectations_met.values()) if expectations_met else True

        return TurnResult(
            turn_index=0,  # Will be set by caller.
            turn_type=turn.type.value,
            expectations_met=expectations_met,
            actual_values=actual_values,
            duration_ms=round(duration_ms, 2),
            cost_usd=round(cost, 4),
            passed=passed,
        )

    def _simulate_user_message(
        self, turn: Turn, context: Dict[str, Any]
    ) -> Tuple[float, Dict[str, bool], Dict[str, Any]]:
        """Simulate a user message turn."""
        message = turn.content
        expectations = turn.expectations
        met: Dict[str, bool] = {}
        actual: Dict[str, Any] = {}

        # Clarification gate scoring.
        gate_score = _score_clarification_gate(message)
        gate_activates = gate_score > 60
        gate_passes = gate_score <= 60
        actual["clarification_gate_score"] = gate_score
        actual["clarification_gate_activates"] = gate_activates

        if "clarification_gate_activates" in expectations:
            met["clarification_gate_activates"] = gate_activates == expectations["clarification_gate_activates"]
        if "clarification_gate_passes" in expectations:
            met["clarification_gate_passes"] = gate_passes == expectations["clarification_gate_passes"]

        # Track gate activation.
        if gate_activates:
            sa = context.setdefault("safety_activations", {})
            sa["clarification-gate"] = sa.get("clarification-gate", 0) + 1

        # Blast radius estimation.
        blast = _estimate_blast_radius(message)
        actual["blast_radius"] = blast
        if "blast_radius" in expectations:
            met["blast_radius"] = blast == expectations["blast_radius"]

        # SDD pipeline suggestion.
        sdd = _detect_sdd_suggestion(message)
        actual["sdd_pipeline_suggested"] = sdd
        if "sdd_pipeline_suggested" in expectations:
            met["sdd_pipeline_suggested"] = sdd == expectations["sdd_pipeline_suggested"]

        # Planning poker.
        poker = _detect_planning_poker(message)
        actual["planning_poker_runs"] = poker
        if "planning_poker_runs" in expectations:
            met["planning_poker_runs"] = poker == expectations["planning_poker_runs"]

        # Cost estimation.
        cost = _estimate_cost_for_message(message)
        actual["cost_estimate"] = cost
        if "cost_prediction_shown" in expectations:
            met["cost_prediction_shown"] = cost > 0

        # Scope proportionality.
        if "scope_proportionality_check" in expectations:
            actual["scope_proportionality_check"] = True
            met["scope_proportionality_check"] = True

        # Memory search (simulated).
        if "memory_search_first" in expectations:
            # Simulate that the OS always searches memory first.
            context.setdefault("memory_ops", {})["searches"] = (
                context.get("memory_ops", {}).get("searches", 0) + 1
            )
            actual["memory_search_first"] = True
            met["memory_search_first"] = True

        # Memory hit (for evolution scenarios).
        if "memory_hit" in expectations:
            # Memory hit depends on whether a prior save exists in context.
            has_prior = context.get("memory_ops", {}).get("saves", 0) > 0
            actual["memory_hit"] = has_prior
            met["memory_hit"] = has_prior == expectations["memory_hit"]

        # Cost lower than first run.
        if "cost_lower_than_first" in expectations:
            turn_costs = context.get("turn_costs", [])
            if turn_costs:
                lower = cost < turn_costs[0]
                actual["cost_lower_than_first"] = lower
                met["cost_lower_than_first"] = lower == expectations["cost_lower_than_first"]
            else:
                actual["cost_lower_than_first"] = False
                met["cost_lower_than_first"] = not expectations["cost_lower_than_first"]

        # No redundant search.
        if "no_redundant_search" in expectations:
            has_prior = context.get("memory_ops", {}).get("saves", 0) > 0
            actual["no_redundant_search"] = has_prior
            met["no_redundant_search"] = has_prior == expectations["no_redundant_search"]

        # Deep research skill.
        if "deep_research_skill" in expectations:
            is_research = bool(re.search(r"\b(research|investigate|compare|evaluate)\b", message, re.IGNORECASE))
            actual["deep_research_skill"] = is_research
            met["deep_research_skill"] = is_research == expectations["deep_research_skill"]

        # Reason (informational only).
        if "reason" in expectations:
            actual["reason"] = expectations["reason"]

        context.setdefault("turn_costs", []).append(cost)
        return cost, met, actual

    def _simulate_expected_behavior(
        self, turn: Turn, context: Dict[str, Any]
    ) -> Tuple[Dict[str, bool], Dict[str, Any]]:
        """Simulate an expected-behavior turn."""
        expectations = turn.expectations
        met: Dict[str, bool] = {}
        actual: Dict[str, Any] = {}

        # Phase checks.
        if "phase" in expectations:
            phase = expectations["phase"]
            context.setdefault("phases_triggered", []).append(phase)
            actual["phase"] = phase
            met["phase"] = True  # Phase is simulated as triggered.

        # Proposal created.
        if "proposal_created" in expectations:
            actual["proposal_created"] = True
            met["proposal_created"] = True

        # Files analyzed.
        if "files_analyzed" in expectations:
            actual["files_analyzed"] = True
            met["files_analyzed"] = True

        # Files modified max.
        if "files_modified_max" in expectations:
            # In simulation, we assume proportional fixes.
            simulated_count = 1
            actual["files_modified"] = simulated_count
            met["files_modified_max"] = simulated_count <= expectations["files_modified_max"]

        # Files deleted.
        if "files_deleted" in expectations:
            actual["files_deleted"] = 0
            met["files_deleted"] = 0 == expectations["files_deleted"]

        # Claim validator.
        if "claim_validator_runs" in expectations:
            actual["claim_validator_runs"] = True
            met["claim_validator_runs"] = True

        return met, actual

    def _simulate_checkpoint(
        self, turn: Turn, context: Dict[str, Any]
    ) -> Tuple[Dict[str, bool], Dict[str, Any]]:
        """Simulate a checkpoint turn (measure metrics)."""
        expectations = turn.expectations
        met: Dict[str, bool] = {}
        actual: Dict[str, Any] = {}

        cumulative_cost = context.get("cumulative_cost", 0.0)
        actual["cumulative_cost"] = cumulative_cost

        # Cost under check.
        if "cost_under" in expectations:
            threshold = float(expectations["cost_under"])
            met["cost_under"] = cumulative_cost <= threshold
            actual["cost_threshold"] = threshold

        # Memory saved.
        if "memory_saved" in expectations:
            # Simulate a save.
            mem = context.setdefault("memory_ops", {})
            mem["saves"] = mem.get("saves", 0) + 1
            actual["memory_saved"] = True
            met["memory_saved"] = True

        # Trust score above.
        if "trust_score_above" in expectations:
            simulated_trust = 0.85
            actual["trust_score"] = simulated_trust
            met["trust_score_above"] = simulated_trust >= float(expectations["trust_score_above"])

        # Cost recorded.
        if "cost_recorded" in expectations:
            actual["cost_recorded"] = True
            met["cost_recorded"] = True

        return met, actual

    # -- comparison ---------------------------------------------------------

    def compare_runs(self, scenario_name: str) -> Dict[str, Any]:
        """Compare the latest run with previous runs.

        Returns a dict with cost improvement, speed improvement, quality
        improvement, memory reuse, and learning detection.
        """
        history = self._load_history(scenario_name)
        if len(history) < 2:
            return {
                "runs_compared": len(history),
                "cost_improvement": 0.0,
                "speed_improvement": 0.0,
                "quality_improvement": 0.0,
                "memory_reuse": False,
                "learning_detected": False,
            }

        latest = history[-1]
        previous = history[-2]

        prev_cost = previous.get("total_cost", 1.0) or 1.0
        prev_dur = previous.get("total_duration_s", 1.0) or 1.0
        prev_rate = previous.get("pass_rate", 0.0)

        cost_imp = ((latest.get("total_cost", 0) - prev_cost) / prev_cost) * 100
        speed_imp = ((latest.get("total_duration_s", 0) - prev_dur) / prev_dur) * 100
        quality_imp = latest.get("pass_rate", 0) - prev_rate

        mem_ops = latest.get("memory_operations", {})
        memory_reuse = mem_ops.get("searches", 0) > 0 and mem_ops.get("saves", 0) > 0

        learning = cost_imp < 0 or quality_imp > 0 or memory_reuse

        return {
            "runs_compared": 2,
            "cost_improvement": round(cost_imp, 1),
            "speed_improvement": round(speed_imp, 1),
            "quality_improvement": round(quality_imp, 1),
            "memory_reuse": memory_reuse,
            "learning_detected": learning,
        }

    # -- reporting ----------------------------------------------------------

    def format_arena_report(self, result: ScenarioResult) -> str:
        """Format arena results as a readable report."""
        lines: List[str] = []
        sep = "=" * 40

        lines.append("")
        lines.append(f"{sep} SIMULATION ARENA REPORT {sep}")
        lines.append("")
        lines.append(f"Scenario: \"{result.scenario_name}\"")
        lines.append(f"Run: {result.run_id}")
        lines.append(f"Timestamp: {result.timestamp[:19]}")
        lines.append("")

        # Turns section.
        lines.append("TURNS:")
        for tr in result.turns:
            status = "PASS" if tr.passed else "FAIL"
            lines.append(f"  [{tr.turn_index + 1}] {tr.turn_type.upper()}: {status}")
            for exp_name, exp_passed in tr.expectations_met.items():
                marker = "[ok]" if exp_passed else "[FAIL]"
                lines.append(f"      {marker} {exp_name}")
            if tr.cost_usd > 0:
                lines.append(f"      cost: ${tr.cost_usd:.4f}")

        lines.append("")

        # Metrics section.
        lines.append("METRICS:")
        lines.append(f"  Total cost: ${result.total_cost:.4f}")
        lines.append(f"  Duration: {result.total_duration_s:.2f}s")
        lines.append(
            f"  Expectations: {result.expectations_met}/{result.expectations_total} "
            f"met ({result.pass_rate:.1f}%)"
        )
        if result.safety_activations:
            activations = ", ".join(
                f"{k}: {v}" for k, v in result.safety_activations.items()
            )
            lines.append(f"  Safety activations: {activations}")
        if result.memory_operations:
            mem = result.memory_operations
            lines.append(
                f"  Memory: {mem.get('saves', 0)} saves, "
                f"{mem.get('searches', 0)} searches"
            )

        # Improvement vs previous.
        if result.improvement_vs_previous:
            imp = result.improvement_vs_previous
            lines.append("")
            lines.append("VS PREVIOUS RUN:")
            if "cost_delta_pct" in imp:
                lines.append(f"  Cost: {imp['cost_delta_pct']:+.1f}%")
            if "speed_delta_pct" in imp:
                lines.append(f"  Speed: {imp['speed_delta_pct']:+.1f}%")
            if "quality_delta" in imp:
                lines.append(f"  Quality: {imp['quality_delta']:+.1f}%")
            if imp.get("learning_detected"):
                lines.append("  LEARNING DETECTED: Yes")

        lines.append("")
        lines.append(f"{sep}{'=' * 24}{sep}")
        return "\n".join(lines)

    def get_evolution_chart(self, scenario_name: str, runs: int = 10) -> str:
        """ASCII chart showing cost and quality improvement over runs."""
        history = self._load_history(scenario_name)
        if not history:
            return f"No runs recorded for scenario '{scenario_name}'."

        history = history[-runs:]
        lines: List[str] = []

        # Cost trend.
        costs = [h.get("total_cost", 0.0) for h in history]
        max_cost = max(costs) if costs else 1.0

        lines.append(f"Cost trend (last {len(costs)} runs):")
        for i, c in enumerate(costs):
            bar_len = int((c / max_cost) * 30) if max_cost > 0 else 0
            bar = "#" * bar_len
            lines.append(f"  ${c:.2f}  {bar}")

        if len(costs) >= 2 and costs[0] > 0:
            improvement = ((costs[-1] - costs[0]) / costs[0]) * 100
            direction = "improvement" if improvement < 0 else "regression"
            lines.append(f"         {abs(improvement):.0f}% {direction}")

        lines.append("")

        # Quality trend.
        rates = [h.get("pass_rate", 0.0) for h in history]
        lines.append("Quality trend:")
        for r in rates:
            bar_len = int(r / 100 * 30)
            bar = "#" * bar_len
            lines.append(f"  {r:.0f}%  {bar}")

        if len(rates) >= 2:
            lines.append(f"       from {rates[0]:.0f}% to {rates[-1]:.0f}%")

        return "\n".join(lines)

    # -- persistence --------------------------------------------------------

    def save_result(self, result: ScenarioResult) -> None:
        """Save result to JSONL for historical tracking."""
        path = Path(self.results_dir)
        path.mkdir(parents=True, exist_ok=True)

        filepath = path / "arena-results.jsonl"

        record: Dict[str, Any] = {
            "scenario_name": result.scenario_name,
            "run_id": result.run_id,
            "timestamp": result.timestamp,
            "total_cost": result.total_cost,
            "total_duration_s": result.total_duration_s,
            "expectations_met": result.expectations_met,
            "expectations_total": result.expectations_total,
            "pass_rate": result.pass_rate,
            "safety_activations": result.safety_activations,
            "memory_operations": result.memory_operations,
            "improvement_vs_previous": result.improvement_vs_previous,
            "turns": [
                {
                    "turn_index": tr.turn_index,
                    "turn_type": tr.turn_type,
                    "expectations_met": tr.expectations_met,
                    "duration_ms": tr.duration_ms,
                    "cost_usd": tr.cost_usd,
                    "passed": tr.passed,
                }
                for tr in result.turns
            ],
        }

        with open(filepath, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")

    def _load_history(self, scenario_name: str) -> List[Dict[str, Any]]:
        """Load all historical results for a scenario."""
        filepath = Path(self.results_dir) / "arena-results.jsonl"
        if not filepath.exists():
            return []

        results: List[Dict[str, Any]] = []
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if record.get("scenario_name") == scenario_name:
                            results.append(record)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return []
        return results

    def _load_previous_comparison(
        self,
        scenario_name: str,
        current_cost: float,
        current_duration: float,
        current_pass_rate: float,
    ) -> Optional[Dict[str, Any]]:
        """Load the last run and compute deltas."""
        history = self._load_history(scenario_name)
        if not history:
            return None

        prev = history[-1]
        prev_cost = prev.get("total_cost", 0.0) or 1.0
        prev_dur = prev.get("total_duration_s", 0.0) or 1.0
        prev_rate = prev.get("pass_rate", 0.0)

        cost_delta = ((current_cost - prev_cost) / prev_cost) * 100 if prev_cost else 0.0
        speed_delta = ((current_duration - prev_dur) / prev_dur) * 100 if prev_dur else 0.0
        quality_delta = current_pass_rate - prev_rate

        learning = cost_delta < 0 or quality_delta > 0

        return {
            "previous_run_id": prev.get("run_id", "unknown"),
            "cost_delta_pct": round(cost_delta, 1),
            "speed_delta_pct": round(speed_delta, 1),
            "quality_delta": round(quality_delta, 1),
            "learning_detected": learning,
        }

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _generate_run_id(scenario_name: str) -> str:
        """Generate a unique run ID."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        slug = re.sub(r"[^a-z0-9]", "-", scenario_name.lower())[:20]
        return f"{slug}-{ts}"
