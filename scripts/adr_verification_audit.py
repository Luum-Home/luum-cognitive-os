#!/usr/bin/env python3
# SCOPE: both
"""Classify ADR verification evidence and block grep-only theater.

ADR-067 requires ADRs to include a ``## Verification`` section with a fenced
code block. This audit tightens that structural contract into an evidence
contract: verification must contain a meaningful command, not merely a search for
an ADR number.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
ADRS_DIR = ROOT / "docs" / "02-Decisions" / "adrs"
SCHEMA_VERSION = "adr-verification-audit/v1"
ENFORCEMENT_CUTOFF = 67
STRONG_PATTERNS = (
    r"\bpytest\b",
    r"python3?\s+-m\s+pytest\b",
    r"python3?\s+-m\s+py_compile\b",
    r"\bbash\s+-n\b",
    r"\b(shellcheck|ruff|mypy|npm\s+test|go\s+test|cargo\s+test)\b",
    r"\b(smoke|audit|verify|validate|check)\b.*\b(--fail|--strict|--fail-on-block|--fail-hard-gaps)\b",
    r"\bcos-[\w-]*(audit|smoke|verify|validate|check)\b",
)
MEDIUM_PATTERNS = (
    r"\b(test|\[)\s+-[efdx]\b",
    r"\bls\s+-la\b",
    r"\bstat\b",
)
WEAK_PATTERNS = (
    r"\bgrep\s+-rn?\s+['\"]?ADR-?\d{1,4}",
    r"\bgrep\b.*\bADR-?\d{1,4}\b",
    r"\bfind\b.*\bADR-?\d{1,4}\b",
    r"\bls\b.*docs/02-Decisions/adrs/ADR-?\d{1,4}",
)
INVALID_PATTERNS = (
    r"^\s*$",
    r"^\s*(true|false)\b",
    r"\b(TODO|Replace before accepting|intentionally missing)\b",
    r"^\s*echo\b",
)
IMPLEMENTED_STATUSES = {"implemented", "partial"}
NON_RUNTIME_STATUSES = {"not-applicable", "planned", "deferred"}


@dataclass(frozen=True)
class VerificationCommand:
    command: str
    level: str
    reason: str


@dataclass(frozen=True)
class AdrVerificationRow:
    adr: int
    path: str
    implementation_status: str
    declared_level: str | None
    derived_level: str
    status: str
    severity: str
    message: str
    commands: list[dict[str, str]]
    missing_implementation_files: list[str]
    next_action: str


def adr_number(path: Path) -> int:
    match = re.match(r"ADR-0*([0-9]+)", path.name)
    return int(match.group(1)) if match else 0


def extract_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        data = {}
    return data if isinstance(data, dict) else {}, parts[2]


def section_body(text: str, section: str) -> str | None:
    match = re.search(
        rf"^## {re.escape(section)}\b(.+?)(?=^## |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else None


def fenced_blocks(body: str) -> list[str]:
    return [m.group("body") for m in re.finditer(r"^```[^\n]*\n(?P<body>.*?)^```", body, re.MULTILINE | re.DOTALL)]


def split_commands(blocks: Iterable[str]) -> list[str]:
    commands: list[str] = []
    pending = ""
    for block in blocks:
        for raw in block.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith("\\"):
                pending += line[:-1].strip() + " "
                continue
            line = (pending + line).strip()
            pending = ""
            commands.append(line)
    if pending.strip():
        commands.append(pending.strip())
    return commands


def matches_any(command: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, command, flags=re.IGNORECASE) for pattern in patterns)


def classify_command(command: str) -> VerificationCommand:
    if matches_any(command, INVALID_PATTERNS):
        return VerificationCommand(command, "invalid", "placeholder_or_no_assertion")
    if matches_any(command, STRONG_PATTERNS):
        return VerificationCommand(command, "strong", "behavior_or_audit_command")
    if matches_any(command, MEDIUM_PATTERNS):
        return VerificationCommand(command, "medium", "presence_or_compile_surface_check")
    if matches_any(command, WEAK_PATTERNS):
        return VerificationCommand(command, "weak", "generic_adr_text_search")
    # Conservative defaults: concrete repository script/test invocations are
    # stronger than grep theater even when they do not use pytest directly.
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    if parts:
        joined = " ".join(parts)
        if parts[0].startswith(("scripts/", "./scripts/")):
            return VerificationCommand(command, "strong", "repo_script_invocation")
        if len(parts) > 1 and parts[0] in {"bash", "python", "python3"} and parts[1].startswith(("scripts/", "./scripts/", "tests/", "./tests/")):
            return VerificationCommand(command, "strong", "repo_script_or_test_invocation")
        if "_audit" in joined and re.search(r"\b(--strict|--fail|--fail-on-block|--json)\b", joined):
            return VerificationCommand(command, "strong", "audit_command_with_gate")
    return VerificationCommand(command, "weak", "unclassified_command")


def strongest_level(commands: list[VerificationCommand]) -> str:
    order = {"invalid": 0, "weak": 1, "medium": 2, "strong": 3, "not-applicable": 4}
    if not commands:
        return "invalid"
    return max((cmd.level for cmd in commands), key=lambda level: order.get(level, 0))


def path_exists(root: Path, rel: str) -> bool:
    rel = str(rel).split("#", 1)[0].strip()
    if not rel:
        return False
    if rel.startswith(".cognitive-os/"):
        return True
    if "*" in rel:
        return any(root.glob(rel))
    return (root / rel.rstrip("/")).exists()


def declared_verification(fm: dict[str, Any]) -> tuple[str | None, list[str]]:
    raw = fm.get("verification")
    if not isinstance(raw, dict):
        return None, []
    level = raw.get("level")
    commands = raw.get("commands") or []
    if isinstance(commands, str):
        commands = [commands]
    return (str(level) if level is not None else None), [str(cmd) for cmd in commands if str(cmd).strip()]


def audit_adr_file(path: Path, root: Path = ROOT) -> AdrVerificationRow:
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, _body = extract_frontmatter(text)
    implementation_status = str(fm.get("implementation_status") or "unknown")
    declared_level, declared_commands = declared_verification(fm)
    body = section_body(text, "Verification")
    block_commands = split_commands(fenced_blocks(body or ""))
    commands = [classify_command(cmd) for cmd in [*declared_commands, *block_commands]]
    derived = strongest_level(commands)
    impl_files = fm.get("implementation_files") or []
    if not isinstance(impl_files, list):
        impl_files = []
    missing_impl = [str(item) for item in impl_files if not path_exists(root, str(item))]

    failures: list[str] = []
    if body is None:
        failures.append("missing_verification_section")
    elif not fenced_blocks(body):
        failures.append("missing_fenced_code_block")
    if commands and all(cmd.level in {"weak", "invalid"} for cmd in commands):
        failures.append("weak_only_verification")
    if any(cmd.reason == "generic_adr_text_search" for cmd in commands) and not any(cmd.level in {"medium", "strong"} for cmd in commands):
        failures.append("generic_adr_grep_only")
    if implementation_status in IMPLEMENTED_STATUSES and not any(cmd.level == "strong" for cmd in commands):
        failures.append("implemented_without_strong_verification")
    if missing_impl:
        failures.append("missing_implementation_files")
    if declared_level == "weak" and implementation_status in IMPLEMENTED_STATUSES:
        failures.append("declared_weak_for_implemented")

    status = "fail" if failures else "pass"
    message = "pass" if not failures else ", ".join(failures)
    if declared_level == "not-applicable" and implementation_status in NON_RUNTIME_STATUSES and not missing_impl:
        # Non-runtime ADRs may verify decision state; still require a code block
        # and still block grep-only theater via failures above.
        if failures == ["implemented_without_strong_verification"]:
            status = "pass"
            message = "declared_not_applicable"

    return AdrVerificationRow(
        adr=adr_number(path),
        path=path.relative_to(root).as_posix(),
        implementation_status=implementation_status,
        declared_level=declared_level,
        derived_level=derived,
        status=status,
        severity="high" if status == "fail" else "info",
        message=message,
        commands=[asdict(cmd) for cmd in commands],
        missing_implementation_files=missing_impl,
        next_action=(
            "replace grep-only verification with behavior/audit/smoke commands and fix missing implementation files"
            if status == "fail"
            else "keep verification evidence current"
        ),
    )


def adr_files(root: Path) -> list[Path]:
    return sorted((root / "docs" / "02-Decisions" / "adrs").glob("ADR-*.md"), key=lambda p: (adr_number(p), p.name))


def build_report(root: Path) -> dict[str, Any]:
    rows = [audit_adr_file(path, root=root) for path in adr_files(root) if adr_number(path) >= ENFORCEMENT_CUTOFF]
    by_status: dict[str, int] = {}
    by_level: dict[str, int] = {}
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1
        by_level[row.derived_level] = by_level.get(row.derived_level, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "block" if by_status.get("fail", 0) else "pass",
        "summary": {
            "rows": len(rows),
            "by_status": by_status,
            "by_level": by_level,
            "fail_count": by_status.get("fail", 0),
        },
        "rows": [asdict(row) for row in rows],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit ADR verification evidence strength.")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-weak", action="store_true", help="Exit 2 when weak/invalid verification remains.")
    args = parser.parse_args(argv)
    root = Path(args.project_dir).resolve()
    report = build_report(root)
    if args.json or True:
        print(json.dumps(report, indent=2 if not args.json else None, sort_keys=True))
    if args.fail_on_weak and report["status"] == "block":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
