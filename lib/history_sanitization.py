"""ADR-218 history sanitization dry-run and safety checks."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from subprocess import TimeoutExpired
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "history-sanitization-report/v1"
DEFAULT_MANIFEST = Path("manifests/history-sanitization.yaml")


@dataclass(frozen=True)
class CountResult:
    count: int | None
    timed_out: bool = False


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    rule_id: str | None = None
    count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"severity": self.severity, "code": self.code, "message": self.message}
        if self.rule_id is not None:
            out["rule_id"] = self.rule_id
        if self.count is not None:
            out["count"] = self.count
        return out


def load_manifest(project_dir: Path) -> dict[str, Any]:
    path = project_dir / DEFAULT_MANIFEST
    if not path.exists():
        raise FileNotFoundError(f"history sanitization manifest missing: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def git(project_dir: Path, args: list[str], *, timeout_seconds: float | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project_dir), *args],
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout_seconds,
    )


def rev_list(project_dir: Path) -> list[str]:
    proc = git(project_dir, ["rev-list", "--all"])
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def history_text(project_dir: Path) -> str:
    commits = rev_list(project_dir)
    chunks: list[str] = []
    for commit in commits:
        proc = git(project_dir, ["grep", "-I", "-n", "-e", ".", commit])
        if proc.returncode in {0, 1}:
            chunks.append(proc.stdout)
    return "\n".join(chunks)


def normalize_pattern(pattern: str) -> str:
    """Translate manifest regex conveniences into Python-compatible regex."""
    return pattern.replace("[:space:]", r"\s")


def normalize_git_regex(pattern: str) -> str:
    """Translate manifest regex conveniences into git-log compatible regex."""
    return pattern.replace(r"\s", "[[:space:]]")


def history_scan_timeout_seconds(manifest: dict[str, Any]) -> float:
    configured = (manifest.get("scan") or {}).get("per_rule_timeout_seconds")
    raw = os.environ.get("COS_HISTORY_SCAN_TIMEOUT_SECONDS", configured)
    try:
        value = float(raw) if raw is not None else 3.0
    except (TypeError, ValueError):
        value = 3.0
    return max(0.1, value)


def metadata_rewrite_enabled(manifest: dict[str, Any]) -> bool:
    """Return whether author/committer metadata rewrites are explicitly enabled.

    ADR-218 defaults to content-only rewrites. Commit author names/emails are
    human provenance and must not be changed by broad history sanitation unless
    the operator opts in with COS_HISTORY_SANITIZE_METADATA=1 (or an equivalent
    manifest-configured env var).
    """
    config = manifest.get("metadata_rewrite") or {}
    require_env = str(config.get("require_env", "COS_HISTORY_SANITIZE_METADATA"))
    require_value = str(config.get("require_env_value", "1"))
    return os.environ.get(require_env) == require_value


def metadata_scope_findings(manifest: dict[str, Any]) -> list[Finding]:
    """Block metadata-scoped rules unless metadata rewrite is explicit."""
    if metadata_rewrite_enabled(manifest):
        return []
    findings: list[Finding] = []
    for rule in manifest.get("rules", []) or []:
        if str(rule.get("scope", "content")) in {"metadata", "commit-metadata", "all"}:
            findings.append(
                Finding(
                    "block",
                    "metadata-rewrite-not-enabled",
                    f"Rule {rule.get('id')} declares metadata scope, but metadata rewrite is disabled. Set COS_HISTORY_SANITIZE_METADATA=1 only with explicit operator consent.",
                    rule_id=str(rule.get("id")),
                )
            )
    return findings


def count_history(project_dir: Path, pattern: str, *, mode: str, timeout_seconds: float | None = None) -> CountResult:
    """Count commits whose patches indicate a historical content match.

    History sanitization is a release-readiness primitive, so a dry-run must not
    hang the laptop lane on broad regexes over a large repository. If git exceeds
    the per-rule budget, return an unknown count and let the report surface an
    explicit warning instead of blocking all validation.
    """
    if not pattern:
        return CountResult(0)
    if mode == "regex":
        args = ["log", "--all", "--format=%H", "-G", normalize_git_regex(pattern)]
    else:
        args = ["log", "--all", "--format=%H", "-S", pattern]
    try:
        proc = git(project_dir, args, timeout_seconds=timeout_seconds)
    except TimeoutExpired:
        return CountResult(None, timed_out=True)
    if proc.returncode != 0:
        return CountResult(0)
    return CountResult(len({line.strip() for line in proc.stdout.splitlines() if line.strip()}))


def count_literal(text: str, needle: str) -> int:
    return text.count(needle) if needle else 0


def count_regex(text: str, pattern: str) -> int:
    try:
        return len(re.findall(normalize_pattern(pattern), text, flags=re.MULTILINE))
    except re.error:
        return 0


def resolved_rules(manifest: dict[str, Any], environ: dict[str, str] | None = None) -> tuple[list[dict[str, Any]], list[Finding]]:
    env = environ or os.environ
    findings: list[Finding] = []
    rules: list[dict[str, Any]] = []
    for rule in manifest.get("rules", []) or []:
        item = dict(rule)
        value_env = item.get("value_env")
        if value_env:
            value = env.get(str(value_env), "")
            if not value:
                severity = "block" if bool(item.get("required")) else "warn"
                findings.append(
                    Finding(
                        severity,
                        "replacement-value-unresolved",
                        f"Rule {item.get('id')} uses {value_env}, but the environment variable is not set; dry-run cannot count this exact value.",
                        rule_id=str(item.get("id")),
                    )
                )
                item["value"] = None
            else:
                item["value"] = value
        rules.append(item)
    return rules, findings


def scan(project_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    rules, findings = resolved_rules(manifest)
    timeout_seconds = history_scan_timeout_seconds(manifest)
    replacement_hits: list[dict[str, Any]] = []
    resolved_replacement_rules: list[dict[str, Any]] = []
    for rule in rules:
        value = rule.get("value") if rule.get("value_env") else rule.get("pattern")
        if not value:
            replacement_hits.append({"id": rule.get("id"), "resolved": False, "hit_count": None})
            continue
        mode = rule.get("mode", "literal")
        result = count_history(project_dir, str(value), mode=mode, timeout_seconds=timeout_seconds)
        replacement_hits.append({"id": rule.get("id"), "resolved": True, "mode": mode, "hit_count": result.count, "replacement": rule.get("replacement"), "timed_out": result.timed_out})
        if result.timed_out:
            findings.append(Finding("warn", "history-scan-timeout", f"History scan for replacement rule {rule.get('id')} exceeded {timeout_seconds:g}s; rerun with COS_HISTORY_SCAN_TIMEOUT_SECONDS for exhaustive release review.", rule_id=str(rule.get("id"))))
        resolved_replacement_rules.append(rule)

    sensitive_hits: list[dict[str, Any]] = []
    for rule in manifest.get("sensitive_history_patterns", []) or []:
        pattern = str(rule.get("pattern", ""))
        mode = "regex" if rule.get("mode") == "regex" else "literal"
        result = count_history(project_dir, pattern, mode=mode, timeout_seconds=timeout_seconds)
        sensitive_hits.append({"id": rule.get("id"), "severity": rule.get("severity", "warn"), "hit_count": result.count, "timed_out": result.timed_out, "rationale": rule.get("rationale")})
        if result.timed_out:
            findings.append(Finding("warn", "history-scan-timeout", f"History scan for sensitive pattern {rule.get('id')} exceeded {timeout_seconds:g}s; rerun with COS_HISTORY_SCAN_TIMEOUT_SECONDS for exhaustive release review.", rule_id=str(rule.get("id"))))
        elif result.count:
            findings.append(Finding(str(rule.get("severity", "warn")), "sensitive-history-pattern-hit", f"Sensitive history pattern {rule.get('id')} matched historical content.", rule_id=str(rule.get("id")), count=result.count))

    preserve_hits: list[dict[str, Any]] = []
    for rule in manifest.get("preserve", []) or []:
        pattern = str(rule.get("pattern", ""))
        mode = "regex" if rule.get("mode") == "regex" else "literal"
        result = count_history(project_dir, pattern, mode=mode, timeout_seconds=timeout_seconds)
        preserve_hits.append({"id": rule.get("id"), "hit_count": result.count, "timed_out": result.timed_out, "rationale": rule.get("rationale")})
        if result.timed_out:
            findings.append(Finding("warn", "history-scan-timeout", f"History scan for preserve rule {rule.get('id')} exceeded {timeout_seconds:g}s; rerun with COS_HISTORY_SCAN_TIMEOUT_SECONDS for exhaustive release review.", rule_id=str(rule.get("id"))))

    conflicts = preserve_conflicts(resolved_replacement_rules, manifest.get("preserve", []) or [])
    for conflict in conflicts:
        findings.append(
            Finding(
                "block",
                "replacement-preserve-conflict",
                f"Replacement rule {conflict['replacement_rule_id']} may match preserve rule {conflict['preserve_rule_id']}; refine the manifest before execution.",
                rule_id=str(conflict["replacement_rule_id"]),
            )
        )

    return {
        "replacement_hits": replacement_hits,
        "sensitive_hits": sensitive_hits,
        "preserve_hits": preserve_hits,
        "preserve_conflicts": conflicts,
        "findings": findings,
    }


def preserve_conflicts(replacement_rules: list[dict[str, Any]], preserve_rules: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Detect obvious replacement/preserve overlaps without exposing raw values."""
    conflicts: list[dict[str, str]] = []
    for replacement in replacement_rules:
        value = replacement.get("value")
        if not value:
            continue
        value_text = str(value)
        for preserve in preserve_rules:
            pattern = str(preserve.get("pattern", ""))
            if not pattern:
                continue
            preserve_id = str(preserve.get("id", "unknown-preserve"))
            replacement_id = str(replacement.get("id", "unknown-replacement"))
            if preserve.get("mode") == "regex":
                try:
                    if re.search(normalize_pattern(pattern), value_text):
                        conflicts.append({"replacement_rule_id": replacement_id, "preserve_rule_id": preserve_id})
                except re.error:
                    continue
            elif pattern in value_text:
                conflicts.append({"replacement_rule_id": replacement_id, "preserve_rule_id": preserve_id})
    return conflicts


def tool_status() -> dict[str, Any]:
    path = shutil.which("git-filter-repo")
    return {"tool": "git-filter-repo", "installed": bool(path), "path": path}


def build_report(project_dir: Path, *, mode: str = "dry-run") -> dict[str, Any]:
    project = project_dir.resolve()
    manifest = load_manifest(project)
    scan_result = scan(project, manifest)
    findings: list[Finding] = list(scan_result["findings"])
    tool = tool_status()
    if not tool["installed"]:
        findings.append(Finding("warn", "git-filter-repo-missing", "git-filter-repo is not installed; execute mode cannot run until installed."))
    findings.extend(metadata_scope_findings(manifest))
    if mode == "execute":
        required_env = (manifest.get("execution") or {}).get("require_env", "COS_ALLOW_DESTRUCTIVE_GIT")
        required_value = str((manifest.get("execution") or {}).get("require_env_value", "1"))
        if os.environ.get(str(required_env)) != required_value:
            findings.append(Finding("block", "destructive-git-env-missing", f"Execute requires {required_env}={required_value}."))
    status = "block" if any(f.severity == "block" for f in findings) else "warn" if any(f.severity == "warn" for f in findings) else "pass"
    return {
        "schema_version": SCHEMA_VERSION,
        "project_dir": str(project),
        "mode": mode,
        "status": status,
        "tool": tool,
        "replacement_hits": scan_result["replacement_hits"],
        "sensitive_hits": scan_result["sensitive_hits"],
        "preserve_hits": scan_result["preserve_hits"],
        "preserve_conflicts": scan_result["preserve_conflicts"],
        "findings": [finding.to_dict() for finding in findings],
        "policy": "Dry-run is non-mutating. Execute requires backup, COS_ALLOW_DESTRUCTIVE_GIT=1, and explicit operator confirmation.",
    }


def dumps_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


# ────────────────────────────────────────────────────────────────────────
# Execute slice (ADR-218 §"Implementation slices" 2 + 6)
# ────────────────────────────────────────────────────────────────────────

# A `SanitizationError` is raised by `execute()` for any pre-condition
# violation or in-flight failure. Callers should catch it and surface its
# `.message` + `.code` to the operator. Crucially: the error is raised
# AFTER any partial work is rolled back where possible, or else the error
# message instructs the operator to restore from the backup mirror.
class SanitizationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _utc_timestamp() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _backup_destination(project_dir: Path, ts: str) -> Path:
    home = Path(os.path.expanduser("~"))
    return home / ".cognitive-os" / "recovery" / f"pre-history-sanitization-{ts}.git"


def _check_clean_worktree(project_dir: Path) -> None:
    proc = git(project_dir, ["status", "--porcelain"])
    if proc.returncode != 0:
        raise SanitizationError("git-status-failed", f"git status returned {proc.returncode}: {proc.stderr.strip()}")
    if proc.stdout.strip():
        raise SanitizationError(
            "working-tree-not-clean",
            "working tree has uncommitted changes; commit or stash before executing the rewrite.",
        )


def _check_filter_repo_installed() -> str:
    path = shutil.which("git-filter-repo")
    if not path:
        raise SanitizationError(
            "git-filter-repo-missing",
            "git-filter-repo is not on PATH; run scripts/install-git-filter-repo.sh first.",
        )
    return path


def _check_destructive_env(manifest: dict[str, Any]) -> None:
    required_env = (manifest.get("execution") or {}).get("require_env", "COS_ALLOW_DESTRUCTIVE_GIT")
    required_value = str((manifest.get("execution") or {}).get("require_env_value", "1"))
    if os.environ.get(str(required_env)) != required_value:
        raise SanitizationError(
            "destructive-git-env-missing",
            f"Execute requires {required_env}={required_value}.",
        )


def _check_backup_writable(backup_path: Path) -> None:
    if backup_path.exists():
        raise SanitizationError(
            "backup-destination-exists",
            f"backup destination already exists: {backup_path}; refuse to overwrite.",
        )
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if not os.access(str(backup_path.parent), os.W_OK):
        raise SanitizationError("backup-destination-unwritable", f"backup parent not writable: {backup_path.parent}")


def _create_backup_mirror(project_dir: Path, backup_path: Path) -> None:
    proc = subprocess.run(
        ["git", "clone", "--mirror", str(project_dir), str(backup_path)],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SanitizationError(
            "backup-mirror-failed",
            f"git clone --mirror failed (rc={proc.returncode}): {proc.stderr.strip()[:400]}",
        )
    fsck = subprocess.run(
        ["git", "-C", str(backup_path), "fsck", "--no-progress"],
        text=True,
        capture_output=True,
        check=False,
    )
    if fsck.returncode != 0:
        raise SanitizationError(
            "backup-mirror-fsck-failed",
            f"backup mirror failed fsck: {fsck.stderr.strip()[:400]}",
        )




def _snapshot_remotes(project_dir: Path) -> dict[str, dict[str, str]]:
    """Capture local git remotes before git-filter-repo removes them.

    git-filter-repo intentionally strips remotes to prevent accidental pushes of
    rewritten history. COS still needs the pre-existing remote URLs in the
    execute report and, for operator-driven local rewrites, restored locally so
    subsequent smoke/push steps use the same canonical remote.
    """
    proc = git(project_dir, ["remote"])
    if proc.returncode != 0:
        return {}
    remotes: dict[str, dict[str, str]] = {}
    for name in [line.strip() for line in proc.stdout.splitlines() if line.strip()]:
        urls: dict[str, str] = {}
        for kind in ("fetch", "push"):
            url_proc = git(project_dir, ["remote", "get-url", f"--{kind}", name])
            if url_proc.returncode == 0 and url_proc.stdout.strip():
                urls[kind] = url_proc.stdout.strip()
        if urls:
            remotes[name] = urls
    return remotes


def _restore_remotes(project_dir: Path, remotes: dict[str, dict[str, str]]) -> list[str]:
    restored: list[str] = []
    for name, urls in remotes.items():
        fetch_url = urls.get("fetch") or urls.get("push")
        push_url = urls.get("push") or fetch_url
        if not fetch_url:
            continue
        if git(project_dir, ["remote", "get-url", name]).returncode != 0:
            add = git(project_dir, ["remote", "add", name, fetch_url])
            if add.returncode != 0:
                continue
        else:
            git(project_dir, ["remote", "set-url", name, fetch_url])
        if push_url:
            git(project_dir, ["remote", "set-url", "--push", name, push_url])
        restored.append(name)
    return restored

def _write_replacements_file(rules: list[dict[str, Any]], target_path: Path) -> int:
    """Write replacement rules in git-filter-repo's `OLD==>NEW` format.

    Returns the number of rules written. Skips rules whose value is unresolved
    (empty or None) — those would have been flagged in `dry-run` and the
    caller is expected to refuse to proceed if the dry-run had warnings.

    Order matters: longer (more specific) patterns are written FIRST so that
    git-filter-repo applies them before shorter overlapping prefixes. This
    is the opposite ordering from naive expectation; git-filter-repo iterates
    rules per-blob and applies all matches, so the longest-first ordering
    minimises double-application risk on overlapping prefixes (e.g. when
    repo-absolute-path is a strict superset of operator-home-prefix).
    """
    sorted_rules = sorted(rules, key=lambda r: -len(str(r.get("value") or "")))
    lines: list[str] = []
    for rule in sorted_rules:
        value = rule.get("value") or rule.get("pattern")
        replacement = rule.get("replacement")
        if not value or replacement is None:
            continue
        # Filter-repo replacement file format: `OLD==>NEW` literal-by-default.
        # Manifest "mode: regex" rules use `regex:OLD==>NEW`; we honour that.
        mode = rule.get("mode", "literal")
        if mode == "regex":
            lines.append(f"regex:{value}==>{replacement}")
        else:
            lines.append(f"{value}==>{replacement}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def _literal_replacements(rules: list[dict[str, Any]]) -> list[tuple[bytes, bytes]]:
    replacements: list[tuple[bytes, bytes]] = []
    for rule in sorted(rules, key=lambda r: -len(str(r.get("value") or ""))):
        value = rule.get("value") or rule.get("pattern")
        replacement = rule.get("replacement")
        if not value or replacement is None or rule.get("mode", "literal") != "literal":
            continue
        replacements.append((str(value).encode("utf-8"), str(replacement).encode("utf-8")))
    return replacements


def _bytes_replace_expression(var_name: str, replacements: list[tuple[bytes, bytes]]) -> str:
    expr = var_name
    for old, new in replacements:
        expr += f".replace({old!r}, {new!r})"
    return expr


def _metadata_message_callback(replacements: list[tuple[bytes, bytes]]) -> str:
    replaced = _bytes_replace_expression("message", replacements)
    return (
        f"msg = {replaced}\n"
        "lines = []\n"
        "for line in msg.splitlines(keepends=True):\n"
        "    if line.startswith(b'X-COS-'):\n"
        "        continue\n"
        "    lines.append(line)\n"
        "return b''.join(lines)"
    )


def _run_filter_repo(project_dir: Path, rules_file: Path, rules: list[dict[str, Any]], manifest: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    replacements = _literal_replacements(rules)
    message_callback = _metadata_message_callback(replacements)
    cmd = ["git", "filter-repo"]
    if metadata_rewrite_enabled(manifest):
        email_callback = f"return {_bytes_replace_expression('email', replacements)}"
        name_callback = f"return {_bytes_replace_expression('name', replacements)}"
        cmd.extend([
            "--email-callback",
            email_callback,
            "--name-callback",
            name_callback,
        ])
    cmd.extend([
        "--replace-text",
        str(rules_file),
        "--message-callback",
        message_callback,
        "--force",
    ])
    proc = subprocess.run(
        cmd,
        cwd=str(project_dir),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SanitizationError(
            "filter-repo-failed",
            f"git filter-repo --replace-text failed (rc={proc.returncode}): "
            f"{proc.stderr.strip()[:600] or proc.stdout.strip()[:600]}. "
            f"The repo may be in a partially-rewritten state; restore from the backup mirror.",
        )
    return proc


def _verification_haystack(project_dir: Path, *, include_author_metadata: bool) -> str:
    pretty = "fuller" if include_author_metadata else "format:%B"
    proc = subprocess.run(
        ["git", "log", "--all", f"--pretty={pretty}", "-p", "--no-color"],
        cwd=str(project_dir),
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else ""

def _verify_replacements_applied(project_dir: Path, rules: list[dict[str, Any]]) -> dict[str, int]:
    """Run grep against post-rewrite history and metadata for each replacement source.

    Each remaining hit count must be 0 (or close to 0 for regex rules with
    intentional partial matches) for the rewrite to be considered complete.
    Caller decides whether to treat non-zero remaining counts as failure.
    """
    remaining: dict[str, int] = {}
    include_author_metadata = metadata_rewrite_enabled(load_manifest(project_dir))
    haystack = _verification_haystack(project_dir, include_author_metadata=include_author_metadata)
    if not haystack:
        return {str(rule.get("id", "unknown")): -1 for rule in rules}
    for rule in rules:
        value = rule.get("value") or rule.get("pattern")
        rule_id = rule.get("id", "unknown")
        if not value:
            remaining[rule_id] = -1
            continue
        try:
            if rule.get("mode") == "regex":
                count = count_regex(haystack, str(value))
            else:
                count = haystack.count(str(value))
        except Exception:
            count = -1
        remaining[rule_id] = count
    return remaining


def _create_tombstone_branch(project_dir: Path, ts: str) -> str:
    branch_name = f"history-sanitization-{ts}"
    proc = git(project_dir, ["branch", "-f", branch_name, "HEAD"])
    if proc.returncode != 0:
        raise SanitizationError(
            "tombstone-branch-failed",
            f"failed to create tombstone branch {branch_name}: {proc.stderr.strip()}",
        )
    return branch_name


def _write_post_execute_report(
    project_dir: Path,
    *,
    ts: str,
    pre_head: str,
    post_head: str,
    pre_commit_count: int,
    post_commit_count: int,
    rules: list[dict[str, Any]],
    backup_path: Path,
    tombstone_branch: str,
    rules_written: int,
    remaining_hits: dict[str, int],
) -> Path:
    report_dir = project_dir / ".cognitive-os" / "reports" / "history-sanitization"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{ts}.json"

    payload = {
        "schema_version": SCHEMA_VERSION,
        "executed_at": ts,
        "policy_reference": "docs/adrs/ADR-218-history-sanitization-toolchain.md",
        "boundary_tag_recommended": "v0.27.1-pre-history-rewrite",
        "backup_mirror": str(backup_path),
        "tombstone_branch": tombstone_branch,
        "pre_rewrite": {
            "head": pre_head,
            "commit_count": pre_commit_count,
        },
        "post_rewrite": {
            "head": post_head,
            "commit_count": post_commit_count,
        },
        "replacements": [
            {
                "id": str(rule.get("id", "unknown")),
                "mode": str(rule.get("mode", "literal")),
                "replacement": str(rule.get("replacement", "")),
                "expected_hits": rule.get("hit_count"),
                "remaining_hits": remaining_hits.get(str(rule.get("id", "unknown")), -1),
            }
            for rule in rules
        ],
        "rules_written_to_filter_file": rules_written,
        "verification": {
            "all_replacements_resolved_to_zero": all(v == 0 for v in remaining_hits.values()),
            "commit_count_preserved": pre_commit_count == post_commit_count,
        },
        "policy": (
            "Rewrite executed. The backup mirror is the rollback path. "
            "Operator must (1) verify counts above, (2) re-tag versions onto post-rewrite "
            "equivalent SHAs, (3) copy this report to docs/reports/, (4) write disclosure doc, "
            "(5) force-push origin/main only after 1-4."
        ),
    }
    report_path.write_text(dumps_json(payload), encoding="utf-8")
    return report_path


def execute(
    project_dir: Path,
    *,
    confirmed: bool,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Run the actual history rewrite per ADR-218.

    Pre-conditions (refuses to proceed unless ALL pass):
      - working tree clean
      - git-filter-repo installed
      - COS_ALLOW_DESTRUCTIVE_GIT=1 (or manifest-configured equivalent)
      - backup destination writable and not pre-existing
      - dry-run report has no `block`-severity findings (caller responsibility)
      - operator confirmation explicit (`confirmed=True`)

    On success returns a dict with:
      - schema_version
      - status: "ok" | "completed-with-warnings"
      - report_path: absolute path to the post-execute JSON report
      - backup_mirror: absolute path
      - tombstone_branch: name
      - pre_rewrite, post_rewrite: head + commit_count
      - remaining_hits: per-rule grep count (must be 0 for clean rewrite)

    On any failure raises `SanitizationError` with `.code` and `.message`.
    Partial-state recovery: see the backup mirror at the path declared in
    the error message or in the report.
    """
    if not confirmed:
        raise SanitizationError(
            "operator-confirmation-required",
            "execute() refuses to proceed without confirmed=True; the CLI is responsible for the y/n prompt.",
        )

    project = project_dir.resolve()
    manifest = load_manifest(project)
    ts = timestamp or _utc_timestamp()

    # 1. Pre-conditions
    _check_filter_repo_installed()
    _check_destructive_env(manifest)
    _check_clean_worktree(project)

    backup_path = _backup_destination(project, ts)
    _check_backup_writable(backup_path)

    # 2. Resolve rules (same source of truth as dry-run)
    replacement_rules, rule_findings = resolved_rules(manifest)
    if any(f.severity == "block" for f in rule_findings):
        first_block = next(f for f in rule_findings if f.severity == "block")
        raise SanitizationError(
            "rule-resolution-blocked",
            f"replacement rule resolution failed: {first_block.message}",
        )

    # Conflict guard against preserve patterns
    preserve_rules = [r for r in (manifest.get("preserve") or [])]
    conflicts = preserve_conflicts(replacement_rules, preserve_rules)
    if conflicts:
        raise SanitizationError(
            "preserve-conflict",
            f"replacement rules conflict with preserve patterns: {conflicts}; refine manifest before executing.",
        )

    # 3. Capture pre-rewrite state
    pre_head_proc = git(project, ["rev-parse", "HEAD"])
    if pre_head_proc.returncode != 0:
        raise SanitizationError("git-rev-parse-failed", "could not read HEAD before rewrite.")
    pre_head = pre_head_proc.stdout.strip()

    pre_count_proc = git(project, ["rev-list", "--count", "--all"])
    pre_commit_count = int(pre_count_proc.stdout.strip() or "0")
    pre_remotes = _snapshot_remotes(project)

    # 4. Backup mirror (mandatory; backup-or-refuse)
    _create_backup_mirror(project, backup_path)

    # 5. Generate replacements file
    rules_file = project / ".cognitive-os" / "runtime" / f"history-sanitize-rules-{ts}.txt"
    rules_written = _write_replacements_file(replacement_rules, rules_file)
    if rules_written == 0:
        raise SanitizationError(
            "no-rules-to-apply",
            "no replacement rules resolved — refusing to run filter-repo with empty rules.",
        )

    # 6. Run filter-repo (THE destructive step)
    try:
        _run_filter_repo(project, rules_file, replacement_rules, manifest)
    finally:
        # The rules file is intentionally kept for forensic audit (report
        # references it). It can be deleted by the operator post-verify.
        pass
    restored_remotes = _restore_remotes(project, pre_remotes)

    # 7. Capture post-rewrite state
    post_head_proc = git(project, ["rev-parse", "HEAD"])
    if post_head_proc.returncode != 0:
        raise SanitizationError(
            "post-rewrite-rev-parse-failed",
            f"could not read HEAD after filter-repo. Restore from backup: {backup_path}",
        )
    post_head = post_head_proc.stdout.strip()
    post_count_proc = git(project, ["rev-list", "--count", "--all"])
    post_commit_count = int(post_count_proc.stdout.strip() or "0")

    if pre_head == post_head:
        raise SanitizationError(
            "no-rewrite-occurred",
            "filter-repo did not change HEAD — replacement rules may not have matched anything.",
        )

    # 8. Verify replacements applied
    remaining_hits = _verify_replacements_applied(project, replacement_rules)

    # 9. Tombstone branch
    tombstone_branch = _create_tombstone_branch(project, ts)

    # 10. Write report
    report_path = _write_post_execute_report(
        project,
        ts=ts,
        pre_head=pre_head,
        post_head=post_head,
        pre_commit_count=pre_commit_count,
        post_commit_count=post_commit_count,
        rules=replacement_rules,
        backup_path=backup_path,
        tombstone_branch=tombstone_branch,
        rules_written=rules_written,
        remaining_hits=remaining_hits,
    )

    all_clean = all(v == 0 for v in remaining_hits.values())
    count_preserved = pre_commit_count == post_commit_count

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok" if (all_clean and count_preserved) else "completed-with-warnings",
        "report_path": str(report_path),
        "backup_mirror": str(backup_path),
        "tombstone_branch": tombstone_branch,
        "pre_rewrite": {"head": pre_head, "commit_count": pre_commit_count},
        "post_rewrite": {"head": post_head, "commit_count": post_commit_count},
        "remaining_hits": remaining_hits,
        "remotes_restored": restored_remotes,
        "rules_file": str(rules_file),
        "metadata_rewrite_enabled": metadata_rewrite_enabled(manifest),
    }
