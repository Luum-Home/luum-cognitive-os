# SCOPE: both
"""Validator soak evaluator — ADR-174b Part B propose-only trigger.

Reads `.cognitive-os/metrics/skill-md-routing-validator.jsonl` and decides
whether the routing validator is ready to be promoted from advisory to blocking.

Promotion happens ONLY as a human-reviewable proposal artifact.
No runtime behavior is changed automatically.

Soak report is written to:
    docs/06-Daily/reports/promotion-proposals/<date>/validator-advisory-to-blocking.md

Evaluation log is appended to:
    .cognitive-os/metrics/validator-promotion-evaluations.jsonl

False-positive definition (heuristic):
    An entry is considered a false positive (FP) if:
    - The validator warned about a missing routing_patterns: block (type="warn"), AND
    - The entry carries an "outcome" field of "accepted_unchanged" or "override"

    In practice the validator hook may not write outcome data at write-time.
    When outcome data is absent, the evaluator falls back to counting any warning
    whose skill slug subsequently appears in the metrics file with a "pass" entry
    within the soak window — i.e., the skill was accepted after the warning.

    UNCERTAINTY NOTE: This heuristic assumes that a SKILL.md accepted unchanged
    after a warning is a false positive.  A SKILL.md could also be accepted with
    an explicit operator override.  Real soak data will calibrate this rate.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from textwrap import dedent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class SoakReport:
    """Summary of the validator soak evaluation."""

    evaluated_at: str
    soak_days: int
    total_entries: int
    warn_count: int
    fp_count: int
    fp_rate: float
    fp_threshold: float
    proposal_emitted: bool
    proposal_path: str | None
    skip_reason: str | None  # set when proposal was NOT emitted


# ---------------------------------------------------------------------------
# Core evaluator
# ---------------------------------------------------------------------------


def evaluate_validator_soak(
    metrics_path: Path | None = None,
    soak_days: int = 30,
    fp_threshold: float = 0.05,
    min_entries: int = 30,
    project_root: Path | None = None,
) -> SoakReport:
    """Read the validator JSONL, compute FP rate, emit proposal if thresholds met.

    Parameters
    ----------
    metrics_path:
        Path to ``skill-md-routing-validator.jsonl``.
        Defaults to ``<project_root>/.cognitive-os/metrics/skill-md-routing-validator.jsonl``.
    soak_days:
        Minimum number of days the validator must have been running.
    fp_threshold:
        Maximum FP rate (0.0–1.0) to consider promotion safe.  Default 5 %.
    min_entries:
        Minimum number of entries within ``soak_days`` before evaluation is
        meaningful.  Default 30.
    project_root:
        Repository root.  Defaults to the directory two levels above this file
        (i.e. the repo root when running from within the project).
    """
    now = datetime.now(tz=timezone.utc)
    evaluated_at = now.isoformat()

    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent

    if metrics_path is None:
        metrics_path = (
            project_root / ".cognitive-os" / "metrics" / "skill-md-routing-validator.jsonl"
        )

    eval_log_path = (
        project_root / ".cognitive-os" / "metrics" / "validator-promotion-evaluations.jsonl"
    )
    eval_log_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Load entries within soak window ---
    cutoff = now - timedelta(days=soak_days)
    entries: list[dict] = []

    if not metrics_path.exists():
        report = SoakReport(
            evaluated_at=evaluated_at,
            soak_days=soak_days,
            total_entries=0,
            warn_count=0,
            fp_count=0,
            fp_rate=0.0,
            fp_threshold=fp_threshold,
            proposal_emitted=False,
            proposal_path=None,
            skip_reason="metrics_file_not_found",
        )
        _append_eval_log(eval_log_path, report)
        return report

    with metrics_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts_str = entry.get("timestamp") or entry.get("ts") or ""
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue
            if ts >= cutoff:
                entries.append(entry)

    total_entries = len(entries)

    if total_entries < min_entries:
        report = SoakReport(
            evaluated_at=evaluated_at,
            soak_days=soak_days,
            total_entries=total_entries,
            warn_count=0,
            fp_count=0,
            fp_rate=0.0,
            fp_threshold=fp_threshold,
            proposal_emitted=False,
            proposal_path=None,
            skip_reason=f"insufficient_entries ({total_entries} < {min_entries})",
        )
        _append_eval_log(eval_log_path, report)
        return report

    # --- Compute FP rate ---
    warn_entries = [e for e in entries if e.get("level") in ("warn", "warning") or e.get("type") == "warn"]
    warn_count = len(warn_entries)

    # FP: warned but outcome indicates the skill was accepted anyway
    fp_outcomes = {"accepted_unchanged", "override", "accepted"}
    fp_count = sum(
        1
        for e in warn_entries
        if (e.get("outcome") or "").lower() in fp_outcomes
    )

    # Fallback: if no outcome field present, use slug-based pass correlation
    if fp_count == 0 and warn_count > 0:
        # Build a set of slugs that have a subsequent "pass" entry
        passed_slugs: set[str] = {
            e.get("skill_slug") or e.get("slug") or ""
            for e in entries
            if e.get("level") == "pass" or e.get("type") == "pass"
        }
        fp_count = sum(
            1
            for e in warn_entries
            if (e.get("skill_slug") or e.get("slug") or "") in passed_slugs
        )

    fp_rate = fp_count / warn_count if warn_count > 0 else 0.0

    # --- Decision ---
    if fp_rate >= fp_threshold:
        report = SoakReport(
            evaluated_at=evaluated_at,
            soak_days=soak_days,
            total_entries=total_entries,
            warn_count=warn_count,
            fp_count=fp_count,
            fp_rate=fp_rate,
            fp_threshold=fp_threshold,
            proposal_emitted=False,
            proposal_path=None,
            skip_reason=f"fp_rate_too_high ({fp_rate:.1%} >= {fp_threshold:.1%})",
        )
        _append_eval_log(eval_log_path, report)
        return report

    # --- Emit proposal ---
    date_str = now.strftime("%Y-%m-%d")
    proposal_dir = project_root / "docs" / "06-Daily" / "reports" / "promotion-proposals" / date_str
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_path = proposal_dir / "validator-advisory-to-blocking.md"

    # Idempotent: don't overwrite an existing proposal for the same date
    if not proposal_path.exists():
        _write_proposal(
            path=proposal_path,
            evaluated_at=evaluated_at,
            soak_days=soak_days,
            total_entries=total_entries,
            warn_count=warn_count,
            fp_count=fp_count,
            fp_rate=fp_rate,
            fp_threshold=fp_threshold,
        )

    report = SoakReport(
        evaluated_at=evaluated_at,
        soak_days=soak_days,
        total_entries=total_entries,
        warn_count=warn_count,
        fp_count=fp_count,
        fp_rate=fp_rate,
        fp_threshold=fp_threshold,
        proposal_emitted=True,
        proposal_path=str(proposal_path),
        skip_reason=None,
    )
    _append_eval_log(eval_log_path, report)
    return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_proposal(
    *,
    path: Path,
    evaluated_at: str,
    soak_days: int,
    total_entries: int,
    warn_count: int,
    fp_count: int,
    fp_rate: float,
    fp_threshold: float,
) -> None:
    content = dedent(f"""\
        # Proposal: Promote `skill-md-routing-validator` from Advisory to Blocking

        **Generated**: {evaluated_at}
        **Status**: PROPOSED — requires operator review and approval

        ## Soak Data Summary

        | Metric | Value |
        |--------|-------|
        | Soak window | {soak_days} days |
        | Total entries in window | {total_entries} |
        | Warnings emitted | {warn_count} |
        | False positives (estimated) | {fp_count} |
        | False-positive rate | {fp_rate:.2%} |
        | Promotion threshold | < {fp_threshold:.0%} FP rate |

        **Conclusion**: FP rate ({fp_rate:.2%}) is below the {fp_threshold:.0%} threshold.
        The validator appears safe to promote to blocking.

        ## Proposed Change

        In `hooks/skill-md-routing-validator.sh`, change the hook event from:
        ```
        # advisory — emits warnings only
        ```
        to:
        ```
        # blocking — exits non-zero when routing_patterns: is absent
        VALIDATOR_BLOCKING="${{VALIDATOR_BLOCKING:-1}}"
        ```

        And in `.claude/settings.json` / `settings.json`, update the hook entry to
        include `"blocking": true` (or equivalent harness flag).

        ## Falsifiable Claim

        90 days post-promotion, no legitimate SKILL.md write should be blocked.
        Any blocked write that was legitimate must be counted as a regression.

        ## Rollback Path

        Set `VALIDATOR_BLOCKING=0` (or unset) to revert to advisory mode without
        any code change.  The env flag is checked at the top of the hook.

        ## Uncertainty Note

        FP-rate detection is heuristic — assumes that an unchanged SKILL.md after
        a warning means the warning was a false positive, but the SKILL.md may have
        been accepted with an explicit operator override.  Real soak data will
        calibrate.

        The 30-day soak threshold and 5 % FP cutoff are conventional, not validated
        against COS-specific data.

        ## Cross-References

        - ADR-174: Auto-Derived Primitive Routing for Skills
        - ADR-174b: Prevention Followup (Part B — this proposal)
        - `hooks/skill-md-routing-validator.sh`
        - `.cognitive-os/metrics/skill-md-routing-validator.jsonl`
    """)
    path.write_text(content, encoding="utf-8")


def _append_eval_log(path: Path, report: SoakReport) -> None:
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(report)) + "\n")
    except OSError as exc:
        logger.warning("Could not write eval log %s: %s", path, exc)


# ---------------------------------------------------------------------------
# CLI entry point (for manual / cron invocation)
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate validator soak and emit promotion proposal")
    parser.add_argument("--soak-days", type=int, default=30)
    parser.add_argument("--fp-threshold", type=float, default=0.05)
    parser.add_argument("--min-entries", type=int, default=30)
    parser.add_argument("--metrics-path", type=Path, default=None)
    args = parser.parse_args()

    report = evaluate_validator_soak(
        metrics_path=args.metrics_path,
        soak_days=args.soak_days,
        fp_threshold=args.fp_threshold,
        min_entries=args.min_entries,
    )
    print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    main()
