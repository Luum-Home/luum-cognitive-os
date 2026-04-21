"""Agent redirect protocol (ADR-056 Level 2).

Text-based protocol for the L2 block hook to communicate with the parent
orchestrator. When the hook blocks an Agent() call due to quota pressure
or recent rate-limit events, it emits an AGENT_REDIRECT block on stderr.
The orchestrator parses this block and re-issues the call through
`scripts/orchestrator.py run --providers qwen,claude` instead.

Protocol is deliberately LLM-harness agnostic: structured text, not JSON
or MCP tool calls, so it survives any transport (Claude Code hooks,
Cline, Cursor, Qwen Code, custom harnesses).

Block format (stable — do not change without versioning):

    AGENT_REDIRECT: reason=<quota_pressure|rate_limit> pressure=<N.NN>
    SUGGESTED_COMMAND: uv run python3 scripts/orchestrator.py run --task '<prompt>' --providers qwen,claude

The block always occupies exactly 2 lines. No trailing content is part
of the protocol. `<prompt>` is POSIX-shell-quoted via shlex.quote() to
preserve newlines and special characters (backticks, $, !, etc).

See also:
  - docs/adrs/ADR-056-adaptive-agent-dispatch.md (Agent A owns)
  - hooks/agent-quota-redirect.sh (consumer of build_redirect_message)
  - scripts/orchestrator.py (target of SUGGESTED_COMMAND)
"""

from __future__ import annotations

import re
import shlex
from typing import Optional

# Stable protocol constants. If the format ever changes, bump a version
# marker and keep the old parser path for backwards compatibility.
REDIRECT_HEADER = "AGENT_REDIRECT"
COMMAND_HEADER = "SUGGESTED_COMMAND"

# Accepted reason codes. Keep in sync with the hook logic.
REASON_QUOTA_PRESSURE = "quota_pressure"
REASON_RATE_LIMIT = "rate_limit"
VALID_REASONS = frozenset({REASON_QUOTA_PRESSURE, REASON_RATE_LIMIT})

# Regex for parsing. Anchored per-line so extra surrounding stderr noise
# (from the hook's logging) doesn't break extraction.
_REDIRECT_LINE_RE = re.compile(
    r"^AGENT_REDIRECT:\s+reason=(?P<reason>\S+)\s+pressure=(?P<pressure>[0-9]+\.[0-9]+)\s*$",
    re.MULTILINE,
)
_COMMAND_LINE_RE = re.compile(
    r"^SUGGESTED_COMMAND:\s+(?P<command>.+)$",
    re.MULTILINE,
)


def format_orchestrator_command(prompt: str, model_hint: Optional[str] = None) -> str:
    """Build the `uv run python3 scripts/orchestrator.py run ...` string.

    The prompt is shell-quoted via shlex.quote() so newlines, backticks,
    $var references, and other shell metacharacters are preserved
    literally and cannot be interpreted as shell syntax when the parent
    orchestrator executes the suggested command.

    Args:
        prompt: The original Agent() task prompt. Arbitrary text, may
            contain newlines and shell-unsafe characters.
        model_hint: Optional Claude model shortname (opus/sonnet/haiku).
            When provided, mapped by the orchestrator to the Qwen bundle
            via lib/qwen_provider.map_claude_model_to_qwen.

    Returns:
        A single-line command string, shlex-safe for copy-paste into a
        POSIX shell.
    """
    quoted = shlex.quote(prompt)
    parts = [
        "uv run python3 scripts/orchestrator.py run",
        f"--task {quoted}",
        "--providers qwen,claude",
    ]
    if model_hint:
        parts.append(f"--model {shlex.quote(model_hint)}")
    return " ".join(parts)


def build_redirect_message(
    reason: str,
    pressure: float,
    prompt: str,
    model_hint: Optional[str] = None,
) -> str:
    """Format the 2-line AGENT_REDIRECT block the hook writes to stderr.

    The returned string has a trailing newline so it can be written
    directly to stderr with a single call.

    Args:
        reason: One of REASON_QUOTA_PRESSURE, REASON_RATE_LIMIT.
        pressure: Float in [0.0, 1.0] — current quota pressure. Formatted
            with exactly 2 decimal places for stable regex parsing.
        prompt: The original Agent() task prompt (will be shell-quoted
            inside SUGGESTED_COMMAND).
        model_hint: Optional model hint passed through to the suggested
            command.

    Returns:
        Two lines terminated by '\\n', ready for sys.stderr.write().

    Raises:
        ValueError: if reason is not in VALID_REASONS or pressure is not
            a real number in [0.0, 1.0].
    """
    if reason not in VALID_REASONS:
        raise ValueError(
            f"reason must be one of {sorted(VALID_REASONS)!r}, got {reason!r}"
        )
    try:
        pressure_f = float(pressure)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"pressure must be a number, got {pressure!r}") from exc
    if not (0.0 <= pressure_f <= 1.0):
        raise ValueError(
            f"pressure must be in [0.0, 1.0], got {pressure_f!r}"
        )

    command = format_orchestrator_command(prompt, model_hint=model_hint)
    return (
        f"{REDIRECT_HEADER}: reason={reason} pressure={pressure_f:.2f}\n"
        f"{COMMAND_HEADER}: {command}\n"
    )


def parse_redirect_message(text: str) -> Optional[dict]:
    """Parse an AGENT_REDIRECT block out of arbitrary text.

    The orchestrator consumes this to decide whether to re-issue a call
    via scripts/orchestrator.py. Tolerant of surrounding stderr noise
    (log lines, blank lines, hook debug output) — only the two protocol
    lines must be present SOMEWHERE in the input.

    Args:
        text: Arbitrary text, typically the captured stderr of a blocked
            hook invocation.

    Returns:
        A dict with keys 'reason', 'pressure', 'command' on success, or
        None if the block is missing or malformed. Unknown reasons are
        surfaced verbatim (parser is schema-lax; the caller decides
        whether to reject unknowns).
    """
    if not text:
        return None
    redirect_match = _REDIRECT_LINE_RE.search(text)
    command_match = _COMMAND_LINE_RE.search(text)
    if not redirect_match or not command_match:
        return None
    try:
        pressure_f = float(redirect_match.group("pressure"))
    except ValueError:
        return None
    return {
        "reason": redirect_match.group("reason"),
        "pressure": pressure_f,
        "command": command_match.group("command").strip(),
    }
