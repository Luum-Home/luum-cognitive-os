#!/usr/bin/env python3
# SCOPE: both
"""Fast stdlib-only context-budget meter hot path for hooks/context-budget-meter.sh."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_USER_BUDGET = 12000


def _read_user_budget(config: Path) -> int:
    if not config.is_file():
        return DEFAULT_USER_BUDGET
    for raw in config.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw.strip()
        if not stripped.startswith("user_max_tokens:"):
            continue
        value = stripped.split(":", 1)[1].split("#", 1)[0].strip().strip("'\"")
        try:
            parsed = int(value)
        except ValueError:
            return DEFAULT_USER_BUDGET
        return parsed if parsed > 0 else DEFAULT_USER_BUDGET
    return DEFAULT_USER_BUDGET


def _verdict(tokens: int, budget: int) -> tuple[str, bool, str, float]:
    ratio = tokens / budget if budget else 0.0
    if ratio <= 1.0:
        name = "PASS"
    elif ratio <= 1.5:
        name = "WARN"
    else:
        name = "BLOCK"
    allowed = name != "BLOCK" or os.environ.get("COS_ALLOW_CONTEXT_BUDGET_OVERRUN") == "1"
    reason = "override" if name == "BLOCK" and allowed else ""
    return name, allowed, reason, ratio


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main(argv: list[str]) -> int:
    start = time.perf_counter()
    project = Path(argv[1]).resolve()
    session_id = argv[2] if len(argv) > 2 else "unknown"
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    prompt = str(data.get("prompt") or data.get("message") or "")
    hso = data.get("hookSpecificOutput") if isinstance(data.get("hookSpecificOutput"), dict) else {}
    additional = str(data.get("additionalContext") or hso.get("additionalContext") or "")
    total_chars = len(prompt) + len(additional)
    tokens = 0 if total_chars == 0 else max(1, (total_chars + 3) // 4)
    budget = _read_user_budget(project / "cognitive-os.yaml")
    verdict, allowed, reason, ratio = _verdict(tokens, budget)
    now = time.time()
    latency_ms = (time.perf_counter() - start) * 1000
    metrics_dir = project / ".cognitive-os" / "metrics"

    _append(metrics_dir / "context-budget.jsonl", {
        "schema_version": 1,
        "timestamp_epoch": now,
        "session_id": session_id,
        "source": "context-budget-meter",
        "layer": "user",
        "prompt_chars": len(prompt),
        "additional_context_chars": len(additional),
        "total_chars": total_chars,
        "tokens_estimate": tokens,
        "budget_token_max": budget,
        "ratio_used": round(ratio, 4),
        "verdict": verdict,
        "allowed": allowed,
        "reason": reason,
        "latency_ms": round(latency_ms, 3),
    })
    _append(metrics_dir / "ai-resource-ledger.jsonl", {
        "schema_version": 1,
        "timestamp_epoch": now,
        "session_id": session_id,
        "agent_id": str(data.get("agent_id") or data.get("subagent_id") or ""),
        "task_id": str(data.get("task_id") or data.get("tool_use_id") or ""),
        "provider": "hook",
        "model": "context-budget-meter",
        "tokens_in": tokens,
        "tokens_out": 0,
        "estimated_cost_usd": 0.0,
        "actual_cost_usd": 0.0,
        "retry_count": 0,
        "tool_calls": 0,
        "reasoning_effort": "none",
        "kind": "context_budget",
        "source": "context-budget-meter",
    })

    if verdict == "WARN":
        print(f"context-budget-meter: WARN user context {tokens}/{budget} tokens", file=sys.stderr)
    elif verdict == "BLOCK" and not allowed:
        print(f"context-budget-meter: BLOCK user context {tokens}/{budget} tokens", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
