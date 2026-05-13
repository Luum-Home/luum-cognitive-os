"""Unit tests for the ADR-297 LLM-dispatched routing fallback.

The module under test must:
  * short-circuit on the kill switch,
  * only dispatch on ambiguous semantic ties (gate),
  * cache decisions by (prompt, sorted-candidate-names),
  * enforce a rolling hourly cap,
  * stay vendor-neutral (no SDK imports),
  * parse responses strictly,
  * write an audit-trail line per invocation,
  * stay fast on cache hits (p95 < 100ms).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lib.llm_routing_fallback import (
    LLMCandidate,
    build_prompt,
    llm_route,
    parse_response,
    should_dispatch,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class _FakeDispatchResult:
    success: bool = True
    text: str = ""
    provider_used: str = "alibaba_qwen"
    latency_ms: int = 42


@pytest.fixture
def tmp_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate cache + metrics + state under a temp directory."""
    monkeypatch.setenv("COS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("COS_DISABLE_LLM_ROUTING", raising=False)
    monkeypatch.delenv("COS_LLM_ROUTING_HOURLY_CAP", raising=False)
    monkeypatch.delenv("COS_LLM_ROUTING_CACHE_TTL_DAYS", raising=False)
    return tmp_path


def _ambiguous_candidates(top_conf: float = 0.42) -> list[LLMCandidate]:
    """Build a 4-skill candidate list clustered in the ambiguity band."""
    return [
        LLMCandidate("alpha", "/alpha", top_conf, "Do alpha things"),
        LLMCandidate("beta", "/beta", top_conf - 0.04, "Do beta things"),
        LLMCandidate("gamma", "/gamma", top_conf - 0.08, "Do gamma things"),
        LLMCandidate("delta", "/delta", top_conf - 0.10, "Do delta things"),
    ]


# ---------------------------------------------------------------------------
# 1. Kill switch
# ---------------------------------------------------------------------------

def test_kill_switch_returns_none(tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COS_DISABLE_LLM_ROUTING", "1")
    sink = MagicMock()
    result = llm_route("do something ambiguous", _ambiguous_candidates(), dispatch_fn=sink)
    assert result is None
    sink.assert_not_called()


# ---------------------------------------------------------------------------
# 2. Trigger gate — clear winner skips
# ---------------------------------------------------------------------------

def test_trigger_gate_skips_when_clear_winner(tmp_project: Path) -> None:
    cands = [
        LLMCandidate("alpha", "/alpha", 0.78, "Do alpha things"),
        LLMCandidate("beta", "/beta", 0.40, "Do beta things"),
        LLMCandidate("gamma", "/gamma", 0.35, "Do gamma things"),
        LLMCandidate("delta", "/delta", 0.32, "Do delta things"),
    ]
    sink = MagicMock()
    assert llm_route("clear winner prompt", cands, dispatch_fn=sink) is None
    sink.assert_not_called()
    assert should_dispatch(cands) is False


# ---------------------------------------------------------------------------
# 3. Trigger gate — too few/weak candidates skips
# ---------------------------------------------------------------------------

def test_trigger_gate_skips_when_no_viable_candidates(tmp_project: Path) -> None:
    # Only one candidate, very low confidence.
    cands_weak = [LLMCandidate("alpha", "/alpha", 0.20, "Do alpha things")]
    sink = MagicMock()
    assert llm_route("nothing meaningful", cands_weak, dispatch_fn=sink) is None
    sink.assert_not_called()

    # Top in-band but only 2 candidates in the band → still skip.
    cands_two = [
        LLMCandidate("alpha", "/alpha", 0.40, "Do alpha"),
        LLMCandidate("beta", "/beta", 0.35, "Do beta"),
        LLMCandidate("gamma", "/gamma", 0.20, "Do gamma"),
    ]
    assert should_dispatch(cands_two) is False
    assert llm_route("two in band", cands_two, dispatch_fn=sink) is None
    sink.assert_not_called()


# ---------------------------------------------------------------------------
# 4. LLM called when ambiguous
# ---------------------------------------------------------------------------

def test_llm_called_when_ambiguous(tmp_project: Path) -> None:
    cands = _ambiguous_candidates()
    sink = MagicMock(return_value=_FakeDispatchResult(text="/beta"))
    result = llm_route("ambiguous prompt", cands, dispatch_fn=sink)
    assert sink.call_count == 1
    assert result is not None
    assert result.invoke_command == "/beta"
    assert result.skill_name == "beta"
    assert result.cache_hit is False
    assert result.confidence >= 0.5


# ---------------------------------------------------------------------------
# 5. Cache hit avoids dispatch
# ---------------------------------------------------------------------------

def test_cache_hit_avoids_dispatch(tmp_project: Path) -> None:
    cands = _ambiguous_candidates()
    sink = MagicMock(return_value=_FakeDispatchResult(text="/gamma"))
    first = llm_route("repeat me", cands, dispatch_fn=sink)
    assert first is not None
    second = llm_route("repeat me", cands, dispatch_fn=sink)
    assert second is not None
    assert second.cache_hit is True
    assert second.invoke_command == "/gamma"
    assert sink.call_count == 1  # second call must NOT hit dispatch


# ---------------------------------------------------------------------------
# 6. Rate limit degrades to None
# ---------------------------------------------------------------------------

def test_rate_limit_degrades_to_none(tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COS_LLM_ROUTING_HOURLY_CAP", "100")
    # Seed 100 recent entries.
    state_path = tmp_project / ".cognitive-os" / "state" / "llm-routing-rate.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    state_path.write_text(json.dumps({"entries": [now - 30 for _ in range(100)]}), encoding="utf-8")

    cands = _ambiguous_candidates()
    sink = MagicMock(return_value=_FakeDispatchResult(text="/alpha"))
    result = llm_route("over cap prompt", cands, dispatch_fn=sink)
    assert result is None
    sink.assert_not_called()


# ---------------------------------------------------------------------------
# 7. Vendor neutrality — no hardcoded providers in module source
# ---------------------------------------------------------------------------

def test_vendor_neutral_no_hardcoded_provider() -> None:
    module_path = Path(__file__).resolve().parents[2] / "lib" / "llm_routing_fallback.py"
    src = module_path.read_text(encoding="utf-8")
    # No direct vendor SDK imports
    assert "import anthropic" not in src
    assert "from anthropic" not in src
    assert "import openai" not in src
    assert "from openai" not in src
    # Module routes through lib.dispatch — primary integration point
    assert "lib.dispatch" in src


# ---------------------------------------------------------------------------
# 8. Invalid LLM response returns None
# ---------------------------------------------------------------------------

def test_invalid_llm_response_returns_none(tmp_project: Path) -> None:
    cands = _ambiguous_candidates()
    bad_responses = [
        "I think probably /beta is best",          # prose
        "/not-a-known-skill",                      # not in candidate list
        "",                                        # empty
        "/alpha or /beta",                         # multiple tokens
        "MAYBE",                                   # garbage token
    ]
    for response in bad_responses:
        sink = MagicMock(return_value=_FakeDispatchResult(text=response))
        # Use a fresh prompt to avoid cache crossover.
        result = llm_route(f"prompt for {response!r}", cands, dispatch_fn=sink)
        assert result is None, f"expected None for response={response!r}"

    # NONE is the only acceptable non-skill response and still returns None.
    sink_none = MagicMock(return_value=_FakeDispatchResult(text="NONE"))
    assert llm_route("explicit none", cands, dispatch_fn=sink_none) is None

    # And a successful single-token must work — proves parser isn't blanket-rejecting.
    sink_ok = MagicMock(return_value=_FakeDispatchResult(text="/alpha"))
    good = llm_route("good token prompt", cands, dispatch_fn=sink_ok)
    assert good is not None and good.invoke_command == "/alpha"


# ---------------------------------------------------------------------------
# 9. Audit trail written
# ---------------------------------------------------------------------------

def test_audit_trail_written(tmp_project: Path) -> None:
    cands = _ambiguous_candidates()
    sink = MagicMock(return_value=_FakeDispatchResult(text="/delta", provider_used="alibaba_qwen"))
    llm_route("audited prompt", cands, dispatch_fn=sink)
    metrics_file = tmp_project / ".cognitive-os" / "metrics" / "llm-routing.jsonl"
    assert metrics_file.exists()
    lines = [ln for ln in metrics_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    for key in ("ts", "event", "prompt_hash", "chosen_skill", "confidence", "latency_ms", "provider", "cache_hit"):
        assert key in rec, f"missing audit field: {key}"
    assert rec["chosen_skill"] == "delta"
    assert rec["provider"] == "alibaba_qwen"
    assert rec["cache_hit"] is False


# ---------------------------------------------------------------------------
# 10. Latency on warm cache (p95 < 100ms over 50 calls)
# ---------------------------------------------------------------------------

def test_latency_warm_cache_under_100ms(tmp_project: Path) -> None:
    cands = _ambiguous_candidates()
    sink = MagicMock(return_value=_FakeDispatchResult(text="/beta"))
    # Prime cache.
    first = llm_route("latency prompt", cands, dispatch_fn=sink)
    assert first is not None

    samples_ms: list[float] = []
    for _ in range(50):
        t0 = time.monotonic()
        r = llm_route("latency prompt", cands, dispatch_fn=sink)
        samples_ms.append((time.monotonic() - t0) * 1000)
        assert r is not None and r.cache_hit
    assert sink.call_count == 1  # only the prime call

    samples_ms.sort()
    p95 = samples_ms[int(0.95 * len(samples_ms))]
    assert p95 < 100.0, f"p95={p95:.1f}ms exceeds 100ms budget"


# ---------------------------------------------------------------------------
# Bonus: pure helpers
# ---------------------------------------------------------------------------

def test_should_dispatch_pure_predicate() -> None:
    assert should_dispatch([]) is False
    # Top above band → skip
    high = [LLMCandidate(f"s{i}", f"/s{i}", 0.60, "") for i in range(5)]
    assert should_dispatch(high) is False
    # Top below band → skip
    low = [LLMCandidate(f"s{i}", f"/s{i}", 0.20, "") for i in range(5)]
    assert should_dispatch(low) is False
    # In band but <3 candidates in band
    mixed = [
        LLMCandidate("a", "/a", 0.45, ""),
        LLMCandidate("b", "/b", 0.42, ""),
        LLMCandidate("c", "/c", 0.20, ""),
    ]
    assert should_dispatch(mixed) is False
    # In band with >=3 → trigger
    trig = [
        LLMCandidate("a", "/a", 0.45, ""),
        LLMCandidate("b", "/b", 0.42, ""),
        LLMCandidate("c", "/c", 0.38, ""),
    ]
    assert should_dispatch(trig) is True


def test_build_prompt_includes_all_candidates() -> None:
    cands = _ambiguous_candidates()
    text = build_prompt("hello", cands)
    for c in cands:
        assert c.invoke_command in text
    assert "NONE" in text


def test_parse_response_strict() -> None:
    cands = _ambiguous_candidates()
    assert parse_response("/alpha", cands) == "/alpha"
    assert parse_response("/alpha.", cands) == "/alpha"
    assert parse_response("NONE", cands) is None
    assert parse_response("none", cands) is None  # case sensitive on token
    # 'none' lowercased: first token == "none"; we accept upper-case NONE only.
    # The lowercase variant returns None either via NONE-branch or
    # invalid-token branch — both acceptable behaviours.
    assert parse_response("I think /beta", cands) is None
    assert parse_response("", cands) is None
    assert parse_response("/unknown", cands) is None


# ---------------------------------------------------------------------------
# Live LLM smoke test (skipped without explicit opt-in)
# ---------------------------------------------------------------------------

@pytest.mark.llm_routing
@pytest.mark.skipif(
    os.environ.get("COS_LLM_ROUTING_LIVE_TEST") != "1",
    reason="Live LLM test gated behind COS_LLM_ROUTING_LIVE_TEST=1",
)
def test_live_dispatch_roundtrip(tmp_project: Path) -> None:
    """Smoke test that exercises the real lib.dispatch.dispatch path."""
    cands = _ambiguous_candidates()
    result = llm_route("Which option fits best?", cands)
    # Either a valid pick or a clean None — but never an exception.
    if result is not None:
        assert result.invoke_command in {c.invoke_command for c in cands}
