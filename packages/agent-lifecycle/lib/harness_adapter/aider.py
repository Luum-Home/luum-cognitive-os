"""Aider adapter — hardened with version dispatch (ADR-033b).

Aider does not invoke hooks. Instead, it writes a running transcript to
``.aider.chat.history.md`` at the project root. This adapter is a *passive
file-watcher* POC: given a raw payload ``{"history_file": "/path/.aider.chat.history.md"}``
or a tail delta in ``{"new_lines": ["..."]}``, it emits canonical events.

ADR-033b hardening:
- Version detection via header parse (``#### aider v0.XX.Y``).
- Per-version regex dispatch; falls back to "best effort" for unknown versions.
- Emits :class:`~.base.ParseError` canonical event instead of silent skip when
  a non-blank line matches no known pattern.
- Raises :exc:`UnsupportedAiderVersion` when a detected version is outside
  the supported range ``>=0.60, <0.71``.
- Version range pinned in this docstring: **aider>=0.60,<0.71**.

Supported version corpus:
    0.60.x — classic `#### prompt` + `> tool: rest` format
    0.65.x — adds `> Linting …` lines + multi-file edit markers
    0.70.x — adds `> Running tests …` + result summary lines

Wave 2 (Python API migration) is documented in ADR-033b §Rollout but is NOT
implemented here — it is deferred to a dedicated follow-up task.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from .base import (
    AgentEnd,
    AgentStart,
    CanonicalEvent,
    HarnessAdapter,
    HarnessName,
    ParseError,
    ToolUse,
    now_epoch,
)

# ---------------------------------------------------------------------------
# Version support constants
# ---------------------------------------------------------------------------

_MIN_VERSION = (0, 60)
_MAX_VERSION = (0, 71)  # exclusive


class UnsupportedAiderVersion(ValueError):
    """Raised when a transcript header declares a version outside the supported range."""


# ---------------------------------------------------------------------------
# Per-version regex tables
# ---------------------------------------------------------------------------

# Shared patterns
_HEADER_RE = re.compile(r"^#{1,4}\s+aider\s+v?(\d+)\.(\d+)", re.IGNORECASE)
_USER_RE = re.compile(r"^#{4}\s+(.+)$")

# Base patterns (0.60+): user prompt and classic tool lines
_TOOL_BASE_RE = re.compile(
    r"^>\s+(?P<tool>Ran shell command|Applied edit|Saved file):\s+(?P<rest>.+)$"
)

# 0.65+ adds linting and multi-file markers
# "Linting src/foo.py: N issues" and "Fixing src/foo.py: reason"
_TOOL_065_RE = re.compile(
    r"^>\s+(?P<tool>Ran shell command|Applied edit|Saved file"
    r"|Linting(?:\s+\S+)?|Fixing(?:\s+\S+)?):\s+(?P<rest>.+)$"
)

# 0.70+ adds test runner lines
_TOOL_070_RE = re.compile(
    r"^>\s+(?P<tool>Ran shell command|Applied edit|Saved file"
    r"|Linting(?:\s+\S+)?|Fixing(?:\s+\S+)?"
    r"|Running tests|Tests passed|Tests failed):\s*(?P<rest>.*)$"
)

# Result summary lines (0.70+): "Tests passed: 42 passed, 0 failed" etc.
_SUMMARY_070_RE = re.compile(
    r"^>\s+(?P<tool>Tests passed|Tests failed)$"
)

# Blank / comment lines that are always safe to skip
_SKIP_RE = re.compile(r"^\s*$|^#{1,3}\s")

_VERSION_REGEXES: Dict[Tuple[int, int], re.Pattern] = {
    (0, 60): _TOOL_BASE_RE,
    (0, 65): _TOOL_065_RE,
    (0, 70): _TOOL_070_RE,
}


def _best_tool_re(version: Optional[Tuple[int, int]]) -> re.Pattern:
    """Return the most capable regex table for *version* (best-effort)."""
    if version is None:
        return _TOOL_BASE_RE
    major, minor = version
    for threshold in sorted(_VERSION_REGEXES.keys(), reverse=True):
        if (major, minor) >= threshold:
            return _VERSION_REGEXES[threshold]
    return _TOOL_BASE_RE


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class AiderAdapter(HarnessAdapter):
    """Passive file-watcher adapter for Aider with version dispatch (ADR-033b)."""

    name: ClassVar[HarnessName] = HarnessName.AIDER
    default_output: ClassVar[str] = ".cognitive-os/metrics/canonical-events.jsonl"

    # --- detection ---------------------------------------------------------

    @classmethod
    def detect_harness(cls, raw: Any) -> Optional[HarnessName]:
        if isinstance(raw, dict):
            hf = raw.get("history_file")
            if isinstance(hf, str) and hf.endswith(".aider.chat.history.md"):
                return cls.name
            if raw.get("harness") == cls.name.value:
                return cls.name
        if isinstance(raw, (str, Path)):
            p = str(raw)
            if p.endswith(".aider.chat.history.md"):
                return cls.name
        return None

    # --- parsing -----------------------------------------------------------

    def parse_event(self, raw: Dict[str, Any]) -> List[CanonicalEvent]:
        if not isinstance(raw, dict):
            return []

        lines = self._collect_lines(raw)
        if not lines:
            return []

        # Detect version from transcript header (first matching line).
        version = _detect_version(lines)
        _validate_version(version)

        agent_id = raw.get("agent_id") or _stable_id(lines)
        session_id = raw.get("session_id")
        tool_re = _best_tool_re(version)
        events: List[CanonicalEvent] = []

        started = False
        for line in lines:
            stripped = line.rstrip("\n")

            # Skip blank lines and section headers (## / ###)
            if _SKIP_RE.match(stripped):
                continue

            # Skip the version header line itself
            if _HEADER_RE.match(stripped):
                continue

            # User prompt → AgentStart (first occurrence only)
            if not started:
                m = _USER_RE.match(stripped)
                if m:
                    events.append(
                        AgentStart(
                            agent_id=agent_id,
                            started_at=now_epoch(),
                            tool_name="aider",
                            input_summary=m.group(1)[:160],
                            session_id=session_id,
                        )
                    )
                    started = True
                    continue
                # Lines before the first user prompt that aren't blank/header
                # are metadata (e.g. aider banner); emit ParseError for
                # non-blank, non-header lines that don't match.
                if not _SKIP_RE.match(stripped):
                    events.append(
                        ParseError(
                            source_line=stripped[:200],
                            adapter="aider",
                            reason="no_pattern_match_before_prompt",
                            session_id=session_id,
                        )
                    )
                continue

            # Tool line
            m2 = tool_re.match(stripped)
            if m2:
                events.append(
                    ToolUse(
                        agent_id=agent_id,
                        tool_name=m2.group("tool"),
                        started_at=now_epoch(),
                        exit_status="success",
                        tool_input_hash=_hash(m2.group("rest")),
                        session_id=session_id,
                    )
                )
                continue

            # User re-prompt (subsequent #### lines after start)
            if _USER_RE.match(stripped):
                continue

            # Nothing matched — emit ParseError (no silent skip per ADR-033b)
            events.append(
                ParseError(
                    source_line=stripped[:200],
                    adapter="aider",
                    reason="no_pattern_match",
                    session_id=session_id,
                )
            )

        # Terminal delta → AgentEnd
        if raw.get("final") or raw.get("ended"):
            events.append(
                AgentEnd(
                    agent_id=agent_id,
                    ended_at=now_epoch(),
                    exit_status=raw.get("exit_status", "success"),
                    token_usage=raw.get("token_usage") or {},
                    session_id=session_id,
                )
            )

        return events

    # --- helpers -----------------------------------------------------------

    def _collect_lines(self, raw: Dict[str, Any]) -> List[str]:
        if "new_lines" in raw:
            lines = raw["new_lines"]
            if isinstance(lines, list):
                return [str(x) for x in lines]
        if "history_file" in raw:
            try:
                return Path(raw["history_file"]).read_text(encoding="utf-8").splitlines()
            except OSError:
                return []
        return []


# ---------------------------------------------------------------------------
# Version detection / validation
# ---------------------------------------------------------------------------


def _detect_version(lines: List[str]) -> Optional[Tuple[int, int]]:
    """Return ``(major, minor)`` from the first aider version header found."""
    for line in lines[:10]:  # version header is near the top
        m = _HEADER_RE.match(line.rstrip("\n"))
        if m:
            return (int(m.group(1)), int(m.group(2)))
    return None


def _validate_version(version: Optional[Tuple[int, int]]) -> None:
    """Raise :exc:`UnsupportedAiderVersion` if *version* is outside the supported range.

    Supported range: **>=0.60, <0.71** (aider>=0.60,<0.71).
    If *version* is ``None`` (no header found) we allow best-effort parsing.
    """
    if version is None:
        return  # No header → best-effort
    if version < _MIN_VERSION or version >= _MAX_VERSION:
        raise UnsupportedAiderVersion(
            f"Aider version {version[0]}.{version[1]} is outside the supported range "
            f">={_MIN_VERSION[0]}.{_MIN_VERSION[1]}, <{_MAX_VERSION[0]}.{_MAX_VERSION[1]}. "
            "Update the adapter or pin aider>=0.60,<0.71."
        )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _stable_id(lines: List[str]) -> str:
    sig = hashlib.sha1("\n".join(lines[:4]).encode("utf-8")).hexdigest()[:12]
    return f"aider-{sig}"


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
