# SCOPE: os-only
"""LLM-dispatched routing fallback for the COS skill router (ADR-297).

Tail-cleanup layer that closes the ambiguity gap left by the semantic
matcher (ADR-296). Runs *only* when the semantic top candidate sits in
the 0.30-0.55 confidence band with >=3 viable candidates clustered in
the same band — i.e. there is no clear winner.

Pipeline position
-----------------

    regex (>=0.85)  -->  return
        |
        v (regex < 0.75 OR regex top < 0.85)
    semantic (>=0.55)  -->  return
        |
        v (0.30 <= top < 0.55 AND >=3 candidates in band)
    LLM dispatch  -->  parse strict --> return SkillMatch | None
        |
        v (above 0.55, below 0.30, or <3 candidates)
    skip (return None)

Vendor-neutrality
-----------------

This module MUST NOT import any vendor SDK (anthropic, openai, qwen,
etc). All LLM calls flow through :func:`lib.dispatch.dispatch`
(ADR-049), whose Qwen-primary cascade preserves Claude Max quota and
honours kill-switches. The dispatch import is lazy so that the
fallback module loads cheaply when LLM routing is disabled.

Kill switch
-----------

``COS_DISABLE_LLM_ROUTING=1`` → :func:`llm_route` returns ``None``
without touching dispatch. The semantic and regex layers remain.

Cost guard
----------

Hourly rolling cap, default 100 calls (env ``COS_LLM_ROUTING_HOURLY_CAP``).
State lives in ``.cognitive-os/state/llm-routing-rate.json`` and is
trimmed on each call. Exceeded cap → log a warning and return ``None``.

Cache
-----

``sha256(prompt + "|" + sorted_candidate_names_joined)[:16]`` keys a
JSON file under ``.cognitive-os/cache/llm-routing/``. TTL defaults to
7 days (env ``COS_LLM_ROUTING_CACHE_TTL_DAYS``). Cache misses that
fail dispatch are *not* written, so a transient outage does not
poison the cache.

Audit
-----

Every invocation (cache hit or miss, success or skip-after-call)
appends one JSONL line to ``.cognitive-os/metrics/llm-routing.jsonl``.

ADR cross-refs: ADR-049 (dispatch), ADR-296 (semantic), ADR-285 (drift).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Sequence

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunables (env overrides supported)
# ---------------------------------------------------------------------------

BAND_LOW = 0.30   # below this → too weak, skip
BAND_HIGH = 0.55  # at/above this → clear semantic winner, skip
MIN_CANDIDATES_IN_BAND = 3
DEFAULT_HOURLY_CAP = 100
DEFAULT_CACHE_TTL_DAYS = 7
TOP_N_CANDIDATES = 5
DISPATCH_TIMEOUT_S = 30  # generous; well under p95 budget on warm primary


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LLMCandidate:
    """A single candidate skill the LLM will choose among."""

    skill_name: str
    invoke_command: str
    confidence: float
    description: str = ""


@dataclass(frozen=True)
class LLMRouteResult:
    """Outcome of an LLM routing call (success or skip)."""

    skill_name: Optional[str]
    invoke_command: Optional[str]
    confidence: float
    reason: str
    cache_hit: bool
    provider: str  # "" when skipped/cached/failed without dispatch


# ---------------------------------------------------------------------------
# Filesystem locations — resolved lazily so tests can monkey-patch
# ---------------------------------------------------------------------------

def _project_root() -> Path:
    """Return the project root (test-overridable via COS_PROJECT_ROOT)."""
    override = os.environ.get("COS_PROJECT_ROOT", "").strip()
    if override:
        return Path(override)
    # Lazy import to keep this module cheap on disabled paths.
    try:
        from lib.paths import runtime_project_root_or_cwd  # noqa: WPS433
        return runtime_project_root_or_cwd()
    except Exception:  # noqa: BLE001
        return Path.cwd()


def _cache_dir() -> Path:
    return _project_root() / ".cognitive-os" / "cache" / "llm-routing"


def _state_path() -> Path:
    return _project_root() / ".cognitive-os" / "state" / "llm-routing-rate.json"


def _metrics_path() -> Path:
    return _project_root() / ".cognitive-os" / "metrics" / "llm-routing.jsonl"


# ---------------------------------------------------------------------------
# Trigger gate
# ---------------------------------------------------------------------------

def should_dispatch(candidates: Sequence[LLMCandidate]) -> bool:
    """Pure predicate for the LLM trigger gate.

    True iff:
      * there is a top candidate, and
      * BAND_LOW <= top.confidence < BAND_HIGH, and
      * at least MIN_CANDIDATES_IN_BAND candidates fall in [BAND_LOW, BAND_HIGH).
    """
    if not candidates:
        return False
    top = candidates[0].confidence
    if top < BAND_LOW or top >= BAND_HIGH:
        return False
    in_band = sum(1 for c in candidates if BAND_LOW <= c.confidence < BAND_HIGH)
    return in_band >= MIN_CANDIDATES_IN_BAND


# ---------------------------------------------------------------------------
# Cache key + I/O
# ---------------------------------------------------------------------------

def _cache_key(prompt: str, candidate_names: Iterable[str]) -> str:
    names = "|".join(sorted(candidate_names))
    payload = f"{prompt}|{names}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _cache_ttl_seconds() -> int:
    raw = os.environ.get("COS_LLM_ROUTING_CACHE_TTL_DAYS", "").strip()
    days: float
    try:
        days = float(raw) if raw else float(DEFAULT_CACHE_TTL_DAYS)
    except ValueError:
        days = float(DEFAULT_CACHE_TTL_DAYS)
    return int(days * 86400)


def _cache_read(key: str) -> Optional[dict[str, Any]]:
    path = _cache_dir() / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    ts = data.get("ts", 0)
    try:
        ts_f = float(ts)
    except (TypeError, ValueError):
        return None
    if (time.time() - ts_f) > _cache_ttl_seconds():
        return None
    return data


def _cache_write(key: str, payload: dict[str, Any]) -> None:
    try:
        cd = _cache_dir()
        cd.mkdir(parents=True, exist_ok=True)
        tmp = cd / f"{key}.json.tmp"
        final = cd / f"{key}.json"
        tmp.write_text(
            json.dumps({"ts": time.time(), **payload}, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(tmp, final)
    except OSError:
        # Cache is best-effort; never crash routing on cache I/O.
        pass


# ---------------------------------------------------------------------------
# Rate limit — simple rolling 1h counter
# ---------------------------------------------------------------------------

def _hourly_cap() -> int:
    raw = os.environ.get("COS_LLM_ROUTING_HOURLY_CAP", "").strip()
    try:
        return max(0, int(raw)) if raw else DEFAULT_HOURLY_CAP
    except ValueError:
        return DEFAULT_HOURLY_CAP


def _load_rate_entries() -> list[float]:
    path = _state_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    entries = data.get("entries", []) if isinstance(data, dict) else []
    out: list[float] = []
    for item in entries:
        try:
            out.append(float(item))
        except (TypeError, ValueError):
            continue
    return out


def _save_rate_entries(entries: Iterable[float]) -> None:
    path = _state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps({"entries": list(entries)}, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(tmp, path)
    except OSError:
        pass


def _prune_and_count(now: float) -> list[float]:
    """Return entries from the last hour (pruned)."""
    cutoff = now - 3600.0
    return [t for t in _load_rate_entries() if t >= cutoff]


def _rate_limit_blocked() -> bool:
    cap = _hourly_cap()
    if cap <= 0:
        return False
    entries = _prune_and_count(time.time())
    return len(entries) >= cap


def _rate_limit_record() -> None:
    now = time.time()
    entries = _prune_and_count(now)
    entries.append(now)
    _save_rate_entries(entries)


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

def _audit(record: dict[str, Any]) -> None:
    """Append one JSONL line — best effort."""
    try:
        path = _metrics_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {"ts": datetime.now(timezone.utc).isoformat(), **record},
            ensure_ascii=False,
            default=str,
        )
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except (OSError, TypeError, ValueError):
        pass


# ---------------------------------------------------------------------------
# Prompt construction + strict parsing
# ---------------------------------------------------------------------------

def build_prompt(user_prompt: str, candidates: Sequence[LLMCandidate]) -> str:
    """Build the minimal router-decision prompt (English; LLM is multilingual)."""
    lines = [
        "You are routing a user prompt to one of the listed skills.",
        "Reply with ONLY the skill name, nothing else.",
        "",
        "User prompt:",
        user_prompt.strip(),
        "",
        "Candidates (with descriptions):",
    ]
    for c in candidates:
        desc = (c.description or "").strip().splitlines()[0] if c.description else ""
        lines.append(f"- {c.invoke_command}: {desc}")
    valid = ", ".join(c.invoke_command for c in candidates)
    lines += [
        "",
        "If none match, reply: NONE.",
        f"Reply with one of: {valid}, NONE.",
    ]
    return "\n".join(lines)


def parse_response(response: str, candidates: Sequence[LLMCandidate]) -> Optional[str]:
    """Strict parse — return the chosen invoke_command, or None."""
    if not response:
        return None
    raw = response.strip()
    if not raw:
        return None
    # Allow trailing punctuation/period; nothing else.
    token = raw.split()[0].rstrip(".,;:!")
    if token.upper() == "NONE":
        return None
    valid = {c.invoke_command for c in candidates}
    # Reject responses that include extra prose beyond the bare token.
    if len(raw.split()) > 1:
        # We tolerate only the bare token (optionally a trailing period).
        # "I think /skill-b is best" → reject.
        return None
    return token if token in valid else None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def llm_route(
    user_prompt: str,
    candidates: Sequence[LLMCandidate],
    *,
    dispatch_fn: Optional[Callable[..., Any]] = None,
) -> Optional[LLMRouteResult]:
    """Resolve an ambiguous semantic-routing tie via dispatched LLM.

    Returns ``None`` when LLM routing is disabled/skipped/failed.

    ``dispatch_fn`` is a test hook — when omitted, ``lib.dispatch.dispatch``
    is loaded lazily. The function MUST accept the same kwargs as
    :func:`lib.dispatch.dispatch` and return an object exposing
    ``success`` (bool), ``text`` (str), ``provider_used`` (str),
    ``latency_ms`` (int).
    """
    t_call = time.monotonic()

    # 1. Kill switch — short-circuit before any work.
    if os.environ.get("COS_DISABLE_LLM_ROUTING", "").strip() == "1":
        return None

    # 2. Trigger gate.
    if not should_dispatch(candidates):
        return None

    top_candidates = list(candidates[:TOP_N_CANDIDATES])
    cand_names = [c.invoke_command for c in top_candidates]
    key = _cache_key(user_prompt, cand_names)
    prompt_hash = hashlib.sha256(user_prompt.encode("utf-8")).hexdigest()[:16]

    # 3. Cache hit — fast path.
    cached = _cache_read(key)
    if cached is not None:
        chosen = cached.get("chosen_skill")
        invoke = cached.get("invoke_command")
        conf = float(cached.get("confidence", 0.0))
        latency_ms = int((time.monotonic() - t_call) * 1000)
        _audit({
            "event": "llm_route_cache_hit",
            "prompt_hash": prompt_hash,
            "chosen_skill": chosen,
            "confidence": conf,
            "latency_ms": latency_ms,
            "provider": cached.get("provider", ""),
            "cache_hit": True,
        })
        if not chosen or not invoke:
            return None
        return LLMRouteResult(
            skill_name=chosen,
            invoke_command=invoke,
            confidence=conf,
            reason="LLM router (cached)",
            cache_hit=True,
            provider=cached.get("provider", ""),
        )

    # 4. Rate-limit guard.
    if _rate_limit_blocked():
        LOGGER.warning("llm-routing: hourly cap exceeded; returning None")
        _audit({
            "event": "llm_route_rate_limited",
            "prompt_hash": prompt_hash,
            "cache_hit": False,
        })
        return None

    # 5. Dispatch.
    prompt_text = build_prompt(user_prompt, top_candidates)
    if dispatch_fn is None:
        try:
            from lib.dispatch import dispatch as _real_dispatch  # noqa: WPS433
            dispatch_fn = _real_dispatch
        except ImportError:
            _audit({
                "event": "llm_route_dispatch_unavailable",
                "prompt_hash": prompt_hash,
                "cache_hit": False,
            })
            return None

    # Record the attempt BEFORE the call so concurrent processes share the budget.
    _rate_limit_record()
    try:
        result = dispatch_fn(
            prompt=prompt_text,
            task_type="skill_routing",
            timeout=DISPATCH_TIMEOUT_S,
        )
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("llm-routing dispatch raised: %s", exc)
        _audit({
            "event": "llm_route_dispatch_error",
            "prompt_hash": prompt_hash,
            "error": str(exc),
            "cache_hit": False,
        })
        return None

    success = bool(getattr(result, "success", False))
    text = str(getattr(result, "text", "") or "")
    provider = str(getattr(result, "provider_used", "") or "")
    latency_ms = int(getattr(result, "latency_ms", 0) or int((time.monotonic() - t_call) * 1000))

    if not success:
        _audit({
            "event": "llm_route_dispatch_failure",
            "prompt_hash": prompt_hash,
            "provider": provider,
            "latency_ms": latency_ms,
            "cache_hit": False,
        })
        return None

    chosen_invoke = parse_response(text, top_candidates)
    if chosen_invoke is None:
        _audit({
            "event": "llm_route_no_match",
            "prompt_hash": prompt_hash,
            "provider": provider,
            "latency_ms": latency_ms,
            "raw_response": text[:200],
            "cache_hit": False,
        })
        # Do NOT cache uncertain outcomes.
        return None

    # Map back to the originating candidate to recover skill_name + base conf.
    chosen_cand = next((c for c in top_candidates if c.invoke_command == chosen_invoke), None)
    if chosen_cand is None:
        return None

    # Confidence after LLM tie-break: lift to a fixed mid-band signal so
    # downstream best_match() (>=0.50) accepts it, but stay below the
    # 0.85 regex high-confidence band to preserve precedence semantics.
    final_conf = 0.70

    payload = {
        "chosen_skill": chosen_cand.skill_name,
        "invoke_command": chosen_invoke,
        "confidence": final_conf,
        "provider": provider,
    }
    _cache_write(key, payload)
    _audit({
        "event": "llm_route_success",
        "prompt_hash": prompt_hash,
        "chosen_skill": chosen_cand.skill_name,
        "confidence": final_conf,
        "latency_ms": latency_ms,
        "provider": provider,
        "cache_hit": False,
    })
    return LLMRouteResult(
        skill_name=chosen_cand.skill_name,
        invoke_command=chosen_invoke,
        confidence=final_conf,
        reason="LLM router tie-break",
        cache_hit=False,
        provider=provider,
    )


__all__ = [
    "BAND_LOW",
    "BAND_HIGH",
    "MIN_CANDIDATES_IN_BAND",
    "LLMCandidate",
    "LLMRouteResult",
    "build_prompt",
    "parse_response",
    "should_dispatch",
    "llm_route",
]
