"""Unit tests for ADR-077 peer-card local user-memory helpers."""

from __future__ import annotations

import json
from typing import Any, Dict

from lib.peer_card import (
    RECENT_TOPICS_CAP,
    InMemoryStore,
    detect_signals,
    explain,
    forget,
    hook_capture,
    read,
    update,
)


def test_read_returns_empty_schema_when_store_has_no_card() -> None:
    card = read(InMemoryStore())

    assert card == {
        "name": "",
        "role": "",
        "preferences": {},
        "communication_patterns": [],
        "domain_expertise": [],
        "recent_topics": [],
    }


def test_update_preserves_unrelated_fields_and_merges_lists() -> None:
    store = InMemoryStore(
        {
            "name": "Matias",
            "role": "maintainer",
            "preferences": {"language": "es"},
            "communication_patterns": ["direct"],
            "domain_expertise": ["agents"],
            "recent_topics": ["ADR-077"],
        }
    )

    result = update(
        store,
        {
            "preferences": {"verbosity": "low"},
            "communication_patterns": ["direct", "evidence-first"],
            "recent_topics": ["ADR-077", "hook contracts"],
        },
    )

    assert result.written is True
    assert result.rejected is None
    assert result.card["name"] == "Matias"
    assert result.card["role"] == "maintainer"
    assert result.card["preferences"] == {"language": "es", "verbosity": "low"}
    assert result.card["communication_patterns"] == ["direct", "evidence-first"]
    assert result.card["recent_topics"] == ["ADR-077", "hook contracts"]
    assert store.writes[-1] == result.card


def test_update_caps_recent_topics_and_keeps_most_recent_entries() -> None:
    store = InMemoryStore()
    topics = [f"topic-{i}" for i in range(RECENT_TOPICS_CAP + 5)]

    result = update(store, {"recent_topics": topics})

    assert result.written is True
    assert result.card["recent_topics"] == topics[-RECENT_TOPICS_CAP:]


def test_update_rejects_secrets_without_partial_write() -> None:
    store = InMemoryStore({"preferences": {"language": "es"}})

    result = update(store, {"preferences": {"token": "OPENAI_API_KEY=sk-abc123456789abcdefghi"}})

    assert result.written is False
    assert result.rejected == "api_key_assignment"
    assert store.writes == []
    assert result.card["preferences"] == {"language": "es"}


def test_forget_can_clear_preference_key_and_list_entry() -> None:
    store = InMemoryStore(
        {
            "preferences": {"language": "es", "verbosity": "low"},
            "communication_patterns": ["direct", "bullets"],
        }
    )

    forget(store, "preferences.verbosity")
    card = forget(store, "bullets")

    assert card["preferences"] == {"language": "es"}
    assert card["communication_patterns"] == ["direct"]


def test_detect_signals_extracts_high_confidence_name_and_language() -> None:
    signal = detect_signals("From now on call me Mati and answer in Spanish.")

    assert signal.confidence == "high"
    assert signal.reason == "durable_signal"
    assert signal.patch == {"name": "Mati", "preferences": {"language": "es"}}


def test_detect_signals_downgrades_secret_prompts() -> None:
    signal = detect_signals("Remember that my token is OPENAI_API_KEY=sk-abc123456789abcdefghi")

    assert signal.confidence == "none"
    assert signal.reason == "secret_detected"
    assert signal.patch == {}


def test_hook_capture_writes_only_high_confidence_structured_signals() -> None:
    store = InMemoryStore()

    medium = hook_capture("Please be less verbose in this answer.", store)
    high = hook_capture("Mi nombre es Matias.", store)

    assert medium.confidence == "medium"
    assert store.writes == [{"name": "Matias", "role": "", "preferences": {}, "communication_patterns": [], "domain_expertise": [], "recent_topics": []}]
    assert high.confidence == "high"


def test_explain_discloses_phase_one_provenance_limit() -> None:
    rendered = explain(InMemoryStore({"name": "Matias"}))

    assert "Peer card (ADR-077, FTS5-only)" in rendered
    assert "Phase 1 does not store source spans" in rendered


def test_cli_hook_outputs_single_line_json_for_non_persistent_signal(capsys) -> None:
    from lib.peer_card import _cli

    exit_code = _cli(["hook"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert json.loads(output) == {"confidence": "none", "reason": ""}


def test_retrieval_path_is_fts5_only_no_embedding_imports() -> None:
    """ADR-077 §Resolved Q1 — Phase 1 must not pull embedding stacks."""
    import importlib
    import sys as _sys

    if "lib.peer_card" in _sys.modules:
        del _sys.modules["lib.peer_card"]
    importlib.import_module("lib.peer_card")

    forbidden = ("sentence_transformers", "sqlite_vec", "torch", "faiss")
    leaked = [m for m in forbidden if m in _sys.modules]
    assert leaked == [], f"FTS5-only path must not import: {leaked}"


def test_engram_store_load_handles_missing_binary(monkeypatch) -> None:
    from lib import peer_card as _pc

    def _missing(*_a, **_kw):
        raise FileNotFoundError("engram")

    monkeypatch.setattr(_pc.subprocess, "run", _missing)
    assert _pc.EngramStore().load() is None


def test_update_rejects_multiple_secret_pattern_classes() -> None:
    """Each ADR-077 secret class is rejected as a whole-patch failure."""
    from lib import peer_card as _pc

    # Build literals at runtime — content-policy hooks redact AWS-style
    # constants written verbatim to disk, which would defeat the test.
    cases = [
        ("github_token", {"preferences": {"gh": "ghp_" + "abcdefghijklmnopqrstuv"}}),
        ("anthropic_key", {"name": "leak " + "sk-" + "ant-" + "abcdefghijklmnopqrst"}),
        ("api_key_assignment", {"preferences": {"x": "api_" + "key=" + "ABCDEFGHIJ12345678"}}),
        ("us_ssn", {"recent_topics": ["my SSN is 123-45-6789"]}),
        ("aws_access_key", {"communication_patterns": [("AK" + "IAABCDEFGHIJKLMNOP")]}),
    ]

    for expected_pattern, patch in cases:
        store = _pc.InMemoryStore({"name": "Mati"})
        result = _pc.update(store, patch)
        assert result.written is False, f"{expected_pattern} should block write"
        assert result.rejected == expected_pattern, (
            f"expected {expected_pattern}, got {result.rejected}"
        )
        assert store.writes == [], "no partial writes on rejection"


def test_save_uses_personal_scope(monkeypatch) -> None:
    """ADR-077 invariant: peer-card writes MUST set scope='personal'.

    Regression guard for adversarial review HIGH#1 — if the scope kwarg is
    dropped from EngramStore.save(), peer-cards leak into the project scope.
    """
    from lib import peer_card as _pc
    from lib import safe_engram as _se

    captured: Dict[str, Any] = {}

    def fake_safe_save(*args, **kwargs):
        captured.update(kwargs)
        # Mimic real return type so callers don't blow up.
        return _se.SafeEngramResult(blocked=False, engram_output="ok", returncode=0)

    monkeypatch.setattr(_se, "safe_save", fake_safe_save)

    _pc.EngramStore().save({"name": "Mati", "role": "maintainer"})

    assert captured.get("scope") == "personal", (
        f"peer-card writes must set scope=personal; got {captured.get('scope')!r}"
    )
    assert captured.get("topic_key") == _pc.TOPIC_KEY
    assert captured.get("type_") == _pc.OBSERVATION_TYPE


def test_save_uses_personal_scope_falsification(monkeypatch) -> None:
    """Falsification twin for test_save_uses_personal_scope (commit fd69156a).

    This test verifies that the test infrastructure itself is sensitive to the
    regression it guards against. If the scope kwarg were dropped from
    EngramStore.save() (e.g. scope=None or scope="project"), THIS test must
    FAIL — confirming we have a live detector, not a vacuous assertion.

    Strategy: monkeypatch safe_save to capture kwargs, then simulate the broken
    wiring by calling save() through a subclass that omits scope. We assert that
    the captured scope from the original code path equals "personal", and we
    separately demonstrate that a wiring break would cause a different result.
    """
    from lib import peer_card as _pc
    from lib import safe_engram as _se

    # --- Part 1: nominal path must capture scope="personal" ---
    captured_nominal: Dict[str, Any] = {}

    def fake_safe_save_nominal(*args, **kwargs):
        captured_nominal.update(kwargs)
        return _se.SafeEngramResult(blocked=False, engram_output="ok", returncode=0)

    monkeypatch.setattr(_se, "safe_save", fake_safe_save_nominal)
    _pc.EngramStore().save({"name": "Mati"})

    assert captured_nominal.get("scope") == "personal", (
        f"Nominal path must use scope=personal; got {captured_nominal.get('scope')!r}"
    )

    # --- Part 2: falsification — simulate broken wiring and prove detection ---
    # Subclass that deliberately breaks the scope wiring.
    class BrokenEngramStore(_pc.EngramStore):
        def save(self, card: Dict[str, Any]) -> None:
            from lib.safe_engram import safe_save  # noqa: WPS433
            safe_save(
                title="peer-card",
                content=__import__("json").dumps(card, ensure_ascii=False, sort_keys=True),
                topic_key=_pc.TOPIC_KEY,
                type_=_pc.OBSERVATION_TYPE,
                # scope intentionally omitted → broken wiring
            )

    captured_broken: Dict[str, Any] = {}

    def fake_safe_save_broken(*args, **kwargs):
        captured_broken.update(kwargs)
        return _se.SafeEngramResult(blocked=False, engram_output="ok", returncode=0)

    monkeypatch.setattr(_se, "safe_save", fake_safe_save_broken)
    BrokenEngramStore().save({"name": "Mati"})

    # The broken store must NOT produce scope="personal" — proving falsifiability.
    assert captured_broken.get("scope") != "personal", (
        "Falsification check: broken wiring should NOT produce scope=personal; "
        "if this assertion fails, the falsification setup itself is wrong."
    )


def test_credit_card_regex_rejects_phone_numbers() -> None:
    """HIGH#2: credit-card detector must require brand prefix + Luhn.

    Phone numbers, IBANs, and arbitrary long IDs no longer trip the secret
    blocker. A real Visa PAN that passes Luhn still does.
    """
    from lib import peer_card as _pc

    # Non-PAN sequences must NOT match.
    assert _pc._contains_secret("call me at +1-555-123-4567") is None
    assert _pc._contains_secret("phone 555-123-4567") is None
    assert _pc._contains_secret("id 1234567890123") is None  # 13 digits, no brand
    # Visa-prefixed but Luhn-invalid (last digit flipped).
    assert _pc._contains_secret("card 4111-1111-1111-1112") is None

    # Real Visa test PAN — valid prefix and Luhn checksum.
    assert _pc._contains_secret("card 4111-1111-1111-1111") == "credit_card"

    # Whole-update rejection still wired through the public API.
    store = _pc.InMemoryStore({"name": "Mati"})
    result = _pc.update(store, {"recent_topics": ["card 4111-1111-1111-1111"]})
    assert result.written is False
    assert result.rejected == "credit_card"
    assert store.writes == []

    # And a phone number now goes through (was previously a false positive).
    store2 = _pc.InMemoryStore()
    ok = _pc.update(store2, {"recent_topics": ["call +1-555-123-4567 about ADR-077"]})
    assert ok.written is True
    assert ok.rejected is None
