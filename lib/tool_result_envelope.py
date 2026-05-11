# SCOPE: both
"""Tool Result Envelope — compact envelope format for large tool outputs (ADR-264).

When a tool result exceeds ``ENVELOPE_THRESHOLD`` bytes, ``wrap_if_large`` replaces
the raw output with a structured Markdown envelope that preserves:

- The first ``ENVELOPE_PREVIEW_SIZE`` characters as a human-readable preview.
- Metadata: real size, tool name, target hint.
- An optional pointer to the full payload written to spillover storage.

Design:
- Pure stdlib — no external dependencies.
- Idempotent: calling ``wrap_if_large`` on an already-enveloped string is a no-op.
- Composable with ADR-263 (tool-replay ledger): when ledger returns REFERENCE_ONLY,
  pass ``preview_size=0`` to collapse the envelope to pointer-only.

Spillover storage location::

    .cognitive-os/sessions/<session-id>/envelopes/<sha256>.txt

Session ID resolution order:
    1. ``COS_SESSION_ID`` environment variable.
    2. ``.cognitive-os/sessions/.current`` file (first line).
    3. ``pid-<pid>`` fallback.

Pattern adopted from holaOS (clean-room rewrite).
Source-pattern: .private/holaos-research/holaos-annex-g-surprise-findings.md §G1
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Threshold in bytes above which a tool result gets enveloped (ADR-264 §Context).
#: 28 KB ≈ 7 000 tokens ≈ 3.5% of Claude Code's 200K-token context window.
ENVELOPE_THRESHOLD: int = 28 * 1024

#: Number of characters exposed in the envelope preview.
ENVELOPE_PREVIEW_SIZE: int = 7 * 1024

#: Marker string present in every rendered envelope — used for idempotency detection.
_ENVELOPE_MARKER: str = "[TOOL RESULT ENVELOPE]"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class EnvelopePreview:
    """Structured representation of a large tool result."""

    preview_text: str          # First ~7 KB of the original result
    full_chars: int            # Real size in characters
    tool_name: str             # Name of the tool that produced the result
    target_hint: str           # e.g. file path, URL, shell command
    full_pointer: Optional[str]  # Absolute path to spillover file, or None


# ---------------------------------------------------------------------------
# Session ID resolution
# ---------------------------------------------------------------------------


def _get_session_id() -> str:
    """Resolve the current session ID.

    Order of precedence:
    1. ``COS_SESSION_ID`` environment variable.
    2. First line of ``.cognitive-os/sessions/.current``.
    3. ``pid-<pid>`` fallback.
    """
    env_sid = os.environ.get("COS_SESSION_ID", "").strip()
    if env_sid:
        return env_sid

    current_file = Path(".cognitive-os") / "sessions" / ".current"
    try:
        text = current_file.read_text(encoding="utf-8").strip()
        if text:
            return text.splitlines()[0].strip()
    except OSError:
        pass

    return f"pid-{os.getpid()}"


def _default_spillover_dir() -> Path:
    """Return the default spillover directory for the current session."""
    return Path(".cognitive-os") / "sessions" / _get_session_id() / "envelopes"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def render_envelope(ep: EnvelopePreview) -> str:
    """Render an EnvelopePreview as a Markdown string for model consumption.

    Format (exact, per ADR-264 §2)::

        [TOOL RESULT ENVELOPE]
        tool: <tool_name>
        target: <target_hint>
        full_size: <N> chars (truncated; preview below)
        full_pointer: <path-or-none>

        --- preview (<M> chars) ---
        <preview_text>
        --- end preview ---
    """
    pointer_str = ep.full_pointer if ep.full_pointer is not None else "none"
    preview_chars = len(ep.preview_text)

    lines = [
        _ENVELOPE_MARKER,
        f"tool: {ep.tool_name}",
        f"target: {ep.target_hint}",
        f"full_size: {ep.full_chars} chars (truncated; preview below)",
        f"full_pointer: {pointer_str}",
        "",
        f"--- preview ({preview_chars} chars) ---",
        ep.preview_text,
        "--- end preview ---",
    ]
    return "\n".join(lines)


def wrap_if_large(
    raw_result: str,
    tool_name: str,
    target_hint: str,
    threshold: int = ENVELOPE_THRESHOLD,
    preview_size: int = ENVELOPE_PREVIEW_SIZE,
    persist_full: bool = True,
    spillover_dir: Optional[str] = None,
) -> str:
    """Return raw_result unchanged if it fits within threshold.

    If ``len(raw_result) > threshold``, returns a structured Markdown envelope
    with a preview of the first ``preview_size`` characters, metadata, and
    optionally a pointer to the full payload on disk.

    Args:
        raw_result:    The full tool output string.
        tool_name:     Name of the tool that produced ``raw_result``.
        target_hint:   Human-readable hint about what was targeted (path, URL…).
        threshold:     Maximum size (characters) before enveloping kicks in.
                       Pass ``math.inf`` to disable enveloping.
        preview_size:  Number of characters to include in the envelope preview.
        persist_full:  When True (default), write the full payload to spillover
                       storage and set ``full_pointer``. When False, no file is
                       written and ``full_pointer`` is None.
        spillover_dir: Override the default spillover directory. Must be a
                       string path; created on first write.

    Returns:
        ``raw_result`` unchanged if small enough, otherwise an envelope string.
    """
    # Idempotency guard: never re-wrap an already-enveloped string.
    if _ENVELOPE_MARKER in raw_result:
        return raw_result

    if len(raw_result) <= threshold:
        return raw_result

    # Build spillover path using SHA-256 of the raw content.
    sha256_hex = hashlib.sha256(raw_result.encode("utf-8", errors="replace")).hexdigest()
    # Use first 64 chars of digest as filename (full SHA-256 is 64 hex chars).
    filename = sha256_hex[:64] + ".txt"

    full_pointer: Optional[str] = None
    if persist_full:
        spill_path = (
            Path(spillover_dir) if spillover_dir is not None else _default_spillover_dir()
        )
        spill_path.mkdir(parents=True, exist_ok=True)
        spill_file = spill_path / filename
        try:
            spill_file.write_text(raw_result, encoding="utf-8")
            full_pointer = str(spill_file.resolve())
        except OSError:
            # If we can't write, degrade gracefully — no pointer, but no crash.
            full_pointer = None

    preview_text = raw_result[:preview_size]

    ep = EnvelopePreview(
        preview_text=preview_text,
        full_chars=len(raw_result),
        tool_name=tool_name,
        target_hint=target_hint,
        full_pointer=full_pointer,
    )
    return render_envelope(ep)
