#!/usr/bin/env python3
# SCOPE: os-only
"""Build a machine-readable readiness ledger for script surfaces.

The ledger classifies every automation file under scripts/ as one of the
approved primitive-readiness roles. It is deliberately evidence-first: lifecycle
metadata, usage references, tests, wrapper relationships, and name/path signals
are emitted with the role so future agents can promote, demote, or archive rows
without re-discovering the surface from scratch.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_IGNORE_PARTS = {"__pycache__", ".pytest_cache", ".venv", "node_modules"}
REPO_IGNORE_PREFIXES = ("docs/reports/", ".claude/plugins/", "dashboard/.next/")
SCRIPT_SUFFIXES = {".py", ".sh", ".js", ".mjs", ".txt", ""}
ROLES = {
    "agentic-primitive",
    "maintainer-tool",
    "migration-only",
    "driver-specific",
    "lab",
    "archive",
}
SELF_EVOLUTION_PATTERNS = (
    "primitive",
    "self_improvement",
    "self-improvement",
    "doctrine",
    "demotion",
    "lifecycle",
    "readiness",
)
DRIVER_PATTERNS = (
    "settings-driver",
    "claude",
    "codex",
    "cursor",
    "windsurf",
    "harness",
    "opencode",
    "antigravity",
    "aider",
    "kiro",
)
MIGRATION_PATTERNS = (
    "backfill",
    "migrate",
    "migration",
    "reserve",
    "regen",
    "align",
    "cleanup",
    "repair_legacy",
)
LAB_PATTERNS = (
    "chaos/",
    "benchmark",
    "bench",
    "experiment",
    "prototype",
    "sample",
    "sandbox",
)


@dataclass(frozen=True)
class Consumer:
    family: str
    path: str


@dataclass
class ScriptRow:
    path: str
    role: str
    role_source: str
    confidence: str
    lifecycle_id: str | None = None
    lifecycle_state: str | None = None
    distribution: str | None = None
    supported_harnesses: list[str] = field(default_factory=list)
    wrapper_for: str | None = None
    override_rationale: str | None = None
    protected_install_surface: bool = False
    install_surface: str | None = None
    install_surface_rationale: str | None = None
    consumer_accessibility: str = "so-local-only"
    consumer_access_next_action: str = ""
    skill_consumers: int = 0
    total_consumers: int = 0
    consumer_families: dict[str, int] = field(default_factory=dict)
    consumers: list[Consumer] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    next_action: str = ""


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def relpath(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def script_files(root: Path) -> list[Path]:
    scripts = root / "scripts"
    files: list[Path] = []
    if not scripts.exists():
        return files
    for path in scripts.rglob("*"):
        if not path.is_file() and not path.is_symlink():
            continue
        rel_parts = path.relative_to(root).parts
        if REPO_IGNORE_PARTS.intersection(rel_parts):
            continue
        rel = relpath(root, path)
        if any(rel.startswith(prefix) for prefix in REPO_IGNORE_PREFIXES):
            continue
        if path.suffix in SCRIPT_SUFFIXES:
            files.append(path)
    return sorted(files, key=lambda item: relpath(root, item))


def consumer_files(root: Path) -> list[Path]:
    patterns = [
        "skills/**/SKILL.md",
        ".codex/skills/**/SKILL.md",
        "packages/**/skills/**/SKILL.md",
        "hooks/**/*.sh",
        "packages/**/hooks/**/*.sh",
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
        "cognitive-os.yaml",
        "AGENTS.md",
        "README.md",
    ]
    found: dict[str, Path] = {}
    for pattern in patterns:
        for path in root.glob(pattern):
            if not path.is_file() and not path.is_symlink():
                continue
            rel = relpath(root, path)
            if REPO_IGNORE_PARTS.intersection(path.relative_to(root).parts):
                continue
            if any(rel.startswith(prefix) for prefix in REPO_IGNORE_PREFIXES):
                continue
            found[rel] = path
    return [found[key] for key in sorted(found)]


def classify_consumer(root: Path, path: Path) -> str:
    rel = relpath(root, path)
    if path.name == "SKILL.md" and (rel.startswith(("skills/", ".codex/skills/")) or "/skills/" in rel):
        return "skill"
    if rel.startswith("hooks/") or "/hooks/" in rel:
        return "hook"
    if rel.startswith("rules/"):
        return "rule"
    if rel.startswith("tests/"):
        return "test"
    if rel.startswith("docs/") or rel.endswith(".md"):
        return "doc"
    if rel.startswith(".github/workflows/"):
        return "workflow"
    if rel.startswith("scripts/"):
        return "script"
    if rel.startswith((".claude/", ".codex/", ".cursor/", ".windsurf/", "manifests/")) or rel in {
        "cognitive-os.yaml",
        "AGENTS.md",
    }:
        return "config"
    if rel.startswith("agents/") or "/agents/" in rel:
        return "agent"
    return "other"


def references(text: str, target: str) -> bool:
    basename = Path(target).name
    if target in text:
        return True
    if basename and basename != target and basename in text:
        return True
    return False


def build_usage(root: Path, targets: list[Path]) -> dict[str, list[Consumer]]:
    consumers = [(path, relpath(root, path), read_text(path)) for path in consumer_files(root)]
    usage: dict[str, list[Consumer]] = {}
    for target in targets:
        target_rel = relpath(root, target)
        rows: list[Consumer] = []
        for consumer, consumer_rel, text in consumers:
            if consumer_rel == target_rel:
                continue
            if references(text, target_rel):
                rows.append(Consumer(classify_consumer(root, consumer), consumer_rel))
        rows.sort(key=lambda item: (item.family, item.path))
        usage[target_rel] = rows
    return usage


def load_lifecycle(root: Path) -> dict[str, dict[str, Any]]:
    manifest = root / "manifests" / "primitive-lifecycle.yaml"
    if not manifest.exists():
        return {}
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    rows = {}
    for primitive in data.get("primitives", []):
        pid = primitive.get("id")
        if isinstance(pid, str):
            rows[pid] = primitive
    return rows


def load_overrides(root: Path, path: str | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    override_path = root / path
    if not override_path.exists():
        return {}
    data = yaml.safe_load(override_path.read_text(encoding="utf-8")) or {}
    overrides: dict[str, dict[str, Any]] = {}
    for item in data.get("scripts", []):
        if "path" not in item:
            continue
        role = item.get("role")
        if role and role not in ROLES:
            raise ValueError(f"invalid override role for {item['path']}: {role}")
        overrides[str(item["path"])] = item
    return overrides


def load_protected_install_surfaces(root: Path, path: str | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    manifest = root / path
    if not manifest.exists():
        return {}
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    return {str(item["path"]): item for item in data.get("scripts", []) if "path" in item}


def wrapper_target(root: Path, path: Path) -> str | None:
    text = read_text(path)
    matches = re.findall(r"scripts/[A-Za-z0-9_./-]+\.(?:py|sh|js|mjs)", text)
    for match in matches:
        if match != relpath(root, path) and (root / match).exists():
            return match
    return None


def family_counts(consumers: list[Consumer]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for consumer in consumers:
        counts[consumer.family] = counts.get(consumer.family, 0) + 1
    return dict(sorted(counts.items()))


def has_any(rel: str, patterns: tuple[str, ...]) -> bool:
    lowered = rel.lower()
    return any(pattern in lowered for pattern in patterns)


def classify_role(rel: str, lifecycle: dict[str, Any] | None, override: dict[str, Any] | None, consumers: list[Consumer], wrapper: str | None) -> tuple[str, str, str]:
    if override and override.get("role"):
        return str(override["role"]), "override", "high"

    if lifecycle:
        distribution = lifecycle.get("distribution")
        if distribution == "lab" or lifecycle.get("lifecycle_state") == "sandbox":
            return "lab", "lifecycle", "high"
        if lifecycle.get("kind") in {"script", "doctor"}:
            return "agentic-primitive", "lifecycle", "high"

    if rel.startswith("scripts/_lib/") or has_any(rel, DRIVER_PATTERNS) and "harness_parity" not in rel.replace("-", "_"):
        return "driver-specific", "heuristic:path", "medium"
    if has_any(rel, MIGRATION_PATTERNS):
        return "migration-only", "heuristic:path", "medium"
    if has_any(rel, LAB_PATTERNS):
        return "lab", "heuristic:path", "medium"

    counts = family_counts(consumers)
    if counts.get("skill", 0) > 0:
        return "agentic-primitive", "usage:skill", "high"
    if wrapper and wrapper.startswith("scripts/cos"):
        return "agentic-primitive", "wrapper", "medium"
    if rel.startswith("scripts/cos-") or rel.startswith("scripts/cos_") or has_any(rel, SELF_EVOLUTION_PATTERNS):
        return "maintainer-tool", "heuristic:self-evolution", "medium"
    if counts.get("test", 0) > 0 or counts.get("workflow", 0) > 0 or counts.get("hook", 0) > 0:
        return "maintainer-tool", "usage:repo", "medium"
    if counts.get("doc", 0) > 0 or counts.get("rule", 0) > 0:
        return "maintainer-tool", "usage:doc-rule", "low"
    return "maintainer-tool", "default", "low"



def consumer_accessibility_for(row: ScriptRow) -> tuple[str, str]:
    if row.protected_install_surface:
        return (
            "install-profile-managed",
            "prove generated consumer profile/harness projection before claiming project availability",
        )
    if row.lifecycle_id:
        if row.distribution in {"core", "team"}:
            return (
                "lifecycle-declared-consumer-candidate",
                "prove installation/projection into a consumer project for each supported harness",
            )
        return (
            "lifecycle-declared-maintainer",
            "keep maintainer-only unless an explicit package/profile projects it to consumers",
        )
    if row.skill_consumers > 0:
        return (
            "skill-referenced-not-projectable",
            "add lifecycle/package/projection metadata before assuming consumer access",
        )
    return (
        "so-local-only",
        "do not rely on this from consumer projects unless exported through install/projection",
    )


def next_action_for(row: ScriptRow) -> str:
    if row.protected_install_surface:
        return "profile-managed install/projection surface: review generated profiles and harness settings before demotion or archive"
    if row.role == "agentic-primitive":
        if not row.lifecycle_id:
            return "add lifecycle metadata or explicit package boundary before claiming shared-agent support"
        return "keep lifecycle evidence and supported harness declarations current"
    if row.role == "maintainer-tool":
        return "keep out of default user surface unless promoted through lifecycle metadata"
    if row.role == "migration-only":
        return "add sunset criteria and archive after retention window"
    if row.role == "driver-specific":
        return "declare supported harnesses and fallback behavior"
    if row.role == "lab":
        return "keep non-default until tests and operator value justify promotion"
    if row.role == "archive":
        return "archive-first and remove active references"
    return "classify before use"


def build_ledger(root: Path, overrides_path: str | None = None, protected_install_surfaces_path: str | None = "manifests/primitive-readiness-protected-install-surfaces.yaml") -> list[ScriptRow]:
    targets = script_files(root)
    usage = build_usage(root, targets)
    lifecycle_rows = load_lifecycle(root)
    overrides = load_overrides(root, overrides_path)
    protected_install_surfaces = load_protected_install_surfaces(root, protected_install_surfaces_path)
    rows: list[ScriptRow] = []
    for target in targets:
        rel = relpath(root, target)
        lifecycle = lifecycle_rows.get(rel)
        override = overrides.get(rel)
        consumers = usage.get(rel, [])
        wrapper = wrapper_target(root, target)
        protected = protected_install_surfaces.get(rel)
        role, source, confidence = classify_role(rel, lifecycle, override, consumers, wrapper)
        if role not in ROLES:
            role = "maintainer-tool"
            source = "invalid-override-fallback"
            confidence = "low"
        counts = family_counts(consumers)
        evidence = []
        if lifecycle:
            evidence.append("lifecycle")
        if override and override.get("rationale"):
            evidence.append("override_rationale")
        if protected:
            evidence.append(f"protected_install_surface:{protected.get('surface', 'unknown')}")
        if wrapper:
            evidence.append(f"wrapper_for:{wrapper}")
        for family in ("skill", "test", "hook", "workflow", "doc", "rule", "config", "script"):
            if counts.get(family, 0):
                evidence.append(f"{family}_consumers:{counts[family]}")
        row = ScriptRow(
            path=rel,
            role=role,
            role_source=source,
            confidence=confidence,
            lifecycle_id=rel if lifecycle else None,
            lifecycle_state=lifecycle.get("lifecycle_state") if lifecycle else None,
            distribution=lifecycle.get("distribution") if lifecycle else None,
            supported_harnesses=list(lifecycle.get("supported_harnesses", [])) if lifecycle else [],
            wrapper_for=wrapper,
            override_rationale=str(override.get("rationale")) if override and override.get("rationale") else None,
            protected_install_surface=bool(protected),
            install_surface=str(protected.get("surface")) if protected and protected.get("surface") else None,
            install_surface_rationale=str(protected.get("rationale")) if protected and protected.get("rationale") else None,
            skill_consumers=counts.get("skill", 0),
            total_consumers=len(consumers),
            consumer_families=counts,
            consumers=consumers,
            evidence=evidence,
        )
        row.consumer_accessibility, row.consumer_access_next_action = consumer_accessibility_for(row)
        row.next_action = next_action_for(row)
        rows.append(row)
    return rows


def summarize(rows: list[ScriptRow]) -> dict[str, Any]:
    by_role: dict[str, int] = {role: 0 for role in sorted(ROLES)}
    by_confidence: dict[str, int] = {}
    by_consumer_access: dict[str, int] = {}
    without_consumers = 0
    without_lifecycle = 0
    for row in rows:
        by_role[row.role] = by_role.get(row.role, 0) + 1
        by_confidence[row.confidence] = by_confidence.get(row.confidence, 0) + 1
        by_consumer_access[row.consumer_accessibility] = by_consumer_access.get(row.consumer_accessibility, 0) + 1
        if row.total_consumers == 0:
            without_consumers += 1
        if row.role == "agentic-primitive" and not row.lifecycle_id:
            without_lifecycle += 1
    return {
        "total_scripts": len(rows),
        "roles": {key: value for key, value in by_role.items() if value},
        "confidence": dict(sorted(by_confidence.items())),
        "consumer_accessibility": dict(sorted(by_consumer_access.items())),
        "without_consumers": without_consumers,
        "agentic_primitives_without_lifecycle": without_lifecycle,
        "low_confidence_rows": sum(1 for row in rows if row.confidence == "low"),
    }


def row_to_dict(row: ScriptRow) -> dict[str, Any]:
    data = asdict(row)
    data["consumers"] = [asdict(consumer) for consumer in row.consumers]
    return data


def write_json(rows: list[ScriptRow], path: Path) -> None:
    payload = {
        "schema_version": 1,
        "target_family": "scripts",
        "allowed_roles": sorted(ROLES),
        "summary": summarize(rows),
        "scripts": [row_to_dict(row) for row in rows],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(rows: list[ScriptRow], path: Path) -> None:
    summary = summarize(rows)
    lines = [
        "# Primitive Readiness Ledger — Scripts",
        "",
        f"Total scripts: {summary['total_scripts']}",
        f"Roles: {', '.join(f'{role}:{count}' for role, count in summary['roles'].items())}",
        f"Low confidence rows: {summary['low_confidence_rows']}",
        f"Agentic primitives without lifecycle metadata: {summary['agentic_primitives_without_lifecycle']}",
        "",
        "| Script | Role | Source | Confidence | Consumer Access | Lifecycle | Harnesses | Consumers | Next action |",
        "|---|---|---|---|---|---|---|---:|---|",
    ]
    for row in rows:
        lifecycle = row.lifecycle_state or ""
        harnesses = ", ".join(row.supported_harnesses)
        lines.append(
            f"| `{row.path}` | {row.role} | {row.role_source} | {row.confidence} | {row.consumer_accessibility} | {lifecycle} | {harnesses} | {row.total_consumers} | {row.next_action} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")



def lifecycle_backlog(rows: list[ScriptRow]) -> list[dict[str, Any]]:
    backlog: list[dict[str, Any]] = []
    for row in rows:
        if row.role != "agentic-primitive" or row.lifecycle_id:
            continue
        if row.protected_install_surface:
            priority = "protected"
            reason = f"profile-managed install/projection surface ({row.install_surface}) lacks lifecycle metadata"
            recommended_distribution = "core" if row.install_surface in {"bootstrap", "settings-projection", "profile-application"} else "maintainer"
        elif row.skill_consumers > 0:
            priority = "high"
            reason = "skill-facing agentic primitive lacks lifecycle metadata"
            recommended_distribution = "team"
        elif row.wrapper_for:
            priority = "medium"
            reason = "wrapper/CLI agentic primitive lacks lifecycle metadata"
            recommended_distribution = "maintainer"
        else:
            priority = "medium"
            reason = "agentic primitive classification lacks lifecycle metadata"
            recommended_distribution = "maintainer"
        backlog.append({
            "path": row.path,
            "priority": priority,
            "reason": reason,
            "role_source": row.role_source,
            "confidence": row.confidence,
            "skill_consumers": row.skill_consumers,
            "total_consumers": row.total_consumers,
            "consumer_families": row.consumer_families,
            "wrapper_for": row.wrapper_for,
            "recommended_kind": "script",
            "recommended_lifecycle_state": "candidate",
            "recommended_maturity": "advisory",
            "recommended_distribution": recommended_distribution,
            "install_surface": row.install_surface,
            "protected_install_surface": row.protected_install_surface,
            "next_action": "create ADR-126 lifecycle row or downgrade role before claiming shared/harness-portable support",
        })
    priority_order = {"protected": 0, "high": 1, "medium": 2, "low": 3}
    backlog.sort(key=lambda item: (priority_order.get(str(item["priority"]), 9), -int(item["skill_consumers"]), -int(item["total_consumers"]), str(item["path"])))
    return backlog


def write_lifecycle_backlog_json(rows: list[ScriptRow], path: Path) -> None:
    backlog = lifecycle_backlog(rows)
    payload = {
        "schema_version": 1,
        "target_family": "scripts",
        "purpose": "agentic primitives missing ADR-126 lifecycle metadata",
        "summary": {
            "total": len(backlog),
            "protected": sum(1 for item in backlog if item["priority"] == "protected"),
            "high": sum(1 for item in backlog if item["priority"] == "high"),
            "medium": sum(1 for item in backlog if item["priority"] == "medium"),
        },
        "items": backlog,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_lifecycle_backlog_markdown(rows: list[ScriptRow], path: Path) -> None:
    backlog = lifecycle_backlog(rows)
    lines = [
        "# Primitive Readiness Lifecycle Backlog — Scripts",
        "",
        f"Total agentic-primitives without lifecycle metadata: {len(backlog)}",
        "",
        "| Script | Priority | Reason | Install Surface | Skill Consumers | Total Consumers | Recommended Distribution | Next action |",
        "|---|---|---|---|---:|---:|---|---|",
    ]
    for item in backlog:
        lines.append(
            f"| `{item['path']}` | {item['priority']} | {item['reason']} | {item.get('install_surface') or ''} | {item['skill_consumers']} | {item['total_consumers']} | {item['recommended_distribution']} | {item['next_action']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build primitive readiness ledger for scripts")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--overrides", default="manifests/primitive-readiness-script-overrides.yaml")
    parser.add_argument("--protected-install-surfaces", default="manifests/primitive-readiness-protected-install-surfaces.yaml")
    parser.add_argument("--json-out", default="docs/reports/primitive-readiness-ledger-scripts-latest.json")
    parser.add_argument("--md-out", default="docs/reports/primitive-readiness-ledger-scripts-latest.md")
    parser.add_argument("--lifecycle-backlog-json-out", default="docs/reports/primitive-readiness-lifecycle-backlog-scripts-latest.json")
    parser.add_argument("--lifecycle-backlog-md-out", default="docs/reports/primitive-readiness-lifecycle-backlog-scripts-latest.md")
    parser.add_argument("--fail-low-confidence", action="store_true", help="Exit non-zero when any row has low confidence")
    parser.add_argument("--fail-agentic-without-lifecycle", action="store_true", help="Exit non-zero when an agentic primitive lacks lifecycle metadata")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    rows = build_ledger(root, args.overrides, args.protected_install_surfaces)
    json_path = root / args.json_out
    md_path = root / args.md_out
    write_json(rows, json_path)
    write_markdown(rows, md_path)
    backlog_json_path = root / args.lifecycle_backlog_json_out
    backlog_md_path = root / args.lifecycle_backlog_md_out
    write_lifecycle_backlog_json(rows, backlog_json_path)
    write_lifecycle_backlog_markdown(rows, backlog_md_path)
    summary = summarize(rows)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "lifecycle_backlog_json": str(backlog_json_path), "lifecycle_backlog_markdown": str(backlog_md_path), **summary}, sort_keys=True))
    if args.fail_low_confidence and summary["low_confidence_rows"]:
        return 1
    if args.fail_agentic_without_lifecycle and summary["agentic_primitives_without_lifecycle"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
