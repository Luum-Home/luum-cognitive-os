"""Classify and gate destructive cleanup intents for untracked work.

This module is intentionally conservative: untracked files are treated as
active human/agent work unless the deletion carries an explicit classification,
reason, and approval path.  It powers the PreToolUse Bash guard and the
``scripts/cos-safe-clean`` dry-run/execute primitive.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from collections.abc import Collection, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

PROTECTED_PREFIXES = (
    "docs/03-PoCs/research/",
    "docs/06-Daily/reports/",
    "plans/",
    ".cognitive-os/plans/",
)
ALLOWED_CLASSIFICATIONS = {
    "generated-cache",
    "temp",
    "duplicate",
    "rejected",
    "operator-approved",
}
APPROVAL_ENVS = (
    "COS_SAFE_DELETE_APPROVED",
    "COS_ALLOW_UNTRACKED_DELETE",
)


@dataclass(frozen=True)
class DeleteTarget:
    path: str
    exists: bool
    untracked: bool
    protected_artifact: bool
    created_by_current_session: bool
    reason: str


@dataclass(frozen=True)
class DeleteIntent:
    operation: str
    command: str
    targets: list[DeleteTarget]
    classification: str | None
    delete_reason: str | None
    approved: bool
    allowed: bool
    message: str


def _run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )


def repo_root(path: str | Path = ".") -> Path:
    candidate = Path(path).resolve()
    result = _run_git(candidate, ["rev-parse", "--show-toplevel"])
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    return candidate


def normalize_path(root: Path, raw: str) -> str:
    raw = raw.strip().strip("'\"")
    if raw in {"", ".", "./"}:
        return "."
    expanded = os.path.expandvars(os.path.expanduser(raw))
    path = Path(expanded)
    if not path.is_absolute():
        path = root / path
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def git_untracked(root: Path) -> set[str]:
    result = _run_git(root, ["status", "--porcelain=v1", "--untracked-files=all"])
    out: set[str] = set()
    if result.returncode != 0:
        return out
    for line in result.stdout.splitlines():
        if line.startswith("?? "):
            out.add(line[3:].strip())
    return out


def is_untracked_path(rel: str, untracked: set[str]) -> bool:
    if rel in untracked:
        return True
    prefix = rel.rstrip("/") + "/"
    return any(item.startswith(prefix) for item in untracked)


def is_protected_artifact(rel: str) -> bool:
    normalized = rel.lstrip("./")
    return any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in PROTECTED_PREFIXES)


def created_by_current_session(root: Path, rel: str, session_id: str | None = None) -> bool:
    session_id = session_id or os.environ.get("COGNITIVE_OS_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("CODEX_SESSION_ID")
    if not session_id:
        return False
    # Best-effort ownership marker.  Future hooks can write richer manifests; the
    # guard treats absence as not owned by this session.
    marker = root / ".cognitive-os" / "coordination" / "artifact-claims.jsonl"
    if not marker.exists():
        return False
    try:
        for line in marker.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("path") == rel and row.get("session_id") == session_id:
                return True
    except Exception:
        return False
    return False


def split_segments(command: str) -> list[str]:
    # Conservative shell split by common command separators.  We do not attempt
    # full shell parsing; this is a safety classifier, not an executor.
    segments: list[str] = []
    current = []
    in_single = False
    in_double = False
    i = 0
    while i < len(command):
        ch = command[i]
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        if not in_single and not in_double and ch in ";|\n":
            segment = "".join(current).strip()
            if segment:
                segments.append(segment)
            current = []
        elif not in_single and not in_double and ch == "&":
            segment = "".join(current).strip()
            if segment:
                segments.append(segment)
            current = []
            if i + 1 < len(command) and command[i + 1] == "&":
                i += 1
        else:
            current.append(ch)
        i += 1
    segment = "".join(current).strip()
    if segment:
        segments.append(segment)
    return segments


def _shlex(segment: str) -> list[str]:
    try:
        return shlex.split(segment)
    except ValueError:
        return []


def _strip_options(tokens: list[str], *, options_with_values: Collection[str] = frozenset()) -> list[str]:
    out: list[str] = []
    skip = False
    for token in tokens:
        if skip:
            skip = False
            continue
        if token == "--":
            out.extend(tokens[tokens.index(token) + 1 :])
            break
        if token in options_with_values:
            skip = True
            continue
        if token.startswith("-"):
            continue
        out.append(token)
    return out


def extract_delete_operations(command: str) -> list[tuple[str, list[str]]]:
    operations: list[tuple[str, list[str]]] = []
    for segment in split_segments(command):
        tokens = _shlex(segment)
        if not tokens:
            continue
        cmd = Path(tokens[0]).name
        if cmd == "rm":
            flags = [t for t in tokens[1:] if t.startswith("-") and t != "--"]
            recursive = any("r" in t.lower() for t in flags) or "--recursive" in flags
            if recursive:
                paths = _strip_options(tokens[1:])
                if paths:
                    operations.append(("rm-recursive", paths))
        elif cmd == "git":
            # Skip global git options to find subcommand.
            i = 1
            while i < len(tokens):
                if tokens[i] in {"-C", "--git-dir", "--work-tree", "-c"}:
                    i += 2
                    continue
                if tokens[i].startswith(("--git-dir=", "--work-tree=")):
                    i += 1
                    continue
                break
            sub = tokens[i] if i < len(tokens) else ""
            args = tokens[i + 1 :]
            if sub == "clean" and any(a.startswith("-") and "f" in a for a in args):
                paths = [a for a in args if not a.startswith("-")]
                operations.append(("git-clean", paths or ["."]))
        elif cmd == "find" and "-delete" in tokens[1:]:
            # find PATH ... -delete; if no path appears before expression, default is .
            paths: list[str] = []
            for token in tokens[1:]:
                if token == "--":
                    continue
                if token.startswith("-") or token in {"!", "(", ")"}:
                    break
                paths.append(token)
            operations.append(("find-delete", paths or ["."]))
    return operations


def classify_targets(root: Path, raw_paths: Iterable[str]) -> list[DeleteTarget]:
    untracked = git_untracked(root)
    rows: list[DeleteTarget] = []
    for raw in raw_paths:
        rel = normalize_path(root, raw)
        path = root / rel if not Path(rel).is_absolute() else Path(rel)
        untracked_hit = is_untracked_path(rel, untracked)
        protected = is_protected_artifact(rel) or any(is_protected_artifact(item) for item in untracked if item.startswith(rel.rstrip("/") + "/"))
        owned = created_by_current_session(root, rel)
        reason = "untracked" if untracked_hit else "not-untracked"
        if protected:
            reason += ";protected-artifact"
        if not owned:
            reason += ";no-current-session-claim"
        rows.append(DeleteTarget(rel, path.exists(), untracked_hit, protected, owned, reason))
    return rows


def approval_from_env(env: Mapping[str, str] | None = None) -> tuple[bool, str | None, str | None]:
    source: Mapping[str, str] = os.environ if env is None else env
    approved = any(source.get(name) == "1" for name in APPROVAL_ENVS)
    classification = source.get("COS_DELETE_CLASSIFICATION")
    reason = source.get("COS_DELETE_REASON") or source.get("COS_BYPASS_REASON")
    return approved, classification, reason


def evaluate_command(root: Path, command: str, env: dict[str, str] | None = None) -> DeleteIntent:
    approved, classification, reason = approval_from_env(env)
    ops = extract_delete_operations(command)
    all_targets: list[DeleteTarget] = []
    op_names: list[str] = []
    for op, raw_paths in ops:
        op_names.append(op)
        all_targets.extend(classify_targets(root, raw_paths))
    risky = [t for t in all_targets if t.untracked or t.protected_artifact]
    if not risky:
        return DeleteIntent(
            operation=",".join(op_names) if op_names else "none",
            command=command,
            targets=all_targets,
            classification=classification,
            delete_reason=reason,
            approved=approved,
            allowed=True,
            message="No untracked/protected delete target detected.",
        )
    valid_classification = classification in ALLOWED_CLASSIFICATIONS
    has_reason = bool(reason and reason.strip())
    if approved and valid_classification and has_reason:
        return DeleteIntent(
            operation=",".join(sorted(set(op_names))),
            command=command,
            targets=all_targets,
            classification=classification,
            delete_reason=reason,
            approved=True,
            allowed=True,
            message="Approved delete intent with classification and reason.",
        )
    missing: list[str] = []
    if not approved:
        missing.append("approval env COS_SAFE_DELETE_APPROVED=1")
    if not valid_classification:
        missing.append("COS_DELETE_CLASSIFICATION in " + ",".join(sorted(ALLOWED_CLASSIFICATIONS)))
    if not has_reason:
        missing.append("COS_DELETE_REASON")
    return DeleteIntent(
        operation=",".join(sorted(set(op_names))),
        command=command,
        targets=all_targets,
        classification=classification,
        delete_reason=reason,
        approved=approved,
        allowed=False,
        message="Blocked delete of untracked/protected work; missing " + "; ".join(missing),
    )


def safe_clean_plan(root: Path, paths: list[str], classification: str | None, reason: str | None, approved: bool) -> DeleteIntent:
    targets = classify_targets(root, paths)
    env = {
        "COS_SAFE_DELETE_APPROVED": "1" if approved else "0",
        "COS_DELETE_CLASSIFICATION": classification or "",
        "COS_DELETE_REASON": reason or "",
    }
    # Reuse evaluator semantics with synthetic rm command, but keep the
    # precomputed target rows so dry-run output reflects caller paths exactly.
    intent = evaluate_command(root, "rm -rf -- " + " ".join(shlex.quote(p) for p in paths), env=env)
    return DeleteIntent(
        operation=intent.operation,
        command=intent.command,
        targets=targets,
        classification=intent.classification,
        delete_reason=intent.delete_reason,
        approved=intent.approved,
        allowed=intent.allowed,
        message=intent.message,
    )



def emit(intent: DeleteIntent) -> str:
    return json.dumps(asdict(intent), indent=2, sort_keys=True)


def _cmd_guard(args: argparse.Namespace) -> int:
    intent = evaluate_command(repo_root(args.project_dir), args.command)
    print(emit(intent))
    return 0 if intent.allowed else 2


def _cmd_plan(args: argparse.Namespace) -> int:
    intent = safe_clean_plan(repo_root(args.project_dir), args.path, args.classification, args.reason, args.approved)
    print(emit(intent))
    return 0 if intent.allowed else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    guard = sub.add_parser("guard")
    guard.add_argument("--project-dir", default=".")
    guard.add_argument("--command", required=True)
    guard.set_defaults(func=_cmd_guard)
    plan = sub.add_parser("plan")
    plan.add_argument("--project-dir", default=".")
    plan.add_argument("--path", action="append", required=True)
    plan.add_argument("--classification")
    plan.add_argument("--reason")
    plan.add_argument("--approved", action="store_true")
    plan.set_defaults(func=_cmd_plan)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
