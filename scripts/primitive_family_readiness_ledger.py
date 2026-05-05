#!/usr/bin/env python3
# SCOPE: os-only
"""Build primitive readiness ledgers for hooks, skills, and rules.

This complements the script ledger with family-specific role taxonomies while
keeping the same evidence-first shape: role, role source, confidence, lifecycle
metadata, consumers, consumer accessibility, evidence, and next action.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.script_io import read_text as read_text
from lib.project_paths import relpath as relpath
from lib.primitive_readiness_common import family_counts, load_lifecycle, row_to_dict
from typing import Any


REPO_IGNORE_PARTS = {"__pycache__", ".pytest_cache", ".venv", "node_modules", ".git"}
REPO_IGNORE_PREFIXES = ("docs/reports/", "dashboard/.next/", ".claude/plugins/")
FAMILIES = {"hooks", "skills", "rules"}
ROLES = {
    "hooks": {"runtime-safety", "observability", "memory-lifecycle", "driver-specific", "lab", "archive"},
    "skills": {"shared-agent-tool", "so-maintainer", "project-extension", "compatibility-wrapper", "lab", "archive"},
    "rules": {"hook-enforced", "context-only", "doctrine", "driver-specific", "lab", "archive"},
}
INACTIVE_STATES = {"candidate", "demoted", "archived", "deleted"}
CONSUMER_PATTERNS = [
    "skills/**/SKILL.md",
    ".codex/skills/**/SKILL.md",
    "hooks/**/*.sh",
    "rules/**/*.md",
    "agents/**/*",
    "docs/**/*.md",
    "tests/**/*.py",
    "scripts/**/*",
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".claude/**/*.json",
    ".codex/**/*.json",
    ".cursor/**/*.json",
    ".windsurf/**/*.json",
    "manifests/**/*.yaml",
    "manifests/**/*.json",
    "AGENTS.md",
    "README.md",
    "cognitive-os.yaml",
]


@dataclass(frozen=True)
class Consumer:
    family: str
    path: str


@dataclass
class FamilyRow:
    path: str
    family: str
    role: str
    role_source: str
    confidence: str
    lifecycle_id: str | None = None
    lifecycle_state: str | None = None
    distribution: str | None = None
    supported_harnesses: list[str] = field(default_factory=list)
    consumer_accessibility: str = "so-local-only"
    consumer_access_next_action: str = ""
    total_consumers: int = 0
    consumer_families: dict[str, int] = field(default_factory=dict)
    consumers: list[Consumer] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    next_action: str = ""


def ignored(root: Path, path: Path) -> bool:
    rel = relpath(root, path)
    return bool(REPO_IGNORE_PARTS.intersection(path.relative_to(root).parts)) or any(
        rel.startswith(prefix) for prefix in REPO_IGNORE_PREFIXES
    )


def target_files(root: Path, family: str) -> list[Path]:
    if family == "hooks":
        files = [path for path in (root / "hooks").rglob("*.sh") if path.is_file()]
    elif family == "skills":
        files = [path for base in (root / "skills", root / ".codex" / "skills") if base.exists() for path in base.rglob("SKILL.md") if path.is_file()]
    elif family == "rules":
        files = [path for path in (root / "rules").rglob("*.md") if path.is_file()]
    else:
        raise ValueError(f"unsupported family: {family}")
    return sorted([path for path in files if not ignored(root, path)], key=lambda item: relpath(root, item))


def classify_consumer(root: Path, path: Path) -> str:
    rel = relpath(root, path)
    if rel.startswith("hooks/"):
        return "hook"
    if path.name == "SKILL.md" and (rel.startswith(("skills/", ".codex/skills/")) or "/skills/" in rel):
        return "skill"
    if rel.startswith("rules/"):
        return "rule"
    if rel.startswith("tests/"):
        return "test"
    if rel.startswith("docs/") or rel.endswith(".md"):
        return "doc"
    if rel.startswith("scripts/"):
        return "script"
    if rel.startswith(".github/workflows/"):
        return "workflow"
    if rel.startswith((".claude/", ".codex/", ".cursor/", ".windsurf/", "manifests/")) or rel in {"AGENTS.md", "README.md", "cognitive-os.yaml"}:
        return "config"
    if rel.startswith("agents/"):
        return "agent"
    return "other"


def consumer_files(root: Path) -> list[Path]:
    found: dict[str, Path] = {}
    for pattern in CONSUMER_PATTERNS:
        for path in root.glob(pattern):
            if path.is_file() and not ignored(root, path):
                found[relpath(root, path)] = path
    return [found[key] for key in sorted(found)]


def references(text: str, target: str) -> bool:
    name = Path(target).name
    stem = Path(target).stem
    parent = Path(target).parent.name
    if name == "SKILL.md":
        return target in text or f"{parent}/SKILL.md" in text or (len(parent) > 4 and parent in text)
    return target in text or (name and name in text) or (stem and len(stem) > 4 and stem in text)


def usage_map(root: Path, targets: list[Path]) -> dict[str, list[Consumer]]:
    consumers = [(path, relpath(root, path), read_text(path)) for path in consumer_files(root)]
    output: dict[str, list[Consumer]] = {}
    for target in targets:
        target_rel = relpath(root, target)
        rows = []
        for consumer, consumer_rel, text in consumers:
            if consumer_rel == target_rel:
                continue
            if references(text, target_rel):
                rows.append(Consumer(classify_consumer(root, consumer), consumer_rel))
        output[target_rel] = sorted(rows, key=lambda item: (item.family, item.path))
    return output


def lower_text(root: Path, path: Path) -> str:
    return f"{relpath(root, path)}\n{read_text(path)}".lower()


def classify_role(root: Path, family: str, path: Path, lifecycle: dict[str, Any] | None, consumers: list[Consumer]) -> tuple[str, str, str]:
    text = lower_text(root, path)
    state = lifecycle.get("lifecycle_state") if lifecycle else None
    distribution = lifecycle.get("distribution") if lifecycle else None
    if state in {"archived", "deleted"}:
        return "archive", "lifecycle", "high"
    if distribution == "lab" or state == "sandbox" or "sandbox" in text or "experiment" in text:
        return "lab", "lifecycle" if lifecycle else "heuristic:path", "high" if lifecycle else "medium"
    if family == "hooks":
        if any(token in text for token in ("engram", "memory", "session", "compaction", "summary")):
            return "memory-lifecycle", "lifecycle" if lifecycle else "heuristic:text", "high" if lifecycle else "medium"
        if any(token in text for token in ("metric", "timing", "statusline", "telemetry", "observability")):
            return "observability", "lifecycle" if lifecycle else "heuristic:text", "high" if lifecycle else "medium"
        if any(token in text for token in ("claude", "codex", "cursor", "windsurf", "harness", "driver")):
            return "driver-specific", "lifecycle" if lifecycle else "heuristic:text", "high" if lifecycle else "medium"
        return "runtime-safety", "lifecycle" if lifecycle else "default", "high" if lifecycle else "medium"
    if family == "skills":
        if any(token in text for token in ("wrapper", "scripts/", "hooks/", "compatibility")):
            return "compatibility-wrapper", "usage:script-hook", "high"
        if lifecycle and distribution in {"core", "team"}:
            return "shared-agent-tool", "lifecycle", "high"
        if relpath(root, path).startswith("skills/auto-generated/") or "auto-generated: true" in text:
            return "lab", "heuristic:path", "medium"
        if any(token in text for token in ("maintainer", "release", "audit", "migration", "doctor")):
            return "so-maintainer", "heuristic:text", "medium"
        return "project-extension", "default", "medium"
    if family == "rules":
        if any(token in text for token in ("hook-enforced", "enforced by", "pretooluse", "posttooluse", "sessionstart", "stop hook")):
            return "hook-enforced", "heuristic:text", "medium"
        if any(token in text for token in ("claude", "codex", "cursor", "windsurf", "harness", "ide")):
            return "driver-specific", "heuristic:text", "medium"
        if any(token in text for token in ("adr", "doctrine", "architecture", "decision", "policy")):
            return "doctrine", "heuristic:text", "medium"
        return "context-only", "default", "medium"
    raise ValueError(f"unsupported family: {family}")


def consumer_accessibility(row: FamilyRow) -> tuple[str, str]:
    if row.lifecycle_id and row.distribution in {"core", "team"}:
        if row.lifecycle_state in INACTIVE_STATES:
            return "lifecycle-declared-consumer-candidate", "prove projection into a consumer project before claiming availability"
        return "projected-consumer-surface", "keep install/profile/harness proof current"
    if row.lifecycle_id:
        return "lifecycle-declared-maintainer", "keep maintainer-only unless a package/profile exports it"
    if row.family == "skills" and row.path.startswith("skills/"):
        return "repo-skill-not-projectable", "add package/profile projection metadata before assuming downstream availability"
    return "so-local-only", "do not rely on this from consumer projects unless exported through install/projection"


def next_action(row: FamilyRow) -> str:
    if row.consumer_accessibility in {"so-local-only", "repo-skill-not-projectable"}:
        return "add lifecycle/package/projection metadata or keep SO-local"
    if row.consumer_accessibility == "lifecycle-declared-consumer-candidate":
        return "prove consumer project projection per supported harness before promotion"
    if row.consumer_accessibility == "lifecycle-declared-maintainer":
        return "keep maintainer-only or add explicit export path"
    return "keep lifecycle, tests, and harness proof current"


def build_ledger(root: Path, family: str) -> list[FamilyRow]:
    targets = target_files(root, family)
    usages = usage_map(root, targets)
    lifecycle_rows = load_lifecycle(root)
    rows: list[FamilyRow] = []
    for target in targets:
        rel = relpath(root, target)
        lifecycle = lifecycle_rows.get(rel)
        consumers = usages[rel]
        role, source, confidence = classify_role(root, family, target, lifecycle, consumers)
        counts = family_counts(consumers)
        evidence = []
        if lifecycle:
            evidence.append("lifecycle")
        for key in ("skill", "hook", "rule", "script", "test", "doc", "config", "workflow"):
            if counts.get(key, 0):
                evidence.append(f"{key}_consumers:{counts[key]}")
        row = FamilyRow(
            path=rel,
            family=family,
            role=role,
            role_source=source,
            confidence=confidence,
            lifecycle_id=rel if lifecycle else None,
            lifecycle_state=lifecycle.get("lifecycle_state") if lifecycle else None,
            distribution=lifecycle.get("distribution") if lifecycle else None,
            supported_harnesses=list(lifecycle.get("supported_harnesses", [])) if lifecycle else [],
            total_consumers=len(consumers),
            consumer_families=counts,
            consumers=consumers,
            evidence=evidence,
        )
        row.consumer_accessibility, row.consumer_access_next_action = consumer_accessibility(row)
        row.next_action = next_action(row)
        rows.append(row)
    return rows


def summarize(rows: list[FamilyRow]) -> dict[str, Any]:
    roles: dict[str, int] = {}
    confidence: dict[str, int] = {}
    access: dict[str, int] = {}
    without_lifecycle = 0
    for row in rows:
        roles[row.role] = roles.get(row.role, 0) + 1
        confidence[row.confidence] = confidence.get(row.confidence, 0) + 1
        access[row.consumer_accessibility] = access.get(row.consumer_accessibility, 0) + 1
        if not row.lifecycle_id:
            without_lifecycle += 1
    return {
        "total": len(rows),
        "roles": dict(sorted(roles.items())),
        "confidence": dict(sorted(confidence.items())),
        "consumer_accessibility": dict(sorted(access.items())),
        "without_lifecycle": without_lifecycle,
        "without_consumers": sum(1 for row in rows if row.total_consumers == 0),
    }


def write_json(rows: list[FamilyRow], path: Path) -> None:
    payload = {
        "schema_version": 1,
        "target_family": rows[0].family if rows else "unknown",
        "allowed_roles": sorted(ROLES[rows[0].family]) if rows else [],
        "summary": summarize(rows),
        "items": [row_to_dict(row) for row in rows],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(rows: list[FamilyRow], path: Path) -> None:
    family = rows[0].family if rows else "unknown"
    summary = summarize(rows)
    lines = [
        f"# Primitive Readiness Ledger — {family.title()}",
        "",
        f"Total rows: {summary['total']}",
        f"Rows without lifecycle metadata: {summary['without_lifecycle']}",
        f"Consumer accessibility: {', '.join(f'{key}:{value}' for key, value in summary['consumer_accessibility'].items())}",
        "",
        "| Path | Role | Source | Confidence | Consumer Access | Lifecycle | Consumers | Next action |",
        "|---|---|---|---|---|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row.path}` | {row.role} | {row.role_source} | {row.confidence} | {row.consumer_accessibility} | {row.lifecycle_state or ''} | {row.total_consumers} | {row.next_action} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build primitive readiness ledgers for hooks, skills, or rules")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--target-family", required=True, choices=sorted(FAMILIES))
    parser.add_argument("--json-out")
    parser.add_argument("--md-out")
    parser.add_argument("--fail-without-lifecycle", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    rows = build_ledger(root, args.target_family)
    json_out = Path(args.json_out) if args.json_out else Path(f"docs/reports/primitive-readiness-ledger-{args.target_family}-latest.json")
    md_out = Path(args.md_out) if args.md_out else Path(f"docs/reports/primitive-readiness-ledger-{args.target_family}-latest.md")
    write_json(rows, root / json_out)
    write_markdown(rows, root / md_out)
    summary = summarize(rows)
    print(json.dumps({"json": str(root / json_out), "markdown": str(root / md_out), **summary}, sort_keys=True))
    if args.fail_without_lifecycle and summary["without_lifecycle"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
