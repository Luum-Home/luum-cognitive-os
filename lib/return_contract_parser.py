# scope: both
"""
Return Contract Parser — lib/return_contract_parser.py

Parses and validates the structured RESULT: block that sub-agents are required
to emit at the end of their responses (see templates/agent-preamble.md).

The contract format:

    RESULT:
      STATUS: {success|partial|failed}
      SUMMARY: {1-2 sentences}
      FILES_CHANGED:
        - {path} — {what changed}
      KEY_FINDINGS:
        - {finding}
      BLOCKERS: {none, or description}
      TOKENS_ESTIMATE: {number}

Usage:
    from lib.return_contract_parser import parse_return_contract, validate_return_contract, format_compact_result

    parsed = parse_return_contract(agent_output)
    if parsed:
        violations = validate_return_contract(parsed)
        compact = format_compact_result(parsed)
"""

from __future__ import annotations

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_return_contract(output: str) -> Optional[dict]:
    """Parse RESULT: block from agent output.

    Returns a dict with keys:
        status          str  — "success" | "partial" | "failed"
        summary         str  — 1-2 sentence description
        files_changed   list[str]  — each item is "path — description"
        key_findings    list[str]  — non-obvious discoveries
        blockers        str  — "none" or explanation
        tokens_estimate int | None  — rough token count estimate

    Returns None if no RESULT: block is found.
    """
    if not output or "RESULT:" not in output:
        return None

    # Extract the RESULT: block — everything from "RESULT:" to the next
    # top-level section marker (TRUST_REPORT:, ESCALATION:, or end of string).
    block_match = re.search(
        r"^RESULT:\s*\n(.*?)(?=^(?:TRUST_REPORT:|ESCALATION:|NEEDS_CLARIFICATION:)|\Z)",
        output,
        re.MULTILINE | re.DOTALL,
    )
    if not block_match:
        # Fallback: try to find RESULT: and consume until blank line or end
        block_match = re.search(
            r"^RESULT:\s*\n(.*)",
            output,
            re.MULTILINE | re.DOTALL,
        )
    if not block_match:
        return None

    block = block_match.group(1)

    result: dict = {
        "status": "",
        "summary": "",
        "files_changed": [],
        "key_findings": [],
        "blockers": "none",
        "tokens_estimate": None,
    }

    # Parse STATUS
    status_match = re.search(r"^\s*STATUS:\s*(.+)$", block, re.MULTILINE)
    if status_match:
        raw = status_match.group(1).strip().lower()
        # Normalise — accept any casing and strip surrounding braces/quotes
        raw = re.sub(r"[{}\[\]\"']", "", raw).strip()
        if raw in ("success", "partial", "failed"):
            result["status"] = raw
        else:
            result["status"] = raw  # preserve unknown value for validation

    # Parse SUMMARY
    summary_match = re.search(r"^\s*SUMMARY:\s*(.+)$", block, re.MULTILINE)
    if summary_match:
        result["summary"] = summary_match.group(1).strip()

    # Parse FILES_CHANGED — list items starting with "- "
    result["files_changed"] = _parse_list_section(block, "FILES_CHANGED")

    # Parse KEY_FINDINGS
    result["key_findings"] = _parse_list_section(block, "KEY_FINDINGS")

    # Parse BLOCKERS (single-line value or multi-line list)
    blockers_match = re.search(
        r"^\s*BLOCKERS:\s*(.+?)(?=^\s*[A-Z_]+:|$)",
        block,
        re.MULTILINE | re.DOTALL,
    )
    if blockers_match:
        raw_blockers = blockers_match.group(1).strip()
        result["blockers"] = raw_blockers if raw_blockers else "none"

    # Parse TOKENS_ESTIMATE
    tokens_match = re.search(r"^\s*TOKENS_ESTIMATE:\s*([0-9,_]+)", block, re.MULTILINE)
    if tokens_match:
        try:
            result["tokens_estimate"] = int(re.sub(r"[,_]", "", tokens_match.group(1)))
        except ValueError:
            result["tokens_estimate"] = None

    return result


def validate_return_contract(parsed: dict) -> list[str]:
    """Validate a parsed return contract.

    Returns a list of violation strings (empty list = valid).
    """
    violations: list[str] = []

    if not parsed.get("status"):
        violations.append("STATUS is missing")
    elif parsed["status"] not in ("success", "partial", "failed"):
        violations.append(
            f"STATUS must be 'success', 'partial', or 'failed'; got '{parsed['status']}'"
        )

    summary = parsed.get("summary", "").strip()
    if not summary:
        violations.append("SUMMARY is empty")
    elif len(summary) > 500:
        violations.append(
            f"SUMMARY exceeds 500 characters ({len(summary)} chars) — use 1-2 sentences max"
        )

    status = parsed.get("status", "")
    blockers = parsed.get("blockers", "none").strip().lower()
    if status in ("failed", "partial") and (blockers == "none" or not blockers):
        violations.append(
            f"BLOCKERS must explain why STATUS is '{status}' — cannot be 'none'"
        )

    key_findings = parsed.get("key_findings", [])
    if len(key_findings) > 5:
        violations.append(
            f"KEY_FINDINGS has {len(key_findings)} items; max is 5"
        )

    return violations


def format_compact_result(parsed: dict) -> str:
    """Format a parsed return contract into a minimal ~200-token string.

    Intended for the orchestrator to inject into its own context as a concise
    record of what the sub-agent accomplished, without retaining the full
    verbose output.
    """
    if not parsed:
        return "[no return contract]"

    lines: list[str] = []

    status = parsed.get("status", "unknown").upper()
    summary = parsed.get("summary", "").strip()
    lines.append(f"STATUS: {status} — {summary}" if summary else f"STATUS: {status}")

    files = parsed.get("files_changed", [])
    if files:
        lines.append(f"FILES ({len(files)}): " + "; ".join(f[:80] for f in files[:5]))
        if len(files) > 5:
            lines.append(f"  …and {len(files) - 5} more")

    findings = parsed.get("key_findings", [])
    if findings:
        lines.append("FINDINGS:")
        for f in findings[:5]:
            lines.append(f"  • {f[:120]}")

    blockers = parsed.get("blockers", "none").strip()
    if blockers and blockers.lower() != "none":
        lines.append(f"BLOCKERS: {blockers[:200]}")

    tokens = parsed.get("tokens_estimate")
    if tokens is not None:
        lines.append(f"~{tokens:,} tokens consumed")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_list_section(block: str, section_name: str) -> list[str]:
    """Extract a bullet-list section from the block.

    Looks for a line like "  SECTION_NAME:" and collects all subsequent
    bullet lines ("  - ...") until the next section header (a line whose
    first non-whitespace characters are an ALL_CAPS identifier followed by
    a colon, but only when that whole token starts at the beginning of the
    line — i.e., it IS the header, not text within a bullet).
    """
    # Find the start of the section
    header_pattern = re.compile(
        rf"^\s*{re.escape(section_name)}:\s*$",
        re.MULTILINE,
    )
    header_match = header_pattern.search(block)
    if not header_match:
        return []

    # Walk lines after the header, collecting bullet items, stopping at the
    # next top-level section header.  A top-level header is a line where the
    # very first non-space characters are two or more uppercase letters /
    # underscores immediately followed by a colon, with nothing non-space
    # before them on that line.
    next_header_re = re.compile(r"^\s{0,3}[A-Z_]{2,}:\s*")

    items: list[str] = []
    lines = block[header_match.end():].splitlines()
    for line in lines:
        # Stop at the next section header (but not indented list content)
        if next_header_re.match(line):
            # It's a header if the content before the colon is ALL_CAPS only
            left = line.strip().split(":")[0]
            if re.match(r"^[A-Z_]{2,}$", left):
                break
        stripped = line.strip()
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                items.append(item)

    return items
