#!/usr/bin/env python3
# SCOPE: both
"""Project-agnostic provenance hygiene scanner for agent-assisted repos.

The scanner blocks host-local paths, sensitive source-project terms, prohibited
imports/path hacks, external Go replace directives, and explicit provenance
language that identifies private/local origins. Projects configure policy in `manifests/provenance-scan.yaml` or `.cognitive-os/provenance-scan.yaml`.
"""
from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ALLOW_MARKER = "cos-allow-provenance-scan"
CONFIG_CANDIDATES = (
    "manifests/provenance-scan.yaml",
    ".cognitive-os/provenance-scan.yaml",
    "provenance-scan.yaml",
)
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "target",
    "dist",
    "build",
}
DEFAULT_EXCLUDED_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".woff", ".woff2",
    ".ttf", ".zip", ".gz", ".tar", ".db", ".sqlite", ".pyc", ".lock",
}
DEFAULT_FORBIDDEN_PATH_PATTERNS = [
    r"/Users/[^\s`'\"<>)]*",  # cos-allow-provenance-scan: scanner pattern literal  # cos-allow-absolute-path cos-allow-local-privacy-pattern: scanner pattern literal
    r"/home/(?!jovyan/)[^\s`'\"<>)]*",  # cos-allow-provenance-scan: scanner pattern literal  # cos-allow-absolute-path cos-allow-local-privacy-pattern: scanner pattern literal
    r"[A-Za-z]:\\Users\\[^\s`'\"<>)]*",
    r"(?:^|[\s`'\"(])Projects/[A-Za-z0-9._/-]+",  # cos-allow-absolute-path cos-allow-local-privacy-pattern: scanner pattern literal
]
DEFAULT_PROVENANCE_LANGUAGE_PATTERNS = [
    # Block provenance wording only when it points at sensitive/local origins.
    r"\b(?:cloned|copied|adapted)\s+from\b[^\n]{0,160}(?:/Users/|/home/|Projects/|private\s+repo|local\s+reference)",  # cos-allow-provenance-scan: scanner pattern literal  # cos-allow-absolute-path cos-allow-local-privacy-pattern: scanner pattern literal
    r"\bbased\s+on\s+(?:a\s+)?private\s+repo\b",
    r"\blocal\s+reference\s+(?:repo|project|backend|monorepo|pattern)s?\b",
    r"\breference\s+backend\s+monorepos?\b",
]
GO_IMPORT_RE = re.compile(r'^[\s_]*"([^"\s]+)"')
GO_SINGLE_IMPORT_RE = re.compile(r'^\s*import\s+(?:[\w.]+\s+)?"([^"]+)"')
GO_REPLACE_RE = re.compile(r'^\s*replace\s+([^\s]+)\s+=>\s+([^\s]+)')
PY_IMPORT_RE = re.compile(r'^\s*(?:from\s+([A-Za-z_][\w.]*)\s+import\b|import\s+([A-Za-z_][\w.]*))')
TS_IMPORT_RE = re.compile(r'''(?:from\s+['"]([^'"]+)['"]|import\s*\(?\s*['"]([^'"]+)['"]\)?)''')
PATH_HACK_RE = re.compile(r"sys\.path\.(?:append|insert)\(([^)]*)\)")


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    category: str
    detail: str
    matched: str


@dataclass(frozen=True)
class Policy:
    forbidden_terms: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    provenance_language: tuple[str, ...]
    allowed_absolute_paths: tuple[str, ...]
    allowed_domains: tuple[str, ...]
    allowed_import_roots: dict[str, tuple[str, ...]]
    forbidden_import_roots: dict[str, tuple[str, ...]]
    exclude_globs: tuple[str, ...]
    scan_imports: bool
    scan_path_hacks: bool


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if importlib.util.find_spec("yaml") is None:
        raise SystemExit("ERROR: PyYAML is required to read provenance scan config")
    import yaml  # type: ignore

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: provenance config must be a mapping: {path}")
    return data


def find_config(root: Path, raw: str | None) -> Path | None:
    if raw:
        path = Path(raw)
        return path if path.is_absolute() else root / path
    for rel in CONFIG_CANDIDATES:
        path = root / rel
        if path.exists():
            return path
    return None


def as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    raise SystemExit(f"ERROR: expected string/list in provenance config, got {type(value).__name__}")


def roots_map(value: Any) -> dict[str, tuple[str, ...]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise SystemExit("ERROR: import root config must be a mapping")
    return {str(k): as_tuple(v) for k, v in value.items()}


def build_policy(root: Path, config_path: Path | None) -> Policy:
    raw = load_yaml(config_path) if config_path else {}
    section = raw.get("provenance", raw)
    if not isinstance(section, dict):
        raise SystemExit("ERROR: provenance config section must be a mapping")
    return Policy(
        forbidden_terms=as_tuple(section.get("forbidden_terms")),
        forbidden_paths=tuple(DEFAULT_FORBIDDEN_PATH_PATTERNS) + as_tuple(section.get("forbidden_paths")),
        provenance_language=tuple(DEFAULT_PROVENANCE_LANGUAGE_PATTERNS) + as_tuple(section.get("forbidden_provenance_language")),
        allowed_absolute_paths=("/tmp/", "/var/folders/", "/private/var/folders/") + as_tuple(section.get("allowed_absolute_paths")),
        allowed_domains=as_tuple(section.get("allowed_domains")),
        allowed_import_roots=roots_map(section.get("allowed_import_roots")),
        forbidden_import_roots=roots_map(section.get("forbidden_import_roots")),
        exclude_globs=as_tuple(section.get("exclude_globs")),
        scan_imports=bool(section.get("scan_imports", True)),
        scan_path_hacks=bool(section.get("scan_path_hacks", True)),
    )


def git_root() -> Path:
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, capture_output=True, check=False, timeout=30)
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 and result.stdout.strip() else Path.cwd().resolve()


def git_deleted(root: Path) -> set[str]:
    result = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=D"], cwd=root, text=True, capture_output=True, check=False, timeout=30)
    return set(result.stdout.splitlines()) if result.returncode == 0 else set()


def git_tracked(root: Path) -> list[str]:
    result = subprocess.run(["git", "ls-files"], cwd=root, text=True, capture_output=True, check=False, timeout=60)
    if result.returncode != 0:
        return []
    deleted = git_deleted(root)
    return [line for line in result.stdout.splitlines() if line and line not in deleted]


def staged_files(root: Path) -> list[str]:
    result = subprocess.run(["git", "diff", "--cached", "--raw", "-M", "-C", "--diff-filter=ACM"], cwd=root, text=True, capture_output=True, check=False, timeout=60)
    files: list[str] = []
    for line in result.stdout.splitlines() if result.returncode == 0 else []:
        _meta, _tab, raw_path = line.partition("\t")
        if raw_path:
            files.append(raw_path.split("\t")[-1])
    return files


def should_skip(path: Path, root: Path, policy: Policy, content: bytes | None = None) -> bool:
    try:
        rel = path.relative_to(root).as_posix()
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    if any(part in DEFAULT_EXCLUDED_DIRS for part in parts):
        return True
    if path.suffix.lower() in DEFAULT_EXCLUDED_SUFFIXES:
        return True
    if any(fnmatch.fnmatch(rel, pattern) for pattern in policy.exclude_globs):
        return True
    if content is None:
        try:
            content = path.read_bytes()[:4096]
        except OSError:
            return True
    return b"\0" in content[:4096]


def iter_paths(root: Path, paths: list[str], all_files: bool, policy: Policy) -> list[Path]:
    if not paths and not all_files:
        paths = git_tracked(root)
        return [(root / rel).resolve() for rel in paths if (root / rel).is_file() and not should_skip((root / rel).resolve(), root, policy)]
    if all_files and not paths:
        paths = git_tracked(root) or ["."]
    out: list[Path] = []
    for raw in paths:
        path = Path(raw) if Path(raw).is_absolute() else root / raw
        if path.is_file():
            out.append(path.resolve())
        elif path.is_dir():
            out.extend(p.resolve() for p in path.rglob("*") if p.is_file())
    return [p for p in out if not should_skip(p, root, policy)]


def language_for(path: Path) -> str | None:
    name = path.name
    suffix = path.suffix.lower()
    if name == "go.mod" or suffix == ".go":
        return "go"
    if suffix == ".py":
        return "python"
    if suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}:
        return "ts"
    return None


def allowed_by_prefix(value: str, prefixes: tuple[str, ...]) -> bool:
    return any(value == prefix or value.startswith(prefix.rstrip("/") + "/") or value.startswith(prefix) for prefix in prefixes)


def is_relative_import(value: str) -> bool:
    return value.startswith((".", "..", "/"))


def is_internal_go_replace(path: Path, root: Path, target: str) -> bool:
    if not target.startswith(("./", "../")):
        return False
    try:
        resolved = (path.parent / target).resolve()
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def import_findings(path: Path, root: Path, line_no: int, line: str, policy: Policy) -> list[Finding]:
    if not policy.scan_imports:
        return []
    lang = language_for(path)
    if lang is None:
        return []
    findings: list[Finding] = []
    imports: list[str] = []
    if lang == "go":
        if m := GO_SINGLE_IMPORT_RE.search(line):
            imports.append(m.group(1))
        elif m := GO_IMPORT_RE.search(line):
            imports.append(m.group(1))
        if path.name == "go.mod" and (m := GO_REPLACE_RE.search(line)):
            target = m.group(2)
            if target.startswith(("../", "./")) and is_internal_go_replace(path, root, target):
                pass
            elif target.startswith(("/", "../", "./")) and not allowed_by_prefix(target, policy.allowed_absolute_paths):
                findings.append(Finding(path, line_no, "external-go-replace", "Go replace points outside allowed roots", target))
    elif lang == "python":
        if m := PY_IMPORT_RE.search(line):
            imports.append((m.group(1) or m.group(2)).split(".", 1)[0])
        if policy.scan_path_hacks and (m := PATH_HACK_RE.search(line)):
            expr = m.group(1)
            if any(token in expr for token in ("/Users/", "/home/", "Projects/", "..")):  # cos-allow-absolute-path cos-allow-local-privacy-pattern: scanner pattern literal
                findings.append(Finding(path, line_no, "python-path-hack", "sys.path mutation references local/external path", expr.strip()))
    elif lang == "ts":
        for m in TS_IMPORT_RE.finditer(line):
            imports.append(m.group(1) or m.group(2))

    allowed = policy.allowed_import_roots.get(lang, ())
    forbidden = policy.forbidden_import_roots.get(lang, ())
    for imp in imports:
        if not imp or is_relative_import(imp):
            continue
        if forbidden and allowed_by_prefix(imp, forbidden):
            findings.append(Finding(path, line_no, f"forbidden-{lang}-import", "import root is explicitly forbidden", imp))
        if allowed and not allowed_by_prefix(imp, allowed):
            findings.append(Finding(path, line_no, f"unapproved-{lang}-import", "import root is not in allowlist", imp))
    return findings


def allowed_path_match(match: str, policy: Policy) -> bool:
    normalized = match.strip()
    if normalized in {"/Users/", "/home/", "C:\\Users\\"}:  # cos-allow-absolute-path cos-allow-local-privacy-pattern: scanner pattern literal
        return True
    if normalized.startswith(("/Users/...", "/home/...")):  # cos-allow-absolute-path cos-allow-local-privacy-pattern: scanner pattern literal
        return True
    if normalized.startswith("C:\\Users\\..."):  # cos-allow-absolute-path cos-allow-local-privacy-pattern: scanner pattern literal
        return True
    return allowed_by_prefix(normalized, policy.allowed_absolute_paths)


def scan_text(path: Path, root: Path, text: str, policy: Policy) -> list[Finding]:
    findings: list[Finding] = []
    compiled_paths = [re.compile(pattern) for pattern in policy.forbidden_paths]
    compiled_provenance = [re.compile(pattern, re.IGNORECASE) for pattern in policy.provenance_language]
    forbidden_terms = tuple(term for term in policy.forbidden_terms if term)
    for line_no, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        for regex in compiled_paths:
            for match in regex.findall(line):
                value = match if isinstance(match, str) else "".join(match)
                value = value.strip(" `\"'()")
                if value and not allowed_path_match(value, policy):
                    findings.append(Finding(path, line_no, "forbidden-path", "host-local or non-canonical path", value))
        for term in forbidden_terms:
            if term in line:
                findings.append(Finding(path, line_no, "forbidden-term", "project/source term is forbidden", term))
        for regex in compiled_provenance:
            if m := regex.search(line):
                findings.append(Finding(path, line_no, "provenance-language", "sensitive provenance wording", m.group(0)))
        findings.extend(import_findings(path, root, line_no, line, policy))
    return findings


def read_text(content: bytes) -> str | None:
    for enc in ("utf-8", "latin-1"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            pass
    return None


def scan_file(path: Path, root: Path, policy: Policy) -> list[Finding]:
    try:
        content = path.read_bytes()
    except OSError:
        return []
    if should_skip(path, root, policy, content):
        return []
    text = read_text(content)
    return [] if text is None else scan_text(path, root, text, policy)


def scan_staged(root: Path, policy: Policy) -> list[Finding]:
    findings: list[Finding] = []
    for rel in staged_files(root):
        path = root / rel
        result = subprocess.run(["git", "show", f":{rel}"], cwd=root, capture_output=True, check=False, timeout=60)
        if result.returncode != 0 or should_skip(path, root, policy, result.stdout):
            continue
        text = read_text(result.stdout)
        if text is not None:
            findings.extend(scan_text(path, root, text, policy))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan repository provenance hygiene.")
    parser.add_argument("paths", nargs="*", help="Files/directories to scan. Defaults to git-tracked files.")
    parser.add_argument("--root", default=None, help="Repository root. Defaults to git root or cwd.")
    parser.add_argument("--config", default=None, help="YAML config path. Defaults to manifests/provenance-scan.yaml if present.")
    parser.add_argument("--staged", action="store_true", help="Scan staged files only.")
    parser.add_argument("--all-files", action="store_true", help="Scan all tracked files or provided directories.")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else git_root()
    config_path = find_config(root, args.config)
    policy = build_policy(root, config_path)
    findings = scan_staged(root, policy) if args.staged else []
    if not args.staged:
        for path in iter_paths(root, args.paths, args.all_files, policy):
            findings.extend(scan_file(path, root, policy))

    unique = sorted(set(findings), key=lambda f: (str(f.path), f.line, f.category, f.matched))
    payload = {
        "schema_version": "provenance-scan/v1",
        "status": "fail" if unique else "pass",
        "config": str(config_path.relative_to(root)) if config_path and config_path.is_relative_to(root) else (str(config_path) if config_path else None),
        "finding_count": len(unique),
        "findings": [
            {
                "path": str(f.path.relative_to(root)),
                "line": f.line,
                "category": f.category,
                "detail": f.detail,
                "matched": f.matched,
            }
            for f in unique[:200]
        ],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif unique:
        for item in payload["findings"]:
            print(f"{item['path']}:{item['line']}: {item['category']}: {item['matched']} — {item['detail']}", file=sys.stderr)
        print("\nBLOCKED: provenance-scan found non-portable or sensitive provenance content.", file=sys.stderr)
    else:
        print("provenance-scan-ok")
    return 1 if unique else 0


if __name__ == "__main__":
    raise SystemExit(main())
