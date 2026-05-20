#!/usr/bin/env python3
# SCOPE: os-only
"""Audit projected Claude hooks against lifecycle metadata and observable runtime behavior."""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SETTINGS = REPO_ROOT / ".claude" / "settings.json"
DEFAULT_MANIFEST = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"
DEFAULT_REGISTRATION_CLASSIFICATION = REPO_ROOT / "manifests" / "hook-registration-classification.yaml"
HOOK_PATH_RE = re.compile(r"hooks/[A-Za-z0-9_.-]+\.sh")
RUNTIME_PATH_RE = re.compile(
    r"(?:(?:\$PWD|\$\{PWD\}|\$CLAUDE_PROJECT_DIR|\$\{CLAUDE_PROJECT_DIR\}|\$CODEX_PROJECT_DIR|\$\{CODEX_PROJECT_DIR\}|\$COGNITIVE_OS_PROJECT_DIR|\$\{COGNITIVE_OS_PROJECT_DIR(?::-[^}]*)?\})/)?"
    r"(?P<path>(?:\.cognitive-os/(?:hooks|scripts)/cos|hooks|scripts)/[A-Za-z0-9_./-]+\.(?:sh|py))"
)
EXIT_2_RE = re.compile(r"(?:^|[;&|({\s])(?:exit|return)\s+(?:2|\$\?)(?:\s|[;&|)}]|$)")
METRICS_RE = re.compile(
    r"(safe-jsonl|\.jsonl\b|/metrics/|\.cognitive-os/metrics|record[_-]?metric|emit[_-]?metric|metrics)",
    re.IGNORECASE,
)
NATIVE_BLOCK_RE = re.compile(
    r"(permissionDecision|decision)\s*:\s*[\"']block[\"']|[\"'](permissionDecision|decision)[\"']\s*:\s*[\"']block[\"']",
    re.IGNORECASE,
)
BLOCKING_LABELS = {"blocking", "default-on", "enforcing"}
INACTIVE_STATES = {"demoted", "archived", "deleted"}
CATEGORIES = (
    "real_blocking",
    "real_advisory",
    "observe_only",
    "dormant",
    "projected_but_undocumented",
    "documented_but_not_projected",
)


class RuntimeHookRealityError(ValueError):
    """Raised when the runtime hook reality audit cannot be built."""


@dataclass(frozen=True)
class ProjectedHook:
    path: str
    events: tuple[str, ...]
    async_projected: bool
    commands: tuple[str, ...]


@dataclass(frozen=True)
class DocumentedHook:
    path: str
    maturity: str
    lifecycle_state: str
    risk_class: str
    runtime_projection: bool
    behavior_evidence: str
    evidence_commands: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeSignals:
    hook_exists: bool
    exit2_observable: bool
    native_block_observable: bool
    metrics_or_jsonl_observable: bool


@dataclass(frozen=True)
class ClassifiedHook:
    path: str
    category: str
    projected_events: list[str] = field(default_factory=list)
    async_projected: bool = False
    maturity: str | None = None
    lifecycle_state: str | None = None
    risk_class: str | None = None
    runtime_projection: bool | None = None
    hook_exists: bool | None = None
    exit2_observable: bool | None = None
    native_block_observable: bool | None = None
    metrics_or_jsonl_observable: bool | None = None
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HookCommand:
    event: str
    command: str
    async_projected: bool = False


@dataclass(frozen=True)
class RuntimeDependencyReference:
    reference: str
    resolved_path: str
    source: str
    event: str
    command: str
    exists: bool
    scope: str | None
    allowed_by_scope: bool
    required: bool
    reason: str


def _load_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeHookRealityError(f"missing Claude settings: {path}") from exc
    except OSError as exc:
        raise RuntimeHookRealityError(f"cannot read Claude settings: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeHookRealityError(f"invalid Claude settings JSON: {exc}") from exc
    if not isinstance(loaded, dict):
        raise RuntimeHookRealityError("Claude settings root must be a mapping")
    return loaded


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeHookRealityError(f"missing primitive lifecycle manifest: {path}") from exc
    except OSError as exc:
        raise RuntimeHookRealityError(f"cannot read primitive lifecycle manifest: {exc}") from exc
    except yaml.YAMLError as exc:
        raise RuntimeHookRealityError(f"invalid primitive lifecycle manifest YAML: {exc}") from exc
    if not isinstance(loaded, dict):
        raise RuntimeHookRealityError("primitive lifecycle manifest root must be a mapping")
    return loaded


def _load_registration_classification(root: Path) -> dict[str, str]:
    path = root / "manifests" / "hook-registration-classification.yaml"
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    entries = loaded.get("entries")
    if not isinstance(entries, list):
        return {}
    out: dict[str, str] = {}
    for entry in entries:
        if isinstance(entry, dict) and entry.get("path"):
            out[str(entry["path"])] = str(entry.get("status") or "classified")
    return out


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _hooks_mapping_from_settings(settings: dict[str, Any]) -> dict[str, Any]:
    hooks_by_event = settings.get("hooks")
    if isinstance(hooks_by_event, dict):
        return hooks_by_event
    # Codex hooks.json uses lifecycle events at the top level.
    return {key: value for key, value in settings.items() if isinstance(value, list)}


def iter_hook_commands(settings_path: Path) -> list[HookCommand]:
    """Return all hook commands from Claude settings.json or Codex hooks.json."""
    settings = _load_json(settings_path)
    hooks_by_event = _hooks_mapping_from_settings(settings)
    if not isinstance(hooks_by_event, dict):
        raise RuntimeHookRealityError("settings driver must contain hook event mappings")

    commands: list[HookCommand] = []
    for event_name in sorted(hooks_by_event):
        matchers = hooks_by_event[event_name]
        if not isinstance(matchers, list):
            continue
        for matcher in matchers:
            if not isinstance(matcher, dict):
                continue
            hook_defs = matcher.get("hooks")
            if not isinstance(hook_defs, list):
                continue
            for hook_def in hook_defs:
                if not isinstance(hook_def, dict):
                    continue
                command = hook_def.get("command")
                if isinstance(command, str):
                    commands.append(HookCommand(str(event_name), command, bool(hook_def.get("async"))))
    return commands


def _scope_from_header(path: Path) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[:3]
    except OSError:
        return None
    for line in lines:
        match = re.search(r"(?:# SCOPE:|<!-- SCOPE:)\s+([A-Za-z_/-]+)", line)
        if match:
            return match.group(1).strip()
    return None


def _scope_allowed(scope: str | None, install_scope: str) -> bool:
    if install_scope == "all":
        return True
    if scope == "os-only":
        return False
    return True


def extract_runtime_paths(text: str) -> list[str]:
    """Extract project-relative runtime executable paths from text."""
    paths: list[str] = []
    for match in RUNTIME_PATH_RE.finditer(text):
        candidate = match.group("path").rstrip('"\'`),;')
        if candidate not in paths:
            paths.append(candidate)
    return paths


def _line_reference_required(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    if re.match(r"^(echo|printf|jq)\b", stripped):
        return False
    if "additionalContext" in stripped or "hookSpecificOutput" in stripped:
        return False
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=", stripped):
        return False
    if "[ -x" in stripped or "[ -f" in stripped or "test -x" in stripped or "test -f" in stripped:
        return False
    if "|| true" in stripped or "2>/dev/null" in stripped or "&" == stripped[-1:]:
        return False
    return True


def iter_runtime_path_mentions(text: str) -> list[tuple[str, bool]]:
    mentions: list[tuple[str, bool]] = []
    for line in text.splitlines():
        required = _line_reference_required(line)
        for reference in extract_runtime_paths(line):
            item = (reference, required)
            if item not in mentions:
                mentions.append(item)
    return mentions


def _resolve_runtime_path(project_root: Path, reference: str) -> Path:
    return (project_root / reference).resolve()


def _dependency_reference(
    project_root: Path,
    *,
    reference: str,
    source: str,
    event: str,
    command: str,
    install_scope: str,
    required: bool = True,
) -> RuntimeDependencyReference:
    resolved = _resolve_runtime_path(project_root, reference)
    exists = resolved.exists()
    scope = _scope_from_header(resolved) if exists else None
    allowed = exists and _scope_allowed(scope, install_scope)
    optional_prefix = "optional " if not required else ""
    if not exists:
        reason = f"{optional_prefix}referenced runtime path is not installed"
    elif not allowed:
        reason = f"{optional_prefix}referenced runtime path has SCOPE {scope!r}, disallowed for install scope {install_scope!r}"
    else:
        reason = f"{optional_prefix}referenced runtime path exists and is scope-allowed"
    return RuntimeDependencyReference(
        reference=reference,
        resolved_path=str(resolved),
        source=source,
        event=event,
        command=command,
        exists=exists,
        scope=scope,
        allowed_by_scope=allowed,
        required=required,
        reason=reason,
    )


def build_dependency_closure_report(
    *,
    project_root: Path,
    settings_path: Path,
    install_scope: str = "project",
) -> dict[str, Any]:
    """Audit runtime path closure for generated hook drivers.

    This intentionally does not require the COS source manifest: it can run
    against a consumer project install and verifies that every project-relative
    path referenced by the active hook driver exists and is allowed by the
    requested install scope. Hook bodies are scanned one level deeper for
    project scripts they invoke at runtime.
    """
    root = project_root.resolve()
    references: dict[tuple[str, str], RuntimeDependencyReference] = {}
    for hook_command in iter_hook_commands(settings_path):
        for reference in extract_runtime_paths(hook_command.command):
            ref = _dependency_reference(
                root,
                reference=reference,
                source="driver",
                event=hook_command.event,
                command=hook_command.command,
                install_scope=install_scope,
            )
            references[(ref.source, ref.reference)] = ref
            resolved = Path(ref.resolved_path)
            if ref.exists and reference.endswith(".sh") and ("/hooks/" in f"/{reference}" or reference.startswith("hooks/")):
                try:
                    body = resolved.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    body = ""
                dispatcher_graceful_optional = Path(reference).name == "bash-hot-path-dispatcher.sh"
                for nested, required in iter_runtime_path_mentions(_strip_shell_comments(body)):
                    # Hook-local libraries are covered by the copied _lib directory
                    # and usually appear as $HOOK_DIR/_lib, not project-root paths.
                    # The Bash hot-path dispatcher intentionally degrades when a
                    # conditional child gate is absent: _run_gate checks [ -x ]/[ -f ]
                    # and returns 0 for missing gates. The active driver dependency
                    # is the dispatcher itself; nested dispatcher candidates are
                    # optional unless projected by the selected install profile.
                    nested_ref = _dependency_reference(
                        root,
                        reference=nested,
                        source=reference,
                        event=hook_command.event,
                        command=hook_command.command,
                        install_scope=install_scope,
                        required=False if dispatcher_graceful_optional else required,
                    )
                    references[(nested_ref.source, nested_ref.reference)] = nested_ref

    rows = [asdict(ref) for ref in sorted(references.values(), key=lambda item: (item.source, item.reference))]
    findings: list[dict[str, Any]] = []
    for ref in references.values():
        if not ref.required:
            continue
        if not ref.exists:
            findings.append({
                "id": "runtime-reference-missing",
                "severity": "fail",
                "reference": ref.reference,
                "source": ref.source,
                "event": ref.event,
                "required": ref.required,
                "reason": ref.reason,
            })
        elif not ref.allowed_by_scope:
            findings.append({
                "id": "runtime-reference-scope-disallowed",
                "severity": "fail",
                "reference": ref.reference,
                "source": ref.source,
                "event": ref.event,
                "required": ref.required,
                "scope": ref.scope,
                "reason": ref.reason,
            })

    return {
        "schema_version": "runtime-dependency-closure.v1",
        "sources": {"settings": str(settings_path), "project_root": str(root)},
        "summary": {
            "status": "fail" if any(item["severity"] == "fail" for item in findings) else "pass",
            "install_scope": install_scope,
            "runtime_references": len(rows),
            "optional_runtime_references": sum(1 for ref in references.values() if not ref.required),
            "findings": len(findings),
        },
        "findings": sorted(findings, key=lambda item: (item["id"], item["source"], item["reference"])),
        "references": rows,
    }


def load_projected_hooks(settings_path: Path) -> dict[str, ProjectedHook]:
    settings = _load_json(settings_path)
    hooks_by_event = _hooks_mapping_from_settings(settings)
    if not isinstance(hooks_by_event, dict):
        raise RuntimeHookRealityError("settings driver must contain hook event mappings")

    events_by_path: dict[str, set[str]] = {}
    commands_by_path: dict[str, set[str]] = {}
    async_by_path: dict[str, bool] = {}
    for event_name in sorted(hooks_by_event):
        matchers = hooks_by_event[event_name]
        if not isinstance(matchers, list):
            continue
        for matcher in matchers:
            if not isinstance(matcher, dict):
                continue
            hook_defs = matcher.get("hooks")
            if not isinstance(hook_defs, list):
                continue
            for hook_def in hook_defs:
                if not isinstance(hook_def, dict):
                    continue
                command = hook_def.get("command")
                if not isinstance(command, str):
                    continue
                for hook_path in HOOK_PATH_RE.findall(command):
                    events_by_path.setdefault(hook_path, set()).add(str(event_name))
                    commands_by_path.setdefault(hook_path, set()).add(command)
                    async_by_path[hook_path] = bool(async_by_path.get(hook_path) or hook_def.get("async"))

    projected = {
        path: ProjectedHook(
            path=path,
            events=tuple(sorted(events_by_path[path])),
            async_projected=async_by_path.get(path, False),
            commands=tuple(sorted(commands_by_path.get(path, set()))),
        )
        for path in sorted(events_by_path)
    }
    root = settings_path.resolve().parents[1]
    dispatcher = projected.get("hooks/bash-hot-path-dispatcher.sh")
    dispatcher_path = root / "hooks" / "bash-hot-path-dispatcher.sh"
    if dispatcher and dispatcher_path.exists():
        text = dispatcher_path.read_text(encoding="utf-8", errors="ignore")
        for child in sorted(set(HOOK_PATH_RE.findall(text))):
            if child == dispatcher.path:
                continue
            projected.setdefault(
                child,
                ProjectedHook(
                    path=child,
                    events=dispatcher.events,
                    async_projected=dispatcher.async_projected,
                    commands=tuple(f"{command} -> {child}" for command in dispatcher.commands),
                ),
            )
    return projected


def load_documented_hooks(manifest_path: Path) -> dict[str, DocumentedHook]:
    manifest = _load_yaml(manifest_path)
    primitives = manifest.get("primitives")
    if not isinstance(primitives, list):
        raise RuntimeHookRealityError("primitive lifecycle manifest must contain a primitives list")

    documented: dict[str, DocumentedHook] = {}
    for primitive in primitives:
        if not isinstance(primitive, dict) or primitive.get("kind") != "hook":
            continue
        primitive_id = primitive.get("id")
        if not isinstance(primitive_id, str):
            continue
        match = HOOK_PATH_RE.search(primitive_id)
        if not match:
            continue
        path = match.group(0)
        documented[path] = DocumentedHook(
            path=path,
            maturity=str(primitive.get("maturity") or "unknown"),
            lifecycle_state=str(primitive.get("lifecycle_state") or "unknown"),
            risk_class=str(primitive.get("risk_class") or "unknown"),
            runtime_projection=bool(primitive.get("runtime_projection")),
            behavior_evidence=str(primitive.get("behavior_evidence") or ""),
            evidence_commands=_string_tuple(primitive.get("evidence_commands")),
        )
    return dict(sorted(documented.items()))


def _strip_shell_comments(text: str) -> str:
    stripped: list[str] = []
    for line in text.splitlines():
        trimmed = line.lstrip()
        if trimmed.startswith("#"):
            continue
        stripped.append(line.split("#", 1)[0])
    return "\n".join(stripped)


def runtime_signals(root: Path, hook_path: str) -> RuntimeSignals:
    absolute = root / hook_path
    if not absolute.exists():
        return RuntimeSignals(hook_exists=False, exit2_observable=False, native_block_observable=False, metrics_or_jsonl_observable=False)
    text = absolute.read_text(encoding="utf-8", errors="ignore")
    executable_text = _strip_shell_comments(text)
    return RuntimeSignals(
        hook_exists=True,
        exit2_observable=bool(EXIT_2_RE.search(executable_text)),
        native_block_observable=bool(NATIVE_BLOCK_RE.search(executable_text)),
        metrics_or_jsonl_observable=bool(METRICS_RE.search(executable_text)),
    )


def _claims_blocking(documented: DocumentedHook) -> bool:
    labels = {documented.maturity, documented.lifecycle_state, documented.risk_class}
    return bool(labels & BLOCKING_LABELS)


def classify_hook(
    root: Path,
    path: str,
    projected: ProjectedHook | None,
    documented: DocumentedHook | None,
) -> ClassifiedHook:
    reasons: list[str] = []
    signals: RuntimeSignals | None = None
    category: str

    if projected is None and documented is not None:
        if documented.runtime_projection and documented.lifecycle_state not in INACTIVE_STATES:
            category = "documented_but_not_projected"
            reasons.append("manifest claims runtime projection but hook is absent from .claude/settings.json")
        else:
            category = "dormant"
            reasons.append("hook is documented but not currently projected at runtime")
        return ClassifiedHook(
            path=path,
            category=category,
            maturity=documented.maturity,
            lifecycle_state=documented.lifecycle_state,
            risk_class=documented.risk_class,
            runtime_projection=documented.runtime_projection,
            reasons=reasons,
        )

    if projected is not None and documented is None:
        signals = runtime_signals(root, path)
        return ClassifiedHook(
            path=path,
            category="projected_but_undocumented",
            projected_events=list(projected.events),
            async_projected=projected.async_projected,
            hook_exists=signals.hook_exists,
            exit2_observable=signals.exit2_observable,
            native_block_observable=signals.native_block_observable,
            metrics_or_jsonl_observable=signals.metrics_or_jsonl_observable,
            reasons=["hook is projected by .claude/settings.json but absent from primitive lifecycle metadata"],
        )

    if projected is None or documented is None:
        raise RuntimeHookRealityError(f"internal classification error for {path}")

    signals = runtime_signals(root, path)
    if _claims_blocking(documented):
        if signals.exit2_observable or signals.native_block_observable:
            category = "real_blocking"
            reasons.append("blocking metadata is backed by an observable legacy exit 2 or native block path")
        else:
            category = "observe_only"
            reasons.append("blocking metadata is not backed by an observable legacy exit 2 or native block path")
    elif signals.metrics_or_jsonl_observable:
        category = "real_advisory"
        reasons.append("non-blocking hook has observable metrics/jsonl behavior")
    else:
        category = "observe_only"
        reasons.append("non-blocking hook has no observable metrics/jsonl behavior")

    if not signals.hook_exists:
        reasons.append("hook file does not exist on disk")

    return ClassifiedHook(
        path=path,
        category=category,
        projected_events=list(projected.events),
        async_projected=projected.async_projected,
        maturity=documented.maturity,
        lifecycle_state=documented.lifecycle_state,
        risk_class=documented.risk_class,
        runtime_projection=documented.runtime_projection,
        hook_exists=signals.hook_exists,
        exit2_observable=signals.exit2_observable,
        native_block_observable=signals.native_block_observable,
        metrics_or_jsonl_observable=signals.metrics_or_jsonl_observable,
        reasons=reasons,
    )


def build_report(
    *,
    project_root: Path = REPO_ROOT,
    settings_path: Path = DEFAULT_SETTINGS,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    root = project_root.resolve()
    projected = load_projected_hooks(settings_path)
    documented = load_documented_hooks(manifest_path)
    classified_absence = _load_registration_classification(root)
    all_paths = sorted(set(projected) | set(documented))
    classified = [classify_hook(root, path, projected.get(path), documented.get(path)) for path in all_paths]

    by_category = {category: [] for category in CATEGORIES}
    for hook in classified:
        by_category[hook.category].append(asdict(hook))
    counts = {category: len(by_category[category]) for category in CATEGORIES}

    findings: list[dict[str, Any]] = []
    for hook in classified:
        if hook.category == "projected_but_undocumented":
            findings.append({"id": "projected-hook-undocumented", "severity": "fail", "hook": hook.path})
        elif hook.category == "documented_but_not_projected":
            severity = "warn" if hook.path in classified_absence else "fail"
            findings.append({
                "id": "documented-hook-not-projected",
                "severity": severity,
                "hook": hook.path,
                "classification": classified_absence.get(hook.path),
            })
        elif hook.lifecycle_state not in INACTIVE_STATES and hook.maturity in BLOCKING_LABELS and not (hook.exit2_observable or hook.native_block_observable):
            findings.append({"id": "blocking-hook-without-exit2", "severity": "fail", "hook": hook.path})
        elif hook.hook_exists is False:
            findings.append({"id": "hook-file-missing", "severity": "fail", "hook": hook.path})

    return {
        "schema_version": 1,
        "sources": {
            "settings": str(settings_path),
            "manifest": str(manifest_path),
        },
        "summary": {
            "status": "fail" if any(item["severity"] == "fail" for item in findings) else "pass",
            "projected_unique_hooks": len(projected),
            "documented_hooks": len(documented),
            "audited_hooks": len(classified),
            "counts": counts,
        },
        "findings": findings,
        "hooks_by_category": by_category,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--dependency-closure", action="store_true", help="audit hook driver runtime path closure instead of lifecycle reality")
    parser.add_argument("--install-scope", choices=("project", "both", "all"), default="project", help="scope filter expected for dependency closure")
    parser.add_argument("--fail-on-findings", action="store_true", help="exit 1 when audit findings are present")
    args = parser.parse_args(argv)

    try:
        if args.dependency_closure:
            report = build_dependency_closure_report(
                project_root=args.project_root,
                settings_path=args.settings,
                install_scope=args.install_scope,
            )
        else:
            report = build_report(project_root=args.project_root, settings_path=args.settings, manifest_path=args.manifest)
    except RuntimeHookRealityError as exc:
        print(f"runtime-hook-reality: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2, sort_keys=True))
    if args.fail_on_findings and report["summary"]["status"] == "fail":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
