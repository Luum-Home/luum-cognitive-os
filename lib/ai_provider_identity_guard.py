"""Guard against AI-provider-looking invented authorship emails.

This primitive blocks the pattern we hit during public-history cleanup:
models inventing or preserving provider-looking identities such as
Co-authored-by trailers or noreply addresses for AI systems. The policy is
intentionally provider-generic; it is not a one-off check for a single model.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

DEFAULT_POLICY = Path("manifests/ai-provider-identity-policy.yaml")
SCHEMA_VERSION = "ai-provider-identity-guard-report/v1"
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
TRAILER_RE = re.compile(r"^\s*(co-authored-by|coauthored-by|signed-off-by|authored-by)\s*:\s*(.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    code: str
    excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "line": self.line, "code": self.code, "excerpt": self.excerpt}


def load_policy(project_dir: Path, policy_path: Path | None = None) -> dict[str, Any]:
    path = policy_path or project_dir / DEFAULT_POLICY
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _norm_list(policy: dict[str, Any], key: str) -> list[str]:
    return [str(v).lower() for v in policy.get(key, []) or [] if str(v).strip()]


def _is_allowed_path(path: str, policy: dict[str, Any]) -> bool:
    normalized = path.replace("\\", "/")
    return any(normalized.startswith(prefix) for prefix in policy.get("allowed_paths", []) or [])


def _is_allowed_email(email: str, policy: dict[str, Any]) -> bool:
    allowed = {str(v).lower() for v in policy.get("allowed_emails", []) or []}
    return email.lower() in allowed


def _email_is_provider_like(email: str, policy: dict[str, Any]) -> bool:
    if _is_allowed_email(email, policy):
        return False
    local, _, domain = email.lower().partition("@")
    domains = set(_norm_list(policy, "blocked_email_domains"))
    local_parts = set(_norm_list(policy, "blocked_email_local_parts"))
    provider_names = set(_norm_list(policy, "provider_names"))
    if domain in domains and (local in local_parts or any(token in local for token in provider_names)):
        return True
    if local in local_parts and domain in domains:
        return True
    return False


def _trailer_claims_provider_identity(line: str, policy: dict[str, Any]) -> bool:
    match = TRAILER_RE.match(line)
    if not match:
        return False
    value = match.group(2).lower()
    provider_names = set(_norm_list(policy, "provider_names"))
    if any(name in value for name in provider_names):
        return True
    return any(_email_is_provider_like(email, policy) for email in EMAIL_RE.findall(value))


def scan_text(text: str, *, path: str, policy: dict[str, Any]) -> list[Finding]:
    if _is_allowed_path(path, policy):
        return []
    findings: list[Finding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if _trailer_claims_provider_identity(line, policy):
            findings.append(Finding(path, line_no, "ai-provider-authorship-trailer", line.strip()[:220]))
            continue
        for email in EMAIL_RE.findall(line):
            if _email_is_provider_like(email, policy):
                findings.append(Finding(path, line_no, "ai-provider-email", line.strip()[:220]))
                break
    return findings


def _git(project_dir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(project_dir), *args], text=True, capture_output=True, check=False)


def _git_bytes(project_dir: Path, args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(project_dir), *args], text=False, capture_output=True, check=False)


def staged_paths(project_dir: Path) -> list[str]:
    proc = _git(project_dir, ["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def staged_text(project_dir: Path, path: str) -> str | None:
    proc = _git_bytes(project_dir, ["show", f":{path}"])
    if proc.returncode != 0:
        return None
    if b"\x00" in proc.stdout:
        return None
    try:
        return proc.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None


def tracked_paths(project_dir: Path) -> list[str]:
    proc = _git(project_dir, ["ls-files"])
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def tracked_text(project_dir: Path, path: str) -> str | None:
    file_path = project_dir / path
    if not file_path.exists() or not file_path.is_file():
        return None
    try:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    if "\x00" in text:
        return None
    return text


def scan_paths(paths: Iterable[Path], *, project_dir: Path, policy: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        rel = str(path if path.is_absolute() else path)
        try:
            rel = str(path.resolve().relative_to(project_dir.resolve()))
        except ValueError:
            pass
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        findings.extend(scan_text(text, path=rel, policy=policy))
    return findings


def scan_tracked(project_dir: Path, policy: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for path in tracked_paths(project_dir):
        text = tracked_text(project_dir, path)
        if text is None:
            continue
        findings.extend(scan_text(text, path=path, policy=policy))
    return findings


def scan_staged(project_dir: Path, policy: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for path in staged_paths(project_dir):
        text = staged_text(project_dir, path)
        if text is None:
            continue
        findings.extend(scan_text(text, path=path, policy=policy))
    return findings


def build_report(findings: list[Finding]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "block" if findings else "pass",
        "finding_count": len(findings),
        "findings": [finding.to_dict() for finding in findings],
        "policy": "Do not publish AI-provider-looking invented emails or co-author trailers; use COS provenance/session artifacts instead.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Block AI-provider-looking invented author/contact identities.")
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--staged", action="store_true", help="Scan staged file contents from the git index")
    parser.add_argument("--tracked", action="store_true", help="Scan tracked working-tree files")
    parser.add_argument("--path", action="append", default=[], help="Scan a working-tree path; may be repeated")
    parser.add_argument("--commit-msg", type=Path, help="Scan a commit message file")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    project_dir = args.project_dir.resolve()
    policy = load_policy(project_dir, args.policy)
    findings: list[Finding] = []
    if args.staged:
        findings.extend(scan_staged(project_dir, policy))
    if args.tracked:
        findings.extend(scan_tracked(project_dir, policy))
    if args.path:
        findings.extend(scan_paths([Path(p) for p in args.path], project_dir=project_dir, policy=policy))
    if args.commit_msg:
        text = args.commit_msg.read_text(encoding="utf-8", errors="ignore")
        findings.extend(scan_text(text, path=str(args.commit_msg), policy=policy))

    report = build_report(findings)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif findings:
        print("BLOCKED: AI-provider-looking invented identity found.")
        for finding in findings[:20]:
            print(f"  {finding.path}:{finding.line}: {finding.code}: {finding.excerpt}")
        print("Use the verified human operator identity and COS provenance/session artifacts instead.")
    return 2 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
