#!/usr/bin/env python3
"""Automated validation harness for tier_filter: [0] decision.

Replaces the 30-min human session requirement from stage2-expansion-baseline.md
by replaying real session transcripts through both tier_filter configs and
measuring the delta in unexpanded_keys (rule expansion misses).

Usage:
    python3 scripts/validate_tier_filter.py --approach=replay --n=30 \
        --output=docs/06-Daily/measurements/tier-filter-validation-2026-05-01.json

CLI flags:
    --approach   replay (default) | synthetic
    --n          target sample size (default 30)
    --output     path to write JSON report
    --dry-run    parse and wire without executing statistical tests
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from lib.ref_key_loader import expand, find_ref_keys  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def _resolve_session_dir() -> Path:
    """Derive the Claude Code project-key for this repo without hardcoding paths.

    Claude Code stores per-project sessions under
    ``~/.claude/projects/<slug>`` where ``<slug>`` is the absolute path of
    the project directory with ``/`` replaced by ``-`` (and a leading ``-``).
    Computing it from the runtime project root keeps this script portable —
    no operator-specific home path is committed.
    """
    override = os.environ.get("COS_SESSION_DIR")
    if override:
        return Path(override).expanduser()
    slug = "-" + str(_PROJECT_ROOT).replace("/", "-")
    return Path("~/.claude/projects").expanduser() / slug


_SESSION_DIR = _resolve_session_dir()

_LEARNINGS_LOG = _PROJECT_ROOT / ".cognitive-os" / "metrics" / "session-learnings.jsonl"

# Config A = current production setting
TIER_FILTER_A: set[int] = {0, 1}   # label: "A=[0,1]"
# Config B = candidate setting (saves ~35K tokens per delegation)
TIER_FILTER_B: set[int] = {0}      # label: "B=[0]"

# Revert threshold from runbook (2× baseline)
BASELINE_RATE = 0.445
REVERT_THRESHOLD = 0.890

# Synthetic seed prompts that exercise Tier 1 rules
_SYNTHETIC_SEEDS = [
    # Tier 1: blast-radius, scope-proportionality, decomposition, impact-analysis
    "Perform a cross-service refactor extracting shared RateLimiter from svc-auth and svc-orders into lib/rate-limiter. Follow [`blast-radius`] and [`decomposition`] rules.",
    # Tier 1: model-routing, token-economy, cost-prediction
    "Route this agent delegation: complex debugging task. Apply [`model-routing`] and [`token-economy`] to select the right model and estimate cost.",
    # Tier 1: clarification-gate, scope-creep-detection, prompt-quality
    "Review this PR: changes 47 files across 3 services. Apply [`clarification-gate`] before starting and [`scope-creep-detection`] throughout.",
    # Tier 1: context-management, result-management, response-compression
    "Summarize the last 200 messages in context. Use [`context-management`] rules to decide what to drop and [`result-management`] for output size.",
    # Tier 1: auto-rollback, crash-recovery, error-learning
    "A deploy just failed mid-migration. Apply [`auto-rollback`] protocol, then document in [`error-learning`] format.",
    # Tier 1: confidence-gate, anti-hallucination, assumption-tracking
    "Verify that the new auth module is complete. Apply [`confidence-gate`] — report unknowns explicitly with [`assumption-tracking`].",
    # Tier 1: agent-security, credential-management, confidentiality-protection
    "An agent needs access to the production DB. Apply [`agent-security`] TTL policy and [`credential-management`] rules.",
    # Tier 1: rate-limiting, rate-limit-protection, non-blocking-retry
    "The LLM API is rate-limited. Apply [`rate-limiting`] and [`rate-limit-protection`] — show the non-blocking retry approach.",
    # Tier 1: audit-trail, agent-identity, content-policy
    "Log all agent actions for the past session. Follow [`audit-trail`] and [`agent-identity`] rules to produce a structured log.",
    # Tier 1: blast-radius (again, different angle) + model-directive
    "Apply a schema migration across 5 microservices. Assess [`blast-radius`] first. Use [`model-directive`] to pick the right model.",
    # Tier 0 only (control — should show zero diff between A and B)
    "Fix a typo in README.md. Apply [`acceptance-criteria`] and [`trust-score`].",
    "Add a unit test for the login function. Follow [`definition-of-done`] and [`agent-quality`].",
    "Review the last commit. Use [`trust-score`] to assess confidence in the changes.",
    "Write a simple bash one-liner to count lines. Apply [`agent-escalation`] rules if stuck.",
    "Summarize the task requirements. Follow [`closed-loop-prompts`] format.",
]


# ---------------------------------------------------------------------------
# Core: measure unexpanded_keys for a prompt under both configs
# ---------------------------------------------------------------------------

def measure_prompt(text: str) -> dict[str, Any]:
    """Return expansion metrics for a single prompt under both tier configs."""
    def _run(tf: Optional[set[int]]) -> dict[str, Any]:
        expanded = expand(text, tier_filter=tf)
        raw_keys = find_ref_keys(text)
        expanded_keys = find_ref_keys(expanded)
        missed = set(expanded_keys)
        resolved = set(raw_keys) - missed
        return {
            "unexpanded_keys": len(expanded_keys),
            "total_ref_keys": len(raw_keys),
            "resolved_keys": len(resolved),
            "unexpanded_key_names": sorted(expanded_keys),
        }

    return {
        "config_a": _run(TIER_FILTER_A),
        "config_b": _run(TIER_FILTER_B),
    }


# ---------------------------------------------------------------------------
# Replay approach: extract prompts from session transcripts
# ---------------------------------------------------------------------------

def _extract_prompts_from_session(path: Path, max_prompts: int = 3) -> list[str]:
    """Extract user-turn content from a Claude session JSONL file."""
    prompts: list[str] = []
    try:
        for line in path.open(errors="replace"):
            if len(prompts) >= max_prompts:
                break
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "user":
                continue
            msg = obj.get("message", {})
            if not isinstance(msg, dict):
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                # Extract text blocks
                parts = [
                    c.get("text", "")
                    for c in content
                    if isinstance(c, dict) and c.get("type") == "text"
                ]
                content = "\n".join(p for p in parts if p)
            if not isinstance(content, str):
                continue
            text = content.strip()
            # Only keep prompts that contain ref-key markers (relevant to expansion)
            if text and find_ref_keys(text):
                prompts.append(text)
    except Exception:
        pass
    return prompts


def collect_replay_prompts(n: int) -> list[dict[str, Any]]:
    """Collect up to n prompts from real session transcripts."""
    if not _SESSION_DIR.exists():
        return []

    files = sorted(
        [f for f in _SESSION_DIR.iterdir() if f.suffix == ".jsonl"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    trials: list[dict[str, Any]] = []
    for fpath in files:
        if len(trials) >= n:
            break
        prompts = _extract_prompts_from_session(fpath, max_prompts=3)
        for p in prompts:
            if len(trials) >= n:
                break
            trials.append({
                "source": "replay",
                "session_file": fpath.name,
                "prompt_preview": p[:120],
                **measure_prompt(p),
            })
    return trials


# ---------------------------------------------------------------------------
# Synthetic approach: use fixed seed prompts
# ---------------------------------------------------------------------------

def collect_synthetic_prompts(n: int) -> list[dict[str, Any]]:
    """Run synthetic seed prompts through both configs (no LLM calls needed)."""
    seeds = (_SYNTHETIC_SEEDS * math.ceil(n / len(_SYNTHETIC_SEEDS)))[:n]
    trials: list[dict[str, Any]] = []
    for i, seed in enumerate(seeds):
        trials.append({
            "source": "synthetic",
            "seed_index": i % len(_SYNTHETIC_SEEDS),
            "prompt_preview": seed[:120],
            **measure_prompt(seed),
        })
    return trials


# ---------------------------------------------------------------------------
# Statistics: Wilcoxon signed-rank test (non-parametric, paired)
# ---------------------------------------------------------------------------

def _sign_rank(diffs: list[float]) -> tuple[float, str]:
    """Wilcoxon signed-rank test. Returns (W_statistic, interpretation)."""
    nonzero = [(abs(d), 1 if d > 0 else -1) for d in diffs if d != 0]
    if not nonzero:
        return 0.0, "all_tied"

    ranked = sorted(nonzero, key=lambda x: x[0])
    w_plus = sum(
        (i + 1) for i, (_, sign) in enumerate(ranked) if sign > 0
    )
    w_minus = sum(
        (i + 1) for i, (_, sign) in enumerate(ranked) if sign < 0
    )
    n = len(ranked)
    w = min(w_plus, w_minus)

    # Normal approximation (valid for n >= 10)
    if n < 10:
        return w, "insufficient_n_for_normal_approx"

    mean_w = n * (n + 1) / 4
    std_w = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = abs((w - mean_w) / std_w) if std_w > 0 else 0
    # Two-tailed p-value via standard normal approximation
    # P(Z > z) ≈ erfc(z/sqrt(2))/2 — use math.erfc
    p_value = math.erfc(z / math.sqrt(2))
    return w, f"z={z:.3f} p={p_value:.4f}"


def compute_statistics(trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate trial results and run statistical comparison."""
    a_unexpanded = [t["config_a"]["unexpanded_keys"] for t in trials]
    b_unexpanded = [t["config_b"]["unexpanded_keys"] for t in trials]

    diffs = [b - a for a, b in zip(a_unexpanded, b_unexpanded)]

    n = len(trials)
    mean_a = sum(a_unexpanded) / n if n else 0
    mean_b = sum(b_unexpanded) / n if n else 0
    mean_diff = sum(diffs) / n if n else 0

    # Count prompts where B leaves MORE keys unexpanded than A
    regressions = sum(1 for d in diffs if d > 0)
    neutral = sum(1 for d in diffs if d == 0)
    improvements = sum(1 for d in diffs if d < 0)

    w_stat, stat_note = _sign_rank(diffs)

    # Derive skills_failed proxy from session-learnings (last 7 days)
    skills_failed_rate = _compute_skills_failed_rate()

    return {
        "n_trials": n,
        "config_a_label": "tier_filter=[0,1]",
        "config_b_label": "tier_filter=[0]",
        "mean_unexpanded_keys_a": round(mean_a, 3),
        "mean_unexpanded_keys_b": round(mean_b, 3),
        "mean_delta_b_minus_a": round(mean_diff, 3),
        "trials_b_worse": regressions,
        "trials_neutral": neutral,
        "trials_b_better": improvements,
        "wilcoxon_w": w_stat,
        "wilcoxon_note": stat_note,
        "baseline_skills_failed_rate": BASELINE_RATE,
        "revert_threshold": REVERT_THRESHOLD,
        "observed_skills_failed_rate": skills_failed_rate,
    }


def _compute_skills_failed_rate() -> Optional[float]:
    """Read session-learnings.jsonl and compute skills_failed/session for last 7 days."""
    if not _LEARNINGS_LOG.exists():
        return None
    from datetime import timedelta
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=7)
    ).isoformat()
    sessions, failures = 0, 0
    try:
        for line in _LEARNINGS_LOG.open():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("timestamp", "") >= cutoff:
                sessions += 1
                failures += obj.get("skills_failed", 0)
    except Exception:
        return None
    return round(failures / sessions, 4) if sessions else 0.0


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------

def make_recommendation(stats: dict[str, Any]) -> dict[str, Any]:
    """Produce FLIP / KEEP / NEEDS-MORE-DATA recommendation."""
    n = stats["n_trials"]
    mean_diff = stats["mean_delta_b_minus_a"]
    regressions = stats["trials_b_worse"]
    regression_rate = regressions / n if n else 0
    observed_rate = stats["observed_skills_failed_rate"]
    threshold = stats["revert_threshold"]

    # Primary gate: observed live skills_failed rate
    live_gate_pass = (observed_rate is not None and observed_rate <= threshold)
    live_gate_note = (
        f"observed_rate={observed_rate} <= threshold={threshold}"
        if live_gate_pass
        else f"observed_rate={observed_rate} > threshold={threshold}"
    )

    # Secondary gate: expansion regression rate
    # <30% = FLIP safe; 30-50% = borderline/KEEP; >50% = definite KEEP
    expansion_gate_pass = regression_rate < 0.30
    expansion_high_risk = regression_rate >= 0.50  # majority of tasks regress

    # Tertiary: mean delta magnitude (≥3 keys = strong Tier-1 dependency)
    high_expansion_risk = mean_diff >= 3.0

    if n < 15:
        recommendation = "NEEDS-MORE-DATA"
        rationale = f"Only {n} trials collected; minimum 15 required for statistical validity."
    elif not live_gate_pass:
        recommendation = "KEEP"
        rationale = (
            f"Live skills_failed rate ({observed_rate:.3f}) exceeds 2× baseline "
            f"({threshold}). Keep tier_filter=[0,1]. {live_gate_note}. "
            f"Expansion regression in {regressions}/{n} trials."
        )
    elif expansion_high_risk:
        # >50% of prompts regress under [0] — strong signal to keep [0,1]
        recommendation = "KEEP"
        rationale = (
            f"Expansion regression in {regressions}/{n} trials ({regression_rate:.0%}) — "
            f"majority of sampled tasks leave Tier-1 rules unexpanded under [0]. "
            f"Mean delta={mean_diff:.2f} keys. Live rate OK ({live_gate_note}) "
            f"but context quality risk is unacceptably high for complex tasks."
        )
    elif high_expansion_risk and not expansion_gate_pass:
        recommendation = "KEEP"
        rationale = (
            f"Expansion regression in {regressions}/{n} trials ({regression_rate:.0%}) "
            f"and mean delta={mean_diff:.1f} keys — Tier-1 rules frequently missed under [0]. "
            f"Live rate OK ({live_gate_note}) but context quality risk is high."
        )
    elif expansion_gate_pass and live_gate_pass:
        recommendation = "FLIP"
        rationale = (
            f"Live skills_failed rate ({observed_rate:.3f}) within threshold ({threshold}). "
            f"Expansion regression in only {regressions}/{n} trials ({regression_rate:.0%}), "
            f"mean delta={mean_diff:.2f} unexpanded keys. "
            f"Tier-0-heavy workloads dominate; Tier-1 miss risk is acceptable. "
            f"Estimated savings: ~35K tokens/agent delegation."
        )
    else:
        # 30-50% regression rate — borderline, recommend KEEP with more data
        recommendation = "KEEP"
        rationale = (
            f"Borderline expansion regression: {regressions}/{n} trials ({regression_rate:.0%}) "
            f"leave more Tier-1 rules unexpanded under [0]. Mean delta={mean_diff:.2f} keys. "
            f"Live rate OK ({live_gate_note}) but Tier-1 context loss risk is meaningful. "
            f"Conservative recommendation: Keep [0,1] until regression rate falls below 30%."
        )

    auto_flip_enabled = os.environ.get("COS_AUTO_FLIP_TIER_FILTER", "").strip() == "1"

    return {
        "recommendation": recommendation,
        "rationale": rationale,
        "auto_flip_eligible": recommendation == "FLIP" and auto_flip_enabled,
        "auto_flip_env_var": "COS_AUTO_FLIP_TIER_FILTER",
        "auto_flip_enabled": auto_flip_enabled,
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def build_report(
    trials: list[dict[str, Any]],
    stats: dict[str, Any],
    decision: dict[str, Any],
    approach: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "harness": "scripts/validate_tier_filter.py",
        "approach": approach,
        "dry_run": dry_run,
        "config_a": "tier_filter=[0,1]",
        "config_b": "tier_filter=[0]",
        "baseline_skills_failed_rate": BASELINE_RATE,
        "revert_threshold": REVERT_THRESHOLD,
        "statistics": stats,
        "decision": decision,
        "trials": trials,
        "repeatability": (
            "Re-run at any time with: "
            "python3 scripts/validate_tier_filter.py --approach=replay --n=30 "
            "--output=docs/06-Daily/measurements/tier-filter-validation-$(date +%F).json"
        ),
    }


def write_markdown_summary(report: dict[str, Any], path: Path) -> None:
    """Write human-readable summary alongside the JSON report."""
    stats = report["statistics"]
    decision = report["decision"]
    rec = decision["recommendation"]
    badge = {"FLIP": "FLIP (safe to lower)", "KEEP": "KEEP [0,1]", "NEEDS-MORE-DATA": "NEEDS-MORE-DATA"}.get(rec, rec)

    lines = [
        "# Tier-Filter Validation Report",
        "",
        f"**Generated**: {report['generated_at']}  ",
        f"**Harness**: {report['harness']}  ",
        f"**Approach**: {report['approach']} ({stats['n_trials']} trials)  ",
        f"**Recommendation**: {badge}",
        "",
        "## Statistical Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Trials (N) | {stats['n_trials']} |",
        f"| Mean unexpanded keys — Config A [0,1] | {stats['mean_unexpanded_keys_a']:.2f} |",
        f"| Mean unexpanded keys — Config B [0] | {stats['mean_unexpanded_keys_b']:.2f} |",
        f"| Mean delta (B-A) | {stats['mean_delta_b_minus_a']:+.2f} keys |",
        f"| Trials where B leaves more unexpanded | {stats['trials_b_worse']} / {stats['n_trials']} |",
        f"| Trials neutral (no difference) | {stats['trials_neutral']} / {stats['n_trials']} |",
        f"| Wilcoxon W | {stats['wilcoxon_w']} ({stats['wilcoxon_note']}) |",
        f"| Baseline skills_failed/session | {stats['baseline_skills_failed_rate']} |",
        f"| Observed skills_failed/session (last 7d) | {stats['observed_skills_failed_rate']} |",
        f"| Revert threshold | {stats['revert_threshold']} |",
        "",
        "## Decision",
        "",
        f"**{rec}** — {decision['rationale']}",
        "",
    ]

    if rec == "FLIP":
        lines += [
            "### To apply the change",
            "",
            "Edit `cognitive-os.yaml`:",
            "```yaml",
            "expansion:",
            "  tier_filter: [0]",
            "```",
            "",
            "Or set `COS_AUTO_FLIP_TIER_FILTER=1` and re-run the harness for automatic application.",
            "",
        ]

    lines += [
        "## Repeatability",
        "",
        f"```bash",
        f"{report['repeatability']}",
        "```",
        "",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate tier_filter=[0] decision.")
    parser.add_argument(
        "--approach", choices=["replay", "synthetic"], default="replay",
        help="replay=use real session transcripts; synthetic=use seed prompts",
    )
    parser.add_argument("--n", type=int, default=30, help="Target sample size")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    parser.add_argument("--dry-run", action="store_true", help="Wire up only, no stats")
    args = parser.parse_args(argv)

    print(f"[validate_tier_filter] approach={args.approach} n={args.n}")

    # Collect trials
    if args.approach == "replay":
        trials = collect_replay_prompts(args.n)
        if not trials:
            print("[validate_tier_filter] No replay prompts found with ref-key markers; "
                  "falling back to synthetic approach.", file=sys.stderr)
            trials = collect_synthetic_prompts(args.n)
            approach_used = "synthetic (fallback from replay)"
        else:
            approach_used = "replay"
    else:
        trials = collect_synthetic_prompts(args.n)
        approach_used = "synthetic"

    print(f"[validate_tier_filter] Collected {len(trials)} trials via {approach_used}")

    if args.dry_run:
        stats = {
            "n_trials": len(trials),
            "config_a_label": "tier_filter=[0,1]",
            "config_b_label": "tier_filter=[0]",
            "mean_unexpanded_keys_a": 0.0,
            "mean_unexpanded_keys_b": 0.0,
            "mean_delta_b_minus_a": 0.0,
            "trials_b_worse": 0,
            "trials_neutral": len(trials),
            "trials_b_better": 0,
            "wilcoxon_w": 0,
            "wilcoxon_note": "dry-run",
            "baseline_skills_failed_rate": BASELINE_RATE,
            "revert_threshold": REVERT_THRESHOLD,
            "observed_skills_failed_rate": None,
            "dry_run": True,
        }
        decision = {"recommendation": "DRY-RUN", "rationale": "dry-run mode; no stats computed"}
    else:
        stats = compute_statistics(trials)
        decision = make_recommendation(stats)

    report = build_report(trials, stats, decision, approach_used, dry_run=args.dry_run)

    # Output path
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = _PROJECT_ROOT / "docs" / "measurements" / "tier-filter-validation-output.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[validate_tier_filter] Report written to {out_path}")

    # Also write markdown summary
    md_path = out_path.with_suffix(".md")
    write_markdown_summary(report, md_path)
    print(f"[validate_tier_filter] Summary written to {md_path}")

    # Print recommendation
    rec = decision.get("recommendation", "UNKNOWN")
    print(f"\n=== RECOMMENDATION: {rec} ===")
    print(decision.get("rationale", ""))
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
