# SCOPE: both
"""Abstract LLM dispatcher with priority cascade + rich metrics (ADR-049 Option B).

Encapsulates the logic that was inline in `scripts/orchestrator.py::cmd_run`
so the same cascade can be invoked from:
  - scripts/orchestrator.py (--providers CLI)
  - Python callers (skills, tests, future auto-router)
  - The upcoming ADR-051 agent loop (when it needs to dispatch sub-tasks)

Forward-compatible with:
  - ADR-050 per-skill routing (skill_requirements parameter reserved)
  - ADR-052 benchmark harness (metrics JSONL feeds it)
  - ADR-053 auto-optimizer (metrics JSONL is its input)

Metrics schema (one JSONL line per dispatch):
    {
      "ts": "2026-04-21T18:00:00Z",
      "dispatch_id": "<uuid>",
      "providers_requested": ["qwen", "claude"],
      "providers_tried": ["qwen"],
      "provider_used": "alibaba_qwen",
      "model": "qwen3.6-plus",
      "task_type": "general",
      "skill_name": null,
      "tokens_in": 234,
      "tokens_out": 1890,
      "cost_usd": 0.0045,
      "latency_ms": 2340,
      "success": true,
      "error": ""
    }

Written to `.cognitive-os/metrics/llm-dispatch.jsonl` (appended, never truncated
— rotation handled by hooks/metrics-rotation.sh).
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

# Rate-limit patterns for cascade advance logic. Kept in sync with
# scripts/orchestrator.py _RATE_LIMIT_PATTERNS and hooks/rate-limit-detector.sh.
# If any of these substrings appear (case-insensitive) in a provider error,
# cascade advances to the next provider. Otherwise Claude-fallback is skipped.
_RATE_LIMIT_PATTERNS = (
    "out of extra usage",
    "rate limit exceeded",
    "approximate usage limit",
    "approximately usage limit",
    "approaching your usage limit",
    "you're out of",
    "usage limit reached",
)


@dataclass
class DispatchResult:
    """Provider-agnostic result returned by dispatch().

    Mirrors the shape that cmd_run reports so callers don't branch on provider.
    """

    success: bool = False
    text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: str = ""
    provider_used: str = "none"
    providers_tried: list[str] = field(default_factory=list)
    latency_ms: int = 0
    model: str = ""


def _is_rate_limit_error(error: str | None) -> bool:
    if not error:
        return False
    low = error.lower()
    return any(p in low for p in _RATE_LIMIT_PATTERNS)


def _fallback_disabled() -> bool:
    """True if COS_DISABLE_LLM_FALLBACK=1 blocks cascade advance."""
    return os.environ.get("COS_DISABLE_LLM_FALLBACK", "").strip() == "1"


def _metrics_path(project_dir: Path | None = None) -> Path:
    """Resolve the JSONL metrics file path. Honors CLAUDE_PROJECT_DIR."""
    if project_dir is None:
        project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
    return project_dir / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"


def _log_metric(record: dict[str, Any], project_dir: Path | None = None) -> None:
    """Append a structured record to llm-dispatch.jsonl. Best-effort, never raises."""
    try:
        path = _metrics_path(project_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except (OSError, TypeError, ValueError):
        # Metrics logging must never crash the dispatch itself.
        pass


def _try_qwen(
    prompt: str,
    claude_model: Optional[str] = None,
    verbose: bool = False,
) -> Optional[dict]:
    """Call lib/qwen_provider.py. Returns dict with response fields or None if
    unavailable/disabled. Kept here (rather than imported from orchestrator.py)
    so tests can stub this cleanly and the dispatch logic stays self-contained.
    """
    # Per-provider kill-switch
    if os.environ.get("COS_DISABLE_QWEN", "").strip() == "1":
        if verbose:
            print("[dispatch] COS_DISABLE_QWEN=1 — skipping Qwen", file=sys.stderr)
        return None

    try:
        from lib.qwen_provider import call as qwen_call, is_configured, select_model
    except ImportError:
        return None

    if not is_configured():
        return None

    chosen_model = select_model(claude_model_hint=claude_model)
    messages = [{"role": "user", "content": prompt}]
    r = qwen_call(messages, model=chosen_model)

    return {
        "success": r.success,
        "text": r.text,
        "tokens_in": r.tokens_in,
        "tokens_out": r.tokens_out,
        "cost_usd": r.cost_usd,
        "error": r.error,
        "model": chosen_model,
        "provider_label": "alibaba_qwen",
    }


def _try_claude(
    prompt: str,
    claude_model: Optional[str],
    claude_executor: Any,
    timeout: int = 600,
) -> dict:
    """Call ClaudeExecutor. Returns dict with response fields.

    claude_executor is injected (already-instantiated) so dispatch stays
    unit-testable without spawning real sub-claudes.
    """
    r = claude_executor.run(prompt, model=claude_model, timeout=timeout)
    return {
        "success": r.success,
        "text": getattr(r, "text", ""),
        "tokens_in": getattr(r, "input_tokens", 0),
        "tokens_out": getattr(r, "output_tokens", 0),
        "cost_usd": getattr(r, "cost_usd", 0.0),
        "error": getattr(r, "error", "") or "",
        "model": claude_model or "",
        "provider_label": "claude",
    }


def dispatch(
    prompt: str,
    providers: list[str] | None = None,
    claude_executor: Any = None,
    claude_model: Optional[str] = None,
    task_type: str = "general",
    skill_name: Optional[str] = None,
    skill_requirements: dict | None = None,  # RESERVED for ADR-050
    timeout: int = 600,
    verbose: bool = False,
    _qwen_fn: Optional[Callable] = None,  # test injection
    _claude_fn: Optional[Callable] = None,  # test injection
    _metric_sink: Optional[Callable] = None,  # test injection: replaces _log_metric
) -> DispatchResult:
    """Iterate the priority-cascade providers list; first success wins.

    Args:
      prompt: user-facing task text
      providers: priority list (e.g. ["qwen", "claude"]). None → env-driven default.
      claude_executor: already-instantiated ClaudeExecutor (required if 'claude' in list)
      claude_model: optional model hint (opus/sonnet/haiku or full name)
      task_type: freeform tag for metrics (e.g. "general", "code", "reasoning")
      skill_name: optional skill name for metrics — enables per-skill routing
      skill_requirements: ADR-050 per-skill routing dict. Recognised keys:
        providers_preferred (list), providers_excluded (list),
        fallback_on_rate_limit (bool, default True),
        fallback_on_any_error (bool, default False),
        budget_max_usd_per_call (float | None). When present, overrides the
        default `providers` cascade and controls fallback advance rules.
        None → legacy uniform behaviour (backward-compatible).
      timeout: per-call timeout in seconds
      verbose: print cascade decisions to stderr

    Returns DispatchResult. Always writes one JSONL record per invocation.
    """
    # Resolve providers list
    if providers is None:
        providers = ["qwen", "claude"]
    # Honor COS_FORCE_CLAUDE_PRIMARY override at the dispatch boundary too
    if os.environ.get("COS_FORCE_CLAUDE_PRIMARY", "").strip() == "1":
        providers = ["claude"]

    # ADR-050: apply per-skill routing if provided. Env override (COS_FORCE_CLAUDE_PRIMARY)
    # takes precedence — it's a hard kill-switch.
    _skill_req = skill_requirements if isinstance(skill_requirements, dict) else {}
    if _skill_req and os.environ.get("COS_FORCE_CLAUDE_PRIMARY", "").strip() != "1":
        pref = _skill_req.get("providers_preferred") or []
        if isinstance(pref, list) and pref:
            providers = list(pref)
        excl = _skill_req.get("providers_excluded") or []
        if isinstance(excl, list) and excl:
            _blocked = set(excl)
            providers = [p for p in providers if p not in _blocked]
        if verbose:
            print(f"[dispatch] ADR-050 skill routing applied → providers={providers}",
                  file=sys.stderr)

    # Fallback policy (ADR-050) — defaults preserve legacy cascade semantics
    _fallback_on_rate_limit = bool(_skill_req.get("fallback_on_rate_limit", True))
    _fallback_on_any_error = bool(_skill_req.get("fallback_on_any_error", False))
    _budget_cap = _skill_req.get("budget_max_usd_per_call")
    try:
        _budget_cap = float(_budget_cap) if _budget_cap is not None else None
    except (TypeError, ValueError):
        _budget_cap = None

    providers_requested = list(providers)
    providers_tried: list[str] = []
    dispatch_id = uuid.uuid4().hex[:12]
    t0 = time.monotonic()

    # Injectable test hooks (production calls _try_qwen / _try_claude)
    qwen_fn = _qwen_fn or _try_qwen
    claude_fn = _claude_fn or _try_claude
    metric_sink = _metric_sink or _log_metric

    response: dict | None = None

    for idx, provider in enumerate(providers_requested):
        is_fallback = idx > 0

        if is_fallback and _fallback_disabled():
            if verbose:
                print("[dispatch] COS_DISABLE_LLM_FALLBACK=1 — cascade blocked", file=sys.stderr)
            break

        # Cascade advance policy:
        #   - ADR-050 fallback_on_any_error=False (default for quality-sensitive
        #     skills): previous Claude failure without rate-limit → stop cascade.
        #   - ADR-050 fallback_on_rate_limit=False: even rate-limit errors don't
        #     advance — fail hard rather than silently degrade.
        #   - Otherwise: Qwen failure → ALWAYS advance; Claude failure → ONLY
        #     advance if rate-limit.
        if is_fallback and response is not None:
            prev_was_claude = response.get("provider_label") == "claude"
            prev_err = response.get("error")
            prev_was_rate_limit = _is_rate_limit_error(prev_err)

            # ADR-050: explicit fallback_on_rate_limit=False overrides rate-limit advance
            if prev_was_rate_limit and not _fallback_on_rate_limit:
                if verbose:
                    print(
                        "[dispatch] ADR-050 fallback_on_rate_limit=false — not advancing on rate limit",
                        file=sys.stderr,
                    )
                break

            if prev_was_claude and not prev_was_rate_limit and not _fallback_on_any_error:
                if verbose:
                    print(
                        "[dispatch] Claude failed non-rate-limit — not advancing to cheaper fallback",
                        file=sys.stderr,
                    )
                break

        # ADR-050 budget cap: if we've already spent at/above the cap, stop cascade
        # (this prevents a cheap fallback from still being cost-capped blind).
        # Checked pre-call so we never exceed the declared budget.
        if _budget_cap is not None and response is not None:
            spent = float(response.get("cost_usd", 0.0) or 0.0)
            if spent >= _budget_cap:
                if verbose:
                    print(
                        f"[dispatch] ADR-050 budget cap ${_budget_cap:.4f} reached "
                        f"(spent ${spent:.4f}) — stopping cascade",
                        file=sys.stderr,
                    )
                break

        providers_tried.append(provider)
        if verbose:
            prefix = "[dispatch] primary" if not is_fallback else "[dispatch] fallback"
            print(f"{prefix} → {provider}", file=sys.stderr)

        if provider == "qwen":
            attempt = qwen_fn(prompt, claude_model=claude_model, verbose=verbose)
            if attempt is None:
                # Qwen unavailable (unconfigured / SDK missing / disabled) — advance
                if verbose:
                    print("[dispatch] qwen unavailable — advancing", file=sys.stderr)
                continue
            response = attempt
        elif provider == "claude":
            if claude_executor is None:
                if verbose:
                    print("[dispatch] no claude_executor provided — skipping", file=sys.stderr)
                continue
            response = claude_fn(prompt, claude_model, claude_executor, timeout)
        else:
            # Future providers (deepseek, minimax, glm, etc.) — scaffold here
            if verbose:
                print(f"[dispatch] provider {provider!r} not implemented — skipping",
                      file=sys.stderr)
            continue

        if response.get("success"):
            break

    latency_ms = int((time.monotonic() - t0) * 1000)

    # Build result
    if response is None:
        result = DispatchResult(
            success=False,
            error=f"no providers in cascade produced a result (requested: {providers_requested}, "
                  f"tried: {providers_tried})",
            providers_tried=providers_tried,
            latency_ms=latency_ms,
            provider_used="none",
        )
    else:
        result = DispatchResult(
            success=bool(response.get("success")),
            text=response.get("text", ""),
            input_tokens=int(response.get("tokens_in", 0)),
            output_tokens=int(response.get("tokens_out", 0)),
            cost_usd=float(response.get("cost_usd", 0.0)),
            error=response.get("error", "") or "",
            provider_used=response.get("provider_label", "none"),
            providers_tried=providers_tried,
            latency_ms=latency_ms,
            model=response.get("model", ""),
        )

    # Metric emission — always, regardless of success
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dispatch_id": dispatch_id,
        "providers_requested": providers_requested,
        "providers_tried": providers_tried,
        "provider_used": result.provider_used,
        "model": result.model,
        "task_type": task_type,
        "skill_name": skill_name,
        "tokens_in": result.input_tokens,
        "tokens_out": result.output_tokens,
        "cost_usd": result.cost_usd,
        "latency_ms": result.latency_ms,
        "success": result.success,
        "error": result.error[:500] if result.error else "",
        # ADR-050: surface the routing policy that shaped this dispatch
        "skill_routing": {
            "tier": _skill_req.get("tier") if _skill_req else None,
            "providers_preferred": list(_skill_req.get("providers_preferred") or []) if _skill_req else [],
            "providers_excluded": list(_skill_req.get("providers_excluded") or []) if _skill_req else [],
            "fallback_on_rate_limit": _fallback_on_rate_limit if _skill_req else None,
            "fallback_on_any_error": _fallback_on_any_error if _skill_req else None,
            "budget_max_usd_per_call": _budget_cap,
        } if _skill_req else None,
    }
    metric_sink(record)

    return result
