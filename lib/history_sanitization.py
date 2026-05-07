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
