# SCOPE: both
"""Peer-Card local user-memory model.

ADR-077 Phase 1 (no-embeddings v1 / FTS5-only) implementation.

A peer card is a single Engram observation per user storing structured facts:
``name``, ``role``, ``preferences``, ``communication_patterns``,
``domain_expertise``, ``recent_topics``. Stored as JSON content under topic
key ``user/peer-card`` (upsert on update).

This module is **storage-agnostic**: all Engram interactions go through a
``PeerCardStore`` protocol so tests can inject an in-memory backend without
spawning the engram CLI. The default backend wraps :func:`lib.safe_engram.safe_save`
for writes and ``engram search`` for reads.

Operations
----------
- :func:`read`     — return the current peer-card dict (empty schema if none).
- :func:`update`   — merge a partial dict into the card, preserving unrelated
                     fields, capping ``recent_topics`` and rejecting secrets.
- :func:`forget`   — clear a field or remove a list entry.
- :func:`explain`  — render a human-readable summary of provenance.
- :func:`detect_signals` — classify a user prompt into high/medium/none
                            confidence durable signals (used by the
                            ``user-prompt-capture`` hook).

Schema cap: ``recent_topics`` is capped at :data:`RECENT_TOPICS_CAP` (20). The
cap is documented in ``skills/peer-card/SKILL.md``.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOPIC_KEY = "user/peer-card"
"""Stable upsert key used by every peer-card write."""

OBSERVATION_TYPE = "peer-card"
"""Engram observation type for peer-card observations."""

OBSERVATION_SCOPE = "personal"
"""Engram scope — peer cards are user-personal, never project-shared."""

RECENT_TOPICS_CAP = 20
"""Maximum number of entries kept in ``recent_topics``.

Older entries are dropped FIFO when the cap is exceeded. This keeps the card
bounded in size and search-relevant: very old topics are irrelevant noise.
"""

# Fields the schema knows about. Extra keys passed to update() are dropped.
_KNOWN_FIELDS = (
    "name",
    "role",
    "preferences",
    "communication_patterns",
    "domain_expertise",
    "recent_topics",
)

# ---------------------------------------------------------------------------
# Secret / PII rejection
# ---------------------------------------------------------------------------

# Patterns for tokens, keys, secrets, and obvious PII that must NEVER be
# written to the peer card. Matching is conservative — false positives are
# better than leaking a credential into long-lived memory.
_SECRET_PATTERNS: Tuple[Tuple[str, "re.Pattern[str]"], ...] = tuple(
    (name, re.compile(pat, re.IGNORECASE))
    for name, pat in (
        # Generic key=value secrets
        ("api_key_assignment",
         r"(?:api[_-]?key|secret|token|password|passwd|bearer)\s*[:=]\s*['\"]?[A-Za-z0-9_\-./+=]{8,}"),
        # Common credential prefixes
        ("github_token",       r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
        ("aws_access_key",     r"\bAKIA[0-9A-Z]{12,}\b"),
        ("openai_key",         r"\bsk-[A-Za-z0-9]{20,}\b"),
        ("anthropic_key",      r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b"),
        ("private_key_block",  r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        ("jwt_like",           r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"),
        # PII / regulated identifiers
        ("us_ssn",             r"\b\d{3}-\d{2}-\d{4}\b"),
    )
)

# Credit-card detection — separate from _SECRET_PATTERNS because it needs a
# Luhn-checksum validator, not just a regex. Two-stage match:
#   1. Pull contiguous digit-with-separator candidates of plausible PAN length
#      (13-19 digits, optional space/dash every 4).
#   2. Strip separators, then verify both a known brand prefix AND Luhn.
# This avoids the prior regex pitfall where a single \b...{13,19}\b pattern
# silently dropped phone numbers, IBANs, and arbitrary IDs.
_CREDIT_CARD_CANDIDATE = re.compile(
    r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"
)

# Brand prefixes per ISO/IEC 7812-1 with allowed lengths. Each entry is
# ``(compiled_prefix_regex, allowed_lengths)`` matched against the digits-only
# string. Lengths are exact — Visa 13/16/19, MC 16, Amex 15, etc.
_CREDIT_CARD_BRANDS: Tuple[Tuple["re.Pattern[str]", Tuple[int, ...]], ...] = (
    (re.compile(r"^4\d+$"),                                        (13, 16, 19)),  # Visa
    (re.compile(r"^(?:5[1-5]|2(?:2(?:2[1-9]|[3-9]\d)|[3-6]\d{2}|7(?:[01]\d|20)))\d+$"),
                                                                   (16,)),         # MasterCard
    (re.compile(r"^3[47]\d+$"),                                    (15,)),         # Amex
    (re.compile(r"^(?:6011|65\d{2}|64[4-9]\d)\d+$"),               (16,)),         # Discover
    (re.compile(r"^35(?:2[89]|[3-8]\d)\d+$"),                      (16,)),         # JCB
    (re.compile(r"^3(?:0[0-5]|[68]\d)\d+$"),                       (14,)),         # Diners
)


def _luhn_valid(digits: str) -> bool:
    """Validate *digits* (a numeric string) against the Luhn (mod-10) checksum.

    Returns ``False`` for empty input or any non-digit character. Used to gate
    credit-card matches so that arbitrary 13-19 digit numbers (phone numbers,
    IBANs, account IDs) do not silently block legitimate peer-card updates.
    """
    if not digits or not digits.isdigit():
        return False
    total = 0
    # Walk right-to-left, double every second digit.
    for i, ch in enumerate(reversed(digits)):
        n = ord(ch) - 48  # ord('0') == 48
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _contains_credit_card(text: str) -> bool:
    """Return True if *text* contains a Luhn-valid PAN with a known brand prefix."""
    if not text:
        return False
    for match in _CREDIT_CARD_CANDIDATE.finditer(text):
        digits = re.sub(r"[ -]", "", match.group(0))
        if not _luhn_valid(digits):
            continue
        for prefix_re, lengths in _CREDIT_CARD_BRANDS:
            if len(digits) in lengths and prefix_re.match(digits):
                return True
    return False


def _contains_secret(text: str) -> Optional[str]:
    """Return the first matching secret-pattern name, or ``None`` if clean."""
    if not text:
        return None
    for name, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            return name
    if _contains_credit_card(text):
        return "credit_card"
    return None


def _scrub_value(value: Any) -> Optional[str]:
    """Reject *value* (recursively) if any sub-string looks like a secret.

    Returns the offending pattern name or ``None`` when the value is clean.
    """
    if isinstance(value, str):
        return _contains_secret(value)
    if isinstance(value, (list, tuple)):
        for item in value:
            hit = _scrub_value(item)
            if hit:
                return hit
        return None
    if isinstance(value, dict):
        for k, v in value.items():
            hit = _contains_secret(str(k)) or _scrub_value(v)
            if hit:
                return hit
        return None
    return None


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def empty_schema() -> Dict[str, Any]:
    """Return a fresh peer-card dict with all known fields populated."""
    return {
        "name": "",
        "role": "",
        "preferences": {},
        "communication_patterns": [],
        "domain_expertise": [],
        "recent_topics": [],
    }


def _coerce(card: Dict[str, Any]) -> Dict[str, Any]:
    """Fill in any missing keys with schema defaults; drop unknown keys."""
    out = empty_schema()
    for key in _KNOWN_FIELDS:
        if key in card:
            out[key] = card[key]
    return out


# ---------------------------------------------------------------------------
# Storage protocol — pluggable so tests can inject an in-memory backend.
# ---------------------------------------------------------------------------


class PeerCardStore(Protocol):
    """Backend contract — tests use an in-memory implementation."""

    def load(self) -> Optional[Dict[str, Any]]:
        """Return the most recent peer-card body, or ``None`` if absent."""
        ...

    def save(self, card: Dict[str, Any]) -> None:
        """Upsert *card* under the peer-card topic key."""
        ...


class InMemoryStore:
    """Reference store for tests and read-only previews.

    Accepts an optional initial card dict positionally so tests can preload a
    state. ``writes`` records every successful save for assertions; the
    initial seed is intentionally **not** counted as a write.
    """

    def __init__(self, initial: Optional[Dict[str, Any]] = None) -> None:
        self._card: Optional[Dict[str, Any]] = (
            _coerce(initial) if initial is not None else None
        )
        self.writes: List[Dict[str, Any]] = []

    def load(self) -> Optional[Dict[str, Any]]:
        return None if self._card is None else dict(self._card)

    def save(self, card: Dict[str, Any]) -> None:
        self._card = dict(card)
        self.writes.append(dict(card))


@dataclass
class EngramStore:
    """Default backend — reads via ``engram search``, writes via safe_save.

    FTS5-only retrieval (ADR-077 Phase 1). No embedding step.
    """

    engram_bin: str = ""
    timeout: int = 10

    def _bin(self) -> str:
        return self.engram_bin or os.environ.get("ENGRAM_BIN", "engram")

    def load(self) -> Optional[Dict[str, Any]]:
        """Search Engram by topic key and return the parsed JSON body."""
        try:
            proc = subprocess.run(
                [self._bin(), "search", "--query", TOPIC_KEY, "--json"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if proc.returncode != 0 or not proc.stdout.strip():
            return None
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return None

        # Support both list-of-results and dict-with-results shapes.
        results = payload if isinstance(payload, list) else payload.get("results", [])
        for entry in results:
            if entry.get("topic_key") != TOPIC_KEY:
                continue
            content = entry.get("content") or entry.get("body") or ""
            try:
                return _coerce(json.loads(content))
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    def save(self, card: Dict[str, Any]) -> None:
        """Persist *card* via :func:`lib.safe_engram.safe_save` (upsert)."""
        # Local import — keeps lib.peer_card importable in environments
        # where safe_engram's MemoryScanner deps are unavailable (tests).
        from lib.safe_engram import safe_save  # noqa: WPS433

        safe_save(
            title="peer-card",
            content=json.dumps(card, ensure_ascii=False, sort_keys=True),
            topic_key=TOPIC_KEY,
            type_=OBSERVATION_TYPE,
            scope=OBSERVATION_SCOPE,
        )


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------


@dataclass
class UpdateResult:
    """Outcome of :func:`update`. ``rejected`` is set on secret matches."""

    card: Dict[str, Any]
    written: bool
    rejected: Optional[str] = None  # secret-pattern name when blocked


def read(store: PeerCardStore) -> Dict[str, Any]:
    """Return the current peer card (empty schema if none stored)."""
    loaded = store.load()
    return _coerce(loaded) if loaded else empty_schema()


def update(store: PeerCardStore, patch: Dict[str, Any]) -> UpdateResult:
    """Merge *patch* into the stored peer card.

    Behavior:

    - Secrets / PII in *patch* values cause the entire update to be rejected
      (no partial writes). The current card is returned unchanged.
    - Unrelated fields are preserved (per ADR-077 §Resolved Q3 invariant).
    - ``preferences`` merges shallowly (key-level upsert).
    - List fields (``communication_patterns``, ``domain_expertise``) deduplicate
      while preserving insertion order.
    - ``recent_topics`` is appended-then-trimmed to :data:`RECENT_TOPICS_CAP`,
      keeping the most recent entries.
    """
    secret_hit = _scrub_value(patch)
    current = read(store)
    if secret_hit:
        return UpdateResult(card=current, written=False, rejected=secret_hit)

    merged = dict(current)

    if "name" in patch and isinstance(patch["name"], str):
        merged["name"] = patch["name"].strip()
    if "role" in patch and isinstance(patch["role"], str):
        merged["role"] = patch["role"].strip()

    if isinstance(patch.get("preferences"), dict):
        prefs = dict(merged.get("preferences") or {})
        prefs.update({str(k): v for k, v in patch["preferences"].items()})
        merged["preferences"] = prefs

    for list_field in ("communication_patterns", "domain_expertise"):
        incoming = patch.get(list_field)
        if isinstance(incoming, list):
            existing = list(merged.get(list_field) or [])
            for item in incoming:
                if isinstance(item, str) and item and item not in existing:
                    existing.append(item)
            merged[list_field] = existing

    incoming_topics = patch.get("recent_topics")
    if isinstance(incoming_topics, list):
        topics = list(merged.get("recent_topics") or [])
        for topic in incoming_topics:
            if not isinstance(topic, str) or not topic:
                continue
            # Move-to-end semantics so most recent stays at tail.
            if topic in topics:
                topics.remove(topic)
            topics.append(topic)
        if len(topics) > RECENT_TOPICS_CAP:
            topics = topics[-RECENT_TOPICS_CAP:]
        merged["recent_topics"] = topics

    store.save(merged)
    return UpdateResult(card=merged, written=True)


def forget(store: PeerCardStore, target: str) -> Dict[str, Any]:
    """Remove a field or list entry from the peer card.

    *target* may be:

    - A schema field name (``"name"``, ``"role"``, ``"preferences"``, …)
      → reset to its empty default.
    - ``"preferences.<key>"`` → drop that single preference key.
    - A literal string present in any list field → remove the entry.
    """
    card = read(store)

    if target in _KNOWN_FIELDS:
        card[target] = empty_schema()[target]
        store.save(card)
        return card

    if target.startswith("preferences."):
        key = target.split(".", 1)[1]
        prefs = dict(card.get("preferences") or {})
        prefs.pop(key, None)
        card["preferences"] = prefs
        store.save(card)
        return card

    changed = False
    for list_field in ("communication_patterns", "domain_expertise", "recent_topics"):
        items = list(card.get(list_field) or [])
        if target in items:
            card[list_field] = [x for x in items if x != target]
            changed = True
    if changed:
        store.save(card)
    return card


def explain(store: PeerCardStore) -> str:
    """Return a plain-text summary of the peer card.

    Provenance for individual facts is not tracked in Phase 1 (the schema does
    not store source spans). The output explicitly states this so the agent
    surfacing the card does not invent justifications. ADR-077 §Resolved Q3
    requires this honest disclosure.
    """
    card = read(store)
    lines: List[str] = ["Peer card (ADR-077, FTS5-only)"]
    name = card.get("name") or "(unset)"
    role = card.get("role") or "(unset)"
    lines.append(f"  name: {name}")
    lines.append(f"  role: {role}")

    prefs = card.get("preferences") or {}
    if prefs:
        lines.append("  preferences:")
        for k, v in sorted(prefs.items()):
            lines.append(f"    - {k}: {v}")
    else:
        lines.append("  preferences: (none)")

    for label, key in (
        ("communication_patterns", "communication_patterns"),
        ("domain_expertise", "domain_expertise"),
        ("recent_topics", "recent_topics"),
    ):
        items = card.get(key) or []
        if items:
            lines.append(f"  {label}:")
            for item in items:
                lines.append(f"    - {item}")
        else:
            lines.append(f"  {label}: (none)")

    lines.append(
        "Provenance: Phase 1 does not store source spans; facts above are "
        "the result of explicit user statements or session-end consolidation."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Signal detection (ADR-077 §Resolved Q2)
# ---------------------------------------------------------------------------


@dataclass
class Signal:
    """A durable-preference signal extracted from a user prompt."""

    confidence: str  # "high" | "medium" | "none"
    patch: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""


# High-confidence cues — explicit durable preference commands or stable
# identity facts. These trigger immediate writes from the hook.
_HIGH_CUES_EN = re.compile(
    r"\b(from now on|always|never|i prefer|call me|"
    r"remember that|don'?t remember that|that'?s wrong about me|update my preference|"
    r"my name is|i am a|i'?m a |my role is)\b",
    re.IGNORECASE,
)
_HIGH_CUES_ES = re.compile(
    r"\b(de ahora en (m[aá]s|adelante)|siempre|nunca|prefiero|llam[aá](me|enme)|"
    r"record[aá] que|no recordar|eso est[aá] mal sobre m[ií]|actualiz[aá] mi preferencia|"
    r"mi nombre es|soy un[ao]?|mi rol es)\b",
    re.IGNORECASE,
)

# Medium-confidence cues — recurring style/format feedback. Buffered, not
# immediately written by the hook.
_MEDIUM_CUES = re.compile(
    r"\b(prefer|gusta|m[aá]s corto|menos verboso|less verbose|shorter|"
    r"bullet points|in spanish|en espa[ñn]ol|in english|en ingl[eé]s)\b",
    re.IGNORECASE,
)

_NAME_RE = re.compile(
    r"(?:my name is|call me|mi nombre es|llamame|llámame)\s+([A-Za-zÀ-ÿ][\w\-']{0,40})",
    re.IGNORECASE,
)
_ROLE_RE = re.compile(
    r"(?:i am a|i'?m a|my role is|soy (?:un[ao]?|el|la)|mi rol es)\s+"
    r"([A-Za-zÀ-ÿ][\w\- ]{2,60})",
    re.IGNORECASE,
)
_LANG_PREFS = (
    (re.compile(r"\b(in spanish|en espa[ñn]ol|habl[aá] espa[ñn]ol)\b", re.IGNORECASE), "es"),
    (re.compile(r"\b(in english|en ingl[eé]s|speak english)\b", re.IGNORECASE), "en"),
)


def detect_signals(prompt: str) -> Signal:
    """Classify *prompt* into a :class:`Signal`.

    Only high-confidence signals carry a structured ``patch``; medium cues
    return ``confidence='medium'`` with an empty patch so the hook can buffer
    them for session-end consolidation. Secrets always downgrade to ``none``.
    """
    if not prompt or not prompt.strip():
        return Signal(confidence="none")

    if _contains_secret(prompt):
        return Signal(confidence="none", reason="secret_detected")

    has_high = bool(_HIGH_CUES_EN.search(prompt) or _HIGH_CUES_ES.search(prompt))

    if has_high:
        patch: Dict[str, Any] = {}
        m = _NAME_RE.search(prompt)
        if m:
            patch["name"] = m.group(1).strip(" .,'\"")
        m = _ROLE_RE.search(prompt)
        if m:
            role = m.group(1).strip(" .,'\"")
            # Heuristic floor: drop role candidates that are too short / generic.
            if len(role) >= 3:
                patch["role"] = role
        for pattern, lang in _LANG_PREFS:
            if pattern.search(prompt):
                patch.setdefault("preferences", {})["language"] = lang
                break

        # Even with a high cue, an empty patch is still useful for the hook:
        # it knows the prompt was intentful but did not yield extractable
        # fields, so it can defer to medium-confidence consolidation.
        if patch:
            return Signal(confidence="high", patch=patch, reason="durable_signal")
        return Signal(confidence="medium", reason="high_cue_no_extraction")

    if _MEDIUM_CUES.search(prompt):
        return Signal(confidence="medium", reason="style_cue")

    return Signal(confidence="none")


# ---------------------------------------------------------------------------
# Hook entry point — invoked by user-prompt-capture.sh
# ---------------------------------------------------------------------------


def hook_capture(prompt: str, store: Optional[PeerCardStore] = None) -> Signal:
    """Hook helper: detect signals and update the peer card on high confidence.

    Returns the detected :class:`Signal`. Medium-confidence signals are *not*
    written immediately (per ADR-077 §Resolved Q2 — buffered for session-end
    consolidation). Secrets are silently rejected.

    The default store is :class:`EngramStore`; tests pass an in-memory store.
    """
    signal = detect_signals(prompt)
    if signal.confidence != "high" or not signal.patch:
        return signal

    backend = store if store is not None else EngramStore()
    update(backend, signal.patch)
    return signal


# ---------------------------------------------------------------------------
# CLI — `python3 -m lib.peer_card <op> [...]`
# ---------------------------------------------------------------------------


def _cli(argv: List[str]) -> int:
    if not argv:
        print("usage: peer_card <hook|read|explain> [...]", flush=True)
        return 2
    op = argv[0]
    if op == "hook":
        try:
            text = sys.stdin.read()
        except (OSError, ValueError):
            # Stdin unavailable (e.g. captured by a test harness).
            text = ""
        signal = hook_capture(text)
        # Single-line JSON for easy log scraping.
        print(json.dumps({"confidence": signal.confidence, "reason": signal.reason}))
        return 0
    if op == "read":
        print(json.dumps(read(EngramStore()), ensure_ascii=False, indent=2))
        return 0
    if op == "explain":
        print(explain(EngramStore()))
        return 0
    print(f"unknown op: {op}", flush=True)
    return 2


if __name__ == "__main__":  # pragma: no cover — exercised via CLI tests
    raise SystemExit(_cli(sys.argv[1:]))
