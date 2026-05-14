#!/usr/bin/env python3
# SCOPE: os-only
"""Deterministic license/default gate for Agentic Mastery optional tools.

The gate reads a pinned JSON manifest and emits a Markdown report. It is pure
stdlib by design: tests and core validation must not need network access or
third-party packages.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST = Path(".cognitive-os/tests/agentic-tools/license-matrix.json")
BLOCKED_LICENSE_TOKENS = ("AGPL", "SSPL", "BSL", "ELV2", "COMMONS-CLAUSE")
HEAVY_WEIGHTS = {"high", "very high", "very-high", "very_high"}
ALLOWED_INSTALL_MODES = {"none", "optional-cli", "optional-container", "dev-only", "vendored"}
REQUIRED_FIELDS = ("name", "license_spdx", "install_mode", "default_enabled", "data_sharing", "weight")


@dataclass(frozen=True)
class ToolRecord:
    name: str
    version_ref: str
    license_spdx: str
    install_mode: str
    default_enabled: bool
    data_sharing: str
    weight: str
    source: str = ""
    notes: str = ""


@dataclass(frozen=True)
class GateFinding:
    tool: str
    severity: str
    rule: str
    message: str


@dataclass(frozen=True)
class GateResult:
    generated_at: str
    manifest_path: str
    tools: list[ToolRecord]
    findings: list[GateFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(finding.severity == "block" for finding in self.findings)


def normalize_license_id(value: str) -> str:
    """Normalize common SPDX spelling variants for policy matching."""
    text = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-").upper()
    return text.replace("ELASTIC-LICENSE-2-0", "ELV2")


def is_blocked_license(license_spdx: str) -> bool:
    normalized = normalize_license_id(license_spdx)
    return any(token in normalized for token in BLOCKED_LICENSE_TOKENS)


def is_heavy_weight(weight: str) -> bool:
    return weight.strip().lower() in HEAVY_WEIGHTS


def is_external_install(install_mode: str) -> bool:
    return install_mode.strip().lower() != "none"


def load_manifest(path: Path) -> list[ToolRecord]:
    """Load a manifest shaped as either {"tools": [...]} or a bare list."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("tools") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        raise ValueError("manifest must be a JSON list or an object with a 'tools' list")

    tools: list[ToolRecord] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"tool #{index} must be an object")
        missing = [field for field in REQUIRED_FIELDS if field not in row]
        if "version_ref" not in row and "version" not in row and "ref" not in row:
            missing.append("version_ref|version|ref")
        if missing:
            raise ValueError(f"tool #{index} missing required field(s): {', '.join(missing)}")
        if not isinstance(row["default_enabled"], bool):
            raise ValueError(f"tool #{index} default_enabled must be boolean")
        install_mode = str(row["install_mode"])
        if install_mode not in ALLOWED_INSTALL_MODES:
            raise ValueError(
                f"tool #{index} install_mode must be one of {', '.join(sorted(ALLOWED_INSTALL_MODES))}"
            )
        tools.append(
            ToolRecord(
                name=str(row["name"]),
                version_ref=str(row.get("version_ref") or row.get("version") or row.get("ref")),
                license_spdx=str(row["license_spdx"]),
                install_mode=install_mode,
                default_enabled=row["default_enabled"],
                data_sharing=str(row["data_sharing"]),
                weight=str(row["weight"]),
                source=str(row.get("source", "")),
                notes=str(row.get("notes", "")),
            )
        )
    return tools


def evaluate_tools(tools: list[ToolRecord], manifest_path: Path) -> GateResult:
    findings: list[GateFinding] = []
    for tool in tools:
        if is_blocked_license(tool.license_spdx):
            findings.append(
                GateFinding(
                    tool=tool.name,
                    severity="block",
                    rule="blocked-license",
                    message="Blocked SPDX family: AGPL, SSPL, BSL, ELv2, or Commons-Clause.",
                )
            )
        if tool.default_enabled and is_external_install(tool.install_mode) and is_heavy_weight(tool.weight):
            findings.append(
                GateFinding(
                    tool=tool.name,
                    severity="block",
                    rule="heavy-external-default",
                    message="Heavy external tools must be opt-in; default_enabled must be false.",
                )
            )
        if tool.default_enabled and tool.data_sharing.strip().lower() not in {"none", "local-only"}:
            findings.append(
                GateFinding(
                    tool=tool.name,
                    severity="warn",
                    rule="default-data-sharing",
                    message="Default-enabled tools should not share code, prompts, or skill contents off-machine.",
                )
            )
    return GateResult(
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        manifest_path=str(manifest_path),
        tools=tools,
        findings=findings,
    )


def render_markdown(result: GateResult) -> str:
    status = "PASS" if result.passed else "BLOCK"
    lines = [
        "# Agentic Mastery Tool License Gate Report",
        "",
        f"- Status: **{status}**",
        f"- Generated: `{result.generated_at}`",
        f"- Manifest: `{result.manifest_path}`",
        f"- Tools evaluated: {len(result.tools)}",
        f"- Blocking findings: {sum(1 for finding in result.findings if finding.severity == 'block')}",
        "",
        "## Policy checks",
        "",
        "- Block licenses: AGPL, SSPL, BSL, ELv2, Commons-Clause.",
        "- Block `default_enabled=true` for external tools with `High` or `Very high` weight.",
        "- Warn when default-enabled tools share data beyond local-only execution.",
        "",
        "## Tools",
        "",
        "| Tool | Version/ref | License | Install mode | Default | Data sharing | Weight | Status |",
        "|---|---|---|---|---:|---|---|---|",
    ]
    findings_by_tool: dict[str, list[GateFinding]] = {}
    for finding in result.findings:
        findings_by_tool.setdefault(finding.tool, []).append(finding)
    for tool in result.tools:
        tool_findings = findings_by_tool.get(tool.name, [])
        if any(finding.severity == "block" for finding in tool_findings):
            tool_status = "BLOCK"
        elif tool_findings:
            tool_status = "WARN"
        else:
            tool_status = "PASS"
        lines.append(
            "| "
            + " | ".join(
                [
                    tool.name,
                    tool.version_ref,
                    tool.license_spdx,
                    tool.install_mode,
                    "true" if tool.default_enabled else "false",
                    tool.data_sharing,
                    tool.weight,
                    tool_status,
                ]
            )
            + " |"
        )
    lines.extend(["", "## Findings", ""])
    if not result.findings:
        lines.append("No findings.")
    else:
        for finding in result.findings:
            lines.append(f"- **{finding.severity.upper()}** `{finding.tool}` `{finding.rule}` — {finding.message}")
    lines.append("")
    return "\n".join(lines)


def result_to_dict(result: GateResult) -> dict[str, Any]:
    return {
        "generated_at": result.generated_at,
        "manifest_path": result.manifest_path,
        "passed": result.passed,
        "tools": [asdict(tool) for tool in result.tools],
        "findings": [asdict(finding) for finding in result.findings],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Agentic Mastery tool license gate.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to the JSON tool manifest.")
    parser.add_argument("--markdown-out", type=Path, help="Optional path for the Markdown report.")
    parser.add_argument("--json-out", type=Path, help="Optional path for the machine-readable result.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        tools = load_manifest(args.manifest)
        result = evaluate_tools(tools, args.manifest)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"license gate error: {exc}", file=sys.stderr)
        return 2

    markdown = render_markdown(result)
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown, encoding="utf-8")
    else:
        print(markdown)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result_to_dict(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
