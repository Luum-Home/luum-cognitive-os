#!/usr/bin/env python3
# SCOPE: os-only
"""Audit primitive read/write authority contracts.

Static pass: classify script authority from explicit manifest rows and existing
scope/projection/readiness metadata, then detect obvious file-write surfaces.
Dynamic pass: run a small set of safe smokes in temporary workspaces and verify
filesystem deltas stay inside declared surfaces.
"""
from __future__ import annotations
import os as _cos_os
import sys as _cos_sys
_cos_sys.path.insert(0, _cos_os.path.dirname(_cos_os.path.dirname(__file__)))
from lib.script_helpers import read_yaml_dict as read_yaml
from lib.script_helpers import read_json_dict as read_json
from lib.project_paths import relpath as rel

import argparse
import ast
import fnmatch
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "primitive-authority-audit.v1"
DEFAULT_MANIFEST = Path("manifests/primitive-authority.yaml")
DEFAULT_JSON = Path("docs/06-Daily/reports/primitive-authority-latest.json")
DEFAULT_MD = Path("docs/06-Daily/reports/primitive-authority-latest.md")
VALID_MODES = {
    "observe-only",
    "propose-only",
    "project-local-write",
    "os-maintainer-write",
    "profile-projection-write",
    "dangerous-human-approved",
}
LIVE_SURFACES = {"os_live_primitives", "consumer_source", "secrets", "user_global_config"}
WRITE_ATTRS = {"write_text", "write_bytes", "mkdir", "touch", "unlink", "symlink_to", "rename", "replace"}
WRITE_FUNCS = {"open", "copy2", "copy", "copyfile", "copytree", "rmtree", "move", "remove", "unlink", "makedirs"}
SHELL_MUTATING_CMD_RE = re.compile(r"(^|[;&|]\s*)(cp|mv|rm|rsync|tee|ln)\b")
SHELL_REDIRECT_RE = re.compile(r"(?<![0-9&])>{1,2}\s*(?P<target>[^\s;&|]+)")
PATH_LITERAL_RE = re.compile(r"(?P<path>(?:\.?/?(?:hooks|rules|skills|scripts|templates|manifests|\.claude|\.codex|\.cursor|\.cognitive-os|docs/06-Daily/reports|docs/03-PoCs/proposals|\.github/workflows|secrets|src|lib|app|packages|internal|cmd)/)[A-Za-z0-9_./{}@:+,=-]+|\.env(?:\.[A-Za-z0-9_-]+)?)")


@dataclass
class WriteHit:
    path: str
    operation: str
    surface: str
    line: int
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


@dataclass
class AuditRow:
    path: str
    scope: str
    role: str
    consumer_accessibility: str
    authority_mode: str
    authority_source: str
    detected_write_surfaces: list[str] = field(default_factory=list)
    writes: list[WriteHit] = field(default_factory=list)
    status: str = "pass"
    findings: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = self.__dict__.copy()
        payload["writes"] = [hit.to_dict() for hit in self.writes]
        return payload


def script_files(root: Path) -> list[Path]:
    base = root / "scripts"
    if not base.exists():
        return []
    out = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts:
            continue
        if path.suffix in {"", ".py", ".sh", ".js", ".mjs"}:
            out.append(path)
    return sorted(out)


def header_scope(path: Path) -> str | None:
    try:
        header = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:8])
    except OSError:
        return None
    match = re.search(r"\bSCOPE:\s*([A-Za-z0-9_-]+)", header)
    return match.group(1) if match else None


def load_scope_overrides(root: Path) -> list[dict[str, str]]:
    data = read_yaml(root / "manifests" / "primitive-scope-overrides.yaml")
    return [dict(item) for item in data.get("rules", []) if item.get("pattern") and item.get("scope")]


def scope_for(root: Path, relpath: str, overrides: list[dict[str, str]]) -> str:
    path = root / relpath
    scoped = header_scope(path)
    if scoped:
        return scoped
    for item in overrides:
        if fnmatch.fnmatch(relpath, str(item["pattern"])):
            return str(item["scope"])
    return "os-only"


def readiness_by_path(root: Path) -> dict[str, dict[str, Any]]:
    data = read_json(root / "docs" / "06-Daily" / "reports" / "primitive-readiness-ledger-scripts-latest.json")
    rows = data.get("scripts", []) if isinstance(data, dict) else []
    return {str(row.get("path")): row for row in rows if row.get("path")}


def manifest_entries(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["path"]): item for item in manifest.get("entries", []) if item.get("path")}


def shell_ci_commands(root: Path) -> set[str]:
    data = read_yaml(root / "manifests" / "shell-ci-projection.yaml")
    return {str(item["path"]) for item in data.get("commands", []) if item.get("path")}


def profile_driver_scripts(root: Path) -> set[str]:
    data = read_yaml(root / "manifests" / "primitive-projection-profiles.yaml")
    return {str(item["path"]) for item in data.get("profile_driver_scripts", []) if item.get("path")}


def derive_authority(path: str, scope: str, row: dict[str, Any], manifest_entry: dict[str, Any] | None, shell_ci: set[str], profile_drivers: set[str]) -> tuple[str, str]:
    if manifest_entry:
        mode = str((manifest_entry.get("authority") or {}).get("mode") or "")
        if mode in VALID_MODES:
            return mode, "explicit"
    if "consumer-improvement-proposals" in path or path.endswith("cos_consumer_improvement_proposals.py"):
        return "propose-only", "derived:consumer-improvement-proposals"
    if path in shell_ci:
        return "profile-projection-write", "derived:shell-ci-command"
    if path in profile_drivers:
        return "profile-projection-write", "derived:profile-driver"
    if row.get("consumer_accessibility") == "install-profile-managed":
        return "profile-projection-write", "derived:install-profile-managed"
    if scope == "os-only":
        return "os-maintainer-write", "derived:os-only-default"
    if scope in {"project", "both"}:
        return "observe-only", "derived:shared-default"
    return "observe-only", "derived:fallback"


def classify_surface(path: str) -> str:
    normalized = path[2:] if path.startswith("./") else path
    if normalized.startswith((".cognitive-os/improvements/proposals/", "docs/03-PoCs/proposals/")):
        return "os_review_artifacts"
    if normalized.startswith(("docs/06-Daily/reports/", ".cognitive-os/reports/")):
        return "reports"
    if normalized.startswith(".cognitive-os/metrics/"):
        return "metrics"
    if normalized.startswith((".env", "secrets/")) or normalized.endswith((".pem", ".key")):
        return "secrets"
    if normalized.startswith(("hooks/", "rules/", "skills/", "scripts/", "templates/", "manifests/", ".claude/", ".codex/", ".cursor/")):
        return "os_live_primitives"
    if normalized.startswith(("src/", "lib/", "app/", "packages/", "internal/", "cmd/")):
        return "consumer_source"
    if normalized.startswith((".cognitive-os/", ".github/workflows/", ".vscode/", ".qwen/", ".kimi/", ".gemini/")):
        return "projection_roots"
    return "unknown"


def literal(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("{}")
        return "".join(parts)
    if isinstance(node, ast.Call):
        # Common pattern: Path("target").write_text(...)
        if isinstance(node.func, ast.Name) and node.func.id in {"Path", "PurePath"} and node.args:
            return literal(node.args[0])
        if isinstance(node.func, ast.Attribute) and node.func.attr in {"Path", "PurePath"} and node.args:
            return literal(node.args[0])
    return None


def ast_write_hits(path: Path) -> list[WriteHit]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text, filename=str(path))
    except (OSError, SyntaxError):
        return []
    hits: list[WriteHit] = []
    lines = text.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        opname = ""
        target_value: str | None = None
        if isinstance(node.func, ast.Attribute) and node.func.attr in WRITE_ATTRS:
            opname = node.func.attr
            target_value = literal(node.func.value) or (literal(node.args[0]) if node.args else None)
        elif isinstance(node.func, ast.Name) and node.func.id in WRITE_FUNCS:
            opname = node.func.id
            target_value = literal(node.args[0]) if node.args else None
            if opname == "open" and len(node.args) > 1:
                mode = literal(node.args[1]) or ""
                if not any(flag in mode for flag in "wax+"):
                    continue
        elif isinstance(node.func, ast.Attribute) and node.func.attr in WRITE_FUNCS:
            opname = node.func.attr
            target_value = literal(node.args[0]) if node.args else None
        if not opname or not target_value:
            continue
        surface = classify_surface(target_value)
        if surface == "unknown" and not PATH_LITERAL_RE.search(target_value):
            continue
        hits.append(WriteHit(target_value, opname, surface, int(getattr(node, "lineno", 0)), lines[getattr(node, "lineno", 1) - 1].strip() if lines else ""))
    return hits


def shell_write_hits(path: Path) -> list[WriteHit]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    hits: list[WriteHit] = []
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if SHELL_MUTATING_CMD_RE.search(stripped):
            for match in PATH_LITERAL_RE.finditer(stripped):
                target = match.group("path")
                hits.append(WriteHit(target, "shell-write", classify_surface(target), idx, stripped))
        for redir in SHELL_REDIRECT_RE.finditer(stripped):
            target = redir.group("target").strip('"\'')
            if target in {"/dev/null", "&1", "&2"} or target.startswith("&"):
                continue
            surface = classify_surface(target)
            if surface != "unknown" or PATH_LITERAL_RE.search(target):
                hits.append(WriteHit(target, "shell-redirection", surface, idx, stripped))
    return hits


def detect_writes(path: Path) -> list[WriteHit]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".py" or text.startswith("#!/usr/bin/env python"):
        return ast_write_hits(path)
    return shell_write_hits(path)


def evaluate_row(row: AuditRow) -> None:
    surfaces = sorted({hit.surface for hit in row.writes})
    row.detected_write_surfaces = surfaces
    findings: list[dict[str, Any]] = []
    if row.authority_mode == "propose-only" and any(hit.surface in {"os_live_primitives", "consumer_source", "secrets"} for hit in row.writes):
        findings.append({"severity": "block", "code": "propose-only-live-write", "reason": "propose-only primitive writes forbidden live/runtime surface"})
    if row.authority_mode == "observe-only" and any(hit.surface in LIVE_SURFACES for hit in row.writes):
        findings.append({"severity": "block", "code": "observe-only-live-write", "reason": "observe-only primitive writes live/runtime surface"})
    if row.scope in {"project", "both"} and row.authority_mode == "os-maintainer-write":
        findings.append({"severity": "block", "code": "project-shared-os-maintainer-write", "reason": "project/both primitive derived maintainer write authority"})
    if row.authority_mode == "profile-projection-write" and any(hit.surface == "secrets" for hit in row.writes):
        findings.append({"severity": "block", "code": "profile-projection-secret-write", "reason": "profile projection writes secret surface"})
    row.findings = findings
    if any(f["severity"] == "block" for f in findings):
        row.status = "block"
    elif row.writes:
        row.status = "warn"
    else:
        row.status = "pass"


def static_audit(root: Path, manifest: dict[str, Any]) -> list[AuditRow]:
    overrides = load_scope_overrides(root)
    readiness = readiness_by_path(root)
    entries = manifest_entries(manifest)
    shell_ci = shell_ci_commands(root)
    profile_drivers = profile_driver_scripts(root)
    rows: list[AuditRow] = []
    for script in script_files(root):
        rpath = rel(root, script)
        scope = scope_for(root, rpath, overrides)
        ready = readiness.get(rpath, {})
        mode, source = derive_authority(rpath, scope, ready, entries.get(rpath), shell_ci, profile_drivers)
        row = AuditRow(
            path=rpath,
            scope=scope,
            role=str(ready.get("role") or "unknown"),
            consumer_accessibility=str(ready.get("consumer_accessibility") or "unknown"),
            authority_mode=mode,
            authority_source=source,
            writes=detect_writes(script),
        )
        evaluate_row(row)
        rows.append(row)
    return rows


def snapshot(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not root.exists():
        return out
    for path in root.rglob("*"):
        if path.is_file() or path.is_symlink():
            try:
                stat = path.lstat()
            except OSError:
                continue
            out[rel(root, path)] = f"{stat.st_mode}:{stat.st_size}:{stat.st_mtime_ns}"
    return out


def delta(before: dict[str, str], after: dict[str, str]) -> list[str]:
    keys = set(before) | set(after)
    return sorted(key for key in keys if before.get(key) != after.get(key))


def allowed(path: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in globs)


def dynamic_smokes(root: Path) -> list[dict[str, Any]]:
    smokes: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="cos-authority-smoke-") as td:
        base = Path(td)
        # Consumer improvement export/import.
        consumer = base / "consumer"
        (consumer / ".cognitive-os" / "metrics").mkdir(parents=True)
        (consumer / ".cognitive-os" / "metrics" / "skill-feedback.jsonl").write_text('{"skill":"demo","success":false}\n' * 3, encoding="utf-8")
        before = snapshot(consumer)
        bundle = base / "bundle.json"
        cmd = [sys.executable, str(root / "scripts" / "cos_consumer_improvement_proposals.py"), "export", "--project-dir", str(consumer), "--project", "demo", "--output", str(bundle)]
        proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True, check=False, timeout=30)
        changed = delta(before, snapshot(consumer))
        smokes.append({"id": "consumer-improvement-export", "returncode": proc.returncode, "changed_paths": changed, "status": "pass" if proc.returncode == 0 and not changed and bundle.exists() else "block"})
        before = snapshot(consumer)
        cmd = [sys.executable, str(root / "scripts" / "cos_consumer_improvement_proposals.py"), "import", "--project-dir", str(consumer), str(bundle)]
        proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True, check=False, timeout=30)
        changed = delta(before, snapshot(consumer))
        bad = [p for p in changed if not allowed(p, [".cognitive-os/improvements/proposals/**"])]
        smokes.append({"id": "consumer-improvement-import", "returncode": proc.returncode, "changed_paths": changed, "unexpected_paths": bad, "status": "pass" if proc.returncode == 0 and not bad else "block"})

        # Shell/CI projection.
        proj = base / "shellci"
        proj.mkdir()
        before = snapshot(proj)
        cmd = [sys.executable, str(root / "scripts" / "project_shell_ci.py"), "--project-dir", str(proj), "--profile", "default", "--json"]
        proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True, check=False, timeout=30)
        changed = delta(before, snapshot(proj))
        bad = [p for p in changed if not allowed(p, [".cognitive-os/scripts/cos/**", ".cognitive-os/shell-ci-projection.json", "scripts/*", ".github/workflows/**"])]
        smokes.append({"id": "project-shell-ci", "returncode": proc.returncode, "changed_paths": changed, "unexpected_paths": bad, "status": "pass" if proc.returncode == 0 and not bad else "block"})

        # cos_init projection.
        init = base / "init"
        init.mkdir()
        before = snapshot(init)
        env = {**os.environ, "COS_REGISTRY_FILE": str(base / "registry.json")}
        cmd = [sys.executable, str(root / "scripts" / "cos_init.py"), "--default", "--harness", "codex"]
        proc = subprocess.run(cmd, cwd=init, env=env, text=True, capture_output=True, check=False, timeout=60)
        changed = delta(before, snapshot(init))
        bad = [p for p in changed if not allowed(p, [".cognitive-os/**", ".codex/**", ".gitignore", "cognitive-os.yaml"])]
        smokes.append({"id": "cos-init-codex", "returncode": proc.returncode, "changed_paths": changed[:80], "changed_count": len(changed), "unexpected_paths": bad[:40], "status": "pass" if proc.returncode == 0 and not bad else "block"})
    return smokes


def summarize(rows: list[AuditRow], smokes: list[dict[str, Any]]) -> dict[str, Any]:
    by_mode: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for row in rows:
        by_mode[row.authority_mode] = by_mode.get(row.authority_mode, 0) + 1
        by_status[row.status] = by_status.get(row.status, 0) + 1
    blocks = sum(1 for row in rows if row.status == "block") + sum(1 for smoke in smokes if smoke.get("status") == "block")
    return {
        "total_scripts": len(rows),
        "by_mode": dict(sorted(by_mode.items())),
        "by_status": dict(sorted(by_status.items())),
        "dynamic_smokes": len(smokes),
        "dynamic_blocks": sum(1 for smoke in smokes if smoke.get("status") == "block"),
        "block_count": blocks,
    }


def build_report(root: Path, manifest_path: Path, include_dynamic: bool = True) -> dict[str, Any]:
    manifest = read_yaml(manifest_path)
    rows = static_audit(root, manifest)
    smokes = dynamic_smokes(root) if include_dynamic else []
    summary = summarize(rows, smokes)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "block" if summary["block_count"] else "pass",
        "manifest": rel(root, manifest_path),
        "summary": summary,
        "items": [row.to_dict() for row in rows],
        "dynamic_smokes": smokes,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Primitive Authority Audit — Latest",
        "",
        f"Generated: {report['generated_at']}",
        f"Status: `{report['status']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: `{value}`")
    lines += ["", "## Blocking findings", "", "| Path | Mode | Scope | Surfaces | Findings |", "|---|---|---|---|---|"]
    blockers = [row for row in report["items"] if row["status"] == "block"]
    if not blockers:
        lines.append("| none | - | - | - | - |")
    for row in blockers[:80]:
        lines.append(f"| `{row['path']}` | `{row['authority_mode']}` | `{row['scope']}` | `{', '.join(row['detected_write_surfaces'])}` | `{json.dumps(row['findings'], sort_keys=True)[:240]}` |")
    lines += ["", "## Dynamic smokes", "", "| Smoke | Status | Changed paths | Unexpected paths |", "|---|---|---:|---|"]
    for smoke in report.get("dynamic_smokes", []):
        lines.append(f"| `{smoke['id']}` | `{smoke['status']}` | {smoke.get('changed_count', len(smoke.get('changed_paths', [])))} | `{', '.join(smoke.get('unexpected_paths', []))}` |")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=str(ROOT))
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--static-only", action="store_true")
    parser.add_argument("--fail-on-block", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).resolve()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    report = build_report(root, manifest_path, include_dynamic=not args.static_only)
    if not args.no_write:
        (root / DEFAULT_JSON).parent.mkdir(parents=True, exist_ok=True)
        (root / DEFAULT_JSON).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (root / DEFAULT_MD).write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps({"status": report["status"], "summary": report["summary"]}, sort_keys=True))
    return 1 if args.fail_on_block and report["status"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
