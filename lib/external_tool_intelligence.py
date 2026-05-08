"""External-tool intelligence plane helpers.

ADR-254 keeps deep tool research in COS and lets consumer projects provide a
lightweight overlay. These helpers intentionally stay dependency-light and work
from repository-local manifests, dependency files, SBOM-like JSON, and Markdown
reports.
"""
from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ADOPTION_SCHEMA = "external-tools-adoption/v1"
OVERLAY_SCHEMA = "cos-project-tool-overlay/v1"
INVENTORY_SCHEMA = "external-tool-inventory/v1"
AUDIT_SCHEMA = "external-tool-adoption-audit/v1"
RENDER_SCHEMA = "external-tool-radar-render/v1"
RESEARCH_CHECK_SCHEMA = "external-tool-research-check/v1"

DEPENDENCY_FILES = [
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "go.mod",
    "go.sum",
]

MD_TOOL_RE = re.compile(r"`([A-Za-z0-9][A-Za-z0-9_.@/+:-]{1,80})`")
URL_RE = re.compile(r"https?://(?:www\.)?(?:github\.com/)?([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+|[A-Za-z0-9_.-]+\.[A-Za-z]{2,})(?:[/#?][^\s)]*)?")
REQ_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+(?:\[[^\]]+\])?)\s*(?:[<>=!~]=?|===|@|;|#|$)")
GO_REQUIRE_RE = re.compile(r"^\s*([A-Za-z0-9_.\-/]+\.[A-Za-z0-9_.\-/]+)\s+v")


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    tool: str | None = None
    path: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"severity": self.severity, "code": self.code, "message": self.message}
        if self.tool:
            payload["tool"] = self.tool
        if self.path:
            payload["path"] = self.path
        if self.details:
            payload["details"] = self.details
        return payload


def normalize_tool_id(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\[.*\]", "", value)
    value = value.replace("_", "-")
    value = re.sub(r"[^a-z0-9./+-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value


def _display_path(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def repo_root(start: Path) -> Path:
    cur = start.resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / ".git").exists():
            return candidate
    return cur


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _add_item(items: dict[str, dict[str, Any]], *, tool: str, source: str, path: str, confidence: str = "medium") -> None:
    tool_id = normalize_tool_id(tool)
    if not tool_id or len(tool_id) < 2:
        return
    item = items.setdefault(tool_id, {"id": tool_id, "names": sorted({tool}), "sources": [], "confidence": confidence})
    names = set(item.get("names", []))
    names.add(tool)
    item["names"] = sorted(names)
    item["sources"].append({"source": source, "path": path})
    if confidence == "high" or item.get("confidence") != "high":
        item["confidence"] = confidence if item.get("confidence") != "high" else "high"


def parse_requirements(path: Path) -> list[str]:
    out: list[str] = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        m = REQ_RE.match(stripped)
        if m:
            out.append(normalize_tool_id(m.group(1)))
    return sorted(set(out))


def parse_pyproject(path: Path) -> list[str]:
    if not path.exists():
        return []
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    deps: list[str] = []
    project = data.get("project", {})
    project_name = normalize_tool_id(str(project.get("name", "")))
    deps.extend(project.get("dependencies", []) or [])
    for values in (project.get("optional-dependencies", {}) or {}).values():
        deps.extend(values or [])
    result: list[str] = []
    for dep in deps:
        m = REQ_RE.match(str(dep))
        if m:
            dep_id = normalize_tool_id(m.group(1))
            # Self-referential extras such as "luum-cognitive-os[testing]" are
            # packaging composition, not an external tool adoption.
            if dep_id and dep_id != project_name:
                result.append(dep_id)
    return sorted(set(result))


def parse_package_json(path: Path) -> list[str]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    deps: list[str] = []
    for key in ["dependencies", "devDependencies", "peerDependencies", "optionalDependencies"]:
        deps.extend((data.get(key) or {}).keys())
    return sorted({normalize_tool_id(dep) for dep in deps})


def parse_go_mod(path: Path) -> list[str]:
    if not path.exists():
        return []
    deps: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "// indirect" in line:
            continue
        m = GO_REQUIRE_RE.match(line)
        if m:
            deps.append(normalize_tool_id(m.group(1)))
    return sorted(set(deps))


def direct_dependencies(root: Path) -> dict[str, list[str]]:
    files = {
        "requirements.txt": parse_requirements(root / "requirements.txt"),
        "pyproject.toml": parse_pyproject(root / "pyproject.toml"),
        "package.json": parse_package_json(root / "package.json"),
        "go.mod": parse_go_mod(root / "go.mod"),
    }
    return {path: deps for path, deps in files.items() if deps}


def inventory(root: Path, *, include_docs: bool = True) -> dict[str, Any]:
    items: dict[str, dict[str, Any]] = {}
    for path, deps in direct_dependencies(root).items():
        for dep in deps:
            _add_item(items, tool=dep, source="dependency", path=path, confidence="high")

    if include_docs:
        globs = ["docs/**/*.md", "manifests/**/*.yaml", "*.md"]
        seen: set[Path] = set()
        for pattern in globs:
            for path in root.glob(pattern):
                if path in seen or not path.is_file():
                    continue
                seen.add(path)
                text = path.read_text(encoding="utf-8", errors="replace")
                rel = str(path.relative_to(root))
                for m in MD_TOOL_RE.finditer(text):
                    token = m.group(1)
                    if "/" in token or token.lower() in {"fastmcp", "litellm", "langfuse", "semgrep", "mlflow", "ragas", "deepeval", "phoenix", "opik", "cognee"}:
                        _add_item(items, tool=token, source="doc-token", path=rel, confidence="medium")
                for m in URL_RE.finditer(text):
                    _add_item(items, tool=m.group(1), source="url", path=rel, confidence="medium")

    sorted_items = sorted(items.values(), key=lambda item: item["id"])
    return {
        "schema_version": INVENTORY_SCHEMA,
        "item_count": len(sorted_items),
        "items": sorted_items,
        "direct_dependencies": direct_dependencies(root),
    }


def load_adoption_manifest(path: Path) -> dict[str, Any]:
    data = read_yaml(path)
    if not data:
        return {"schema_version": ADOPTION_SCHEMA, "tools": []}
    return data


def load_overlay(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    return read_yaml(path)


def manifest_indexes(manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_package: dict[str, dict[str, Any]] = {}
    for tool in manifest.get("tools", []) or []:
        tid = normalize_tool_id(str(tool.get("id", "")))
        if not tid:
            continue
        by_id[tid] = tool
        by_package[tid] = tool
        for pkg in tool.get("package_names", []) or []:
            by_package[normalize_tool_id(str(pkg))] = tool
    return by_id, by_package


def _has_consumer_proof(tool: dict[str, Any]) -> bool:
    evidence = tool.get("evidence") or {}
    return bool(evidence.get("consumers")) and bool(evidence.get("tests"))


def audit_adoption(root: Path, manifest_path: Path, overlay_path: Path | None = None, *, strict: bool = False) -> dict[str, Any]:
    manifest = load_adoption_manifest(manifest_path)
    overlay = load_overlay(overlay_path)
    by_id, by_package = manifest_indexes(manifest)
    findings: list[Finding] = []
    deps_by_file = direct_dependencies(root)
    all_deps = sorted({dep for deps in deps_by_file.values() for dep in deps})

    for dep in all_deps:
        if dep not in by_package:
            severity = "block" if strict else "warn"
            findings.append(Finding(severity, "used-tool-not-declared", "Direct dependency is not declared in external-tools adoption manifest.", dep, details={"dependency_files": [p for p, deps in deps_by_file.items() if dep in deps]}))
            continue
        tool = by_package[dep]
        verdict = str(tool.get("verdict", "")).upper()
        status = str(tool.get("status", "")).lower()
        if verdict in {"REMOVE", "REJECT"} or status in {"cleanup_required", "removed"}:
            findings.append(Finding("block", "removed-tool-still-used", "Tool is marked REMOVE/REJECT or cleanup_required but remains in direct dependencies.", str(tool.get("id") or dep), details={"package": dep, "dependency_files": [p for p, deps in deps_by_file.items() if dep in deps], "verdict": verdict, "status": status}))

    for tid, tool in by_id.items():
        if str(tool.get("verdict", "")).upper() == "ADOPT" and not _has_consumer_proof(tool):
            findings.append(Finding("block", "adopt-without-consumer-proof", "ADOPT verdict requires both consumer and test evidence.", tid))

    waiver_ids = {normalize_tool_id(str(w.get("tool_id") or w.get("id") or "")) for w in (overlay.get("waivers", []) or [])}
    for local in overlay.get("local_tools", []) or []:
        tid = normalize_tool_id(str(local.get("id", "")))
        source = str(local.get("source", ""))
        local_status = str(local.get("local_status", "")).lower()
        if source == "os-radar" and tid and tid not in by_id and tid not in by_package:
            findings.append(Finding("block", "overlay-references-unknown-os-tool", "Project overlay references an OS radar tool that is not declared in the COS manifest.", tid))
            continue
        tool = by_id.get(tid) or by_package.get(tid)
        if tool and local_status in {"enabled", "required", "adopt"} and str(tool.get("verdict", "")).upper() in {"REMOVE", "REJECT", "DEFER"} and tid not in waiver_ids:
            findings.append(Finding("block", "overlay-contradiction-without-waiver", "Project overlay enables a tool whose COS verdict requires remove/reject/defer without a waiver.", tid, details={"cos_verdict": tool.get("verdict"), "local_status": local_status}))
        if source == "project-only" and local.get("requires_deep_research") is True and not local.get("deep_dive"):
            findings.append(Finding("warn", "project-only-tool-needs-deep-dive", "Project-only tool requests deep research but has no deep_dive pointer.", tid))

    finding_dicts = [f.to_dict() for f in findings]
    block = sum(1 for f in finding_dicts if f["severity"] == "block")
    warn = sum(1 for f in finding_dicts if f["severity"] == "warn")
    return {
        "schema_version": AUDIT_SCHEMA,
        "status": "block" if block else "warn" if warn else "pass",
        "summary": {"block": block, "warn": warn, "findings": len(finding_dicts)},
        "manifest": _display_path(manifest_path),
        "overlay": _display_path(overlay_path),
        "direct_dependencies": deps_by_file,
        "findings": finding_dicts,
    }


def render_radar(manifest_path: Path, overlay_path: Path | None, *, mode: str = "combined") -> dict[str, Any]:
    manifest = load_adoption_manifest(manifest_path)
    overlay = load_overlay(overlay_path)
    tools = manifest.get("tools", []) or []
    project_tools = overlay.get("local_tools", []) if overlay else []
    payload: dict[str, Any] = {"schema_version": RENDER_SCHEMA, "mode": mode}
    if mode in {"os-only", "combined"}:
        payload["os_tools"] = sorted(tools, key=lambda t: str(t.get("id", "")))
    if mode in {"project-only", "combined"}:
        payload["project_tools"] = sorted(project_tools, key=lambda t: str(t.get("id", "")))
    if mode == "combined":
        by_id, by_pkg = manifest_indexes(manifest)
        effective = []
        for local in project_tools:
            tid = normalize_tool_id(str(local.get("id", "")))
            base = by_id.get(tid) or by_pkg.get(tid)
            effective.append({"id": tid, "source": local.get("source"), "local_status": local.get("local_status"), "cos_verdict": base.get("verdict") if base else None, "reason": local.get("reason")})
        payload["effective_project_view"] = effective
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [f"# External Tool Radar Render — {payload.get('mode')}", ""]
    if "os_tools" in payload:
        lines += ["## OS tools", "", "| Tool | Domain | Verdict | Status |", "|---|---|---|---|"]
        for tool in payload["os_tools"]:
            lines.append(f"| {tool.get('id')} | {tool.get('domain', '')} | {tool.get('verdict', '')} | {tool.get('status', '')} |")
        lines.append("")
    if "project_tools" in payload:
        lines += ["## Project overlay tools", "", "| Tool | Source | Local status | Reason |", "|---|---|---|---|"]
        for tool in payload["project_tools"]:
            lines.append(f"| {tool.get('id')} | {tool.get('source', '')} | {tool.get('local_status', '')} | {tool.get('reason', '')} |")
        lines.append("")
    if "effective_project_view" in payload:
        lines += ["## Effective project view", "", "| Tool | Source | Local status | COS verdict |", "|---|---|---|---|"]
        for tool in payload["effective_project_view"]:
            lines.append(f"| {tool.get('id')} | {tool.get('source', '')} | {tool.get('local_status', '')} | {tool.get('cos_verdict', '')} |")
        lines.append("")
    return "\n".join(lines)


def research_check(candidate_path: Path) -> dict[str, Any]:
    data = read_yaml(candidate_path) if candidate_path.suffix.lower() in {".yaml", ".yml"} else json.loads(candidate_path.read_text(encoding="utf-8"))
    required = ["id", "license", "footprint", "adoption_kind", "source_links", "test_plan", "rollback_path"]
    findings: list[Finding] = []
    for key in required:
        value = data.get(key)
        if value in (None, "", [], {}):
            findings.append(Finding("block", "research-packet-missing-field", "Research packet is missing a required field.", str(data.get("id") or candidate_path.name), details={"field": key}))
    footprint = data.get("footprint") or {}
    for surface in ["os_repo", "consumer_projects", "service_mode", "docker_runtime"]:
        if surface not in footprint:
            findings.append(Finding("block", "research-packet-missing-footprint-surface", "Footprint must cover all COS surfaces.", str(data.get("id") or candidate_path.name), details={"surface": surface}))
    finding_dicts = [f.to_dict() for f in findings]
    return {
        "schema_version": RESEARCH_CHECK_SCHEMA,
        "status": "block" if finding_dicts else "pass",
        "candidate": str(candidate_path),
        "summary": {"block": len(finding_dicts), "warn": 0, "findings": len(finding_dicts)},
        "findings": finding_dicts,
    }


def markdown_inventory(payload: dict[str, Any]) -> str:
    lines = ["# External Tool Inventory", "", f"Items: {payload.get('item_count', 0)}", "", "| Tool | Confidence | Sources |", "|---|---|---|"]
    for item in payload.get("items", []):
        sources = ", ".join(sorted({src.get("path", "") for src in item.get("sources", [])})[:5])
        lines.append(f"| {item.get('id')} | {item.get('confidence')} | {sources} |")
    lines.append("")
    return "\n".join(lines)
