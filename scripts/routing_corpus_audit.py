#!/usr/bin/env python3
# SCOPE: os-only
"""Audit multilingual routing benchmark corpus coverage.

This is a structural guard: it does not claim semantic correctness. It verifies
that the benchmark corpus is large enough, spans enough skills/languages, uses
catalogued skills, and makes uncovered user-facing skill surfaces visible.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from lib.routing_benchmark import LANGUAGES, load_corpus, load_skill_catalog


@dataclass(frozen=True)
class CorpusIssue:
    code: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class CorpusCoverageReport:
    root: str
    corpus_path: str
    corpus_skills: int
    corpus_prompts: int
    candidate_skills: int
    languages_with_prompts: list[str]
    prompts_by_language: dict[str, int]
    issue_count: int
    issues: list[CorpusIssue] = field(default_factory=list)
    uncovered_user_facing_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _frontmatter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return {}
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _skill_files(root: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for base_name in ("skills", "packages"):
        base = root / base_name
        if not base.exists():
            continue
        for path in sorted(base.rglob("SKILL.md")):
            out.setdefault(path.parent.name, path)
    return out


def _user_facing_skills(root: Path) -> list[str]:
    out: list[str] = []
    for name, path in _skill_files(root).items():
        meta = _frontmatter(path)
        user_invocable = bool(
            meta.get("user-invocable")
            or meta.get("user_invocable")
            or meta.get("user_invokable")
        )
        triggers = meta.get("triggers") or meta.get("routing_patterns") or []
        audience = str(meta.get("audience") or "").strip().lower()
        if user_invocable or triggers or audience in {"project", "both", "os-dev"}:
            out.append(name)
    return sorted(set(out))


def audit_corpus(
    root: Path,
    corpus_path: Path,
    *,
    min_skills: int,
    min_prompts: int,
    min_languages: int,
    min_prompts_per_language: int,
    max_uncovered_user_facing: int | None,
) -> CorpusCoverageReport:
    root = root.resolve()
    corpus_path = corpus_path if corpus_path.is_absolute() else root / corpus_path
    corpus = load_corpus(corpus_path)
    catalog = load_skill_catalog(root / "skills", root / "packages")
    user_facing = _user_facing_skills(root)

    prompts_by_language = {
        lang: sum(len(entry["prompts"].get(lang, [])) for entry in corpus.values())
        for lang in LANGUAGES
    }
    corpus_prompts = sum(prompts_by_language.values())
    languages_with_prompts = [lang for lang, count in prompts_by_language.items() if count]
    issues: list[CorpusIssue] = []

    if len(corpus) < min_skills:
        issues.append(
            CorpusIssue(
                "too-few-corpus-skills",
                f"Corpus covers {len(corpus)} skills; minimum is {min_skills}.",
            )
        )
    if corpus_prompts < min_prompts:
        issues.append(
            CorpusIssue(
                "too-few-corpus-prompts",
                f"Corpus has {corpus_prompts} prompts; minimum is {min_prompts}.",
            )
        )
    if len(languages_with_prompts) < min_languages:
        issues.append(
            CorpusIssue(
                "too-few-languages",
                f"Corpus has prompts for {len(languages_with_prompts)} languages; minimum is {min_languages}.",
            )
        )
    for lang, count in prompts_by_language.items():
        if count < min_prompts_per_language:
            issues.append(
                CorpusIssue(
                    "too-few-language-prompts",
                    f"Language {lang} has {count} prompts; minimum is {min_prompts_per_language}.",
                    severity="warning" if min_prompts_per_language == 0 else "error",
                )
            )

    missing_catalog = sorted(set(corpus) - set(catalog))
    for skill in missing_catalog:
        issues.append(
            CorpusIssue(
                "corpus-skill-not-in-catalog",
                f"Corpus skill {skill!r} is not present in the on-disk skill catalog.",
            )
        )

    uncovered = sorted(set(user_facing) - set(corpus))
    if max_uncovered_user_facing is not None and len(uncovered) > max_uncovered_user_facing:
        issues.append(
            CorpusIssue(
                "too-many-uncovered-user-facing-skills",
                f"{len(uncovered)} user-facing skills have no corpus prompt; maximum is {max_uncovered_user_facing}.",
            )
        )

    error_count = sum(1 for issue in issues if issue.severity == "error")
    return CorpusCoverageReport(
        root=str(root),
        corpus_path=str(corpus_path),
        corpus_skills=len(corpus),
        corpus_prompts=corpus_prompts,
        candidate_skills=len(catalog),
        languages_with_prompts=languages_with_prompts,
        prompts_by_language=prompts_by_language,
        issue_count=error_count,
        issues=issues,
        uncovered_user_facing_skills=uncovered,
    )


def render_markdown(report: CorpusCoverageReport, *, uncovered_limit: int) -> str:
    lines = [
        "# Routing Corpus Coverage Audit",
        "",
        f"- Root: `{report.root}`",
        f"- Corpus: `{report.corpus_path}`",
        f"- Corpus skills: {report.corpus_skills}",
        f"- Corpus prompts: {report.corpus_prompts}",
        f"- Catalog candidates: {report.candidate_skills}",
        f"- Languages with prompts: {', '.join(report.languages_with_prompts) or '_none_'}",
        "",
        "## Prompts by Language",
        "",
        "| language | prompts |",
        "| --- | ---: |",
    ]
    for lang, count in report.prompts_by_language.items():
        lines.append(f"| {lang} | {count} |")
    lines.extend(["", "## Issues", "", "| severity | code | message |", "| --- | --- | --- |"])
    if report.issues:
        for issue in report.issues:
            lines.append(f"| {issue.severity} | {issue.code} | {issue.message} |")
    else:
        lines.append("| _none_ |  |  |")
    lines.extend(["", "## Uncovered User-Facing Skills", ""])
    if report.uncovered_user_facing_skills:
        for skill in report.uncovered_user_facing_skills[:uncovered_limit]:
            lines.append(f"- `{skill}`")
        remaining = len(report.uncovered_user_facing_skills) - uncovered_limit
        if remaining > 0:
            lines.append(f"- ... {remaining} more omitted")
    else:
        lines.append("_None._")
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit routing benchmark corpus coverage.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--corpus", default="manifests/routing-benchmark-corpus-multilingual.yaml")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-issues", action="store_true")
    parser.add_argument("--min-skills", type=int, default=5)
    parser.add_argument("--min-prompts", type=int, default=8)
    parser.add_argument("--min-languages", type=int, default=4)
    parser.add_argument("--min-prompts-per-language", type=int, default=0)
    parser.add_argument("--max-uncovered-user-facing", type=int, default=None)
    parser.add_argument("--uncovered-limit", type=int, default=50)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = audit_corpus(
        Path(args.root),
        Path(args.corpus),
        min_skills=args.min_skills,
        min_prompts=args.min_prompts,
        min_languages=args.min_languages,
        min_prompts_per_language=args.min_prompts_per_language,
        max_uncovered_user_facing=args.max_uncovered_user_facing,
    )
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(render_markdown(report, uncovered_limit=args.uncovered_limit))
    return 1 if args.fail_on_issues and report.issue_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
