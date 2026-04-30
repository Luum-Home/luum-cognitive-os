from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_RUNTIME_CONTRACT_GLOBS = ("skills/*/SKILL.md", "packages/*/skills/*/SKILL.md")
RULE_RUNTIME_CONTRACT_GLOBS = ("rules/*.md",)


def iter_paths(patterns: tuple[str, ...]) -> list[Path]:
    rows: list[Path] = []
    for pattern in patterns:
        rows.extend(path for path in PROJECT_ROOT.glob(pattern) if path.is_file())
    return sorted(rows)


def test_runtime_skill_files_are_actionable_documents() -> None:
    """Runtime-referenced skills must have enough content to be usable by an agent."""
    paths = iter_paths(SKILL_RUNTIME_CONTRACT_GLOBS)
    assert paths, "expected skill files to audit"
    failures: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if len(text.strip()) < 120:
            failures.append(f"{rel}: too short")
        if "## " not in text and "name:" not in text[:400]:
            failures.append(f"{rel}: missing heading/name")
    assert not failures


def test_runtime_rules_have_loader_metadata_or_explicit_trigger() -> None:
    """Loaded rule docs must carry tier metadata or a contextual trigger contract."""
    paths = [path for path in iter_paths(RULE_RUNTIME_CONTRACT_GLOBS) if path.name != "RULES-COMPACT.md"]
    assert paths, "expected rule files to audit"
    failures: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        has_tier = "<!-- TIER:" in text
        has_trigger = "Contextual Trigger" in text
        if not has_tier and not has_trigger:
            failures.append(f"{rel}: missing tier metadata and contextual trigger")
    assert not failures
