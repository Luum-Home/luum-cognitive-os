# SCOPE: os-only
"""Read-only dependency coverage audit for COS installability drift.

The audit reconciles five local truth sources without installing anything:
package manifests, script command probes, the ADR-168 dependency installer
manifest, external-tool adoption policy, and dependency-lane files.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import yaml

from lib import compat_tomllib as tomllib
from lib.external_tool_intelligence import normalize_tool_id, parse_go_mod, parse_package_json, parse_pyproject, parse_requirements
from lib.manifest_loader import Manifest, ManifestError, load_manifest

SCHEMA_VERSION = "cos-deps-coverage-audit.v1"

EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
EXCLUDED_PREFIXES = (
    ".cognitive-os/external-source-cache/",
    ".cognitive-os/snapshots/",
    ".cognitive-os/transpiler-eval/",
    ".claude/plugins/",
    "dashboard/.next/",
)

# Commands that are generally provided by the shell or by baseline POSIX-ish host
# images. They may still be missing on exotic environments, but they are not COS
# install-profile debt unless a runtime contract explicitly promotes them.
PLATFORM_BUILTINS = {
    "[",
    "awk",
    "basename",
    "bash",
    "cat",
    "cd",
    "chmod",
    "cp",
    "cut",
    "date",
    "dirname",
    "echo",
    "env",
    "false",
    "find",
    "grep",
    "head",
    "ln",
    "ls",
    "mkdir",
    "mktemp",
    "mv",
    "printf",
    "pwd",
    "rm",
    "sed",
    "sh",
    "sleep",
    "sort",
    "tail",
    "test",
    "tr",
    "true",
    "uname",
    "wc",
    "which",
    "xargs",
    "zsh",
}

# Helpers commonly exposed by sourced COS shell libraries. These should not be
# treated as external CLIs when a command probe checks for them defensively.
KNOWN_INTERNAL_HELPERS = {
    "cache_hit",
    "cache_update",
    "cos_stash_lock_acquire",
    "cos_stash_lock_release",
    "file_exists_strict",
    "portable_epoch_now",
    "safe_jsonl_append",
}

COMMAND_V_RE = re.compile(r"\bcommand\s+-v\s+([A-Za-z0-9_.@/+:-]+)")
SHUTIL_WHICH_RE = re.compile(r"\bshutil\.which\(\s*[\"']([^\"']+)[\"']")
SUBPROCESS_LIST_RE = re.compile(r"\bsubprocess\.(?:run|Popen|check_call|check_output)\(\s*\[\s*[\"']([^\"']+)[\"']")
BREW_INSTALL_RE = re.compile(r"\bbrew\s+install\s+([A-Za-z0-9_.@/+:-]+)")
CARGO_INSTALL_RE = re.compile(r"\bcargo\s+install\s+([A-Za-z0-9_.@/+:-]+)")
GO_INSTALL_RE = re.compile(r"\bgo\s+install\s+([A-Za-z0-9_.@/+:-]+)")
NPM_INSTALL_GLOBAL_RE = re.compile(r"\bnpm\s+install\s+-g\s+([A-Za-z0-9_.@/+:-]+)")
PIP_INSTALL_RE = re.compile(r"\b(?:python3?\s+-m\s+)?pip(?:3)?\s+install\s+(?:--user\s+)?([A-Za-z0-9_.@/+:-]+)")
BASH_FUNCTION_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{")
SHELL_FUNCTION_RE = re.compile(r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\b")
REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+(?:\[[^\]]+\])?)")

PACKAGE_MANIFEST_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "go.mod",
    "Cargo.toml",
}


@dataclass(frozen=True)
class SourceRef:
    path: str
    line: int | None = None
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"path": self.path}
        if self.line is not None:
            out["line"] = self.line
        if self.source:
            out["source"] = self.source
        return out


@dataclass(frozen=True)
class Candidate:
    name: str
    kind: str
    sources: tuple[SourceRef, ...]
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "name": self.name,
            "kind": self.kind,
            "sources": [source.to_dict() for source in self.sources],
        }
        if self.details:
            out["details"] = self.details
        return out


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _is_excluded(root: Path, path: Path) -> bool:
    rel = _rel(root, path)
    if any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return True
    return any(part in EXCLUDED_DIR_NAMES for part in path.parts)


def _tracked_files(root: Path) -> list[Path] | None:
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return [root / line for line in proc.stdout.splitlines() if line.strip()]


def _iter_files(root: Path, suffixes: tuple[str, ...]) -> Iterable[Path]:
    candidates = _tracked_files(root)
    if candidates is None:
        candidates = [path for path in root.rglob("*") if path.is_file()]
    for path in candidates:
        if not path.is_file() or _is_excluded(root, path):
            continue
        if path.name in PACKAGE_MANIFEST_NAMES or path.suffix in suffixes:
            yield path


def _unique_candidates(rows: Iterable[Candidate]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row.name, row.kind)
        current = merged.setdefault(
            key,
            {"name": row.name, "kind": row.kind, "sources": [], "details": {}},
        )
        current["sources"].extend(source.to_dict() for source in row.sources)
        if row.details:
            current["details"].update(row.details)
    out: list[dict[str, Any]] = []
    for item in merged.values():
        seen_sources = set()
        deduped_sources = []
        for source in item["sources"]:
            marker = json.dumps(source, sort_keys=True)
            if marker in seen_sources:
                continue
            seen_sources.add(marker)
            deduped_sources.append(source)
        item["sources"] = deduped_sources
        if not item["details"]:
            item.pop("details", None)
        out.append(item)
    return sorted(out, key=lambda item: (item["kind"], item["name"]))


def _parse_req_name(spec: str) -> str | None:
    match = REQ_NAME_RE.match(spec.strip())
    if not match:
        return None
    name = normalize_tool_id(match.group(1))
    return name or None


def _manifest_python_names(manifest: Manifest) -> set[str]:
    names: set[str] = set()
    for spec in manifest.python_required:
        name = _parse_req_name(spec)
        if name:
            names.add(name)
    for specs in manifest.python_groups.values():
        for spec in specs:
            name = _parse_req_name(spec)
            if name:
                names.add(name)
    return names


def _manifest_tool_names(manifest: Manifest) -> set[str]:
    names = {tool.name for tool in manifest.tools}
    for tool in manifest.tools:
        command = (tool.check or "").split()
        if command:
            names.add(command[0])
    return {name for name in names if name}


def _load_adoption_package_index(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "manifests" / "external-tools-adoption.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    index: dict[str, dict[str, Any]] = {}
    for tool in data.get("tools", []) or []:
        tid = normalize_tool_id(str(tool.get("id", "")))
        if tid:
            index[tid] = tool
        for package in tool.get("package_names", []) or []:
            pid = normalize_tool_id(str(package))
            if pid:
                index[pid] = tool
    return index


def collect_package_dependencies(root: Path) -> list[Candidate]:
    rows: list[Candidate] = []
    for path in _iter_files(root, (".txt", ".toml", ".json",)):
        rel = _rel(root, path)
        deps: list[str] = []
        kind = "package"
        try:
            if path.name == "pyproject.toml":
                deps = parse_pyproject(path)
                kind = "python"
            elif path.name.startswith("requirements") and path.suffix == ".txt":
                deps = parse_requirements(path)
                kind = "python"
            elif "requirements/dependency-lanes" in rel and path.suffix == ".txt":
                deps = parse_requirements(path)
                kind = "python"
            elif path.name == "package.json":
                deps = parse_package_json(path)
                kind = "node"
            elif path.name == "go.mod":
                deps = parse_go_mod(path)
                kind = "go"
            elif path.name == "Cargo.toml":
                data = tomllib.loads(path.read_text(encoding="utf-8"))
                deps = sorted(normalize_tool_id(dep) for dep in (data.get("dependencies", {}) or {}).keys())
                kind = "rust"
        except Exception:
            continue
        for dep in deps:
            rows.append(Candidate(dep, kind, (SourceRef(rel, source="package-manifest"),)))
    return rows


def _defined_shell_functions(text: str) -> set[str]:
    names: set[str] = set()
    for line in text.splitlines():
        for regex in (BASH_FUNCTION_RE, SHELL_FUNCTION_RE):
            match = regex.match(line)
            if match:
                names.add(match.group(1))
    return names



def _clean_command_name(value: str, source: str) -> str | None:
    value = value.strip().strip('"\'').strip('.,;:')
    if not value or value.startswith(("$", "-")) or value in {".", "+"}:
        return None
    if "/" in value and source not in {"go-install"}:
        value = Path(value).name
    if not value or not re.match(r"^[A-Za-z0-9@][A-Za-z0-9_.@+:-]*$", value):
        return None
    return value


def _first_install_operand(value: str) -> str | None:
    for token in value.split():
        if token.startswith("-") or token in {"install", "upgrade"}:
            continue
        return token
    return None

def _command_candidates_from_line(line: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for regex, source in (
        (COMMAND_V_RE, "command-v"),
        (SHUTIL_WHICH_RE, "shutil-which"),
        (SUBPROCESS_LIST_RE, "subprocess"),
        (BREW_INSTALL_RE, "brew-install"),
        (CARGO_INSTALL_RE, "cargo-install"),
        (GO_INSTALL_RE, "go-install"),
        (NPM_INSTALL_GLOBAL_RE, "npm-install-global"),
        (PIP_INSTALL_RE, "pip-install"),
    ):
        for match in regex.finditer(line):
            value = match.group(1).strip()
            if source in {"brew-install", "cargo-install", "npm-install-global", "pip-install"}:
                operand = _first_install_operand(value)
                if operand is None:
                    continue
                value = operand
            if source == "go-install" and "/" in value:
                value = value.rstrip("/").split("/")[-1].split("@")[0]
            if source == "pip-install":
                value = value.split("[")[0]
            cleaned = _clean_command_name(value, source)
            if cleaned is None:
                continue
            out.append((cleaned, source))
    return out


def collect_command_probes(root: Path) -> list[Candidate]:
    rows: list[Candidate] = []
    for path in _iter_files(root, (".py", ".sh",)):
        if path.suffix not in {".py", ".sh"} and not path.name.startswith("cos-"):
            continue
        rel = _rel(root, path)
        text = path.read_text(encoding="utf-8", errors="replace")
        internal = _defined_shell_functions(text) | KNOWN_INTERNAL_HELPERS
        for lineno, line in enumerate(text.splitlines(), start=1):
            for command, source in _command_candidates_from_line(line):
                name = command.strip().strip('"\'')
                if not name:
                    continue
                if name in internal:
                    kind = "internal-helper"
                elif name in PLATFORM_BUILTINS:
                    kind = "platform-builtin"
                else:
                    kind = "host-tool"
                rows.append(Candidate(name, kind, (SourceRef(rel, lineno, source),)))
    return rows


def build_report(root: Path, *, manifest_path: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    manifest = load_manifest(manifest_path or root / "manifests" / "dependencies.yaml")
    manifest_tools = _manifest_tool_names(manifest)
    manifest_python = _manifest_python_names(manifest)
    adoption_index = _load_adoption_package_index(root)

    package_rows = collect_package_dependencies(root)
    command_rows = collect_command_probes(root)

    declared_host_tool_names = {row.name for row in command_rows if row.kind == "host-tool"}
    declared_python_names = {row.name for row in package_rows if row.kind == "python"}

    missing_from_manifest: list[Candidate] = []
    platform_builtin: list[Candidate] = []
    internal_helper_false_positive: list[Candidate] = []
    optional_lane_needed: list[Candidate] = []
    declared_python_dependency: list[Candidate] = []
    declared_host_tool: list[Candidate] = []
    blocked_or_removed_by_policy: list[Candidate] = []

    for row in command_rows:
        if row.kind == "platform-builtin":
            platform_builtin.append(row)
        elif row.kind == "internal-helper":
            internal_helper_false_positive.append(row)
        elif row.kind == "host-tool":
            declared_host_tool.append(row)
            if row.name not in manifest_tools:
                missing_from_manifest.append(row)

    for row in package_rows:
        if row.kind == "python":
            declared_python_dependency.append(row)
            in_lane = any(source.path.startswith("requirements/dependency-lanes/") for source in row.sources)
            if row.name not in manifest_python and in_lane:
                optional_lane_needed.append(row)
            elif row.name not in manifest_python:
                missing_from_manifest.append(Candidate(row.name, "python", row.sources, {"reason": "python dependency not declared in manifests/dependencies.yaml python groups"}))
        policy = adoption_index.get(row.name)
        if policy:
            verdict = str(policy.get("verdict", "")).upper()
            status = str(policy.get("status", "")).lower()
            if verdict in {"REMOVE", "REJECT"} or status in {"cleanup_required", "removed"}:
                blocked_or_removed_by_policy.append(Candidate(row.name, row.kind, row.sources, {"verdict": verdict, "status": status, "tool_id": policy.get("id")}))

    manifested_but_unused = [
        Candidate(name, "host-tool", (SourceRef("manifests/dependencies.yaml", source="dependency-manifest"),))
        for name in sorted(manifest_tools - declared_host_tool_names)
    ]

    profile_candidate = [
        Candidate(row.name, row.kind, row.sources, {"reason": "observed in repository but absent from install manifest"})
        for row in missing_from_manifest
    ]

    report = {
        "schema_version": SCHEMA_VERSION,
        "root": str(root),
        "summary": {},
        "missing_from_manifest": _unique_candidates(missing_from_manifest),
        "manifested_but_unused": _unique_candidates(manifested_but_unused),
        "platform_builtin": _unique_candidates(platform_builtin),
        "internal_helper_false_positive": _unique_candidates(internal_helper_false_positive),
        "optional_lane_needed": _unique_candidates(optional_lane_needed),
        "declared_python_dependency": _unique_candidates(declared_python_dependency),
        "declared_host_tool": _unique_candidates(declared_host_tool),
        "blocked_or_removed_by_policy": _unique_candidates(blocked_or_removed_by_policy),
        "profile_candidate": _unique_candidates(profile_candidate),
        "manifest": {
            "path": _rel(root, manifest_path or root / "manifests" / "dependencies.yaml"),
            "tool_count": len(manifest.tools),
            "python_dependency_count": len(manifest_python),
            "profiles": sorted(manifest.profiles),
        },
    }
    report["summary"] = {
        key: len(value)
        for key, value in report.items()
        if isinstance(value, list)
    }
    return report


def dumps_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def format_human(report: dict[str, Any]) -> str:
    lines = [f"dependency coverage audit: {report['schema_version']}"]
    for key, count in sorted(report.get("summary", {}).items()):
        lines.append(f"  {key}: {count}")
    missing = report.get("missing_from_manifest", [])[:20]
    if missing:
        lines.append("\nmissing_from_manifest sample:")
        for row in missing:
            first = row.get("sources", [{}])[0]
            loc = first.get("path", "?")
            if first.get("line"):
                loc = f"{loc}:{first['line']}"
            lines.append(f"  - {row['name']} ({row['kind']}) @ {loc}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit dependency coverage drift without installing anything.")
    parser.add_argument("--root", default=".", help="Repository root to audit. Defaults to current directory.")
    parser.add_argument("--manifest", help="Override dependency manifest path.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    manifest_path = Path(args.manifest).resolve() if args.manifest else None
    try:
        report = build_report(root, manifest_path=manifest_path)
    except ManifestError as exc:
        print(f"dependency coverage audit: {exc}")
        return 2
    print(dumps_json(report) if args.json else format_human(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
