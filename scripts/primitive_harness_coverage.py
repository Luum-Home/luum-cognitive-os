#!/usr/bin/env python3
# SCOPE: both
"""Report per-harness implementation coverage for Cognitive OS primitives.

Scope classification (`os-only`, `project`, `both`) declares intended audience.
This report measures a different axis: whether each primitive is actually
projected, wired, executable, and behavior-proven for each harness/IDE surface.
"""
from __future__ import annotations

import argparse
import json
import re
import stat
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.project_paths import relpath
from lib.script_io import read_text

VALID_SCOPES = {"os-only", "project", "both"}
FAMILIES = {"hooks", "skills", "rules", "scripts", "templates"}
HOOK_EVENTS = {"SessionStart", "UserPromptSubmit", "SubagentStart", "PreCompact", "PreToolUse", "PostToolUse", "Stop", "TeammateIdle", "TaskCreated", "TaskCompleted"}
SCRIPT_SUFFIXES = {"", ".py", ".sh", ".js", ".mjs", ".txt"}
IGNORE_PARTS = {"__pycache__", ".pytest_cache", ".venv", "node_modules", ".git"}
IGNORE_PREFIXES = ("docs/reports/", ".claude/plugins/", "dashboard/.next/")
DEFAULT_HARNESSES = ("claude", "codex", "shell-ci")


@dataclass(frozen=True)
class HarnessState:
    installed: bool = False
    projected: bool = False
    wired: bool = False
    executable: bool = False
    behavior_proven: bool = False
    events: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CoverageRow:
    primitive: str
    family: str
    scope: str | None
    harnesses: dict[str, HarnessState]
    coverage: str
    gap: str | None


def _ignored(root: Path, path: Path) -> bool:
    rel = relpath(root, path)
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return bool(IGNORE_PARTS.intersection(parts)) or any(rel.startswith(prefix) for prefix in IGNORE_PREFIXES)


def _scope(path: Path) -> str | None:
    header = "\n".join(read_text(path).splitlines()[:8])
    match = re.search(r"\bSCOPE:\s*([A-Za-z0-9_-]+)", header)
    return match.group(1) if match else None


def _primitive_files(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in (root / "hooks").rglob("*.sh") if (root / "hooks").exists() else []:
        if path.is_file() and not _ignored(root, path):
            out[relpath(root, path)] = "hooks"
    skill_roots = [root / "skills", root / ".codex" / "skills"]
    for base in skill_roots:
        if base.exists():
            for path in base.rglob("SKILL.md"):
                if path.is_file() and not _ignored(root, path):
                    out[relpath(root, path)] = "skills"
    for path in (root / "rules").rglob("*.md") if (root / "rules").exists() else []:
        if path.is_file() and not _ignored(root, path):
            out[relpath(root, path)] = "rules"
    for path in (root / "scripts").rglob("*") if (root / "scripts").exists() else []:
        if path.is_file() and path.suffix in SCRIPT_SUFFIXES and not _ignored(root, path):
            out[relpath(root, path)] = "scripts"
    for path in (root / "templates").rglob("*.md") if (root / "templates").exists() else []:
        if path.is_file() and not _ignored(root, path):
            out[relpath(root, path)] = "templates"
    return dict(sorted(out.items()))


def _extract_hook_ref(command: str) -> str | None:
    matches = re.findall(r"hooks/[A-Za-z0-9_./-]+\.sh", command)
    if not matches:
        return None
    return matches[-1]


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _claude_wiring(root: Path) -> dict[str, dict[str, list[str]]]:
    data = _load_json(root / ".claude" / "settings.json") or {}
    hooks = data.get("hooks") or {}
    wiring: dict[str, dict[str, list[str]]] = {}
    for event, entries in hooks.items():
        for entry in entries if isinstance(entries, list) else []:
            for hook in entry.get("hooks", []) if isinstance(entry, dict) else []:
                command = str(hook.get("command", ""))
                ref = _extract_hook_ref(command)
                if ref:
                    wiring.setdefault(ref, {"events": [], "commands": []})
                    wiring[ref]["events"].append(str(event))
                    wiring[ref]["commands"].append(command)
    return wiring


def _codex_wiring(root: Path) -> dict[str, dict[str, list[str]]]:
    data = _load_json(root / ".codex" / "hooks.json") or {}
    wiring: dict[str, dict[str, list[str]]] = {}
    for event, entries in data.items() if isinstance(data, dict) else []:
        for entry in entries if isinstance(entries, list) else []:
            for hook in entry.get("hooks", []) if isinstance(entry, dict) else []:
                command = str(hook.get("command", ""))
                ref = _extract_hook_ref(command)
                if ref:
                    wiring.setdefault(ref, {"events": [], "commands": []})
                    wiring[ref]["events"].append(str(event))
                    wiring[ref]["commands"].append(command)
    return wiring


def _shell_ci_projection(root: Path) -> dict[str, dict[str, list[str]]]:
    projected: dict[str, dict[str, list[str]]] = {}
    runtime = _load_json(root / ".cognitive-os" / "shell-ci-projection.json")
    if runtime:
        for item in runtime.get("projected", []):
            source = item.get("source")
            if source:
                projected.setdefault(str(source), {"commands": [], "events": []})
                projected[str(source)]["commands"].append(str(item.get("driver_path") or source))
        return projected
    manifest = root / "manifests" / "shell-ci-projection.yaml"
    if manifest.exists():
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
            rows = data.get("commands") or data.get("scripts") or []
            for item in rows:
                source = item.get("path") if isinstance(item, dict) else str(item)
                if source:
                    projected.setdefault(str(source), {"commands": [], "events": []})
                    projected[str(source)]["commands"].append(str(source))
        except Exception:
            for match in re.findall(r"scripts/[A-Za-z0-9_./-]+\.(?:py|sh)|scripts/cos\b", manifest.read_text(encoding="utf-8", errors="replace")):
                projected.setdefault(match, {"commands": [], "events": []})
                projected[match]["commands"].append(match)
    return projected


def _test_index(root: Path) -> str:
    chunks: list[str] = []
    for base in (root / "tests", root / "docs" / "manual-tests"):
        if base.exists():
            for path in base.rglob("*"):
                if path.is_file() and path.suffix in {".py", ".md", ".bats", ".sh"}:
                    chunks.append(relpath(root, path) + "\n" + read_text(path))
    return "\n".join(chunks)


def _behavior_proven(test_text: str, primitive: str) -> bool:
    path = Path(primitive)
    candidates = {primitive, path.name}
    if path.name == "SKILL.md":
        candidates.add(path.parent.name)
        candidates.add(str(path.parent))
    if len(path.stem) > 4:
        candidates.add(path.stem)
    return any(candidate and candidate in test_text for candidate in candidates)


def _is_executable(root: Path, primitive: str) -> bool:
    path = root / primitive
    if not path.exists():
        return False
    if primitive.endswith((".sh", ".py")) or primitive.startswith("hooks/") or primitive.startswith("scripts/"):
        try:
            mode = path.stat().st_mode
        except OSError:
            return False
        if mode & stat.S_IXUSR:
            return True
        first = read_text(path).splitlines()[:1]
        return bool(first and first[0].startswith("#!"))
    return False


def _structural_projected(family: str, scope: str | None, harness: str) -> bool:
    if scope == "os-only":
        return False
    if family in {"skills", "rules"} and harness in {"claude", "codex"}:
        return True
    return False


def _state_for(root: Path, primitive: str, family: str, scope: str | None, harness: str, wiring: dict[str, dict[str, list[str]]], test_text: str) -> HarnessState:
    wire = wiring.get(primitive)
    structurally_projected = _structural_projected(family, scope, harness)
    installed = (root / primitive).exists()
    projected = bool(wire) or structurally_projected
    wired = bool(wire and wire.get("events"))
    executable = _is_executable(root, primitive)
    behavior = _behavior_proven(test_text, primitive)
    evidence: list[str] = []
    if wire:
        evidence.append("settings-wiring")
    if structurally_projected:
        evidence.append("structural-skill-rule-projection")
    if behavior:
        evidence.append("test-or-manual-reference")
    return HarnessState(
        installed=installed,
        projected=projected,
        wired=wired,
        executable=executable,
        behavior_proven=behavior,
        events=sorted(set(wire.get("events", []))) if wire else [],
        commands=wire.get("commands", []) if wire else [],
        evidence=evidence,
    )


def _coverage_and_gap(scope: str | None, family: str, harnesses: dict[str, HarnessState]) -> tuple[str, str | None]:
    implemented = sorted(name for name, state in harnesses.items() if state.projected or state.wired)
    behavior = sorted(name for name, state in harnesses.items() if state.behavior_proven and (state.projected or state.wired))
    coverage = "+".join(implemented) if implemented else "none"
    if scope == "both":
        missing = [name for name in ("claude", "codex") if name in harnesses and not (harnesses[name].projected or harnesses[name].wired)]
        if missing:
            return coverage, f"scope=both but missing projected/wired support for: {', '.join(missing)}"
        weak = [name for name in ("claude", "codex") if name in harnesses and family == "hooks" and not harnesses[name].wired]
        if weak:
            return coverage, f"scope=both hook lacks runtime wiring for: {', '.join(weak)}"
    if scope == "project" and not implemented:
        return coverage, "scope=project but no harness projection detected"
    if implemented and not behavior:
        return coverage, "projected/wired but no direct behavior proof reference detected"
    return coverage, None


def build_report(root: Path, harnesses: tuple[str, ...] = DEFAULT_HARNESSES) -> dict[str, Any]:
    primitives = _primitive_files(root)
    wiring_by_harness: dict[str, dict[str, dict[str, list[str]]]] = {
        "claude": _claude_wiring(root),
        "codex": _codex_wiring(root),
        "shell-ci": _shell_ci_projection(root),
    }
    test_text = _test_index(root)
    rows: list[CoverageRow] = []
    for primitive, family in primitives.items():
        scope = _scope(root / primitive)
        states = {
            harness: _state_for(root, primitive, family, scope, harness, wiring_by_harness.get(harness, {}), test_text)
            for harness in harnesses
        }
        coverage, gap = _coverage_and_gap(scope, family, states)
        rows.append(CoverageRow(primitive=primitive, family=family, scope=scope, harnesses=states, coverage=coverage, gap=gap))
    summary = {
        "total_primitives": len(rows),
        "by_family": {},
        "by_scope": {},
        "gaps": sum(1 for row in rows if row.gap),
        "harness_projected_or_wired": {h: sum(1 for row in rows if row.harnesses[h].projected or row.harnesses[h].wired) for h in harnesses},
        "harness_wired_hooks": {h: sum(1 for row in rows if row.family == "hooks" and row.harnesses[h].wired) for h in harnesses},
    }
    for row in rows:
        summary["by_family"][row.family] = summary["by_family"].get(row.family, 0) + 1
        summary["by_scope"][str(row.scope)] = summary["by_scope"].get(str(row.scope), 0) + 1
    return {
        "schema_version": "primitive-harness-coverage.v1",
        "purpose": "Measure effective harness/IDE implementation coverage separately from scope intent.",
        "state_semantics": ["installed", "projected", "wired", "executable", "behavior-proven"],
        "harnesses": list(harnesses),
        "summary": summary,
        "items": [_row_to_dict(row) for row in rows],
    }


def _row_to_dict(row: CoverageRow) -> dict[str, Any]:
    data = asdict(row)
    data["harnesses"] = {name: asdict(state) for name, state in row.harnesses.items()}
    return data


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Primitive Harness Coverage",
        "",
        "Scope declares intent; harness coverage proves effective implementation per IDE/harness.",
        "",
        f"Total primitives: {report['summary']['total_primitives']}",
        f"Gaps: {report['summary']['gaps']}",
        f"Projected/wired by harness: {report['summary']['harness_projected_or_wired']}",
        f"Wired hooks by harness: {report['summary']['harness_wired_hooks']}",
        "",
        "| Primitive | Family | Scope | Coverage | Gap | Claude | Codex | Shell CI |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in report["items"]:
        h = row["harnesses"]
        def cell(name: str) -> str:
            state = h.get(name, {})
            bits = []
            if state.get("wired"):
                bits.append("wired:" + ",".join(state.get("events") or []))
            elif state.get("projected"):
                bits.append("projected")
            elif state.get("installed"):
                bits.append("installed")
            else:
                bits.append("absent")
            if state.get("behavior_proven"):
                bits.append("proven")
            return "<br>".join(bits)
        lines.append(
            f"| `{row['primitive']}` | {row['family']} | {row.get('scope') or ''} | {row['coverage']} | {row.get('gap') or ''} | {cell('claude')} | {cell('codex')} | {cell('shell-ci')} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build primitive harness/IDE implementation coverage report")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--json-out", default="docs/reports/primitive-harness-coverage-latest.json")
    parser.add_argument("--md-out", default="docs/reports/primitive-harness-coverage-latest.md")
    parser.add_argument("--print-json", action="store_true")
    parser.add_argument("--fail-gaps", action="store_true", help="Exit non-zero if any gap is detected")
    args = parser.parse_args()
    root = Path(args.project_dir).resolve()
    report = build_report(root)
    json_path = root / args.json_out
    md_path = root / args.md_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(report, md_path)
    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps({"json": str(json_path), "markdown": str(md_path), **report["summary"]}, sort_keys=True))
    if args.fail_gaps and report["summary"]["gaps"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
