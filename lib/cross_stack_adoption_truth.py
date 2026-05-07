"""ADR-217 cross-stack adoption-truth audit substrate."""
from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "cross-stack-adoption-truth-report/v1"
DEFAULT_MANIFEST = Path("manifests/cross-stack-adoption-truth.yaml")


@dataclass(frozen=True)
class DependencyRow:
    name: str
    sources: list[str]
    in_lockfile: bool = False
    in_notice: bool = False
    component_status: str | None = None
    inventory_bucket: str | None = None
    adoption_verdict: str = "NOT_APPLICABLE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "sources": sorted(set(self.sources)),
            "in_lockfile": self.in_lockfile,
            "in_notice": self.in_notice,
            "component_sources_status": self.component_status,
            "inventory_bucket": self.inventory_bucket,
            "adoption_verdict": self.adoption_verdict,
        }


def load_manifest(project_dir: Path) -> dict[str, Any]:
    path = project_dir / DEFAULT_MANIFEST
    if not path.exists():
        raise FileNotFoundError(f"adoption-truth manifest missing: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def normalize_name(name: str) -> str:
    value = name.strip().lower()
    value = re.sub(r"^[\"']|[\"']$", "", value)
    value = re.sub(r"\[.*\]$", "", value)
    value = value.replace("_", "-")
    if "/" in value and not value.startswith("@"):
        value = value.rstrip("/").split("/")[-1]
    return value


def _glob(project_dir: Path, patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pattern in patterns:
        out.extend(path for path in project_dir.glob(pattern) if path.is_file())
    return sorted(set(out))


def _dep_name_from_requirement(requirement: str) -> str | None:
    token = re.split(r"[<>=!~;\[ ]", requirement.strip(), maxsplit=1)[0]
    return normalize_name(token) if token else None


def parse_python(project_dir: Path, patterns: list[str]) -> dict[str, list[str]]:
    deps: dict[str, list[str]] = {}
    for path in _glob(project_dir, patterns):
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        candidates: list[str] = []
        project = data.get("project") or {}
        candidates.extend(project.get("dependencies") or [])
        optional = project.get("optional-dependencies") or {}
        for values in optional.values():
            candidates.extend(values or [])
        for requirement in candidates:
            name = _dep_name_from_requirement(str(requirement))
            if name:
                deps.setdefault(name, []).append(str(path.relative_to(project_dir)))
    return deps


def parse_node(project_dir: Path, patterns: list[str]) -> dict[str, list[str]]:
    deps: dict[str, list[str]] = {}
    for path in _glob(project_dir, patterns):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for section in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
            for name in (data.get(section) or {}).keys():
                deps.setdefault(normalize_name(str(name)), []).append(str(path.relative_to(project_dir)))
    return deps


def parse_go(project_dir: Path, patterns: list[str]) -> dict[str, list[str]]:
    deps: dict[str, list[str]] = {}
    for path in _glob(project_dir, patterns):
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("//") or line in {"require (", ")"}:
                continue
            if line.startswith("require "):
                line = line.removeprefix("require ").strip()
            module = line.split()[0] if line.split() else ""
            if "." in module or "/" in module:
                deps.setdefault(normalize_name(module), []).append(str(path.relative_to(project_dir)))
    return deps


def parse_submodules(project_dir: Path, manifest_path: str | None) -> dict[str, list[str]]:
    if not manifest_path:
        return {}
    path = project_dir / manifest_path
    if not path.exists():
        return {}
    deps: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("path ="):
            name = normalize_name(stripped.split("=", 1)[1])
            deps.setdefault(name, []).append(str(path.relative_to(project_dir)))
    return deps


def parse_notice(project_dir: Path, notice_path: str | None) -> dict[str, list[str]]:
    if not notice_path:
        return {}
    path = project_dir / notice_path
    if not path.exists():
        return {}
    entries: dict[str, list[str]] = {}
    previous = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("---"):
            previous = ""
            continue
        if previous == "---" or (stripped and not stripped.startswith(("Licensed", "Copyright", "https://", "This product", "See "))):
            if len(stripped.split()) <= 4 and not any(ch in stripped for ch in ":|`[]"):
                entries.setdefault(normalize_name(stripped), []).append(str(path.relative_to(project_dir)))
        previous = stripped
    return entries


def parse_component_sources(project_dir: Path, component_path: str | None) -> dict[str, str]:
    if not component_path:
        return {}
    path = project_dir / component_path
    if not path.exists():
        return {}
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "---" in line or " Source " in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 5:
            continue
        name_cell = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cells[0]).strip()
        status = cells[4].split("--", 1)[0].strip().upper()
        if name_cell:
            rows[normalize_name(name_cell)] = status
    return rows


def parse_inventory(project_dir: Path, patterns: list[str]) -> dict[str, str]:
    buckets: dict[str, str] = {}
    for path in _glob(project_dir, patterns):
        bucket = "inventory"
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            heading = re.match(r"^#{1,4}\s+(.+)$", line)
            if heading:
                bucket = heading.group(1).strip().lower().replace(" ", "-")[:80]
            for match in re.finditer(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", line):
                buckets[normalize_name(match.group(2))] = bucket
    return buckets


def marketing_text(project_dir: Path, patterns: list[str]) -> str:
    chunks: list[str] = []
    for path in _glob(project_dir, patterns):
        chunks.append(path.read_text(encoding="utf-8", errors="ignore").lower())
    return "\n".join(chunks)


def merge_sources(*maps: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for source in maps:
        for name, paths in source.items():
            merged.setdefault(name, []).extend(paths)
    return merged


def classify(name: str, *, in_lockfile: bool, in_notice: bool, status: str | None, inventory_bucket: str | None, marketing: str, allowlists: dict[str, Any]) -> str:
    if name in set(allowlists.get("transitive_only") or []):
        return "NOT_APPLICABLE"
    if in_notice and not in_lockfile and name not in set(allowlists.get("notice_optional") or []):
        return "DEAD_IN_NOTICE"
    if in_lockfile and not status:
        return "INTEGRATED_UNTRACKED"
    if status == "PLANNED" and name in marketing:
        return "ASPIRATIONAL_PLANNED"
    if status in {"WATCH", "EVALUATED"} and re.search(rf"\b(use|uses|using|powered by|integrated with)\s+{re.escape(name)}\b", marketing):
        return "OVERCLAIMED"
    if in_lockfile and status:
        return "INTEGRATED"
    if inventory_bucket or status:
        return "ACTIVELY_TRACKED"
    return "NOT_APPLICABLE"


def build_report(project_dir: Path, *, strict: bool = False) -> dict[str, Any]:
    project = project_dir.resolve()
    manifest = load_manifest(project)
    sources = manifest.get("sources") or {}
    allowlists = manifest.get("allowlists") or {}
    lockfiles = merge_sources(
        parse_python(project, sources.get("python_pyproject_globs") or []),
        parse_node(project, sources.get("node_package_json_globs") or []),
        parse_go(project, sources.get("go_mod_globs") or []),
        parse_submodules(project, sources.get("submodule_manifest")),
    )
    notice = parse_notice(project, sources.get("notice"))
    components = parse_component_sources(project, sources.get("component_sources"))
    inventory = parse_inventory(project, sources.get("external_inventory_globs") or [])
    marketing = marketing_text(project, sources.get("marketing_doc_globs") or [])
    names = sorted(set(lockfiles) | set(notice) | set(components) | set(inventory))
    rows: list[dict[str, Any]] = []
    for name in names:
        verdict = classify(
            name,
            in_lockfile=name in lockfiles,
            in_notice=name in notice,
            status=components.get(name),
            inventory_bucket=inventory.get(name),
            marketing=marketing,
            allowlists=allowlists,
        )
        rows.append(
            DependencyRow(
                name=name,
                sources=[*lockfiles.get(name, []), *notice.get(name, [])],
                in_lockfile=name in lockfiles,
                in_notice=name in notice,
                component_status=components.get(name),
                inventory_bucket=inventory.get(name),
                adoption_verdict=verdict,
            ).to_dict()
        )
    strict_verdicts = set(manifest.get("strict_block_verdicts") or [])
    findings = [row for row in rows if row["adoption_verdict"] in strict_verdicts or row["adoption_verdict"] == "INTEGRATED_UNTRACKED"]
    blocking = [row for row in rows if row["adoption_verdict"] in strict_verdicts]
    status = "block" if strict and blocking else "warn" if findings else "pass"
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["adoption_verdict"]] = counts.get(row["adoption_verdict"], 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "project_dir": str(project),
        "status": status,
        "strict": strict,
        "summary": {"rows": len(rows), "findings": len(findings), "blocking_findings": len(blocking), "verdict_counts": counts},
        "findings": findings,
        "rows": rows,
    }


def dumps_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)
