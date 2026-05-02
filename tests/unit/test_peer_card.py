"""Unit tests for ADR-077 peer-card local user-memory helpers."""

from __future__ import annotations

import json

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
