"""Integration tests for ADR-030 Q1 — log-then-reconcile AUTO-TRIGGER compliance.

Design
------
Two hooks write to two JSONL files:

  .cognitive-os/metrics/auto-trigger-events.jsonl
      source=session-wrapup-trigger, event_type=auto_trigger.emitted
      Logged by hooks/session-wrapup-trigger.sh on every regex match.

  .cognitive-os/metrics/skill-invocations.jsonl
      source=skill-invocation-logger, event_type=skill.invoked
      Logged by hooks/skill-invocation-logger.sh on every Skill tool call.

The reconciliation logic: for each AUTO-TRIGGER emission, look for a
skill.invoked event for the *suggested* skill that arrives within
COMPLIANCE_WINDOW_SECS seconds. If found → emission is "honoured".
Uninitiated skill invocations (no prior emission) are not penalised.

The test is **parameterized on the data source** so it can run:
  - In CI against synthetic fixtures written to tmp_path
  - In production against the real .cognitive-os/metrics/ files

To run against the real files:
    pytest tests/integration/test_auto_trigger_honoured.py -v

To override the data root (e.g. in CI with fixture data):
    AUTO_TRIGGER_DATA_ROOT=/some/path pytest ...

The test does NOT hard-fail on low compliance today (we are bootstrapping data).
Below 80% rate it logs a warning. A hard-fail threshold will be added after 2
weeks of data collection.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COMPLIANCE_WINDOW_SECS: float = 60.0

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Allow env override for CI / fixture testing
_DATA_ROOT_ENV = os.environ.get("AUTO_TRIGGER_DATA_ROOT", "")
DEFAULT_DATA_ROOT = Path(_DATA_ROOT_ENV) if _DATA_ROOT_ENV else PROJECT_ROOT / ".cognitive-os" / "metrics"

pytestmark = [pytest.mark.integration]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_events(path: Path, event_type: str) -> list[dict[str, Any]]:
    """Parse a JSONL file and return rows matching *event_type*.

    Tolerates:
    - File does not exist → returns []
    - Malformed lines → skips them silently
    - Unknown extra fields → preserved in dict (MetricEvent schema allows this)
    """
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("event_type") == event_type:
                events.append(row)
    return events


def _parse_ts(ts_str: str) -> float | None:
    """Parse an ISO-8601 timestamp string to a Unix epoch float. Returns None on failure."""
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def _compute_compliance(
    emissions: list[dict[str, Any]],
    invocations: list[dict[str, Any]],
    window_secs: float = COMPLIANCE_WINDOW_SECS,
) -> tuple[float, list[dict[str, Any]]]:
    """Return (compliance_rate 0.0..1.0, list_of_ignored_emissions).

    An emission is "honoured" when there is a skill.invoked event for the
    suggested_skill whose timestamp is within [emission_ts, emission_ts + window_secs].

    Emissions whose timestamp cannot be parsed are treated as non-compliant.
    """
    if not emissions:
        return 1.0, []  # vacuously compliant

    honoured = 0
    ignored: list[dict[str, Any]] = []

    for emission in emissions:
        em_ts = _parse_ts(emission.get("timestamp", ""))
        suggested = emission.get("payload", {}).get("suggested_skill", "")

        if em_ts is None:
            ignored.append({**emission, "_reason": "unparseable_timestamp"})
            continue

        deadline = em_ts + window_secs
        found = False
        for inv in invocations:
            inv_ts = _parse_ts(inv.get("timestamp", ""))
            if inv_ts is None:
                continue
            inv_skill = inv.get("payload", {}).get("skill_name", "")
            if inv_ts >= em_ts and inv_ts <= deadline and inv_skill == suggested:
                found = True
                break

        if found:
            honoured += 1
        else:
            ignored.append({**emission, "_reason": "no_matching_invocation_in_window"})

    rate = honoured / len(emissions)
    return rate, ignored


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _make_emission(
    timestamp: str, suggested_skill: str = "session-wrapup", session_id: str = "s1"
) -> dict[str, Any]:
    return {
        "source": "session-wrapup-trigger",
        "event_type": "auto_trigger.emitted",
        "timestamp": timestamp,
        "severity": "info",
        "schema_version": 1,
        "payload": {
            "suggested_skill": suggested_skill,
            "session_id": session_id,
            "prompt_digest": "abcd1234",
            "matched_phrase": "cerremos la sesión",
        },
    }


def _make_invocation(
    timestamp: str, skill_name: str = "session-wrapup", session_id: str = "s1"
) -> dict[str, Any]:
    return {
        "source": "skill-invocation-logger",
        "event_type": "skill.invoked",
        "timestamp": timestamp,
        "severity": "info",
        "schema_version": 1,
        "payload": {
            "skill_name": skill_name,
            "args": "",
            "session_id": session_id,
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def data_root(tmp_path):
    """Return the data root for fixture-based tests.

    Each test that needs injected data should write to:
      data_root / "auto-trigger-events.jsonl"
      data_root / "skill-invocations.jsonl"
    """
    return tmp_path / "metrics"


# ---------------------------------------------------------------------------
# Unit-level helper tests (always run, no real data needed)
# ---------------------------------------------------------------------------


class TestLoadEvents:
    """_load_events helper tests."""

    def test_returns_empty_list_for_missing_file(self, tmp_path):
        path = tmp_path / "nonexistent.jsonl"
        result = _load_events(path, "auto_trigger.emitted")
        assert result == []

    def test_filters_by_event_type(self, tmp_path):
        path = tmp_path / "events.jsonl"
        rows = [
            {"event_type": "auto_trigger.emitted", "timestamp": "2026-01-01T00:00:00+00:00", "payload": {}},
            {"event_type": "skill.invoked", "timestamp": "2026-01-01T00:00:01+00:00", "payload": {}},
            {"event_type": "auto_trigger.emitted", "timestamp": "2026-01-01T00:00:02+00:00", "payload": {}},
        ]
        _write_jsonl(path, rows)
        result = _load_events(path, "auto_trigger.emitted")
        assert len(result) == 2

    def test_skips_malformed_lines(self, tmp_path):
        path = tmp_path / "bad.jsonl"
        path.write_text('{"event_type":"auto_trigger.emitted","timestamp":"2026-01-01T00:00:00+00:00","payload":{}}\nnot-json\n{"event_type":"auto_trigger.emitted","timestamp":"2026-01-01T00:00:01+00:00","payload":{}}\n')
        result = _load_events(path, "auto_trigger.emitted")
        assert len(result) == 2

    def test_empty_file_returns_empty(self, tmp_path):
        path = tmp_path / "empty.jsonl"
        path.write_text("")
        result = _load_events(path, "auto_trigger.emitted")
        assert result == []


class TestComputeCompliance:
    """_compute_compliance helper tests."""

    def test_empty_emissions_returns_vacuous_compliance(self):
        rate, ignored = _compute_compliance([], [])
        assert rate == 1.0
        assert ignored == []

    def test_single_emission_matched_within_window(self):
        emissions = [_make_emission("2026-01-01T10:00:00+00:00")]
        # Invocation 30s after emission — within 60s window
        invocations = [_make_invocation("2026-01-01T10:00:30+00:00")]
        rate, ignored = _compute_compliance(emissions, invocations)
        assert rate == 1.0
        assert ignored == []

    def test_single_emission_not_honoured(self):
        emissions = [_make_emission("2026-01-01T10:00:00+00:00")]
        # No matching invocation
        invocations = []
        rate, ignored = _compute_compliance(emissions, invocations)
        assert rate == 0.0
        assert len(ignored) == 1
        assert ignored[0]["_reason"] == "no_matching_invocation_in_window"

    def test_invocation_after_window_not_compliant(self):
        emissions = [_make_emission("2026-01-01T10:00:00+00:00")]
        # Invocation 61s after emission — just outside 60s window
        invocations = [_make_invocation("2026-01-01T10:01:01+00:00")]
        rate, ignored = _compute_compliance(emissions, invocations, window_secs=60.0)
        assert rate == 0.0
        assert len(ignored) == 1

    def test_invocation_exactly_at_window_edge_is_compliant(self):
        emissions = [_make_emission("2026-01-01T10:00:00+00:00")]
        # Invocation exactly 60s after emission — within window (inclusive)
        invocations = [_make_invocation("2026-01-01T10:01:00+00:00")]
        rate, ignored = _compute_compliance(emissions, invocations, window_secs=60.0)
        assert rate == 1.0

    def test_uninitiated_invocation_not_penalised(self):
        """Skill invocations without a prior emission must not affect compliance rate."""
        emissions = [_make_emission("2026-01-01T10:00:00+00:00")]
        # Matching invocation within window + extra uninitiated invocations
        invocations = [
            _make_invocation("2026-01-01T10:00:30+00:00"),
            _make_invocation("2026-01-01T09:00:00+00:00", skill_name="session-backlog"),
            _make_invocation("2026-01-01T11:00:00+00:00", skill_name="recall-search"),
        ]
        rate, ignored = _compute_compliance(emissions, invocations)
        assert rate == 1.0
        assert ignored == []

    def test_mixed_compliance_computed_correctly(self):
        """2 emissions, 1 honoured → 50% rate."""
        emissions = [
            _make_emission("2026-01-01T10:00:00+00:00"),
            _make_emission("2026-01-01T11:00:00+00:00"),
        ]
        invocations = [
            # Only the first emission is honoured
            _make_invocation("2026-01-01T10:00:20+00:00"),
            # Second emission: invocation is 90s later — outside window
            _make_invocation("2026-01-01T11:01:30+00:00"),
        ]
        rate, ignored = _compute_compliance(emissions, invocations)
        assert abs(rate - 0.5) < 1e-9
        assert len(ignored) == 1

    def test_wrong_skill_name_not_counted(self):
        """Invocation of a different skill does not satisfy the emission."""
        emissions = [_make_emission("2026-01-01T10:00:00+00:00", suggested_skill="session-wrapup")]
        invocations = [_make_invocation("2026-01-01T10:00:10+00:00", skill_name="recall-search")]
        rate, ignored = _compute_compliance(emissions, invocations)
        assert rate == 0.0

    def test_emission_with_unparseable_timestamp_becomes_non_compliant(self):
        bad_emission = {
            **_make_emission("2026-01-01T10:00:00+00:00"),
            "timestamp": "not-a-date",
        }
        rate, ignored = _compute_compliance([bad_emission], [])
        assert rate == 0.0
        assert ignored[0]["_reason"] == "unparseable_timestamp"


# ---------------------------------------------------------------------------
# Fixture-driven integration tests (injected JSONL data)
# ---------------------------------------------------------------------------


class TestAutoTriggerComplianceFromFixtures:
    """Reconciliation tests using synthetic JSONL written to tmp_path."""

    def _paths(self, data_root: Path) -> tuple[Path, Path]:
        return (
            data_root / "auto-trigger-events.jsonl",
            data_root / "skill-invocations.jsonl",
        )

    def test_empty_files_skip_gracefully(self, data_root):
        """Both files empty → no data to audit → test skips or reports vacuous compliance."""
        emissions_path, invocations_path = self._paths(data_root)
        _write_jsonl(emissions_path, [])
        _write_jsonl(invocations_path, [])

        emissions = _load_events(emissions_path, "auto_trigger.emitted")
        invocations = _load_events(invocations_path, "skill.invoked")

        if not emissions:
            pytest.skip("no auto-trigger emissions yet — bootstrapping phase")

    def test_single_emission_compliant(self, data_root):
        """One emission + matching invocation within window → 100% compliance."""
        emissions_path, invocations_path = self._paths(data_root)
        _write_jsonl(emissions_path, [_make_emission("2026-01-01T10:00:00+00:00")])
        _write_jsonl(invocations_path, [_make_invocation("2026-01-01T10:00:45+00:00")])

        emissions = _load_events(emissions_path, "auto_trigger.emitted")
        invocations = _load_events(invocations_path, "skill.invoked")
        rate, ignored = _compute_compliance(emissions, invocations)

        assert rate == 1.0, f"Expected 100% compliance, got {rate:.0%}. Ignored: {ignored}"

    def test_single_emission_non_compliant_reported(self, data_root):
        """One emission without matching invocation → compliance < 100%, event listed."""
        emissions_path, invocations_path = self._paths(data_root)
        _write_jsonl(emissions_path, [_make_emission("2026-01-01T10:00:00+00:00")])
        _write_jsonl(invocations_path, [])

        emissions = _load_events(emissions_path, "auto_trigger.emitted")
        invocations = _load_events(invocations_path, "skill.invoked")
        rate, ignored = _compute_compliance(emissions, invocations)

        assert rate < 1.0
        assert len(ignored) == 1
        assert ignored[0]["event_type"] == "auto_trigger.emitted"

    def test_multiple_emissions_mixed_compliance(self, data_root):
        """3 emissions, 2 honoured → 66.7% compliance rate."""
        emissions_path, invocations_path = self._paths(data_root)
        emissions = [
            _make_emission("2026-01-01T10:00:00+00:00", session_id="s1"),
            _make_emission("2026-01-01T11:00:00+00:00", session_id="s2"),
            _make_emission("2026-01-01T12:00:00+00:00", session_id="s3"),
        ]
        invocations = [
            _make_invocation("2026-01-01T10:00:15+00:00", session_id="s1"),
            _make_invocation("2026-01-01T11:00:59+00:00", session_id="s2"),
            # No invocation for s3 emission → non-compliant
        ]
        _write_jsonl(emissions_path, emissions)
        _write_jsonl(invocations_path, invocations)

        loaded_emissions = _load_events(emissions_path, "auto_trigger.emitted")
        loaded_invocations = _load_events(invocations_path, "skill.invoked")
        rate, ignored = _compute_compliance(loaded_emissions, loaded_invocations)

        assert abs(rate - 2 / 3) < 1e-9
        assert len(ignored) == 1

    def test_invocation_before_emission_not_counted(self, data_root):
        """An invocation that precedes the emission by 1s must not count as compliance."""
        emissions_path, invocations_path = self._paths(data_root)
        _write_jsonl(emissions_path, [_make_emission("2026-01-01T10:00:10+00:00")])
        _write_jsonl(invocations_path, [_make_invocation("2026-01-01T10:00:09+00:00")])

        emissions = _load_events(emissions_path, "auto_trigger.emitted")
        invocations = _load_events(invocations_path, "skill.invoked")
        rate, ignored = _compute_compliance(emissions, invocations)

        assert rate == 0.0

    def test_uninitiated_invocations_not_penalised_in_fixture(self, data_root):
        """Many uninitiated skill calls must not drag down the compliance rate."""
        emissions_path, invocations_path = self._paths(data_root)
        _write_jsonl(emissions_path, [_make_emission("2026-01-01T10:00:00+00:00")])
        # One matching + five uninitiated
        invocations = [
            _make_invocation("2026-01-01T10:00:30+00:00"),  # honours the emission
            _make_invocation("2026-01-01T07:00:00+00:00", skill_name="doc-sync"),
            _make_invocation("2026-01-01T08:00:00+00:00", skill_name="session-backlog"),
            _make_invocation("2026-01-01T09:00:00+00:00", skill_name="resume-tasks"),
            _make_invocation("2026-01-01T13:00:00+00:00", skill_name="session-manager"),
            _make_invocation("2026-01-01T14:00:00+00:00", skill_name="recall-search"),
        ]
        _write_jsonl(invocations_path, invocations)

        emissions = _load_events(emissions_path, "auto_trigger.emitted")
        loaded_invocations = _load_events(invocations_path, "skill.invoked")
        rate, ignored = _compute_compliance(emissions, loaded_invocations)

        assert rate == 1.0
        assert ignored == []

    def test_time_window_edge_61s_not_compliant(self, data_root):
        """Invocation 61s after emission is NOT within the 60s window."""
        emissions_path, invocations_path = self._paths(data_root)
        _write_jsonl(emissions_path, [_make_emission("2026-01-01T10:00:00+00:00")])
        _write_jsonl(invocations_path, [_make_invocation("2026-01-01T10:01:01+00:00")])

        emissions = _load_events(emissions_path, "auto_trigger.emitted")
        invocations = _load_events(invocations_path, "skill.invoked")
        rate, ignored = _compute_compliance(emissions, invocations, window_secs=60.0)

        assert rate == 0.0
        assert len(ignored) == 1


# ---------------------------------------------------------------------------
# Production audit test (reads the REAL metrics files)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_auto_trigger_compliance_rate():
    """Measure: of all AUTO-TRIGGER emissions, how many had a matching
    skill invocation within 60 seconds?

    Reports compliance rate; does NOT hard-fail below a threshold today
    (we are bootstrapping data). Logs a warning if rate < 80%.

    Hard-fail threshold to be tuned after 2 weeks of data accumulation.
    """
    emissions_path = DEFAULT_DATA_ROOT / "auto-trigger-events.jsonl"
    invocations_path = DEFAULT_DATA_ROOT / "skill-invocations.jsonl"

    emissions = _load_events(emissions_path, "auto_trigger.emitted")
    invocations = _load_events(invocations_path, "skill.invoked")

    if not emissions:
        pytest.skip(
            "no auto-trigger emissions found — bootstrapping phase, "
            f"checked {emissions_path}"
        )

    rate, ignored = _compute_compliance(emissions, invocations)

    pct = rate * 100
    total = len(emissions)
    honoured = total - len(ignored)

    report_lines = [
        f"AUTO-TRIGGER compliance: {pct:.1f}% ({honoured}/{total} emissions honoured)",
    ]
    if ignored:
        report_lines.append(f"Non-compliant emissions ({len(ignored)}):")
        for ev in ignored[:10]:  # show at most 10
            ts = ev.get("timestamp", "?")
            skill = ev.get("payload", {}).get("suggested_skill", "?")
            reason = ev.get("_reason", "?")
            report_lines.append(f"  [{ts}] suggested={skill} reason={reason}")
        if len(ignored) > 10:
            report_lines.append(f"  ... and {len(ignored) - 10} more")

    report = "\n".join(report_lines)

    if rate < 0.80:
        # Warn but do not hard-fail during bootstrapping period
        import warnings
        warnings.warn(
            f"AUTO-TRIGGER compliance below 80%: {pct:.1f}%\n{report}",
            UserWarning,
            stacklevel=2,
        )

    # Sanity assertions that always hold regardless of rate
    assert 0.0 <= rate <= 1.0, f"compliance rate out of bounds: {rate}"
    assert honoured >= 0
    assert honoured <= total

    print(f"\n{report}")
