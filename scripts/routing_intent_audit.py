#!/usr/bin/env python3
# SCOPE: os-only
"""Audit SKILL.md routing_intents quality.

This script is intentionally read-only. It identifies skills that are risky for
language-agnostic semantic routing because they have no routing_intents or only
low-signal generic intent descriptions.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_GENERIC_PHRASES = (
    "use when you need this cognitive os skill",
    "do not use when a narrower skill directly matches",
    "this cognitive os skill",
    "step-by-step guide",
)
_GENERIC_WORDS = {
    "skill",
    "tool",
    "task",
    "thing",
    "stuff",
    "help",
    "use",
    "run",
    "do",
    "make",
    "create",
    "manage",
    "process",
}


@dataclass(frozen=True)
class IntentIssue:
    code: str
    message: str


@dataclass(frozen=True)
class SkillIntentAudit:
    skill: str
    path: str
    intent_count: int
    issues: list[IntentIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class AuditReport:
    root: str
    skill_count: int
    skills_with_intents: int
    issue_count: int
    audits: list[SkillIntentAudit]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def iter_skill_files(root: Path) -> Iterable[Path]:
    for base_name in ("skills", "packages"):
        base = root / base_name
        if not base.exists():
            continue
        yield from sorted(base.rglob("SKILL.md"))


def _frontmatter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _normalise_intents(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            intent = str(item.get("intent") or "").strip()
            desc = str(item.get("description") or "").strip()
            if intent or desc:
                out.append(f"{intent}: {desc}" if intent and desc else intent or desc)
        elif isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_]+", text))


def _is_low_signal(text: str, *, skill: str = "") -> bool:
    lowered = text.lower()
    if skill == "run-tests" and lowered == "run the tests":
        return False
    if any(phrase in lowered for phrase in _GENERIC_PHRASES):
        return True
    words = re.findall(r"[a-z]+", lowered)
    if len(words) < 6:
        return True
    informative = [w for w in words if w not in _GENERIC_WORDS]
    return len(informative) < 4


def audit_skill(path: Path, root: Path) -> SkillIntentAudit:
    data = _frontmatter(path)
    skill = str(data.get("name") or path.parent.name).strip() or path.parent.name
    intents = _normalise_intents(data.get("routing_intents"))
    issues: list[IntentIssue] = []
    if not intents:
        issues.append(IntentIssue("missing-routing-intents", "No routing_intents declared."))
    else:
        low_signal = [intent for intent in intents if _is_low_signal(intent, skill=skill)]
        if low_signal:
            issues.append(
                IntentIssue(
                    "low-signal-routing-intent",
                    f"{len(low_signal)} routing_intents are too short or generic.",
                )
            )
        combined_words = _word_count(" ".join(intents))
        if combined_words < 10:
            issues.append(
                IntentIssue(
                    "thin-routing-intents",
                    "Combined routing_intents text has fewer than 10 words.",
                )
            )
    return SkillIntentAudit(
        skill=skill,
        path=str(path.relative_to(root)),
        intent_count=len(intents),
        issues=issues,
    )


def audit(root: Path) -> AuditReport:
    root = root.resolve()
    audits = [audit_skill(path, root) for path in iter_skill_files(root)]
    return AuditReport(
        root=str(root),
        skill_count=len(audits),
        skills_with_intents=sum(1 for item in audits if item.intent_count > 0),
        issue_count=sum(len(item.issues) for item in audits),
        audits=audits,
    )


def render_markdown(report: AuditReport, *, limit: int = 50) -> str:
    lines = [
        "# Routing Intents Audit",
        "",
        f"- Root: `{report.root}`",
        f"- Skills scanned: {report.skill_count}",
        f"- Skills with routing_intents: {report.skills_with_intents}",
        f"- Issues: {report.issue_count}",
        "",
        "## Findings",
        "",
        "| skill | intents | issues | path |",
        "| --- | ---: | --- | --- |",
    ]
    findings = [item for item in report.audits if item.issues]
    for item in findings[:limit]:
        issues = "; ".join(f"{issue.code}: {issue.message}" for issue in item.issues)
        lines.append(f"| {item.skill} | {item.intent_count} | {issues} | `{item.path}` |")
    if len(findings) > limit:
        lines.append(f"| ... | ... | {len(findings) - limit} more findings omitted | ... |")
    if not findings:
        lines.append("| _none_ |  |  |  |")
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit SKILL.md routing_intents quality.")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--fail-on-issues", action="store_true", help="Exit 1 when issues are found")
    parser.add_argument("--limit", type=int, default=50, help="Maximum findings in Markdown output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit(Path(args.root))
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(render_markdown(report, limit=args.limit))
    return 1 if args.fail_on_issues and report.issue_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
