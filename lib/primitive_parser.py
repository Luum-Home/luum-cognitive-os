"""Normalize Cognitive OS agentic primitive files into typed contracts.

The parser is intentionally descriptive. It extracts structure, activation,
metadata, and weak semantic hints, but it does not decide final SCOPE. Scope
classification remains owned by scripts/primitive_scope_classifier.py and
ADR-314 evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

VALID_SCOPE_MARKERS = {"os-only", "project", "both"}
SCOPE_RE = re.compile(
    r"^\s*(?:<!--\s*SCOPE:\s*([A-Za-z0-9_-]+)\s*-->|[#/]{1,2}\s*SCOPE:\s*([A-Za-z0-9_-]+))\s*$",
    re.IGNORECASE | re.MULTILINE,
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
HOOK_EVENT_NAMES = (
    "SessionStart",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "SubagentStop",
    "Notification",
    "UserPromptSubmit",
    "PreCompact",
)
OPENING_RULE_SECTIONS = {"purpose", "rule", "principle", "mandate", "overview", "activation", "always active", "context"}
OS_INTERNAL_PATTERNS = (
    ".cognitive-os/",
    "cognitive-os.yaml",
    "docs/02-Decisions/",
    "docs/02-decisions/",
    "manifests/",
    "scripts/cos-",
    "ADR-",
)
PROJECT_HINT_PATTERNS = (
    "downstream project",
    "consumer project",
    "generated project",
    "target project",
)
REPO_AGNOSTIC_PATTERNS = (
    "any repo",
    "any repository",
    "repository-agnostic",
    "framework-agnostic",
    "language-agnostic",
    "code review",
    "testing discipline",
)
_STRUCTURE_SCOPE_CACHE: dict[Path, dict[str, str]] = {}


@dataclass(frozen=True)
class PrimitiveActivation:
    """Activation metadata extracted from the primitive file."""

    mode: str = "unknown"
    triggers: tuple[str, ...] = ()


@dataclass(frozen=True)
class PrimitiveContract:
    """Parsed, normalized description of an agentic primitive file."""

    path: str
    kind: str
    is_primitive: bool
    scope_marker: str | None = None
    title: str = ""
    summary: str = ""
    audience: str | None = None
    activation: PrimitiveActivation = field(default_factory=PrimitiveActivation)
    frontmatter: dict[str, Any] = field(default_factory=dict)
    sections: tuple[str, ...] = ()
    structural_findings: tuple[str, ...] = ()
    semantic_hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ParsedMarkdown:
    body: str
    frontmatter: dict[str, Any]
    frontmatter_present: bool
    frontmatter_error: str | None
    lines: tuple[str, ...]
    sections: tuple[str, ...]
    h1: str | None


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def detect_primitive_kind(path: Path, root: Path | None = None) -> str:
    """Return the primitive kind implied by a repository path."""

    rel = _rel(root or Path.cwd(), path)
    parts = rel.split("/")
    if _is_support_path(rel, path):
        return "support"
    if len(parts) >= 3 and parts[0] == "skills" and parts[-1] == "SKILL.md":
        return "skill"
    if len(parts) >= 5 and parts[0] == "packages" and parts[2] == "skills" and parts[-1] == "SKILL.md":
        return "skill"
    if len(parts) >= 4 and parts[0] == "packages" and parts[2] == "hooks" and path.is_file():
        return "hook"
    if len(parts) >= 4 and parts[0] == "packages" and parts[2] == "rules" and path.suffix in {".md", ".mdc"}:
        return "rule"
    if parts and parts[0] == "rules" and path.suffix in {".md", ".mdc"}:
        if path.name in {"RULES-COMPACT.md", "ROADMAP.md"}:
            return "rule-index"
        return "rule"
    if parts and parts[0] == "hooks" and path.is_file():
        return "hook"
    if len(parts) >= 2 and parts[0] == "scripts" and parts[1] == "_lib" and path.is_file():
        return "script-lib"
    if parts and parts[0] == "scripts" and path.is_file():
        return "script"
    if parts and parts[0] == "templates" and path.is_file():
        return "template"
    return "unknown"


def parse_primitive_file(path: Path, root: Path | None = None) -> PrimitiveContract:
    """Parse a primitive file into a normalized contract."""

    root = root or Path.cwd()
    rel = _rel(root, path)
    kind = detect_primitive_kind(path, root)
    text = path.read_text(encoding="utf-8", errors="ignore")
    parsed = _parse_markdown_like(text)
    scope_marker = _scope_marker(text, parsed.frontmatter) or _manifest_scope_marker(root, rel)
    semantic_hints = _semantic_hints(text, rel)

    if kind == "skill":
        return _parse_skill(rel, parsed, scope_marker, semantic_hints)
    if kind == "rule":
        return _parse_rule(rel, parsed, scope_marker, semantic_hints)
    if kind == "rule-index":
        return _parse_rule_index(rel, path, parsed, scope_marker, semantic_hints)
    if kind == "hook":
        return _parse_hook(rel, path, parsed, scope_marker, semantic_hints, text)
    if kind == "script-lib":
        return _parse_script_lib(rel, path, parsed, scope_marker, semantic_hints)
    if kind == "script":
        return _parse_script(rel, path, parsed, scope_marker, semantic_hints)
    if kind == "template":
        return _parse_template(rel, path, parsed, scope_marker, semantic_hints, text)
    if kind == "support":
        return PrimitiveContract(
            path=rel,
            kind="support",
            is_primitive=False,
            scope_marker=scope_marker,
            title=parsed.h1 or path.name,
            summary=_summary(parsed, fallback=path.name),
            frontmatter=parsed.frontmatter,
            sections=parsed.sections,
            semantic_hints=semantic_hints,
        )
    return PrimitiveContract(
        path=rel,
        kind="unknown",
        is_primitive=False,
        scope_marker=scope_marker,
        title=parsed.h1 or path.name,
        summary=_summary(parsed, fallback=path.name),
        frontmatter=parsed.frontmatter,
        sections=parsed.sections,
        structural_findings=("unknown-primitive-kind",),
        semantic_hints=semantic_hints,
    )


def parse_primitive_files(paths: Iterable[Path], root: Path | None = None) -> list[PrimitiveContract]:
    """Parse multiple primitive paths in deterministic path order."""

    root = root or Path.cwd()
    return [parse_primitive_file(path, root) for path in sorted(paths, key=lambda p: _rel(root, p))]


def _is_support_path(rel: str, path: Path) -> bool:
    parts = rel.split("/")
    if path.name.endswith((".bak", ".disabled")):
        return True
    if parts[:2] == ["hooks", "_archived"]:
        return True
    if parts and parts[0] == "hooks" and path.suffix == ".txt":
        return True
    if parts and parts[0] == "scripts" and path.suffix == ".txt":
        return True
    return False


def _parse_markdown_like(text: str) -> _ParsedMarkdown:
    lines = tuple(text.splitlines())
    frontmatter: dict[str, Any] = {}
    frontmatter_present = False
    frontmatter_error: str | None = None
    body = text

    if lines and lines[0].strip() == "---":
        frontmatter_present = True
        closing_index: int | None = None
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                closing_index = index
                break
        if closing_index is None:
            frontmatter_error = "frontmatter-not-closed"
        else:
            raw = "\n".join(lines[1:closing_index])
            body = "\n".join(lines[closing_index + 1 :])
            try:
                loaded = yaml.safe_load(raw) or {}
                if isinstance(loaded, dict):
                    frontmatter = loaded
                else:
                    frontmatter_error = "frontmatter-not-mapping"
            except yaml.YAMLError:
                frontmatter_error = "frontmatter-yaml-error"

    body_lines = tuple(body.splitlines())
    headings = []
    h1 = None
    for line in body_lines:
        match = HEADING_RE.match(line)
        if not match:
            continue
        title = match.group(2).strip().strip("#")
        headings.append(title)
        if match.group(1) == "#" and h1 is None:
            h1 = title

    return _ParsedMarkdown(
        body=body,
        frontmatter=frontmatter,
        frontmatter_present=frontmatter_present,
        frontmatter_error=frontmatter_error,
        lines=body_lines,
        sections=tuple(headings),
        h1=h1,
    )


def _scope_marker(text: str, frontmatter: dict[str, Any] | None = None) -> str | None:
    # Skills need YAML frontmatter at byte 0 for common SKILL.md loaders, while
    # Cognitive OS still records SCOPE as an HTML/comment marker immediately
    # after that frontmatter. Search the near-top preamble instead of only the
    # first handful of lines so valid skill metadata does not hide the marker.
    if frontmatter:
        raw = frontmatter.get("scope")
        if isinstance(raw, str):
            marker = raw.lower()
            if marker in VALID_SCOPE_MARKERS:
                return marker
    head = "\n".join(text.splitlines()[:80])
    match = SCOPE_RE.search(head)
    if not match:
        return None
    marker = next(group for group in match.groups() if group).lower()
    return marker if marker in VALID_SCOPE_MARKERS else match.group(1)


def _manifest_scope_marker(root: Path, rel: str) -> str | None:
    manifest = root / "manifests" / "primitive-structure-scopes.yaml"
    if manifest not in _STRUCTURE_SCOPE_CACHE:
        if not manifest.exists():
            _STRUCTURE_SCOPE_CACHE[manifest] = {}
        else:
            data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
            items = data.get("items") or []
            _STRUCTURE_SCOPE_CACHE[manifest] = {
                str(item["path"]): str(item["scope"]).lower()
                for item in items
                if isinstance(item, dict)
                and item.get("path")
                and str(item.get("scope", "")).lower() in VALID_SCOPE_MARKERS
            }
    return _STRUCTURE_SCOPE_CACHE[manifest].get(rel)


def _summary(parsed: _ParsedMarkdown, fallback: str = "") -> str:
    desc = parsed.frontmatter.get("description")
    if isinstance(desc, str) and desc.strip():
        return desc.strip()
    for line in parsed.body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("<!--") or stripped == "---":
            continue
        if stripped.startswith("-") or stripped.startswith("|"):
            continue
        return SENTENCE_RE.split(stripped, maxsplit=1)[0].strip()
    return fallback


def _frontmatter_triggers(frontmatter: dict[str, Any]) -> tuple[str, ...]:
    raw = frontmatter.get("triggers") or frontmatter.get("trigger")
    if isinstance(raw, str):
        return (raw,)
    if isinstance(raw, list):
        return tuple(str(item) for item in raw if str(item).strip())
    return ()


def _section_text(parsed: _ParsedMarkdown, section_name: str) -> str:
    target = section_name.strip().lower()
    lines = parsed.body.splitlines()
    capture = False
    chunk: list[str] = []
    for line in lines:
        match = HEADING_RE.match(line)
        if match:
            title = match.group(2).strip().lower()
            if capture:
                break
            capture = title == target
            continue
        if capture:
            chunk.append(line)
    return "\n".join(chunk).strip()


def _section_triggers(parsed: _ParsedMarkdown) -> tuple[str, ...]:
    for section in parsed.sections:
        if section.strip().lower() == "contextual trigger":
            text = _section_text(parsed, section)
            values: list[str] = []
            for line in text.splitlines():
                cleaned = line.strip().lstrip("-*` ").strip("` ")
                if cleaned:
                    values.append(cleaned)
            return tuple(values)
    return ()


def _parse_skill(rel: str, parsed: _ParsedMarkdown, scope_marker: str | None, semantic_hints: tuple[str, ...]) -> PrimitiveContract:
    findings: list[str] = []
    if not parsed.frontmatter_present:
        findings.append("skill-missing-yaml-frontmatter")
    if parsed.frontmatter_error:
        findings.append(parsed.frontmatter_error)
    for key in ("name", "version", "description", "triggers"):
        if key not in parsed.frontmatter:
            findings.append(f"skill-missing-frontmatter-{key}")
    triggers = _frontmatter_triggers(parsed.frontmatter) or _section_triggers(parsed)
    if not triggers:
        findings.append("skill-missing-contextual-trigger")
    title = parsed.h1 or str(parsed.frontmatter.get("name") or rel.split("/")[-2])
    audience = parsed.frontmatter.get("audience")
    return PrimitiveContract(
        path=rel,
        kind="skill",
        is_primitive=True,
        scope_marker=scope_marker,
        title=title,
        summary=_summary(parsed, fallback=title),
        audience=str(audience) if audience is not None else None,
        activation=PrimitiveActivation("contextual" if triggers else "manual", triggers),
        frontmatter=parsed.frontmatter,
        sections=parsed.sections,
        structural_findings=tuple(findings),
        semantic_hints=semantic_hints,
    )


def _parse_rule(rel: str, parsed: _ParsedMarkdown, scope_marker: str | None, semantic_hints: tuple[str, ...]) -> PrimitiveContract:
    findings: list[str] = []
    if parsed.frontmatter_error:
        findings.append(parsed.frontmatter_error)
    if scope_marker is None:
        findings.append("rule-missing-scope-marker")
    if not parsed.h1:
        findings.append("rule-missing-h1")
    lower_sections = {section.lower() for section in parsed.sections}
    if not any(section.startswith(tuple(OPENING_RULE_SECTIONS)) for section in lower_sections):
        findings.append("rule-missing-opening-section")
    triggers = _section_triggers(parsed) or _frontmatter_triggers(parsed.frontmatter)
    if "contextual trigger" not in lower_sections:
        findings.append("rule-missing-contextual-trigger")
    mode = "contextual" if triggers or "contextual trigger" in lower_sections else "unknown"
    return PrimitiveContract(
        path=rel,
        kind="rule",
        is_primitive=True,
        scope_marker=scope_marker,
        title=parsed.h1 or Path(rel).stem,
        summary=_summary(parsed, fallback=Path(rel).stem),
        audience=str(parsed.frontmatter.get("audience")) if "audience" in parsed.frontmatter else None,
        activation=PrimitiveActivation(mode, triggers),
        frontmatter=parsed.frontmatter,
        sections=parsed.sections,
        structural_findings=tuple(findings),
        semantic_hints=semantic_hints,
    )


def _parse_rule_index(rel: str, path: Path, parsed: _ParsedMarkdown, scope_marker: str | None, semantic_hints: tuple[str, ...]) -> PrimitiveContract:
    findings: list[str] = []
    if scope_marker is None:
        findings.append("rule-index-missing-scope-marker")
    return PrimitiveContract(
        path=rel,
        kind="rule-index",
        is_primitive=True,
        scope_marker=scope_marker,
        title=parsed.h1 or path.stem,
        summary=_summary(parsed, fallback=path.stem),
        audience=str(parsed.frontmatter.get("audience")) if "audience" in parsed.frontmatter else None,
        activation=PrimitiveActivation("always", (path.name,)),
        frontmatter=parsed.frontmatter,
        sections=parsed.sections,
        structural_findings=tuple(findings),
        semantic_hints=semantic_hints,
    )


def _parse_hook(rel: str, path: Path, parsed: _ParsedMarkdown, scope_marker: str | None, semantic_hints: tuple[str, ...], text: str) -> PrimitiveContract:
    findings: list[str] = []
    if scope_marker is None:
        findings.append("hook-missing-scope-marker")
    events = tuple(event for event in HOOK_EVENT_NAMES if event.lower() in text.lower() or event.lower() in path.name.lower())
    triggers = events or (path.stem,)
    title = parsed.h1 or path.name
    hints = list(semantic_hints)
    if path.is_symlink():
        hints.append("symlink-surface")
    return PrimitiveContract(
        path=rel,
        kind="hook",
        is_primitive=True,
        scope_marker=scope_marker,
        title=title,
        summary=_summary(parsed, fallback=path.name),
        audience=str(parsed.frontmatter.get("audience")) if "audience" in parsed.frontmatter else None,
        activation=PrimitiveActivation("event", triggers),
        frontmatter=parsed.frontmatter,
        sections=parsed.sections,
        structural_findings=tuple(findings),
        semantic_hints=tuple(dict.fromkeys(hints)),
    )


def _parse_script_lib(rel: str, path: Path, parsed: _ParsedMarkdown, scope_marker: str | None, semantic_hints: tuple[str, ...]) -> PrimitiveContract:
    return PrimitiveContract(
        path=rel,
        kind="script-lib",
        is_primitive=False,
        scope_marker=scope_marker,
        title=parsed.h1 or path.name,
        summary=_summary(parsed, fallback=path.name),
        audience=str(parsed.frontmatter.get("audience")) if "audience" in parsed.frontmatter else None,
        activation=PrimitiveActivation("manual", (path.name,)),
        frontmatter=parsed.frontmatter,
        sections=parsed.sections,
        semantic_hints=semantic_hints,
    )


def _parse_script(rel: str, path: Path, parsed: _ParsedMarkdown, scope_marker: str | None, semantic_hints: tuple[str, ...]) -> PrimitiveContract:
    findings: list[str] = []
    if scope_marker is None:
        findings.append("script-missing-scope-marker")
    hints = list(semantic_hints)
    if path.name.startswith("cos-") or path.stem.startswith("cos_"):
        hints.append("cos-maintainer-command-name")
    return PrimitiveContract(
        path=rel,
        kind="script",
        is_primitive=True,
        scope_marker=scope_marker,
        title=parsed.h1 or path.name,
        summary=_summary(parsed, fallback=path.name),
        audience=str(parsed.frontmatter.get("audience")) if "audience" in parsed.frontmatter else None,
        activation=PrimitiveActivation("manual", (path.name,)),
        frontmatter=parsed.frontmatter,
        sections=parsed.sections,
        structural_findings=tuple(findings),
        semantic_hints=tuple(dict.fromkeys(hints)),
    )


def _parse_template(rel: str, path: Path, parsed: _ParsedMarkdown, scope_marker: str | None, semantic_hints: tuple[str, ...], text: str) -> PrimitiveContract:
    findings: list[str] = []
    if scope_marker is None:
        findings.append("template-missing-scope-marker")
    hints = list(semantic_hints)
    if "{{" in text or "${" in text:
        hints.append("template-placeholders")
    return PrimitiveContract(
        path=rel,
        kind="template",
        is_primitive=True,
        scope_marker=scope_marker,
        title=parsed.h1 or path.name,
        summary=_summary(parsed, fallback=path.name),
        audience=str(parsed.frontmatter.get("audience")) if "audience" in parsed.frontmatter else None,
        activation=PrimitiveActivation("template", (path.name,)),
        frontmatter=parsed.frontmatter,
        sections=parsed.sections,
        structural_findings=tuple(findings),
        semantic_hints=tuple(dict.fromkeys(hints)),
    )


def _semantic_hints(text: str, rel: str) -> tuple[str, ...]:
    lowered = text.lower()
    hints: list[str] = []
    if any(pattern.lower() in lowered for pattern in OS_INTERNAL_PATTERNS):
        hints.append("os-internal-reference")
    if any(pattern in lowered for pattern in PROJECT_HINT_PATTERNS):
        hints.append("project-surface-language")
    if any(pattern in lowered for pattern in REPO_AGNOSTIC_PATTERNS):
        hints.append("repo-agnostic-language")
    if rel.startswith("packages/"):
        hints.append("package-primitive-surface")
    return tuple(dict.fromkeys(hints))
