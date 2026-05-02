#!/usr/bin/env python3
# SCOPE: os-only
"""Map which COS agentic primitives and repo surfaces reference each primitive.

This is a static reachability map, not runtime coverage. It answers questions
like: "which skills use each Python script?" and "which scripts have no skill
consumer?" so dormant/aspirational surfaces can be promoted, wired, or archived.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Consumer:
    family: str
    path: str


@dataclass
class TargetUsage:
    family: str
    path: str
    consumers: list[Consumer] = field(default_factory=list)

    @property
    def consumer_families(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for consumer in self.consumers:
            counts[consumer.family] = counts.get(consumer.family, 0) + 1
        return dict(sorted(counts.items()))

    @property
    def skill_consumers(self) -> int:
        return self.consumer_families.get("skill", 0)

    @property
    def total_consumers(self) -> int:
        return len(self.consumers)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def repo_files(root: Path, patterns: Iterable[str]) -> list[Path]:
    files: dict[str, Path] = {}
    ignored_parts = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
    ignored_prefixes = ("docs/reports/",)
    for pattern in patterns:
        for path in root.glob(pattern):
            if not path.is_file() and not path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            if ignored_parts.intersection(path.relative_to(root).parts):
                continue
            if any(rel.startswith(prefix) for prefix in ignored_prefixes):
                continue
            files[rel] = path
    return [files[key] for key in sorted(files)]


def classify_consumer(root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix()
    name = path.name
    if name == "SKILL.md" and ("/skills/" in f"/{rel}" or rel.startswith(("skills/", ".codex/skills/"))):
        return "skill"
    if rel.startswith("hooks/") or "/hooks/" in rel:
        return "hook"
    if rel.startswith("rules/"):
        return "rule"
    if rel.startswith("agents/") or "/agents/" in rel:
        return "agent"
    if rel.startswith("tests/"):
        return "test"
    if rel.startswith("docs/") or rel.endswith(".md"):
        return "doc"
    if rel.startswith(".github/workflows/"):
        return "workflow"
    if rel.startswith((".claude/", "manifests/")) or rel in {"cognitive-os.yaml", "AGENTS.md"}:
        return "config"
    if rel.startswith("scripts/"):
        return "script"
    return "other"


def target_patterns(family: str) -> list[str]:
    if family == "scripts":
        return ["scripts/**/*.py"]
    if family == "hooks":
        return ["hooks/**/*.sh", "packages/**/hooks/**/*.sh"]
    if family == "skills":
        return ["skills/**/SKILL.md", ".codex/skills/**/SKILL.md", "packages/**/skills/**/SKILL.md"]
    if family == "rules":
        return ["rules/**/*.md"]
    raise ValueError(f"unsupported family: {family}")


def consumer_patterns() -> list[str]:
    return [
        "skills/**/SKILL.md",
        ".codex/skills/**/SKILL.md",
        "packages/**/skills/**/SKILL.md",
        "hooks/**/*.sh",
        "packages/**/hooks/**/*.sh",
        "rules/**/*.md",
        "agents/**/*",
        "docs/**/*.md",
        "tests/**/*.py",
        "scripts/**/*.py",
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        ".claude/**/*.json",
        "manifests/**/*.json",
        "cognitive-os.yaml",
        "AGENTS.md",
        "README.md",
    ]


def ref_patterns(rel_path: str) -> list[re.Pattern[str]]:
    basename = Path(rel_path).name
    stem = Path(rel_path).stem
    refs = [re.escape(rel_path)]
    if basename != rel_path:
        refs.append(rf"(?<![A-Za-z0-9_.-]){re.escape(basename)}(?![A-Za-z0-9_.-])")
    if rel_path.endswith("/SKILL.md"):
        skill_name = Path(rel_path).parent.name
        refs.append(rf"(?<![A-Za-z0-9_/-])/{re.escape(skill_name)}(?![A-Za-z0-9_/-])")
        refs.append(rf"(?<![A-Za-z0-9_.-]){re.escape(skill_name)}(?![A-Za-z0-9_.-])")
    elif rel_path.startswith("rules/") and rel_path.endswith(".md"):
        refs.append(rf"(?<![A-Za-z0-9_.-]){re.escape(stem)}(?![A-Za-z0-9_.-])")
    return [re.compile(pattern) for pattern in refs]


def references_target(text: str, rel_path: str) -> bool:
    return any(pattern.search(text) for pattern in ref_patterns(rel_path))


def build_usage(root: Path, family: str) -> list[TargetUsage]:
    targets = repo_files(root, target_patterns(family))
    consumers = repo_files(root, consumer_patterns())
    consumer_text: list[tuple[Path, str, str]] = []
    for consumer in consumers:
        rel = consumer.relative_to(root).as_posix()
        consumer_text.append((consumer, rel, read_text(consumer)))

    rows: list[TargetUsage] = []
    for target in targets:
        rel = target.relative_to(root).as_posix()
        row = TargetUsage(family=family, path=rel)
        for consumer, consumer_rel, text in consumer_text:
            if consumer_rel == rel:
                continue
            if references_target(text, rel):
                row.consumers.append(Consumer(classify_consumer(root, consumer), consumer_rel))
        row.consumers.sort(key=lambda item: (item.family, item.path))
        rows.append(row)
    rows.sort(key=lambda item: item.path)
    return rows


def summarize(rows: list[TargetUsage]) -> dict[str, object]:
    missing_skill = [row.path for row in rows if row.skill_consumers == 0]
    orphan = [row.path for row in rows if row.total_consumers == 0]
    family_totals: dict[str, int] = {}
    for row in rows:
        for family, count in row.consumer_families.items():
            family_totals[family] = family_totals.get(family, 0) + count
    return {
        "targets": len(rows),
        "without_skill_consumer": len(missing_skill),
        "without_any_consumer": len(orphan),
        "consumer_reference_totals": dict(sorted(family_totals.items())),
    }


def write_markdown(rows: list[TargetUsage], path: Path) -> None:
    summary = summarize(rows)
    lines = [
        "# Primitive Usage Map — Latest",
        "",
        f"Targets: {summary['targets']}",
        f"Targets without skill consumer: {summary['without_skill_consumer']}",
        f"Targets without any consumer: {summary['without_any_consumer']}",
        "",
        "| Target | Skill Consumers | Total Consumers | Consumer Families |",
        "|---|---:|---:|---|",
    ]
    for row in rows:
        families = ", ".join(f"{family}:{count}" for family, count in row.consumer_families.items())
        lines.append(f"| `{row.path}` | {row.skill_consumers} | {row.total_consumers} | {families} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Map primitive-to-primitive/static repo usage")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--target-family", choices=("scripts", "hooks", "skills", "rules"), default="scripts")
    parser.add_argument("--json-out", default="docs/reports/primitive-usage-map-latest.json")
    parser.add_argument("--md-out", default="docs/reports/primitive-usage-map-latest.md")
    parser.add_argument("--fail-orphans", action="store_true", help="Exit non-zero if any target has no consumer at all")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    rows = build_usage(root, args.target_family)
    summary = summarize(rows)
    payload = {
        "target_family": args.target_family,
        "summary": summary,
        "targets": [
            {
                "family": row.family,
                "path": row.path,
                "consumer_families": row.consumer_families,
                "skill_consumers": row.skill_consumers,
                "total_consumers": row.total_consumers,
                "consumers": [asdict(consumer) for consumer in row.consumers],
            }
            for row in rows
        ],
    }
    json_path = root / args.json_out
    md_path = root / args.md_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(rows, md_path)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), **summary}, sort_keys=True))
    if args.fail_orphans and summary["without_any_consumer"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
