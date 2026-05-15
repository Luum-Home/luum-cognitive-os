#!/usr/bin/env python3
# SCOPE: both
"""Validate Executable Acceptance Specification (EAS) Markdown artifacts.

EAS is the evidence artifact. EARS (Easy Approach to Requirements Syntax) is
a requirements-writing syntax that EAS may embed in its Requirements section.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REQUIRED_SECTIONS = (
    "Intent",
    "Requirements",
    "Non-goals",
    "Executable Acceptance Criteria",
    "Gap Matrix",
    "Adversarial Personas",
    "Detractor Mode",
    "Detractor Objection Log",
    "Verification Commands",
    "Residual Risks",
)

_PLACEHOLDER_RE = re.compile(r"<[^>]+>|\b(tbd|todo|fixme|n/a)\b", re.IGNORECASE)
_REQ_RE = re.compile(r"\bREQ-[A-Za-z0-9._-]+\b")
_AC_RE = re.compile(r"\bAC-[A-Za-z0-9._-]+\b")
_OBJ_RE = re.compile(r"\bOBJ-[A-Za-z0-9._-]+\b")
_UNCOVERED_RE = re.compile(r"\b(gap|uncovered|missing|none|partial)\b", re.IGNORECASE)
_RESOLVED_RE = re.compile(r"\b(resolved|covered|task|residual risk|accepted risk|mitigated)\b", re.IGNORECASE)
_NONE_RISK_RE = re.compile(r"\b(no residual risks?|none)\b", re.IGNORECASE)
_DETRACTOR_MODE_RE = re.compile(
    r"\b(Tenth Man Rule|Tenth Man|Devil'?s Advocate|Pre-mortem|Premortem|Black Hat|Red Team)\b",
    re.IGNORECASE,
)
_EARS_RE = re.compile(
    r"(?:\bWHEN\b.+\bTHE SYSTEM SHALL\b|"
    r"\bIF\b.+\bTHEN\b.+\bTHE SYSTEM SHALL\b|"
    r"\bWHILE\b.+\bTHE SYSTEM SHALL\b|"
    r"\bWHERE\b.+\bTHE SYSTEM SHALL\b|"
    r"\bTHE SYSTEM SHALL\b)",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class EASValidationResult:
    path: str
    ok: bool
    errors: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _normalize_heading(text: str) -> str:
    text = re.sub(r"^\d+\.\s*", "", text.strip())
    return re.sub(r"\s+", " ", text).strip().lower()


def _sections(markdown: str) -> dict[str, str]:
    headings: list[tuple[str, int, int]] = []
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^(#{2,6})\s+(.+?)\s*$", line)
        if match:
            headings.append((_normalize_heading(match.group(2)), len(match.group(1)), index))
    result: dict[str, str] = {}
    for i, (name, level, start) in enumerate(headings):
        end = len(lines)
        for next_name, next_level, next_index in headings[i + 1 :]:
            if next_level <= level:
                end = next_index
                break
        result[name] = "\n".join(lines[start + 1 : end]).strip()
    return result


def _table_rows(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
            continue
        rows.append(cells)
    if rows and not any(re.search(r"\bREQ-|\bAC-|\bOBJ-|detractor", " ".join(row), re.IGNORECASE) for row in rows[:1]):
        return rows[1:]
    return rows


def _non_placeholder(value: str) -> bool:
    return bool(value.strip()) and not _PLACEHOLDER_RE.search(value)


def _ids(pattern: re.Pattern[str], values: Iterable[str]) -> set[str]:
    found: set[str] = set()
    for value in values:
        found.update(match.group(0) for match in pattern.finditer(value))
    return found


def _requirement_rows(section: str) -> list[list[str]]:
    rows = _table_rows(section)
    if rows:
        return rows
    bullet_rows: list[list[str]] = []
    for line in section.splitlines():
        match = re.match(r"^\s*[-*]\s+(REQ-[A-Za-z0-9._-]+)\s*:?\s*(.+?)\s*$", line)
        if match:
            bullet_rows.append([match.group(1), match.group(2), "functional"])
    return bullet_rows


def _is_functional_requirement(row: list[str]) -> bool:
    if len(row) >= 3 and re.search(r"\bfunctional\b", row[2], re.IGNORECASE):
        return True
    return len(row) < 3


def _requirement_text(row: list[str]) -> str:
    if len(row) >= 2:
        return row[1]
    return " ".join(row)


def _ears_like(text: str) -> bool:
    return bool(_EARS_RE.search(text))


def validate_eas_text(markdown: str, path: str = "<memory>", *, require_ears: bool = False) -> EASValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    sections = _sections(markdown)

    for section in REQUIRED_SECTIONS:
        key = _normalize_heading(section)
        if key not in sections:
            errors.append(f"missing required section: {section}")
        elif not sections[key].strip():
            errors.append(f"empty required section: {section}")

    requirements = sections.get("requirements", "")
    acceptance = sections.get("executable acceptance criteria", "")
    gap_matrix = sections.get("gap matrix", "")
    personas = sections.get("adversarial personas", "")
    detractor_mode = sections.get("detractor mode", "")
    objections = sections.get("detractor objection log", "")
    commands = sections.get("verification commands", "")
    residual = sections.get("residual risks", "")

    req_ids = _ids(_REQ_RE, [requirements])
    req_rows = _requirement_rows(requirements)
    ac_rows = _table_rows(acceptance)
    gap_rows = _table_rows(gap_matrix)
    objection_rows = _table_rows(objections)
    residual_rows = _table_rows(residual)

    if not req_ids:
        errors.append("requirements section must define at least one REQ-* id")

    for row in req_rows:
        row_text = " ".join(row)
        if not _REQ_RE.search(row_text) or not _is_functional_requirement(row):
            continue
        requirement = _requirement_text(row)
        if not _ears_like(requirement):
            message = f"functional requirement should use EARS syntax: {row_text}"
            if require_ears:
                errors.append(message)
            else:
                warnings.append(message)

    ac_by_req: dict[str, list[list[str]]] = {req: [] for req in req_ids}
    for row in ac_rows:
        row_text = " ".join(row)
        if not _AC_RE.search(row_text):
            continue
        if len(row) >= 5 and not _non_placeholder(row[3]):
            errors.append(f"acceptance row lacks verification method: {row_text}")
        if len(row) >= 5 and not _non_placeholder(row[4]):
            errors.append(f"acceptance row lacks expected result: {row_text}")
        for req in req_ids:
            if req in row_text:
                ac_by_req.setdefault(req, []).append(row)

    if not _ids(_AC_RE, [acceptance]):
        errors.append("executable acceptance criteria must define at least one AC-* id")

    for req, rows in ac_by_req.items():
        if not rows:
            errors.append(f"requirement {req} has no acceptance criteria coverage")

    gap_by_req: dict[str, list[list[str]]] = {req: [] for req in req_ids}
    for row in gap_rows:
        row_text = " ".join(row)
        for req in req_ids:
            if req in row_text:
                gap_by_req.setdefault(req, []).append(row)
        if _REQ_RE.search(row_text):
            evidence = row[2] if len(row) >= 3 else ""
            status = row[3] if len(row) >= 4 else ""
            if not _non_placeholder(evidence):
                errors.append(f"gap matrix row lacks evidence: {row_text}")
            if _UNCOVERED_RE.search(status):
                errors.append(f"gap matrix row is not fully covered: {row_text}")

    for req, rows in gap_by_req.items():
        if not rows:
            errors.append(f"requirement {req} is missing from gap matrix")

    if "detractor" not in personas.lower():
        errors.append("adversarial personas must include a Detractor persona")

    if not _DETRACTOR_MODE_RE.search(detractor_mode):
        errors.append(
            "detractor mode must name at least one mode: Tenth Man Rule, Devil's Advocate, Pre-mortem, Black Hat, or Red Team"
        )

    if not _ids(_OBJ_RE, [objections]):
        errors.append("detractor objection log must define at least one OBJ-* id")
    for row in objection_rows:
        row_text = " ".join(row)
        if not _OBJ_RE.search(row_text):
            continue
        if len(row) < 5:
            errors.append(f"detractor objection row must include disposition: {row_text}")
            continue
        disposition = row[4]
        if not _non_placeholder(disposition) or not _RESOLVED_RE.search(disposition):
            errors.append(f"detractor objection disposition is unresolved: {row_text}")

    command_lines = [line.strip() for line in commands.splitlines() if line.strip() and not line.strip().startswith("```")]
    real_command_lines = [line for line in command_lines if _non_placeholder(line)]
    if not real_command_lines:
        errors.append("verification commands section must include at least one concrete command or manual check")

    residual_text = residual.strip()
    residual_has_table_evidence = any(any(_non_placeholder(cell) for cell in row) for row in residual_rows)
    if not residual_text:
        errors.append("residual risks section must explicitly list risks or state that none remain")
    elif not residual_has_table_evidence and not _NONE_RISK_RE.search(residual_text):
        errors.append("residual risks section must include concrete risk rows or explicitly state that none remain")

    if len(req_ids) != len(set(req_ids)):
        warnings.append("duplicate requirement ids detected")

    return EASValidationResult(path=path, ok=not errors, errors=errors, warnings=warnings)


def validate_eas_file(path: Path, *, require_ears: bool = False) -> EASValidationResult:
    return validate_eas_text(path.read_text(encoding="utf-8"), str(path), require_ears=require_ears)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an Executable Acceptance Specification Markdown file.")
    parser.add_argument("path", type=Path, help="Path to EAS Markdown file")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--require-ears", action="store_true", help="Fail functional requirements that do not use EARS syntax")
    args = parser.parse_args(argv)

    result = validate_eas_file(args.path, require_ears=args.require_ears)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    elif result.ok:
        print(f"EAS validation passed: {result.path}")
        for warning in result.warnings:
            print(f"WARN: {warning}")
    else:
        print(f"EAS validation failed: {result.path}")
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARN: {warning}")
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
