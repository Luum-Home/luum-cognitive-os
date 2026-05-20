#!/usr/bin/env python3
# SCOPE: os-only
"""Audit skill platform support levels.

ADR-329 keeps the legacy `platforms` list for loader compatibility but requires
precise support metadata for high-risk generic CLI claims.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

VALID_SUPPORT_LEVELS = {
    "loadable",
    "documented-only",
    "advisory",
    "executable",
    "lifecycle-enforced",
}
STRICT_PLATFORM = "generic-cli"


@dataclass(frozen=True)
class Finding:
    path: str
    code: str
    severity: str
    rationale: str


def _load_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end < 0:
        return {}
    data = yaml.safe_load(text[3:end]) or {}
    return data if isinstance(data, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _platform_support(data: dict[str, Any], platform: str) -> dict[str, Any]:
    support = data.get("platform_support")
    if not isinstance(support, dict):
        return {}
    entry = support.get(platform)
    return entry if isinstance(entry, dict) else {}


def audit_skill(path: Path, root: Path, *, strict_platform: str = STRICT_PLATFORM) -> list[Finding]:
    rel = str(path.relative_to(root))
    data = _load_frontmatter(path)
    platforms = _as_list(data.get("platforms"))
    findings: list[Finding] = []
    if strict_platform not in platforms:
        return findings

    entry = _platform_support(data, strict_platform)
    if not entry:
        findings.append(
            Finding(
                path=rel,
                code="missing-platform-support",
                severity="block",
                rationale=f"declares {strict_platform} but lacks platform_support.{strict_platform}",
            )
        )
        return findings

    level = entry.get("support_level")
    if level not in VALID_SUPPORT_LEVELS:
        findings.append(
            Finding(
                path=rel,
                code="invalid-support-level",
                severity="block",
                rationale=f"{strict_platform} support_level must be one of {sorted(VALID_SUPPORT_LEVELS)}; got {level!r}",
            )
        )

    evidence = _as_list(entry.get("evidence"))
    if not evidence or not all(isinstance(item, str) and item.strip() for item in evidence):
        findings.append(
            Finding(
                path=rel,
                code="missing-platform-evidence",
                severity="block",
                rationale=f"{strict_platform} support metadata must cite at least one evidence string",
            )
        )

    if level == "lifecycle-enforced":
        joined = "\n".join(str(item) for item in evidence)
        if not any(marker in joined for marker in ("hooks/", ".claude/", ".codex/", "primitive-contracts", "tests/")):
            findings.append(
                Finding(
                    path=rel,
                    code="weak-lifecycle-evidence",
                    severity="block",
                    rationale="lifecycle-enforced support must cite hook, settings, contract, or test evidence",
                )
            )
    return findings


def build_report(root: Path, *, strict_platform: str = STRICT_PLATFORM) -> dict[str, Any]:
    skills = sorted((root / "skills").glob("*/SKILL.md"))
    findings: list[Finding] = []
    by_support: dict[str, int] = {}
    generic_cli_total = 0
    for path in skills:
        data = _load_frontmatter(path)
        platforms = _as_list(data.get("platforms"))
        if strict_platform in platforms:
            generic_cli_total += 1
            entry = _platform_support(data, strict_platform)
            level = str(entry.get("support_level") or "missing")
            by_support[level] = by_support.get(level, 0) + 1
        findings.extend(audit_skill(path, root, strict_platform=strict_platform))

    return {
        "schema_version": "skill-platform-support-audit/v1",
        "strict_platform": strict_platform,
        "skills_scanned": len(skills),
        "strict_platform_skills": generic_cli_total,
        "by_support_level": dict(sorted(by_support.items())),
        "findings": [asdict(finding) for finding in findings],
        "summary": {
            "findings": len(findings),
            "blockers": sum(1 for finding in findings if finding.severity == "block"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--strict-platform", default=STRICT_PLATFORM)
    parser.add_argument("--json-out")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.project_dir).resolve()
    report = build_report(root, strict_platform=args.strict_platform)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n", encoding="utf-8")
    print(json.dumps(report["summary"] | {"strict_platform_skills": report["strict_platform_skills"]}, sort_keys=True))
    if args.strict and report["summary"]["blockers"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
