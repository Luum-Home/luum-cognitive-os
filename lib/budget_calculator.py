# SCOPE: both
"""Budget calculator for pre-development project estimation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Lookup table: (phase, complexity) -> (hours_min, hours_max, hours_expected)
# All values are per-person base hours.
# ---------------------------------------------------------------------------
PHASE_HOURS: Dict[Tuple[str, str], Tuple[float, float, float]] = {
    ("context-analysis", "low"): (4, 8, 6),
    ("context-analysis", "medium"): (8, 20, 14),
    ("context-analysis", "high"): (16, 40, 28),
    ("architecture", "low"): (8, 16, 12),
    ("architecture", "medium"): (16, 40, 28),
    ("architecture", "high"): (32, 80, 56),
    ("security-review", "low"): (4, 8, 6),
    ("security-review", "medium"): (8, 24, 16),
    ("security-review", "high"): (16, 48, 32),
    ("competitive-research", "low"): (4, 12, 8),
    ("competitive-research", "medium"): (12, 30, 20),
    ("competitive-research", "high"): (24, 60, 40),
    ("execution-planning", "low"): (4, 8, 6),
    ("execution-planning", "medium"): (8, 16, 12),
    ("execution-planning", "high"): (16, 32, 24),
    ("documentation", "low"): (2, 4, 3),
    ("documentation", "medium"): (4, 12, 8),
    ("documentation", "high"): (8, 24, 16),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PhaseEstimate:
    """Hour estimate for a single project phase."""

    name: str
    complexity: str
    team_size: int
    hours_min: float
    hours_max: float
    hours_expected: float


@dataclass
class InfraCost:
    """Monthly infrastructure or third-party service cost."""

    service: str
    monthly_cost: float
    months: int
    verified_source: str = ""  # URL or "" if unverified


@dataclass
class BudgetSummary:
    """Aggregated budget across all phases and cost categories."""

    phases: List[PhaseEstimate]
    infra_costs: List[InfraCost]
    third_party_costs: List[InfraCost]
    hourly_rate: float
    total_hours: float
    total_labor_cost: float
    total_infra_cost: float
    total_third_party: float
    grand_total: float


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def estimate_phase_hours(
    phase: str, complexity: str, team_size: int = 1
) -> PhaseEstimate:
    """Return a PhaseEstimate for the given phase / complexity / team size.

    Hours scale with team size using a power-law model to capture diminishing
    returns from parallelism:

        adjusted = base / (team_size ** 0.7)

    Args:
        phase: Name of the project phase (must be in PHASE_HOURS).
        complexity: Complexity level — "low", "medium", or "high".
        team_size: Number of people working on the phase simultaneously.

    Returns:
        PhaseEstimate with scaled hour values.

    Raises:
        KeyError: If (phase, complexity) is not in PHASE_HOURS.
        ValueError: If team_size < 1.
    """
    if team_size < 1:
        raise ValueError(f"team_size must be >= 1, got {team_size}")

    base_min, base_max, base_expected = PHASE_HOURS[(phase, complexity)]
    divisor = team_size ** 0.7

    return PhaseEstimate(
        name=phase,
        complexity=complexity,
        team_size=team_size,
        hours_min=base_min / divisor,
        hours_max=base_max / divisor,
        hours_expected=base_expected / divisor,
    )


def generate_budget_summary(
    phases: List[PhaseEstimate],
    infra_costs: List[InfraCost],
    third_party_costs: List[InfraCost],
    hourly_rate: float,
) -> BudgetSummary:
    """Build an aggregated BudgetSummary from phase estimates and cost items.

    Args:
        phases: Phase estimates produced by estimate_phase_hours.
        infra_costs: Infrastructure service cost items.
        third_party_costs: Third-party SaaS / API cost items.
        hourly_rate: Billable hourly rate (USD or any consistent currency).

    Returns:
        BudgetSummary with all totals calculated.
    """
    total_hours = sum(p.hours_expected for p in phases)
    total_labor_cost = total_hours * hourly_rate
    total_infra = sum(c.monthly_cost * c.months for c in infra_costs)
    total_third_party = sum(c.monthly_cost * c.months for c in third_party_costs)
    grand_total = total_labor_cost + total_infra + total_third_party

    return BudgetSummary(
        phases=phases,
        infra_costs=infra_costs,
        third_party_costs=third_party_costs,
        hourly_rate=hourly_rate,
        total_hours=total_hours,
        total_labor_cost=total_labor_cost,
        total_infra_cost=total_infra,
        total_third_party=total_third_party,
        grand_total=grand_total,
    )


def flag_unverified_prices(budget: BudgetSummary) -> List[str]:
    """Return names of cost items whose price has no verified source URL.

    Checks both infra_costs and third_party_costs.

    Args:
        budget: A BudgetSummary returned by generate_budget_summary.

    Returns:
        List of service names where verified_source is empty or whitespace.
    """
    unverified: List[str] = []
    for cost in budget.infra_costs + budget.third_party_costs:
        if not cost.verified_source.strip():
            unverified.append(cost.service)
    return unverified
