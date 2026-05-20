#!/usr/bin/env python3
# SCOPE: both
"""Cross-IDE high-stakes claim gate for orchestrators.

The gate is intentionally harness-agnostic: Claude/Codex hooks can call it from a
Bash PreToolUse surface, and agents can run it directly before committing or
pushing. It does not trust sub-agent supplied commands; it re-runs deterministic
repo verifiers against staged plans and commit/push claims. High-stakes
agent completions use scripts/claim_enforcer.py and require verification:
evidence in the Trust Report.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.orchestrator_verify import verify_all
from scripts.verify_plan_claims import verify_plan


PLAN_PATH = re.compile(r"(^|/)(\.cognitive-os/plans|plans)/|plan", re.IGNORECASE)
SCOPED_CLAIM_LINE = re.compile(
    r"^\s*(RESULT:|STATUS:|done\s+\d+\s+[A-Za-z][A-Za-z0-9_-]*)",
    re.IGNORECASE,
)
SUBJECT_CLAIM_LINE = re.compile(
    r"^\s*(archived|deleted|removed|wired|integrated|registered|done|closed|migrated|tested|verified|claimed)\b",
    re.IGNORECASE,
)
AGGREGATE_MISSING_CLAIM = re.compile(
    r"\b(?P<count>\d{2,})\s+(?:items?\s+|files?\s+|skills?\s+|entries?\s+)?"
    r"(?P<status>missing|not[_ -]?found|absent)\b|"
    r"\b(?P<status_first>missing|not[_ -]?found|absent)\s+"
    r"(?P<count_after>\d{2,})\s+(?:items?\s+|files?\s+|skills?\s+|entries?)\b",
    re.IGNORECASE,
)
PER_ITEM_EVIDENCE_ROW = re.compile(
    r"^\s*(?:[-*]|\d+\.|\|)\s+.*"
    r"(?:`[^`]+`|(?:^|[\s:])(?:[./][^\s`|]+|[A-Za-z0-9_.-]+/[^\s`|]+)|"
    r"\b(?:checked|verified|exists|missing|not[_ -]?found|ls\s+-la|test\s+-e)\b)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GateFinding:
    source: str
    status: str
    message: str
    evidence: str = ""


@dataclass(frozen=True)
class GateResult:
    ok: bool
    findings: list[GateFinding]


def run_git(root: Path, args: Sequence[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        timeout=60,
    )


def split_git_command(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return []


def find_git_subcommand(parts: Sequence[str]) -> tuple[str, int] | tuple[None, int]:
    try:
        idx = parts.index("git")
    except ValueError:
        if parts and Path(parts[0]).name == "git":
            idx = 0
        else:
            return None, -1

    i = idx + 1
    while i < len(parts):
        token = parts[i]
        if token in {"-C", "--git-dir", "--work-tree", "-c"}:
            i += 2
            continue
        if token.startswith("--git-dir=") or token.startswith("--work-tree=") or token.startswith("-c"):
            i += 1
            continue
        return token, i
    return None, -1


def extract_commit_messages(command: str) -> list[str]:
    parts = split_git_command(command)
    subcommand, idx = find_git_subcommand(parts)
    if subcommand != "commit":
        return []
    messages: list[str] = []
    i = idx + 1
    while i < len(parts):
        token = parts[i]
        if token in {"-m", "--message"} and i + 1 < len(parts):
            messages.append(parts[i + 1])
            i += 2
            continue
        if token.startswith("--message="):
            messages.append(token.split("=", 1)[1])
        elif token.startswith("-m") and len(token) > 2:
            messages.append(token[2:])
        i += 1
    return messages


def is_git_commit_or_push(command: str) -> str | None:
    parts = split_git_command(command)
    subcommand, _idx = find_git_subcommand(parts)
    if subcommand in {"commit", "push"}:
        return subcommand
    return None


def staged_files(root: Path) -> list[Path]:
    proc = run_git(root, ["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    if proc.returncode != 0:
        return []
    return [root / line for line in proc.stdout.splitlines() if line.strip()]


def _is_plan_file(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    return path.suffix.lower() == ".md" and bool(PLAN_PATH.search(rel))


def verify_staged_plans(root: Path) -> list[GateFinding]:
    findings: list[GateFinding] = []
    for path in staged_files(root):
        if not path.exists() or not _is_plan_file(path, root):
            continue
        plan_findings = verify_plan(root, path)
        for finding in plan_findings:
            rel = path.relative_to(root).as_posix()
            findings.append(
                GateFinding(
                    source=rel,
                    status="FAIL",
                    message=f"line {finding.line}: {finding.message}",
                    evidence="plans with high-stakes [x] claims require inline (verified: ...) proof",
                )
            )
    return findings


def verify_text_claims(root: Path, text: str, source: str) -> list[GateFinding]:
    if not text.strip():
        return []
    outcomes = verify_all(text, str(root))
    findings: list[GateFinding] = []
    for outcome in outcomes:
        if outcome.verified:
            continue
        findings.append(
            GateFinding(
                source=source,
                status="FAIL",
                message=(
                    f"unverified high-stakes claim: {outcome.claim.verb} "
                    f"{outcome.claim.target}"
                ),
                evidence=outcome.failure_reason or json.dumps(outcome.evidence, sort_keys=True),
            )
        )
    return findings


def verify_aggregate_missing_evidence(text: str, source: str) -> list[GateFinding]:
    """Block aggregate "N missing" claims unless N per-item evidence rows exist.

    This enforces the subagent-context rule that a report may not claim a
    count of missing/not-found items from a bulk search alone. The report must
    include enough individual evidence rows to support the aggregate count.
    """
    findings: list[GateFinding] = []
    if not text.strip():
        return findings

    counts: list[int] = []
    for match in AGGREGATE_MISSING_CLAIM.finditer(text):
        raw = match.group("count") or match.group("count_after")
        if not raw:
            continue
        count = int(raw)
        if count >= 2:
            counts.append(count)

    if not counts:
        return findings

    evidence_rows = [
        line for line in text.splitlines() if PER_ITEM_EVIDENCE_ROW.search(line)
    ]
    required = max(counts)
    if len(evidence_rows) < required:
        findings.append(
            GateFinding(
                source=source,
                status="FAIL",
                message=(
                    f"aggregate missing/not-found claim requires per-item evidence: "
                    f"claimed {required}, found {len(evidence_rows)} evidence rows"
                ),
                evidence=(
                    "For any 'N missing'/'N NOT_FOUND' report, include one bullet/table "
                    "row per item with the checked path or command evidence."
                ),
            )
        )
    return findings


def scoped_claim_text(text: str) -> str:
    """Return only lines that intentionally carry high-stakes status claims.

    Commit bodies and push ranges often contain examples, changelog prose, or
    implementation descriptions with words like "wired" or "archived". Treating
    the whole body as an agent claim produced false positives. ADR-133 moves the
    commit-boundary gate to scoped semantic lines: RESULT:, STATUS:, explicit
    "done <number> <noun>" completion claims, or a commit subject that starts
    with a high-stakes verb. This keeps ``git commit -m "archived hooks/foo.sh"``
    verifiable without treating conventional-commit prose like
    ``docs: wired core.hooksPath example`` as an operational claim.
    """
    raw_lines = text.splitlines()
    lines = [line for line in raw_lines if SCOPED_CLAIM_LINE.search(line)]
    first_nonempty = next((line for line in raw_lines if line.strip()), "")
    if first_nonempty and first_nonempty not in lines and SUBJECT_CLAIM_LINE.search(first_nonempty):
        lines.insert(0, first_nonempty)
    return "\n".join(lines)


def commit_range(root: Path) -> list[str]:
    branch_proc = run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    if branch_proc.returncode != 0:
        return []
    branch = branch_proc.stdout.strip()
    upstream = f"origin/{branch}"
    upstream_proc = run_git(root, ["rev-parse", "--verify", upstream])
    if upstream_proc.returncode != 0:
        return []
    log_proc = run_git(root, ["log", "--format=%B%x1e", f"{upstream}..HEAD"])
    if log_proc.returncode != 0:
        return []
    return [entry.strip() for entry in log_proc.stdout.split("\x1e") if entry.strip()]




def _commit_subjects(root: Path, rev_range: str) -> list[tuple[str, str]]:
    proc = run_git(root, ["log", "--format=%H%x1f%s", rev_range])
    if proc.returncode != 0:
        return []
    rows: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        if "\x1f" not in line:
            continue
        sha, subject = line.split("\x1f", 1)
        rows.append((sha.strip(), subject.strip()))
    return rows


def _patch_id(root: Path, sha: str) -> str | None:
    show = run_git(root, ["show", "--format=", "--no-ext-diff", sha])
    if show.returncode != 0:
        return None
    proc = subprocess.run(
        ["git", "patch-id", "--stable"],
        cwd=str(root),
        input=show.stdout,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return proc.stdout.split()[0]


def verify_push_collisions(root: Path) -> list[GateFinding]:
    branch_proc = run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    if branch_proc.returncode != 0:
        return []
    branch = branch_proc.stdout.strip()
    upstream = f"origin/{branch}"
    if run_git(root, ["rev-parse", "--verify", upstream]).returncode != 0:
        return []
    local = _commit_subjects(root, f"{upstream}..HEAD")
    if not local:
        return []
    recent = _commit_subjects(root, f"{upstream}~200..{upstream}") or _commit_subjects(root, upstream)
    recent_by_subject: dict[str, list[str]] = {}
    for sha, subject in recent:
        if subject:
            recent_by_subject.setdefault(subject, []).append(sha)
    findings: list[GateFinding] = []
    for local_sha, subject in local:
        if not subject or subject not in recent_by_subject:
            continue
        local_pid = _patch_id(root, local_sha)
        remote_pids = {pid for sha in recent_by_subject[subject] if (pid := _patch_id(root, sha))}
        verdict = "same patch-id already landed" if local_pid and local_pid in remote_pids else "same subject landed with different content"
        findings.append(
            GateFinding(
                source=f"unpushed-commit:{local_sha[:12]}",
                status="FAIL",
                message=f"push collision: subject already exists on {upstream}: {subject}",
                evidence=f"{verdict}; inspect origin before push, then drop/merge/rename intentionally",
            )
        )
    return findings


def _patch_id_from_diff(root: Path, diff_text: str) -> str | None:
    if not diff_text.strip():
        return None
    proc = subprocess.run(
        ["git", "patch-id", "--stable"],
        cwd=str(root),
        input=diff_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return proc.stdout.split()[0]


def staged_patch_id(root: Path) -> str | None:
    diff = run_git(root, ["diff", "--cached", "--no-ext-diff", "--binary"])
    if diff.returncode != 0:
        return None
    return _patch_id_from_diff(root, diff.stdout)


def _first_existing_ref(root: Path, refs: Sequence[str]) -> str | None:
    for ref in refs:
        if run_git(root, ["rev-parse", "--verify", ref]).returncode == 0:
            return ref
    return None


def recent_patch_ids(root: Path, base_ref: str, limit: int = 200) -> dict[str, list[str]]:
    log = run_git(root, ["log", f"--max-count={limit}", "--format=%H", base_ref])
    if log.returncode != 0:
        return {}
    by_patch: dict[str, list[str]] = {}
    for sha in (line.strip() for line in log.stdout.splitlines() if line.strip()):
        pid = _patch_id(root, sha)
        if pid:
            by_patch.setdefault(pid, []).append(sha)
    return by_patch


def verify_staged_patch_id_dedupe(root: Path) -> list[GateFinding]:
    staged_pid = staged_patch_id(root)
    if not staged_pid:
        return []
    base_ref = _first_existing_ref(root, ["origin/main", "main"])
    if not base_ref:
        return []
    recent = recent_patch_ids(root, base_ref)
    matches = recent.get(staged_pid, [])
    if not matches:
        return []
    sha_list = ", ".join(sha[:12] for sha in matches[:5])
    return [
        GateFinding(
            source="staged-diff",
            status="FAIL",
            message=f"duplicate staged diff: patch-id already exists on {base_ref}",
            evidence=f"patch-id={staged_pid}; matching commit(s): {sha_list}; skip/drop duplicate work or rebase before committing",
        )
    ]

def evaluate(root: Path, mode: str, command: str = "", text: str = "") -> GateResult:
    findings: list[GateFinding] = []

    if text:
        findings.extend(verify_text_claims(root, text, "agent-output"))
        findings.extend(verify_aggregate_missing_evidence(text, "agent-output"))

    if mode in {"pre-commit", "pre-push"}:
        findings.extend(verify_staged_plans(root))

    if mode == "pre-commit":
        findings.extend(verify_staged_patch_id_dedupe(root))

    if command:
        subcommand = is_git_commit_or_push(command)
        if subcommand == "commit":
            for idx, message in enumerate(extract_commit_messages(command), start=1):
                findings.extend(verify_text_claims(root, scoped_claim_text(message), f"commit-message:{idx}"))
            if not extract_commit_messages(command):
                findings.append(
                    GateFinding(
                        source="commit-message",
                        status="WARN",
                        message="git commit without inline -m message cannot be claim-verified before editor opens",
                        evidence="run scripts/orchestrator_claim_gate.py --text <message> before committing high-stakes closures",
                    )
                )
        elif subcommand == "push":
            for idx, message in enumerate(commit_range(root), start=1):
                findings.extend(verify_text_claims(root, scoped_claim_text(message), f"unpushed-commit:{idx}"))
            findings.extend(verify_push_collisions(root))

    hard_failures = [f for f in findings if f.status == "FAIL"]
    return GateResult(ok=not hard_failures, findings=findings)


def write_metric(root: Path, result: GateResult, mode: str, command: str) -> None:
    metrics_dir = root / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "orchestrator_claim_gate",
        "mode": mode,
        "ok": result.ok,
        "command_kind": is_git_commit_or_push(command) if command else None,
        "findings": [asdict(f) for f in result.findings],
    }
    with (metrics_dir / "orchestrator-claim-gate.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def format_gate_report(result: GateResult) -> str:
    if not result.findings:
        return "orchestrator-claim-gate: PASS — no high-stakes claims requiring proof detected"
    lines: list[str] = ["orchestrator-claim-gate: %s" % ("PASS" if result.ok else "FAIL")]
    for finding in result.findings:
        lines.append(f"- [{finding.status}] {finding.source}: {finding.message}")
        if finding.evidence:
            lines.append(f"  evidence: {finding.evidence}")
    return "\n".join(lines)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    parser.add_argument("--mode", choices=["check", "pre-commit", "pre-push"], default="check")
    parser.add_argument("--command", default="", help="Bash command about to run, usually from a PreToolUse hook")
    parser.add_argument("--text", default="", help="Agent/subagent output or commit text to verify")
    parser.add_argument("--stdin", action="store_true", help="Read text to verify from stdin")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--metrics", action="store_true", help="Append result to .cognitive-os/metrics/orchestrator-claim-gate.jsonl")
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.project_dir).resolve()
    text = args.text
    if args.stdin:
        text = sys.stdin.read()
    result = evaluate(root, args.mode, command=args.command, text=text)
    if args.metrics:
        write_metric(root, result, args.mode, args.command)
    if args.json:
        print(json.dumps({"ok": result.ok, "findings": [asdict(f) for f in result.findings]}, indent=2, sort_keys=True))
    else:
        print(format_gate_report(result))
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
