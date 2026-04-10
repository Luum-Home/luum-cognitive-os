"""Unit tests for lib/budget_calculator.py."""

import pytest

from lib.budget_calculator import (
    BudgetSummary,
    InfraCost,
    PhaseEstimate,
    estimate_phase_hours,
    flag_unverified_prices,
    generate_budget_summary,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# D1: estimate_phase_hours returns positive and internally consistent hours
# ---------------------------------------------------------------------------


class TestEstimatePhaseHours:
    def test_estimate_phase_hours_returns_positive(self):
        """D1 — hours_expected > 0 and min <= expected <= max."""
        result = estimate_phase_hours("context-analysis", "medium", team_size=1)

        assert isinstance(result, PhaseEstimate)
        assert result.hours_expected > 0, "hours_expected must be positive"
        assert result.hours_min <= result.hours_expected, (
            "hours_min must not exceed hours_expected"
        )
        assert result.hours_expected <= result.hours_max, (
            "hours_expected must not exceed hours_max"
        )

    def test_estimate_phase_hours_stores_inputs(self):
        """Returned PhaseEstimate reflects the requested phase / complexity / team."""
        result = estimate_phase_hours("architecture", "high", team_size=2)

        assert result.name == "architecture"
        assert result.complexity == "high"
        assert result.team_size == 2

    def test_estimate_phase_hours_team_size_reduces_hours(self):
        """Larger team_size produces fewer expected hours."""
        single = estimate_phase_hours("architecture", "medium", team_size=1)
        team = estimate_phase_hours("architecture", "medium", team_size=4)

        assert team.hours_expected < single.hours_expected, (
            "4-person team should finish faster than 1 person"
        )

    def test_estimate_phase_hours_invalid_team_size_raises(self):
        """team_size < 1 must raise ValueError."""
        with pytest.raises(ValueError):
            estimate_phase_hours("architecture", "low", team_size=0)

    def test_estimate_phase_hours_unknown_phase_raises(self):
        """Unknown (phase, complexity) pair must raise KeyError."""
        with pytest.raises(KeyError):
            estimate_phase_hours("nonexistent-phase", "medium")

    def test_estimate_phase_hours_all_complexity_levels(self):
        """Low / medium / high escalate monotonically for the same phase."""
        low = estimate_phase_hours("documentation", "low")
        med = estimate_phase_hours("documentation", "medium")
        high = estimate_phase_hours("documentation", "high")

        assert low.hours_expected < med.hours_expected < high.hours_expected


# ---------------------------------------------------------------------------
# D2: generate_budget_summary — math is correct
# ---------------------------------------------------------------------------


class TestGenerateBudgetSummary:
    def _make_summary(self) -> BudgetSummary:
        phases = [
            estimate_phase_hours("context-analysis", "low"),   # 6h expected
            estimate_phase_hours("architecture", "low"),        # 12h expected
            estimate_phase_hours("documentation", "low"),       # 3h expected
        ]
        infra = [InfraCost("supabase", 25.0, 3)]
        third_party: list[InfraCost] = []
        return generate_budget_summary(phases, infra, third_party, hourly_rate=150.0)

    def test_budget_summary_math(self):
        """D2 — grand_total equals labor + infra + third_party."""
        summary = self._make_summary()

        expected_labor = summary.total_hours * 150.0
        expected_infra = 25.0 * 3         # 75
        expected_third_party = 0.0
        expected_grand = expected_labor + expected_infra + expected_third_party

        assert pytest.approx(summary.total_labor_cost) == expected_labor
        assert pytest.approx(summary.total_infra_cost) == expected_infra
        assert pytest.approx(summary.total_third_party) == expected_third_party
        assert pytest.approx(summary.grand_total) == expected_grand

    def test_budget_summary_total_hours(self):
        """total_hours equals sum of phase hours_expected."""
        phases = [
            estimate_phase_hours("context-analysis", "medium"),
            estimate_phase_hours("security-review", "low"),
        ]
        summary = generate_budget_summary(phases, [], [], hourly_rate=100.0)

        expected = sum(p.hours_expected for p in phases)
        assert pytest.approx(summary.total_hours) == expected

    def test_budget_summary_preserves_costs(self):
        """InfraCost and third-party items are stored on the summary."""
        infra = [InfraCost("aws", 50.0, 12, "https://aws.amazon.com/pricing")]
        third = [InfraCost("stripe", 0.0, 1)]
        phases = [estimate_phase_hours("documentation", "low")]
        summary = generate_budget_summary(phases, infra, third, hourly_rate=100.0)

        assert summary.infra_costs == infra
        assert summary.third_party_costs == third

    def test_budget_summary_no_costs(self):
        """Zero costs still produce a valid summary."""
        phases = [estimate_phase_hours("documentation", "low")]
        summary = generate_budget_summary(phases, [], [], hourly_rate=200.0)

        assert summary.total_infra_cost == 0.0
        assert summary.total_third_party == 0.0
        assert pytest.approx(summary.grand_total) == summary.total_labor_cost

    def test_budget_summary_multiple_infra_items(self):
        """total_infra_cost sums across all InfraCost items."""
        infra = [
            InfraCost("supabase", 25.0, 3),
            InfraCost("vercel", 20.0, 3),
        ]
        phases = [estimate_phase_hours("documentation", "low")]
        summary = generate_budget_summary(phases, infra, [], hourly_rate=100.0)

        assert pytest.approx(summary.total_infra_cost) == 25.0 * 3 + 20.0 * 3


# ---------------------------------------------------------------------------
# D3: flag_unverified_prices
# ---------------------------------------------------------------------------


class TestFlagUnverifiedPrices:
    def test_flag_unverified_prices(self):
        """D3 — only services with empty verified_source are returned."""
        infra = [
            InfraCost("supabase", 25.0, 3, verified_source="https://supabase.com/pricing"),
            InfraCost("vercel", 20.0, 3, verified_source=""),
        ]
        phases = [estimate_phase_hours("documentation", "low")]
        summary = generate_budget_summary(phases, infra, [], hourly_rate=100.0)

        unverified = flag_unverified_prices(summary)

        assert "vercel" in unverified
        assert "supabase" not in unverified

    def test_flag_unverified_prices_none_missing(self):
        """Returns empty list when all costs have verified sources."""
        infra = [
            InfraCost("aws", 50.0, 1, verified_source="https://aws.amazon.com/pricing"),
        ]
        third = [
            InfraCost("stripe", 0.0, 1, verified_source="https://stripe.com/pricing"),
        ]
        phases = [estimate_phase_hours("documentation", "low")]
        summary = generate_budget_summary(phases, infra, third, hourly_rate=100.0)

        assert flag_unverified_prices(summary) == []

    def test_flag_unverified_prices_checks_third_party(self):
        """third_party_costs without verified_source are also flagged."""
        third = [
            InfraCost("sendgrid", 15.0, 6, verified_source=""),
        ]
        phases = [estimate_phase_hours("documentation", "low")]
        summary = generate_budget_summary(phases, [], third, hourly_rate=100.0)

        assert "sendgrid" in flag_unverified_prices(summary)

    def test_flag_unverified_prices_whitespace_counts_as_empty(self):
        """Whitespace-only verified_source should be treated as unverified."""
        infra = [InfraCost("cloudflare", 5.0, 12, verified_source="   ")]
        phases = [estimate_phase_hours("documentation", "low")]
        summary = generate_budget_summary(phases, infra, [], hourly_rate=100.0)

        assert "cloudflare" in flag_unverified_prices(summary)
