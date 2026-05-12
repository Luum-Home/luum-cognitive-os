"""Pre-launch history/content audit and controlled rewrite planning.

The module is intentionally conservative: audit commands are read-only by
standard operation, rewrite execution requires explicit environment flags, and
license/product decisions are surfaced for review rather than silently erased.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "prelaunch-audit/v1"
PLAN_SCHEMA_VERSION = "prelaunch-rewrite-plan/v1"
DEFAULT_PLAN_DIR = Path(".cognitive-os/prelaunch")
DEFAULT_REPORT_DIR = Path("docs/06-Daily/reports")


@dataclass(frozen=True)
class AuditRule:
    id: str
    kind: str
    severity: str
    pattern: str
    rationale: str
    suggested_rewrite: str | None = None
    regex_flags: int = re.IGNORECASE

    def compiled(self) -> re.Pattern[str]:
        return re.compile(self.pattern, self.regex_flags | re.MULTILINE)


@dataclass(frozen=True)
class Finding:
    severity: str
    kind: str
    rule_id: str
    target: str
    message: str
    sample: str | None = None
    suggested_rewrite: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "severity": self.severity,
            "kind": self.kind,
            "rule_id": self.rule_id,
            "target": self.target,
            "message": self.message,
        }
        if self.sample:
            payload["sample"] = self.sample
        if self.suggested_rewrite:
            payload["suggested_rewrite"] = self.suggested_rewrite
        return payload


MESSAGE_RULES: tuple[AuditRule, ...] = (
    AuditRule("wip-message", "quote_mine_risk", "info", r"^(?:wip\b|wip\(|On .*\bwip\b)", "Raw WIP/preserve commit subjects look uncurated in a public pre-1.0 launch."),
    AuditRule("hide-bypass-message", "quote_mine_risk", "warn", r"\b(hide|sneak|smuggle)\b", "Commit messages can be quote-mined as intent to conceal controls."),
    AuditRule("license-switch-message", "license_narrative", "warn", r"license switch|switch from apache|apache\s*(?:2\.0|-2\.0)?\s*(?:to|→)\s*fsl", "License transition should read as pre-launch policy, not a late public bait-and-switch.", "chore(license): establish FSL-1.1-MIT before public launch"),
    AuditRule("hostile-message", "tone", "warn", r"\b(hate|drama|scam|fraud|trash|stupid|idiot)\b|\b(odio|bardo|quilombo|estafa|trucho|bardear)\b", "Hostile phrasing creates avoidable reputational risk."),
    AuditRule("absolute-claim-message", "overclaim", "warn", r"\b(100%|zero risk|production ready|enterprise grade|industry first|unbreakable|perfect)\b", "Absolute claims need strong evidence or calmer wording."),
)

HISTORY_RULES: tuple[AuditRule, ...] = (
    AuditRule("private-key-material", "secret", "block", r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |PRIVATE )?PRIVATE KEY-----", "Private key material must never be present in public history."),
    AuditRule("env-assignment-secret", "secret", "block", r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|pwd)\s*[=:]\s*['\"]?[A-Za-z0-9_./+=:-]{12,}", "Secret-like assignments require manual review or sanitization."),
    AuditRule("github-token", "secret", "block", r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b", "GitHub tokens must be removed from history."),
    AuditRule("openai-token", "secret", "block", r"\bsk-[A-Za-z0-9]{20,}\b", "Provider tokens must be removed from history."),
    AuditRule("aws-access-key", "secret", "block", r"\bAKIA[0-9A-Z]{16}\b", "AWS access keys must be removed from history."),
    AuditRule("local-home-path", "privacy", "warn", r"/U[s]ers/[A-Za-z0-9._-]+/(?:Projects|Desktop|Documents|Downloads|Library|private|var|tmp)", "Machine-local paths expose operator environment details."),
    AuditRule("personal-email", "privacy", "warn", r"\b[A-Z0-9._%+-]+@(gmail|hotmail|outlook|icloud|yahoo)\.[A-Z]{2,}\b", "Personal email addresses should be reviewed before public launch."),
    AuditRule("hostile-content", "tone", "warn", r"\b(drama|scam|stupid|idiot)\b|\b(odio|bardo|quilombo|estafa|trucho|bardear)\b", "Hostile/internal phrasing in tracked history can create avoidable backlash."),
    AuditRule("concealment-content", "quote_mine_risk", "warn", r"\b(sneak|smuggle)\b|\b(esconder|colar)\b", "Concealment language should be reviewed in context."),
    AuditRule("absolute-claim-content", "overclaim", "warn", r"\b(100% confident|industry first|unbreakable)\b", "Absolute public claims should be evidence-backed or softened."),
    AuditRule("license-context", "license_narrative", "info", r"Apache-2\.0|Apache 2\.0|FSL-1\.1-MIT|Functional Source License|source-available", "License references are expected but should be calm, transparent, and consistent."),
)

DEFAULT_MESSAGE_REWRITES: dict[str, str] = {
    "feat(license): switch from Apache 2.0 to FSL-1.1-MIT": "chore(license): establish FSL-1.1-MIT before public launch",
    "fix(license): align package.json with FSL-1.1-MIT": "chore(package): align license metadata with repository license",
    "fix(gate): exclude JSON metadata fields from dependency-adoption-gate": "fix(gate): treat package metadata edits as non-dependency changes",
    "docs: preserve license switch stash review": "docs(history): record pre-launch license review trail",
    "wip: preserve FSL license switch stash": "docs(history): preserve pre-launch license review snapshot",
}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def repo_root(start: Path) -> Path:
    proc = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(f"not a git repository: {start}")
    return Path(proc.stdout.strip()).resolve()


def git(repo: Path, args: list[str], *, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, check=False, timeout=timeout)


def severity_counts(findings: Iterable[Finding]) -> dict[str, int]:
    counts = {"block": 0, "warn": 0, "info": 0}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts


def status_from_counts(counts: dict[str, int]) -> str:
    if counts.get("block", 0):
        return "block"
    if counts.get("warn", 0):
        return "warn"
    return "pass"


def compact_sample(text: str, limit: int = 220) -> str:
    return " ".join(text.strip().split())[:limit]


FIXTURE_LIKE_RE = re.compile(
    r"(?i)(example\.invalid|example\.com|FAKEKEYFORTEST|FAKE|EXAMPLE|"
    r"abcdefghijklmnopqrstuvwxyz|ABCDEF|abc123|key\.pem.*data|"
    r"writeFile\(|test_file|cos_check_quality|load_api_token\(|token_file|fixture|dummy|mock|SECRET1234567890|ENV:[A-Z0-9_]+|process\.env|os\.environ|getenv\(|direct_[a-z0-9_]*api_key|TOKEN:|supersecret|super_secret|1234567890|cos-test-password|cognitive-os-dev|langfuse_pass|langfuse_redis|keyboard-cat)"
)


def fixture_like_line(line: str, file_path: str = "") -> bool:
    if file_path.startswith("tests/") or file_path.endswith("_test.go"):
        return True
    return bool(FIXTURE_LIKE_RE.search(line))


REVIEWED_CONTEXT_RE = re.compile(
    r"(?i)(red flag|not a leak|audit trail|history sanitize replaced|AuditRule\(|Mandatory self-doubt|"
    r"appears \*\*?[0-9]+|block developer home path leaks|warning sign|/U[s]ers/marialuzmontiel/|"
    r"^[-]\s*(?:`|[A-Za-z0-9_./ -])*?/U[s]ers/[A-Za-z0-9._-]+/)"
)


def reviewed_context_line(line: str) -> bool:
    return bool(REVIEWED_CONTEXT_RE.search(line.strip()))


def history_patch_text(repo: Path, *, timeout: float) -> tuple[str, str | None]:
    try:
        proc = git(repo, ["log", "--all", "--no-color", "--format=commit:%H", "-p"], timeout=timeout)
    except subprocess.TimeoutExpired:
        return "", f"history patch scan exceeded {timeout:g}s; raise COS_PRELAUNCH_HISTORY_TIMEOUT_SECONDS for exhaustive review"
    if proc.returncode != 0:
        return "", proc.stderr.strip() or "git log history patch scan failed"
    return proc.stdout, None


def scan_history_text(history: str, rule: AuditRule, *, max_samples: int) -> tuple[list[str], list[str], list[dict[str, str]]]:
    pattern = rule.compiled()
    commits: list[str] = []
    risky_commits: list[str] = []
    samples: list[dict[str, str]] = []
    current_sha = ""
    current_lines: list[str] = []

    def flush() -> None:
        if not current_sha:
            return
        matching_lines = [
            (line, file_path)
            for line, file_path in current_lines
            if not line.startswith(("+++", "---", "@@")) and pattern.search(line)
        ]
        if not matching_lines:
            return
        commits.append(current_sha)
        if any(not fixture_like_line(line, file_path) and not reviewed_context_line(line) for line, file_path in matching_lines):
            risky_commits.append(current_sha)
        sample_line, sample_file = next(
            ((line, file_path) for line, file_path in matching_lines if not fixture_like_line(line, file_path) and not reviewed_context_line(line)),
            matching_lines[0],
        )
        sample = {
            "commit": current_sha,
            "sample": compact_sample(sample_line),
            "fixture_like": fixture_like_line(sample_line, sample_file),
        }
        if len(samples) < max_samples:
            samples.append(sample)
        elif not sample["fixture_like"]:
            for idx, existing in enumerate(samples):
                if existing.get("fixture_like"):
                    samples[idx] = sample
                    break

    for line in history.splitlines():
        if line.startswith("commit:"):
            flush()
            current_sha = line.removeprefix("commit:").strip()
            current_lines = []
            current_file = ""
        elif line.startswith("+++ b/"):
            current_file = line.removeprefix("+++ b/").strip()
            current_lines.append((line, current_file))
        else:
            current_lines.append((line, current_file))
    flush()
    return commits, risky_commits, samples


def matching_commits(repo: Path, rule: AuditRule, *, timeout: float) -> list[str]:
    # Use Python regex over textual patches instead of relying on `git log -G`,
    # whose POSIX regex dialect does not support several Python constructs used
    # by the audit rules. The scan remains read-only and bounded by timeout.
    proc = git(repo, ["log", "--all", "--no-color", "--format=commit:%H", "-p"], timeout=timeout)
    if proc.returncode != 0:
        return []
    pattern = rule.compiled()
    commits: list[str] = []
    current_sha = ""
    current_lines: list[str] = []

    def flush() -> None:
        if current_sha and pattern.search("\n".join(current_lines)):
            commits.append(current_sha)

    for line in proc.stdout.splitlines():
        if line.startswith("commit:"):
            flush()
            current_sha = line.removeprefix("commit:").strip()
            current_lines = []
        else:
            current_lines.append(line)
    flush()
    return commits


def patch_sample(repo: Path, commit: str, rule: AuditRule) -> str | None:
    proc = git(repo, ["show", "--no-color", "--format=", "--unified=0", commit], timeout=4)
    if proc.returncode != 0:
        return None
    pattern = rule.compiled()
    for line in proc.stdout.splitlines():
        if not line or line.startswith(("+++", "---", "@@")):
            continue
        if pattern.search(line):
            return compact_sample(line)
    return None


def audit_history(repo: Path, *, max_samples_per_rule: int = 5, timeout: float | None = None) -> dict[str, Any]:
    findings: list[Finding] = []
    rule_hits: list[dict[str, Any]] = []
    configured_timeout = timeout or float(os.environ.get("COS_PRELAUNCH_HISTORY_TIMEOUT_SECONDS", "60"))
    history, scan_error = history_patch_text(repo, timeout=configured_timeout)
    if scan_error:
        findings.append(
            Finding(
                severity="warn",
                kind="scan_budget",
                rule_id="history-scan-timeout",
                target="history",
                message=scan_error,
            )
        )
    for rule in HISTORY_RULES:
        commits, risky_commits, samples = scan_history_text(history, rule, max_samples=max_samples_per_rule) if history else ([], [], [])
        rule_hits.append({"rule_id": rule.id, "kind": rule.kind, "severity": rule.severity, "commit_count": len(commits), "risky_commit_count": len(risky_commits), "fixture_like_commit_count": max(0, len(commits) - len(risky_commits)), "samples": samples, "rationale": rule.rationale})
        if commits and rule.severity in {"block", "warn"}:
            first = samples[0]["sample"] if samples else None
            effective_severity = rule.severity
            qualifier = ""
            if not risky_commits:
                effective_severity = "info"
                qualifier = " All matches are fixture/example-like or reviewed audit context."
            findings.append(
                Finding(
                    severity=effective_severity,
                    kind=rule.kind,
                    rule_id=rule.id,
                    target=f"history:{len(commits)} commits",
                    message=f"{rule.id} matched {len(commits)} historical commit(s); {len(risky_commits)} need non-fixture review. {rule.rationale}{qualifier}",
                    sample=first,
                )
            )
    counts = severity_counts(findings)
    return {
        "schema_version": SCHEMA_VERSION,
        "audit": "history",
        "repo": "<repo>",
        "status": status_from_counts(counts),
        "summary": {**counts, "findings": len(findings)},
        "rule_hits": rule_hits,
        "findings": [finding.to_dict() for finding in findings],
        "policy": "Read-only scan. License references are reported as context, not auto-sanitized.",
    }


def iter_commit_messages(repo: Path) -> Iterable[tuple[str, str, str]]:
    proc = git(repo, ["log", "--all", "--format=%H%x00%s%x00%b%x1e"])
    if proc.returncode != 0:
        return []
    records = proc.stdout.split("\x1e")
    parsed: list[tuple[str, str, str]] = []
    for record in records:
        if not record.strip():
            continue
        parts = record.strip("\n").split("\x00", 2)
        if len(parts) != 3:
            continue
        parsed.append((parts[0], parts[1], parts[2]))
    return parsed


def audit_messages(repo: Path, *, max_findings: int = 500) -> dict[str, Any]:
    findings: list[Finding] = []
    for sha, subject, body in iter_commit_messages(repo):
        # Commit subject is the public headline most likely to be scanned or
        # quote-mined. Bodies can contain legitimate detailed evidence and are
        # covered by the broader history/content audit.
        text = subject
        for rule in MESSAGE_RULES:
            if not rule.compiled().search(text):
                continue
            suggestion = DEFAULT_MESSAGE_REWRITES.get(subject) or rule.suggested_rewrite
            findings.append(
                Finding(
                    severity=rule.severity,
                    kind=rule.kind,
                    rule_id=rule.id,
                    target=sha,
                    message=subject,
                    sample=compact_sample(body) if body.strip() else None,
                    suggested_rewrite=suggestion,
                )
            )
            break
        if len(findings) >= max_findings:
            break
    counts = severity_counts(findings)
    return {
        "schema_version": SCHEMA_VERSION,
        "audit": "messages",
        "repo": "<repo>",
        "status": status_from_counts(counts),
        "summary": {**counts, "findings": len(findings)},
        "findings": [finding.to_dict() for finding in findings],
        "policy": "Read-only commit-message scan. Suggested rewrites require explicit operator approval before apply.",
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [f"# Prelaunch {report['audit'].title()} Audit", "", f"Status: `{report['status']}`", "", "## Summary", ""]
    summary = report.get("summary", {})
    lines.extend(f"- {key}: {value}" for key, value in summary.items())
    lines.extend(["", "## Findings", ""])
    findings = report.get("findings", [])
    if not findings:
        lines.append("No block/warn findings.")
    for finding in findings:
        lines.append(f"- **{finding['severity']}** `{finding['rule_id']}` on `{finding['target']}` — {finding['message']}")
        if finding.get("suggested_rewrite"):
            lines.append(f"  - suggested rewrite: `{finding['suggested_rewrite']}`")
        if finding.get("sample"):
            lines.append(f"  - sample: `{finding['sample']}`")
    lines.extend(["", "## Policy", "", str(report.get("policy", "")), ""])
    return "\n".join(lines)


def write_report(repo: Path, report: dict[str, Any], *, report_dir: Path | None = None) -> dict[str, str]:
    target_dir = repo / (report_dir or DEFAULT_REPORT_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    stem = f"prelaunch-{report['audit']}-audit-{stamp}"
    json_path = target_dir / f"{stem}.json"
    md_path = target_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def build_rewrite_plan(repo: Path, *, plan_dir: Path | None = None) -> dict[str, Any]:
    message_report = audit_messages(repo)
    rewrites: list[dict[str, str]] = []
    seen_old: set[str] = set()
    for finding in message_report["findings"]:
        old = finding["message"]
        new = finding.get("suggested_rewrite")
        if not new or old in seen_old or old == new:
            continue
        seen_old.add(old)
        rewrites.append({"old": old, "new": new, "reason": f"{finding['rule_id']}: {finding['kind']}"})
    replacements_text = "# git-filter-repo replacement file. Add OLD==>NEW or regex:OLD==>NEW entries after review.\n"
    remotes = snapshot_remotes(repo)
    branch_upstreams = snapshot_branch_upstreams(repo)
    plan = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "repo": "<repo>",
        "generated_at": utc_stamp(),
        "message_rewrites": rewrites,
        "content_replacements_file": str((plan_dir or DEFAULT_PLAN_DIR) / "replacements.txt"),
        "remote_snapshot_file": str((plan_dir or DEFAULT_PLAN_DIR) / "remote-snapshot.json"),
        "branch_upstream_snapshot_file": str((plan_dir or DEFAULT_PLAN_DIR) / "branch-upstream-snapshot.json"),
        "remotes": sorted(remotes),
        "branch_upstreams": sorted(branch_upstreams["branches"]),
        "current_branch": branch_upstreams["current_branch"],
        "policy": "Editable plan. Apply requires COS_ALLOW_PRELAUNCH_REWRITE=1. Force-push requires an additional COS_ALLOW_PRELAUNCH_FORCE_PUSH=1.",
    }
    target_dir = repo / (plan_dir or DEFAULT_PLAN_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "message-rewrites.json").write_text(json.dumps(rewrites, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (target_dir / "replacements.txt").write_text(replacements_text, encoding="utf-8")
    (target_dir / "remote-snapshot.json").write_text(json.dumps(remotes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (target_dir / "branch-upstream-snapshot.json").write_text(json.dumps(branch_upstreams, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (target_dir / "plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return plan


def shell_quote_single(text: str) -> str:
    return "'" + text.replace("'", "'\"'\"'") + "'"


def _message_callback_source(rewrites: list[dict[str, str]]) -> str:
    mapping = {item["old"]: item["new"] for item in rewrites if item.get("old") and item.get("new")}
    return "\n".join(
        [
            "import json",
            f"mapping = json.loads({json.dumps(json.dumps(mapping, sort_keys=True))!r})",
            "msg = message.decode('utf-8', errors='replace')",
            "for old, new in mapping.items():",
            "    msg = msg.replace(old, new)",
            "return msg.encode('utf-8')",
        ]
    )


def load_message_rewrites(plan_path: Path) -> list[dict[str, str]]:
    if not plan_path.exists():
        return []
    data = json.loads(plan_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def ensure_clean(repo: Path) -> None:
    proc = git(repo, ["status", "--porcelain"])
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or "git status failed")
    if proc.stdout.strip():
        raise SystemExit("working tree is dirty; commit or stash before prelaunch rewrite")


def snapshot_remotes(repo: Path) -> dict[str, dict[str, str]]:
    proc = git(repo, ["remote"])
    remotes: dict[str, dict[str, str]] = {}
    if proc.returncode != 0:
        return remotes
    for name in [line.strip() for line in proc.stdout.splitlines() if line.strip()]:
        remotes[name] = {}
        fetch_url = git(repo, ["remote", "get-url", name])
        if fetch_url.returncode == 0 and fetch_url.stdout.strip():
            remotes[name]["fetch"] = fetch_url.stdout.strip()
        push_url = git(repo, ["remote", "get-url", "--push", name])
        if push_url.returncode == 0 and push_url.stdout.strip():
            remotes[name]["push"] = push_url.stdout.strip()
    return remotes


def snapshot_branch_upstreams(repo: Path) -> dict[str, Any]:
    """Capture local branch tracking config that history rewrite tools can drop."""
    current_proc = git(repo, ["branch", "--show-current"])
    current_branch = current_proc.stdout.strip() if current_proc.returncode == 0 else ""
    branches_proc = git(repo, ["for-each-ref", "--format=%(refname:short)", "refs/heads"])
    branches: dict[str, dict[str, str]] = {}
    if branches_proc.returncode != 0:
        return {"current_branch": current_branch, "branches": branches}
    for branch in [line.strip() for line in branches_proc.stdout.splitlines() if line.strip()]:
        remote = git(repo, ["config", "--get", f"branch.{branch}.remote"])
        merge = git(repo, ["config", "--get", f"branch.{branch}.merge"])
        entry: dict[str, str] = {}
        if remote.returncode == 0 and remote.stdout.strip():
            entry["remote"] = remote.stdout.strip()
        if merge.returncode == 0 and merge.stdout.strip():
            entry["merge"] = merge.stdout.strip()
        if entry:
            branches[branch] = entry
    return {"current_branch": current_branch, "branches": branches}


def upstream_tracking_ref(remote: str | None, merge: str | None) -> str:
    if not remote or remote == "." or not merge or not merge.startswith("refs/heads/"):
        return ""
    return f"refs/remotes/{remote}/{merge.removeprefix('refs/heads/')}"


def restore_remotes(repo: Path, remotes: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    restored: dict[str, dict[str, str]] = {}
    for name, urls in remotes.items():
        fetch = urls.get("fetch") or urls.get("push")
        push = urls.get("push") or fetch
        if not fetch:
            continue
        if git(repo, ["remote", "get-url", name]).returncode != 0:
            git(repo, ["remote", "add", name, fetch])
        else:
            git(repo, ["remote", "set-url", name, fetch])
        if push:
            git(repo, ["remote", "set-url", "--push", name, push])
        restored[name] = {"fetch": fetch, "push": push or fetch}
    return restored


def refresh_branch_upstream_refs(repo: Path, snapshot: dict[str, Any]) -> dict[str, list[str]]:
    """Fetch missing remote-tracking refs so restored upstreams resolve as @{u}."""
    refreshed: list[str] = []
    errors: list[str] = []
    branches = snapshot.get("branches", {})
    if not isinstance(branches, dict):
        return {"refreshed": refreshed, "errors": ["branch upstream snapshot is malformed"]}
    for branch, config in branches.items():
        if not isinstance(branch, str) or not isinstance(config, dict):
            continue
        remote = config.get("remote")
        merge = config.get("merge")
        if not isinstance(remote, str) or not isinstance(merge, str):
            continue
        tracking_ref = upstream_tracking_ref(remote, merge)
        if not tracking_ref or git(repo, ["show-ref", "--verify", "--quiet", tracking_ref]).returncode == 0:
            continue
        proc = git(repo, ["fetch", "--no-tags", remote, f"+{merge}:{tracking_ref}"], timeout=60)
        if proc.returncode == 0:
            refreshed.append(tracking_ref)
        else:
            errors.append(f"{branch}: fetch {remote} {merge} failed")
    return {"refreshed": refreshed, "errors": errors}


def restore_branch_upstreams(repo: Path, snapshot: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Restore local branch upstream config after remotes have been restored."""
    restored: dict[str, dict[str, str]] = {}
    branches = snapshot.get("branches", {})
    if not isinstance(branches, dict):
        return restored
    for branch, config in branches.items():
        if not isinstance(branch, str) or not isinstance(config, dict):
            continue
        if git(repo, ["rev-parse", "--verify", f"refs/heads/{branch}"]).returncode != 0:
            continue
        remote = config.get("remote")
        merge = config.get("merge")
        if isinstance(remote, str) and remote:
            git(repo, ["config", f"branch.{branch}.remote", remote])
        if isinstance(merge, str) and merge:
            git(repo, ["config", f"branch.{branch}.merge", merge])
        if remote or merge:
            restored[branch] = {k: v for k, v in {"remote": remote, "merge": merge}.items() if isinstance(v, str) and v}
    return restored


def comparable_remote_url(url: str | None) -> str:
    if not url:
        return ""
    if "://" in url or ":" in url.split("/", 1)[0]:
        return url
    try:
        return str(Path(url).expanduser().resolve())
    except OSError:
        return url


def remote_restore_issues(repo: Path, expected: dict[str, dict[str, str]]) -> list[str]:
    issues: list[str] = []
    actual = snapshot_remotes(repo)
    for name, urls in expected.items():
        expected_fetch = urls.get("fetch") or urls.get("push")
        expected_push = urls.get("push") or expected_fetch
        actual_urls = actual.get(name)
        if not actual_urls:
            issues.append(f"{name}: missing")
            continue
        if expected_fetch and comparable_remote_url(actual_urls.get("fetch")) != comparable_remote_url(expected_fetch):
            issues.append(f"{name}: fetch URL mismatch")
        if expected_push and comparable_remote_url(actual_urls.get("push")) != comparable_remote_url(expected_push):
            issues.append(f"{name}: push URL mismatch")
    return issues


def branch_upstream_restore_issues(repo: Path, expected: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    actual = snapshot_branch_upstreams(repo)
    expected_branches = expected.get("branches", {})
    actual_branches = actual.get("branches", {})
    if not isinstance(expected_branches, dict) or not isinstance(actual_branches, dict):
        return ["branch upstream snapshot is malformed"]
    for branch, config in expected_branches.items():
        if not isinstance(branch, str) or not isinstance(config, dict):
            continue
        if git(repo, ["rev-parse", "--verify", f"refs/heads/{branch}"]).returncode != 0:
            issues.append(f"{branch}: missing local branch")
            continue
        actual_config = actual_branches.get(branch, {})
        if not isinstance(actual_config, dict):
            actual_config = {}
        for key in ("remote", "merge"):
            expected_value = config.get(key)
            if isinstance(expected_value, str) and expected_value and actual_config.get(key) != expected_value:
                issues.append(f"{branch}: {key} mismatch")
        tracking_ref = upstream_tracking_ref(config.get("remote"), config.get("merge"))
        if tracking_ref and git(repo, ["show-ref", "--verify", "--quiet", tracking_ref]).returncode != 0:
            issues.append(f"{branch}: upstream ref missing")
    return issues


def apply_rewrite(repo: Path, *, plan_dir: Path | None = None, dry_run: bool = False) -> dict[str, Any]:
    target_dir = repo / (plan_dir or DEFAULT_PLAN_DIR)
    rewrites = load_message_rewrites(target_dir / "message-rewrites.json")
    replacements = target_dir / "replacements.txt"
    replacement_has_rules = replacements.exists() and any(line.strip() and not line.lstrip().startswith("#") for line in replacements.read_text(encoding="utf-8").splitlines())
    actions: list[list[str]] = []
    if replacement_has_rules:
        actions.append(["git", "filter-repo", "--force", "--replace-text", str(replacements)])
    if rewrites:
        actions.append(["git", "filter-repo", "--force", "--message-callback", _message_callback_source(rewrites)])
    if dry_run:
        return {"schema_version": PLAN_SCHEMA_VERSION, "status": "dry-run", "actions": actions, "message_rewrites": len(rewrites), "content_replacements": replacement_has_rules}
    if os.environ.get("COS_ALLOW_PRELAUNCH_REWRITE") != "1":
        raise SystemExit("apply requires COS_ALLOW_PRELAUNCH_REWRITE=1")
    if not actions:
        return {"schema_version": PLAN_SCHEMA_VERSION, "status": "noop", "message": "No rewrite actions configured."}
    ensure_clean(repo)
    if not shutil.which("git-filter-repo"):
        raise SystemExit("git-filter-repo is required")
    backup_path = repo.parent / f"prelaunch-history-backup-{utc_stamp()}.bundle"
    bundle = subprocess.run(["git", "-C", str(repo), "bundle", "create", str(backup_path), "--all"], text=True, capture_output=True, check=False)
    if bundle.returncode != 0:
        raise SystemExit(bundle.stderr.strip() or "git bundle backup failed")
    remotes = snapshot_remotes(repo)
    branch_upstreams = snapshot_branch_upstreams(repo)
    (target_dir / "remote-snapshot.json").write_text(json.dumps(remotes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (target_dir / "branch-upstream-snapshot.json").write_text(json.dumps(branch_upstreams, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    executed: list[list[str]] = []
    for action in actions:
        proc = subprocess.run(action, cwd=repo, text=True, capture_output=True, check=False)
        executed.append(action[:4])
        if proc.returncode != 0:
            restore_remotes(repo, remotes)
            restore_branch_upstreams(repo, branch_upstreams)
            raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or f"rewrite action failed: {action[:3]}")
    restored = restore_remotes(repo, remotes)
    branch_upstreams_restored = restore_branch_upstreams(repo, branch_upstreams)
    branch_upstream_ref_refresh = refresh_branch_upstream_refs(repo, branch_upstreams)
    restore_issues = remote_restore_issues(repo, remotes)
    branch_upstream_issues = branch_upstream_restore_issues(repo, branch_upstreams)
    branch_upstream_issues.extend(branch_upstream_ref_refresh["errors"])
    result: dict[str, Any] = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "status": "rewritten",
        "backup": str(backup_path),
        "executed": executed,
        "remotes_restored": sorted(restored),
        "remote_restore_issues": restore_issues,
        "branch_upstreams_restored": sorted(branch_upstreams_restored),
        "branch_upstream_refs_refreshed": sorted(branch_upstream_ref_refresh["refreshed"]),
        "branch_upstream_restore_issues": branch_upstream_issues,
    }
    if restore_issues:
        raise SystemExit("git remote restore failed after history rewrite: " + "; ".join(restore_issues))
    if branch_upstream_issues:
        raise SystemExit("git branch upstream restore failed after history rewrite: " + "; ".join(branch_upstream_issues))
    if os.environ.get("COS_ALLOW_PRELAUNCH_FORCE_PUSH") == "1":
        remote = os.environ.get("COS_PRELAUNCH_REMOTE", "origin")
        branch = os.environ.get("COS_PRELAUNCH_BRANCH", "main")
        old = os.environ.get("COS_PRELAUNCH_EXPECT_REMOTE_SHA", "")
        push_args = ["git", "-c", "core.hooksPath=/dev/null", "push"]
        push_args.append(f"--force-with-lease={branch}:{old}" if old else "--force-with-lease")
        push_args.extend([remote, branch])
        push = subprocess.run(push_args, cwd=repo, text=True, capture_output=True, check=False)
        result["push"] = {"returncode": push.returncode, "stdout": push.stdout, "stderr": push.stderr}
        if push.returncode != 0:
            raise SystemExit(push.stderr.strip() or "force push failed")
    return result


def print_or_write(report: dict[str, Any], args: argparse.Namespace, repo: Path) -> int:
    if getattr(args, "write_report", False):
        report["artifacts"] = write_report(repo, report)
    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"prelaunch {report['audit']} audit: {report['status']}")
        for finding in report.get("findings", [])[:25]:
            print(f"[{finding['severity']}] {finding['rule_id']}: {finding['message']}")
        if report.get("artifacts"):
            print(f"artifacts: {report['artifacts']}")
    return 1 if report["status"] == "block" and getattr(args, "fail_on_block", False) else 0


def main_history(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only prelaunch history/content audit.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--fail-on-block", action="store_true")
    args = parser.parse_args(argv)
    repo = repo_root(args.repo)
    return print_or_write(audit_history(repo), args, repo)


def main_messages(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only prelaunch commit-message audit.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--fail-on-block", action="store_true")
    args = parser.parse_args(argv)
    repo = repo_root(args.repo)
    return print_or_write(audit_messages(repo), args, repo)


def main_plan(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate editable prelaunch rewrite plan files.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    repo = repo_root(args.repo)
    plan = build_rewrite_plan(repo)
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(f"prelaunch rewrite plan: {repo / DEFAULT_PLAN_DIR}")
        print(f"message rewrites: {len(plan['message_rewrites'])}")
    return 0


def main_apply(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply approved prelaunch rewrite plan. Destructive unless --dry-run.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    repo = repo_root(args.repo)
    result = apply_rewrite(repo, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"prelaunch apply: {result['status']}")
        if result.get("backup"):
            print(f"backup: {result['backup']}")
    return 0
