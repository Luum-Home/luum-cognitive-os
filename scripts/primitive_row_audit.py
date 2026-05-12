#!/usr/bin/env python3
"""Row-level reality audit for COS primitive families.

This complements the family-level primitive_gap_snapshot by producing concrete
rows for hooks, skills, rules, and metric streams with wiring/test/consumer
signals. The output is intentionally heuristic but evidence-backed and stable
for CI regression review.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.script_io import read_text as read_text

EVENTS = ("SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop")


@dataclass(frozen=True)
class Row:
    family: str
    name: str
    path: str
    status: str
    severity: str
    evidence: str
    next_action: str


def repo_files(root: Path, patterns: tuple[str, ...]) -> list[Path]:
    rows: list[Path] = []
    for pattern in patterns:
        rows.extend(path for path in root.glob(pattern) if path.is_file())
    return sorted(set(rows))


def load_settings_hooks(root: Path) -> dict[str, set[str]]:
    registered: dict[str, set[str]] = {}

    def add_from_command(command: str, event: str) -> None:
        for match in re.findall(r"hooks/([A-Za-z0-9_.-]+\.sh)", command):
            registered.setdefault(match, set()).add(event)

    settings = root / ".claude" / "settings.json"
    if settings.exists():
        try:
            hooks = json.loads(settings.read_text()).get("hooks", {})
        except Exception:
            hooks = {}
        for event, entries in hooks.items():
            for entry in entries or []:
                for hook in entry.get("hooks", []) or []:
                    add_from_command(hook.get("command", ""), event)

    # Projection/configuration scripts and security profiles are not live in the
    # current session but they are intentional activation paths. Treat them as
    # projected instead of dead/test-only to avoid unsafe deletion pressure.
    projection_paths = [root / "scripts" / "apply-efficiency-profile.sh", root / "scripts" / "set-security-profile.sh"]
    projection_paths.extend(sorted((root / "templates" / "security-profiles").glob("*.json")))
    for path in projection_paths:
        if path.exists():
            for match in re.findall(r"([A-Za-z0-9_.-]+\.sh)", read_text(path)):
                registered.setdefault(match, set()).add("projected")
    return registered


def corpus_text(root: Path, globs: tuple[str, ...]) -> str:
    chunks: list[str] = []
    for path in repo_files(root, globs):
        chunks.append(path.as_posix())
        chunks.append(read_text(path))
    return "\n".join(chunks)


def metric_names(text: str) -> set[str]:
    return set(re.findall(r"[A-Za-z0-9_.-]+\.jsonl", text))


def load_demotions(root: Path) -> set[tuple[str, str]]:
    path = root / "manifests" / "reduction-demotions.json"
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    rows: set[tuple[str, str]] = set()
    for item in payload.get("demotions", []):
        if isinstance(item, dict) and item.get("family") and item.get("path"):
            rows.add((str(item["family"]), str(item["path"])))
    return rows


def classify(*, registered: bool, tested: bool, metric: bool = False, consumer: bool = False) -> tuple[str, str, str]:
    if registered and tested and (metric or consumer):
        return "proven", "low", "keep; monitor regression"
    if registered and tested:
        return "partial", "medium", "add metric/consumer proof"
    if registered and not tested:
        return "partial", "high", "add behavioral test"
    if tested and not registered:
        return "partial", "medium", "dormant but behavior-tested: activate, archive, or document optional status"
    return "aspirational", "medium", "archive, wire, or delete"


def audit_hooks(root: Path, tests: str, runtime: str, demotions: set[tuple[str, str]]) -> list[Row]:
    registered = load_settings_hooks(root)
    rows: list[Row] = []
    hooks = repo_files(root, ("hooks/*.sh", "packages/*/hooks/*.sh"))
    metrics = metric_names(runtime)
    for path in hooks:
        name = path.name
        rel_path = path.relative_to(root).as_posix()
        text = read_text(path)
        is_registered = name in registered
        projected_only = is_registered and registered.get(name) == {"projected"}
        is_tested = name in tests
        emits_metric = bool(metric_names(text) & metrics) or ".jsonl" in text
        events = ",".join(sorted(registered.get(name, set()))) or "unregistered"
        optional_package_alias = False
        if path.is_symlink():
            try:
                optional_package_alias = "packages/" in path.resolve().relative_to(root).as_posix()
            except ValueError:
                optional_package_alias = False
        if ("hooks", rel_path) in demotions:
            status, severity, action = "partial", "low", "demoted optional/dormant in manifests/reduction-demotions.json"
        elif projected_only:
            status, severity, action = "partial", "medium", "projected profile hook: activate intentionally or demote"
        elif optional_package_alias and not is_registered:
            status, severity, action = "partial", "medium", "optional package alias: document activation or remove alias"
        else:
            status, severity, action = classify(registered=is_registered, tested=is_tested, metric=emits_metric)
        rows.append(
            Row(
                family="hooks",
                name=name,
                path=rel_path,
                status=status,
                severity=severity,
                evidence=f"events={events}; tested={is_tested}; emits_metric={emits_metric}",
                next_action=action,
            )
        )
    return rows


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    data: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
    return data


def audit_skills(root: Path, tests: str, runtime: str, demotions: set[tuple[str, str]]) -> list[Row]:
    rows: list[Row] = []
    skill_contract_active = "SKILL_RUNTIME_CONTRACT_GLOBS" in tests
    for path in repo_files(root, ("skills/*/SKILL.md", "packages/*/skills/*/SKILL.md", ".codex/skills/*/SKILL.md")):
        text = read_text(path)
        fm = parse_frontmatter(text)
        rel_path = path.relative_to(root).as_posix()
        name = fm.get("name") or path.parent.name
        has_trigger = "triggers" in fm or "Contextual Trigger" in text
        is_tested = path.parent.name in tests or name in tests or (skill_contract_active and not rel_path.startswith(".codex/"))
        is_runtime = path.parent.name in runtime or name in runtime
        if ("skills", rel_path) in demotions:
            status, severity, action = "partial", "low", "demoted optional/dormant in manifests/reduction-demotions.json"
        else:
            status, severity, action = classify(registered=is_runtime or has_trigger, tested=is_tested, consumer=is_runtime)
        rows.append(
            Row(
                family="skills",
                name=name,
                path=rel_path,
                status=status,
                severity=severity,
                evidence=f"frontmatter={bool(fm)}; trigger={has_trigger}; runtime_ref={is_runtime}; tested={is_tested}",
                next_action=action,
            )
        )
    return rows


def audit_rules(root: Path, tests: str, runtime: str) -> list[Row]:
    rows: list[Row] = []
    rule_contract_active = "RULE_RUNTIME_CONTRACT_GLOBS" in tests
    compact = read_text(root / "rules" / "RULES-COMPACT.md")
    for path in repo_files(root, ("rules/*.md",)):
        text = read_text(path)
        name = path.name
        tier = re.search(r"<!--\s*TIER:\s*(\d+)\s*-->", text)
        has_trigger = "Contextual Trigger" in text
        loaded = name in compact or path.stem in compact or name in runtime
        is_tested = name in tests or path.stem in tests or rule_contract_active
        status, severity, action = classify(registered=loaded, tested=is_tested, consumer=bool(tier or has_trigger))
        rows.append(
            Row(
                family="rules",
                name=name,
                path=path.relative_to(root).as_posix(),
                status=status,
                severity=severity,
                evidence=f"tier={tier.group(1) if tier else 'missing'}; trigger={has_trigger}; loaded={loaded}; tested={is_tested}",
                next_action=action,
            )
        )
    return rows


def audit_metrics(root: Path, tests: str, runtime: str, demotions: set[tuple[str, str]]) -> list[Row]:
    rows: list[Row] = []
    metric_paths = repo_files(root, (".cognitive-os/metrics/*.jsonl", "docs/06-Daily/reports/*.jsonl"))
    mentioned = metric_names(runtime + "\n" + tests)
    for path in metric_paths:
        name = path.name
        rel_path = path.relative_to(root).as_posix()
        size = path.stat().st_size
        nonempty = size > 0
        has_consumer = name in mentioned
        if ("metrics", rel_path) in demotions:
            status, severity, action = "partial", "low", "demoted optional/dormant in manifests/reduction-demotions.json"
        elif nonempty and has_consumer:
            status, severity, action = "proven", "low", "keep; assign retention if missing"
        elif nonempty:
            status, severity, action = "partial", "medium", "find/add consumer or mark diagnostic-only"
        else:
            status, severity, action = "aspirational", "medium", "delete, wire producer, or document owner"
        rows.append(
            Row(
                family="metrics",
                name=name,
                path=rel_path,
                status=status,
                severity=severity,
                evidence=f"nonempty={nonempty}; mentioned={has_consumer}",
                next_action=action,
            )
        )
    return rows


def audit(root: Path) -> list[Row]:
    tests = corpus_text(root, ("tests/**/*.py",))
    runtime = corpus_text(root, ("hooks/**/*.sh", "scripts/**/*.py", "lib/**/*.py", ".claude/settings.json", "rules/**/*.md"))
    demotions = load_demotions(root)
    rows: list[Row] = []
    rows.extend(audit_hooks(root, tests, runtime, demotions))
    rows.extend(audit_skills(root, tests, runtime, demotions))
    rows.extend(audit_rules(root, tests, runtime))
    rows.extend(audit_metrics(root, tests, runtime, demotions))
    return rows


def summarize(rows: list[Row]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for row in rows:
        fam = summary.setdefault(row.family, {"total": 0, "proven": 0, "partial": 0, "aspirational": 0, "harmful-overhead": 0})
        fam["total"] += 1
        fam[row.status] = fam.get(row.status, 0) + 1
    return summary


def write_markdown(rows: list[Row], path: Path) -> None:
    summary = summarize(rows)
    lines = ["# Primitive Row Audit — Latest", "", "## Summary", ""]
    lines.append("| Family | Total | Proven | Partial | Aspirational | Harmful |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for family, data in sorted(summary.items()):
        lines.append(
            f"| {family} | {data.get('total', 0)} | {data.get('proven', 0)} | {data.get('partial', 0)} | "
            f"{data.get('aspirational', 0)} | {data.get('harmful-overhead', 0)} |"
        )
    lines.extend(["", "## High-Severity Rows", ""])
    lines.append("| Family | Name | Status | Evidence | Next action |")
    lines.append("|---|---|---|---|---|")
    for row in rows:
        if row.severity in {"blocker", "high"}:
            lines.append(f"| {row.family} | `{row.name}` | {row.status} | {row.evidence} | {row.next_action} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate row-level primitive audit evidence")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--json-out", default="docs/06-Daily/reports/primitive-row-audit-latest.json")
    parser.add_argument("--md-out", default="docs/06-Daily/reports/primitive-row-audit-latest.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    rows = audit(root)
    payload = {"summary": summarize(rows), "rows": [asdict(row) for row in rows]}
    json_path = root / args.json_out
    md_path = root / args.md_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(rows, md_path)
    print(json.dumps({"rows": len(rows), "json": str(json_path), "markdown": str(md_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
