#!/usr/bin/env python3
# SCOPE: both
"""cos-coverage — Agent Capability Coverage (ACC) metric CLI.

Composes data from:
  - .cognitive-os/metrics/aspirational-audit.jsonl   (REAL/DORMANT/ASPIRATIONAL counts)
  - .cognitive-os/coverage-tiers.json                (tier breakdown A/B/C/D)
  - docs/06-Daily/reports/claim-proof-latest.md               (mapped/unmapped/weak-proof counts)
  - .cognitive-os/metrics/coverage-history.jsonl     (trend vs last snapshot)

Cache: .cognitive-os/runtime/coverage-snapshot.json (TTL 30s) to keep p95 < 300ms.
Daily snapshot appended to .cognitive-os/metrics/coverage-history.jsonl.

Usage:
  python3 scripts/cos_coverage.py          # human summary (default)
  python3 scripts/cos_coverage.py --json   # machine-readable JSON
  python3 scripts/cos_coverage.py --brief  # one-line statusline output
  python3 scripts/cos_coverage.py --refresh # force cache refresh
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter
from pathlib import Path

CACHE_TTL_SECONDS = 30
SNAPSHOT_TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%SZ"


# ── Project root resolution ────────────────────────────────────────────────────

def find_project_dir(hint: str | None = None) -> Path:
    if hint:
        return Path(hint).resolve()
    for env in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        val = os.environ.get(env, "")
        if val:
            return Path(val).resolve()
    # walk up for .git
    candidate = Path.cwd()
    while candidate != candidate.parent:
        if (candidate / ".git").exists():
            return candidate
        candidate = candidate.parent
    return Path.cwd()


# ── Claim-proof data ──────────────────────────────────────────────────────────

def parse_claim_proof(project_dir: Path) -> dict[str, int]:
    """Return {mapped, weak_proof, unmapped} from claim-proof-latest.md."""
    report = project_dir / "docs" / "reports" / "claim-proof-latest.md"
    result = {"mapped": 0, "weak_proof": 0, "unmapped": 0}
    if not report.exists():
        return result
    text = report.read_text(errors="replace")
    patterns = {
        "mapped": r"mapped:\s*(\d+)",
        "weak_proof": r"weak-proof:\s*(\d+)",
        "unmapped": r"unmapped:\s*(\d+)",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            result[key] = int(m.group(1))
    return result


# ── Aspirational-audit counts ─────────────────────────────────────────────────

def parse_audit_counts(project_dir: Path) -> dict[str, int]:
    """Return classification counts from aspirational-audit.jsonl (deduplicated)."""
    audit = project_dir / ".cognitive-os" / "metrics" / "aspirational-audit.jsonl"
    if not audit.exists():
        return {}
    counts: Counter[str] = Counter()
    seen: set[tuple[str, str]] = set()
    with audit.open(errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = record.get("payload", {})
            component = payload.get("component", "")
            classification = payload.get("classification", "UNKNOWN")
            key = (component, classification)
            if key not in seen:
                seen.add(key)
                counts[classification] += 1
    return dict(counts)


# ── Tier breakdown ─────────────────────────────────────────────────────────────

def parse_tier_counts(project_dir: Path) -> dict[str, int]:
    """Return tier counts from coverage-tiers.json if present."""
    tiers_file = project_dir / ".cognitive-os" / "coverage-tiers.json"
    if not tiers_file.exists():
        return {}
    try:
        tiers: dict[str, str] = json.loads(tiers_file.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    counts: Counter[str] = Counter(tiers.values())
    return dict(counts)


# ── Coverage percentage ────────────────────────────────────────────────────────

def compute_coverage_pct(audit_counts: dict[str, int]) -> float:
    """Coverage = REAL / (REAL + DORMANT + ASPIRATIONAL) * 100."""
    real = audit_counts.get("REAL", 0)
    dormant = audit_counts.get("DORMANT", 0)
    aspirational = audit_counts.get("ASPIRATIONAL", 0)
    total = real + dormant + aspirational
    if total == 0:
        return 0.0
    return round(real / total * 100, 1)


# ── History / trend ───────────────────────────────────────────────────────────

def load_last_snapshot(project_dir: Path) -> dict | None:
    """Return last daily snapshot from coverage-history.jsonl, or None."""
    history = project_dir / ".cognitive-os" / "metrics" / "coverage-history.jsonl"
    if not history.exists():
        return None
    last_acc: dict | None = None
    with history.open(errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Accept both pre-existing coverage_measurement events and our own acc_snapshot events
            event_type = record.get("event_type", "")
            if event_type in ("acc_snapshot", "coverage_measurement"):
                last_acc = record
    return last_acc


def compute_trend(current: dict, last: dict | None) -> dict[str, str]:
    """Return trend arrows for coverage_pct, real, dormant."""
    if last is None:
        return {}
    lp = last.get("payload", {})
    trend: dict[str, str] = {}

    def arrow(curr: float, prev: float) -> str:
        if curr > prev:
            return "up"
        if curr < prev:
            return "down"
        return "flat"

    if "coverage_pct" in lp:
        trend["coverage_pct"] = arrow(current["coverage_pct"], lp["coverage_pct"])
    if "real" in lp:
        trend["real"] = arrow(current["real"], lp.get("real", 0))
    if "dormant" in lp:
        trend["dormant"] = arrow(current["dormant"], lp.get("dormant", 0))

    return trend


ARROW_MAP = {"up": "↑", "down": "↓", "flat": "→", "": ""}


def append_daily_snapshot(project_dir: Path, snapshot: dict) -> None:
    """Append a daily acc_snapshot to coverage-history.jsonl if not already done today."""
    history = project_dir / ".cognitive-os" / "metrics" / "coverage-history.jsonl"
    today = time.strftime("%Y-%m-%d", time.gmtime())

    # Check if today's snapshot already exists
    if history.exists():
        with history.open(errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("event_type") == "acc_snapshot":
                    ts = record.get("timestamp", "")
                    if ts.startswith(today):
                        return  # Already wrote today

    history.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": time.strftime(SNAPSHOT_TIMESTAMP_FMT, time.gmtime()),
        "source": "cos-coverage",
        "event_type": "acc_snapshot",
        "payload": snapshot,
    }
    with history.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


# ── Cache management ──────────────────────────────────────────────────────────

def load_cache(project_dir: Path) -> dict | None:
    cache_path = project_dir / ".cognitive-os" / "runtime" / "coverage-snapshot.json"
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    cached_at = data.get("_cached_at", 0)
    if time.time() - cached_at > CACHE_TTL_SECONDS:
        return None
    return data


def write_cache(project_dir: Path, data: dict) -> None:
    cache_path = project_dir / ".cognitive-os" / "runtime" / "coverage-snapshot.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    data["_cached_at"] = time.time()
    cache_path.write_text(json.dumps(data))


# ── Data composition ──────────────────────────────────────────────────────────

def compose_data(project_dir: Path) -> dict:
    """Compose all coverage metrics into a single dict."""
    claim_proof = parse_claim_proof(project_dir)
    audit_counts = parse_audit_counts(project_dir)
    tier_counts = parse_tier_counts(project_dir)
    coverage_pct = compute_coverage_pct(audit_counts)

    snapshot_payload = {
        "coverage_pct": coverage_pct,
        "real": audit_counts.get("REAL", 0),
        "dormant": audit_counts.get("DORMANT", 0),
        "aspirational": audit_counts.get("ASPIRATIONAL", 0),
        "on_demand": audit_counts.get("ON_DEMAND", 0),
        "metadata": audit_counts.get("METADATA", 0),
        "mapped": claim_proof.get("mapped", 0),
        "weak_proof": claim_proof.get("weak_proof", 0),
        "unmapped": claim_proof.get("unmapped", 0),
        "tiers": tier_counts,
    }

    last_snapshot = load_last_snapshot(project_dir)
    trend = compute_trend(snapshot_payload, last_snapshot)

    return {
        "project": str(project_dir),
        "generated_at": time.strftime(SNAPSHOT_TIMESTAMP_FMT, time.gmtime()),
        **snapshot_payload,
        "trend": trend,
    }


# ── Formatters ────────────────────────────────────────────────────────────────

def format_human(data: dict) -> str:
    trend = data.get("trend", {})

    def t(key: str) -> str:
        return ARROW_MAP.get(trend.get(key, ""), "")

    lines = [
        f"Agent Capability Coverage (ACC)  {data.get('generated_at', '')}",
        "",
        f"  Coverage:   {data['coverage_pct']}%{t('coverage_pct')}",
        "",
        "  Component classifications:",
        f"    REAL:         {data['real']:>6}{t('real')}",
        f"    DORMANT:      {data['dormant']:>6}{t('dormant')}",
        f"    ASPIRATIONAL: {data['aspirational']:>6}",
        f"    ON_DEMAND:    {data['on_demand']:>6}",
        f"    METADATA:     {data['metadata']:>6}",
        "",
        "  Claim-proof audit:",
        f"    Mapped:       {data['mapped']:>6}",
        f"    Weak-proof:   {data['weak_proof']:>6}",
        f"    Unmapped:     {data['unmapped']:>6}",
    ]

    tiers = data.get("tiers", {})
    if tiers:
        lines.append("")
        lines.append("  Dormant/Aspirational tiers (from coverage-tiers.json):")
        for tier in ("A", "B", "C", "D"):
            label = {
                "A": "Safety-critical",
                "B": "Infrastructure",
                "C": "Advisory/feature-gated",
                "D": "Skills+rules metadata",
            }.get(tier, tier)
            count = tiers.get(tier, 0)
            lines.append(f"    Tier {tier} ({label}): {count}")

    if trend:
        lines.append("")
        arrows = [f"{k} {ARROW_MAP[v]}" for k, v in trend.items() if v in ("up", "down")]
        if arrows:
            lines.append(f"  Trend vs last snapshot: {', '.join(arrows)}")

    return "\n".join(lines)


def format_brief(data: dict) -> str:
    """One-line output for statusline: ACC: 85% | REAL: 1860 DORM: 1393"""
    pct = data["coverage_pct"]
    real = data["real"]
    dorm = data["dormant"]
    trend = data.get("trend", {})
    pct_arrow = ARROW_MAP.get(trend.get("coverage_pct", ""), "")
    return f"ACC: {pct}%{pct_arrow} | REAL: {real} DORM: {dorm}"


def format_json(data: dict) -> str:
    # Remove internal cache field before output
    out = {k: v for k, v in data.items() if not k.startswith("_")}
    return json.dumps(out, indent=2)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show Agent Capability Coverage (ACC) metrics."
    )
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Output as JSON for machine consumption.")
    parser.add_argument("--brief", action="store_true",
                        help="One-line output for statusline integration.")
    parser.add_argument("--refresh", action="store_true",
                        help="Force cache refresh (ignore TTL).")
    parser.add_argument("--project-dir", default=None,
                        help="Project root directory.")
    args = parser.parse_args()

    project_dir = find_project_dir(args.project_dir)

    # Try cache first (unless refresh requested)
    data: dict | None = None
    if not args.refresh:
        data = load_cache(project_dir)

    if data is None:
        data = compose_data(project_dir)
        write_cache(project_dir, data)
        # Append daily snapshot for trend history
        snapshot_payload = {
            k: data[k]
            for k in (
                "coverage_pct", "real", "dormant", "aspirational",
                "on_demand", "metadata", "mapped", "weak_proof", "unmapped", "tiers",
            )
            if k in data
        }
        append_daily_snapshot(project_dir, snapshot_payload)

    if args.json_out:
        print(format_json(data))
    elif args.brief:
        print(format_brief(data))
    else:
        print(format_human(data))


if __name__ == "__main__":
    main()
