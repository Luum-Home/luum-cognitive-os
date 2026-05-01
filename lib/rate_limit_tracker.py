"""Portable per-provider rate-limit instrumentation layer (ADR-080 Tier 1 #4).

Ported and adapted from Hermes (MIT license):
  - .claude/plugins/hermes-agent/agent/rate_limit_tracker.py  — header parsing,
    data model, RateLimitState, formatting utilities
  - .claude/plugins/hermes-agent/agent/nous_rate_guard.py     — gating logic,
    cross-session cooldown persistence

Original author: Hermes contributors (MIT)
COS adaptation: Matias Nahuel Améndola, 2026-05-01

-----------------------------------------------------------------------
RELATIONSHIP TO hooks/rate-limiter.sh
-----------------------------------------------------------------------
hooks/rate-limiter.sh is a *rule-based* tool-usage throttler. It counts
how many Bash/Write/Agent calls happen per minute and blocks when the
bucket overflows. It knows nothing about provider quota windows — it
purely governs COS's own tool invocation rate.

This module is *header-driven* provider instrumentation. It reads the
x-ratelimit-* (OpenAI-family) and anthropic-ratelimit-* (Anthropic-family)
response headers returned by actual provider calls, tracks per-window
consumption, predicts exhaustion, and gates dispatch() before a call is
even made. The two layers are complementary:

  hooks/rate-limiter.sh  →  governs COS tool usage rate (agent-side)
  lib/rate_limit_tracker →  governs provider API consumption (provider-side)

-----------------------------------------------------------------------
OPT-IN
-----------------------------------------------------------------------
Set COS_RATE_TRACKER=1 to activate tracking and gating.
Without the env var the module is fully no-op — dispatch behaviour is
unchanged, zero performance cost.

When active:
  - record() is called after every provider response (always)
  - should_throttle() is called before every provider call
  - Throttle gate fires only when a bucket exceeds THROTTLE_THRESHOLD_PCT (85%)
  - State is also persisted to .cognitive-os/runtime/rate-limits.jsonl
    (append-only; daily rotation via metrics-rotation.sh)

-----------------------------------------------------------------------
THRESHOLD TUNING
-----------------------------------------------------------------------
THROTTLE_THRESHOLD_PCT = 85  (default)

  At 85% consumed the guard starts routing around the provider rather
  than waiting for a 429. Lower values (e.g. 70) are more conservative
  and reduce risk of hitting limits but increase unnecessary fallbacks.
  Higher values (e.g. 95) minimise unnecessary fallbacks but leave less
  headroom before a real limit hit.

  Override at runtime: set COS_RATE_THROTTLE_PCT=<int> in the environment.
  Example: COS_RATE_THROTTLE_PCT=90 allows more headroom consumption.

-----------------------------------------------------------------------
PROVIDER SUPPORT
-----------------------------------------------------------------------
Provider         Header family                    Notes
-------------    -------------------------        -------------------------
anthropic        anthropic-ratelimit-*            Requests+tokens/min+day
openai           x-ratelimit-*                    Requests+tokens/min+hour
qwen             x-ratelimit-* (best-effort)      Same shape as OpenAI
ollama           (none)                           Local — always no-op
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_DEFAULT_THROTTLE_PCT: float = 85.0
_JSONL_SUBDIR = "runtime"
_JSONL_FILENAME = "rate-limits.jsonl"


def _throttle_threshold() -> float:
    """Read COS_RATE_THROTTLE_PCT env var; fall back to 85."""
    raw = os.environ.get("COS_RATE_THROTTLE_PCT", "")
    try:
        val = float(raw)
        if 0 < val <= 100:
            return val
    except (TypeError, ValueError):
        pass
    return _DEFAULT_THROTTLE_PCT


def _tracker_enabled() -> bool:
    """True when COS_RATE_TRACKER=1 is set."""
    return os.environ.get("COS_RATE_TRACKER", "").strip() == "1"


# ── Data model ───────────────────────────────────────────────────────────────

@dataclass
class RateLimitBucket:
    """One rate-limit window (e.g. requests per minute)."""

    limit: int = 0
    remaining: int = 0
    reset_seconds: float = 0.0
    captured_at: float = field(default_factory=time.time)

    @property
    def used(self) -> int:
        return max(0, self.limit - self.remaining)

    @property
    def usage_pct(self) -> float:
        if self.limit <= 0:
            return 0.0
        return (self.used / self.limit) * 100.0

    @property
    def remaining_seconds_now(self) -> float:
        """Estimated seconds until reset, adjusted for elapsed time."""
        elapsed = time.time() - self.captured_at
        return max(0.0, self.reset_seconds - elapsed)

    @property
    def has_data(self) -> bool:
        return self.limit > 0


@dataclass
class RateLimitState:
    """Full per-provider rate-limit state parsed from response headers."""

    requests_min: RateLimitBucket = field(default_factory=RateLimitBucket)
    requests_day: RateLimitBucket = field(default_factory=RateLimitBucket)
    tokens_min: RateLimitBucket = field(default_factory=RateLimitBucket)
    tokens_day: RateLimitBucket = field(default_factory=RateLimitBucket)
    captured_at: float = 0.0
    provider: str = ""

    @property
    def has_data(self) -> bool:
        return self.captured_at > 0

    @property
    def age_seconds(self) -> float:
        if not self.has_data:
            return float("inf")
        return time.time() - self.captured_at

    def worst_bucket_pct(self) -> float:
        """Return the highest usage_pct across all buckets that have data."""
        pcts = [
            b.usage_pct
            for b in (self.requests_min, self.requests_day,
                       self.tokens_min, self.tokens_day)
            if b.has_data
        ]
        return max(pcts, default=0.0)

    def worst_bucket_label(self) -> str:
        """Return a human label for the most-consumed bucket."""
        pairs = [
            ("requests/min", self.requests_min),
            ("requests/day", self.requests_day),
            ("tokens/min", self.tokens_min),
            ("tokens/day", self.tokens_day),
        ]
        worst_label, worst_pct = "unknown", 0.0
        for label, bucket in pairs:
            if bucket.has_data and bucket.usage_pct > worst_pct:
                worst_label, worst_pct = label, bucket.usage_pct
        return worst_label


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ── Per-provider parsers ─────────────────────────────────────────────────────

def _parse_anthropic_headers(lowered: dict[str, str], now: float) -> RateLimitState:
    """Parse anthropic-ratelimit-* header family.

    Anthropic exposes requests+tokens for minute and day windows.
    Header names (as of 2026):
      anthropic-ratelimit-requests-limit
      anthropic-ratelimit-requests-remaining
      anthropic-ratelimit-requests-reset       (ISO-8601 or seconds)
      anthropic-ratelimit-tokens-limit
      anthropic-ratelimit-tokens-remaining
      anthropic-ratelimit-tokens-reset
    Day-window variants use "-day" suffix on some endpoints; treated as
    "requests_day" / "tokens_day" when present.
    """
    def _areset(key: str) -> float:
        raw = lowered.get(key, "")
        if not raw:
            return 0.0
        # Could be seconds (numeric) or ISO-8601 string
        try:
            val = float(raw)
            return max(0.0, val)
        except ValueError:
            # ISO-8601: parse and compute delta from now
            try:
                import datetime
                dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
                delta = dt.timestamp() - now
                return max(0.0, delta)
            except Exception:
                return 0.0

    rm = RateLimitBucket(
        limit=_safe_int(lowered.get("anthropic-ratelimit-requests-limit")),
        remaining=_safe_int(lowered.get("anthropic-ratelimit-requests-remaining")),
        reset_seconds=_areset("anthropic-ratelimit-requests-reset"),
        captured_at=now,
    )
    rd = RateLimitBucket(
        limit=_safe_int(lowered.get("anthropic-ratelimit-requests-day-limit")),
        remaining=_safe_int(lowered.get("anthropic-ratelimit-requests-day-remaining")),
        reset_seconds=_areset("anthropic-ratelimit-requests-day-reset"),
        captured_at=now,
    )
    tm = RateLimitBucket(
        limit=_safe_int(lowered.get("anthropic-ratelimit-tokens-limit")),
        remaining=_safe_int(lowered.get("anthropic-ratelimit-tokens-remaining")),
        reset_seconds=_areset("anthropic-ratelimit-tokens-reset"),
        captured_at=now,
    )
    td = RateLimitBucket(
        limit=_safe_int(lowered.get("anthropic-ratelimit-tokens-day-limit")),
        remaining=_safe_int(lowered.get("anthropic-ratelimit-tokens-day-remaining")),
        reset_seconds=_areset("anthropic-ratelimit-tokens-day-reset"),
        captured_at=now,
    )
    return RateLimitState(
        requests_min=rm,
        requests_day=rd,
        tokens_min=tm,
        tokens_day=td,
        captured_at=now,
        provider="anthropic",
    )


def _parse_openai_headers(lowered: dict[str, str], now: float, provider: str = "openai") -> RateLimitState:
    """Parse x-ratelimit-* header family (OpenAI / Codex / Qwen).

    Hermes original: rate_limit_tracker.py — parse_rate_limit_headers().
    OpenAI exposes requests+tokens for minute and hour windows; mapped to
    requests_min/tokens_min and requests_day/tokens_day respectively.

    Header names (as of 2026):
      x-ratelimit-limit-requests
      x-ratelimit-remaining-requests
      x-ratelimit-reset-requests           (seconds)
      x-ratelimit-limit-requests-1h        (hour variant)
      x-ratelimit-remaining-requests-1h
      x-ratelimit-reset-requests-1h
      x-ratelimit-limit-tokens             (per-minute)
      x-ratelimit-remaining-tokens
      x-ratelimit-reset-tokens
      x-ratelimit-limit-tokens-1h          (hour variant)
      x-ratelimit-remaining-tokens-1h
      x-ratelimit-reset-tokens-1h
    """
    def _bucket(resource: str, suffix: str = "") -> RateLimitBucket:
        tag = f"{resource}{suffix}"
        return RateLimitBucket(
            limit=_safe_int(lowered.get(f"x-ratelimit-limit-{tag}")),
            remaining=_safe_int(lowered.get(f"x-ratelimit-remaining-{tag}")),
            reset_seconds=_safe_float(lowered.get(f"x-ratelimit-reset-{tag}")),
            captured_at=now,
        )

    return RateLimitState(
        requests_min=_bucket("requests"),
        requests_day=_bucket("requests", "-1h"),   # hour window → mapped to "day" slot
        tokens_min=_bucket("tokens"),
        tokens_day=_bucket("tokens", "-1h"),
        captured_at=now,
        provider=provider,
    )


def _parse_ollama_headers(_lowered: dict[str, str], now: float) -> RateLimitState:
    """Ollama is local — no rate-limit headers. Always returns empty state."""
    return RateLimitState(captured_at=0.0, provider="ollama")


def _parse_qwen_headers(lowered: dict[str, str], now: float) -> RateLimitState:
    """Qwen (Alibaba DashScope / compatible) — best-effort OpenAI shape."""
    return _parse_openai_headers(lowered, now, provider="qwen")


# ── Parser dispatch ───────────────────────────────────────────────────────────

_PARSERS = {
    "anthropic": _parse_anthropic_headers,
    "claude": _parse_anthropic_headers,
    "openai": _parse_openai_headers,
    "codex": _parse_openai_headers,
    "openrouter": _parse_openai_headers,
    "qwen": _parse_qwen_headers,
    "ollama": _parse_ollama_headers,
}


def _detect_provider(provider: str, lowered: dict[str, str]) -> str:
    """Infer parser key from provider name or header presence."""
    p = provider.lower()
    if p in _PARSERS:
        return p
    # Auto-detect from header prefix
    if any(k.startswith("anthropic-ratelimit-") for k in lowered):
        return "anthropic"
    if any(k.startswith("x-ratelimit-") for k in lowered):
        return "openai"
    return "openai"  # safest default for unknown providers


# ── Process-local state store ─────────────────────────────────────────────────

_STATE: dict[str, RateLimitState] = {}


# ── Persistence ───────────────────────────────────────────────────────────────

def _jsonl_path() -> Optional[Path]:
    """Resolve .cognitive-os/runtime/rate-limits.jsonl from project root."""
    try:
        from lib.paths import runtime_project_root_or_cwd
        base = runtime_project_root_or_cwd()
    except Exception:
        base = Path.cwd()
    return base / ".cognitive-os" / _JSONL_SUBDIR / _JSONL_FILENAME


def _append_jsonl(record: dict[str, Any]) -> None:
    """Atomic append to rate-limits.jsonl. Best-effort — never raises."""
    try:
        path = _jsonl_path()
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic: write to temp then rename (same dir ensures same filesystem)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            os.replace(tmp, path)  # non-atomic append; we use replace for single-record writes
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            # Fall back to direct append (less atomic but functional)
            try:
                with open(path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            except OSError:
                pass
    except Exception as exc:
        logger.debug("rate_limit_tracker: jsonl append failed: %s", exc)


# ── Public API ────────────────────────────────────────────────────────────────

def record(
    provider: str,
    headers: Mapping[str, str],
    request_id: Optional[str] = None,
) -> None:
    """Ingest response headers, update per-provider state.

    Safe to call unconditionally — no-ops when COS_RATE_TRACKER is not set
    OR when no rate-limit headers are present in the response.

    Args:
        provider:   Provider identifier ("anthropic", "openai", "qwen", etc.)
        headers:    Raw HTTP response headers (case-insensitive dict-like).
        request_id: Optional request identifier for log correlation.
    """
    if not _tracker_enabled():
        return

    if not headers:
        return

    lowered: dict[str, str] = {k.lower(): v for k, v in headers.items()}

    # Quick check: any recognised rate-limit header present?
    has_rl = any(
        k.startswith(("x-ratelimit-", "anthropic-ratelimit-"))
        for k in lowered
    )
    if not has_rl:
        logger.debug("rate_limit_tracker.record(%s): no rate-limit headers", provider)
        return

    parser_key = _detect_provider(provider, lowered)
    parser = _PARSERS.get(parser_key, _parse_openai_headers)

    now = time.time()
    try:
        parsed = parser(lowered, now)
    except Exception as exc:
        logger.warning(
            "rate_limit_tracker: malformed headers for %s — %s; returning safe state",
            provider, exc,
        )
        return

    _STATE[provider] = parsed

    # Persist to JSONL (best-effort)
    _append_jsonl({
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "provider": provider,
        "request_id": request_id,
        "requests_min_pct": parsed.requests_min.usage_pct,
        "requests_day_pct": parsed.requests_day.usage_pct,
        "tokens_min_pct": parsed.tokens_min.usage_pct,
        "tokens_day_pct": parsed.tokens_day.usage_pct,
        "worst_pct": parsed.worst_bucket_pct(),
    })

    logger.debug(
        "rate_limit_tracker.record(%s): worst=%.1f%% (%s)",
        provider, parsed.worst_bucket_pct(), parsed.worst_bucket_label(),
    )


def state(provider: str) -> RateLimitState:
    """Return current quota/window/reset state for a provider.

    Returns an empty RateLimitState (has_data=False) when no data has been
    recorded yet for this provider.
    """
    return _STATE.get(provider, RateLimitState(provider=provider))


def should_throttle(
    provider: str,
    intent: str = "write",
) -> tuple[bool, str]:
    """Predict whether a call to *provider* should be gated.

    Returns (should_block: bool, reason: str).

    Gating fires when:
      - COS_RATE_TRACKER=1 is set, AND
      - The worst bucket for this provider has consumed >= THROTTLE_THRESHOLD_PCT

    When COS_RATE_TRACKER is not set: always returns (False, "").
    When no data is recorded for the provider: always returns (False, "").
    Ollama: always returns (False, "") — local, no limits.

    Args:
        provider: Provider identifier string.
        intent:   "write" (default) or "read" — reserved for future
                  differentiated gating (reads may tolerate higher usage).
    """
    if not _tracker_enabled():
        return False, ""

    if provider.lower() == "ollama":
        return False, ""

    s = _STATE.get(provider)
    if s is None or not s.has_data:
        return False, ""

    threshold = _throttle_threshold()
    worst_pct = s.worst_bucket_pct()
    label = s.worst_bucket_label()

    if worst_pct >= threshold:
        reset_sec = 0.0
        # Find the bucket driving the throttle and report its reset window
        for bucket in (s.requests_min, s.requests_day, s.tokens_min, s.tokens_day):
            if bucket.has_data and bucket.usage_pct >= threshold:
                reset_sec = bucket.remaining_seconds_now
                break

        reason = (
            f"{provider} {label} at {worst_pct:.0f}% (threshold {threshold:.0f}%); "
            f"resets in {_fmt_seconds(reset_sec)}"
        )
        return True, reason

    return False, ""


def metrics() -> dict[str, Any]:
    """Return observability snapshot for all tracked providers.

    Suitable for health endpoints, dashboards, and the resource-governor skill.

    Schema:
        {
          "providers": {
            "<provider>": {
              "worst_pct": float,
              "worst_label": str,
              "requests_min_pct": float,
              "requests_day_pct": float,
              "tokens_min_pct": float,
              "tokens_day_pct": float,
              "age_seconds": float,
              "predicted_exhaustion": str | None   # "Xm Ys" or None
            }
          },
          "throttle_threshold_pct": float,
          "tracker_enabled": bool,
        }
    """
    out: dict[str, Any] = {
        "providers": {},
        "throttle_threshold_pct": _throttle_threshold(),
        "tracker_enabled": _tracker_enabled(),
    }
    for pname, s in _STATE.items():
        worst = s.worst_bucket_pct()
        # Predict exhaustion: find the tightest reset window above threshold
        pred_exhaustion = None
        thresh = _throttle_threshold()
        for bucket in (s.requests_min, s.tokens_min, s.requests_day, s.tokens_day):
            if bucket.has_data and bucket.usage_pct >= thresh:
                pred_exhaustion = _fmt_seconds(bucket.remaining_seconds_now)
                break

        out["providers"][pname] = {
            "worst_pct": worst,
            "worst_label": s.worst_bucket_label(),
            "requests_min_pct": s.requests_min.usage_pct,
            "requests_day_pct": s.requests_day.usage_pct,
            "tokens_min_pct": s.tokens_min.usage_pct,
            "tokens_day_pct": s.tokens_day.usage_pct,
            "age_seconds": s.age_seconds,
            "predicted_exhaustion": pred_exhaustion,
        }
    return out


def clear(provider: Optional[str] = None) -> None:
    """Clear in-process state. Used in tests and after provider recovery."""
    if provider is None:
        _STATE.clear()
    else:
        _STATE.pop(provider, None)


# ── Formatting helpers (from Hermes rate_limit_tracker.py) ───────────────────

def _fmt_seconds(seconds: float) -> str:
    """Seconds → human-friendly duration."""
    s = max(0, int(seconds))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        m, sec = divmod(s, 60)
        return f"{m}m {sec}s" if sec else f"{m}m"
    h, remainder = divmod(s, 3600)
    m = remainder // 60
    return f"{h}h {m}m" if m else f"{h}h"
