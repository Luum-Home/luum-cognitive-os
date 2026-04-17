"""Safe Engram wrapper — security-scanned write path for untrusted content.

FOR (use case)
--------------
Use this module when saving content that originates from **untrusted sources**:
agent output, LLM-generated text, user input, or anything that may carry prompt
injection, credential strings, or invisible Unicode.  Every write is vetted by
``MemoryScanner`` before the engram CLI is invoked.  If scanning is the concern,
this is the right module.

CONSUMERS (as of 2026-04-17)
-----------------------------
- ``mcp-server/cos_mcp.py:204`` — the ``_engram_save`` tool handler (primary consumer).
  Reads ``SafeEngramResult.blocked``, ``.reasons``, ``.returncode``, and
  ``.engram_output`` directly via attribute access.
- ``lib/anchored_summarizer.py:274`` — injects an inline ``safe_save`` call into
  agent prompts for session-summary writes.
- ``tests/unit/test_safe_engram.py`` and ``tests/unit/test_safe_engram_contract.py``
  — the contract test suite that locks consumer-facing behavior.

CONTRACT
--------
- ``safe_save()`` **never raises** — all error conditions (binary missing, timeout,
  scan block) are encoded into the returned ``SafeEngramResult`` dataclass.
- Return-code semantics: ``0`` = engram saved OK; ``127`` = binary not on PATH
  (treated as graceful degradation, not an error); ``-1`` = subprocess timeout;
  any other non-zero = engram CLI error.
- ``engram_output`` is **human-readable plain text**, never JSON.  The CLI command
  deliberately omits ``--json`` so ``cos_mcp`` can return the string verbatim to
  MCP clients.
- ``blocked=True`` means MemoryScanner rejected the content before the CLI ran;
  ``returncode`` is ``None`` in that case.

NOT (cross-reference)
----------------------
This module is **not** for trusted internal reads or structured machine-parseable
writes.  For those, use ``lib.engram_client`` (see ``lib/engram_client.py``), which
returns ``dict | None`` and passes ``--json`` to the CLI.  The two modules have
**zero overlapping callers** — see ADR-026 and ADR-026a for the investigation
that confirmed this boundary.

ADR references: ``docs/architecture/adrs/026-r2-r3-design-review.md`` (R3 findings)
               ``docs/architecture/adrs/026a-decisions.md`` (D3.1 decision)

Usage (Python)::

    from lib.safe_engram import safe_save, SafeEngramResult

    result = safe_save("Auth decision", "We use RS256 JWTs.", topic_key="architecture/auth")
    if result.blocked:
        print("BLOCKED:", result.reasons)
    else:
        print("Saved:", result.engram_output)

Usage (Bash hook — inline scan before ``engram save``)::

    SCAN=$(python3 -c "
    import sys; sys.path.insert(0, '$PROJECT_DIR')
    from lib.safe_engram import scan_only_check
    print(scan_only_check(sys.stdin.read()))
    " <<< "$CONTENT")
    if [[ $SCAN == BLOCKED:* ]]; then
        echo "MEMORY SCAN: ${SCAN}" >&2
        exit 0   # skip the save silently
    fi
    engram save ...

Python 3.9+ compatible.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

from lib.memory_scanner import MemoryScanner

# Module-level scanner — created once, reused across calls.
_scanner = MemoryScanner()


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


@dataclass
class SafeEngramResult:
    """Result returned by :func:`safe_save`."""

    blocked: bool
    """True when the scanner found a threat and the save was skipped."""

    reasons: List[str] = field(default_factory=list)
    """Threat category names detected by the scanner (empty when clean)."""

    engram_output: Optional[str] = None
    """Raw stdout from the engram CLI when the save succeeded."""

    returncode: Optional[int] = None
    """Return code from the engram CLI subprocess (None when blocked)."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan_only_check(content: str) -> str:
    """Scan *content* and return a single-line status string.

    Returns ``"OK"`` for clean content, or ``"BLOCKED:<reason1>,<reason2>"``
    when threats are detected.  Designed for inline use from Bash hooks::

        SCAN=$(python3 -c "
        import sys; sys.path.insert(0, '$PROJECT_DIR')
        from lib.safe_engram import scan_only_check
        print(scan_only_check(sys.stdin.read()))
        " <<< "$CONTENT")

    Args:
        content: The text to scan.

    Returns:
        ``"OK"`` or ``"BLOCKED:<comma-separated reasons>"``.
    """
    result = _scanner.scan(content)
    if result.blocked:
        return "BLOCKED:" + ",".join(result.reasons)
    return "OK"


def safe_save(
    title: str,
    content: str,
    *,
    topic_key: str = "",
    type_: str = "manual",
    project: str = "",
    engram_bin: Optional[str] = None,
    timeout: int = 10,
) -> SafeEngramResult:
    """Scan *content* and, if clean, save it to Engram via the CLI.

    Args:
        title:      Short searchable title for the observation.
        content:    The body to store.  This is the field that is scanned.
        topic_key:  Stable upsert key (e.g. ``"architecture/auth-model"``).
        type_:      Engram observation type (``decision``, ``bugfix``, …).
        project:    Project name for scoping.
        engram_bin: Path to the ``engram`` binary.  Defaults to the
                    ``ENGRAM_BIN`` environment variable or ``"engram"``.
        timeout:    Subprocess timeout in seconds.

    Returns:
        :class:`SafeEngramResult` — check ``.blocked`` before using
        ``.engram_output``.
    """
    # --- scan title + content together so injections hidden in the title
    # --- are also caught.
    scan_target = f"{title}\n\n{content}"
    scan_result = _scanner.scan(scan_target)

    if scan_result.blocked:
        return SafeEngramResult(blocked=True, reasons=scan_result.reasons)

    # --- build CLI command ------------------------------------------------
    bin_ = engram_bin or os.environ.get("ENGRAM_BIN", "engram")
    cmd: List[str] = [
        bin_,
        "save",
        "--title", title,
        "--content", content,
        "--type", type_,
    ]
    if topic_key:
        cmd.extend(["--topic-key", topic_key])
    if project:
        cmd.extend(["--project", project])

    # --- execute ----------------------------------------------------------
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return SafeEngramResult(
            blocked=False,
            engram_output=proc.stdout.strip() or proc.stderr.strip() or "Saved.",
            returncode=proc.returncode,
        )
    except FileNotFoundError:
        # engram binary not found — treat as a non-blocking passthrough
        return SafeEngramResult(
            blocked=False,
            engram_output="engram binary not found; save skipped.",
            returncode=127,
        )
    except subprocess.TimeoutExpired:
        return SafeEngramResult(
            blocked=False,
            engram_output="engram save timed out.",
            returncode=-1,
        )
