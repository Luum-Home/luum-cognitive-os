#!/usr/bin/env python3
# SCOPE: both
"""Portable duplicate-code scanner for COS projects and local consumer fleets.

The scanner is intentionally dry-run/report-first. It uses dependency-free
fallback detection everywhere, and opportunistically records external tool status
for jscpd, PMD CPD, Semgrep, dupl, golangci-lint, and ast-grep when present.
"""
from __future__ import annotations
import os as _cos_os
import sys as _cos_sys
_cos_sys.path.insert(0, _cos_os.path.dirname(_cos_os.path.dirname(__file__)))
from lib.script_helpers import shingles
from lib.project_paths import relpath as _rel

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from typing import Any, Iterable

SCHEMA_VERSION = "cos-quality-duplicates.v1"
BASELINE_SCHEMA = "cos-quality-duplicates-baseline.v1"
DEFAULT_REPORT_DIR = Path(".cognitive-os/reports/quality-duplicates")
DEFAULT_BASELINE = Path(".cognitive-os/baselines/quality-duplicates.json")
DEFAULT_INCLUDE = (".",)
DEFAULT_EXCLUDE_PARTS = {
    ".git", ".hg", ".svn", ".cognitive-os", ".claude", ".codex", ".agents",
    "node_modules", "vendor", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache",
    "dist", "build", ".next", ".turbo", "coverage", "reports", "target",
}
TEXT_SUFFIXES = {
    ".py", ".sh", ".bash", ".zsh", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".kt", ".kts", ".c", ".h", ".cc", ".cpp", ".cxx", ".hpp",
    ".cs", ".rb", ".php", ".swift", ".scala", ".sql", ".lua", ".dart", ".ex", ".exs",
    ".yaml", ".yml", ".json", ".toml", ".md", ".svelte", ".vue", ".astro",
}
WORD_RE = re.compile(r"[A-Za-z0-9_./:-]+")
SHELL_FUNCTION_RE = re.compile(r"(?m)^\s*(?:function\s+([A-Za-z_][A-Za-z0-9_-]*)\s*(?:\(\))?|([A-Za-z_][A-Za-z0-9_-]*)\s*\(\))\s*\{\s*$")
PY_FUNC_RE = re.compile(r"^\s*(?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
JS_FUNC_RE = re.compile(r"\b(function\s+[A-Za-z_$][\w$]*\s*\(|[A-Za-z_$][\w$]*\s*=\s*\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*\([^)]*\)\s*\{)")


@dataclass(frozen=True)
class Finding:
    finding_id: str
    lane: str
    kind: str
    severity: str
    confidence: float
    left: str
    right: str
    similarity: float
    recommendation: str
    rationale: str

    @property
    def pair_key(self) -> str:
        return " :: ".join(sorted((self.left, self.right)))


def stable_id(kind: str, left: str, right: str, extra: str = "") -> str:
    digest = hashlib.sha1(f"{kind}\0{left}\0{right}\0{extra}".encode()).hexdigest()[:12]
    return f"{kind}:{digest}"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def is_text_candidate(path: Path) -> bool:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    if path.name in {"Dockerfile", "Makefile", "AGENTS.md", "README.md", "cognitive-os.yaml"}:
        return True
    return False


def collect_files(root: Path, include: Iterable[str], exclude_globs: Iterable[str] = ()) -> list[Path]:
    files: list[Path] = []
    exclude_patterns = tuple(exclude_globs)
    tracked: set[str] | None = None
    try:
        proc = subprocess.run(["git", "ls-files"], cwd=root, text=True, capture_output=True, timeout=10, check=False)
        if proc.returncode == 0:
            tracked = {line.strip() for line in proc.stdout.splitlines() if line.strip()}
    except Exception:
        tracked = None
    for item in include:
        base = (root / item).resolve() if not Path(item).is_absolute() else Path(item)
        candidates = [base] if base.is_file() else sorted(base.rglob("*")) if base.exists() else []
        for path in candidates:
            if not path.is_file() or path.is_symlink():
                continue
            rel = _rel(root, path)
            if tracked is not None and rel not in tracked:
                continue
            if any(part in DEFAULT_EXCLUDE_PARTS for part in path.parts):
                continue
            if exclude_patterns and any(path.match(pattern) or rel.startswith(pattern.rstrip("/")) for pattern in exclude_patterns):
                continue
            if is_text_candidate(path):
                files.append(path)
    # de-dupe by real path
    by_real: dict[Path, Path] = {}
    for path in files:
        try:
            by_real.setdefault(path.resolve(strict=True), path)
        except OSError:
            by_real.setdefault(path.resolve(), path)
    return sorted(by_real.values(), key=lambda p: _rel(root, p))


def normalize_line(line: str) -> str:
    line = line.strip()
    if not line or line.startswith(("#", "//", "/*", "*")) or line in {"{", "}", "};"}:
        return ""
    line = re.sub(r'"(?:\\.|[^"])*"', '"STR"', line)
    line = re.sub(r"'(?:\\.|[^'])*'", "'STR'", line)
    line = re.sub(r"\b\d+(?:\.\d+)?\b", "0", line)
    line = re.sub(r"\b[a-f0-9]{8,}\b", "HASH", line, flags=re.I)
    return re.sub(r"\s+", " ", line).lower()


def normalize_text(text: str) -> str:
    return "\n".join(line for line in (normalize_line(line) for line in text.splitlines()) if line)


def lexical_findings(root: Path, files: list[Path], min_tokens: int, shingle_size: int, threshold: float) -> list[Finding]:
    records: list[tuple[str, int, set[str]]] = []
    for path in files:
        tokens = WORD_RE.findall(normalize_text(read_text(path)))
        if len(tokens) < min_tokens:
            continue
        records.append((_rel(root, path), len(tokens), shingles(tokens, shingle_size)))
    findings: list[Finding] = []
    for i, left in enumerate(records):
        left_path, left_count, left_shingles = left
        for right_path, right_count, right_shingles in records[i + 1:]:
            if min(left_count, right_count) / max(left_count, right_count) < 0.55:
                continue
            union = len(left_shingles | right_shingles)
            similarity = round(len(left_shingles & right_shingles) / union, 4) if union else 0.0
            if similarity >= threshold:
                findings.append(Finding(
                    stable_id("lexical-near-copy", left_path, right_path),
                    "lexical", "lexical-near-copy", "medium", 0.72,
                    left_path, right_path, similarity,
                    "review-abstraction-or-allowlist", "normalized token shingles are highly similar",
                ))
    return findings


def function_blocks_for(path: Path, root: Path, min_tokens: int) -> list[tuple[str, str]]:
    text = read_text(path)
    rel = _rel(root, path)
    blocks: list[tuple[str, str]] = []
    lines = text.splitlines()
    if path.suffix == ".py":
        for i, line in enumerate(lines):
            match = PY_FUNC_RE.match(line)
            if not match:
                continue
            indent = len(line) - len(line.lstrip())
            end = i + 1
            for j in range(i + 1, len(lines)):
                if lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) <= indent:
                    break
                end = j + 1
            blocks.append((f"{rel}:{i+1}:{match.group(1)}", normalize_text("\n".join(lines[i:end]))))
    elif path.suffix in {".sh", ".bash", ".zsh"} or path.name.endswith(".sh"):
        idx = 0
        while idx < len(lines):
            m = SHELL_FUNCTION_RE.match(lines[idx])
            if not m:
                idx += 1
                continue
            name = m.group(1) or m.group(2) or "function"
            start = idx
            depth = lines[idx].count("{") - lines[idx].count("}")
            idx += 1
            while idx < len(lines) and depth > 0:
                depth += lines[idx].count("{") - lines[idx].count("}")
                idx += 1
            blocks.append((f"{rel}:{start+1}:{name}", normalize_text("\n".join(lines[start + 1:idx]))))
    elif path.suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        for m in JS_FUNC_RE.finditer(text):
            start = text[:m.start()].count("\n") + 1
            # Lightweight brace-balanced extraction from first opening brace.
            brace_at = text.find("{", m.start())
            if brace_at < 0:
                continue
            depth = 0
            end = brace_at
            for pos in range(brace_at, min(len(text), brace_at + 12000)):
                if text[pos] == "{":
                    depth += 1
                elif text[pos] == "}":
                    depth -= 1
                    if depth == 0:
                        end = pos + 1
                        break
            blocks.append((f"{rel}:{start}:js-function", normalize_text(text[brace_at:end])))
    return [(label, body) for label, body in blocks if len(WORD_RE.findall(body)) >= min_tokens]


def function_findings(root: Path, files: list[Path], min_tokens: int) -> list[Finding]:
    seen: dict[str, str] = {}
    findings: list[Finding] = []
    for path in files:
        for label, body in function_blocks_for(path, root, min_tokens):
            normalized = re.sub(r"\b[A-Za-z_][A-Za-z0-9_]*\b", "ID", body)
            digest = hashlib.sha1(normalized.encode()).hexdigest()
            if digest in seen and seen[digest].split(":", 1)[0] != label.split(":", 1)[0]:
                left = seen[digest]
                findings.append(Finding(
                    stable_id("normalized-function-repeat", left, label, digest),
                    "function", "normalized-function-repeat", "medium", 0.84,
                    left, label, 1.0,
                    "extract-common-function-or-document-isolation", "function bodies are identical after literal/identifier normalization",
                ))
            else:
                seen[digest] = label
    return findings


def external_tool_status(root: Path, include: list[str], run_external: bool) -> dict[str, Any]:
    tools = {
        "jscpd": ["jscpd", "--version"],
        "pmd": ["pmd", "--version"],
        "semgrep": ["semgrep", "--version"],
        "dupl": ["dupl", "--help"],
        "golangci-lint": ["golangci-lint", "--version"],
        "ast-grep": ["ast-grep", "--version"],
    }
    status: dict[str, Any] = {}
    for name, version_cmd in tools.items():
        binary = shutil.which(version_cmd[0])
        status[name] = {"present": bool(binary), "path": binary, "ran": False, "returncode": None, "role": tool_role(name)}
        if binary and run_external:
            try:
                proc = subprocess.run(version_cmd, cwd=root, text=True, capture_output=True, timeout=3, check=False)
                status[name]["version"] = (proc.stdout or proc.stderr).splitlines()[:2]
            except Exception as exc:
                status[name]["version_error"] = str(exc)
    if run_external and status["jscpd"]["present"]:
        out_dir = root / DEFAULT_REPORT_DIR / "jscpd"
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = ["jscpd", *include, "--reporters", "json", "--output", str(out_dir), "--silent"]
        try:
            proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True, timeout=120, check=False)
            status["jscpd"].update({"ran": True, "returncode": proc.returncode, "stderr_tail": proc.stderr[-500:]})
        except subprocess.TimeoutExpired:
            status["jscpd"].update({"ran": True, "returncode": 124, "error": "timeout"})
    return status


def tool_role(name: str) -> str:
    return {
        "jscpd": "primary lexical clone detector",
        "pmd": "optional CPD adapter for supported languages",
        "semgrep": "optional policy/common-logic pattern lane, not clone proof",
        "dupl": "optional Go AST clone lane",
        "golangci-lint": "optional Go common-logic lint lane",
        "ast-grep": "optional AST pattern lane",
    }[name]


def finding_identity(finding: dict[str, Any]) -> str:
    fid = finding.get("finding_id")
    if fid:
        return f"id:{fid}"
    return f"pair:{finding.get('kind')}:{finding.get('pair_key')}"


def load_baseline(path: Path | None) -> dict[str, Any] | None:
    if not path or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_baseline(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {"finding_id": item.get("finding_id"), "kind": item.get("kind"), "pair_key": item.get("pair_key"), "left": item.get("left"), "right": item.get("right")}
        for item in data.get("findings", []) if isinstance(item, dict)
    ]
    payload = {"schema_version": BASELINE_SCHEMA, "timestamp": data.get("timestamp"), "entries": entries, "summary": data.get("summary", {})}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def apply_ratchet(data: dict[str, Any], baseline_path: Path | None) -> dict[str, Any]:
    baseline = load_baseline(baseline_path)
    findings = [item for item in data.get("findings", []) if isinstance(item, dict)]
    if baseline is None:
        data["ratchet"] = {"status": "missing-baseline", "baseline": str(baseline_path) if baseline_path else None, "baseline_findings": 0, "current_findings": len(findings), "new_findings": len(findings), "new_finding_ids": [f.get("finding_id") for f in findings]}
        return data
    known = {finding_identity(item) for item in baseline.get("entries", []) if isinstance(item, dict)}
    new = [f for f in findings if finding_identity(f) not in known]
    data["ratchet"] = {"status": "pass" if not new else "fail", "baseline": str(baseline_path), "baseline_findings": len(known), "current_findings": len(findings), "new_findings": len(new), "new_finding_ids": [f.get("finding_id") for f in new]}
    return data


def summarize(findings: list[Finding], files_scanned: int, tools: dict[str, Any]) -> dict[str, Any]:
    by_lane: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for finding in findings:
        by_lane[finding.lane] = by_lane.get(finding.lane, 0) + 1
        by_kind[finding.kind] = by_kind.get(finding.kind, 0) + 1
    return {"files_scanned": files_scanned, "findings": len(findings), "by_lane": dict(sorted(by_lane.items())), "by_kind": dict(sorted(by_kind.items())), "external_tools_present": sorted(name for name, row in tools.items() if row.get("present"))}


def audit_project(root: Path, include: list[str], exclude: list[str], min_tokens: int, shingle_size: int, threshold: float, run_external: bool, baseline: Path | None = None) -> dict[str, Any]:
    files = collect_files(root, include, exclude)
    findings = [*lexical_findings(root, files, min_tokens, shingle_size, threshold), *function_findings(root, files, min_tokens)]
    by_id: dict[str, Finding] = {}
    for finding in findings:
        by_id.setdefault(finding.finding_id, finding)
    findings = sorted(by_id.values(), key=lambda f: (f.lane, f.left, f.right))
    tools = external_tool_status(root, include, run_external)
    data: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": {"root": "<repo-root>"},
        "parameters": {"include": include, "exclude": exclude, "min_tokens": min_tokens, "shingle_size": shingle_size, "threshold": threshold, "run_external": run_external},
        "external_tools": tools,
        "summary": summarize(findings, len(files), tools),
        "findings": [asdict(f) | {"pair_key": f.pair_key} for f in findings],
    }
    if baseline:
        data = apply_ratchet(data, baseline)
    return data


def render_markdown(data: dict[str, Any]) -> str:
    summary = data["summary"]
    lines = [
        "# COS Quality Duplicates — Latest", "", f"Generated: `{data['timestamp']}`", "", "## Summary", "",
        f"- Files scanned: {summary['files_scanned']}", f"- Findings: {summary['findings']}",
        f"- By lane: `{json.dumps(summary['by_lane'], sort_keys=True)}`",
        f"- By kind: `{json.dumps(summary['by_kind'], sort_keys=True)}`",
        f"- External tools present: `{', '.join(summary['external_tools_present']) or 'none'}`",
    ]
    if isinstance(data.get("ratchet"), dict):
        r = data["ratchet"]
        lines.extend([f"- Ratchet status: `{r.get('status')}`", f"- New findings: {r.get('new_findings')}"])
    lines.extend(["", "## External Tool Roles", "", "| Tool | Present | Role |", "|---|---:|---|"])
    for name, row in sorted(data.get("external_tools", {}).items()):
        lines.append(f"| {name} | {row.get('present')} | {row.get('role')} |")
    lines.extend(["", "## Findings", "", "| Lane | Kind | Similarity | Left | Right | Recommendation |", "|---|---|---:|---|---|---|"])
    for finding in data.get("findings", [])[:100]:
        lines.append(f"| {finding['lane']} | {finding['kind']} | {finding['similarity']} | `{finding['left']}` | `{finding['right']}` | {finding['recommendation']} |")
    if not data.get("findings"):
        lines.append("| none | none | 0 |  |  |  |")
    return "\n".join(lines) + "\n"


def discover_registry(source: str | None = None, registry: Path | None = None) -> list[dict[str, Any]]:
    registry = registry or Path.home() / ".cognitive-os" / "installations.json"
    if not registry.exists():
        return []
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except Exception:
        return []
    rows = []
    for row in data.get("installations", []):
        if not isinstance(row, dict):
            continue
        if source and row.get("source") != source:
            continue
        path = row.get("path")
        if path:
            rows.append({"path": str(path), "project_name": row.get("project_name"), "source": row.get("source"), "discovery": "registry"})
    return rows


def discover_markers(root: Path, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in DEFAULT_EXCLUDE_PARTS]
        path = Path(current)
        if "cognitive-os.yaml" in files or (path / ".cognitive-os" / "install-meta.json").exists() or (path / ".cognitive-os" / "version").exists():
            rows.append({"path": str(path), "project_name": path.name, "source": None, "discovery": "marker-scan"})
            dirs[:] = []
        if len(rows) >= limit:
            break
    return rows


def fleet_report(source: str | None, scan_root: Path | None, registry: Path | None, show_paths: bool, limit: int) -> dict[str, Any]:
    registry_rows = discover_registry(source=source, registry=registry)
    marker_rows = discover_markers(scan_root, limit) if scan_root else []
    by_path: dict[str, dict[str, Any]] = {}
    for row in registry_rows + marker_rows:
        by_path.setdefault(row["path"], row)
        if by_path[row["path"]]["discovery"] != row["discovery"]:
            by_path[row["path"]]["discovery"] = "registry+marker-scan"
    projects = []
    for idx, row in enumerate(sorted(by_path.values(), key=lambda r: r["path"]), 1):
        p = Path(row["path"])
        projects.append({
            "project_id": f"project-{idx:03d}",
            "project_name": row.get("project_name") if show_paths else None,
            "path": str(p) if show_paths else None,
            "path_present": p.is_dir(),
            "discovery": row.get("discovery"),
            "has_cognitive_os_yaml": (p / "cognitive-os.yaml").exists(),
            "has_install_meta": (p / ".cognitive-os" / "install-meta.json").exists(),
        })
    return {"schema_version": "cos-quality-duplicates-fleet.v1", "timestamp": datetime.now(timezone.utc).isoformat(), "path_redacted": not show_paths, "project_count": len(projects), "projects": projects}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run COS portable duplicate-code scans")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--include", action="append", default=None)
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--min-tokens", type=int, default=80)
    parser.add_argument("--shingle-size", type=int, default=8)
    parser.add_argument("--threshold", type=float, default=0.82)
    parser.add_argument("--run-external", action="store_true", help="Run available external scanners in addition to COS fallback lanes")
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--fail-on-new", action="store_true")
    parser.add_argument("--fail-on-findings", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--json-out", default=str(DEFAULT_REPORT_DIR / "latest.json"))
    parser.add_argument("--markdown", default=str(DEFAULT_REPORT_DIR / "latest.md"))
    parser.add_argument("--fleet", action="store_true")
    parser.add_argument("--source", help="COS source path filter for fleet registry discovery")
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--scan-root", type=Path, help="Optional filesystem root for marker-scan fleet discovery")
    parser.add_argument("--show-paths", action="store_true")
    parser.add_argument("--limit", type=int, default=50)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.fleet:
        data = fleet_report(args.source, args.scan_root, args.registry, args.show_paths, args.limit)
        print(json.dumps(data, indent=2, sort_keys=True) if args.json else json.dumps(data, indent=2, sort_keys=True))
        return 0
    root = Path(args.project_root).resolve()
    include = args.include or list(DEFAULT_INCLUDE)
    baseline = root / args.baseline if args.baseline else None
    data = audit_project(root, include, args.exclude, args.min_tokens, args.shingle_size, args.threshold, args.run_external, baseline)
    if args.write_baseline and baseline:
        write_baseline(baseline, data)
        data = apply_ratchet(data, baseline)
    json_path = root / args.json_out
    md_path = root / args.markdown
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(data), encoding="utf-8")
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(json.dumps({"json": str(json_path), "markdown": str(md_path), "summary": data["summary"], "ratchet": data.get("ratchet")}, sort_keys=True))
    if args.fail_on_findings and data["summary"]["findings"]:
        return 1
    if args.fail_on_new and data.get("ratchet", {}).get("new_findings", 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
