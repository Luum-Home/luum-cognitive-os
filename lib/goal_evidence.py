# SCOPE: os-only
"""Evidence packet parser and validator for COS-native goal loop.

Implements REQ-003 (structured evidence required) and REQ-006 (proxy evidence
rejection). Evidence packets are always explicit JSON or fenced-markdown JSON
blocks — transcript scraping is out of scope for MVP.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from lib.goal_state import EvidencePacket, CommandEvidence


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------


@dataclass
class EvidenceValidationResult:
    """Outcome of parsing and validating an evidence packet."""

    valid: bool
    packet: EvidencePacket | None
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Required top-level fields (REQ-003)
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS: list[str] = [
    "iteration",
    "files_changed",
    "commands_run",
    "passing_checks",
    "acceptance_coverage",
    "remaining_gaps",
    "blockers",
    "next_action",
    "raw_summary",
]


# ---------------------------------------------------------------------------
# Parser — JSON packet
# ---------------------------------------------------------------------------


def _extract_json_from_markdown(text: str) -> str | None:
    """Extract the first JSON block from a fenced markdown code block."""
    pattern = r"```(?:json)?\s*\n(.*?)```"
    m = re.search(pattern, text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return None


def _load_raw(raw: str) -> dict[str, Any]:
    """Parse raw string as either plain JSON or fenced-markdown JSON.

    Raises ValueError with a descriptive message on failure.
    """
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Evidence packet is not valid JSON: {exc}") from exc
    # Try fenced markdown
    block = _extract_json_from_markdown(raw)
    if block is not None:
        try:
            return json.loads(block)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"JSON block inside fenced markdown is invalid: {exc}"
            ) from exc
    raise ValueError(
        "Evidence must be plain JSON or a fenced markdown JSON block."
    )


# ---------------------------------------------------------------------------
# Field-level validators
# ---------------------------------------------------------------------------


def _validate_required_fields(data: dict[str, Any]) -> list[str]:
    """Return field-specific error messages for missing required fields."""
    errors: list[str] = []
    for fname in _REQUIRED_FIELDS:
        if fname not in data:
            errors.append(f"Missing required field: '{fname}'")
    return errors


def _validate_acceptance_coverage(
    data: dict[str, Any],
    acceptance_checks: list[str] | None,
) -> list[str]:
    """Verify every declared acceptance check has an entry in acceptance_coverage.

    If acceptance_checks is None or empty, only check that coverage is a dict.
    """
    errors: list[str] = []
    coverage = data.get("acceptance_coverage")
    if not isinstance(coverage, dict):
        errors.append("'acceptance_coverage' must be a JSON object (dict).")
        return errors
    if not acceptance_checks:
        return errors
    for check in acceptance_checks:
        if check not in coverage:
            errors.append(
                f"Acceptance check '{check}' has no entry in 'acceptance_coverage'."
            )
    return errors


def _validate_commands_run(data: dict[str, Any]) -> list[str]:
    """Validate that commands_run is a list of objects with required keys."""
    errors: list[str] = []
    commands = data.get("commands_run", [])
    if not isinstance(commands, list):
        errors.append("'commands_run' must be a list.")
        return errors
    for i, item in enumerate(commands):
        if not isinstance(item, dict):
            errors.append(f"'commands_run[{i}]' must be an object.")
            continue
        if "command" not in item:
            errors.append(f"'commands_run[{i}]' is missing 'command'.")
        if "exit_code" not in item:
            errors.append(f"'commands_run[{i}]' is missing 'exit_code'.")
    return errors


def _validate_list_fields(data: dict[str, Any]) -> list[str]:
    """Verify that list-typed fields are actually lists."""
    errors: list[str] = []
    list_fields = ["files_changed", "passing_checks", "remaining_gaps", "blockers"]
    for fname in list_fields:
        val = data.get(fname)
        if val is not None and not isinstance(val, list):
            errors.append(f"'{fname}' must be a list, got {type(val).__name__}.")
    return errors


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_evidence(
    raw: str,
    acceptance_checks: list[str] | None = None,
) -> EvidenceValidationResult:
    """Parse and validate an evidence packet from a raw string.

    Args:
        raw: Plain JSON string or fenced-markdown block containing JSON.
        acceptance_checks: If provided, every check must appear in
            ``acceptance_coverage``. Pass the goal's acceptance checks here
            to enforce full-coverage validation (REQ-003).

    Returns:
        EvidenceValidationResult with ``valid=True`` and a populated ``packet``
        on success, or ``valid=False`` with ``errors`` describing what is wrong.
    """
    # Step 1: parse
    try:
        data = _load_raw(raw)
    except ValueError as exc:
        return EvidenceValidationResult(valid=False, packet=None, errors=[str(exc)])

    if not isinstance(data, dict):
        return EvidenceValidationResult(
            valid=False,
            packet=None,
            errors=["Evidence packet must be a JSON object."],
        )

    # Step 2: field validation
    errors: list[str] = []
    errors.extend(_validate_required_fields(data))
    errors.extend(_validate_commands_run(data))
    errors.extend(_validate_list_fields(data))
    errors.extend(_validate_acceptance_coverage(data, acceptance_checks))

    if errors:
        return EvidenceValidationResult(valid=False, packet=None, errors=errors)

    # Step 3: construct dataclass
    try:
        packet = EvidencePacket(
            iteration=int(data["iteration"]),
            files_changed=list(data.get("files_changed", [])),
            commands_run=[
                CommandEvidence.from_dict(c) for c in data.get("commands_run", [])
            ],
            passing_checks=list(data.get("passing_checks", [])),
            acceptance_coverage=dict(data.get("acceptance_coverage", {})),
            remaining_gaps=list(data.get("remaining_gaps", [])),
            blockers=list(data.get("blockers", [])),
            next_action=data.get("next_action"),
            raw_summary=str(data.get("raw_summary", "")),
            source="explicit-packet",
        )
    except (TypeError, KeyError, ValueError) as exc:
        return EvidenceValidationResult(
            valid=False,
            packet=None,
            errors=[f"Failed to construct EvidencePacket: {exc}"],
        )

    return EvidenceValidationResult(valid=True, packet=packet, errors=[])


def validate_evidence(
    packet: EvidencePacket,
    acceptance_checks: list[str],
) -> list[str]:
    """Validate an already-parsed EvidencePacket against a goal's acceptance checks.

    Returns a list of error strings. Empty list means valid.
    This is a thin wrapper used by the evaluator for proxy-evidence detection.
    """
    errors: list[str] = []
    for check in acceptance_checks:
        if check not in packet.acceptance_coverage:
            errors.append(
                f"Acceptance check '{check}' is not covered in acceptance_coverage."
            )
    return errors
