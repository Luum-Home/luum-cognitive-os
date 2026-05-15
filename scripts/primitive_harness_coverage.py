#!/usr/bin/env python3
# SCOPE: os-only
"""Report per-harness implementation coverage for Cognitive OS primitives.

Scope classification (`os-only`, `project`, `both`) declares intended audience.
This report measures a different axis: whether each primitive is actually
projected, wired, executable, and behavior-proven for each harness/IDE surface.
"""
from __future__ import annotations

import argparse
import fnmatch
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
IGNORE_PREFIXES = ("docs/06-Daily/reports/", ".claude/plugins/", "dashboard/.next/")
DEFAULT_HARNESSES = ("claude", "codex", "shell-ci")
DEFAULT_SURFACES = ("claude", "codex", "shell-ci", "cos-cli", "acc-report", "dashboard", "tui")
STRUCTURAL_HARNESSES = {"cursor", "vscode-copilot", "opencode", "cline", "continue-dev", "kilo-code", "zed-ai", "augment-code", "goose", "aider", "qwen-code", "kimi-code", "gemini-cli", "warp", "amp-code", "jetbrains-junie", "qoder", "factory-droid"}
SURFACE_KIND_BY_ID = {
    "shell-ci": "shell-ci",
    "cos-cli": "cli",
    "acc-report": "report",
    "dashboard": "ui",
    "tui": "ui",
}
CLI_COMMANDS = {
    "scripts/cos": ["scripts/cos status --json", "scripts/cos coverage --json", "scripts/cos primitive harness-coverage --print-json"],
    "scripts/cos-status.sh": ["scripts/cos status --json"],
    "scripts/cos-coverage": ["scripts/cos coverage --json", "scripts/cos-coverage --json"],
    "scripts/cos_coverage.py": ["scripts/cos coverage --json"],
    "scripts/primitive_harness_coverage.py": ["scripts/cos primitive harness-coverage --print-json", "python3 scripts/primitive_harness_coverage.py --print-json"],
}
REPORT_SURFACES = {
    "acc-report": {
        "evidence": ["scripts/acc_pipeline.py", "docs/07-Capabilities/acc/latest.json", "docs/06-Daily/reports/primitive-harness-coverage-latest.json"],
    },
}
UI_SURFACES = {
    "dashboard": {
        "evidence": ["dashboard/lib/cos-api.ts", "dashboard/app/page.tsx"],
        "operable": False,
    },
    "tui": {
        "evidence": ["scripts/cos-tui"],
        "optional_evidence": ["tests/contracts/test_cos_tui_operable_surface_contract.py"],
        "operable": True,
        "operable_primitives": [
            "scripts/cos-tui",
            "scripts/primitive_harness_coverage.py",
            "scripts/primitive_harness_partials.py",
        ],
    },
}


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
    surface_kind: str = "ide-harness"
    surface_id: str = ""
    observable: bool = False
    operable: bool = False
    json_contract: bool = False
    exit_code_contract: bool = False


@dataclass(frozen=True)
class CoverageRow:
    primitive: str
    family: str
    scope: str | None
    harnesses: dict[str, HarnessState]
    surfaces: dict[str, HarnessState]
    coverage: str
    gap: str | None
    gap_policy: str | None = None
    gap_severity: str | None = None
    gap_status: str | None = None



def _load_yaml(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    if not path.exists():
        return {}
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _scope_overrides(root: Path) -> list[dict[str, Any]]:
    return list((_load_yaml(root, "manifests/primitive-scope-overrides.yaml").get("rules") or []))


def _scope_from_overrides(primitive: str, rules: list[dict[str, Any]]) -> str | None:
    for rule in rules:
        pattern = str(rule.get("pattern", ""))
        if pattern and fnmatch.fnmatch(primitive, pattern):
            scope = str(rule.get("scope", ""))
            if scope in VALID_SCOPES:
                return scope
    return None


def _behavior_evidence(root: Path) -> dict[str, Any]:
    data = _load_yaml(root, "manifests/primitive-behavior-evidence.yaml")
    exact = {str(item.get("primitive")): item for item in data.get("evidence", []) if item.get("primitive")}
    return {"exact": exact, "patterns": list(data.get("patterns", []) or [])}


def _implemented_harnesses(root: Path) -> tuple[str, ...]:
    data = _load_yaml(root, "manifests/harness-projection.yaml")
    ids = [str(item.get("id")) for item in data.get("harnesses", []) if item.get("status") == "implemented" and item.get("id")]
    return tuple(ids) if ids else DEFAULT_HARNESSES


def _implemented_surfaces(root: Path) -> tuple[str, ...]:
    ids = list(_implemented_harnesses(root))
    for surface_id in DEFAULT_SURFACES:
        if surface_id not in ids:
            ids.append(surface_id)
    if not (root / "dashboard").exists() and "dashboard" in ids:
        ids.remove("dashboard")
    if not (root / "scripts" / "cos-tui").exists() and "tui" in ids:
        ids.remove("tui")
    return tuple(ids)


def _surface_kind(surface_id: str) -> str:
    return SURFACE_KIND_BY_ID.get(surface_id, "ide-harness")


def _gap_policy_manifest(root: Path) -> dict[str, Any]:
    data = _load_yaml(root, "manifests/primitive-harness-gap-policy.yaml")
    policies = {str(item.get("id")): item for item in data.get("policies", []) if item.get("id")}
    return {"policies": policies, "rules": list(data.get("rules", []) or [])}

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




def _dispatcher_targets(root: Path) -> set[str]:
    text = read_text(root / "hooks" / "bash-hot-path-dispatcher.sh")
    return set(re.findall(r'"(hooks/[A-Za-z0-9_.-]+\.sh)"', text))


def _expand_dispatcher_wiring(root: Path, wiring: dict[str, dict[str, list[str]]]) -> dict[str, dict[str, list[str]]]:
    dispatcher = "hooks/bash-hot-path-dispatcher.sh"
    dispatcher_wire = wiring.get(dispatcher)
    if not dispatcher_wire:
        return wiring
    for child in sorted(_dispatcher_targets(root)):
        if child == dispatcher:
            continue
        child_wire = wiring.setdefault(child, {"events": [], "commands": []})
        for event in dispatcher_wire.get("events", []):
            if event not in child_wire["events"]:
                child_wire["events"].append(event)
        for command in dispatcher_wire.get("commands", []):
            routed = f"{command} -> {child}"
            if routed not in child_wire["commands"]:
                child_wire["commands"].append(routed)
    return wiring

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
    return _expand_dispatcher_wiring(root, wiring)


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
    return _expand_dispatcher_wiring(root, wiring)


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
    # Keep this intentionally cheap: explicit behavior mappings carry the strong
    # evidence, and filename/path references catch common direct tests without
    # loading the whole test corpus into memory.
    chunks: list[str] = []
    for base in (root / "tests", root / "docs" / "manual-tests"):
        if base.exists():
            for path in base.rglob("*"):
                if path.is_file() and path.suffix in {".py", ".md", ".bats", ".sh"}:
                    chunks.append(relpath(root, path))
    return "\n".join(chunks)


def _behavior_proven(test_text: str, primitive: str, explicit: dict[str, Any] | None = None) -> bool:
    explicit = explicit or {"exact": {}, "patterns": []}
    if primitive in explicit.get("exact", {}):
        return True
    for pattern in explicit.get("patterns", []):
        if fnmatch.fnmatch(primitive, str(pattern.get("pattern", ""))) and pattern.get("behavior_proven") is True:
            return True
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
    if family in {"skills", "rules"} and (harness in {"claude", "codex"} or harness in STRUCTURAL_HARNESSES):
        return True
    if family == "templates" and harness in STRUCTURAL_HARNESSES:
        return True
    return False


def _state_for(root: Path, primitive: str, family: str, scope: str | None, harness: str, wiring: dict[str, dict[str, list[str]]], test_text: str, explicit_evidence: dict[str, Any]) -> HarnessState:
    surface_kind = _surface_kind(harness)
    wire = wiring.get(primitive)
    structurally_projected = _structural_projected(family, scope, harness)
    installed = (root / primitive).exists()
    executable = _is_executable(root, primitive)
    behavior = _behavior_proven(test_text, primitive, explicit_evidence)
    evidence: list[str] = []
    commands: list[str] = wire.get("commands", []) if wire else []
    events: list[str] = sorted(set(wire.get("events", []))) if wire else []
    projected = bool(wire) or structurally_projected
    wired = bool(wire and wire.get("events"))
    observable = False
    operable = False
    json_contract = False
    exit_code_contract = False

    if surface_kind == "cli":
        commands = CLI_COMMANDS.get(primitive, [])
        projected = bool(commands)
        wired = False
        observable = bool(commands)
        operable = bool(commands)
        json_contract = bool(commands and any("--json" in command or "--print-json" in command for command in commands))
        exit_code_contract = bool(commands)
        if commands:
            evidence.append("cos-cli-route")
    elif surface_kind == "report":
        report = REPORT_SURFACES.get(harness, {})
        report_paths = [root / str(path) for path in report.get("evidence", [])]
        projected = bool(report_paths and all(path.exists() for path in report_paths[:1]))
        wired = projected
        observable = projected
        json_contract = projected
        exit_code_contract = projected
        if projected:
            evidence.extend(str(path) for path in report.get("evidence", []))
    elif surface_kind == "ui":
        ui = UI_SURFACES.get(harness, {})
        ui_evidence = ui.get("evidence", [])
        evidence_items = ui_evidence if isinstance(ui_evidence, list) else []
        optional_evidence = ui.get("optional_evidence", [])
        optional_items = optional_evidence if isinstance(optional_evidence, list) else []
        raw_operable_primitives = ui.get("operable_primitives", [])
        operable_primitive_items = raw_operable_primitives if isinstance(raw_operable_primitives, list) else []
        ui_paths = [root / str(path) for path in evidence_items]
        projected = bool(ui_paths and all(path.exists() for path in ui_paths))
        wired = projected
        observable = projected
        operable_primitives = set(operable_primitive_items)
        operable = bool(ui.get("operable", False)) and (not operable_primitives or primitive in operable_primitives)
        if projected:
            evidence.extend(str(path) for path in evidence_items)
            evidence.extend(str(path) for path in optional_items if (root / str(path)).exists())
    else:
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
        events=events,
        commands=commands,
        evidence=evidence,
        surface_kind=surface_kind,
        surface_id=harness,
        observable=observable,
        operable=operable,
        json_contract=json_contract,
        exit_code_contract=exit_code_contract,
    )


def _coverage_and_gap(scope: str | None, family: str, harnesses: dict[str, HarnessState]) -> tuple[str, str | None]:
    implemented = sorted(name for name, state in harnesses.items() if state.projected or state.wired)
    behavior = sorted(name for name, state in harnesses.items() if state.behavior_proven and (state.projected or state.wired))
    ide_harnesses = {name: state for name, state in harnesses.items() if state.surface_kind == "ide-harness"}
    command_or_report = any(state.surface_kind in {"cli", "shell-ci", "report", "ui"} and (state.projected or state.wired) for state in harnesses.values())
    coverage = "+".join(implemented) if implemented else "none"
    if scope == "both":
        missing = [name for name in ("claude", "codex") if name in ide_harnesses and not (ide_harnesses[name].projected or ide_harnesses[name].wired)]
        if missing:
            return coverage, f"scope=both but missing projected/wired support for: {', '.join(missing)}"
        weak = [name for name in ("claude", "codex") if name in ide_harnesses and family == "hooks" and not ide_harnesses[name].wired]
        if weak:
            return coverage, f"scope=both hook lacks runtime wiring for: {', '.join(weak)}"
    if scope == "project" and not (implemented or command_or_report):
        return coverage, "scope=project but no surface projection detected"
    if implemented and not behavior:
        return coverage, "projected/wired but no direct behavior proof reference detected"
    return coverage, None


def _policy_matches(rule: dict[str, Any], primitive: str, family: str, scope: str | None, harnesses: dict[str, HarnessState], gap: str | None) -> bool:
    if not gap:
        return False
    if rule.get("family") and rule.get("family") != family:
        return False
    if rule.get("families") and family not in set(rule.get("families") or []):
        return False
    if rule.get("scopes") and scope not in set(rule.get("scopes") or []):
        return False
    if rule.get("primitives") and primitive not in set(rule.get("primitives") or []):
        return False
    if rule.get("path_prefix") and not primitive.startswith(str(rule.get("path_prefix"))):
        return False
    missing = [name for name, state in harnesses.items() if not (state.projected or state.wired)]
    if rule.get("missing_harness") and rule.get("missing_harness") not in missing:
        return False
    if rule.get("missing_harness_any") and not (set(rule.get("missing_harness_any") or []) & set(missing)):
        return False
    if rule.get("harness") and not harnesses.get(str(rule.get("harness")), HarnessState()).projected:
        return False
    if rule.get("gap_contains") and str(rule.get("gap_contains")).lower() not in str(gap).lower():
        return False
    return True


def _classify_gap(policy_manifest: dict[str, Any], primitive: str, family: str, scope: str | None, harnesses: dict[str, HarnessState], gap: str | None) -> tuple[str | None, str | None, str | None]:
    if not gap:
        return None, None, None
    policies = policy_manifest.get("policies", {})
    for rule in policy_manifest.get("rules", []):
        if _policy_matches(rule, primitive, family, scope, harnesses, gap):
            policy_id = str(rule.get("policy"))
            policy = policies.get(policy_id, {})
            return policy_id, str(policy.get("severity", "medium")), str(policy.get("status", "partial"))
    policy = policies.get("unclassified", {})
    return "unclassified", str(policy.get("severity", "medium")), str(policy.get("status", "partial"))


def build_report(root: Path, harnesses: tuple[str, ...] | None = None) -> dict[str, Any]:
    primitives = _primitive_files(root)
    scope_rules = _scope_overrides(root)
    explicit_evidence = _behavior_evidence(root)
    policy_manifest = _gap_policy_manifest(root)
    if harnesses is None:
        harnesses = _implemented_surfaces(root)
    wiring_by_harness: dict[str, dict[str, dict[str, list[str]]]] = {
        "claude": _claude_wiring(root),
        "codex": _codex_wiring(root),
        "shell-ci": _shell_ci_projection(root),
    }
    test_text = _test_index(root)
    rows: list[CoverageRow] = []
    for primitive, family in primitives.items():
        scope = _scope(root / primitive) or _scope_from_overrides(primitive, scope_rules)
        states = {
            harness: _state_for(root, primitive, family, scope, harness, wiring_by_harness.get(harness, {}), test_text, explicit_evidence)
            for harness in harnesses
        }
        coverage, gap = _coverage_and_gap(scope, family, states)
        gap_policy, gap_severity, gap_status = _classify_gap(policy_manifest, primitive, family, scope, states, gap)
        rows.append(CoverageRow(primitive=primitive, family=family, scope=scope, harnesses=states, surfaces=states, coverage=coverage, gap=gap, gap_policy=gap_policy, gap_severity=gap_severity, gap_status=gap_status))
    summary = {
        "total_primitives": len(rows),
        "by_family": {},
        "by_scope": {},
        "gaps": sum(1 for row in rows if row.gap),
        "unclassified_gaps": sum(1 for row in rows if row.gap_policy == "unclassified"),
        "gaps_by_policy": {},
        "gaps_by_status": {},
        "harness_projected_or_wired": {h: sum(1 for row in rows if row.harnesses[h].projected or row.harnesses[h].wired) for h in harnesses},
        "harness_wired_hooks": {h: sum(1 for row in rows if row.family == "hooks" and row.harnesses[h].wired and row.harnesses[h].surface_kind == "ide-harness") for h in harnesses},
        "surface_projected_or_wired": {h: sum(1 for row in rows if row.harnesses[h].projected or row.harnesses[h].wired) for h in harnesses},
        "surfaces_by_kind": {},
    }
    for surface_id in harnesses:
        kind = _surface_kind(surface_id)
        summary["surfaces_by_kind"][kind] = summary["surfaces_by_kind"].get(kind, 0) + 1
    for row in rows:
        summary["by_family"][row.family] = summary["by_family"].get(row.family, 0) + 1
        summary["by_scope"][str(row.scope)] = summary["by_scope"].get(str(row.scope), 0) + 1
        if row.gap_policy:
            summary["gaps_by_policy"][row.gap_policy] = summary["gaps_by_policy"].get(row.gap_policy, 0) + 1
        if row.gap_status:
            summary["gaps_by_status"][row.gap_status] = summary["gaps_by_status"].get(row.gap_status, 0) + 1
    return {
        "schema_version": "primitive-harness-coverage.v1",
        "purpose": "Measure effective surface implementation coverage separately from scope intent. The legacy harnesses key is preserved for compatibility.",
        "state_semantics": ["installed", "projected", "wired", "executable", "behavior-proven", "observable", "operable", "json-contract", "exit-code-contract"],
        "surface_kinds": ["ide-harness", "cli", "shell-ci", "ui", "service", "report"],
        "surfaces": [{"surface_id": h, "surface_kind": _surface_kind(h)} for h in harnesses],
        "harnesses": list(harnesses),
        "summary": summary,
        "items": [_row_to_dict(row) for row in rows],
    }


def _row_to_dict(row: CoverageRow) -> dict[str, Any]:
    data = asdict(row)
    data["harnesses"] = {name: asdict(state) for name, state in row.harnesses.items()}
    data["surfaces"] = {name: asdict(state) for name, state in row.surfaces.items()}
    return data


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Primitive Surface Coverage",
        "",
        "Scope declares intent; surface coverage proves effective implementation per IDE, CLI, UI, CI, service, or report surface.",
        "",
        f"Total primitives: {report['summary']['total_primitives']}",
        f"Gaps: {report['summary']['gaps']}",
        f"Unclassified gaps: {report['summary'].get('unclassified_gaps', 0)}",
        f"Gaps by status: {report['summary'].get('gaps_by_status', {})}",
        f"Projected/wired by surface: {report['summary']['surface_projected_or_wired']}",
        f"Surfaces by kind: {report['summary']['surfaces_by_kind']}",
        f"Wired hooks by harness: {report['summary']['harness_wired_hooks']}",
        "",
        "| Primitive | Family | Scope | Coverage | Gap | Policy | Claude | Codex | Shell CI | COS CLI | ACC Report | Dashboard | TUI |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
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
            if state.get("observable"):
                bits.append("observable")
            if state.get("operable"):
                bits.append("operable")
            if state.get("json_contract"):
                bits.append("json")
            if state.get("exit_code_contract"):
                bits.append("exit")
            if state.get("behavior_proven"):
                bits.append("proven")
            return "<br>".join(bits)
        lines.append(
            f"| `{row['primitive']}` | {row['family']} | {row.get('scope') or ''} | {row['coverage']} | {row.get('gap') or ''} | {row.get('gap_policy') or ''} | {cell('claude')} | {cell('codex')} | {cell('shell-ci')} | {cell('cos-cli')} | {cell('acc-report')} | {cell('dashboard')} | {cell('tui')} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build primitive harness/IDE implementation coverage report")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--json-out", default="docs/06-Daily/reports/primitive-harness-coverage-latest.json")
    parser.add_argument("--md-out", default="docs/06-Daily/reports/primitive-harness-coverage-latest.md")
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
