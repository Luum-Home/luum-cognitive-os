# SCOPE: both
"""Canonical parser for sub-agent ``RESULT:`` blocks.

Accepts the current compact preamble contract and the older WS2 uppercase
contract, then renders a compact summary for orchestrator context.
"""

from __future__ import annotations

import re
from typing import Any, Optional

VALID_STATUSES = frozenset({"completed", "success", "partial", "failed"})


def parse_return_contract(output: str) -> Optional[dict[str, Any]]:
    """Parse and normalise a ``RESULT:`` block from agent output."""
    if not output or "RESULT:" not in output:
        return None
    block = _find_result_block(output)
    if block is None:
        return None
    fields = _parse_line_fields(block)
    files_created = _parse_inline_list(fields.get("files_created", ""))
    files_modified = _parse_inline_list(fields.get("files_modified", ""))
    legacy_files = _parse_list_section(block, "files_changed")
    discoveries = _parse_list_section(block, "discoveries") or _parse_repeated_values(block, "discoveries")
    key_findings = _parse_list_section(block, "key_findings") or discoveries
    files_changed = list(legacy_files)
    files_changed.extend(f"created:{p}" for p in files_created)
    files_changed.extend(f"modified:{p}" for p in files_modified)
    return {
        "status": _normalize_status(fields.get("status", "")),
        "summary": fields.get("summary", "").strip(),
        "files_created": files_created,
        "files_modified": files_modified,
        "files_changed": files_changed,
        "key_findings": key_findings,
        "discoveries": discoveries,
        "blockers": fields.get("blockers", "none").strip() or "none",
        "tests": _parse_tests(fields.get("tests", "")),
        "tokens_estimate": _parse_int(fields.get("tokens_estimate", "")),
        "trust_score": _parse_int(fields.get("trust_score", "")),
    }


def validate_return_contract(parsed: dict[str, Any]) -> list[str]:
    """Validate a parsed return contract. Empty list means valid."""
    violations: list[str] = []
    status = parsed.get("status", "")
    if not status:
        violations.append("STATUS is missing")
    elif status not in VALID_STATUSES:
        violations.append(
            "STATUS must be one of completed, success, partial, failed; "
            f"got '{status}'"
        )
    summary = str(parsed.get("summary", "")).strip()
    if not summary:
        violations.append("SUMMARY is empty")
    elif len(summary) > 500:
        violations.append(
            f"SUMMARY exceeds 500 characters ({len(summary)} chars) — use 1-2 sentences max"
        )
    blockers = str(parsed.get("blockers", "none")).strip().lower()
    if status in ("failed", "partial") and (blockers == "none" or not blockers):
        violations.append(f"BLOCKERS must explain why STATUS is '{status}' — cannot be 'none'")
    key_findings = parsed.get("key_findings", []) or []
    if len(key_findings) > 5:
        violations.append(f"KEY_FINDINGS has {len(key_findings)} items; max is 5")
    return violations


def format_compact_result(parsed: dict[str, Any]) -> str:
    """Render a parsed contract as a bounded orchestrator summary."""
    if not parsed:
        return "[no return contract]"
    lines: list[str] = []
    status = str(parsed.get("status", "unknown")).upper()
    summary = str(parsed.get("summary", "")).strip()
    lines.append(f"STATUS: {status} — {summary}" if summary else f"STATUS: {status}")
    created = parsed.get("files_created", []) or []
    modified = parsed.get("files_modified", []) or []
    legacy = [f for f in (parsed.get("files_changed", []) or []) if not str(f).startswith(("created:", "modified:"))]
    parts: list[str] = []
    if created:
        parts.append("created " + ", ".join(str(f)[:70] for f in created[:4]))
    if modified:
        parts.append("modified " + ", ".join(str(f)[:70] for f in modified[:4]))
    if legacy:
        shown = "; ".join(str(f)[:80] for f in legacy[:5])
        if len(legacy) > 5:
            shown += f"; and {len(legacy) - 5} more"
        parts.append("changed " + shown)
    if parts:
        lines.append("FILES: " + " | ".join(parts))
    tests = parsed.get("tests") or {}
    if tests:
        lines.append(_format_tests(tests))
    findings = parsed.get("key_findings", []) or parsed.get("discoveries", []) or []
    if findings:
        lines.append("FINDINGS: " + "; ".join(str(f)[:100] for f in findings[:3]))
    blockers = str(parsed.get("blockers", "none")).strip()
    if blockers and blockers.lower() != "none":
        lines.append(f"BLOCKERS: {blockers[:180]}")
    trust = parsed.get("trust_score")
    if trust is not None:
        lines.append(f"TRUST: {trust}/100")
    tokens = parsed.get("tokens_estimate")
    if tokens is not None:
        lines.append(f"~{tokens:,} tokens consumed")
    compact = "\n".join(lines)
    return compact if len(compact) <= 800 else compact[:797] + "..."


def _find_result_block(output: str) -> str | None:
    match = re.search(
        r"^RESULT:\s*\n(.*?)(?=^(?:TRUST_REPORT:|ESCALATION:|NEEDS_CLARIFICATION:|##\s)|\Z)",
        output,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else None


def _parse_line_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("- "):
            continue
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if match:
            key = match.group(1).strip().lower()
            value = match.group(2).strip()
            if value or key not in fields:
                fields[key] = value
    return fields


def _normalize_status(value: str) -> str:
    raw = re.sub(r"[{}\[\]\"']", "", str(value or "")).strip().lower()
    return {"succeeded": "success", "complete": "completed"}.get(raw, raw)


def _parse_inline_list(value: str) -> list[str]:
    raw = str(value or "").strip()
    if not raw or raw.lower() in {"none", "[]", "-", "n/a"}:
        return []
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    return [item.strip().strip("'\"") for item in raw.split(",") if item.strip() and item.strip().lower() != "none"]


def _parse_list_section(block: str, section_name: str) -> list[str]:
    header = re.search(rf"^\s*{re.escape(section_name)}:\s*$", block, re.MULTILINE | re.IGNORECASE)
    if not header:
        return []
    items: list[str] = []
    next_header = re.compile(r"^\s{0,3}[A-Za-z_][A-Za-z0-9_]*:\s*")
    for line in block[header.end():].splitlines():
        if next_header.match(line):
            break
        stripped = line.strip()
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                items.append(item)
    return items


def _parse_repeated_values(block: str, key: str) -> list[str]:
    items: list[str] = []
    for match in re.finditer(rf"^\s*{re.escape(key)}:\s*(.+)$", block, re.MULTILINE | re.IGNORECASE):
        value = match.group(1).strip().lstrip("- ").strip()
        if value and value.lower() != "none":
            items.append(value)
    return items


def _parse_int(value: str) -> int | None:
    match = re.search(r"[0-9][0-9,_]*", str(value or ""))
    if not match:
        return None
    try:
        return int(re.sub(r"[,_]", "", match.group(0)))
    except ValueError:
        return None


def _parse_tests(value: str) -> dict[str, int]:
    if not value:
        return {}
    tests = {"passed": 0, "failed": 0, "xfail": 0, "skipped": 0}
    found = False
    for match in re.finditer(r"(\d+)\s+(passed|pass|failed|fail|xfail|skipped|skip)", value, re.IGNORECASE):
        label = match.group(2).lower()
        label = {"pass": "passed", "fail": "failed", "skip": "skipped"}.get(label, label)
        tests[label] = int(match.group(1))
        found = True
    return tests if found else {}


def _format_tests(tests: dict[str, int]) -> str:
    parts = [f"{tests[k]} {k}" for k in ("passed", "failed", "xfail", "skipped") if tests.get(k)]
    if not parts and tests:
        parts = [f"{k}={v}" for k, v in tests.items()]
    return "TESTS: " + ", ".join(parts)
