#!/usr/bin/env python3
# SCOPE: both
"""Portable lean-governance and skill-optimization primitives for Cognitive OS.

The lean primitives review code for avoidable complexity. The skill optimization
primitives treat SKILL.md files as staged, validation-gated artifacts: proposed
edits are written to .cognitive-os first, accepted only by an explicit gate, and
adopted only by a separate command with backups.
"""
from __future__ import annotations

import argparse
import difflib
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

LEAN_SCHEMA = "cos.lean-governance.v1"
SKILL_OPT_SCHEMA = "cos.skill-opt.v1"
SLOW_START = "<!-- COS_SKILL_SLOW_UPDATE_START -->"
SLOW_END = "<!-- COS_SKILL_SLOW_UPDATE_END -->"
LEARNED_START = "<!-- COS_SKILL_LEARNED_START -->"
LEARNED_END = "<!-- COS_SKILL_LEARNED_END -->"
TEXT_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs", ".swift", ".sh", ".md", ".mdx", ".txt", ".json", ".yaml", ".yml", ".toml", ".css", ".scss", ".html"}
CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs", ".swift"}
IGNORED_DIRS = {".git", ".venv", "venv", "node_modules", "dist", "build", "target", "__pycache__", ".pytest_cache", ".mypy_cache"}
DEPENDENCY_FILES = {"package.json", "requirements.txt", "pyproject.toml", "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sanitize_id(value: str | None, fallback: str = "run") -> str:
    raw = (value or fallback).strip()
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in raw)
    return safe or fallback


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def root_from_arg(value: str | None) -> Path:
    return Path(value or os.getcwd()).resolve()


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def emit(payload: dict[str, Any], as_json: bool) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True) if as_json else payload.get("message", json.dumps(payload, sort_keys=True)))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def iter_files(root: Path, max_files: int = 2500) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if len(files) >= max_files:
            break
        if path.is_dir():
            continue
        parts = set(rel(path, root).split(os.sep))
        if parts & IGNORED_DIRS:
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in DEPENDENCY_FILES:
            files.append(path)
    return files


def git_diff(root: Path) -> str:
    proc = subprocess.run(["git", "diff", "--unified=0", "HEAD"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return proc.stdout if proc.returncode == 0 else ""


def changed_files(root: Path) -> list[Path]:
    names: list[str] = []
    for cmd in (["git", "diff", "--name-only", "HEAD"], ["git", "ls-files", "--others", "--exclude-standard"]):
        proc = subprocess.run(cmd, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
        if proc.returncode == 0:
            names.extend(line.strip() for line in proc.stdout.splitlines() if line.strip())
    seen: set[str] = set()
    out: list[Path] = []
    for name in names:
        if name in seen:
            continue
        seen.add(name)
        p = root / name
        if p.exists() and p.is_file():
            out.append(p)
    return out


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def line_findings(path: Path, text: str, root: Path, *, diff_only: bool = False) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    relpath = rel(path, root)
    suffix = path.suffix.lower()
    patterns: list[tuple[str, str, str, str]] = [
        (r"\b(Abstract[A-Z]\w+|Base[A-Z]\w+|I[A-Z][A-Za-z]+)\b", "yagni", "speculative abstraction naming", "Prefer a concrete function/type until multiple implementations exist."),
        (r"\b(factory|manager|registry|provider|adapter)\b", "yagni", "possible indirection layer", "Keep the call direct unless the second implementation already exists."),
        (r"\b(leftPad|padLeft|debounce|throttle|deepClone|uuid|slugify)\b", "stdlib", "possible standard-library/native helper", "Check built-in language/runtime APIs or existing dependencies before custom code."),
        (r"\b(new Map\(|Object\.keys\(|JSON\.parse\(JSON\.stringify\()", "shrink", "custom data plumbing hotspot", "Prefer the smallest built-in transform that preserves behavior."),
        (r"\bclass\s+\w+", "yagni", "class introduced", "Use a function or plain data unless state/polymorphism is required."),
    ]
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if diff_only and not stripped.startswith("+"):
            continue
        body = stripped[1:] if stripped.startswith("+") else stripped
        if not body or body.startswith(("//", "#", "*")):
            continue
        if suffix in CODE_SUFFIXES and len(body) > 160:
            findings.append({"tag": "shrink", "severity": "medium", "path": relpath, "line": lineno, "summary": "long code line", "replacement": "Split only if it clarifies; otherwise remove intermediate boilerplate.", "evidence": body[:220]})
        for regex, tag, summary, replacement in patterns:
            if re.search(regex, body, flags=re.IGNORECASE):
                findings.append({"tag": tag, "severity": "medium", "path": relpath, "line": lineno, "summary": summary, "replacement": replacement, "evidence": body[:220]})
                break
    if path.name in DEPENDENCY_FILES:
        dep_lines = [line for line in text.splitlines() if line.strip().startswith("+") or not diff_only]
        dep_hits = [line.strip() for line in dep_lines if re.search(r"\b(dependencies|devDependencies|require|implementation|cargo add|pip install|version)\b", line, re.I)]
        if dep_hits:
            findings.append({"tag": "dependency", "severity": "high", "path": relpath, "line": 1, "summary": "dependency surface changed or declared", "replacement": "Verify stdlib/native/existing dependency cannot cover this before adding a new dependency.", "evidence": dep_hits[0][:220]})
    return findings


def lean_payload(root: Path, *, mode: str, max_files: int, diff_text: str = "") -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    scanned: list[str] = []
    if mode == "review":
        files = changed_files(root)
        diff = diff_text or git_diff(root)
        if diff:
            current_file = ""
            for raw in diff.splitlines():
                if raw.startswith("+++ b/"):
                    current_file = raw[6:]
                    continue
                if raw.startswith("+") and not raw.startswith("+++") and current_file:
                    tmp = Path(current_file)
                    findings.extend(line_findings(root / current_file, raw, root, diff_only=True))
            scanned = sorted({rel(f, root) for f in files})
        else:
            for f in files[:max_files]:
                scanned.append(rel(f, root))
                findings.extend(line_findings(f, read_text(f), root))
    else:
        for f in iter_files(root, max_files=max_files):
            scanned.append(rel(f, root))
            findings.extend(line_findings(f, read_text(f), root))
    # Dedup same path/tag/summary/line.
    seen: set[tuple[Any, ...]] = set()
    deduped: list[dict[str, Any]] = []
    for item in findings:
        key = (item.get("path"), item.get("line"), item.get("tag"), item.get("summary"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    severity_order = {"high": 0, "medium": 1, "low": 2}
    deduped.sort(key=lambda item: (severity_order.get(str(item.get("severity")), 9), str(item.get("path")), int(item.get("line") or 0)))
    removable_estimate = len(deduped) * 5
    return {
        "schema_version": LEAN_SCHEMA,
        "mode": mode,
        "project_root": str(root),
        "generated_at": utc_now(),
        "scanned_files": scanned[:max_files],
        "finding_count": len(deduped),
        "estimated_lines_removable": removable_estimate,
        "findings": deduped,
        "message": f"lean-{mode}: findings={len(deduped)} estimated_lines_removable={removable_estimate}",
    }


def command_lean_review(args: argparse.Namespace) -> int:
    root = root_from_arg(args.project_dir)
    payload = lean_payload(root, mode="review", max_files=args.max_files)
    emit(payload, args.json)
    return 2 if args.strict and payload["finding_count"] else 0


def command_lean_audit(args: argparse.Namespace) -> int:
    root = root_from_arg(args.project_dir)
    payload = lean_payload(root, mode="audit", max_files=args.max_files)
    out = root / ".cognitive-os" / "lean" / "audit-latest.json"
    write_json(out, payload)
    payload["report_path"] = str(out)
    emit(payload, args.json)
    return 2 if args.strict and payload["finding_count"] else 0


def command_lean_debt(args: argparse.Namespace) -> int:
    root = root_from_arg(args.project_dir)
    marker_re = re.compile(r"(?:#|//|/\*|<!--)\s*cos-lean:\s*(?P<body>.*)", re.I)
    rows: list[dict[str, Any]] = []
    for f in iter_files(root, max_files=args.max_files):
        for lineno, line in enumerate(read_text(f).splitlines(), 1):
            match = marker_re.search(line)
            if not match:
                continue
            body = match.group("body").strip().rstrip("*/ -->")
            lower = body.lower()
            has_trigger = "trigger:" in lower or "when:" in lower or "upgrade:" in lower
            rows.append({"path": rel(f, root), "line": lineno, "body": body, "has_trigger": has_trigger, "status": "actionable" if has_trigger else "missing-trigger"})
    payload = {"schema_version": "cos.lean-debt.v1", "project_root": str(root), "generated_at": utc_now(), "marker": "cos-lean:", "count": len(rows), "missing_trigger_count": sum(1 for r in rows if not r["has_trigger"]), "items": rows, "message": f"lean debt markers={len(rows)} missing_trigger={sum(1 for r in rows if not r['has_trigger'])}"}
    out = root / ".cognitive-os" / "lean" / "debt-ledger.json"
    write_json(out, payload)
    payload["ledger_path"] = str(out)
    emit(payload, args.json)
    return 2 if args.strict and payload["missing_trigger_count"] else 0


def skillopt_root(root: Path, run_id: str) -> Path:
    return root / ".cognitive-os" / "skill-opt" / sanitize_id(run_id, "default")


def load_mapping(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        if yaml is None:
            raise SystemExit("PyYAML is required for YAML contracts")
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise SystemExit(f"contract must be a mapping: {path}")
    return data


def strip_region(text: str, start: str, end: str) -> str:
    while start in text:
        s = text.find(start)
        e = text.find(end, s)
        if e == -1:
            text = text[:s]
            break
        text = text[:s] + text[e + len(end):]
    return re.sub(r"\n{3,}", "\n\n", text).rstrip()


def replace_region(text: str, start: str, end: str, content: str, heading: str = "") -> str:
    base = strip_region(text, start, end)
    body = content.strip()
    if heading:
        body = f"{heading}\n\n{body}" if body else heading
    return f"{base}\n\n{start}\n{body}\n{end}\n"


def append_learned(text: str, lines: list[str]) -> str:
    existing = ""
    if LEARNED_START in text and LEARNED_END in text:
        s = text.find(LEARNED_START) + len(LEARNED_START)
        e = text.find(LEARNED_END, s)
        existing = text[s:e]
    current = [ln[2:].strip() if ln.strip().startswith("- ") else ln.strip() for ln in existing.splitlines() if ln.strip().startswith("- ")]
    seen = {" ".join(ln.lower().split()) for ln in current}
    for line in lines:
        clean = re.sub(r"\s+", " ", line.strip().lstrip("- "))
        key = " ".join(clean.lower().split())
        if clean and key not in seen:
            current.append(clean)
            seen.add(key)
    body = "\n".join(f"- {ln}" for ln in current)
    return replace_region(text, LEARNED_START, LEARNED_END, body, "## Learned Skill Guidance")


def apply_skill_edits(skill_text: str, edits: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    applied: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    text = skill_text
    for edit in edits:
        op = str(edit.get("op") or "add").lower()
        content = str(edit.get("content") or "").strip()
        anchor = str(edit.get("anchor") or edit.get("target") or "")
        if not content and op in {"add", "replace"}:
            rejected.append({**edit, "reason": "empty-content"})
            continue
        if op == "add":
            text = append_learned(text, [content])
            applied.append(edit)
        elif op == "replace":
            if not anchor or anchor not in text:
                rejected.append({**edit, "reason": "anchor-not-found"})
                continue
            text = text.replace(anchor, content, 1)
            applied.append(edit)
        elif op == "delete":
            target = anchor or content
            if not target or target not in text:
                rejected.append({**edit, "reason": "target-not-found"})
                continue
            text = text.replace(target, "", 1)
            applied.append(edit)
        else:
            rejected.append({**edit, "reason": "unknown-op"})
    return text, applied, rejected


def stage_proposal(root: Path, run_id: str, skill_path: Path, proposed_text: str, metadata: dict[str, Any]) -> dict[str, Any]:
    run = skillopt_root(root, run_id)
    stage = run / "staging"
    stage.mkdir(parents=True, exist_ok=True)
    live_text = read_text(skill_path)
    proposed = stage / "proposed_SKILL.md"
    proposed.write_text(proposed_text, encoding="utf-8")
    diff = "".join(difflib.unified_diff(live_text.splitlines(True), proposed_text.splitlines(True), fromfile=str(skill_path), tofile=str(proposed)))
    (stage / "proposal.diff").write_text(diff, encoding="utf-8")
    manifest = {"schema_version": SKILL_OPT_SCHEMA, "run_id": sanitize_id(run_id), "live_skill_path": str(skill_path.resolve()), "proposed_skill_path": str(proposed), "proposal_diff_path": str(stage / "proposal.diff"), "live_hash": sha256_text(live_text), "proposed_hash": sha256_text(proposed_text), "metadata": metadata, "updated_at": utc_now()}
    write_json(stage / "manifest.json", manifest)
    return manifest


def command_skill_proposal_stage(args: argparse.Namespace) -> int:
    root = root_from_arg(args.project_dir)
    skill_path = Path(args.skill).resolve()
    if not skill_path.exists():
        raise SystemExit(f"skill not found: {skill_path}")
    skill_text = read_text(skill_path)
    edits: list[dict[str, Any]] = []
    for item in args.edit_add or []:
        edits.append({"op": "add", "content": item})
    for item in args.edit_replace or []:
        if "=>" not in item:
            raise SystemExit("--edit-replace must be ANCHOR=>CONTENT")
        anchor, content = item.split("=>", 1)
        edits.append({"op": "replace", "anchor": anchor, "content": content})
    if args.proposal:
        proposed_text = read_text(Path(args.proposal).resolve())
        applied = [{"op": "proposal-file", "content": args.proposal}]
        rejected: list[dict[str, Any]] = []
    else:
        proposed_text, applied, rejected = apply_skill_edits(skill_text, edits)
    manifest = stage_proposal(root, args.run_id, skill_path, proposed_text, {"applied_edits": applied, "rejected_edits": rejected, "source": "proposal-stage"})
    if rejected:
        append_jsonl(skillopt_root(root, args.run_id) / "rejected-edits.jsonl", {"ts": utc_now(), "rejected_edits": rejected, "reason": "proposal-stage"})
    payload = {"status": "staged", **manifest, "message": f"skill proposal staged run={sanitize_id(args.run_id)} rejected={len(rejected)}"}
    emit(payload, args.json)
    return 2 if rejected and args.strict else 0


def command_skill_edit_gate(args: argparse.Namespace) -> int:
    root = root_from_arg(args.project_dir)
    run = skillopt_root(root, args.run_id)
    baseline = float(args.baseline_score)
    candidate = float(args.candidate_score)
    min_delta = float(args.min_delta)
    accepted = candidate > baseline + min_delta
    payload = {"schema_version": "cos.skill-edit-gate.v1", "run_id": sanitize_id(args.run_id), "metric": args.metric, "baseline_score": baseline, "candidate_score": candidate, "min_delta": min_delta, "accepted": accepted, "action": "accept" if accepted else "reject", "updated_at": utc_now(), "message": f"skill gate {'accepted' if accepted else 'rejected'} candidate={candidate:.4f} baseline={baseline:.4f}"}
    write_json(run / "gate.json", payload)
    if not accepted:
        append_jsonl(run / "rejected-edits.jsonl", {"ts": utc_now(), "reason": "validation-gate", "baseline_score": baseline, "candidate_score": candidate, "metric": args.metric})
    emit(payload, args.json)
    return 0 if accepted else 2


def command_skill_adopt(args: argparse.Namespace) -> int:
    root = root_from_arg(args.project_dir)
    run = skillopt_root(root, args.run_id)
    manifest = read_json(run / "staging" / "manifest.json")
    gate = read_json(run / "gate.json")
    if not manifest:
        raise SystemExit("missing staged proposal")
    if not gate.get("accepted") and not args.force:
        payload = {"status": "blocked", "reason": "gate-not-accepted", "run_id": sanitize_id(args.run_id), "message": "adopt blocked: gate not accepted"}
        emit(payload, args.json)
        return 2
    live = Path(manifest["live_skill_path"])
    proposed = Path(manifest["proposed_skill_path"])
    backup_dir = run / "backups" / time.strftime("%Y%m%d-%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / live.name
    if live.exists():
        shutil.copy2(live, backup_path)
    if args.apply:
        shutil.copy2(proposed, live)
        status = "adopted"
    else:
        status = "dry-run"
    payload = {"schema_version": "cos.skill-adopt.v1", "run_id": sanitize_id(args.run_id), "status": status, "live_skill_path": str(live), "proposed_skill_path": str(proposed), "backup_path": str(backup_path), "applied": bool(args.apply), "updated_at": utc_now(), "message": f"skill adopt {status} run={sanitize_id(args.run_id)}"}
    write_json(run / "adopt.json", payload)
    emit(payload, args.json)
    return 0


def command_skill_rejected_buffer(args: argparse.Namespace) -> int:
    root = root_from_arg(args.project_dir)
    run = skillopt_root(root, args.run_id)
    path = run / "rejected-edits.jsonl"
    if args.report:
        rows = []
        if path.exists():
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        payload = {"schema_version": "cos.skill-rejected-buffer.v1", "run_id": sanitize_id(args.run_id), "count": len(rows), "items": rows, "buffer_path": str(path), "message": f"rejected edits={len(rows)}"}
        emit(payload, args.json)
        return 0
    row = {"ts": utc_now(), "reason": args.reason, "edit": args.edit or "", "source": "manual"}
    append_jsonl(path, row)
    payload = {"schema_version": "cos.skill-rejected-buffer.v1", "run_id": sanitize_id(args.run_id), "recorded": row, "buffer_path": str(path), "message": "rejected edit recorded"}
    emit(payload, args.json)
    return 0


def command_skill_slow_update(args: argparse.Namespace) -> int:
    root = root_from_arg(args.project_dir)
    skill_path = Path(args.skill).resolve()
    text = read_text(skill_path)
    guidance = "\n".join(args.guidance or []) or read_text(Path(args.guidance_file).resolve()) if args.guidance_file else "\n".join(args.guidance or [])
    if not guidance.strip():
        raise SystemExit("slow update requires --guidance or --guidance-file")
    proposed = replace_region(text, SLOW_START, SLOW_END, guidance, "## Longitudinal Skill Guidance")
    manifest = stage_proposal(root, args.run_id, skill_path, proposed, {"source": "slow-update", "guidance_hash": sha256_text(guidance)})
    payload = {"status": "staged", **manifest, "message": f"slow update staged run={sanitize_id(args.run_id)}"}
    emit(payload, args.json)
    return 0


def command_skill_opt_run(args: argparse.Namespace) -> int:
    root = root_from_arg(args.project_dir)
    skill_path = Path(args.skill).resolve()
    argv = ["--project-dir", str(root), "--run-id", args.run_id, "--skill", str(skill_path)]
    for edit in args.edit_add or []:
        argv.extend(["--edit-add", edit])
    if args.proposal:
        argv.extend(["--proposal", args.proposal])
    stage_args = build_parser().parse_args(["skill-proposal-stage", *argv, "--json"])
    with contextlib.redirect_stdout(io.StringIO()):
        stage_rc = command_skill_proposal_stage(stage_args)
    gate_rc = 0
    if args.baseline_score is not None and args.candidate_score is not None:
        gate_args = build_parser().parse_args(["skill-edit-gate", "--project-dir", str(root), "--run-id", args.run_id, "--baseline-score", str(args.baseline_score), "--candidate-score", str(args.candidate_score), "--metric", args.metric, "--min-delta", str(args.min_delta), "--json"])
        with contextlib.redirect_stdout(io.StringIO()):
            gate_rc = command_skill_edit_gate(gate_args)
    payload = {"schema_version": "cos.skill-opt-run.v1", "run_id": sanitize_id(args.run_id), "staged": stage_rc == 0, "stage_rc": stage_rc, "gate_ran": args.baseline_score is not None and args.candidate_score is not None, "gate_rc": gate_rc, "message": f"skill opt run staged run={sanitize_id(args.run_id)} gate_rc={gate_rc}"}
    emit(payload, args.json)
    return gate_rc


def mine_sleep_tasks(root: Path, trace_dir: Path, max_files: int) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for path in sorted(trace_dir.rglob("*.jsonl"))[:max_files]:
        for line in read_text(path).splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            text = json.dumps(row, sort_keys=True)[:500]
            if any(token in text.lower() for token in ["failed", "blocked", "still", "retry", "verification"]):
                tasks.append({"id": f"task-{len(tasks)+1}", "source": rel(path, root), "signal": text[:240]})
                break
    return tasks


def command_skill_sleep(args: argparse.Namespace) -> int:
    root = root_from_arg(args.project_dir)
    run_id = sanitize_id(args.run_id or f"sleep-{datetime.now().strftime('%Y%m%d')}")
    skill_path = Path(args.skill).resolve()
    trace_dir = Path(args.trace_dir).resolve() if args.trace_dir else root / ".cognitive-os" / "process-loops"
    tasks = mine_sleep_tasks(root, trace_dir, args.max_files) if trace_dir.exists() else []
    guidance_lines = ["Prefer validation-backed updates over unconditional self-editing."]
    if tasks:
        guidance_lines.append(f"Review recurring failure signals before final claims; mined {len(tasks)} task signal(s).")
    else:
        guidance_lines.append("No recurring task signals were mined; keep proposal staged and do not auto-adopt.")
    guidance = "\n".join(f"- {line}" for line in guidance_lines)
    proposed = replace_region(read_text(skill_path), SLOW_START, SLOW_END, guidance, "## Longitudinal Skill Guidance")
    manifest = stage_proposal(root, run_id, skill_path, proposed, {"source": "skill-sleep", "tasks_mined": tasks, "trace_dir": str(trace_dir)})
    report = {"schema_version": "cos.skill-sleep.v1", "run_id": run_id, "tasks_mined": len(tasks), "tasks": tasks, "accepted": False, "staging": manifest, "message": f"skill sleep staged run={run_id} tasks={len(tasks)}"}
    write_json(skillopt_root(root, run_id) / "sleep-report.json", report)
    emit(report, args.json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cognitive OS lean governance and skill optimization primitives")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func in (("lean-review", command_lean_review), ("lean-audit", command_lean_audit)):
        p = sub.add_parser(name)
        p.add_argument("--project-dir", default=os.getcwd())
        p.add_argument("--max-files", type=int, default=2500)
        p.add_argument("--strict", action="store_true")
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=func)
    debt = sub.add_parser("lean-debt")
    debt.add_argument("--project-dir", default=os.getcwd())
    debt.add_argument("--max-files", type=int, default=2500)
    debt.add_argument("--strict", action="store_true")
    debt.add_argument("--json", action="store_true")
    debt.set_defaults(func=command_lean_debt)

    stage = sub.add_parser("skill-proposal-stage")
    stage.add_argument("--project-dir", default=os.getcwd())
    stage.add_argument("--run-id", default="default")
    stage.add_argument("--skill", required=True)
    stage.add_argument("--proposal")
    stage.add_argument("--edit-add", action="append")
    stage.add_argument("--edit-replace", action="append")
    stage.add_argument("--strict", action="store_true")
    stage.add_argument("--json", action="store_true")
    stage.set_defaults(func=command_skill_proposal_stage)

    gate = sub.add_parser("skill-edit-gate")
    gate.add_argument("--project-dir", default=os.getcwd())
    gate.add_argument("--run-id", default="default")
    gate.add_argument("--baseline-score", required=True)
    gate.add_argument("--candidate-score", required=True)
    gate.add_argument("--metric", default="hard")
    gate.add_argument("--min-delta", type=float, default=0.0)
    gate.add_argument("--json", action="store_true")
    gate.set_defaults(func=command_skill_edit_gate)

    adopt = sub.add_parser("skill-adopt")
    adopt.add_argument("--project-dir", default=os.getcwd())
    adopt.add_argument("--run-id", default="default")
    adopt.add_argument("--apply", action="store_true")
    adopt.add_argument("--force", action="store_true")
    adopt.add_argument("--json", action="store_true")
    adopt.set_defaults(func=command_skill_adopt)

    rejected = sub.add_parser("skill-rejected-buffer")
    rejected.add_argument("--project-dir", default=os.getcwd())
    rejected.add_argument("--run-id", default="default")
    rejected.add_argument("--edit")
    rejected.add_argument("--reason", default="manual")
    rejected.add_argument("--report", action="store_true")
    rejected.add_argument("--json", action="store_true")
    rejected.set_defaults(func=command_skill_rejected_buffer)

    slow = sub.add_parser("skill-slow-update")
    slow.add_argument("--project-dir", default=os.getcwd())
    slow.add_argument("--run-id", default="slow-update")
    slow.add_argument("--skill", required=True)
    slow.add_argument("--guidance", action="append")
    slow.add_argument("--guidance-file")
    slow.add_argument("--json", action="store_true")
    slow.set_defaults(func=command_skill_slow_update)

    opt = sub.add_parser("skill-opt-run")
    opt.add_argument("--project-dir", default=os.getcwd())
    opt.add_argument("--run-id", default="default")
    opt.add_argument("--skill", required=True)
    opt.add_argument("--proposal")
    opt.add_argument("--edit-add", action="append")
    opt.add_argument("--baseline-score", type=float)
    opt.add_argument("--candidate-score", type=float)
    opt.add_argument("--metric", default="hard")
    opt.add_argument("--min-delta", type=float, default=0.0)
    opt.add_argument("--json", action="store_true")
    opt.set_defaults(func=command_skill_opt_run)

    sleep = sub.add_parser("skill-sleep")
    sleep.add_argument("--project-dir", default=os.getcwd())
    sleep.add_argument("--run-id")
    sleep.add_argument("--skill", required=True)
    sleep.add_argument("--trace-dir")
    sleep.add_argument("--max-files", type=int, default=200)
    sleep.add_argument("--json", action="store_true")
    sleep.set_defaults(func=command_skill_sleep)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
