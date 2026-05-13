"""SessionStart banner extension for telemetry findings (ADR-304 Slice 2).

Reads `.cognitive-os/metrics/telemetry-snapshot.yaml` and renders the top-N
highest-severity findings as a stderr banner. Silent if snapshot is missing
or older than `max_age_hours`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import yaml

SEVERITY_RANK = {"block": 0, "error": 1, "warn": 2, "info": 3}


def _parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _format_breach_line(idx: int, f: dict) -> str:
    slo_id = f.get("slo_id", "unknown")
    value = f.get("metric_value")
    target = f.get("target")
    comparator = f.get("target_comparator", "<")
    code = f.get("code", "")
    if code == "telemetry-self-tuning-proposal":
        msg = f.get("message", "self-tuning proposal")
        return f"  {idx}. [proposal] {slo_id}: {msg}"
    if code == "telemetry-stream-missing":
        return f"  {idx}. [info] {slo_id}: source stream missing"
    if value is None or target is None:
        return f"  {idx}. {slo_id}: breach (no measurement)"
    try:
        value_f = float(value)
        target_f = float(target)
        if comparator == "<":
            ratio = (value_f - target_f) / target_f if target_f else 0.0
            pct = f"breach {ratio * 100:.0f}%"
        else:
            ratio = (target_f - value_f) / target_f if target_f else 0.0
            pct = f"shortfall {ratio * 100:.0f}%"
    except (TypeError, ValueError, ZeroDivisionError):
        pct = "breach"
    return (
        f"  {idx}. {slo_id}: {value} (target {comparator} {target}, {pct})"
    )


def render_banner(
    snapshot_path: Path,
    *,
    top_n: int = 3,
    max_age_hours: float = 2.0,
    now: datetime | None = None,
) -> str:
    """Return banner text or empty string.

    Silent when:
      - snapshot file missing
      - snapshot older than max_age_hours
      - zero non-info findings (still silent — no noise on clean runs)
    """
    if not snapshot_path.exists():
        return ""
    try:
        with snapshot_path.open("r", encoding="utf-8") as fh:
            snapshot = yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError):
        return ""

    generated_at = _parse_iso(snapshot.get("generated_at", ""))
    if generated_at is None:
        return ""
    now = now or datetime.now(timezone.utc)
    if now - generated_at > timedelta(hours=max_age_hours):
        return ""

    findings: Iterable[dict] = snapshot.get("findings") or []
    # Show breaches + proposals; suppress info-only stream_missing.
    actionable = [
        f for f in findings if f.get("code") != "telemetry-stream-missing"
    ]
    if not actionable:
        return ""

    actionable.sort(
        key=lambda f: (
            SEVERITY_RANK.get(f.get("severity", "info"), 99),
            f.get("slo_id", ""),
        )
    )
    top = actionable[:top_n]

    lines = ["", "⚠️ Performance findings (latest hourly aggregation):"]
    for idx, f in enumerate(top, start=1):
        lines.append(_format_breach_line(idx, f))
    lines.append(
        "Run `scripts/cos-telemetry-aggregate --snapshot` for full report."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=Path(".cognitive-os/metrics/telemetry-snapshot.yaml"),
    )
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument("--max-age-hours", type=float, default=2.0)
    args = parser.parse_args()
    banner = render_banner(
        args.snapshot, top_n=args.top, max_age_hours=args.max_age_hours
    )
    if banner:
        sys.stderr.write(banner + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
