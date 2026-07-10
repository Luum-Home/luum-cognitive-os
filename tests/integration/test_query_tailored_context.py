"""ADR-040 — Integration tests for query-tailored context injection.

Five test scenarios:
1. Task "refactor rate limiter" → top hit references ADR-028 or rate_limiter.
2. Task "fix UI bug" → no rate-limiter content injected.
3. Cache hit on identical task (latency <50ms).
4. Graceful when self-knowledge index missing (skip silently).
5. Graceful when no embeddings available (Jaccard fallback).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

# Ensure the repo root is on sys.path so cos_lib.context_injector is importable.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cos_lib.context_injector import (  # noqa: E402
    build_context,
    _task_hash,
    _cache_path,
    _prefer_synthesis,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def isolated_root(tmp_path: Path) -> Path:
    """Create a minimal project structure for context_injector tests."""
    # docs/02-Decisions/adrs with a rate-limiter ADR.
    adrs = tmp_path / "docs" / "02-Decisions" / "adrs"
    adrs.mkdir(parents=True)

    (adrs / "ADR-028-rate-limiter.md").write_text(
        "# ADR-028 — Rate Limiter\n\n"
        "## Context\n"
        "Controls agent bash_command call frequency (per-minute quota). "
        "lib/rate_limiter.py is the primary implementation. "
        "Hooks: hooks/rate-limiter.sh, hooks/rate-limit-precheck.sh.\n"
    )
    (adrs / "ADR-040-query-tailored-context-injection.md").write_text(
        "# ADR-040 — Query-Tailored Context Injection\n\n"
        "Semantic match for additionalContext.\n"
    )
    (adrs / "ADR-001-ui-routing.md").write_text(
        "# ADR-001 — UI Routing\n\n"
        "Frontend React router configuration and page navigation.\n"
    )

    # .cognitive-os directory (Jaccard code index with rate_limiter entry).
    cos = tmp_path / ".cognitive-os"
    cos.mkdir()

    index_items = [
        {
            "path": "lib/rate_limiter.py",
            "kind": "python",
            "tokens": ["rate", "limiter", "quota", "minute", "window", "bucket", "throttle"],
            "docstring_excerpt": "Rate limiter: per-minute quota enforcement for bash_command calls.",
        },
        {
            "path": "lib/dispatch.py",
            "kind": "python",
            "tokens": ["dispatch", "llm", "provider", "qwen", "claude", "route", "fallback"],
            "docstring_excerpt": "LLM dispatch: routes prompts to Qwen/Claude based on quota.",
        },
        {
            "path": "hooks/rate-limiter.sh",
            "kind": "shell",
            "tokens": ["rate", "limiter", "hook", "precheck", "minute", "bash", "command"],
            "docstring_excerpt": "PreToolUse hook — enforces per-minute bash_command rate limit.",
        },
    ]
    index_payload = {
        "version": 1,
        "built_at": "2026-04-30T00:00:00Z",
        "project_root": str(tmp_path),
        "items": index_items,
    }
    (cos / "reinvention-index.json").write_text(json.dumps(index_payload))

    # Minimal debt register.
    (cos / "debt-register.jsonl").write_text(
        json.dumps({
            "file": "lib/rate_limiter.py",
            "description": "rate_limiter window accumulates across sessions; should reset on startup",
        }) + "\n"
    )

    return tmp_path


# ---------------------------------------------------------------------------
# Test 1: rate-limiter task surfaces relevant context
# ---------------------------------------------------------------------------

def test_rate_limiter_task_hits_rate_limiter_content(isolated_root: Path) -> None:
    """Task 'refactor rate limiter' must produce context mentioning rate_limiter."""
    ctx = build_context("refactor rate limiter", project_root=isolated_root, use_cache=False)

    assert ctx, "Expected non-empty context for rate-limiter task"

    ctx_lower = ctx.lower()
    # At least one of the rate-limiter artefacts must appear.
    assert any(kw in ctx_lower for kw in ("rate_limiter", "rate-limiter", "adr-028", "rate limiter")), (
        f"Expected rate-limiter reference in context, got:\n{ctx}"
    )


# ---------------------------------------------------------------------------
# Test 2: unrelated task does not inject rate-limiter content
# ---------------------------------------------------------------------------

def test_unrelated_task_no_rate_limiter_content(isolated_root: Path) -> None:
    """Task 'fix UI bug' must NOT inject rate-limiter content."""
    # Add a UI-specific entry so the search has something to match.
    cos = isolated_root / ".cognitive-os"
    index_path = cos / "reinvention-index.json"
    payload = json.loads(index_path.read_text())
    payload["items"].append({
        "path": "lib/ui_router.py",
        "kind": "python",
        "tokens": ["ui", "router", "page", "navigation", "component", "render", "frontend"],
        "docstring_excerpt": "UI router: page navigation and component rendering.",
    })
    index_path.write_text(json.dumps(payload))

    ctx = build_context("fix UI bug in page navigation", project_root=isolated_root, use_cache=False)

    ctx_lower = ctx.lower()
    # rate-limiter content must NOT appear for a UI task.
    assert "rate_limiter" not in ctx_lower, (
        f"rate_limiter unexpectedly injected for UI task:\n{ctx}"
    )
    assert "rate-limiter" not in ctx_lower, (
        f"rate-limiter unexpectedly injected for UI task:\n{ctx}"
    )


# ---------------------------------------------------------------------------
# Test 3: cache hit is fast (<50ms)
# ---------------------------------------------------------------------------

def test_cache_hit_is_fast(isolated_root: Path) -> None:
    """Second call with same task must return from cache in <50ms."""
    task = "refactor rate limiter cache test"

    # First call — cold (populates cache).
    build_context(task, project_root=isolated_root, use_cache=True)

    # Second call — should be a cache hit.
    t0 = time.monotonic()
    build_context(task, project_root=isolated_root, use_cache=True)
    elapsed_ms = (time.monotonic() - t0) * 1000

    assert elapsed_ms < 50, (
        f"Cache hit took {elapsed_ms:.1f}ms, expected <50ms"
    )

    # Verify the cache file was actually written.
    cp = _cache_path(isolated_root)
    assert cp.exists(), "Cache file was not created"
    cache = json.loads(cp.read_text())
    h = _task_hash(task)
    assert h in cache, f"Task hash {h!r} not in cache"


# ---------------------------------------------------------------------------
# Test 4: missing self-knowledge index → silent skip
# ---------------------------------------------------------------------------

def test_graceful_when_index_missing(tmp_path: Path) -> None:
    """When no reinvention-index.json exists, build_context returns '' silently."""
    # Provide ADRs but no code index.
    adrs = tmp_path / "docs" / "02-Decisions" / "adrs"
    adrs.mkdir(parents=True)
    # No .cognitive-os/reinvention-index.json created.
    cos = tmp_path / ".cognitive-os"
    cos.mkdir()

    ctx = build_context("refactor rate limiter", project_root=tmp_path, use_cache=False)

    # Should not raise; may return empty or ADR-only context.
    # Key requirement: no exception raised.
    assert isinstance(ctx, str), "Expected str return even when index missing"


# ---------------------------------------------------------------------------
# Test 5: no sentence-transformers → Jaccard fallback still returns results
# ---------------------------------------------------------------------------

def test_jaccard_fallback_when_embeddings_unavailable(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When EmbeddingsIndex import fails, Jaccard fallback must still find results."""
    # Patch _search_code_embeddings to simulate ImportError / unavailability.
    import cos_lib.context_injector as ci

    def _no_embeddings(task: str, project_root: Path, top_k: int = 3) -> None:
        return None  # Simulates ImportError / unavailability

    monkeypatch.setattr(ci, "_search_code_embeddings", _no_embeddings)

    ctx = build_context("refactor rate limiter", project_root=isolated_root, use_cache=False)

    assert ctx, "Expected non-empty context even without embeddings (Jaccard fallback)"
    ctx_lower = ctx.lower()
    assert any(kw in ctx_lower for kw in ("rate_limiter", "rate-limiter", "adr-028", "rate limiter")), (
        f"Expected rate-limiter reference via Jaccard fallback, got:\n{ctx}"
    )


# ---------------------------------------------------------------------------
# Non-ADR synthesis remap (2026 KB rollout — Concepts/Methodology/…)
# ---------------------------------------------------------------------------

@pytest.fixture()
def kb_root(tmp_path: Path) -> Path:
    """Project root with a 04-Concepts doc that has a synthesis sibling and
    a 05-Methodology doc that does NOT (raw fallback)."""
    concepts = tmp_path / "docs" / "04-Concepts" / "architecture"
    concepts.mkdir(parents=True)
    # Raw source doc (scored) — distinctive topic tokens.
    (concepts / "harness-action-receipts.md").write_text(
        "# Harness Action Receipts\n\n"
        "Cryptographic receipt ledger recording every harness tool invocation "
        "for tamper-evident audit provenance and replay verification.\n"
    )
    # Curated Tier-1 synthesis sibling (the served target).
    (concepts / "harness-action-receipts.synthesis.md").write_text(
        "# Harness Action Receipts (synthesis)\n\n"
        "Synthesis: receipt ledger for harness tool invocation provenance.\n"
    )

    # Methodology doc with NO synthesis sibling → raw fallback.
    method = tmp_path / "docs" / "05-Methodology"
    method.mkdir(parents=True)
    (method / "planning-poker-cadence.md").write_text(
        "# Planning Poker Cadence\n\n"
        "Estimation calibration ritual using planning-poker fibonacci story "
        "point voting across the squad each sprint iteration.\n"
    )

    (tmp_path / ".cognitive-os").mkdir()
    return tmp_path


def test_non_adr_doc_serves_synthesis_sibling(kb_root: Path) -> None:
    """A query matching a 04-Concepts source doc must serve its
    .synthesis.md sibling, not the raw .md."""
    ctx = build_context(
        "cryptographic receipt ledger for harness tool invocation provenance",
        project_root=kb_root,
        use_cache=False,
    )
    assert ctx, f"Expected non-empty context, got: {ctx!r}"
    assert "harness-action-receipts.synthesis.md" in ctx, (
        f"Expected synthesis sibling to be served, got:\n{ctx}"
    )
    # The raw doc must NOT be surfaced directly when a synthesis page exists.
    assert "harness-action-receipts.md`" not in ctx.replace(".synthesis.md`", ""), (
        f"Raw doc surfaced instead of synthesis page:\n{ctx}"
    )


def test_non_adr_doc_raw_fallback_when_no_synthesis(kb_root: Path) -> None:
    """A query matching a 05-Methodology doc with no synthesis sibling must
    serve the raw .md (fallback)."""
    ctx = build_context(
        "estimation calibration planning-poker fibonacci story point voting squad",
        project_root=kb_root,
        use_cache=False,
    )
    assert ctx, f"Expected non-empty context, got: {ctx!r}"
    assert "planning-poker-cadence.md" in ctx, (
        f"Expected raw doc served as fallback, got:\n{ctx}"
    )


def test_adr_synthesis_behavior_unchanged(isolated_root: Path) -> None:
    """ADR remap must still serve ADR-NNN.synthesis.md when present and fall
    back to the raw ADR otherwise (no regression from the shared helper)."""
    adrs = isolated_root / "docs" / "02-Decisions" / "adrs"
    # Add a canonical synthesis page for ADR-028.
    (adrs / "ADR-028.synthesis.md").write_text(
        "# ADR-028 — Rate Limiter (synthesis)\n\nCurated per-minute quota summary.\n"
    )
    ctx = build_context("refactor rate limiter", project_root=isolated_root, use_cache=False)
    assert "ADR-028.synthesis.md" in ctx, (
        f"Expected ADR-028 synthesis to be served, got:\n{ctx}"
    )
    # ADR-040 has no synthesis page → raw ADR path must still be reachable via helper.
    served = _prefer_synthesis(adrs / "ADR-040-query-tailored-context-injection.md")
    assert served.name == "ADR-040-query-tailored-context-injection.md", (
        f"Expected raw ADR fallback, got: {served}"
    )


def test_prefer_synthesis_helper(kb_root: Path) -> None:
    """Direct unit coverage of the shared _prefer_synthesis remap helper."""
    concepts = kb_root / "docs" / "04-Concepts" / "architecture"
    method = kb_root / "docs" / "05-Methodology"
    # (a) general doc with synthesis sibling → synthesis served.
    assert _prefer_synthesis(concepts / "harness-action-receipts.md").name == (
        "harness-action-receipts.synthesis.md"
    )
    # (b) general doc without sibling → raw returned.
    assert _prefer_synthesis(method / "planning-poker-cadence.md").name == (
        "planning-poker-cadence.md"
    )
    # (c) a synthesis page is idempotent (returns itself, never double-mapped).
    syn = concepts / "harness-action-receipts.synthesis.md"
    assert _prefer_synthesis(syn) == syn
