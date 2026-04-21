#!/usr/bin/env python3
"""llm-status.py — Companion script for the /llm-status skill.

Reads .env + environment + .cognitive-os/metrics/llm-dispatch.jsonl and
prints a structured status report (ADR-049). Never prints raw API keys.

Usage:
    python3 scripts/llm-status.py              # pretty output, 30-day window
    python3 scripts/llm-status.py --days 7     # last 7 days
    python3 scripts/llm-status.py --json       # machine-readable
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


def _load_env() -> None:
    """Best-effort load of .env into os.environ (does not clobber existing)."""
    env_file = _PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    try:
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = val
    except OSError:
        pass


def _redact(value: str) -> str:
    if not value:
        return "(unset)"
    if len(value) <= 10:
        return "***"
    return f"{value[:6]}...{value[-4:]}"


def _provider_configured() -> dict[str, Any]:
    _load_env()
    result = {
        "claude_max": {
            "configured": True,  # Always — it's the native fallback
            "note": "native Agent tool",
        },
        "alibaba_qwen": {
            "configured": bool(os.environ.get("ALIBABA_QWEN_API_KEY")),
            "api_key_hint": _redact(os.environ.get("ALIBABA_QWEN_API_KEY", "")),
            "base_url": os.environ.get("ALIBABA_QWEN_BASE_URL", "<default>"),
        },
        "anthropic_api_direct": {
            "configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "api_key_hint": _redact(os.environ.get("ANTHROPIC_API_KEY", "")),
        },
        "openrouter": {
            "configured": bool(os.environ.get("OPENROUTER_API_KEY")),
            "api_key_hint": _redact(os.environ.get("OPENROUTER_API_KEY", "")),
        },
    }
    # Live probe for qwen
    try:
        from lib.qwen_provider import is_configured as qwen_is_configured
        result["alibaba_qwen"]["live_probe"] = bool(qwen_is_configured())
    except ImportError:
        result["alibaba_qwen"]["live_probe"] = False
        result["alibaba_qwen"]["probe_error"] = "openai SDK not installed (uv sync --extra direct_providers)"
    return result


def _kill_switches() -> dict[str, bool]:
    return {
        "COS_DISABLE_LLM_FALLBACK": os.environ.get("COS_DISABLE_LLM_FALLBACK", "").strip() == "1",
        "COS_DISABLE_QWEN": os.environ.get("COS_DISABLE_QWEN", "").strip() == "1",
        "COS_FORCE_CLAUDE_PRIMARY": os.environ.get("COS_FORCE_CLAUDE_PRIMARY", "").strip() == "1",
    }


def _recent_metrics(days: int) -> dict[str, Any]:
    metrics_file = _PROJECT_ROOT / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"
    if not metrics_file.exists():
        return {
            "available": False,
            "reason": f"no metrics file at {metrics_file}",
        }

    cutoff = time.time() - (days * 86400)
    records: list[dict] = []
    total_lines = 0
    parse_errors = 0
    try:
        for line in metrics_file.read_text().splitlines():
            total_lines += 1
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                continue
            ts = rec.get("ts", "")
            try:
                epoch = time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
            except (ValueError, TypeError):
                continue
            if epoch < cutoff:
                continue
            records.append(rec)
    except OSError as e:
        return {"available": False, "reason": f"read error: {e}"}

    if not records:
        return {
            "available": True,
            "total": 0,
            "note": f"no dispatches in last {days} days (file: {total_lines} total lines)",
        }

    # Aggregate
    total = len(records)
    successes = sum(1 for r in records if r.get("success"))
    by_provider: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_provider[r.get("provider_used", "unknown")].append(r)

    breakdown = {}
    for provider, recs in by_provider.items():
        latencies = [r.get("latency_ms", 0) for r in recs if isinstance(r.get("latency_ms"), (int, float))]
        breakdown[provider] = {
            "calls": len(recs),
            "success_rate": sum(1 for r in recs if r.get("success")) / len(recs) if recs else 0.0,
            "tokens_in": sum(r.get("tokens_in", 0) for r in recs),
            "tokens_out": sum(r.get("tokens_out", 0) for r in recs),
            "cost_usd": sum(r.get("cost_usd", 0.0) for r in recs),
            "p50_latency_ms": int(statistics.median(latencies)) if latencies else 0,
            "p95_latency_ms": (int(sorted(latencies)[int(len(latencies) * 0.95)])
                               if len(latencies) > 5 else
                               int(max(latencies)) if latencies else 0),
        }

    last_3 = sorted(records, key=lambda r: r.get("ts", ""), reverse=True)[:3]

    return {
        "available": True,
        "window_days": days,
        "total": total,
        "successes": successes,
        "success_rate": successes / total if total else 0.0,
        "by_provider": breakdown,
        "last_3": [
            {
                "ts": r.get("ts"),
                "provider_used": r.get("provider_used"),
                "model": r.get("model"),
                "task_type": r.get("task_type"),
                "skill_name": r.get("skill_name"),
                "success": r.get("success"),
                "cost_usd": r.get("cost_usd", 0.0),
            }
            for r in last_3
        ],
        "parse_errors": parse_errors,
    }


def _render_pretty(status: dict[str, Any]) -> str:
    lines = [
        "COS LLM Dispatch Status",
        "=" * 72,
        "",
        "Providers configured:",
    ]
    providers = status["providers_configured"]
    for name, cfg in providers.items():
        mark = "✓" if cfg.get("configured") else "–"
        note = cfg.get("note") or cfg.get("api_key_hint", "")
        lines.append(f"  {name:<22} {mark}  ({note})")
        if name == "alibaba_qwen" and cfg.get("live_probe") is False and cfg.get("probe_error"):
            lines.append(f"    └ probe: {cfg['probe_error']}")
    lines.append("")
    lines.append("Kill-switches:")
    for k, v in status["kill_switches"].items():
        mark = "ACTIVE" if v else "(not set)"
        lines.append(f"  {k:<35} {mark}")
    lines.append("")
    lines.append(f"Cascade default: --providers qwen,claude  (ADR-049 Option B)")
    lines.append("")

    m = status["metrics"]
    if not m.get("available"):
        lines.append(f"Metrics: {m.get('reason', 'unavailable')}")
    elif m.get("total", 0) == 0:
        lines.append(f"Metrics: {m.get('note', 'no data')}")
    else:
        lines.append(f"Recent dispatches (last {m['window_days']} days):")
        lines.append(f"  total calls:       {m['total']}")
        lines.append(f"  success rate:      {m['success_rate'] * 100:.1f}%")
        lines.append(f"  provider breakdown (sorted by cost):")
        sorted_providers = sorted(
            m["by_provider"].items(),
            key=lambda kv: -kv[1]["cost_usd"],
        )
        for prov, b in sorted_providers:
            lines.append(
                f"    {prov:<18} {b['calls']:>5} calls | "
                f"tokens: {b['tokens_in']}→{b['tokens_out']} | "
                f"cost: ${b['cost_usd']:.4f} | "
                f"p50: {b['p50_latency_ms']}ms p95: {b['p95_latency_ms']}ms | "
                f"success: {b['success_rate'] * 100:.0f}%"
            )
        lines.append("")
        lines.append("Last 3 dispatches:")
        for i, r in enumerate(m["last_3"], 1):
            lines.append(
                f"  {i}. [{r['ts']}] {r['provider_used']:<15} "
                f"model={r['model']:<20} "
                f"{'✓' if r['success'] else '✗'} "
                f"cost=${r['cost_usd']:.4f} "
                f"{'task='+str(r['task_type']) if r.get('task_type') else ''}"
            )

    lines.append("")
    lines.append("Verification:  bash scripts/smoke-qwen-fallback.sh")
    lines.append("Validator:     python3 scripts/cos-config-audit.sh | grep llm_providers")
    lines.append("")
    lines.append("Actions:")
    lines.append("  Disable Qwen:         export COS_DISABLE_QWEN=1")
    lines.append("  Force Claude:         export COS_FORCE_CLAUDE_PRIMARY=1")
    lines.append("  Block fallback:       export COS_DISABLE_LLM_FALLBACK=1")
    lines.append("  Re-enable (unset):    unset COS_DISABLE_QWEN")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Report LLM dispatch state (ADR-049)")
    p.add_argument("--days", type=int, default=30, help="Metrics window in days (default: 30)")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = p.parse_args(argv)

    status = {
        "providers_configured": _provider_configured(),
        "kill_switches": _kill_switches(),
        "metrics": _recent_metrics(args.days),
    }

    if args.json:
        print(json.dumps(status, indent=2, default=str))
    else:
        print(_render_pretty(status))
    return 0


if __name__ == "__main__":
    sys.exit(main())
