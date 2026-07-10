"""
agent_input_validator.py — ADR-038 Wave 1 typed input/output contract.

Parses INPUT SCHEMA blocks from sub-agent prompts and validates a payload dict
against the declared schema.

Schema syntax (mirrors templates/agent-preamble.md):
    field_name: type (required|optional) — description

Public API:
    parse_schema(schema_block: str) -> list[FieldSpec]
    validate_input(schema_block: str, payload: dict) -> tuple[bool, list[str]]
    format_escalation(errors: list[str]) -> str
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Supported primitive types understood by the validator.
# Unknown types pass through as "any" with an informational note.
# ---------------------------------------------------------------------------
_TYPE_MAP: dict[str, type | None] = {
    "str": str,
    "string": str,
    "int": int,
    "integer": int,
    "float": float,
    "bool": bool,
    "boolean": bool,
    "list": list,
    "list[str]": list,
    "list[int]": list,
    "dict": dict,
    "path": str,   # paths are strings; existence check is caller's responsibility
    "any": None,   # None sentinel means "skip type check"
}

# Regex for one schema line: `field_name: type (required|optional) — description`
# The em-dash description part is optional.
_FIELD_RE = re.compile(
    r"^\s*"
    r"(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)"
    r"\s*:\s*"
    r"(?P<type>[^\s(]+)"
    r"(?:\s*\(\s*(?P<cardinality>required|optional)\s*\))?"
    r"(?:\s*[—\-–]+\s*(?P<description>.+))?$",
    re.UNICODE,
)

# Block extractor: captures everything between INPUT SCHEMA: and blank line / next header
_BLOCK_RE = re.compile(
    r"INPUT SCHEMA:\s*\n((?:[ \t]*[^\n]+\n?)*)",
    re.IGNORECASE,
)


@dataclass
class FieldSpec:
    name: str
    raw_type: str                        # as declared in schema
    required: bool = True
    description: str = ""
    python_type: type | None = None     # None = any/unknown, skip type check
    unknown_type: bool = False           # True when raw_type not in _TYPE_MAP


def _resolve_type(raw: str) -> tuple[type | None, bool]:
    """Map raw type string to Python type. Returns (python_type, is_unknown)."""
    key = raw.strip().lower()
    if key in _TYPE_MAP:
        return _TYPE_MAP[key], False
    return None, True  # unknown — treat as any


def _type_error(spec: FieldSpec, value: Any) -> str | None:
    """Return a TYPE_MISMATCH message for *value*, or None when valid."""
    raw = spec.raw_type.strip().lower()

    if raw in {"int", "integer"}:
        # bool is a subclass of int in Python, but schema int must mean a real
        # integer field for launch contracts.
        if isinstance(value, bool) or not isinstance(value, int):
            return (
                f"TYPE_MISMATCH: field '{spec.name}' expected {spec.raw_type} "
                f"but got {type(value).__name__}"
            )
        return None

    if raw in {"list[str]", "list[int]"}:
        if not isinstance(value, list):
            return (
                f"TYPE_MISMATCH: field '{spec.name}' expected {spec.raw_type} "
                f"but got {type(value).__name__}"
            )
        item_type = str if raw == "list[str]" else int
        for index, item in enumerate(value):
            if raw == "list[int]" and isinstance(item, bool):
                valid = False
            else:
                valid = isinstance(item, item_type)
            if not valid:
                return (
                    f"TYPE_MISMATCH: field '{spec.name}' expected {spec.raw_type} "
                    f"but item {index} is {type(item).__name__}"
                )
        return None

    if spec.python_type is not None and not isinstance(value, spec.python_type):
        return (
            f"TYPE_MISMATCH: field '{spec.name}' expected {spec.raw_type} "
            f"but got {type(value).__name__}"
        )
    return None


def parse_schema(schema_block: str) -> list[FieldSpec]:
    """Parse a raw INPUT SCHEMA block (the content after the header line).

    Accepts both:
    - The full prompt (will extract the block automatically)
    - Just the field lines

    Skips blank lines, comment lines (starting with #), and the
    ``... custom fields per launch ...`` placeholder.
    """
    # If the input contains the header keyword, extract the block content.
    match = _BLOCK_RE.search(schema_block)
    if match:
        lines = match.group(1).splitlines()
    else:
        lines = schema_block.splitlines()

    specs: list[FieldSpec] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("..."):
            continue
        m = _FIELD_RE.match(stripped)
        if not m:
            continue
        name = m.group("name")
        raw_type = m.group("type") or "any"
        cardinality = m.group("cardinality") or "required"
        description = (m.group("description") or "").strip()
        python_type, unknown_type = _resolve_type(raw_type)
        specs.append(
            FieldSpec(
                name=name,
                raw_type=raw_type,
                required=(cardinality.lower() == "required"),
                description=description,
                python_type=python_type,
                unknown_type=unknown_type,
            )
        )
    return specs


def validate_input(
    schema_block: str,
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Validate *payload* against the schema declared in *schema_block*.

    Returns:
        (ok, errors)  — ok is True only when errors is empty.

    Error categories:
        - MISSING_REQUIRED: required field absent or None/empty-string
        - TYPE_MISMATCH: field present but wrong Python type
        - UNKNOWN_TYPE: declared type not recognised (informational, not a failure)

    Extra fields in payload not declared in schema are silently accepted
    (treated as informational context per preamble rule).
    """
    specs = parse_schema(schema_block)
    errors: list[str] = []
    informational: list[str] = []

    for spec in specs:
        value = payload.get(spec.name)

        # --- Required presence check ---
        if spec.required:
            if value is None or value == "":
                errors.append(
                    f"MISSING_REQUIRED: field '{spec.name}' is required but absent or empty"
                )
                continue  # no point type-checking a missing value

        # --- Type check (only if value present and type known) ---
        if value is not None and not spec.unknown_type and spec.python_type is not None:
            mismatch = _type_error(spec, value)
            if mismatch:
                errors.append(mismatch)

        # --- Unknown type note (informational, not an error) ---
        if spec.unknown_type and value is not None:
            informational.append(
                f"UNKNOWN_TYPE: field '{spec.name}' has unrecognised type '{spec.raw_type}' "
                f"— validation skipped, treated as any"
            )

    ok = len(errors) == 0
    # Append informational notes after real errors so callers can separate them.
    return ok, errors + informational


def format_escalation(errors: list[str]) -> str:
    """Format validation errors as a preamble-compliant ESCALATION block.

    Per preamble rule: ``ESCALATION: missing required input field: <field_name>``
    This helper produces the full multi-line block when there are multiple issues.
    """
    if not errors:
        return ""
    lines = ["ESCALATION: input validation failed at task start."]
    for err in errors:
        lines.append(f"  - {err}")
    lines.append("Stopping task until orchestrator provides corrected inputs.")
    return "\n".join(lines)
