#!/usr/bin/env python3
# SCOPE: os-only
"""
cos_build_self_knowledge.py — Generate the COS self-knowledge index.

Produces four artifacts under .cognitive-os/self-knowledge/:
  api-surface.json    — module → {classes, functions, shebang_bash_entrypoints}
  dep-graph.json      — {source: [targets]} for Python imports + Bash sources
  glossary.md         — H2/H3 headings + first sentence from docs/adrs + docs/guides
  codebase-summary.md — top subsystems, most-imported modules, ADR index
  .mtime              — ISO-8601 timestamp of last successful build

Usage:
  python3 scripts/cos_build_self_knowledge.py [--project-dir PATH]
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_sentence(text: str) -> str:
    """Return the first non-empty sentence from text."""
    text = text.strip()
    if not text:
        return ""
    # Split on period/exclamation/question that ends a sentence
    m = re.search(r'[.!?](?:\s|$)', text)
    if m:
        return text[: m.end()].strip()
    # Fallback: first 120 chars
    return text[:120].strip()


def _resolve_project_dir(given: str | None) -> Path:
    if given:
        return Path(given).resolve()
    # Walk up from this script looking for cognitive-os.yaml or .claude/
    candidate = Path(__file__).resolve().parent.parent
    if (candidate / "cognitive-os.yaml").exists() or (candidate / ".claude").exists():
        return candidate
    return Path.cwd()


# ---------------------------------------------------------------------------
# Python AST scanner
# ---------------------------------------------------------------------------

def _scan_python(path: Path) -> dict[str, Any]:
    """Extract classes, functions (name + signature + first doc line) from a .py file."""
    src = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return {"classes": [], "functions": [], "shebang_bash_entrypoints": []}

    # Module-level classes and functions only (iter_child_nodes = one level deep)
    classes: list[str] = []
    functions: list[dict[str, str]] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sig = _extract_signature(node, src)
            doc = ast.get_docstring(node) or ""
            functions.append({
                "name": node.name,
                "signature": sig,
                "doc_first_line": _first_sentence(doc),
            })

    return {"classes": classes, "functions": functions, "shebang_bash_entrypoints": []}


def _extract_signature(node: ast.FunctionDef | ast.AsyncFunctionDef, src: str) -> str:
    """Build a readable signature string from an AST function node."""
    args = node.args
    params: list[str] = []

    # positional args with optional defaults
    defaults = args.defaults
    n_defaults = len(defaults)
    n_args = len(args.args)
    for i, arg in enumerate(args.args):
        default_offset = i - (n_args - n_defaults)
        ann = ""
        if arg.annotation:
            ann = f": {ast.unparse(arg.annotation)}"
        if default_offset >= 0:
            default_val = f" = {ast.unparse(defaults[default_offset])}"
            params.append(f"{arg.arg}{ann}{default_val}")
        else:
            params.append(f"{arg.arg}{ann}")

    # *args
    if args.vararg:
        ann = f": {ast.unparse(args.vararg.annotation)}" if args.vararg.annotation else ""
        params.append(f"*{args.vararg.arg}{ann}")
    # keyword-only
    for karg, kdefault in zip(args.kwonlyargs, args.kw_defaults):
        ann = f": {ast.unparse(karg.annotation)}" if karg.annotation else ""
        dv = f" = {ast.unparse(kdefault)}" if kdefault else ""
        params.append(f"{karg.arg}{ann}{dv}")
    # **kwargs
    if args.kwarg:
        ann = f": {ast.unparse(args.kwarg.annotation)}" if args.kwarg.annotation else ""
        params.append(f"**{args.kwarg.arg}{ann}")

    ret = ""
    if node.returns:
        ret = f" -> {ast.unparse(node.returns)}"

    return f"({', '.join(params)}){ret}"


# ---------------------------------------------------------------------------
# Bash scanner
# ---------------------------------------------------------------------------

_BASH_FUNC_RE = re.compile(r'^(?:function\s+)?(\w[\w_-]*)\s*\(\s*\)\s*\{', re.MULTILINE)


def _scan_bash(path: Path) -> dict[str, Any]:
    """Extract entrypoint (shebang present) and function names from a .sh file."""
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"classes": [], "functions": [], "shebang_bash_entrypoints": []}

    entrypoints: list[str] = []
    if src.startswith("#!/"):
        entrypoints = [str(path)]

    func_names = _BASH_FUNC_RE.findall(src)
    functions = [{"name": n, "signature": "()", "doc_first_line": ""} for n in func_names]

    return {"classes": [], "functions": functions, "shebang_bash_entrypoints": entrypoints}


# ---------------------------------------------------------------------------
# Dependency extraction
# ---------------------------------------------------------------------------

_PY_IMPORT_RE = re.compile(
    r'^(?:from|import)\s+(lib\.\w[\w.]*|hooks\._lib\.\w[\w.]*|packages\.\w[\w.]*)',
    re.MULTILINE,
)
_BASH_SOURCE_RE = re.compile(
    r'(?:source|\.)\s+["\']?(\$[A-Z_]*/)?(?:hooks/|lib/)([\w/_.-]+\.sh)',
    re.MULTILINE,
)


def _extract_python_deps(path: Path) -> list[str]:
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    deps = []
    for m in _PY_IMPORT_RE.finditer(src):
        raw = m.group(1)
        # Convert dotted import to path: lib.foo_bar -> lib/foo_bar.py
        parts = raw.split(".")
        if len(parts) >= 2:
            dep_path = "/".join(parts) + ".py"
            deps.append(dep_path)
    return list(set(deps))


def _extract_bash_deps(path: Path) -> list[str]:
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    deps = []
    for m in _BASH_SOURCE_RE.finditer(src):
        prefix = "hooks/" if not m.group(1) else ""
        dep = prefix + m.group(2)
        deps.append(dep)
    return list(set(deps))


# ---------------------------------------------------------------------------
# Glossary builder
# ---------------------------------------------------------------------------

_H2H3_RE = re.compile(r'^#{2,3}\s+(.+)', re.MULTILINE)


def _build_glossary(project_dir: Path) -> str:
    entries: dict[str, str] = {}

    sources: list[Path] = []
    for pattern in ["docs/adrs/*.md", "docs/guides/*.md"]:
        sources.extend(project_dir.glob(pattern))

    for doc in sorted(sources):
        try:
            src = doc.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        # Extract first sentence of the whole document (for ADRs: the decision)
        # and pair it with each H2/H3 heading found.
        headings = _H2H3_RE.findall(src)
        for heading in headings:
            key = heading.strip()
            if key in entries:
                continue  # dedup
            # Find the paragraph right after this heading
            pattern = re.escape("## " + key) + r'|' + re.escape("### " + key)
            m = re.search(pattern, src)
            snippet = ""
            if m:
                after = src[m.end():].lstrip()
                snippet = _first_sentence(after)
            entries[key] = snippet

    if not entries:
        return "# Glossary\n\n*(No documentation sources found.)*\n"

    lines = ["# Glossary\n", "Auto-generated from ADR + guide headings. Rebuild with `cos-build-self-knowledge.py`.\n"]
    for key in sorted(entries.keys(), key=str.lower):
        snippet = entries[key]
        if snippet:
            lines.append(f"\n## {key}\n\n{snippet}\n")
        else:
            lines.append(f"\n## {key}\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Codebase summary builder
# ---------------------------------------------------------------------------

def _build_codebase_summary(
    project_dir: Path,
    api_surface: dict[str, Any],
    dep_graph: dict[str, list[str]],
) -> str:
    # 1. Subsystems by file count
    subsystem_counts: Counter[str] = Counter()
    for path_str in api_surface:
        parts = Path(path_str).parts
        if len(parts) >= 2:
            subsystem_counts[parts[0] + "/" + parts[1]] += 1
        elif parts:
            subsystem_counts[parts[0]] += 1

    # 2. Most-imported modules (in-degree in dep-graph)
    in_degree: Counter[str] = Counter()
    for targets in dep_graph.values():
        for t in targets:
            in_degree[t] += 1

    # 3. ADR index
    adr_entries: list[tuple[str, str, str]] = []
    for adr_file in sorted((project_dir / "docs" / "adrs").glob("ADR-*.md")):
        try:
            content = adr_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        title_m = re.search(r'^#\s+ADR-\d+\w*\s+[—–-]+\s+(.+)', content, re.MULTILINE)
        status_m = re.search(r'\*\*Status\*\*:\s*(\w+)', content)
        title = title_m.group(1).strip() if title_m else adr_file.stem
        status = status_m.group(1) if status_m else "Unknown"
        adr_num = adr_file.stem
        adr_entries.append((adr_num, title, status))

    lines: list[str] = [
        "# Codebase Summary",
        "",
        f"Auto-generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Total indexed files: {len(api_surface)}",
        "",
        "## Top 5 Subsystems by File Count",
        "",
    ]
    for sub, count in subsystem_counts.most_common(5):
        lines.append(f"- `{sub}` — {count} files")

    lines += ["", "## 10 Most-Imported Modules", ""]
    for mod, cnt in in_degree.most_common(10):
        lines.append(f"- `{mod}` — imported by {cnt} file(s)")

    lines += ["", "## ADR Index", ""]
    for adr_num, title, status in adr_entries:
        lines.append(f"- **{adr_num}** [{status}] — {title}")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Source tree scanner
# ---------------------------------------------------------------------------

def _collect_source_files(project_dir: Path) -> list[Path]:
    """Return all Python + Bash files in the indexed trees."""
    files: list[Path] = []
    search_roots = [
        project_dir / "lib",
        project_dir / "hooks",
        project_dir / "scripts",
    ]
    # packages/*/lib
    packages_dir = project_dir / "packages"
    if packages_dir.is_dir():
        for pkg in packages_dir.iterdir():
            pkg_lib = pkg / "lib"
            if pkg_lib.is_dir():
                search_roots.append(pkg_lib)

    for root in search_roots:
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix in (".py", ".sh"):
                # Skip compiled / cache dirs
                if "__pycache__" in p.parts or ".egg-info" in str(p):
                    continue
                files.append(p)

    return files


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build(project_dir: Path) -> dict[str, Any]:
    """Build all four artifacts. Returns a summary dict."""
    out_dir = project_dir / ".cognitive-os" / "self-knowledge"
    out_dir.mkdir(parents=True, exist_ok=True)

    files = _collect_source_files(project_dir)
    print(f"Scanning {len(files)} files …", file=sys.stderr)

    api_surface: dict[str, Any] = {}
    dep_graph: dict[str, list[str]] = {}

    for file in sorted(files):
        rel = str(file.relative_to(project_dir))
        if file.suffix == ".py":
            api_surface[rel] = _scan_python(file)
            deps = _extract_python_deps(file)
        else:
            api_surface[rel] = _scan_bash(file)
            deps = _extract_bash_deps(file)
        if deps:
            dep_graph[rel] = deps

    # Write api-surface.json
    (out_dir / "api-surface.json").write_text(
        json.dumps(api_surface, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Write dep-graph.json
    (out_dir / "dep-graph.json").write_text(
        json.dumps(dep_graph, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Write glossary.md
    (out_dir / "glossary.md").write_text(
        _build_glossary(project_dir), encoding="utf-8"
    )

    # Write codebase-summary.md
    (out_dir / "codebase-summary.md").write_text(
        _build_codebase_summary(project_dir, api_surface, dep_graph), encoding="utf-8"
    )

    # Write .mtime stamp
    stamp = datetime.now(timezone.utc).isoformat()
    (out_dir / ".mtime").write_text(stamp + "\n", encoding="utf-8")

    print(f"Self-knowledge index written to {out_dir}", file=sys.stderr)
    return {
        "files_scanned": len(files),
        "api_surface_entries": len(api_surface),
        "dep_graph_edges": sum(len(v) for v in dep_graph.values()),
        "out_dir": str(out_dir),
        "stamp": stamp,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build COS self-knowledge index.")
    parser.add_argument("--project-dir", default=None, help="Project root (default: auto-detect)")
    args = parser.parse_args()

    project_dir = _resolve_project_dir(args.project_dir)
    if not project_dir.exists():
        print(f"ERROR: project dir not found: {project_dir}", file=sys.stderr)
        sys.exit(1)

    result = build(project_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
