"""AUDIT: decision tracking convention — ADR-069 §5b regression guard.

ROOT CAUSE: ADR-069 §5 said decisions persist via "engram observation OR new ADR".
The OR ambiguity meant nobody created `decision/<topic>` observations when shipping
implementations. /decision-triage couldn't see decisions as ANSWERED, so all 33
decisions stayed PENDING indefinitely — causing false-critical alerts.

FIX (2026-04-27): ADR-069 §5b now REQUIRES calling lib/decision_tracker.record_decision()
whenever an operator accepts a recommendation. This test FAILS if:
  - A research report has a Decision Points / Open Questions section, AND
  - The report is > 7 days old (past the active triage window), AND
  - No `decision/<topic_key>` engram observation exists for it, AND
  - The decision is not tagged `decision-deferred: <reason>`

This test would have caught the original 33-fake-criticals bug if it had run weekly.
"""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = REPO / "docs" / "06-Daily" / "reports"

# Same patterns as decision_triage.py (keep in sync)
DECISION_SECTION_PATTERNS = [
    re.compile(r"^##\s+open\s+questions?\s*(?:for\s+operator)?$", re.IGNORECASE),
    re.compile(r"^##\s+decision\s+points?(?:\s*\(operator\s+answers?\s+needed\))?$", re.IGNORECASE),
    re.compile(r"^##\s+operator\s+decisions?\s+pending$", re.IGNORECASE),
    re.compile(r"^##\s+decisions?\s+for\s+operator$", re.IGNORECASE),
]

DEFERRED_PATTERN = re.compile(r"decision-deferred:\s*(.+)", re.IGNORECASE)

TRIAGE_WINDOW_DAYS = 7  # Reports < 7 days old are in active triage; skip check


def _file_age_days(path: Path) -> float:
    try:
        mtime = path.stat().st_mtime
        return (datetime.now(timezone.utc).timestamp() - mtime) / 86400
    except OSError:
        return 999.0


def _engram_search(query: str, timeout: int = 5) -> str | None:
    """Query engram CLI for a topic key. Returns stdout text or None."""
    try:
        result = subprocess.run(
            ["engram", "search", query],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception:
        return None


def _engram_available() -> bool:
    """Probe whether the engram CLI is accessible."""
    try:
        result = subprocess.run(
            ["engram", "search", "probe-test-ping"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return result.returncode == 0
    except Exception:
        return False


def _has_decision_section(text: str) -> bool:
    for line in text.splitlines():
        for pat in DECISION_SECTION_PATTERNS:
            if pat.match(line.strip()):
                return True
    return False


def _infer_topic_slug(report_path: Path) -> str:
    """Derive a topic slug from the report filename (same logic as decision_triage.py)."""
    stem = report_path.stem  # e.g. "cos-init-migration-2026-04-24"
    # Strip trailing date if present
    slug = re.sub(r"-\d{4}-\d{2}-\d{2}$", "", stem)
    return slug


@pytest.mark.audit
@pytest.mark.requires_engram
def test_old_decision_reports_have_engram_observations() -> None:
    """Every research report >7 days old with a Decision Points section must have
    a corresponding `decision/<topic_key>` engram observation marking it ANSWERED,
    or be explicitly tagged `decision-deferred: <reason>`.

    This test FAILS when the ADR-069 §5 OR ambiguity recurs — i.e., someone accepts
    a decision verbally but doesn't call lib/decision_tracker.record_decision().
    """
    if not _engram_available():
        pytest.skip("engram CLI not available — run with engram running (PID check)")

    if not REPORTS_DIR.exists():
        pytest.skip(f"reports dir {REPORTS_DIR} does not exist")

    violations: list[dict] = []

    for report_file in sorted(REPORTS_DIR.glob("*.md")):
        age_days = _file_age_days(report_file)
        if age_days <= TRIAGE_WINDOW_DAYS:
            continue  # In active triage window — skip

        try:
            text = report_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        if not _has_decision_section(text):
            continue  # No decision section — skip

        # Check for explicit deferred annotation
        if DEFERRED_PATTERN.search(text):
            continue  # Explicitly deferred — skip

        # Infer topic slug and check engram
        slug = _infer_topic_slug(report_file)
        topic_key = f"decision/{slug}"
        result = _engram_search(topic_key)

        if result is None or "answered" not in result.lower():
            violations.append({
                "file": str(report_file.relative_to(REPO)),
                "age_days": round(age_days, 1),
                "topic_key": topic_key,
            })

    assert not violations, (
        f"Found {len(violations)} research report(s) with Decision Points sections "
        f"that are > {TRIAGE_WINDOW_DAYS} days old but have no corresponding "
        f"`decision/<topic>` engram observation. This is the ADR-069 §5b anti-pattern "
        f"that caused /decision-triage to show 33 false-critical decisions. "
        f"Fix: call `lib/decision_tracker.record_decision(topic_key, decision_text)` "
        f"for each accepted decision. Or tag the decision with "
        f"`<!-- decision-deferred: <reason> -->` to explicitly defer. "
        f"Violations (first 5): {violations[:5]}"
    )


@pytest.mark.audit
def test_decision_tracker_module_importable() -> None:
    """lib/decision_tracker.py must be importable (validates Fix 2 didn't break imports)."""
    try:
        import importlib.util  # noqa: PLC0415 (test-only import)
        spec = importlib.util.spec_from_file_location(
            "decision_tracker",
            REPO / "lib" / "decision_tracker.py",
        )
        assert spec is not None, "Could not find spec for lib/decision_tracker.py"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        assert hasattr(mod, "record_decision"), (
            "lib/decision_tracker.py must export record_decision()"
        )
        assert hasattr(mod, "mark_answered_by_slug"), (
            "lib/decision_tracker.py must export mark_answered_by_slug()"
        )
    except ImportError as exc:
        pytest.fail(f"lib/decision_tracker.py import failed: {exc}")


@pytest.mark.audit
def test_decision_triage_has_mark_answered_arg() -> None:
    """scripts/decision_triage.py must expose --mark-answered argument.

    This is Fix 2: the arg was missing, so there was no CLI path to record an
    answered decision from a shell script or human operator.
    """
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415

    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "decision_triage.py"), "--help"],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=REPO,
    )
    # argparse --help exits with code 0
    help_text = result.stdout + result.stderr  # argparse may write to either
    assert "--mark-answered" in help_text, (
        "scripts/decision_triage.py is missing --mark-answered argument. "
        "This is Fix 2 for the ADR-069 §5b convention violation. "
        "Add: parser.add_argument('--mark-answered', metavar='SLUG', ...) "
        f"Help output: {help_text[:300]}"
    )
