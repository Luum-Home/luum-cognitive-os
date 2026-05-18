# SCOPE: both
"""Harness action receipt schema and VCS trust promotion helpers.

Receipts are vendor-neutral telemetry for actions reported by IDE/CLI harnesses.
A raw harness directive is advisory until local repository evidence promotes it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "harness-action-receipt.v1"
DEFAULT_METRICS_PATH = Path(".cognitive-os/metrics/vcs-actions.jsonl")
TRUST_LEVELS = ("advisory", "observed", "verified", "authoritative")
TRUST_RANK = {name: idx for idx, name in enumerate(TRUST_LEVELS)}
VCS_EVENTS = frozenset(
    {
        "vcs.stage",
        "vcs.unstage",
        "vcs.commit",
        "vcs.branch.create",
        "vcs.push",
        "vcs.push.blocked",
        "vcs.pr.create",
        "vcs.merge.enqueue",
        "vcs.merge.land",
        "vcs.merge.fail",
        "vcs.bypass",
        "vcs.conflict.detected",
    }
)
ACTION_BY_EVENT = {
    "vcs.stage": "stage",
    "vcs.unstage": "unstage",
    "vcs.commit": "commit",
    "vcs.branch.create": "branch.create",
    "vcs.push": "push",
    "vcs.push.blocked": "push.blocked",
    "vcs.pr.create": "pr.create",
    "vcs.merge.enqueue": "merge.enqueue",
    "vcs.merge.land": "merge.land",
    "vcs.merge.fail": "merge.fail",
    "vcs.bypass": "bypass",
    "vcs.conflict.detected": "conflict.detected",
}
DIRECTIVE_EVENT = {
    "git-stage": "vcs.stage",
    "git-commit": "vcs.commit",
    "git-push": "vcs.push",
    "git-create-branch": "vcs.branch.create",
    "git-create-pr": "vcs.pr.create",
}
DIRECTIVE_RE = re.compile(r"::(?P<name>git-[a-z-]+)\{(?P<body>[^}]*)\}")
DIRECTIVE_ATTR_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_-]*)=(?P<value>\"[^\"]*\"|[^\s]+)")


@dataclass(frozen=True)
class HarnessActionReceipt:
    """One normalized action receipt."""

    event_type: str
    provider: str
    source: str
    trust: str = "advisory"
    project_dir: str = ""
    domain: str = "vcs"
    action: str = ""
    branch: str | None = None
    session_id: str | None = None
    actor: str | None = None
    files: list[str] = field(default_factory=list)
    commit_sha: str | None = None
    remote: str | None = None
    protected_branch: bool | None = None
    governed_path: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable mapping, omitting empty optional values."""
        raw = asdict(self)
        if not raw["action"]:
            raw["action"] = _event_action(self.event_type)
        return {key: value for key, value in raw.items() if value not in (None, "", [], {})}


class ReceiptError(ValueError):
    """Raised when a receipt is malformed or cannot be promoted."""


def _run_git(project_dir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(project_dir),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )


def resolve_project_dir(raw: str | None = None) -> Path:
    """Resolve the project directory using explicit input, COS env, or cwd."""
    value = raw or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.environ.get("CODEX_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(value).expanduser().resolve()


def current_branch(project_dir: Path) -> str | None:
    """Return current branch or None when unavailable."""
    proc = _run_git(project_dir, ["branch", "--show-current"])
    branch = proc.stdout.strip()
    return branch or None


def current_head(project_dir: Path) -> str | None:
    """Return current HEAD SHA or None when unavailable."""
    proc = _run_git(project_dir, ["rev-parse", "HEAD"])
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def remote_head(project_dir: Path, remote: str, branch: str) -> str | None:
    """Return the remote branch SHA using live remote query, then local tracking fallback."""
    proc = _run_git(project_dir, ["ls-remote", "--heads", remote, branch])
    if proc.returncode == 0 and proc.stdout.strip():
        first = proc.stdout.splitlines()[0].split()
        if first:
            return first[0]
    proc = _run_git(project_dir, ["rev-parse", f"refs/remotes/{remote}/{branch}"])
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    return None


def staged_files(project_dir: Path) -> list[str]:
    """Return staged file paths relative to the repository root."""
    proc = _run_git(project_dir, ["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line.strip()]


def _event_action(event_type: str) -> str:
    return ACTION_BY_EVENT.get(event_type, event_type.split(".", 1)[-1])


def validate_receipt(receipt: Mapping[str, Any]) -> None:
    """Validate a receipt dictionary against the v1 structural contract."""
    required = ("schema_version", "event_type", "domain", "provider", "source", "trust", "timestamp")
    missing = [field for field in required if not receipt.get(field)]
    if missing:
        raise ReceiptError(f"missing required receipt fields: {', '.join(missing)}")
    if receipt["schema_version"] != SCHEMA_VERSION:
        raise ReceiptError(f"unsupported schema_version: {receipt['schema_version']!r}")
    if receipt["domain"] != "vcs":
        raise ReceiptError(f"unsupported receipt domain: {receipt['domain']!r}")
    if receipt["event_type"] not in VCS_EVENTS:
        raise ReceiptError(f"unsupported VCS event_type: {receipt['event_type']!r}")
    if receipt["trust"] not in TRUST_RANK:
        raise ReceiptError(f"unsupported trust level: {receipt['trust']!r}")
    evidence = receipt.get("evidence", {})
    if evidence is not None and not isinstance(evidence, Mapping):
        raise ReceiptError("receipt evidence must be an object")


def make_receipt(
    *,
    event_type: str,
    provider: str,
    source: str,
    trust: str = "advisory",
    project_dir: str | Path | None = None,
    branch: str | None = None,
    session_id: str | None = None,
    actor: str | None = None,
    files: Iterable[str] | None = None,
    commit_sha: str | None = None,
    remote: str | None = None,
    protected_branch: bool | None = None,
    governed_path: str | None = None,
    evidence: Mapping[str, Any] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build and validate one normalized receipt dictionary."""
    root = resolve_project_dir(str(project_dir) if project_dir else None)
    receipt = HarnessActionReceipt(
        event_type=event_type,
        provider=provider,
        source=source,
        trust=trust,
        project_dir=str(root),
        action=_event_action(event_type),
        branch=branch or current_branch(root),
        session_id=session_id or os.environ.get("COGNITIVE_OS_SESSION_ID") or os.environ.get("CODEX_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID"),
        actor=actor or os.environ.get("COS_ACTOR") or os.environ.get("COGNITIVE_OS_ACTOR"),
        files=list(files or []),
        commit_sha=commit_sha,
        remote=remote,
        protected_branch=protected_branch,
        governed_path=governed_path,
        evidence=dict(evidence or {}),
        timestamp=timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    ).to_dict()
    validate_receipt(receipt)
    return receipt


def promote_with_git_observation(receipt: Mapping[str, Any], project_dir: str | Path | None = None) -> dict[str, Any]:
    """Promote advisory VCS receipts to observed when local Git state supports them."""
    promoted = dict(receipt)
    root = resolve_project_dir(str(project_dir) if project_dir else str(promoted.get("project_dir") or ""))
    event_type = str(promoted.get("event_type") or "")
    evidence = dict(promoted.get("evidence") or {})

    if TRUST_RANK.get(str(promoted.get("trust")), -1) >= TRUST_RANK["verified"]:
        validate_receipt(promoted)
        return promoted

    if event_type == "vcs.stage":
        staged = staged_files(root)
        if not staged:
            raise ReceiptError("cannot promote vcs.stage: no staged files observed")
        promoted["files"] = staged
        evidence["observed_git_status"] = {"staged_files": staged}
    elif event_type == "vcs.commit":
        head = current_head(root)
        if not head:
            raise ReceiptError("cannot promote vcs.commit: HEAD not observed")
        promoted["commit_sha"] = head
        evidence["observed_git_status"] = {"head": head}
    elif event_type == "vcs.branch.create":
        branch = current_branch(root)
        if not branch:
            raise ReceiptError("cannot promote vcs.branch.create: branch not observed")
        promoted["branch"] = branch
        evidence["observed_git_status"] = {"branch": branch}
    elif event_type == "vcs.push":
        remote = str(promoted.get("remote") or evidence.get("remote") or "origin")
        branch = str(promoted.get("branch") or current_branch(root) or "")
        if not branch:
            raise ReceiptError("cannot promote vcs.push: branch not observed")
        local_sha = str(promoted.get("commit_sha") or current_head(root) or "")
        remote_sha = remote_head(root, remote, branch)
        if not local_sha or not remote_sha:
            raise ReceiptError("cannot promote vcs.push: local or remote ref not observed")
        if local_sha != remote_sha:
            raise ReceiptError("cannot promote vcs.push: remote ref does not match local commit")
        promoted["branch"] = branch
        promoted["remote"] = remote
        promoted["commit_sha"] = local_sha
        evidence["observed_git_status"] = {
            "branch": branch,
            "local_sha": local_sha,
            "remote": remote,
            "remote_sha": remote_sha,
        }
    else:
        raise ReceiptError(f"no local Git promotion rule for {event_type}")

    promoted["trust"] = "observed"
    promoted["source"] = "local-git-observation" if promoted.get("source") == "harness-directive" else promoted["source"]
    promoted["evidence"] = evidence
    validate_receipt(promoted)
    return promoted


def promote_with_pre_push_evidence(receipt: Mapping[str, Any], pre_push_refs: str) -> dict[str, Any]:
    """Promote a push receipt to verified when a pre-push hook observed matching refs."""
    promoted = dict(receipt)
    if promoted.get("event_type") != "vcs.push":
        raise ReceiptError("pre-push evidence only applies to vcs.push receipts")
    branch = str(promoted.get("branch") or "")
    commit_sha = str(promoted.get("commit_sha") or "")
    if not branch:
        raise ReceiptError("cannot verify push: branch is required")
    matched = False
    parsed_refs: list[dict[str, str]] = []
    for raw in pre_push_refs.splitlines():
        parts = raw.split()
        if len(parts) < 4:
            continue
        local_ref, local_sha, remote_ref, remote_sha = parts[:4]
        parsed_refs.append(
            {"local_ref": local_ref, "local_sha": local_sha, "remote_ref": remote_ref, "remote_sha": remote_sha}
        )
        ref_branch = remote_ref.removeprefix("refs/heads/")
        if ref_branch == branch and (not commit_sha or local_sha == commit_sha):
            matched = True
            promoted["commit_sha"] = local_sha
    if not matched:
        raise ReceiptError("cannot verify push: pre-push refs do not match receipt branch/commit")
    evidence = dict(promoted.get("evidence") or {})
    evidence["pre_push"] = {"refs": parsed_refs}
    promoted["trust"] = "verified"
    promoted["source"] = "git-hook" if promoted.get("source") == "harness-directive" else promoted["source"]
    promoted["governed_path"] = promoted.get("governed_path") or "pre-push"
    promoted["evidence"] = evidence
    validate_receipt(promoted)
    return promoted


def promote_with_provider_evidence(receipt: Mapping[str, Any], provider_evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Promote push/PR/merge receipts with provider API acceptance evidence."""
    promoted = dict(receipt)
    if not provider_evidence.get("accepted"):
        raise ReceiptError("provider evidence must include accepted=true")
    evidence = dict(promoted.get("evidence") or {})
    evidence["provider_api"] = dict(provider_evidence)
    if provider_evidence.get("remote_ref_sha"):
        promoted["commit_sha"] = str(provider_evidence["remote_ref_sha"])
    if provider_evidence.get("branch"):
        promoted["branch"] = str(provider_evidence["branch"])
    if provider_evidence.get("remote"):
        promoted["remote"] = str(provider_evidence["remote"])
    promoted["trust"] = "authoritative"
    promoted["source"] = "provider-api"
    promoted["evidence"] = evidence
    validate_receipt(promoted)
    return promoted


def append_receipt(receipt: Mapping[str, Any], *, project_dir: str | Path | None = None, metrics_path: str | Path | None = None) -> Path:
    """Append a validated receipt to a JSONL metrics file and return its path."""
    validate_receipt(receipt)
    root = resolve_project_dir(str(project_dir) if project_dir else str(receipt.get("project_dir") or ""))
    path = Path(metrics_path).expanduser().resolve() if metrics_path else root / DEFAULT_METRICS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dict(receipt), sort_keys=True, ensure_ascii=False) + "\n")
    return path


def load_receipts(*, project_dir: str | Path | None = None, metrics_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load valid receipts from JSONL, skipping malformed lines."""
    root = resolve_project_dir(str(project_dir) if project_dir else None)
    path = Path(metrics_path).expanduser().resolve() if metrics_path else root / DEFAULT_METRICS_PATH
    receipts: list[dict[str, Any]] = []
    if not path.exists():
        return receipts
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            receipt = json.loads(raw)
            validate_receipt(receipt)
        except (json.JSONDecodeError, ReceiptError):
            continue
        receipts.append(receipt)
    return receipts


def receipt_stats(*, project_dir: str | Path | None = None, metrics_path: str | Path | None = None) -> dict[str, Any]:
    """Return dashboard/report-friendly counts by trust, event, and source."""
    receipts = load_receipts(project_dir=project_dir, metrics_path=metrics_path)
    by_trust = Counter(str(receipt.get("trust", "unknown")) for receipt in receipts)
    by_event_type = Counter(str(receipt.get("event_type", "unknown")) for receipt in receipts)
    by_source = Counter(str(receipt.get("source", "unknown")) for receipt in receipts)
    by_trust_event = Counter(
        f"{receipt.get('trust', 'unknown')}:{receipt.get('event_type', 'unknown')}" for receipt in receipts
    )
    return {
        "schema_version": "harness-action-receipt-stats.v1",
        "total": len(receipts),
        "by_trust": dict(sorted(by_trust.items())),
        "by_event_type": dict(sorted(by_event_type.items())),
        "by_source": dict(sorted(by_source.items())),
        "by_trust_event": dict(sorted(by_trust_event.items())),
        "authoritative": by_trust.get("authoritative", 0),
        "verified": by_trust.get("verified", 0),
        "observed": by_trust.get("observed", 0),
        "advisory": by_trust.get("advisory", 0),
    }


def render_markdown_report(stats: Mapping[str, Any]) -> str:
    """Render receipt stats as a compact Markdown report."""
    lines = [
        "# VCS Action Receipts",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Total receipts | {int(stats.get('total', 0))} |",
        f"| Advisory | {int(stats.get('advisory', 0))} |",
        f"| Observed | {int(stats.get('observed', 0))} |",
        f"| Verified | {int(stats.get('verified', 0))} |",
        f"| Authoritative | {int(stats.get('authoritative', 0))} |",
        "",
        "## By trust",
        "",
        "| Trust | Count |",
        "|---|---:|",
    ]
    for trust, count in dict(stats.get("by_trust", {})).items():
        lines.append(f"| `{trust}` | {count} |")
    lines.extend(["", "## By event type", "", "| Event | Count |", "|---|---:|"])
    for event_type, count in dict(stats.get("by_event_type", {})).items():
        lines.append(f"| `{event_type}` | {count} |")
    lines.extend(["", "## By source", "", "| Source | Count |", "|---|---:|"])
    for source, count in dict(stats.get("by_source", {})).items():
        lines.append(f"| `{source}` | {count} |")
    lines.append("")
    return "\n".join(lines)


def _parse_directive_attrs(body: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in DIRECTIVE_ATTR_RE.finditer(body):
        value = match.group("value")
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        attrs[match.group("key")] = value
    return attrs


def receipts_from_codex_directives(text: str, *, provider: str = "codex-desktop") -> list[dict[str, Any]]:
    """Parse Codex-style ::git-* directives into advisory VCS receipts."""
    receipts: list[dict[str, Any]] = []
    for match in DIRECTIVE_RE.finditer(text):
        name = match.group("name")
        event_type = DIRECTIVE_EVENT.get(name)
        if not event_type:
            continue
        attrs = _parse_directive_attrs(match.group("body"))
        cwd = attrs.get("cwd")
        branch = attrs.get("branch")
        commit_sha = attrs.get("commit") or attrs.get("sha")
        remote = attrs.get("remote")
        evidence = {"directive": match.group(0), "directive_attrs": attrs}
        receipts.append(
            make_receipt(
                event_type=event_type,
                provider=provider,
                source="harness-directive",
                trust="advisory",
                project_dir=cwd,
                branch=branch,
                commit_sha=commit_sha,
                remote=remote,
                evidence=evidence,
            )
        )
    return receipts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create and validate Cognitive OS harness action receipts")
    sub = parser.add_subparsers(dest="command", required=True)

    emit = sub.add_parser("emit", help="Create one receipt from CLI flags")
    emit.add_argument("event_type", choices=sorted(VCS_EVENTS))
    emit.add_argument("--provider", required=True)
    emit.add_argument("--source", required=True)
    emit.add_argument("--trust", default="advisory", choices=TRUST_LEVELS)
    emit.add_argument("--project-dir")
    emit.add_argument("--branch")
    emit.add_argument("--session-id")
    emit.add_argument("--actor")
    emit.add_argument("--file", action="append", dest="files", default=[])
    emit.add_argument("--commit-sha")
    emit.add_argument("--remote")
    emit.add_argument("--protected-branch", action="store_true")
    emit.add_argument("--governed-path")
    emit.add_argument("--evidence-json", default="{}")
    emit.add_argument("--promote-git", action="store_true")
    emit.add_argument("--pre-push-refs", default=None, help="Pre-push refs text, '-' for stdin, or @file")
    emit.add_argument("--provider-evidence-json", default=None, help="Provider API acceptance evidence JSON")
    emit.add_argument("--append", action="store_true")
    emit.add_argument("--metrics-path")
    emit.add_argument("--json", action="store_true")

    parse = sub.add_parser("parse-codex", help="Parse Codex ::git-* directives from text/stdin")
    parse.add_argument("--text", default="-", help="Text, '-' for stdin, or @file")
    parse.add_argument("--provider", default="codex-desktop")
    parse.add_argument("--promote-git", action="store_true")
    parse.add_argument("--append", action="store_true")
    parse.add_argument("--metrics-path")
    parse.add_argument("--json", action="store_true")

    validate = sub.add_parser("validate", help="Validate receipt JSON from stdin or @file")
    validate.add_argument("receipt_json", nargs="?", default="-")
    validate.add_argument("--append", action="store_true")
    validate.add_argument("--metrics-path")
    validate.add_argument("--json", action="store_true")

    stats = sub.add_parser("stats", help="Summarize receipt metrics by trust/event/source")
    stats.add_argument("--project-dir")
    stats.add_argument("--metrics-path")
    stats.add_argument("--json", action="store_true")

    report = sub.add_parser("report", help="Write a Markdown receipt summary report")
    report.add_argument("--project-dir")
    report.add_argument("--metrics-path")
    report.add_argument("--output", default="docs/06-Daily/reports/vcs-action-receipts-latest.md")
    report.add_argument("--json", action="store_true")
    return parser


def _read_arg(value: str) -> str:
    if value == "-":
        return sys.stdin.read()
    if value.startswith("@"):
        return Path(value[1:]).read_text(encoding="utf-8")
    return value


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "emit":
            evidence = json.loads(args.evidence_json)
            receipt = make_receipt(
                event_type=args.event_type,
                provider=args.provider,
                source=args.source,
                trust=args.trust,
                project_dir=args.project_dir,
                branch=args.branch,
                session_id=args.session_id,
                actor=args.actor,
                files=args.files,
                commit_sha=args.commit_sha,
                remote=args.remote,
                protected_branch=True if args.protected_branch else None,
                governed_path=args.governed_path,
                evidence=evidence,
            )
            if args.promote_git:
                receipt = promote_with_git_observation(receipt, args.project_dir)
            if args.pre_push_refs is not None:
                receipt = promote_with_pre_push_evidence(receipt, _read_arg(args.pre_push_refs))
            if args.provider_evidence_json is not None:
                receipt = promote_with_provider_evidence(receipt, json.loads(args.provider_evidence_json))
            if args.append:
                append_receipt(receipt, project_dir=args.project_dir, metrics_path=args.metrics_path)
            print(json.dumps(receipt, indent=2 if args.json else None, sort_keys=True))
            return 0
        if args.command == "parse-codex":
            text = _read_arg(args.text)
            receipts = receipts_from_codex_directives(text, provider=args.provider)
            if args.promote_git:
                receipts = [promote_with_git_observation(receipt) for receipt in receipts]
            if args.append:
                for receipt in receipts:
                    append_receipt(receipt, metrics_path=args.metrics_path)
            print(json.dumps(receipts, indent=2 if args.json else None, sort_keys=True))
            return 0
        if args.command == "stats":
            stats = receipt_stats(project_dir=args.project_dir, metrics_path=args.metrics_path)
            print(json.dumps(stats, indent=2 if args.json else None, sort_keys=True))
            return 0
        if args.command == "report":
            stats = receipt_stats(project_dir=args.project_dir, metrics_path=args.metrics_path)
            root = resolve_project_dir(args.project_dir)
            output = Path(args.output)
            if not output.is_absolute():
                output = root / output
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(render_markdown_report(stats), encoding="utf-8")
            payload = {"output": str(output), "stats": stats}
            print(json.dumps(payload, indent=2 if args.json else None, sort_keys=True))
            return 0
        raw = json.loads(_read_arg(args.receipt_json))
        validate_receipt(raw)
        if args.append:
            append_receipt(raw, metrics_path=args.metrics_path)
        print(json.dumps(raw, indent=2 if args.json else None, sort_keys=True))
        return 0
    except (json.JSONDecodeError, ReceiptError, OSError) as exc:
        print(f"cos-action-receipt: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
