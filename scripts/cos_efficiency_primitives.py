#!/usr/bin/env python3
# SCOPE: both
"""Cognitive OS efficiency operating-model primitives.

These commands implement the first portable slice of the efficiency roadmap:
status aggregation, adapter capability reporting, projection transaction planning,
skill registry indexing, context planning, role selection, testing capability
detection, TDD evidence verification, and review workload forecasting.

The implementation is intentionally harness-neutral and advisory by default. It
emits stable JSON receipts that stronger hooks/dispatchers can consume later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_PREFIX = "cos.efficiency"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".cs",
    ".swift",
    ".md",
    ".mdx",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".sh",
    ".sql",
    ".css",
    ".scss",
    ".html",
}
IGNORED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "target", "dist", "build", ".cognitive-os/external-source-cache"}


@dataclass
class CommandResult:
    command: list[str]
    exit_code: int
    stdout: str = ""
    stderr: str = ""


@dataclass
class AdapterCapability:
    adapter: str
    config_paths: list[str]
    native_hooks: bool
    lifecycle_events: list[str]
    subagents: bool
    mcp: bool
    projection_level: str
    proof_level: str
    detected: bool
    evidence: list[str] = field(default_factory=list)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root(start: Path) -> Path:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=start, text=True, stderr=subprocess.DEVNULL).strip()
        if out:
            return Path(out).resolve()
    except Exception:
        pass
    return start.resolve()


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def run_command(command: list[str], cwd: Path, timeout: int = 20) -> CommandResult:
    try:
        proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
        return CommandResult(command=command, exit_code=proc.returncode, stdout=proc.stdout[:4000], stderr=proc.stderr[:4000])
    except FileNotFoundError as exc:
        return CommandResult(command=command, exit_code=127, stderr=str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandResult(command=command, exit_code=124, stdout=(exc.stdout or "")[:4000] if isinstance(exc.stdout, str) else "", stderr=(exc.stderr or "")[:4000] if isinstance(exc.stderr, str) else "timeout")


def is_ignored(path: Path, root: Path) -> bool:
    parts = rel(path, root).split(os.sep)
    for i in range(len(parts)):
        joined = "/".join(parts[: i + 1])
        if joined in IGNORED_DIRS or parts[i] in IGNORED_DIRS:
            return True
    return False


def iter_files(root: Path, limit: int = 5000) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*"):
        if len(files) >= limit:
            break
        if p.is_dir():
            continue
        if is_ignored(p, root):
            continue
        files.append(p)
    return files


def git_changed_files(root: Path) -> list[Path]:
    result = run_command(["git", "diff", "--name-only", "HEAD"], root)
    names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    result_untracked = run_command(["git", "ls-files", "--others", "--exclude-standard"], root)
    names.extend(line.strip() for line in result_untracked.stdout.splitlines() if line.strip())
    seen: set[str] = set()
    out: list[Path] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        p = root / name
        if p.exists() and p.is_file() and not is_ignored(p, root):
            out.append(p)
    return out


def file_lines(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    except Exception:
        return 0


def adapter_capabilities(root: Path) -> list[AdapterCapability]:
    candidates = [
        AdapterCapability("claude-code", [".claude/settings.json", ".claude/settings.local.json"], True, ["SessionStart", "PreToolUse", "PostToolUse", "Stop"], True, True, "driver-projected", "runtime-smoked-if-settings-present", False),
        AdapterCapability("codex", [".codex/config.toml", ".codex/hooks.json", ".codex/skills"], True, ["SessionStart", "PreToolUse", "PostToolUse", "Stop"], True, True, "driver-projected", "runtime-smoked-if-hooks-present", False),
        AdapterCapability("opencode", ["opencode.json", ".opencode/config.json", ".opencode/hooks.json"], True, ["session.start", "tool.before", "tool.after", "session.idle"], True, True, "driver-projected", "structural-plus-smoke", False),
        AdapterCapability("cursor", [".cursor", ".cursor/rules"], False, [], False, False, "structural", "documentation-only-unless-adapter-smoked", False),
        AdapterCapability("windsurf", [".windsurf", ".windsurfrules"], False, [], False, False, "structural", "documentation-only-unless-adapter-smoked", False),
        AdapterCapability("generic", ["AGENTS.md", ".cognitive-os"], False, [], False, False, "structural", "portable-filesystem-contract", False),
    ]
    for item in candidates:
        evidence = []
        for config_path in item.config_paths:
            if (root / config_path).exists():
                evidence.append(config_path)
        item.detected = bool(evidence)
        item.evidence = evidence
    return candidates


def command_adapter_capabilities(args: argparse.Namespace) -> int:
    root = repo_root(Path(args.project_dir).resolve())
    payload = {
        "schema": f"{SCHEMA_PREFIX}.adapter-capabilities.v1",
        "project_root": str(root),
        "generated_at": utc_now(),
        "adapters": [asdict(a) for a in adapter_capabilities(root)],
    }
    emit(payload, args.json)
    return 0


def read_skill_frontmatter(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return data
    if not text.startswith("---"):
        first = text.splitlines()[0] if text.splitlines() else path.parent.name
        return {"name": path.parent.name, "description": first.lstrip("# ").strip()}
    lines = text.splitlines()[1:]
    for line in lines:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"\'')
        data[key.strip()] = value
    data.setdefault("name", path.parent.name)
    return data


def find_skill_files(root: Path) -> list[Path]:
    sources = [root / "skills", root / ".cognitive-os" / "skills", root / ".claude" / "skills"]
    home = Path.home()
    sources.extend([home / ".agents" / "skills", home / ".codex" / "skills"])
    files: list[Path] = []
    seen: set[Path] = set()
    for source in sources:
        if not source.exists():
            continue
        for skill in source.rglob("SKILL.md"):
            if skill in seen:
                continue
            seen.add(skill)
            files.append(skill)
    return files


def skill_registry(root: Path) -> dict[str, Any]:
    entries = []
    for skill in find_skill_files(root):
        meta = read_skill_frontmatter(skill)
        source = "project" if root in skill.resolve().parents else "user"
        entries.append(
            {
                "name": meta.get("name") or skill.parent.name,
                "path": rel(skill, root) if source == "project" else str(skill),
                "source": source,
                "description": meta.get("description", ""),
                "triggers": meta.get("triggers", ""),
            }
        )
    entries.sort(key=lambda e: (0 if e["source"] == "project" else 1, e["name"], e["path"]))
    fingerprint = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
    return {"schema": f"{SCHEMA_PREFIX}.skill-registry.v1", "project_root": str(root), "generated_at": utc_now(), "fingerprint": fingerprint, "skill_count": len(entries), "entries": entries}


def command_skill_registry_refresh(args: argparse.Namespace) -> int:
    root = repo_root(Path(args.project_dir).resolve())
    payload = skill_registry(root)
    output = Path(args.output) if args.output else root / ".cognitive-os" / "skill-registry.md"
    cache = output.parent / ".skill-registry.cache.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Cognitive OS Skill Registry", "", f"Generated: {payload['generated_at']}", f"Fingerprint: `{payload['fingerprint']}`", "", "| Skill | Source | Path | Description |", "|---|---|---|---|"]
    for e in payload["entries"]:
        desc = str(e.get("description") or "").replace("|", "\\|")
        lines.append(f"| `{e['name']}` | {e['source']} | `{e['path']}` | {desc} |")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cache.write_text(json.dumps({"fingerprint": payload["fingerprint"], "skill_count": payload["skill_count"], "updated_at": payload["generated_at"]}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    payload["registry_path"] = str(output)
    payload["cache_path"] = str(cache)
    emit(payload, args.json)
    return 0


def detect_testing_capabilities(root: Path) -> dict[str, Any]:
    caps: list[dict[str, Any]] = []
    def add(stack: str, runner: str, command: str, evidence: str, layer: str = "unit") -> None:
        caps.append({"stack": stack, "runner": runner, "command": command, "evidence": evidence, "layer": layer})
    if (root / "package.json").exists():
        try:
            pkg = json.loads((root / "package.json").read_text())
            scripts = pkg.get("scripts") or {}
            for name in ("test", "test:unit", "test:ci", "lint", "typecheck"):
                if name in scripts:
                    add("node", name, f"npm run {name}", "package.json", "quality" if name in {"lint", "typecheck"} else "unit")
        except Exception:
            add("node", "npm", "npm test", "package.json")
    if any((root / name).exists() for name in ("pytest.ini", "pyproject.toml", "requirements.txt")) or (root / "tests").exists():
        if (root / "tests").exists():
            add("python", "pytest", "python -m pytest", "tests/")
        if (root / "pyproject.toml").exists():
            text = (root / "pyproject.toml").read_text(errors="ignore")
            if "ruff" in text:
                add("python", "ruff", "ruff check .", "pyproject.toml", "quality")
            if "mypy" in text:
                add("python", "mypy", "mypy .", "pyproject.toml", "quality")
    if (root / "go.mod").exists():
        add("go", "go test", "go test ./...", "go.mod")
    if (root / "Cargo.toml").exists():
        add("rust", "cargo test", "cargo test", "Cargo.toml")
        add("rust", "cargo clippy", "cargo clippy --all-targets", "Cargo.toml", "quality")
    if (root / "pom.xml").exists():
        add("java", "maven", "mvn test", "pom.xml")
    if (root / "build.gradle").exists() or (root / "build.gradle.kts").exists():
        add("java", "gradle", "./gradlew test", "build.gradle")
    return {"schema": f"{SCHEMA_PREFIX}.testing-capabilities.v1", "project_root": str(root), "generated_at": utc_now(), "strict_tdd_supported": any(c["layer"] == "unit" for c in caps), "capabilities": caps}


def command_testing_capabilities(args: argparse.Namespace) -> int:
    root = repo_root(Path(args.project_dir).resolve())
    emit(detect_testing_capabilities(root), args.json)
    return 0


def context_plan(root: Path, goal: str) -> dict[str, Any]:
    changed = git_changed_files(root)
    scored: list[dict[str, Any]] = []
    goal_terms = {t.lower() for t in re.findall(r"[A-Za-z0-9_/-]{3,}", goal)}
    candidates = changed or [p for p in iter_files(root, 2000) if p.suffix in TEXT_EXTENSIONS]
    for p in candidates[:1000]:
        if p.suffix not in TEXT_EXTENSIONS:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")[:20000]
        words = set(re.findall(r"[A-Za-z0-9_/-]{3,}", text.lower()))
        overlap = len(goal_terms & words)
        score = overlap * 5 + (20 if p in changed else 0) + min(file_lines(p), 400) / 100
        if score > 0 or p in changed:
            scored.append({"path": rel(p, root), "lines": file_lines(p), "score": round(score, 2), "reasons": [*( ["changed"] if p in changed else []), *( ["goal-term-overlap"] if overlap else [])]})
    scored.sort(key=lambda e: (-e["score"], e["path"]))
    selected = scored[: int(os.environ.get("COS_CONTEXT_PLAN_LIMIT", "20"))]
    return {"schema": f"{SCHEMA_PREFIX}.context-plan.v1", "project_root": str(root), "generated_at": utc_now(), "goal": goal, "changed_files": [rel(p, root) for p in changed], "selected_files": selected, "estimated_context_lines": sum(int(e["lines"]) for e in selected), "advisory": "Inspect selected files before broad reads; Graphify/query-tailored context can refine this plan when available."}


def command_context_plan(args: argparse.Namespace) -> int:
    root = repo_root(Path(args.project_dir).resolve())
    emit(context_plan(root, args.goal or ""), args.json)
    return 0


def role_selection(root: Path, goal: str) -> dict[str, Any]:
    changed = git_changed_files(root)
    caps = detect_testing_capabilities(root)
    roles: list[dict[str, Any]] = []
    def role(name: str, reason: str, tools: list[str], budget: dict[str, Any]) -> None:
        roles.append({"role": name, "reason": reason, "allowed_tools": tools, "budget": budget})
    role("planner", "establish work contract, acceptance criteria, and context plan", ["read", "search", "status"], {"max_context_lines": 1200, "max_tool_calls": 12})
    if len(changed) > 3 or any(tok in goal.lower() for tok in ("refactor", "feature", "migrate", "implement", "crear", "agregar")):
        role("implementer", "code changes expected from task shape", ["read", "edit", "test"], {"max_context_lines": 2500, "max_tool_calls": 35})
    if caps["strict_tdd_supported"] or any(tok in goal.lower() for tok in ("test", "tdd", "quality", "bug", "fix")):
        role("tester", "test capability or quality/fix intent detected", ["read", "test"], {"max_context_lines": 1500, "max_tool_calls": 20})
    if len(changed) > 1 or any(tok in goal.lower() for tok in ("review", "release", "seguridad", "risk")):
        role("reviewer", "multi-file or review/risk intent detected", ["read", "diff", "test"], {"max_context_lines": 2000, "max_tool_calls": 20})
    if any(tok in goal.lower() for tok in ("release", "push", "deploy")):
        role("release-checker", "release/deploy intent detected", ["status", "test", "git"], {"max_context_lines": 1000, "max_tool_calls": 15})
    return {"schema": f"{SCHEMA_PREFIX}.role-selection.v1", "project_root": str(root), "generated_at": utc_now(), "goal": goal, "changed_file_count": len(changed), "roles": roles, "stop_conditions": ["verification fails", "budget exceeded", "blocking review finding", "unclear source/goal"]}


def command_role_selection(args: argparse.Namespace) -> int:
    root = repo_root(Path(args.project_dir).resolve())
    emit(role_selection(root, args.goal or ""), args.json)
    return 0


def review_workload(root: Path) -> dict[str, Any]:
    changed = git_changed_files(root)
    stat = run_command(["git", "diff", "--numstat", "HEAD"], root)
    added = removed = 0
    for line in stat.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            if parts[0].isdigit():
                added += int(parts[0])
            if parts[1].isdigit():
                removed += int(parts[1])
    risk = "low"
    if len(changed) > 12 or added + removed > 800:
        risk = "high"
    elif len(changed) > 5 or added + removed > 300:
        risk = "medium"
    recommendations = []
    if risk == "high":
        recommendations.append("split into chained review/process-loop slices before apply")
    elif risk == "medium":
        recommendations.append("run fresh review and targeted tests before final verdict")
    else:
        recommendations.append("single review lane is likely sufficient")
    return {"schema": f"{SCHEMA_PREFIX}.review-workload.v1", "project_root": str(root), "generated_at": utc_now(), "changed_files": [rel(p, root) for p in changed], "changed_file_count": len(changed), "added_lines": added, "removed_lines": removed, "risk": risk, "recommendations": recommendations}


def command_review_workload(args: argparse.Namespace) -> int:
    root = repo_root(Path(args.project_dir).resolve())
    emit(review_workload(root), args.json)
    return 0


def tdd_evidence_verify(root: Path, evidence_path: Path | None) -> dict[str, Any]:
    caps = detect_testing_capabilities(root)
    evidence_text = ""
    if evidence_path and evidence_path.exists():
        evidence_text = evidence_path.read_text(encoding="utf-8", errors="ignore")
    markers = {
        "red": bool(re.search(r"\bRED\b|failing test|test fall", evidence_text, re.I)),
        "green": bool(re.search(r"\bGREEN\b|passing test|tests? pass", evidence_text, re.I)),
        "triangulate": bool(re.search(r"TRIANGULATE|second case|segundo caso", evidence_text, re.I)),
        "refactor": bool(re.search(r"REFACTOR|refactor", evidence_text, re.I)),
        "safety_net": bool(re.search(r"baseline|safety net|existing tests", evidence_text, re.I)),
    }
    test_files = [rel(p, root) for p in iter_files(root, 2000) if ("test" in p.name.lower() or "spec" in p.name.lower()) and p.suffix in TEXT_EXTENSIONS]
    required = caps["strict_tdd_supported"]
    passed = (not required) or (all(markers.values()) and bool(test_files))
    blockers = [] if passed else [name for name, ok in markers.items() if not ok]
    if required and not test_files:
        blockers.append("no-test-files-detected")
    return {"schema": f"{SCHEMA_PREFIX}.tdd-evidence.v1", "project_root": str(root), "generated_at": utc_now(), "strict_tdd_required": required, "passed": passed, "markers": markers, "test_files": test_files[:50], "blockers": blockers, "capabilities": caps["capabilities"]}


def command_tdd_evidence_verify(args: argparse.Namespace) -> int:
    root = repo_root(Path(args.project_dir).resolve())
    payload = tdd_evidence_verify(root, Path(args.evidence).resolve() if args.evidence else None)
    emit(payload, args.json)
    return 0 if payload["passed"] else 2


def projection_transaction(root: Path, paths: list[str], apply: bool) -> dict[str, Any]:
    receipts = []
    backup_root = root / ".cognitive-os" / "projection-transactions" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for raw in paths:
        p = (root / raw).resolve()
        item = {"path": rel(p, root), "exists": p.exists(), "backup": None, "status": "planned"}
        if apply and p.exists() and p.is_file():
            backup = backup_root / rel(p, root)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, backup)
            item["backup"] = str(backup)
            item["status"] = "backed-up"
        receipts.append(item)
    return {"schema": f"{SCHEMA_PREFIX}.projection-transaction.v1", "project_root": str(root), "generated_at": utc_now(), "mode": "apply" if apply else "plan", "backup_root": str(backup_root) if apply else None, "receipts": receipts, "rollback_hint": "restore files from backup_root and rerun projection postcheck"}


def command_projection_transaction(args: argparse.Namespace) -> int:
    root = repo_root(Path(args.project_dir).resolve())
    emit(projection_transaction(root, args.path or [], args.apply), args.json)
    return 0


def status(root: Path, goal: str) -> dict[str, Any]:
    adapters = adapter_capabilities(root)
    skills = skill_registry(root)
    caps = detect_testing_capabilities(root)
    workload = review_workload(root)
    ctx = context_plan(root, goal)
    roles = role_selection(root, goal)
    next_action = "context-plan"
    blockers: list[str] = []
    if not any(a.detected for a in adapters):
        blockers.append("no-adapter-detected")
    if skills["skill_count"] == 0:
        blockers.append("no-skills-detected")
    if workload["risk"] == "high":
        next_action = "split-workload"
    elif caps["strict_tdd_supported"]:
        next_action = "record-tdd-evidence"
    elif ctx["selected_files"]:
        next_action = "inspect-selected-context"
    return {"schema": f"{SCHEMA_PREFIX}.status.v1", "project_root": str(root), "generated_at": utc_now(), "goal": goal, "next_recommended": next_action, "blockers": blockers, "summary": {"detected_adapters": [a.adapter for a in adapters if a.detected], "skill_count": skills["skill_count"], "strict_tdd_supported": caps["strict_tdd_supported"], "review_risk": workload["risk"], "selected_context_files": len(ctx["selected_files"]), "roles": [r["role"] for r in roles["roles"]]}, "paths": {"skill_registry_default": str(root / ".cognitive-os" / "skill-registry.md")}}


def command_status(args: argparse.Namespace) -> int:
    root = repo_root(Path(args.project_dir).resolve())
    emit(status(root, args.goal or ""), args.json)
    return 0


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(f"schema: {payload.get('schema')}")
    if "next_recommended" in payload:
        print(f"next: {payload['next_recommended']}")
    if "summary" in payload:
        for key, value in payload["summary"].items():
            print(f"{key}: {value}")
    elif "skill_count" in payload:
        print(f"skills: {payload['skill_count']}")
        print(f"registry: {payload.get('registry_path', '')}")
    elif "capabilities" in payload:
        print(f"capabilities: {len(payload['capabilities'])}")
        print(f"strict_tdd_supported: {payload.get('strict_tdd_supported')}")
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cognitive OS efficiency operating-model primitives")
    sub = parser.add_subparsers(dest="command", required=True)
    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project-dir", default=os.getcwd())
        p.add_argument("--json", action="store_true")
    p = sub.add_parser("status")
    common(p); p.add_argument("--goal", default=""); p.set_defaults(func=command_status)
    p = sub.add_parser("adapter-capabilities")
    common(p); p.set_defaults(func=command_adapter_capabilities)
    p = sub.add_parser("projection-transaction")
    common(p); p.add_argument("--path", action="append"); p.add_argument("--apply", action="store_true"); p.set_defaults(func=command_projection_transaction)
    p = sub.add_parser("skill-registry-refresh")
    common(p); p.add_argument("--output"); p.set_defaults(func=command_skill_registry_refresh)
    p = sub.add_parser("context-plan")
    common(p); p.add_argument("--goal", default=""); p.set_defaults(func=command_context_plan)
    p = sub.add_parser("role-selection-report")
    common(p); p.add_argument("--goal", default=""); p.set_defaults(func=command_role_selection)
    p = sub.add_parser("testing-capabilities")
    common(p); p.set_defaults(func=command_testing_capabilities)
    p = sub.add_parser("tdd-evidence-verify")
    common(p); p.add_argument("--evidence"); p.set_defaults(func=command_tdd_evidence_verify)
    p = sub.add_parser("review-workload-forecast")
    common(p); p.set_defaults(func=command_review_workload)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
